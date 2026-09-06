"""干涉法测微小量实验数据处理模块。

按指导书《干涉法测微小量》三部分内容：
一、用牛顿环测平凸透镜的曲率半径：
   十字叉丝竖丝依次与第 30、25、20、15、10、5 暗环两侧相切，记录读数显微镜
   位置读数 d30~d5、d'5~d'30；每组测完将牛顿环装置转过 120°，共 3 组。
   由 D_m = |d'_m − d_m| 求三组平均 D̄_m，用差值法
   R = (D²_{m+n} − D²_m)/(4nλ)（n = 15，三对 (5,20)、(10,25)、(15,30)）
   求平凸透镜的曲率半径 R，并以 D̄²–m 最小二乘拟合（斜率 = 4Rλ）交叉验证。
二、用劈尖的等厚干涉测细丝直径：
   在劈尖玻璃面三个不同部分测 20 条暗纹总长度 Δl（右、左端点读数之差）
   和劈尖两玻璃片交线处到夹细丝处的总长度 L，各 3 次，求平均值 Δl̄、L̄、
   单位长度干涉条纹数 n = 20/Δl̄，由 d = Nλ/2 = 10λL/Δl 求细丝直径。
三、用干涉条纹检查玻璃表面面形并作定性分析（无数据处理）。
实验指导说明"本实验不写实验报告"，故 report_enabled = False。

物理公式：
  光程差（含半波损失）： Δ = 2δ + λ/2
  暗环条件：            δ_m = mλ/2，r_m² = mRλ → D_m² = 4mRλ
  差值法：              R = (D²_{m+n} − D²_m)/(4nλ)
  劈尖暗纹：            d_m = mλ/2
  单位长度条纹数：      n = 20/Δl̄
  细丝直径：            d = Nλ/2 = 10λL/Δl
  光源：钠灯 λ = 589.3 nm

不确定度约定：
  读数显微镜仪器允差 0.01 mm、估读允差 0.005 mm，C = √3，P = 0.95。
  D_m、Δl、L 均为两次读数之差，B 类允差 = √2·√(0.01² + 0.005²) mm；
  D̄_m、Δl̄、L̄ 用 analyse()（A 类 = 多次测量的 σ/√n + B 类）得延伸不确定度；
  R_m、R̄、d 用 analyse_com 逐级误差传递。
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from head import *  # 旧版 handle 依赖的万能头（pandas/matplotlib/docx 等）
from structured_support import as_number, copied_tables, formatted, make_schema, make_table
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
    save_figure,
)


def name():  # 返回实验名称
    return "干涉法测微小量"


# 钠灯波长（nm）
_LAMBDA_NM = 589.3
# 读数显微镜允差（mm）：仪器允差、估读允差
_DELTA_INSTRUMENT = 0.01
_DELTA_ESTIMATE = 0.005
# 单次读数的 B 类允差（两允差源方和根）
_DELTA_READING = math.sqrt(_DELTA_INSTRUMENT ** 2 + _DELTA_ESTIMATE ** 2)
# D_m、Δl、L 是两次读数之差，B 类允差乘 √2
_DELTA_DIFFERENCE = math.sqrt(2.0) * _DELTA_READING
# 牛顿环表环序（第30圈→第5圈，与示例数据列序一致）
_RING_ORDERS = (30, 25, 20, 15, 10, 5)
# 差值法环序对（n = 15）
_PAIRS = ((5, 20), (10, 25), (15, 30))
_N_DIFF = 15
# 牛顿环测量组数（装置每转 120° 为一组）
_N_GROUPS = 3
# 劈尖表示例行标签
_WIRE_ITEM_LABELS = ("Δl（20 条暗纹总长度）", "L（交线到细丝总长度）")
# 细丝直径常见范围（μm）
_D_UM_RANGE = (40.0, 100.0)


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def handle(workpath, extension):
    """旧版单表入口（兼容 b_adapter 等旧调用路径）：牛顿环曲率半径部分。

    CSV 文件名与 name() 一致（"干涉法测微小量.csv"），列序为：
    组与方向标签 + 第30圈~第5圈读数（mm）。
    """
    try:
        excelpath = workpath + name() + '.' + extension
        column_names = ["name", "d30", "d25", "d20", "d15", "d10", "d5"]

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, names=column_names, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0, names=column_names)

        os.remove(excelpath)

        payload = {"parameters": {},
                   "tables": {"table1": _rows_from_legacy_frame(data),
                              "table2": []}}
        result = handle_structured(workpath, payload)
        return 0 if result.get("code") == 0 else 1
    except Exception:
        traceback.print_exc()  # 打印错误
        return 1  # 若失败，返回1


def _rows_from_legacy_frame(data):
    """把旧版 CSV 读出的 DataFrame（组/方向 × 第30~5圈读数）转成新版环序行。"""
    raw = []
    for _, record in data.iterrows():
        row = [str(record["name"]).strip() if pd.notna(record["name"]) else ""]
        for col in ("d30", "d25", "d20", "d15", "d10", "d5"):
            value = record[col]
            row.append("" if pd.isna(value) else str(value).strip())
        raw.append(row)
    sample = _ring_rows_from_matrix(raw)
    return [{"c%d" % j: cell for j, cell in enumerate(row)} for row in sample]


# ─────────────────────────────────────────────
# 示例数据转换与基础计算工具
# ─────────────────────────────────────────────
def _ring_rows_from_matrix(raw):
    """把 3 组 ×（右/左）行 × 6 环序列读数矩阵转成 6 个环序行（含派生列）。"""
    out = []
    for j, m in enumerate(_RING_ORDERS):
        row = [str(m)]
        values = []
        for g in range(_N_GROUPS):
            right = raw[2 * g][j + 1] if 2 * g < len(raw) and j + 1 < len(raw[2 * g]) else ""
            left = raw[2 * g + 1][j + 1] if 2 * g + 1 < len(raw) and j + 1 < len(raw[2 * g + 1]) else ""
            row.append(str(right).strip())
            row.append(str(left).strip())
            a, b = as_number(right), as_number(left)
            if a is not None and b is not None:
                values.append(abs(a - b))
        d_cells, mean_c, u_c, d2_c = _ring_derived(values)
        row.extend(d_cells)
        row.extend([mean_c, u_c, d2_c])
        out.append(row)
    return out


def _wire_rows_from_matrix(raw):
    """把 4 行（Δl 左/右、L 左/右）× 3 次读数矩阵转成 2 行（含派生列）。"""
    out = []
    for index, label in ((0, _WIRE_ITEM_LABELS[0]), (2, _WIRE_ITEM_LABELS[1])):
        row = [label]
        values = []
        for j in range(3):
            left = raw[index][j + 1] if index < len(raw) and j + 1 < len(raw[index]) else ""
            right = raw[index + 1][j + 1] if index + 1 < len(raw) and j + 1 < len(raw[index + 1]) else ""
            row.append(str(right).strip())
            row.append(str(left).strip())
            a, b = as_number(right), as_number(left)
            if a is not None and b is not None:
                values.append(abs(a - b))
        s_cells, mean_c, u_c = _wire_derived(values)
        row.extend(s_cells)
        row.extend([mean_c, u_c])
        out.append(row)
    return out


def _ring_derived(values):
    """牛顿环派生量：各组 D_m、平均 D̄_m、U(D̄_m)、D̄_m²（6 个单元格字符串）。"""
    d_cells = ["{:.3f}".format(v) for v in values[:3]]
    while len(d_cells) < 3:
        d_cells.append("")
    if not values:
        return d_cells, "", "", ""
    mean = sum(values) / len(values)
    u_cell = ""
    if len(values) >= 2:
        res = analyse(pd.Series(values), _DELTA_DIFFERENCE, 0.0, "D", "mm", confidence_C=3 ** 0.5)
        u_cell = formatted(res.unc, 3)
    return d_cells, "{:.3f}".format(mean), u_cell, "{:.2f}".format(mean * mean)


def _wire_derived(values):
    """劈尖派生量：三次差值、平均、U（5 个单元格字符串）。"""
    s_cells = ["{:.3f}".format(v) for v in values[:3]]
    while len(s_cells) < 3:
        s_cells.append("")
    if not values:
        return s_cells, "", ""
    mean = sum(values) / len(values)
    u_cell = ""
    if len(values) >= 2:
        res = analyse(pd.Series(values), _DELTA_DIFFERENCE, 0.0, "l", "mm", confidence_C=3 ** 0.5)
        u_cell = formatted(res.unc, 3)
    return s_cells, "{:.3f}".format(mean), u_cell


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


# ─────────────────────────────────────────────
# 各表计算
# ─────────────────────────────────────────────
def _calc_rings(rows: Any, lambda_nm: float) -> tuple[list[str], list[str]]:
    """牛顿环：各组 D_m、差值法曲率半径 R 与 D̄²–m 拟合交叉验证。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 3:
        raise OpticsInputError("牛顿环数据表至少需要 3 行（环序）有效数据")
    lambda_mm = float(lambda_nm) * 1e-6
    if lambda_mm <= 0:
        raise OpticsInputError("光源波长必须大于 0")

    warnings: list[str] = []
    rings: dict[float, list[float]] = {}  # 环序 m → 各组 D_m
    for index, row in enumerate(cleaned):
        m = as_number(row.get("c0"))
        if m is None:
            m = _RING_ORDERS[index] if index < len(_RING_ORDERS) else None
        values = []
        for g in range(_N_GROUPS):
            a = as_number(row.get("c%d" % (2 * g + 1)))
            b = as_number(row.get("c%d" % (2 * g + 2)))
            if a is not None and b is not None:
                values.append(abs(a - b))
        if m is None:
            warnings.append("第 {} 行缺少环序，该行已忽略。".format(index + 1))
            continue
        if m in rings:
            warnings.append("环序 {} 重复出现，仅保留第一行。".format(int(m)))
            continue
        if m <= 0:
            warnings.append("环序 {} 无效（应为正整数），该行已忽略。".format(int(m)))
            continue
        if values:
            rings[m] = values
    if not rings:
        raise OpticsInputError("牛顿环数据表需至少填写一组两侧读数，无法计算。")
    missing = sorted(set(_RING_ORDERS) - set(rings))
    if missing:
        warnings.append("缺少第 {} 圈的读数。".format("、".join(str(int(x)) for x in missing)))

    lines: list[str] = []
    dbar: dict[float, float] = {}
    ubar: dict[float, float] = {}
    for m in sorted(rings, reverse=True):
        values = rings[m]
        mean = sum(values) / len(values)
        dbar[m] = mean
        if len(values) >= 2:
            res = analyse(pd.Series(values), _DELTA_DIFFERENCE, 0.0, "D", "mm", confidence_C=3 ** 0.5)
            ubar[m] = float(res.unc)
            lines.append("第 {} 圈：D̄ = {} ± {} mm（{} 组测量）".format(
                int(m), formatted(mean, 3), formatted(ubar[m], 3), len(values)))
        else:
            lines.append("第 {} 圈：D̄ = {} mm（仅 1 组测量，无不确定度）".format(int(m), formatted(mean, 3)))
            warnings.append("第 {} 圈仅 1 组有效 D_m。".format(int(m)))

    # 差值法：三对环序（n = 15）
    pair_results: list[tuple[int, int, float, float]] = []
    for lo, hi in _PAIRS:
        if lo not in dbar or hi not in dbar or lo not in ubar or hi not in ubar:
            continue
        res = analyse_com(
            "R=(Db^2-Da^2)/(4*n*λ)",
            (("Da", dbar[lo], ubar[lo]), ("Db", dbar[hi], ubar[hi])),
            (("n", float(_N_DIFF)), ("λ", lambda_mm)), "mm")
        pair_results.append((lo, hi, float(res.ans), float(res.unc)))
        lines.append("差值法 R({},{}) = {} ± {} mm（n = {}）".format(
            lo, hi, formatted(float(res.ans), 0), formatted(float(res.unc), 0), _N_DIFF))
    if not pair_results:
        raise OpticsInputError("缺少完整的环序对（5,20）、（10,25）、（15,30），无法用差值法计算曲率半径。")

    if len(pair_results) == 1:
        r_mean, u_r = pair_results[0][2], pair_results[0][3]
    else:
        count = len(pair_results)
        expr = "Rm=(%s)/%d" % ("+".join("R_%d" % i for i in range(1, count + 1)), count)
        res_mean = analyse_com(
            expr,
            tuple(("R_%d" % idx, value, unc) for idx, (_, _, value, unc) in enumerate(pair_results, 1)),
            (), "mm")
        r_mean, u_r = float(res_mean.ans), float(res_mean.unc)
    lines.append("平均曲率半径 R̄ = {} ± {} mm（P = 0.95）".format(formatted(r_mean, 0), formatted(u_r, 0)))
    if len(pair_results) >= 2:
        spread = (max(v for _, _, v, _ in pair_results) - min(v for _, _, v, _ in pair_results)) / r_mean
        if spread > 0.05:
            warnings.append("三对差值法结果相对极差 {:.1f}%，超出 5%，请检查读数。".format(spread * 100))

    # 交叉验证：D̄²–m 最小二乘拟合（理论上 D̄_m² = 4Rλ·m，斜率 k = 4Rλ）
    if len(dbar) >= 3:
        m_arr = np.array(sorted(dbar), dtype=float)
        d2_arr = np.array([dbar[m] ** 2 for m in sorted(dbar)], dtype=float)
        try:
            fit = _linear_fit(m_arr, d2_arr)
            r_fit = fit["slope"] / (4.0 * lambda_mm)
            u_fit = fit["slope_unc"] / (4.0 * lambda_mm)
            deviation = (r_fit - r_mean) / r_mean * 100.0 if r_mean else 0.0
            lines.append("交叉验证：D̄²–m 拟合斜率 k = {} mm²（R² = {}），"
                         "R_fit = {} ± {} mm，与差值法偏差 {:+.1f}%".format(
                             formatted(fit["slope"], 4), formatted(fit["r2"], 5),
                             formatted(r_fit, 0), formatted(u_fit, 0), deviation))
            if abs(deviation) > 5:
                warnings.append("D̄²–m 拟合与差值法结果偏差 {:+.1f}%，超出 5%，请检查读数。".format(deviation))
        except OpticsInputError:
            warnings.append("有效环序不足 3 个，未作 D̄²–m 最小二乘交叉验证。")
    else:
        warnings.append("有效环序不足 3 个，未作 D̄²–m 最小二乘交叉验证。")
    return lines, warnings


def _calc_wire(rows: Any, lambda_nm: float, n_wire: float) -> tuple[list[str], list[str]]:
    """劈尖：Δl、L 的测量值与细丝直径 d = NλL/(2Δl) 及其不确定度。"""
    cleaned = _cleaned_rows(rows)
    if len(cleaned) < 2:
        raise OpticsInputError("劈尖数据表需 Δl、L 两行有效数据。")
    lambda_mm = float(lambda_nm) * 1e-6
    if lambda_mm <= 0:
        raise OpticsInputError("光源波长必须大于 0")
    if float(n_wire) <= 0:
        raise OpticsInputError("所数暗纹数 N 必须大于 0")

    spans: dict[str, list[float]] = {}
    for index, row in enumerate(cleaned):
        label = str(row.get("c0", ""))
        values = []
        for j in range(3):
            a = as_number(row.get("c%d" % (2 * j + 1)))
            b = as_number(row.get("c%d" % (2 * j + 2)))
            if a is not None and b is not None:
                values.append(abs(a - b))
        if "Δl" in label or "暗纹" in label or "条纹" in label:
            key = "dl"
        elif "细丝" in label or "交线" in label or ("L" in label and "Δl" not in label):
            key = "L"
        else:
            key = "dl" if index == 0 else "L"
        spans.setdefault(key, []).extend(values)
    dl_vals = spans.get("dl", [])
    L_vals = spans.get("L", [])
    if len(dl_vals) < 2 or len(L_vals) < 2:
        raise OpticsInputError("Δl 或 L 的有效测量不足 2 次，无法计算细丝直径。")

    res_dl = analyse(pd.Series(dl_vals), _DELTA_DIFFERENCE, 0.0, "Dl", "mm", confidence_C=3 ** 0.5)
    res_L = analyse(pd.Series(L_vals), _DELTA_DIFFERENCE, 0.0, "L", "mm", confidence_C=3 ** 0.5)
    dl_bar, L_bar = float(res_dl.average), float(res_L.average)
    if dl_bar <= 0:
        raise OpticsInputError("Δl̄ 必须大于 0。")
    n_line = float(n_wire) / dl_bar
    # 注意：sympy 解析表达式时 N 是内置函数名，条数变量改叫 nw
    res_d = analyse_com("d=nw*λ*L/(2*Dl)",
                        (("L", L_bar, float(res_L.unc)), ("Dl", dl_bar, float(res_dl.unc))),
                        (("λ", lambda_mm), ("nw", float(n_wire))), "mm")
    d_mm, u_d = float(res_d.ans), float(res_d.unc)
    lines = [
        "Δl 三次测量：{} mm，Δl̄ = {} ± {} mm".format(
            "、".join(formatted(v, 3) for v in dl_vals), formatted(dl_bar, 3), formatted(res_dl.unc, 3)),
        "L 三次测量：{} mm，L̄ = {} ± {} mm".format(
            "、".join(formatted(v, 3) for v in L_vals), formatted(L_bar, 3), formatted(res_L.unc, 3)),
        "单位长度干涉条纹数 n = {}/Δl̄ = {} 条/mm".format(formatted(n_wire, 0), formatted(n_line, 3)),
        "细丝直径 d = NλL̄/(2Δl̄) = {} ± {} mm = {} ± {} μm（P = 0.95）".format(
            formatted(d_mm, 4), formatted(u_d, 4), formatted(d_mm * 1000, 1), formatted(u_d * 1000, 1)),
    ]
    warnings: list[str] = []
    if L_bar < dl_bar:
        warnings.append("L̄ 小于 Δl̄，数据不合理：交线到细丝的距离应远大于 20 条暗纹的总长度，请检查读数。")
    d_um = d_mm * 1000
    if d_um < _D_UM_RANGE[0] or d_um > _D_UM_RANGE[1]:
        warnings.append("细丝直径 {} μm 超出常见范围 40~100 μm，请检查 Δl 与 L 的读数。".format(formatted(d_um, 1)))
    for label, values in (("Δl", dl_vals), ("L", L_vals)):
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
        if mean > 0 and std / mean > 0.10:
            warnings.append("{} 三次测量离散偏大（相对标准差 {:.1f}%），请检查读数。".format(label, std / mean * 100))
    return lines, warnings


def _run_calculations(tables: dict[str, Any], parameters: dict[str, Any]):
    """执行全部计算，返回 (calc_results, calc_messages)。"""
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    lambda_nm = as_number((parameters or {}).get("lambda_nm")) or _LAMBDA_NM
    n_wire = as_number((parameters or {}).get("n_wire")) or 20.0

    if _has_data(tables.get("table1") or [], ("c0", "c1", "c2", "c3", "c4", "c5", "c6")):
        try:
            lines, warnings = _calc_rings(tables["table1"], lambda_nm)
            calc_results["table1"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))
    if _has_data(tables.get("table2") or [], ("c0", "c1", "c2", "c3", "c4", "c5", "c6")):
        try:
            lines, warnings = _calc_wire(tables["table2"], lambda_nm, n_wire)
            calc_results["table2"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))
    return calc_results, calc_messages


def _enrich_tables(tables: dict[str, Any]) -> dict[str, Any]:
    """逐行补齐派生列（只读列）：各组 D_m、Δl/L 差值、平均、U、D̄_m²。"""
    for row in tables.get("table1", []):
        if not isinstance(row, dict):
            continue
        values = []
        for g in range(_N_GROUPS):
            a = as_number(row.get("c%d" % (2 * g + 1)))
            b = as_number(row.get("c%d" % (2 * g + 2)))
            if a is not None and b is not None:
                values.append(abs(a - b))
        d_cells, mean_c, u_c, d2_c = _ring_derived(values)
        row["c7"], row["c8"], row["c9"] = d_cells
        row["c10"], row["c11"], row["c12"] = mean_c, u_c, d2_c

    for row in tables.get("table2", []):
        if not isinstance(row, dict):
            continue
        values = []
        for j in range(3):
            a = as_number(row.get("c%d" % (2 * j + 1)))
            b = as_number(row.get("c%d" % (2 * j + 2)))
            if a is not None and b is not None:
                values.append(abs(a - b))
        s_cells, mean_c, u_c = _wire_derived(values)
        row["c7"], row["c8"], row["c9"] = s_cells
        row["c10"], row["c11"] = mean_c, u_c
    return tables


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：各组 D_m、Δl/L 差值、平均与不确定度、曲率半径与细丝直径。"""
    tables = _enrich_tables(copied_tables(payload))
    calc_results, calc_messages = _run_calculations(tables, payload.get("parameters") or {})
    return {"tables": tables, "calc_results": calc_results, "calc_messages": calc_messages}


def _ring_plot_series(rows: Any) -> tuple[np.ndarray, np.ndarray]:
    """从（已补派生列的）牛顿环表取 (m, D̄_m²) 散点序列。"""
    points = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        m = as_number(row.get("c0"))
        dbar = as_number(row.get("c10"))
        if m is not None and dbar is not None:
            points.append((m, dbar * dbar))
    points.sort()
    if len(points) < 2:
        raise OpticsInputError("有效环序不足 2 个，无法绘制 D̄²–m 图。")
    return (np.array([p[0] for p in points], dtype=float),
            np.array([p[1] for p in points], dtype=float))


def _add_ring_tables(doc, rows):
    """Word：原始读数表（组/方向 × 环序）与 D_m 汇总表。"""
    ordered = []
    for row in rows or []:
        if isinstance(row, dict) and as_number(row.get("c0")) is not None:
            ordered.append((as_number(row.get("c0")), row))
    ordered.sort(key=lambda item: -item[0])

    headers = ["组与方向"] + ["第{}圈/mm".format(int(m)) for m in _RING_ORDERS]
    raw_rows = []
    for g in range(_N_GROUPS):
        raw_rows.append(["第 {} 组（右）".format(g + 1)] +
                        [str(row.get("c%d" % (2 * g + 1), "")) for _, row in ordered])
        raw_rows.append(["第 {} 组（左）".format(g + 1)] +
                        [str(row.get("c%d" % (2 * g + 2), "")) for _, row in ordered])
    add_table(doc, "表1-1  牛顿环读数（D_m = |左读数 − 右读数|）", headers, raw_rows)
    add_table(doc, "表1-2  各组直径与平均",
              ["环序 m", "第1组D_m/mm", "第2组D_m/mm", "第3组D_m/mm",
               "D̄_m/mm", "U(D̄_m)/mm", "D̄_m²/mm²"],
              [[str(int(m))] + [str(row.get("c%d" % (7 + g), "")) for g in range(_N_GROUPS)] +
               [str(row.get("c10", "")), str(row.get("c11", "")), str(row.get("c12", ""))]
               for m, row in ordered])


def _add_wire_tables(doc, rows):
    """Word：劈尖原始读数表（端点 × 3 次）与差值汇总表。"""
    identified = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict):
            continue
        label = str(row.get("c0", ""))
        if "Δl" in label or "暗纹" in label or "条纹" in label:
            identified.append((_WIRE_ITEM_LABELS[0], row))
        elif "细丝" in label or "交线" in label or ("L" in label and "Δl" not in label):
            identified.append((_WIRE_ITEM_LABELS[1], row))
        elif index == 0:
            identified.append((_WIRE_ITEM_LABELS[0], row))
        else:
            identified.append((_WIRE_ITEM_LABELS[1], row))

    raw_rows = []
    for label, row in identified:
        raw_rows.append([label + " 右端点"] +
                        [str(row.get("c%d" % (2 * j + 1), "")) for j in range(3)])
        raw_rows.append([label + " 左端点"] +
                        [str(row.get("c%d" % (2 * j + 2), "")) for j in range(3)])
    add_table(doc, "表2-1  劈尖读数（Δ = |右端点 − 左端点|）",
              ["测量项", "第1次/mm", "第2次/mm", "第3次/mm"], raw_rows)
    add_table(doc, "表2-2  差值与平均",
              ["测量项", "第1次Δ/mm", "第2次Δ/mm", "第3次Δ/mm", "平均 Δ̄/mm", "U/mm"],
              [[label] + [str(row.get("c%d" % (7 + j), "")) for j in range(3)] +
               [str(row.get("c10", "")), str(row.get("c11", ""))]
               for label, row in identified])


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """结构化接口：牛顿环曲率半径 + 劈尖细丝直径计算、图表与 Word 文档。"""
    try:
        tables = _enrich_tables(copied_tables(payload))
        parameters = payload.get("parameters") or {}
        lambda_nm = get_parameter(payload, "lambda_nm", _LAMBDA_NM, False, cast=float)
        n_wire = get_parameter(payload, "n_wire", 20.0, False, cast=float)

        # 两表至少完成其一；有数据但行数不足时给出明确错误
        get_rows(payload, "table1", required=False, min_rows=6)
        get_rows(payload, "table2", required=False, min_rows=2)

        calc_results, calc_messages = _run_calculations(tables, parameters)
        if not calc_results:
            calc_messages.append("两个数据表均无有效数据，未进行任何计算。")
        if calc_messages:
            return {"code": 1, "message": "；".join(calc_messages)}

        # ── 图表 ──（先配置中文字体再创建 Figure，否则中文会回退成方框）
        configure_plotting()
        charts = []
        if "table1" in calc_results:
            m_arr, d2_arr = _ring_plot_series(tables["table1"])
            fig, ax = plt.subplots(figsize=(7.6, 4.6))
            ax.plot(m_arr, d2_arr, "o", markersize=5, color="#4472C4", label="测量数据")
            try:
                fit = _linear_fit(m_arr, d2_arr)
                grid = np.linspace(float(m_arr.min()), float(m_arr.max()), 60)
                ax.plot(grid, fit["intercept"] + fit["slope"] * grid, "-",
                        linewidth=1.4, color="#E74C3C", label="最小二乘拟合")
            except OpticsInputError:
                pass  # 有效环序不足 3 个时只画测量点
            ax.set_xlabel("环序 m")
            ax.set_ylabel(r"$\bar{D}_m^2$ / mm$^2$")
            ax.set_title(r"牛顿环 $\bar{D}^2$–m 关系（斜率 = 4Rλ）")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.35)
            filename = save_figure(fig, workpath, "exp19_d2_m.png")
            charts.append({"filename": filename, "title": "牛顿环 D̄²–m 关系与最小二乘拟合"})

        # ── Word 文档 ──
        doc = create_document(name(), subtitle="用牛顿环测平凸透镜曲率半径 · 用劈尖等厚干涉测细丝直径")
        add_key_values(doc, "实验参数", [
            ("光源波长 λ (nm)", "{:.4g}".format(lambda_nm)),
            ("劈尖所数暗纹数 N", "{:.4g}".format(n_wire)),
            ("读数显微镜仪器允差 (mm)", "{:.4g}".format(_DELTA_INSTRUMENT)),
            ("估读允差 (mm)", "{:.4g}".format(_DELTA_ESTIMATE)),
            ("置信概率 P", "0.95（C = √3）"),
        ])
        if "table1" in calc_results:
            _add_ring_tables(doc, tables["table1"])
        else:
            doc.add_heading("用牛顿环测平凸透镜的曲率半径", level=1)
            doc.add_paragraph("未填写牛顿环数据。")
        if "table2" in calc_results:
            _add_wire_tables(doc, tables["table2"])
        else:
            doc.add_heading("用劈尖的等厚干涉测细丝直径", level=1)
            doc.add_paragraph("未填写劈尖数据。")

        summary: list[str] = []
        for table_id, label in (("table1", "用牛顿环测平凸透镜的曲率半径"),
                                ("table2", "用劈尖的等厚干涉测细丝直径")):
            if table_id in calc_results:
                summary.append("【{}】".format(label))
                summary.extend(calc_results[table_id]["lines"])
        add_summary(doc, summary)

        doc.add_heading("用干涉条纹检查玻璃表面面形（定性分析）", level=1)
        doc.add_paragraph("将平面平晶放在被测表面上，在单色光垂直照射下观察等厚干涉条纹：")
        doc.add_paragraph("（1）若条纹为等距离的平行直条纹，被测表面是精确的平面；"
                          "若条纹弯向膜层较薄的 A 端，说明被测表面中心沿 AB 方向有一柱面形凹痕"
                          "（凹痕处空气膜较其两侧厚）。")
        doc.add_paragraph("（2）若呈同心圆环状条纹，用手指在平晶上表面中心部位轻轻一按："
                          "圆环向中心收缩则为凹面，从中心向边缘扩散则为凸面"
                          "（按下后空气膜变薄，各级条纹移动以满足 δ_m = mλ/2）。")

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
def schema():
    rings_raw = load_sample_data("exp19", "干涉法测微小量（测曲率半径）")
    wire_raw = load_sample_data("exp19", "干涉法测微小量（测头发丝直径）")

    table1 = make_table(
        "table1",
        "牛顿环直径测量数据表",
        ["环序 m", "第1组右 d′/mm", "第1组左 d/mm", "第2组右 d′/mm", "第2组左 d/mm",
         "第3组右 d′/mm", "第3组左 d/mm", "第1组D_m/mm", "第2组D_m/mm", "第3组D_m/mm",
         "D̄_m/mm", "U(D̄_m)/mm", "D̄_m²/mm²"],
        sample=_ring_rows_from_matrix(rings_raw),
        readonly=(7, 8, 9, 10, 11, 12),
        min_rows=6,
        initial_rows=6,
        description="每行对应一个暗环（环序 m 按 30、25、20、15、10、5 排列），"
                    "填写十字叉丝竖丝与该暗环两侧相切时读数显微镜的位置读数；"
                    "每组测量记录右、左两侧读数，每组测完将牛顿环装置转过 120°，共 3 组。"
                    "系统自动计算各组 D_m = |左读数 − 右读数|、平均 D̄_m、不确定度 U(D̄_m) 与 D̄_m²，"
                    "并用差值法求平凸透镜曲率半径 R。",
        chart={"x_column": "c0", "y_column": "c12",
               "x_label": "环序 m", "y_label": "D̄_m² (mm²)",
               "title": "牛顿环 D̄²–m 关系（理论 D̄_m² = 4Rλ·m）", "fit": "linear"},
    )
    table1["calc"] = {"label": "计算曲率半径 R"}

    table2 = make_table(
        "table2",
        "劈尖干涉测量数据表",
        ["测量项", "第1次右 l′/mm", "第1次左 l/mm", "第2次右 l′/mm", "第2次左 l/mm",
         "第3次右 l′/mm", "第3次左 l/mm", "第1次Δ/mm", "第2次Δ/mm", "第3次Δ/mm",
         "平均 Δ̄/mm", "U/mm"],
        sample=_wire_rows_from_matrix(wire_raw),
        readonly=(7, 8, 9, 10, 11),
        text_columns=(0,),
        min_rows=2,
        initial_rows=2,
        description="两行分别对应 Δl（20 条暗纹总长度）与 L（劈尖交线到细丝的总长度），"
                    "各填写 3 次测量的右、左端点读数；系统自动计算差值 Δ = |右端点 − 左端点|、"
                    "平均值与不确定度，并由 d = NλL/(2Δl) 求细丝直径。",
    )
    table2["calc"] = {"label": "计算细丝直径 d"}

    parameters = [
        {"id": "lambda_nm", "label": "光源波长 λ", "unit": "nm", "type": "number",
         "default": "589.3", "min": 0, "step": "any", "required": False,
         "help": "钠灯黄光平均波长，指导书取 589.3 nm"},
        {"id": "n_wire", "label": "劈尖所数暗纹数 N", "unit": "条", "type": "number",
         "default": "20", "min": 1, "step": "any", "required": False,
         "help": "劈尖测量中所数的暗纹条数（指导书为 20 条），细丝直径 d = NλL/(2Δl)"},
    ]

    theory = get_table_theory("exp19")
    global_theory = theory.get("_global", {})
    return make_schema(
        (
            "干涉法测微小量：\n① 牛顿环测曲率半径——十字叉丝依次与第 30、25、20、15、10、5 暗环"
            "两侧相切记录位置（每组转 120°，共 3 组），由  " r"$D_m = |d'_m - d_m|$ " " 求各环直径，"
            "用差值法  " r"$R = \frac{D^2_{m+n} - D^2_m}{4n\lambda}$" 
            r"（$n = 15$" "，取  (5,20) 、 (10,25) 、 (15,30) 三对）求 " r"$R$" "，并以 "
            r"$\bar{D}^2$" r"–$m$" " 最小二乘拟合验证；\n② 劈尖干涉测细丝直径——在劈尖三个部位"
            "测 20 条暗纹总长度 " r"$\Delta l$" " 与交线到细丝的距离 " r"$L$" "（各 3 次），由 "
            r"$d = 10\lambda L/\Delta l$" " 求细丝直径；\n③ 用干涉条纹定性检查玻璃面形（无数据处理）。"
            "光源为钠灯（" r"$\lambda = 589.3$" " nm）。"
        ),
        [table1, table2],
        parameters=parameters,
        parameters_sample={"lambda_nm": 589.3, "n_wire": 20},
        analysis_hints=(
            "D_m 应随环序 m 增大而增大（D_m² = 4mRλ，D̄²–m 图应近似为过原点的直线）；"
            "同一环三组 D_m 应接近，中心附近小环的读数离散偏大属正常现象；"
            "差值法三对 (5,20)、(10,25)、(15,30) 的 R 应接近（相对极差 < 5%），"
            "并与 D̄²–m 拟合斜率（k = 4Rλ）交叉验证一致；平凸透镜曲率半径常见约 1~2 m；"
            "细丝直径 d 常见 40~100 μm，L̄ 应远大于 Δl̄。"
        ),
        preview_enabled=True,
        report_enabled=False,
        formulas=global_theory.get("formulas", []),
        variables=global_theory.get("variables", []),
        table_theory=theory,
    )
