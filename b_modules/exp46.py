"""导热系数（稳态法）实验数据处理模块。

必做内容（指导书第 1-7 页）：
1. 记录稳态温度 T1、T2 与黄铜盘 A 的自由冷却曲线（每 30 s 一点，约 12 点）；
2. 对冷却段 T(t) 做最小二乘拟合求冷却速率 dT/dt；
3. 按指导书公式（6）计算不良导体导热系数 λ。

选做拓展：
- 提高内容：热电偶定标（30~100 °C 温差电动势线性拟合）；
- 高阶内容：金属棒热导率（λ = P·h/(S·ΔT)，对照铜 401 / 铝 235 W/(m·K)）。
"""

from __future__ import annotations

import math
import os
from typing import Any

from structured_support import as_number, copied_tables, make_schema, make_table, structured_result
from theory_content import get_table_theory

# ── 常数与参考值 ──
_THERMOCOUPLE_COEFF_REF = 0.04   # 铜-康铜热电偶温差电系数参考值（mV/K）
_METAL_REFERENCE = {"铜": 401.0, "铝": 235.0}  # 金属棒理论热导率（W/(m·K)）


def name():
    return "导热系数"


# ──────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────

def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    number = as_number(value)
    if number is None:
        raise ValueError(f"{label}必须填写数字")
    number = float(number)
    if positive and number <= 0:
        raise ValueError(f"{label}必须大于 0")
    return number


def _linear_fit(x_values: list[float], y_values: list[float]) -> dict[str, float]:
    """最小二乘线性拟合，返回斜率、截距、R² 与斜率标准不确定度。"""
    if len(x_values) != len(y_values) or len(x_values) < 3:
        raise ValueError("线性拟合至少需要3组完整数据")
    count = len(x_values)
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    ss_x = sum((value - mean_x) ** 2 for value in x_values)
    ss_y = sum((value - mean_y) ** 2 for value in y_values)
    if ss_x <= 0:
        raise ValueError("拟合横坐标不能全部相同")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / ss_x
    intercept = mean_y - slope * mean_x
    residual = sum((y - intercept - slope * x) ** 2 for x, y in zip(x_values, y_values))
    r_squared = 1.0 if ss_y <= 0 and residual <= 0 else (0.0 if ss_y <= 0 else 1.0 - residual / ss_y)
    correlation = 0.0 if ss_y <= 0 else sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)
    ) / math.sqrt(ss_x * ss_y)
    slope_uncertainty = 0.0
    if count > 2 and abs(correlation) > 1e-15:
        slope_uncertainty = abs(slope) * math.sqrt(max(0.0, (1.0 / correlation ** 2 - 1.0) / (count - 2)))
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r_squared,
        "correlation": correlation,
        "slope_unc": slope_uncertainty,
    }


def _collect_rows(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> tuple[list[list[float]], list[int]]:
    """按列顺序提取完整数值行；不完整或非数字的行号收集到 bad 列表中。"""
    data: list[list[float]] = []
    bad: list[int] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in columns):
            continue
        try:
            data.append([float(row.get(column)) for column in columns])
        except (TypeError, ValueError):
            bad.append(index)
    return data, bad


# ──────────────────────────────────────────────
# 各表计算
# ──────────────────────────────────────────────

def _calc_steady(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """稳态温度：取最后一个完整行作为稳态读数。"""
    data, bad = _collect_rows(rows, ("c0", "c1"))
    if bad:
        raise ValueError("稳态温度表第 {} 行数据不完整或不是数字".format("、".join(map(str, bad))))
    if not data:
        raise ValueError("请填写稳态温度 T1 和 T2")
    t1, t2 = data[-1]
    if t1 - t2 <= 0:
        raise ValueError("稳态温差 T1 - T2 必须为正（T1 为上盘高温端）")
    return {"t1": t1, "t2": t2, "delta_t": t1 - t2, "row_count": len(data)}


def _calc_cooling(rows: list[dict[str, Any]], parameters: dict[str, Any],
                  steady: dict[str, Any]) -> dict[str, Any]:
    """冷却曲线最小二乘拟合 + 指导书公式（6）计算导热系数。"""
    data, bad = _collect_rows(rows, ("c0", "c1"))
    if bad:
        raise ValueError("冷却曲线第 {} 行数据不完整或不是数字".format("、".join(map(str, bad))))
    if len(data) < 3:
        raise ValueError("冷却曲线至少需要 3 组数据（每 30 s 一点，取 T2 前后各约 6 个）")

    ts = [row[0] for row in data]
    temps = [row[1] for row in data]
    fit = _linear_fit(ts, temps)
    k_abs = abs(fit["slope"])
    if k_abs <= 0:
        raise ValueError("冷却速率拟合斜率必须非零（自然冷却应为负斜率）")

    h_a = _number(parameters.get("h_A"), "黄铜盘厚度 h_A", positive=True) / 1000
    h_b = _number(parameters.get("h_B"), "样品盘厚度 h_B", positive=True) / 1000
    d_b = _number(parameters.get("D_B"), "样品盘直径 D_B", positive=True) / 1000
    m_copper = _number(parameters.get("m_copper"), "黄铜盘质量", positive=True) / 1000
    c_copper = _number(parameters.get("c_copper"), "黄铜比热容", positive=True)
    lambda_ref = _number(parameters.get("lambda_ref"), "参考导热系数", positive=True)

    r_b = d_b / 2
    area = math.pi * r_b ** 2
    correction = (r_b + 2 * h_a) / (2 * r_b + 2 * h_a)
    delta_t = steady["delta_t"]

    # 指导书公式（6）
    lam = m_copper * c_copper * h_b * k_abs * correction / (area * delta_t)
    u_lam = lam * fit["slope_unc"] / k_abs
    rel_err = abs(lam - lambda_ref) / lambda_ref * 100

    lines = [
        "稳态温度 T1 = {:.1f} °C，T2 = {:.1f} °C，ΔT = {:.1f} °C".format(
            steady["t1"], steady["t2"], delta_t),
        "冷却速率最小二乘拟合：T = {:.3f} + ({:.5f})t，R² = {:.5f}，u(k) = {:.5f} K/s".format(
            fit["intercept"], fit["slope"], fit["r2"], fit["slope_unc"]),
        "散热面积修正系数 (R_B+2h_A)/(2R_B+2h_A) = {:.4f}".format(correction),
        "导热系数 λ = {:.4f} ± {:.4f} W/(m·K)".format(lam, u_lam),
        "与参考值 {:.2f} W/(m·K) 相比，相对误差 {:.2f}%".format(lambda_ref, rel_err),
    ]
    return {"lines": lines, "lam": lam, "u_lam": u_lam, "correction": correction, "fit": fit}


def _calc_calib(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """热电偶定标：温差电动势-温度线性拟合。"""
    data, bad = _collect_rows(rows, ("c0", "c1"))
    if bad:
        raise ValueError("定标表第 {} 行数据不完整或不是数字".format("、".join(map(str, bad))))
    if len(data) < 3:
        raise ValueError("热电偶定标至少需要 3 组数据（30~100 °C 每隔 10 °C 一组）")

    temps = [row[0] for row in data]
    emfs = [row[1] for row in data]
    fit = _linear_fit(temps, emfs)
    coeff = fit["slope"]
    if abs(coeff) < 1e-12:
        raise ValueError("定标拟合斜率不能为零")
    rel_err = abs(abs(coeff) - _THERMOCOUPLE_COEFF_REF) / _THERMOCOUPLE_COEFF_REF * 100

    lines = [
        "定标拟合：E = {:.4f} + ({:.5f})T，R² = {:.5f}".format(fit["intercept"], coeff, fit["r2"]),
        "温差电系数 a = {:.4f} mV/K（铜-康铜参考值 {:.2f} mV/K，相对误差 {:.2f}%）".format(
            coeff, _THERMOCOUPLE_COEFF_REF, rel_err),
        "定标关系：T = (E - {:.4f}) / {:.5f}（T：°C，E：mV）".format(fit["intercept"], coeff),
    ]
    return {"lines": lines, "fit": fit}


def _calc_metal(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """金属棒热导率：λ = P·h/(S·ΔT)，与理论值对照。"""
    rod_d = _number(parameters.get("rod_d"), "金属棒直径", positive=True) / 1000
    area = math.pi * rod_d ** 2 / 4
    lines = []
    used = False
    columns = ("c1", "c2", "c3", "c4", "c5")
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in columns):
            continue
        material = str(row.get("c0") or "").strip()
        try:
            h = float(row.get("c1")) / 100
            voltage = float(row.get("c2"))
            current = float(row.get("c3"))
            t1 = float(row.get("c4"))
            t2 = float(row.get("c5"))
        except (TypeError, ValueError):
            raise ValueError("第 {} 行金属棒数据不完整或不是数字".format(index))
        delta_t = abs(t1 - t2)
        if delta_t <= 0:
            raise ValueError("第 {} 行金属棒温差必须非零".format(index))
        power = voltage * current
        lam = power * h / (area * delta_t)
        reference = next((value for key, value in _METAL_REFERENCE.items() if key in material), None)
        material_text = material or "未填写样品"
        if reference is None:
            lines.append(
                "第 {} 行（{}）：P = {:.2f} W，λ = {:.2f} W/(m·K)".format(index, material_text, power, lam))
        else:
            rel = abs(lam - reference) / reference * 100
            lines.append(
                "第 {} 行（{}）：P = {:.2f} W，λ = {:.2f} W/(m·K)，理论值 {:.0f}，相对误差 {:.2f}%".format(
                    index, material_text, power, lam, reference, rel))
        used = True
    if not used:
        raise ValueError("请填写金属棒数据（样品、h、U、I、T1、T2）")
    return {"lines": lines}


# ──────────────────────────────────────────────
# 结构化接口
# ──────────────────────────────────────────────

def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：稳态法导热系数、热电偶定标、金属棒热导率。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    fit_notes: dict[str, list[str]] = {}

    steady_info = None
    steady_rows = tables.get("steady", []) or []
    if any(_has_value(row.get("c0")) and _has_value(row.get("c1")) for row in steady_rows):
        try:
            steady_info = _calc_steady(steady_rows, parameters)
            if steady_info["row_count"] > 1:
                fit_notes["steady"] = [
                    "稳态表共 {} 行，取最后一行作为稳态读数。".format(steady_info["row_count"])]
        except ValueError as exc:
            calc_messages.append(str(exc))

    cooling_rows = tables.get("cooling", []) or []
    if any(_has_value(row.get("c0")) and _has_value(row.get("c1")) for row in cooling_rows):
        try:
            if steady_info is None:
                raise ValueError("请先填写稳态温度表（T1、T2）。")
            calc_results["cooling"] = _calc_cooling(cooling_rows, parameters, steady_info)
        except ValueError as exc:
            calc_messages.append(str(exc))

    calib_rows = tables.get("calib", []) or []
    if any(_has_value(row.get("c0")) and _has_value(row.get("c1")) for row in calib_rows):
        try:
            calc_results["calib"] = _calc_calib(calib_rows, parameters)
        except ValueError as exc:
            calc_messages.append(str(exc))

    metal_rows = tables.get("metal", []) or []
    if any(_has_value(row.get(column)) for row in metal_rows for column in ("c1", "c2", "c3", "c4", "c5")):
        try:
            calc_results["metal"] = _calc_metal(metal_rows, parameters)
        except ValueError as exc:
            calc_messages.append(str(exc))

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


def _schema_table(schema_data: dict[str, Any], table_id: str) -> dict[str, Any]:
    return next(table for table in schema_data["tables"] if table["id"] == table_id)


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """新版结构化接口：计算导热系数并输出摘要与图表。"""
    parameters = payload.get("parameters") or {}
    try:
        for key, label in (
            ("h_A", "黄铜盘厚度 h_A"),
            ("h_B", "样品盘厚度 h_B"),
            ("D_B", "样品盘直径 D_B"),
            ("m_copper", "黄铜盘质量"),
            ("c_copper", "黄铜比热容"),
            ("lambda_ref", "参考导热系数"),
            ("rod_d", "金属棒直径"),
        ):
            _number(parameters.get(key), label, positive=True)
    except ValueError as exc:
        return {"code": 1, "message": str(exc)}

    result = preview(payload)
    if "cooling" not in result["calc_results"]:
        return {"code": 1, "message": "；".join(result["calc_messages"]) or "请完整填写稳态温度与冷却曲线数据。"}

    os.makedirs(workpath, exist_ok=True)
    from structured_support import make_chart_from_table

    schema_data = schema()
    charts = []
    if "cooling" in result["calc_results"]:
        table_schema = _schema_table(schema_data, "cooling")
        charts.append(make_chart_from_table(
            table_schema, result["tables"].get("cooling") or [],
            table_schema["chart"], workpath, "cooling_fit.png"))
    if "calib" in result["calc_results"]:
        table_schema = _schema_table(schema_data, "calib")
        charts.append(make_chart_from_table(
            table_schema, result["tables"].get("calib") or [],
            table_schema["chart"], workpath, "calib_fit.png"))

    summary: list[str] = []
    for table_id, label in (("cooling", "稳态法测导热系数"),
                            ("calib", "热电偶定标"),
                            ("metal", "金属棒热导率")):
        if table_id in result["calc_results"]:
            summary.append("【{}】".format(label))
            summary.extend(result["calc_results"][table_id]["lines"])

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath, name(), schema_data, enriched,
        summary=summary,
        charts=charts,
    )


# ──────────────────────────────────────────────
# 表结构与示例数据
# ──────────────────────────────────────────────

def schema() -> dict[str, Any]:
    steady = make_table(
        "steady", "稳态温度记录表",
        ["上盘温度 T1/°C", "下盘温度 T2/°C"],
        sample=[[80.0, 50.0]],
        min_rows=1, initial_rows=1,
        description=(
            "加热约 50-70 分钟后，上下盘温度不再上升且 10 分钟内各自变化不超过 0.5 °C 即达稳态，"
            "记录此时 T1、T2。若记录了多组，计算取最后一组。"
        ),
    )

    cooling = make_table(
        "cooling", "黄铜盘 A 自由冷却数据表",
        ["时间 t/s", "温度 T/°C"],
        sample=[
            [0, 60.0], [30, 58.5], [60, 57.1], [90, 55.6], [120, 54.0], [150, 52.6],
            [180, 51.0], [210, 49.6], [240, 48.0], [270, 46.6], [300, 45.0], [330, 43.6],
        ],
        min_rows=3, initial_rows=12,
        description=(
            "移去样品盘使 C、A 两盘直接接触，将 A 盘加热到高于 T2 约 10 °C 后自然冷却，"
            "每 30 s 记录一次温度，取最接近 T2 前后的各 6 个数据（约 12 点）。"
        ),
        chart={
            "x_column": "c0", "y_column": "c1",
            "x_label": "时间 t (s)", "y_label": "温度 T (°C)",
            "title": "黄铜盘自由冷却曲线", "fit": "linear",
        },
    )
    cooling["calc"] = {"label": "计算导热系数"}

    calib = make_table(
        "calib", "热电偶定标数据表（提高内容，选做）",
        ["水浴温度 T/°C", "温差电动势 E/mV"],
        sample=[
            [30, 1.21], [40, 1.60], [50, 2.02], [60, 2.40],
            [70, 2.81], [80, 3.21], [90, 3.60], [100, 4.02],
        ],
        min_rows=3, initial_rows=8, required=False,
        description=(
            "热端放入水浴箱、冷端插入冰水混合物（0 °C），水浴从 30 °C 加热到 100 °C，"
            "每隔 10 °C 记录一次电压表读数，拟合得到温度-电压定标关系。"
        ),
        chart={
            "x_column": "c0", "y_column": "c1",
            "x_label": "水浴温度 T (°C)", "y_label": "温差电动势 E (mV)",
            "title": "热电偶定标曲线", "fit": "linear",
        },
    )
    calib["calc"] = {"label": "拟合定标关系"}
    calib["enabled_by_default"] = False

    metal = make_table(
        "metal", "金属棒热导率数据表（高阶内容，选做）",
        ["样品", "传感器间距 h/cm", "加热电压 U/V", "加热电流 I/A",
         "热端温度 T1/°C", "冷端温度 T2/°C"],
        sample=[
            ["铜", 10, 12.0, 0.95, 94.0, 78.0],
            ["铜", 5, 12.0, 0.95, 86.0, 78.0],
            ["铝", 10, 12.0, 0.95, 92.0, 65.0],
            ["铝", 5, 12.0, 0.95, 78.5, 65.0],
        ],
        text_columns=(0,), min_rows=1, initial_rows=4, required=False,
        description=(
            "恒功率加热金属棒，传感器间距 h 取 10 cm 或 5 cm，待温差稳定后记录 U、I、T1、T2。"
            "样品直径约 15 mm（游标卡尺测量，填入参数区）。"
        ),
    )
    metal["calc"] = {"label": "计算金属热导率"}
    metal["enabled_by_default"] = False

    parameters = [
        {"id": "h_A", "label": "黄铜盘 A 厚度 h_A", "unit": "mm", "type": "number",
         "default": 10.0, "min": 0, "step": "any", "required": True},
        {"id": "h_B", "label": "样品盘 B 厚度 h_B", "unit": "mm", "type": "number",
         "default": 5.0, "min": 0, "step": "any", "required": True},
        {"id": "D_B", "label": "样品盘 B 直径 D_B", "unit": "mm", "type": "number",
         "default": 130.0, "min": 0, "step": "any", "required": True},
        {"id": "m_copper", "label": "黄铜盘 A 质量", "unit": "g", "type": "number",
         "default": 1180.0, "min": 0, "step": "any", "required": True,
         "help": "电子天平单次测量"},
        {"id": "c_copper", "label": "黄铜比热容", "unit": "J/(kg·K)", "type": "number",
         "default": 370.9, "min": 0, "step": "any", "required": True,
         "help": "指导书给定 0.3709 kJ/(kg·K)"},
        {"id": "lambda_ref", "label": "参考导热系数", "unit": "W/(m·K)", "type": "number",
         "default": 0.15, "min": 0, "step": "any", "required": True,
         "help": "典型硅胶/橡胶垫约 0.1~0.3，用于相对误差参考"},
        {"id": "rod_d", "label": "金属棒直径", "unit": "mm", "type": "number",
         "default": 15.0, "min": 0, "step": "any", "required": True,
         "help": "约 15 mm，游标卡尺测量（金属棒实验用）"},
    ]

    theory = get_table_theory("exp46")
    return make_schema(
        (
            "本实验用稳态法（李氏法）测量不良导体的导热系数：① 记录稳态温度 "
            r"$T_1$" "、" r"$T_2$" "（10 分钟内变化不超过 0.5 ℃ 判稳）；"
            "② 记录散热盘自由冷却曲线，最小二乘法求冷却速率；③ 按指导书公式计算导热系数。"
            "提高/高阶内容可选做热电偶定标与金属棒热导率。"
        ),
        [steady, cooling, calib, metal],
        parameters=parameters,
        parameters_sample={
            "h_A": 10.0, "h_B": 5.0, "D_B": 130.0, "m_copper": 1180.0,
            "c_copper": 370.9, "lambda_ref": 0.15, "rod_d": 15.0,
        },
        analysis_hints=(
            "判稳条件：10 分钟内温度变化不超过 0.5 °C；"
            "冷却段取最接近 T2 前后各 6 个数据；"
            "检查冷却曲线拟合的 R² 与导热系数量级（不良导体约 0.1~0.3 W/(m·K)）；"
            "金属棒结果对照铜 401、铝 235 W/(m·K)。"
        ),
        preview_enabled=True,
        report_enabled=False,
        formulas=theory.get("cooling", {}).get("formulas", []),
        variables=theory.get("cooling", {}).get("variables", []),
        table_theory=theory,
    )


def handle(workpath: str, extension: str) -> int:
    """保留旧插件入口；本实验使用新版多表结构化接口。"""
    return 1
