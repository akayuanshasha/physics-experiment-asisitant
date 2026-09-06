"""密立根油滴实验 B 数据处理模块。

本模块从三颗油滴的原始下落时间和平衡电压出发，计算油滴带电量、
元电荷及相对误差。按用户确认，即使 N-Q 图在新版指导中属高阶内容，
仍保留学长旧代码的 q-n 线性拟合图，用于选交实验报告。
"""

from __future__ import annotations

import math
import os
import statistics
from typing import Any

from structured_support import as_number, copied_tables, make_schema, make_table, structured_result


_E_REFERENCE = 1.602176634e-19
_DEFAULT_INSTRUMENT_C = 1.429e-14
_DEFAULT_CORRECTION_A = 0.0196

_SAMPLE_OILS = {
    "oil1": (
        [34.80, 34.87, 35.77, 36.40, 36.04, 35.20, 34.77, 36.17],
        [-143, -153, -157, -156, -147, -151, -146, -145],
    ),
    "oil2": (
        [32.56, 32.53, 33.69, 34.01, 32.12, 33.04, 33.53, 32.26],
        [96, 101, 98, 102, 104, 99, 103, 97],
    ),
    "oil3": (
        [33.43, 35.16, 34.99, 33.99, 33.87, 33.98, 33.50, 33.41],
        [72, 76, 74, 77, 75, 73, 78, 74],
    ),
}


def name():
    return "密立根油滴实验B"


_OIL_LABELS = {
    "oil1": "第一颗油滴",
    "oil2": "第二颗油滴",
    "oil3": "第三颗油滴",
}


_TABLE_THEORY = {
    table_id: {
        "formulas": [{
            "title": f"{label}的静态平衡法计算",
            "steps": [
                {"note": "下落时间平均值：", "formula": r"\overline{t_f}=\frac1N\sum_{i=1}^{N}t_{f,i}"},
                {"note": "平衡电压中心值：", "formula": r"U_c=\frac{U_{\max}+U_{\min}}{2}"},
                {"note": "仪器附录给出的简化电荷公式：", "formula": r"q=\frac{C}{U_c\left[t_f\left(1+a\sqrt{t_f}\right)\right]^{3/2}}"},
            ],
        }],
        "variables": [
            {"symbol": "tᶠ", "description": "油滴自然下落 2 mm 的时间（匀速段）", "unit": "s"},
            {"symbol": "U", "description": "平衡电压（使油滴静止时的极板电压，计算时取绝对值）", "unit": "V"},
            {"symbol": "q(C)", "description": "单次测量的油滴电荷量估计值，用于验证电荷量子化 q = ne", "unit": "10⁻¹⁹ C"},
        ],
    }
    for table_id, label in _OIL_LABELS.items()
}


def _oil_table(table_id: str) -> dict[str, Any]:
    times, voltages = _SAMPLE_OILS[table_id]
    sample = [[index + 1, times[index], voltages[index], ""] for index in range(8)]
    table = make_table(
        table_id,
        f"{_OIL_LABELS[table_id]}：平衡电压和下落时间",
        ["测量次数", "下落时间 tᶠ/s", "平衡电压 U/V", "单次电荷估计 q/(×10⁻¹⁹ C)"],
        sample=sample,
        readonly=(0, 3),
        min_rows=8,
        initial_rows=8,
        required=True,
        description=(
            "每颗油滴至少记录8次自然下落2 mm的时间和平衡电压。"
            "仪器极性导致的负电压可直接填写，计算时自动取绝对值。"
        ),
    )
    table["calc"] = {"label": f"🧮 计算{_OIL_LABELS[table_id]}电荷量"}
    return table


def schema():
    return make_schema(
        (
            "密立根油滴实验：三张表均为必做，对三颗油滴分别记录至少 8 次自然下落时间与平衡电压。"
            "页面会自动计算每次测量的带电量 " r"$q_i$" "、推定元电荷数 " r"$n_i$" "，并完成 "
            r"$q$" r"–$n$" " 线性拟合，由拟合斜率求得元电荷 " r"$e$" "；"
            "请按实验报告要求在参数区选取一颗油滴，计算其带电量 " r"$q$" " 的标准不确定度。"
        ),
        [_oil_table("oil1"), _oil_table("oil2"), _oil_table("oil3")],
        parameters=[
            {
                "id": "instrument_C",
                "label": "仪器简化公式常数 C",
                "unit": "C·V·s³⁄²",
                "type": "number",
                "default": _DEFAULT_INSTRUMENT_C,
                "min": 0,
                "step": "any",
                "required": True,
                "help": "2026年指导书 OM99S 仪器附录给定值为 1.429×10⁻¹⁴。",
            },
            {
                "id": "correction_a",
                "label": "粘滞修正系数 a",
                "unit": "s⁻¹⁄²",
                "type": "number",
                "default": _DEFAULT_CORRECTION_A,
                "min": 0,
                "step": "any",
                "required": True,
                "help": "2026年指导书简化公式给定值为 0.0196。",
            },
            {
                "id": "uncertainty_oil",
                "label": "计算标准不确定度的油滴",
                "type": "select",
                "default": "oil1",
                "required": True,
                "options": [
                    {"value": "oil1", "label": "第一颗油滴"},
                    {"value": "oil2", "label": "第二颗油滴"},
                    {"value": "oil3", "label": "第三颗油滴"},
                ],
                "help": "按实验报告要求，选取一颗油滴计算 q 的标准不确定度。",
            },
        ],
        analysis_hints=(
            "检查各颗油滴的下落时间和平衡电压离散程度；检查 q/e₀ 是否接近整数；"
            "检查 q-n 拟合的截距和 R²。"
        ),
        preview_enabled=True,
        report_enabled=True,
        revision=7,
        formulas=[
            {
                "title": "油滴电荷量与元电荷",
                "steps": [
                    {"note": "静态平衡法简化公式：", "formula": r"q=\frac{C}{U_c\left[t_f\left(1+a\sqrt{t_f}\right)\right]^{3/2}}"},
                    {"note": "电荷量子化关系：", "formula": r"q_i=n_i e"},
                    {"note": "拟合模型：", "formula": r"q=b+en"},
                ],
            },
            {
                "title": "选定油滴的A类标准不确定度",
                "steps": [
                    {"note": "重复测量平均值的标准不确定度：", "formula": r"u_t=\frac{s_t}{\sqrt N},\qquad u_U=\frac{s_U}{\sqrt N}"},
                    {"note": "传播至油滴电荷：", "formula": r"u_q=\sqrt{\left(\frac{\partial q}{\partial U}u_U\right)^2+\left(\frac{\partial q}{\partial t}u_t\right)^2}"},
                ],
            },
        ],
        variables=[
            {"symbol": "q_i", "description": "第 i 颗油滴带电量", "unit": "C"},
            {"symbol": "n_i", "description": "第 i 颗油滴所带元电荷数", "unit": "无单位"},
            {"symbol": "e", "description": "由 q-n 拟合斜率得到的元电荷", "unit": "C"},
            {"symbol": "u_q", "description": "选定油滴电荷量的A类标准不确定度", "unit": "C"},
        ],
        table_theory=_TABLE_THEORY,
    )


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


def _parameters(payload: dict[str, Any]) -> tuple[float, float, str]:
    parameters = payload.get("parameters") or {}
    instrument_c = _number(parameters.get("instrument_C"), "仪器简化公式常数 C", positive=True)
    correction_a = _number(parameters.get("correction_a"), "粘滞修正系数 a")
    if correction_a < 0:
        raise ValueError("粘滞修正系数 a 不能为负")
    uncertainty_oil = str(parameters.get("uncertainty_oil") or "oil1")
    if uncertainty_oil not in _OIL_LABELS:
        raise ValueError("请选择要计算不确定度的油滴")
    return instrument_c, correction_a, uncertainty_oil


def _meaningful_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if _has_value(row.get("c1")) or _has_value(row.get("c2"))]


def _oil_result(
    table_id: str,
    rows: list[dict[str, Any]],
    instrument_c: float,
    correction_a: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = _meaningful_rows(rows)
    if len(rows) < 8:
        raise ValueError(f"{_OIL_LABELS[table_id]}至少需要8组完整测量")
    cleaned = []
    times = []
    voltages = []
    for index, raw_row in enumerate(rows, start=1):
        row = dict(raw_row)
        row["c0"] = index
        time_value = _number(row.get("c1"), f"{_OIL_LABELS[table_id]}第 {index} 次下落时间", positive=True)
        voltage_value = abs(_number(row.get("c2"), f"{_OIL_LABELS[table_id]}第 {index} 次平衡电压"))
        if voltage_value <= 0:
            raise ValueError(f"{_OIL_LABELS[table_id]}第 {index} 次平衡电压的绝对值必须大于 0")
        times.append(time_value)
        voltages.append(voltage_value)
        single_charge = instrument_c / (
            voltage_value
            * (time_value * (1.0 + correction_a * math.sqrt(time_value))) ** 1.5
        )
        row["c3"] = f"{single_charge / 1e-19:.6f}"
        cleaned.append(row)

    count = len(times)
    mean_time = statistics.fmean(times)
    mean_voltage = statistics.fmean(voltages)
    voltage_upper = max(voltages)
    voltage_lower = min(voltages)
    voltage_center = (voltage_upper + voltage_lower) / 2.0
    time_std = statistics.stdev(times)
    voltage_std = statistics.stdev(voltages)
    time_uncertainty = time_std / math.sqrt(count)
    voltage_uncertainty = voltage_std / math.sqrt(count)

    correction = 1.0 + correction_a * math.sqrt(mean_time)
    charge = instrument_c / (voltage_center * (mean_time * correction) ** 1.5)
    dq_d_u = -charge / voltage_center
    time_sensitivity = -1.5 * charge * (
        1.0 / mean_time
        + correction_a / (2.0 * math.sqrt(mean_time) * correction)
    )
    charge_uncertainty = math.sqrt(
        (dq_d_u * voltage_uncertainty) ** 2
        + (time_sensitivity * time_uncertainty) ** 2
    )
    charge_number = max(1, int(round(charge / _E_REFERENCE)))
    elementary_estimate = charge / charge_number
    return {
        "label": _OIL_LABELS[table_id],
        "count": count,
        "mean_time": mean_time,
        "mean_voltage": mean_voltage,
        "voltage_upper": voltage_upper,
        "voltage_lower": voltage_lower,
        "voltage_center": voltage_center,
        "time_std": time_std,
        "voltage_std": voltage_std,
        "time_uncertainty": time_uncertainty,
        "voltage_uncertainty": voltage_uncertainty,
        "charge": charge,
        "charge_uncertainty": charge_uncertainty,
        "charge_number": charge_number,
        "elementary_estimate": elementary_estimate,
        "lines": [
            f"有效测量次数 N = {count}",
            f"平均下落时间 t̄ = {mean_time:.6f} s，样本标准差 s(t) = {time_std:.6f} s",
            f"平衡电压平均值 = {mean_voltage:.6f} V，上限 = {voltage_upper:.6f} V，下限 = {voltage_lower:.6f} V",
            f"平衡电压中心值 Uc = {voltage_center:.6f} V",
            f"油滴带电量 q = {charge:.6g} C",
            f"推定元电荷数 n = {charge_number}，q/n = {elementary_estimate:.6g} C",
        ],
    }, cleaned


def _linear_fit(x_values: list[float], y_values: list[float]) -> dict[str, float]:
    count = len(x_values)
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    ss_x = sum((value - mean_x) ** 2 for value in x_values)
    ss_y = sum((value - mean_y) ** 2 for value in y_values)
    if ss_x <= 0:
        raise ValueError("三颗油滴推定的元电荷数 n 全部相同，无法生成有意义的 q-n 拟合图")
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
        "r_squared": r_squared,
        "correlation": correlation,
        "slope_uncertainty": slope_uncertainty,
    }


def _combined_result(oils: dict[str, dict[str, Any]], selected_oil: str) -> dict[str, Any]:
    ordered = [oils[table_id] for table_id in _OIL_LABELS]
    charge_numbers = [float(item["charge_number"]) for item in ordered]
    charges = [float(item["charge"]) for item in ordered]
    fit = _linear_fit(charge_numbers, charges)
    elementary_charge = abs(fit["slope"])
    relative_error = abs(elementary_charge - _E_REFERENCE) / _E_REFERENCE * 100.0
    selected = oils[selected_oil]
    return {
        "x": charge_numbers,
        "y": charges,
        "fit": fit,
        "elementary_charge": elementary_charge,
        "relative_error": relative_error,
        "selected_oil": selected_oil,
        "lines": [
            f"q-n 拟合：q = {fit['intercept']:.6g} + ({fit['slope']:.6g})n C",
            f"决定系数 R² = {fit['r_squared']:.6f}",
            f"由斜率得到元电荷 e = {elementary_charge:.6g} C",
            f"斜率标准不确定度 u(e) = {fit['slope_uncertainty']:.3g} C",
            f"与公认值 e₀ = {_E_REFERENCE:.10g} C 相比，相对误差 = {relative_error:.3f}%",
            f"【{selected['label']}不确定度】u(t̄) = {selected['time_uncertainty']:.6g} s，u(Ū) = {selected['voltage_uncertainty']:.6g} V",
            f"仅计入重复测量A类分量时，u(q) = {selected['charge_uncertainty']:.3g} C",
            f"选定油滴结果：q = ({selected['charge']:.6g} ± {selected['charge_uncertainty']:.2g}) C",
        ],
    }


def preview(payload):
    tables = copied_tables(payload)
    calc_results = {}
    calc_messages = []
    try:
        instrument_c, correction_a, selected_oil = _parameters(payload)
    except ValueError as exc:
        return {"tables": tables, "calc_results": {}, "calc_messages": [str(exc)]}

    oils = {}
    for table_id in _OIL_LABELS:
        rows = tables.get(table_id, []) or []
        if not _meaningful_rows(rows):
            continue
        try:
            result, cleaned = _oil_result(table_id, rows, instrument_c, correction_a)
            tables[table_id] = cleaned
            oils[table_id] = result
            calc_results[table_id] = result
        except ValueError as exc:
            calc_messages.append(str(exc))

    if len(oils) == len(_OIL_LABELS):
        try:
            calc_results["combined"] = _combined_result(oils, selected_oil)
        except ValueError as exc:
            calc_messages.append(str(exc))
    return {"tables": tables, "calc_results": calc_results, "calc_messages": calc_messages}


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_charge_chart(workpath: str, combined: dict[str, Any]) -> dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    x_values = combined["x"]
    y_values = [value * 1e19 for value in combined["y"]]
    slope = combined["fit"]["slope"] * 1e19
    intercept = combined["fit"]["intercept"] * 1e19
    fit_x = sorted(x_values)
    fit_y = [intercept + slope * value for value in fit_x]

    figure, axis = plt.subplots(figsize=(7.0, 5.0))
    axis.scatter(x_values, y_values, color="#d94b40", s=38, label="Measured charge")
    axis.plot(fit_x, fit_y, color="#2f7fc1", linewidth=1.6, label="Linear fit")
    title = "油滴电荷量与元电荷数的关系"
    axis.set_title(title, fontproperties=font)
    axis.set_xlabel("n")
    axis.set_ylabel("q (10⁻¹⁹ C)")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    filename = "charge_number_fit.png"
    figure.savefig(os.path.join(workpath, filename), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": filename, "title": title, "x_label": "n", "y_label": "q (10⁻¹⁹ C)"}


def handle_structured(workpath, payload):
    result = preview(payload)
    required_ids = tuple(_OIL_LABELS)
    missing = [table_id for table_id in required_ids if table_id not in result["calc_results"]]
    if missing or "combined" not in result["calc_results"]:
        message = "；".join(result["calc_messages"])
        if not message:
            labels = "、".join(_OIL_LABELS[table_id] for table_id in missing)
            message = f"请完整填写{labels}的至少8次测量。"
        return {"code": 1, "message": message}

    os.makedirs(workpath, exist_ok=True)
    combined = result["calc_results"]["combined"]
    chart = _make_charge_chart(workpath, combined)
    summary = []
    for table_id in required_ids:
        summary.append(f"【{_OIL_LABELS[table_id]}】")
        summary.extend(result["calc_results"][table_id]["lines"])
    summary.append("【元电荷与不确定度】")
    summary.extend(combined["lines"])
    warnings = [
        "u(q) 只包含下落时间和平衡电压重复测量的A类标准不确定度，未包含指导书未给出的仪器B类分量。"
    ]

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath,
        name(),
        schema(),
        enriched,
        summary=summary,
        warnings=warnings,
        charts=[chart],
    )


def handle(workpath, extension):
    """保留旧插件入口；本实验使用新版三表结构化接口。"""
    return 1
