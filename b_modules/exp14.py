"""直流电源特性实验数据处理模块。

按指导书《直流电源特性B（实验指导）》四部分内容：
一、不同负载下纹波系数的测量（基础内容，写实验报告）
1. 负载功率曲线：信号源 500 Hz、Vp-p=10 V 正弦，1μF π 型全波整流滤波，
   RL 电阻箱在 20~2000 Ω 内取 10~12 个点，由 P = U_DC²/R 求输出功率，
   回答"输出功率最大时负载有多大"；
2. 纹波系数曲线：同电路分别用万用表直流、交流电压档测输出端电压，Ku = U_AC/U_DC；
3. 电容对纹波系数的影响：改用单个 10μF 电容（全波整流滤波），重复测量并分析优劣。
二、非线性内阻电源开路电压和短路电流的测定（提升内容）：
   等效电路（补偿法）测开路电压，取样电阻法间接测短路电流 I_sc = U_s/Rs，
   计算电源内阻 r = E/I_sc。
三、电表改装（进阶内容）：半偏法测 100μA 电流表内阻 R_g = R2 − 2R1，
   改装成 2.00V 电压表需串联 R_ser = U/I_g − R_g。
四、改装电表的定标（高阶内容）：与标准电压表逐点比对，由最大绝对误差
   与量程之比定电表等级。

指导书要求选交报告（基础部分保留报告），report_enabled 保持默认 True。
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from head import *  # 旧版 handle 依赖的万能头（pandas/matplotlib/docx 等）
from structured_support import as_number, copied_tables, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data
from optics_common import (
    OpticsInputError,
    add_key_values,
    add_summary,
    add_table,
    configure_plotting,
    create_document,
    error_result,
    finish_report,
    get_parameter,
    get_rows,
    numeric_column,
    save_figure,
)


def name():  # 返回实验名称
    return "直流电源特性"


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def handle(workpath, extension):
    """旧版 CSV 单表接口：读取 R/U_DC/U_AC → 画 P-R、Ku-R 曲线 → Word。"""
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf")

        excelpath = workpath + name() + '.' + extension

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, names=["R", "U_DC", "U_AC"], encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0, names=["R", "U_DC", "U_AC"])

        os.remove(excelpath)

        data["P"] = data["U_DC"] * data["U_DC"] / data["R"] * 1000
        data["K"] = data["U_AC"] / data["U_DC"] * 100

        fig, ax = plt.subplots()
        ax.plot(data["R"], data["P"], "o", color='r', markersize=3)
        ax.plot(data["R"], data["P"], color='b', linewidth=1.5)
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.set_title("输出功率和负载 $P$–$R$ 曲线", fontproperties=zhfont)
        ax.set_xlabel(r"Load Resistance ($\Omega$)")
        ax.set_ylabel("Output Power (mW)")
        imgpath_P = workpath + "Power.jpg"
        fig.savefig(imgpath_P, dpi=300, bbox_inches='tight')
        plt.close()

        fig, ax = plt.subplots()
        ax.plot(data["R"], data["K"], "o", color='r', markersize=3)
        ax.plot(data["R"], data["K"], color='b', linewidth=1.5)
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.set_title("纹波系数和负载 $K$–$R$ 曲线", fontproperties=zhfont)
        ax.set_xlabel(r"Load Resistance ($\Omega$)")
        ax.set_ylabel("Ripple Factor (%)")
        imgpath_K = workpath + "ripple.jpg"
        fig.savefig(imgpath_K, dpi=300, bbox_inches='tight')
        plt.close()

        docu = Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【本文档不只有一页，请向下翻阅】")
        docu.add_paragraph()
        docu.add_paragraph("输出功率：")
        docu.add_picture(imgpath_P)
        docu.add_paragraph()
        docu.add_paragraph("纹波系数：")
        docu.add_picture(imgpath_K)

        docu.save(workpath + name() + ".docx")

        os.remove(imgpath_P)
        os.remove(imgpath_K)

        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 示例数据与基础计算工具
# ─────────────────────────────────────────────

# 10μF 示例数据的微小扰动（让纹波比值偏离理论值 10 一点点，更接近真实测量）
_TEN_UF_NOISE = [0.010, -0.015, 0.020, -0.010, 0.015, -0.020, 0.010, -0.015, 0.020, -0.010, 0.015, -0.020]

# 电表等级标准序列（引用误差向上靠拢）
_STANDARD_GRADES = (0.1, 0.2, 0.5, 1.0, 1.5, 2.5, 5.0)

# 半偏法测电流表内阻示例（E = 3 V、I_g = 100 μA、R_g ≈ 270 Ω：R1 ≈ 29.73 kΩ、R2 ≈ 59.73 kΩ）
_METER_SAMPLE = [[1, 29731, 59736], [2, 29728, 59722], [3, 29730, 59728]]

# 改装电表定标示例（2.00 V 量程，最大绝对误差 5 mV → 引用误差 0.25% → 0.5 级）
_CALIBRATION_SAMPLE = [
    [0.20, 0.198], [0.40, 0.403], [0.60, 0.599], [0.80, 0.804], [1.00, 1.000],
    [1.20, 1.202], [1.40, 1.396], [1.60, 1.601], [1.80, 1.805], [2.00, 1.997],
]


def _linear_fit(x_values: Any, y_values: Any) -> dict[str, Any]:
    """最小二乘线性拟合，返回斜率、截距、R²、斜率标准不确定度与回归标准差。

    斜率不确定度按相关系数法（与 exp46/exp48 一致），另返回 sy、sxx 等中间量。
    """
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    count = len(x)
    if count < 3:
        raise OpticsInputError("线性拟合至少需要 3 组数据")
    mean_x = float(x.mean())
    mean_y = float(y.mean())
    sxx = float(((x - mean_x) ** 2).sum())
    sxy = float(((x - mean_x) * (y - mean_y)).sum())
    syy = float(((y - mean_y) ** 2).sum())
    if sxx <= 0:
        raise OpticsInputError("拟合横坐标不能全部相同")
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = y - (slope * x + intercept)
    sse = float((residuals ** 2).sum())
    r_squared = 1.0 if syy <= 0 and sse <= 0 else (0.0 if syy <= 0 else 1.0 - sse / syy)
    correlation = 0.0 if syy <= 0 else sxy / math.sqrt(sxx * syy)
    slope_uncertainty = 0.0
    if count > 2 and abs(correlation) > 1e-15:
        slope_uncertainty = abs(slope) * math.sqrt(max(0.0, (1.0 / correlation ** 2 - 1.0) / (count - 2)))
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r_squared,
        "correlation": correlation,
        "slope_unc": slope_uncertainty,
        "sy": math.sqrt(sse / (count - 2)) if count > 2 else 0.0,
        "n": count,
        "x": x,
        "y": y,
        "mean_x": mean_x,
        "mean_y": mean_y,
        "sxx": sxx,
        "residuals": residuals,
    }


def _has_data(rows: Any, keys: tuple[str, ...]) -> bool:
    """判断表格是否有任何有效输入。"""
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if any(str(row.get(key, "")).strip() for key in keys):
            return True
    return False


def _cleaned_rows(rows: Any) -> list[dict[str, str]]:
    """过滤空行并把所有单元格转为字符串。"""
    return [
        {str(k): ("" if v is None else str(v).strip()) for k, v in row.items()}
        for row in rows or []
        if isinstance(row, dict) and any(str(v).strip() for v in row.values())
    ]


def _mean_std(values: Any) -> tuple[float, float, int]:
    """平均值与样本标准差（n−1），返回 (mean, std, n)。"""
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return mean, std, int(arr.size)


def _grade(percent: float) -> float:
    """引用误差百分比向上靠拢标准电表等级。"""
    for level in _STANDARD_GRADES:
        if level >= percent:
            return level
    return _STANDARD_GRADES[-1]


def _power_series(rows: Any) -> tuple[np.ndarray, np.ndarray]:
    """由行数据计算负载功率 P = U_DC²/R（mW），按 R 排序后返回 (r, power)。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 2:
        raise OpticsInputError("绘图至少需要 2 行有效数据")
    r = numeric_column(cleaned, "c0", "负载电阻")
    udc = numeric_column(cleaned, "c1", "直流电压")
    if np.any(r <= 0):
        raise OpticsInputError("负载电阻必须大于 0")
    power = udc ** 2 / r * 1000.0
    order = np.argsort(r)
    return r[order], power[order]


def _ripple_series(rows: Any) -> tuple[np.ndarray, np.ndarray]:
    """由行数据计算纹波系数 Ku = U_AC/U_DC（%），按 R 排序后返回 (r, ripple)。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 2:
        raise OpticsInputError("绘图至少需要 2 行有效数据")
    r = numeric_column(cleaned, "c0", "负载电阻")
    udc = numeric_column(cleaned, "c1", "直流电压")
    uac = numeric_column(cleaned, "c2", "交流电压")
    if np.any(udc == 0):
        raise OpticsInputError("直流电压不能为 0")
    ripple = uac / udc * 100.0
    order = np.argsort(r)
    return r[order], ripple[order]


# ─────────────────────────────────────────────
# 各表计算
# ─────────────────────────────────────────────

def _calc_power(rows: Any) -> tuple[list[str], list[str]]:
    """1μF 电路负载功率与纹波系数：最大功率点与 Ku 变化范围。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 3:
        raise OpticsInputError("负载特性表至少需要 3 行有效数据")
    r = numeric_column(cleaned, "c0", "负载电阻")
    udc = numeric_column(cleaned, "c1", "直流电压")
    uac = numeric_column(cleaned, "c2", "交流电压")
    if np.any(r <= 0):
        raise OpticsInputError("负载电阻必须大于 0")
    if np.any(udc == 0):
        raise OpticsInputError("直流电压不能为 0")
    power = udc ** 2 / r * 1000.0
    ripple = uac / udc * 100.0
    index_p = int(np.argmax(power))
    lines = [
        "共 {} 个测量点，负载范围 {:.0f} ~ {:.0f} Ω".format(len(r), float(r.min()), float(r.max())),
        "最大输出功率 P_max = {:.3f} mW，对应负载 R = {:.0f} Ω".format(float(power[index_p]), float(r[index_p])),
    ]
    warnings = []
    if index_p in (0, len(power) - 1):
        warnings.append("最大功率出现在测量区间边界，可扩大 RL 范围继续测量，以确认峰值位置。")
    else:
        lines.append("峰值负载 R ≈ {:.0f} Ω，由最大功率传输定理（R = r），对应电源内阻约为 {:.0f} Ω。".format(
            float(r[index_p]), float(r[index_p])))
    index_max_ku = int(np.argmax(ripple))
    index_min_ku = int(np.argmin(ripple))
    lines.append("纹波系数 Ku 从 {:.2f}%（R = {:.0f} Ω）降至 {:.2f}%（R = {:.0f} Ω），随负载电阻增大而减小。".format(
        float(ripple[index_max_ku]), float(r[index_max_ku]),
        float(ripple[index_min_ku]), float(r[index_min_ku])))
    if float(ripple[index_max_ku]) > 50:
        warnings.append("低阻端纹波系数超过 50%，滤波效果差，请检查滤波电容是否接入电路。")
    return lines, warnings


def _calc_ripple_compare(rows_1uf: Any, rows_10uf: Any) -> tuple[list[str], list[str]]:
    """1μF 与 10μF 纹波系数逐点对比（小纹波近似下比值应接近 C₂/C₁ = 10）。"""
    def by_r(rows):
        cleaned = _cleaned_rows(rows)
        if len(cleaned) < 3:
            raise OpticsInputError("至少需要 3 行有效数据")
        r = numeric_column(cleaned, "c0", "负载电阻")
        udc = numeric_column(cleaned, "c1", "直流电压")
        uac = numeric_column(cleaned, "c2", "交流电压")
        if np.any(udc == 0):
            raise OpticsInputError("直流电压不能为 0")
        return {round(float(ri), 6): float(ui / di * 100.0) for ri, di, ui in zip(r, udc, uac)}

    ku1 = by_r(rows_1uf)
    ku2 = by_r(rows_10uf)
    pairs = [(r_value, ku1[r_value], ku2[r_value]) for r_value in sorted(ku1) if r_value in ku2]
    if len(pairs) < 3:
        raise OpticsInputError("两表至少需要 3 个相同负载电阻值才能对比")
    ratios = [k1 / k2 for _, k1, k2 in pairs]
    high_ratios = [k1 / k2 for r_value, k1, k2 in pairs if r_value >= 300]
    mean_ratio = sum(ratios) / len(ratios)
    mean_high = sum(high_ratios) / len(high_ratios) if high_ratios else None
    lines = [
        "在 {} 个相同负载电阻点上比较：Ku(1μF)/Ku(10μF) 平均比值 {:.2f} 倍".format(len(pairs), mean_ratio),
    ]
    if mean_high is not None:
        lines.append("中高阻段（R ≥ 300 Ω）平均比值 {:.2f} 倍，理论（小纹波近似）比值 ≈ C₂/C₁ = 10".format(mean_high))
    lines.append("结论：10μF 电容滤波的纹波系数约为 1μF 电路的 1/{:.1f}，滤波效果显著更好。".format(mean_ratio))
    lines.append("注意：1μF 为 π 型滤波（两级电容），10μF 为单电容全波整流滤波，两者电路结构不同，改善同时来自电容容量的增大。")
    warnings = []
    if max(k1 for _, k1, _ in pairs) > 30:
        warnings.append("1μF 电路低阻端纹波系数超过 30%，已超出小纹波近似适用范围，该段比值偏大属正常现象。")
    if mean_high is not None and mean_high < 7:
        warnings.append("10μF 电路纹波改善不明显（比值小于 7），请检查 10μF 电容是否真正接入电路。")
    return lines, warnings


def _calc_oc_sc(rows: Any, rs: float) -> tuple[list[str], list[str]]:
    """补偿法开路电压 + 取样电阻法短路电流 → 电源内阻 r = E/I_sc。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 3:
        raise OpticsInputError("至少需要 3 行有效数据")
    e = numeric_column(cleaned, "c1", "开路电压")
    us = numeric_column(cleaned, "c2", "取样电压")
    if rs <= 0:
        raise OpticsInputError("取样电阻 Rs 必须大于 0")
    isc = us / rs
    mean_e, std_e, count = _mean_std(e)
    mean_i, std_i, _ = _mean_std(isc)
    if mean_e == 0:
        raise OpticsInputError("开路电压为 0，请检查补偿法测量")
    if mean_i <= 0:
        raise OpticsInputError("短路电流计算值为 0，请检查取样电压读数")
    u_e = std_e / math.sqrt(count)
    u_i = std_i / math.sqrt(count)
    r_int = mean_e / (mean_i / 1000.0)
    u_r = r_int * math.sqrt((u_e / mean_e) ** 2 + (u_i / mean_i) ** 2)
    lines = [
        "开路电压 E = {:.4f} ± {:.2g} V（{} 次测量平均）".format(mean_e, u_e, count),
        "短路电流 I_sc = {:.2f} ± {:.2g} mA（I_sc = U_s/Rs）".format(mean_i, u_i),
        "电源内阻 r = E/I_sc = {:.2f} ± {:.2g} Ω".format(r_int, u_r),
    ]
    warnings = []
    if std_e / mean_e > 0.02:
        warnings.append("开路电压读数波动超过 2%，请检查补偿法检零判断的准确性。")
    if std_i / mean_i > 0.02:
        warnings.append("短路电流读数波动超过 2%，请检查取样电阻阻值与电压表档位。")
    return lines, warnings


def _calc_meter(rows: Any, ig_ua: float, u_target: float) -> tuple[list[str], list[str]]:
    """半偏法电流表内阻 R_g = R2 − 2R1，并计算改装电压表串联电阻。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 2:
        raise OpticsInputError("半偏法至少需要 2 行有效数据")
    r1 = numeric_column(cleaned, "c1", "满偏电阻箱阻值")
    r2 = numeric_column(cleaned, "c2", "半偏电阻箱阻值")
    if ig_ua <= 0:
        raise OpticsInputError("电流表量程 I_g 必须大于 0")
    if u_target <= 0:
        raise OpticsInputError("改装电压表量程必须大于 0")
    rg = r2 - 2.0 * r1
    mean_rg, std_rg, count = _mean_std(rg)
    u_rg = std_rg / math.sqrt(count)
    r_ser = u_target / (ig_ua * 1e-6) - mean_rg
    lines = [
        "各次测量电流表内阻：{} Ω".format("、".join("{:.1f}".format(v) for v in rg)),
        "电流表内阻 R_g = {:.1f} ± {:.2g} Ω（{} 次测量平均）".format(mean_rg, u_rg, count),
        "改装成 {:.2f} V 电压表需串联电阻 R_ser = U/I_g − R_g = {:.0f} Ω".format(u_target, r_ser),
    ]
    warnings = []
    if np.any(rg <= 0):
        warnings.append("半偏法数据异常（R_g ≤ 0），请检查 R_g = R2 − 2R1 的读数关系。")
    elif abs(mean_rg) > 0 and std_rg / abs(mean_rg) > 0.10:
        warnings.append("各次 R_g 离散超过 10%，请检查电阻箱读数。")
    if r_ser <= 0:
        warnings.append("测得内阻超过 U/I_g，无法改装成该量程电压表，请检查数据。")
    return lines, warnings


def _calc_calibration(rows: Any, u_target: float) -> tuple[list[str], list[str]]:
    """改装电表定标：线性拟合 U_m = k·U_std + b，由最大绝对误差定电表等级。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 3:
        raise OpticsInputError("定标表至少需要 3 行有效数据")
    u_std = numeric_column(cleaned, "c0", "标准电压")
    u_m = numeric_column(cleaned, "c1", "改装表读数")
    fit = _linear_fit(u_std, u_m)
    errors = u_m - u_std
    index = int(np.argmax(np.abs(errors)))
    pct = abs(float(errors[index])) / u_target * 100.0
    grade = _grade(pct)
    lines = [
        "定标拟合：U_m = {:.4f}·U_std + {:.4f}，R² = {:.5f}".format(fit["slope"], fit["intercept"], fit["r2"]),
        "最大绝对误差 |ΔU|_max = {:.4g} V（U_std = {:.3g} V）".format(abs(float(errors[index])), float(u_std[index])),
        "满量程引用误差 = {:.3f}% → 该改装表定级为 {:.1f} 级".format(pct, grade),
    ]
    warnings = []
    if abs(fit["slope"] - 1.0) > 0.02:
        warnings.append("定标曲线斜率 k = {:.4f} 明显偏离 1，改装表存在系统偏差，请检查串联电阻阻值。".format(fit["slope"]))
    if abs(fit["intercept"]) > 0.01 * u_target:
        warnings.append("定标曲线截距 b = {:.4f} V 偏大，请检查表头机械零点。".format(fit["intercept"]))
    if pct >= 2.5:
        warnings.append("改装表引用误差偏大（≥ 2.5 级），请检查改装电路与元件数值。")
    return lines, warnings


def _run_calculations(tables: dict[str, Any], parameters: dict[str, Any]):
    """执行全部计算，返回 (calc_results, calc_messages)。"""
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    rs = as_number(parameters.get("rs")) or 1.0
    ig_ua = as_number(parameters.get("ig")) or 100.0
    u_target = as_number(parameters.get("u_target")) or 2.0

    rows1 = tables.get("table1") or []
    rows2 = tables.get("table2") or []
    if _has_data(rows1, ("c0", "c1", "c2")):
        try:
            lines, warnings = _calc_power(rows1)
            calc_results["table1"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))
    if _has_data(rows2, ("c0", "c1", "c2")):
        try:
            if "table1" not in calc_results:
                raise OpticsInputError("对比纹波系数需要先填写 1μF 电路表")
            lines, warnings = _calc_ripple_compare(rows1, rows2)
            calc_results["table2"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))

    if _has_data(tables.get("table3") or [], ("c1", "c2")):
        try:
            lines, warnings = _calc_oc_sc(tables["table3"], rs)
            calc_results["table3"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))

    if _has_data(tables.get("table4") or [], ("c1", "c2")):
        try:
            lines, warnings = _calc_meter(tables["table4"], ig_ua, u_target)
            calc_results["table4"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))

    if _has_data(tables.get("table5") or [], ("c0", "c1")):
        try:
            lines, warnings = _calc_calibration(tables["table5"], u_target)
            calc_results["table5"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))

    return calc_results, calc_messages


def _enrich_tables(tables: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    """逐行补齐派生列（只读列）：P、Ku、I_sc、R_g、ΔU 与相对误差。"""
    rs = as_number(parameters.get("rs")) or 1.0

    for table_id in ("table1", "table2"):
        for row in tables.get(table_id, []):
            r = as_number(row.get("c0"))
            udc = as_number(row.get("c1"))
            uac = as_number(row.get("c2"))
            row["c3"] = "{:.3f}".format(udc * udc / r * 1000) if (r and udc is not None) else ""
            row["c4"] = "{:.2f}".format(uac / udc * 100) if (udc and uac is not None) else ""

    for row in tables.get("table3", []):
        us = as_number(row.get("c2"))
        row["c3"] = "{:.3f}".format(us / rs) if us is not None else ""

    for row in tables.get("table4", []):
        r1 = as_number(row.get("c1"))
        r2 = as_number(row.get("c2"))
        row["c3"] = "{:.1f}".format(r2 - 2 * r1) if (r1 is not None and r2 is not None) else ""

    for row in tables.get("table5", []):
        u_std = as_number(row.get("c0"))
        u_m = as_number(row.get("c1"))
        row["c2"] = "{:.4f}".format(u_m - u_std) if (u_m is not None and u_std is not None) else ""
        row["c3"] = "{:.2f}".format((u_m - u_std) / u_std * 100) if (u_m is not None and u_std) else ""

    return tables


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────

def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：输出功率、纹波系数、短路电流、表头内阻、定标误差。"""
    tables = _enrich_tables(copied_tables(payload), payload.get("parameters") or {})
    calc_results, calc_messages = _run_calculations(tables, payload.get("parameters") or {})
    return {"tables": tables, "calc_results": calc_results, "calc_messages": calc_messages}


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """结构化接口：计算功率/纹波/内阻/改装/定标，生成对比图表与 Word 文档。"""
    try:
        tables = _enrich_tables(copied_tables(payload), payload.get("parameters") or {})
        parameters = payload.get("parameters") or {}
        rs = get_parameter(payload, "rs", 1.0, False, cast=float)
        ig_ua = get_parameter(payload, "ig", 100.0, False, cast=float)
        u_target = get_parameter(payload, "u_target", 2.0, False, cast=float)

        # 基础内容两表必做：指导书要求 10~12 个测量点
        get_rows(payload, "table1", required=True, min_rows=10)
        get_rows(payload, "table2", required=True, min_rows=10)

        calc_results, calc_messages = _run_calculations(tables, parameters)
        required_ids = {"table1", "table2"}
        incomplete = sorted(required_ids - set(calc_results))
        if incomplete:
            calc_messages.append("表格“{}”数据不足或无效".format("、".join(incomplete)))
        if calc_messages:
            return {"code": 1, "message": "；".join(calc_messages)}

        power1 = _power_series(tables["table1"])
        power2 = _power_series(tables["table2"])
        ripple1 = _ripple_series(tables["table1"])
        ripple2 = _ripple_series(tables["table2"])

        # ── 图表 ──（先配置中文字体再创建 Figure，否则中文会回退成方框）
        configure_plotting()
        charts = []

        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        ax.plot(power1[0], power1[1], "o-", markersize=4.5, color="#4472C4", label="1μF π型滤波")
        ax.plot(power2[0], power2[1], "s--", markersize=4.5, color="#2ECC71", label="10μF 全波整流")
        index_p = int(np.argmax(power1[1]))
        ax.plot(power1[0][index_p], power1[1][index_p], "*", markersize=14, color="#E67E22")
        ax.annotate("最大功率 {:.2f} mW\nR = {:.0f} Ω".format(power1[1][index_p], power1[0][index_p]),
                    xy=(power1[0][index_p], power1[1][index_p]),
                    xytext=(0.52, 0.22), textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#E67E22"))
        ax.set_xlabel("负载电阻 R / Ω")
        ax.set_ylabel("输出功率 P / mW")
        ax.set_title("负载功率曲线 P-R")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp14_power.png")
        charts.append({"filename": filename, "title": "负载功率曲线（1μF 与 10μF 对比）"})

        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        for (r, ku, label, color, marker) in (
                (ripple1[0], ripple1[1], "1μF π型滤波", "#4472C4", "o"),
                (ripple2[0], ripple2[1], "10μF 全波整流", "#2ECC71", "s")):
            ax.semilogx(r, ku, marker, markersize=4.5, label=label, color=color)
            try:
                fit = _linear_fit(1.0 / r, ku)
                grid = np.linspace(r[0], r[-1], 80)
                ax.semilogx(grid, fit["intercept"] + fit["slope"] / grid, "--",
                            linewidth=1.2, color=color, alpha=0.8)
            except OpticsInputError:
                pass  # 数据不支持反比模型曲线时只画测量点
        ax.set_xlabel("负载电阻 R / Ω")
        ax.set_ylabel("纹波系数 Ku / %")
        ax.set_title("纹波系数曲线 Ku-R（对数横轴）")
        ax.legend()
        ax.grid(True, which="both", linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp14_ripple.png")
        charts.append({"filename": filename, "title": "纹波系数曲线（1μF 与 10μF 对比）"})

        if "table5" in calc_results:
            cleaned5 = _cleaned_rows(tables["table5"])
            u_std = numeric_column(cleaned5, "c0", "标准电压")
            u_m = numeric_column(cleaned5, "c1", "改装表读数")
            fit5 = _linear_fit(u_std, u_m)
            fig, ax = plt.subplots(figsize=(7.6, 4.6))
            ax.plot(u_std, u_m, "o", markersize=4.5, color="#9B59B6", label="测量点")
            grid = np.linspace(float(u_std.min()), float(u_std.max()), 50)
            ax.plot(grid, fit5["intercept"] + fit5["slope"] * grid, "-",
                    linewidth=1.4, color="#9B59B6", label="定标拟合")
            ax.plot(grid, grid, "--", linewidth=1.1, color="#B0B0B0", label="理想曲线 U_m = U_std")
            ax.set_xlabel("标准电压 U_std / V")
            ax.set_ylabel("改装表读数 U_m / V")
            ax.set_title("改装电压表定标曲线")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.35)
            filename = save_figure(fig, workpath, "exp14_calibration.png")
            charts.append({"filename": filename, "title": "改装电压表定标曲线"})

        # ── Word 文档 ──
        doc = create_document(name(), subtitle="负载功率与纹波系数 · 开路短路测定 · 电表改装与定标")
        add_key_values(doc, "实验参数", [
            ("取样电阻 Rs (Ω)", "{:.4g}".format(rs)),
            ("电流表量程 I_g (μA)", "{:.4g}".format(ig_ua)),
            ("改装电压表量程 U (V)", "{:.4g}".format(u_target)),
        ])

        for title, table_id, headers, cols in (
                ("表1  负载特性（1μF π型全波整流滤波）", "table1",
                 ["R/Ω", "U_DC/V", "U_AC/V", "P/mW", "Ku/%"],
                 ("c0", "c1", "c2", "c3", "c4")),
                ("表2  负载特性（10μF 全波整流滤波）", "table2",
                 ["R/Ω", "U_DC/V", "U_AC/V", "P/mW", "Ku/%"],
                 ("c0", "c1", "c2", "c3", "c4")),
                ("表3  开路电压与短路电流测定", "table3",
                 ["序号", "U_oc/V", "U_s/mV", "I_sc/mA"],
                 ("c0", "c1", "c2", "c3")),
                ("表4  半偏法测电流表内阻", "table4",
                 ["序号", "R1/Ω", "R2/Ω", "R_g/Ω"],
                 ("c0", "c1", "c2", "c3")),
                ("表5  改装电表定标", "table5",
                 ["U_std/V", "U_m/V", "ΔU/V", "相对误差/%"],
                 ("c0", "c1", "c2", "c3")),
        ):
            rows = tables.get(table_id) or []
            if not rows:
                continue
            table_rows = [[str(row.get(key, "")).strip() for key in cols]
                          for row in rows if isinstance(row, dict)]
            add_table(doc, title, headers, table_rows)

        summary: list[str] = []
        for table_id, label in (("table1", "负载功率与纹波系数（1μF）"),
                                ("table2", "电容对纹波系数的影响（10μF 对比）"),
                                ("table3", "开路电压与短路电流"),
                                ("table4", "电流表内阻与电压表改装"),
                                ("table5", "改装电表定标")):
            if table_id in calc_results:
                summary.append("【{}】".format(label))
                summary.extend(calc_results[table_id]["lines"])
        add_summary(doc, summary)

        warnings: list[str] = []
        for result in calc_results.values():
            warnings.extend(result.get("warnings", []))
        warnings = list(dict.fromkeys(warnings))

        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


# ─────────────────────────────────────────────
# 表结构与示例数据
# ─────────────────────────────────────────────

def _ten_uf_sample(sample1: list[list[Any]]) -> list[list[Any]]:
    """由 1μF 实测数据生成 10μF 示例：直流分量略升、交流分量约为 1/10。"""
    sample2 = []
    for index, row in enumerate(sample1):
        try:
            r, udc, uac = [float(value) for value in row[:3]]
        except (TypeError, ValueError, IndexError):
            continue
        udc2 = udc + 0.05 * (1.0 - udc / 2.0)  # 大电容放电更慢，直流分量略高
        uac2 = uac / 10.0 * (1.0 + _TEN_UF_NOISE[index % len(_TEN_UF_NOISE)])
        sample2.append([r, round(udc2, 4), round(uac2, 5)])
    return sample2


def schema():
    sample1 = load_sample_data("exp14", "直流电源特性")
    sample2 = _ten_uf_sample(sample1)

    table1 = make_table(
        "table1",
        "负载功率与纹波系数（1μF π型全波整流滤波）",
        ["负载电阻 R(Ω)", "直流电压 U_DC(V)", "交流电压 U_AC(V)",
         "输出功率 P(mW)", "纹波系数 Ku(%)"],
        sample=sample1,
        readonly=(3, 4),
        min_rows=10,
        initial_rows=12,
        description="信号源 500 Hz、Vp-p=10 V 正弦；电容 1μF；在面包板上连接 π 型全波整流滤波电路，"
                    "RL 电阻箱在 20~2000 Ω 范围内取 10~12 个点，分别用万用表直流、交流电压档测输出端电压，"
                    "计算输出功率 P 与纹波系数 Ku。",
        chart={"x_column": "c0", "y_column": "c3",
               "x_label": "负载电阻 R (Ω)", "y_label": "输出功率 P (mW)",
               "title": "负载功率曲线 P-R（1μF）"},
    )
    table1["calc"] = {"label": "计算功率与纹波系数"}

    table2 = make_table(
        "table2",
        "电容对纹波系数的影响（10μF 全波整流滤波）",
        ["负载电阻 R(Ω)", "直流电压 U_DC(V)", "交流电压 U_AC(V)",
         "输出功率 P(mW)", "纹波系数 Ku(%)"],
        sample=sample2,
        readonly=(3, 4),
        min_rows=10,
        initial_rows=12,
        description="改用单个 10μF 电容，连接全波整流滤波电路，重复上述测量，"
                    "与 1μF 结果比较，分析大电容滤波的优劣。",
        chart={"x_column": "c0", "y_column": "c4",
               "x_label": "负载电阻 R (Ω)", "y_label": "纹波系数 Ku (%)",
               "title": "纹波系数曲线 Ku-R（10μF）", "fit": "inverse"},
    )
    table2["calc"] = {"label": "对比 1μF 与 10μF 滤波效果"}

    table3 = make_table(
        "table3",
        "开路电压与短路电流的测定（等效电路/补偿法）",
        ["测量序号", "开路电压 U_oc(V)", "取样电阻电压 U_s(mV)", "短路电流 I_sc(mA)"],
        sample=[[1, 1.502, 143.2], [2, 1.498, 142.8], [3, 1.505, 144.1],
                [4, 1.500, 143.5], [5, 1.503, 143.9]],
        readonly=(3,),
        min_rows=3,
        initial_rows=5,
        required=False,
        description="非线性内阻电源不能直接用电压表/电流表测开路电压与短路电流"
                    "（电压表内阻有限、直接短路会损坏电源），采用等效电路（补偿法）测量。"
                    "开路电压用补偿法测得；短路电流用取样电阻 Rs 间接测得（I_sc = U_s/Rs），"
                    "再由 r = E/I_sc 求内阻。",
    )
    table3["calc"] = {"label": "计算电源内阻"}
    table3["enabled_by_default"] = True

    table4 = make_table(
        "table4",
        "电流表内阻测量（半偏法）",
        ["测量序号", "满偏电阻箱阻值 R1(Ω)", "半偏电阻箱阻值 R2(Ω)", "电流表内阻 R_g(Ω)"],
        sample=_METER_SAMPLE,
        readonly=(3,),
        min_rows=2,
        initial_rows=3,
        required=False,
        description="100μA 直流电流表与电阻箱串联接电源：调电阻箱 R1 使表头满偏，再调至 R2 使表头半偏，"
                    "由 R_g = R2 − 2R1 求内阻；改装成量程 U 的电压表需串联 R_ser = U/I_g − R_g。",
    )
    table4["calc"] = {"label": "计算内阻与改装电阻"}
    table4["enabled_by_default"] = True

    table5 = make_table(
        "table5",
        "改装电表的定标",
        ["标准电压 U_std(V)", "改装表读数 U_m(V)", "绝对误差 ΔU(V)", "相对误差 δ(%)"],
        sample=_CALIBRATION_SAMPLE,
        readonly=(2, 3),
        min_rows=5,
        initial_rows=10,
        required=False,
        description="将改装电压表与标准电压表并联，从小到大给定标准电压，记录两表读数，"
                    "计算绝对误差 ΔU = U_m − U_std，由最大绝对误差与量程之比定电表等级。",
        chart={"x_column": "c0", "y_column": "c1",
               "x_label": "标准电压 U_std (V)", "y_label": "改装表读数 U_m (V)",
               "title": "改装电表定标曲线", "fit": "linear"},
    )
    table5["calc"] = {"label": "定标与误差分析"}
    table5["enabled_by_default"] = True

    parameters = [
        {"id": "rs", "label": "取样电阻 Rs", "unit": "Ω", "type": "number",
         "default": "1", "min": 0, "step": "any", "required": False,
         "help": "短路电流间接测量用取样电阻：I_sc = U_s / Rs"},
        {"id": "ig", "label": "电流表量程 I_g", "unit": "μA", "type": "number",
         "default": "100", "min": 0, "step": "any", "required": False,
         "help": "待改装直流电流表的满偏电流（指导书为 100 μA）"},
        {"id": "u_target", "label": "改装电压表量程 U", "unit": "V", "type": "number",
         "default": "2.00", "min": 0, "step": "any", "required": False,
         "help": "改装目标量程（指导书为 2.00 V），串联电阻 R_ser = U/I_g − R_g"},
    ]

    theory = get_table_theory("exp14")
    global_theory = theory.get("_global", {})
    return make_schema(
        (
            "直流电源特性（B）：① 负载功率 " r"$P = U_{DC}^2/R$" " 与纹波系数 "
            r"$K_u = U_{AC}/U_{DC}$" " 曲线（1 μF π 型整流滤波，"
            r"$R_L = 20$" r"~$2000\,\Omega$" "，取 10~12 点）；② 换 10 μF 电容对比滤波优劣；"
            "③ 补偿法测开路电压、取样电阻法测短路电流，得内阻 " r"$r=E/I_{sc}$" "；"
            "④ 半偏法测表头内阻并改装为 2.00 V 电压表；⑤ 改装电表定标与误差分析。"
        ),
        [table1, table2, table3, table4, table5],
        parameters=parameters,
        parameters_sample={"rs": 1.0, "ig": 100, "u_target": 2.00},
        analysis_hints=(
            "P-R 曲线应存在最大输出功率点（最大功率传输定理 R = r），若最大值在区间边界应扩大 RL 继续测量；"
            "Ku 随 RL 增大而减小，10μF 大电容滤波的纹波应约为 1μF 的 1/10（小纹波近似，比值 ≈ C₂/C₁ = 10）；"
            "开路电压与短路电流由补偿法/取样电阻法测得，r = E/I_sc；"
            "半偏法要求 R_g = R2 − 2R1，改装电压表串联电阻 R_ser = U/I_g − R_g；"
            "定标曲线斜率应接近 1，电表等级按最大引用误差向上靠拢标准等级。"
        ),
        preview_enabled=True,
        formulas=global_theory.get("formulas", []),
        variables=global_theory.get("variables", []),
        table_theory=theory,
    )
