"""传感器实验数据处理模块。

按指导书《传感器（实验指导）》两部分内容：
一、电应变片传感器
1. 应变片受力情况研究（双弯曲悬梁上四个应变片的拉伸/压缩记录）；
2. 单臂/半桥/全桥电桥输出特性：U-m 最小二乘拟合求灵敏度 S = ΔU/Δm，
   三种电桥灵敏度之比应与理论 1:2:4 相符；
3. 全桥标定作电子秤，测待测物质量 m_x = (U′ - b)/S。
二、压阻传感器
1. 元器件检测记录（传感器、继电器、蜂鸣器、LED、二极管/三极管导通电压）；
2. 正压、负压输出特性 U-P 拟合，求正/负压灵敏度并对比；
3. 报警系统工作气压记录。

指导书要求不交完整报告，只需基本数据处理，故 report_enabled=False，
但仍提供实时预计算、图表和 Word 处理结果文档。
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from structured_support import as_number, copied_tables, make_schema, make_table
from theory_content import get_table_theory
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

# ── 常数与示例数据 ──
_MASSES = list(range(0, 201, 20))  # 依次增加砝码：0~200 g，步长 20 g
_PRESSURE_POS = list(range(0, 101, 10))
_PRESSURE_NEG = list(range(0, -81, -10))


def _noisy_bridge(slope, intercept, noises):
    """生成带小噪声的电桥标定示例数据：[[m, U], ...]。"""
    return [
        [mass, round(slope * mass + intercept + noise, 3)]
        for mass, noise in zip(_MASSES, noises)
    ]


_QUARTER_NOISE = [0.008, -0.035, 0.022, -0.015, 0.040, -0.028, 0.012, -0.038, 0.030, -0.020, 0.034]
_HALF_NOISE = [-0.015, 0.030, -0.040, 0.020, -0.010, 0.035, -0.025, 0.014, -0.030, 0.040, -0.018]
_FULL_NOISE = [0.028, -0.020, 0.046, -0.033, 0.016, -0.042, 0.030, -0.014, 0.036, -0.026, 0.020]
_POS_NOISE = [0.004, -0.026, 0.016, -0.010, 0.030, -0.020, 0.013, -0.032, 0.022, -0.007, 0.019]
_NEG_NOISE = [-0.006, 0.020, -0.029, 0.010, -0.023, 0.032, -0.013, 0.026, -0.036, 0.016, -0.019]


def name():
    return "传感器实验"


# ──────────────────────────────────────────────
# 基础计算工具
# ──────────────────────────────────────────────

def _linear_fit(x_values: Any, y_values: Any) -> dict[str, Any]:
    """最小二乘线性拟合，返回斜率、截距、R²、斜率标准不确定度与回归标准差。

    斜率不确定度按相关系数法（与 exp46 一致），另返回 sy、sxx 用于
    标定反推（待测物质量）的预测区间估计。
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


def _xy_fit(rows: Any, x_key: str, y_key: str, x_label: str, y_label: str,
            min_rows: int = 3) -> dict[str, Any]:
    """从行数据提取两列数值并做最小二乘拟合。"""
    cleaned = [
        {str(k): ("" if v is None else str(v).strip()) for k, v in row.items()}
        for row in rows or []
        if isinstance(row, dict) and any(str(v).strip() for v in row.values())
    ]
    if len(cleaned) < min_rows:
        raise OpticsInputError("至少需要 {} 行有效数据".format(min_rows))
    x = numeric_column(cleaned, x_key, x_label)
    y = numeric_column(cleaned, y_key, y_label)
    return _linear_fit(x, y)


# ──────────────────────────────────────────────
# 各表计算
# ──────────────────────────────────────────────

def _calc_bridge(fit: dict[str, Any], label: str, supply_v: float | None,
                 theory_fraction: int) -> tuple[list[str], list[str]]:
    """电桥标定结果：灵敏度、拟合质量、理论灵敏度对照与零点检查。"""
    lines = [
        "{}拟合：U = {:.4f} + {:.4f}·m（m/g，U/mV），R² = {:.5f}".format(
            label, fit["intercept"], fit["slope"], fit["r2"]),
        "{}灵敏度 S = {:.4f} ± {:.4g} mV/g".format(label, fit["slope"], fit["slope_unc"]),
    ]
    warnings = []
    if supply_v is not None:
        if theory_fraction == 1:
            lines.append("理论电桥灵敏度（每单位 ΔR/R）：S_th = U₀ = {:.4f} V".format(supply_v))
        else:
            lines.append("理论电桥灵敏度（每单位 ΔR/R）：S_th = U₀/{} = {:.4f} V".format(
                theory_fraction, supply_v / theory_fraction))
    span = float(np.abs(fit["y"]).max()) or 1.0
    if abs(fit["intercept"]) > 0.02 * span:
        warnings.append("{}电桥零点偏移明显（截距 b = {:.4f} mV），请检查电桥是否调零。".format(
            label, fit["intercept"]))
    if fit["r2"] < 0.995:
        warnings.append("{}拟合 R² = {:.4f} 偏低，请检查数据线性。".format(label, fit["r2"]))
    return lines, warnings


def _compare_bridges(fits: dict[str, dict[str, Any]],
                     supply_v: float | None) -> tuple[list[str], list[str]]:
    """三种电桥灵敏度之比与理论 1:2:4 对照。"""
    quarter, half, full = fits["quarter"], fits["half"], fits["full"]
    s1, s2, s3 = quarter["slope"], half["slope"], full["slope"]
    lines = []
    warnings = []
    for label, ratio, expect in (
            ("半桥/单臂", s2 / s1, 2.0),
            ("全桥/单臂", s3 / s1, 4.0)):
        deviation = abs(ratio - expect) / expect * 100
        lines.append("{}灵敏度之比 = {:.3f}（理论 {:.0f}），偏差 {:.2f}%".format(
            label, ratio, expect, deviation))
        if deviation > 10:
            warnings.append(
                "{}灵敏度之比与理论值偏差 {:.1f}%，请检查电桥连接（应变片是否接入正确桥臂）。".format(
                    label, deviation))
    if supply_v is not None:
        lines.append(
            "理论灵敏度（U₀ = {:.2f} V）：单臂 {:.3f}、半桥 {:.3f}、全桥 {:.3f} V（每单位 ΔR/R）".format(
                supply_v, supply_v / 4, supply_v / 2, supply_v))
    return lines, warnings


def _calc_unknown(rows: Any, full_fit: dict[str, Any],
                  ref_g: float | None) -> tuple[list[str], list[str]]:
    """用全桥标定反推待测物质量：m = (U′ − b)/S，附预测区间不确定度。"""
    lines = []
    warnings = []
    slope = full_fit["slope"]
    intercept = full_fit["intercept"]
    if abs(slope) < 1e-12:
        raise OpticsInputError("全桥标定灵敏度为零，无法反推待测物质量")
    for index, row in enumerate(rows or [], start=1):
        if not isinstance(row, dict) or not str(row.get("c1", "")).strip():
            continue
        sample_name = str(row.get("c0", "")).strip() or "待测物{}".format(index)
        try:
            u_prime = float(row.get("c1"))
        except (TypeError, ValueError) as exc:
            raise OpticsInputError("第 {} 行待测物输出电压不是有效数字".format(index)) from exc
        mass = (u_prime - intercept) / slope
        u_mass = (full_fit["sy"] / abs(slope)) * math.sqrt(
            1.0 + 1.0 / full_fit["n"]
            + (u_prime - full_fit["mean_y"]) ** 2 / (slope ** 2 * full_fit["sxx"]))
        text = "{}：U′ = {:.3f} mV，m_x = {:.2f} ± {:.2f} g".format(
            sample_name, u_prime, mass, u_mass)
        if ref_g is not None:
            text += "，标称 {:.1f} g，相对误差 {:.2f}%".format(
                ref_g, abs(mass - ref_g) / ref_g * 100)
        lines.append(text)
        if mass < float(full_fit["x"].min()) or mass > float(full_fit["x"].max()):
            warnings.append("{}的质量 {} g 超出标定范围（{}~{} g），结果仅供参考。".format(
                sample_name, round(mass, 2), full_fit["x"].min(), full_fit["x"].max()))
    if not lines:
        raise OpticsInputError("请填写待测物的全桥输出电压 U′")
    return lines, warnings


def _calc_pressure(fit: dict[str, Any], label: str) -> tuple[list[str], list[str]]:
    """压阻传感器输出特性：灵敏度 S = ΔU/ΔP 与零点检查。"""
    lines = [
        "{}拟合：U = {:.4f} + {:.4f}·P（P/kPa，U/mV），R² = {:.5f}".format(
            label, fit["intercept"], fit["slope"], fit["r2"]),
        "{}灵敏度 S = {:.4f} ± {:.4g} mV/kPa".format(label, fit["slope"], fit["slope_unc"]),
    ]
    warnings = []
    span = float(np.abs(fit["y"]).max()) or 1.0
    if abs(fit["intercept"]) > 0.02 * span:
        warnings.append("{}零点输出偏移明显（b = {:.4f} mV）。".format(label, fit["intercept"]))
    if fit["r2"] < 0.995:
        warnings.append("{}拟合 R² = {:.4f} 偏低，请检查数据线性。".format(label, fit["r2"]))
    return lines, warnings


def _compare_pressure(fit_pos: dict[str, Any],
                      fit_neg: dict[str, Any]) -> tuple[list[str], list[str]]:
    """正、负压灵敏度大小对比（理想情况两侧对称）。"""
    s_pos = abs(fit_pos["slope"])
    s_neg = abs(fit_neg["slope"])
    deviation = abs(s_pos - s_neg) / ((s_pos + s_neg) / 2) * 100
    lines = ["正、负压灵敏度 |S₊| = {:.4f}、|S₋| = {:.4f} mV/kPa，相对差异 {:.2f}%".format(
        s_pos, s_neg, deviation)]
    warnings = []
    if deviation > 10:
        warnings.append("正、负压灵敏度相差超过 10%，请检查气压读数方向与传感器量程是否对称。")
    return lines, warnings


def _run_calculations(tables: dict[str, Any], parameters: dict[str, Any]):
    """执行全部计算，返回 (calc_results, calc_messages)。"""
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    supply_v = as_number(parameters.get("bridge_supply_v"))
    ref_g = as_number(parameters.get("unknown_ref_g"))

    bridge_fits: dict[str, dict[str, Any]] = {}
    for table_id, label, fraction in (("quarter", "单臂电桥", 4),
                                      ("half", "半桥", 2),
                                      ("full", "全桥", 1)):
        rows = tables.get(table_id) or []
        if not _has_data(rows, ("c0", "c1")):
            continue
        try:
            fit = _xy_fit(rows, "c0", "c1", "砝码质量", "输出电压")
        except OpticsInputError as exc:
            calc_messages.append(str(exc))
            continue
        bridge_fits[table_id] = fit
        lines, warnings = _calc_bridge(fit, label, supply_v, fraction)
        calc_results[table_id] = {"lines": lines, "warnings": warnings}

    if len(bridge_fits) == 3:
        lines, warnings = _compare_bridges(bridge_fits, supply_v)
        calc_results["bridge_compare"] = {"lines": lines, "warnings": warnings}

    if "full" in bridge_fits and _has_data(tables.get("unknown") or [], ("c1",)):
        try:
            lines, warnings = _calc_unknown(tables["unknown"], bridge_fits["full"], ref_g)
            calc_results["unknown"] = {"lines": lines, "warnings": warnings}
        except OpticsInputError as exc:
            calc_messages.append(str(exc))

    pressure_fits: dict[str, dict[str, Any]] = {}
    for table_id, label in (("pressure_pos", "正压"), ("pressure_neg", "负压")):
        rows = tables.get(table_id) or []
        if not _has_data(rows, ("c0", "c1")):
            continue
        try:
            fit = _xy_fit(rows, "c0", "c1", "气压", "输出电压")
        except OpticsInputError as exc:
            calc_messages.append(str(exc))
            continue
        pressure_fits[table_id] = fit
        lines, warnings = _calc_pressure(fit, label)
        calc_results[table_id] = {"lines": lines, "warnings": warnings}

    if "pressure_pos" in pressure_fits and "pressure_neg" in pressure_fits:
        lines, warnings = _compare_pressure(pressure_fits["pressure_pos"], pressure_fits["pressure_neg"])
        for table_id in ("pressure_pos", "pressure_neg"):
            calc_results[table_id]["lines"].extend(lines)
            calc_results[table_id]["warnings"].extend(warnings)
    return calc_results, calc_messages


def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：电桥灵敏度、待测物质量、压阻正/负压灵敏度。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results, calc_messages = _run_calculations(tables, parameters)
    return {"tables": tables, "calc_results": calc_results, "calc_messages": calc_messages}


# ──────────────────────────────────────────────
# 结构化接口
# ──────────────────────────────────────────────

def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """结构化接口：计算灵敏度/待测物质量并生成对比图表与 Word 处理文档。"""
    try:
        tables = copied_tables(payload)
        parameters = payload.get("parameters") or {}
        supply_v = get_parameter(payload, "bridge_supply_v", None, False, cast=float)
        ref_g = get_parameter(payload, "unknown_ref_g", None, False, cast=float)
        alarm_pressure = get_parameter(payload, "alarm_pressure_kpa", None, False, cast=float)

        # 必做数据表校验（电桥三表、待测物、正/负压各至少满足最低行数）
        for table_id in ("quarter", "half", "full"):
            get_rows(payload, table_id, required=True, min_rows=3)
        get_rows(payload, "unknown", required=True, min_rows=1)
        for table_id in ("pressure_pos", "pressure_neg"):
            get_rows(payload, table_id, required=True, min_rows=3)

        calc_results, calc_messages = _run_calculations(tables, parameters)
        required_ids = {"quarter", "half", "full", "unknown", "pressure_pos", "pressure_neg"}
        incomplete = sorted(required_ids - set(calc_results))
        if incomplete:
            calc_messages.append("表格“{}”数据不足或无效".format("、".join(incomplete)))
        if calc_messages:
            return {"code": 1, "message": "；".join(calc_messages)}

        bridge_fits = {table_id: _xy_fit(tables[table_id], "c0", "c1", "砝码质量", "输出电压")
                       for table_id in ("quarter", "half", "full")}
        pressure_fits = {table_id: _xy_fit(tables[table_id], "c0", "c1", "气压", "输出电压")
                         for table_id in ("pressure_pos", "pressure_neg")}

        # ── 图表 ──（先配置中文字体再创建 Figure，否则中文会回退成方框）
        configure_plotting()
        charts = []
        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        for table_id, label, color, marker in (
                ("quarter", "单臂电桥 $U_1$", "#4472C4", "o"),
                ("half", "半桥 $U_2$", "#2ECC71", "s"),
                ("full", "全桥 $U_3$", "#E67E22", "^")):
            fit = bridge_fits[table_id]
            ax.plot(fit["x"], fit["y"], marker, markersize=4.5, label=label, color=color)
            grid = np.linspace(fit["x"][0], fit["x"][-1], 50)
            ax.plot(grid, fit["intercept"] + fit["slope"] * grid, "--",
                    linewidth=1.2, color=color, alpha=0.8)
        ax.set_xlabel("砝码质量 m / g")
        ax.set_ylabel("电桥输出电压 U / mV")
        ax.set_title("三种电桥输出特性与线性拟合")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp48_bridges.png")
        charts.append({"filename": filename, "title": "单臂/半桥/全桥电桥输出特性对比"})

        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        for table_id, label, color, marker in (
                ("pressure_pos", "正压", "#9B59B6", "o"),
                ("pressure_neg", "负压", "#E74C3C", "s")):
            fit = pressure_fits[table_id]
            ax.plot(fit["x"], fit["y"], marker, markersize=4.5, label=label, color=color)
            grid = np.linspace(fit["x"][0], fit["x"][-1], 50)
            ax.plot(grid, fit["intercept"] + fit["slope"] * grid, "--",
                    linewidth=1.2, color=color, alpha=0.8)
        ax.set_xlabel("气压 P / kPa")
        ax.set_ylabel("输出电压 U / mV")
        ax.set_title("压阻传感器正、负压输出特性")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp48_pressure.png")
        charts.append({"filename": filename, "title": "压阻传感器正/负压输出特性对比"})

        # ── Word 文档 ──
        doc = create_document(name(), subtitle="电应变片传感器 · 压阻传感器 数据处理")
        key_values = []
        for value, label in ((supply_v, "电桥电源电压 U₀ (V)"),
                             (ref_g, "待测物标称质量 (g)"),
                             (alarm_pressure, "报警系统工作气压 (kPa)")):
            if value is not None:
                key_values.append((label, "{:.2f}".format(value)))
        if key_values:
            add_key_values(doc, "实验参数", key_values)

        table_specs = [
            ("表1  单臂电桥输出特性", "quarter", "砝码质量 m/g", "输出电压 U1/mV",
             "U1_fit/mV", "偏差/mV", bridge_fits["quarter"]),
            ("表2  半桥输出特性", "half", "砝码质量 m/g", "输出电压 U2/mV",
             "U2_fit/mV", "偏差/mV", bridge_fits["half"]),
            ("表3  全桥输出特性", "full", "砝码质量 m/g", "输出电压 U3/mV",
             "U3_fit/mV", "偏差/mV", bridge_fits["full"]),
            ("表4  压阻传感器正压输出特性", "pressure_pos", "气压 P/kPa", "输出电压 U/mV",
             "U_fit/mV", "偏差/mV", pressure_fits["pressure_pos"]),
            ("表5  压阻传感器负压输出特性", "pressure_neg", "气压 P/kPa", "输出电压 U/mV",
             "U_fit/mV", "偏差/mV", pressure_fits["pressure_neg"]),
        ]
        for title, table_id, x_label, y_label, fit_label, dev_label, fit in table_specs:
            table_rows = []
            for row in tables.get(table_id) or []:
                if not isinstance(row, dict) or not str(row.get("c0", "")).strip():
                    continue
                x_text = str(row.get("c0", "")).strip()
                y_text = str(row.get("c1", "")).strip()
                try:
                    x_value, y_value = float(x_text), float(y_text)
                    predicted = fit["intercept"] + fit["slope"] * x_value
                    table_rows.append([
                        "{:.4g}".format(x_value), "{:.4g}".format(y_value),
                        "{:.4g}".format(predicted), "{:.4g}".format(y_value - predicted)])
                except (TypeError, ValueError):
                    table_rows.append([x_text, y_text, "", ""])
            add_table(doc, title, [x_label, y_label, fit_label, dev_label], table_rows)

        for title, table_id, headers in (
                ("表6  待测物质量测量（全桥标定）", "unknown",
                 ["待测物名称", "全桥输出电压 U′/mV"]),
                ("表7  应变片受力情况记录", "strain_record",
                 ["应变片编号", "受力类型（拉伸/压缩）", "说明"]),
                ("表8  元器件检测记录", "components",
                 ["元器件", "检测项目", "检测结果"])):
            rows = tables.get(table_id) or []
            if not rows:
                continue
            table_rows = [[str(row.get(key, "")).strip() for key in sorted(row)]
                          for row in rows if isinstance(row, dict)]
            add_table(doc, title, headers, table_rows)

        summary: list[str] = []
        for table_id, label in (("quarter", "单臂电桥"), ("half", "半桥"), ("full", "全桥"),
                                ("bridge_compare", "灵敏度对比"),
                                ("unknown", "待测物质量"),
                                ("pressure_pos", "压阻传感器正压"),
                                ("pressure_neg", "压阻传感器负压")):
            if table_id in calc_results:
                summary.append("【{}】".format(label))
                summary.extend(calc_results[table_id]["lines"])
        if alarm_pressure is not None:
            summary.append("【报警系统】蜂鸣器开始报警时系统气压：{:.2f} kPa".format(alarm_pressure))
        component_rows = tables.get("components") or []
        if _has_data(component_rows, ("c0", "c1", "c2")):
            summary.append("【元器件检测】已记录 {} 项检测结果。".format(
                len([row for row in component_rows if isinstance(row, dict)
                     and any(str(v).strip() for v in row.values())])))
        add_summary(doc, summary)

        warnings: list[str] = []
        for result in calc_results.values():
            warnings.extend(result.get("warnings", []))
        warnings = list(dict.fromkeys(warnings))

        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


# ──────────────────────────────────────────────
# 表结构与示例数据
# ──────────────────────────────────────────────

def schema() -> dict[str, Any]:
    quarter = make_table(
        "quarter", "单臂电桥输出特性（依次增加砝码）",
        ["砝码质量 m/g", "输出电压 U1/mV"],
        sample=_noisy_bridge(0.502, 0.008, _QUARTER_NOISE),
        min_rows=3, initial_rows=11,
        description=(
            "R1 为应变片，其余三臂接固定电阻；电桥调零后依次增加砝码（约 20 g 一档，至 200 g），"
            "记录万用表读数 U1。"
        ),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "砝码质量 m (g)",
               "y_label": "输出电压 U1 (mV)", "title": "单臂电桥输出特性", "fit": "linear"},
    )
    quarter["calc"] = {"label": "拟合单臂灵敏度"}

    half = make_table(
        "half", "半桥输出特性（依次增加砝码）",
        ["砝码质量 m/g", "输出电压 U2/mV"],
        sample=_noisy_bridge(1.004, -0.012, _HALF_NOISE),
        min_rows=3, initial_rows=11,
        description=(
            "相邻两臂 R1、R2 均为应变片（一拉一压），其余两臂接固定电阻；"
            "同样依次增加砝码并记录 U2。"
        ),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "砝码质量 m (g)",
               "y_label": "输出电压 U2 (mV)", "title": "半桥输出特性", "fit": "linear"},
    )
    half["calc"] = {"label": "拟合半桥灵敏度"}

    full = make_table(
        "full", "全桥输出特性（依次增加砝码）",
        ["砝码质量 m/g", "输出电压 U3/mV"],
        sample=_noisy_bridge(2.006, 0.015, _FULL_NOISE),
        min_rows=3, initial_rows=11,
        description=(
            "四个桥臂全部为应变片（R1、R3 受拉，R2、R4 受压）；标定后作为电子秤使用。"
        ),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "砝码质量 m (g)",
               "y_label": "输出电压 U3 (mV)", "title": "全桥输出特性", "fit": "linear"},
    )
    full["calc"] = {"label": "拟合全桥灵敏度"}

    unknown = make_table(
        "unknown", "待测物质量测量（全桥标定）",
        ["待测物名称", "全桥输出电压 U′/mV"],
        sample=[["待测物A", 78.4], ["待测物B", 152.8]],
        text_columns=(0,), min_rows=1, initial_rows=2,
        description="将标定后的全桥电路视为电子秤，放置待测物并记录桥路输出 U′，由 m_x = (U′−b)/S 求质量。",
    )
    unknown["calc"] = {"label": "计算待测物质量"}

    pressure_pos = make_table(
        "pressure_pos", "压阻传感器正压输出特性",
        ["气压 P/kPa", "输出电压 U/mV"],
        sample=[[p, round(0.263 * p + 0.05 + n, 3)]
                for p, n in zip(_PRESSURE_POS, _POS_NOISE)],
        min_rows=3, initial_rows=11,
        description=(
            "压缩气囊对系统增压，每隔约 10 kPa 记录真空压力表读数与传感器输出电压，"
            "绘制 U-P 曲线并计算灵敏度 S = ΔU/ΔP。"
        ),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "气压 P (kPa)",
               "y_label": "输出电压 U (mV)", "title": "压阻传感器正压输出特性", "fit": "linear"},
    )
    pressure_pos["calc"] = {"label": "拟合正压灵敏度"}

    pressure_neg = make_table(
        "pressure_neg", "压阻传感器负压输出特性",
        ["气压 P/kPa", "输出电压 U/mV"],
        sample=[[p, round(0.259 * p - 0.03 + n, 3)]
                for p, n in zip(_PRESSURE_NEG, _NEG_NOISE)],
        min_rows=3, initial_rows=11,
        description=(
            "用真空泵对系统抽气形成负压，气压按实际（负）值记录，"
            "每隔约 10 kPa 记录一次输出电压并计算负压灵敏度。"
        ),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "气压 P (kPa)",
               "y_label": "输出电压 U (mV)", "title": "压阻传感器负压输出特性", "fit": "linear"},
    )
    pressure_neg["calc"] = {"label": "拟合负压灵敏度"}

    strain_record = make_table(
        "strain_record", "应变片受力情况记录（实验要求1）",
        ["应变片编号", "受力类型（拉伸/压缩）", "说明"],
        sample=[
            ["R1", "拉伸", "粘贴于梁上表面，加载时受拉"],
            ["R2", "压缩", "粘贴于梁下表面，加载时受压"],
            ["R3", "拉伸", "粘贴于梁上表面，加载时受拉"],
            ["R4", "压缩", "粘贴于梁下表面，加载时受压"],
        ],
        text_columns=(0, 1, 2), min_rows=1, initial_rows=4, required=False,
        description="双弯曲悬梁上四个应变片的受力情况（拉伸力/压缩力）研究记录。",
    )
    strain_record["enabled_by_default"] = True

    components = make_table(
        "components", "元器件检测记录表（实验要求1）",
        ["元器件", "检测项目", "检测结果"],
        sample=[
            ["压阻传感器", "工作状态", "正常输出"],
            ["继电器", "开关动作", "正常吸合/释放"],
            ["蜂鸣器", "发声", "报警时正常发声"],
            ["发光二极管", "点亮", "报警时正常点亮"],
            ["二极管", "导通电压", "0.62 V"],
            ["三极管", "基极-发射极导通电压", "0.65 V"],
            ["三极管", "基极-集电极导通电压", "0.64 V"],
        ],
        text_columns=(0, 1, 2), min_rows=1, initial_rows=7, required=False,
        description="检测并记录压阻传感器、继电器、蜂鸣器、发光二极管工作状态及二极管、三极管导通电压。",
    )
    components["enabled_by_default"] = True

    parameters = [
        {"id": "bridge_supply_v", "label": "电桥电源电压 U₀", "unit": "V", "type": "number",
         "default": "", "min": 0, "step": "0.1", "required": False,
         "help": "填写后对照理论电桥灵敏度：单臂 U₀/4、半桥 U₀/2、全桥 U₀（每单位 ΔR/R）"},
        {"id": "unknown_ref_g", "label": "待测物标称质量", "unit": "g", "type": "number",
         "default": "", "min": 0, "step": "any", "required": False,
         "help": "若待测物质量已知（如给定的砝码组合），填写后计算相对误差"},
        {"id": "alarm_pressure_kpa", "label": "报警系统工作气压", "unit": "kPa", "type": "number",
         "default": "", "min": 0, "step": "any", "required": False,
         "help": "记录蜂鸣器开始报警时系统内的气压大小"},
    ]

    theory = get_table_theory("exp48")
    global_theory = theory.get("_global", {})
    return make_schema(
        (
            "传感器系列实验：①电应变片——单臂/半桥/全桥电桥电压-质量特性与灵敏度标定，"
            "三种电桥灵敏度之比应与理论 1:2:4 相符，全桥标定后作电子秤测待测物质量；"
            "②压阻传感器——正压/负压输出特性与灵敏度，元器件检测与报警气压记录。"
            "指导书要求不交完整报告，完成基本数据处理即可。"
        ),
        [quarter, half, full, unknown, pressure_pos, pressure_neg, strain_record, components],
        parameters=parameters,
        parameters_sample={
            "bridge_supply_v": 5.0, "unknown_ref_g": "", "alarm_pressure_kpa": "",
        },
        analysis_hints=(
            "三种电桥灵敏度之比应接近 1:2:4；各表拟合截距应接近 0（电桥未调零会产生零点偏移）；"
            "负压表气压按实际（负）值记录；拟合 R² 应接近 1；"
            "待测物质量由全桥标定反推，超出标定范围的结果仅供参考。"
        ),
        preview_enabled=True,
        report_enabled=False,
        formulas=global_theory.get("formulas", []),
        variables=global_theory.get("variables", []),
        table_theory=theory,
    )


def handle(workpath, extension):
    """保留旧插件入口：处理单表 x-U 标定数据（AI 助教路径兼容）。"""
    try:
        excelpath = workpath + name() + '.' + extension

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        # 多种传感器综合实验，常见数据列：x(位移/压力/温度输入), U(mV输出)
        x_col = [c for c in cols if 'x' in c or '输入' in c or '位移' in c or '压力' in c or 'T' in c.upper()][0] if any('x' in c or '输入' in c or '位移' in c or '压力' in c or 'T' in c.upper() for c in cols) else cols[0]
        u_col = [c for c in cols if 'U' in c or '输出' in c or '电压' in c or 'V' in c][0] if any('U' in c or '输出' in c or '电压' in c or 'V' in c for c in cols) else cols[1]

        x = pd.to_numeric(data[x_col], errors='coerce')
        U_out = pd.to_numeric(data[u_col], errors='coerce')

        # 线性拟合（传感器特性曲线）
        res_lsm = analyse_lsm(x, U_out, 'x', 'U_{out}', '', 'mV')

        # 灵敏度
        sensitivity = res_lsm.m

        # 线性度 = max|Δy| / (满量程输出) * 100%
        y_fit = res_lsm.m * x + res_lsm.b
        linearity = abs(U_out - y_fit).max() / (U_out.max() - U_out.min()) * 100 if (U_out.max() - U_out.min()) > 1e-10 else 0

        # 迟滞（如果有上升/下降两组数据）
        # 简化处理：仅做单向

        docu = Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("传感器特性实验")
        docu.add_paragraph("灵敏度 S = {:.4f} mV/单位".format(sensitivity))
        docu.add_paragraph("线性度 = {:.3f}%".format(linearity))
        docu.add_paragraph()

        docu.add_paragraph("传感器输入-输出特性曲线")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(x)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['输入 x', '输出 U (mV)', '拟合 U_fit', '偏差']):
            table.rows[0].cells[j].text = h
        for i in range(len(x)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(x.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(U_out.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(y_fit.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(U_out.iloc[i] - y_fit.iloc[i])
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()
        docu.add_paragraph("灵敏度：S = \\frac{\\Delta U}{\\Delta x}")
        docu.add_paragraph("线性度：\\delta_L = \\frac{\\max|\\Delta y|}{Y_{FS}} \\times 100\\%")

        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1
