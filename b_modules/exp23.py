"""光电效应 B 数据处理模块。

按 2026 年新版实验指导，仅实现不交实验报告时仍需完成的基本数据处理：

1. 零电流法和补偿法的遏止电压-频率拟合；
2. 改变光阑孔径时，验证饱和光电流与光强的关系；
3. 改变光源距离时，验证饱和光电流与光强的关系。

伏安特性曲线、拐点法和内光电效应均属选做，本模块不提供输入项。
"""

from __future__ import annotations

import math
import os
from typing import Any

from structured_support import as_number, copied_tables, make_schema, make_table, structured_result


_E_CHARGE = 1.602e-19
_H_REFERENCE = 6.626e-34
_LIGHT_SPEED = 2.99792458e8
_SPECTRAL_LINES = (
    (365.0, 8.214),
    (404.7, 7.408),
    (435.8, 6.879),
    (546.1, 5.490),
    (577.0, 5.196),
)


def name():
    return "光电效应B"


def _table(
    table_id: str,
    title: str,
    labels: list[str],
    sample: list[list[Any]],
    description: str,
    calc_label: str,
    *,
    readonly: tuple[int, ...] = (),
) -> dict[str, Any]:
    table = make_table(
        table_id,
        title,
        labels,
        sample=sample,
        readonly=readonly,
        min_rows=1,
        initial_rows=len(sample),
        required=True,
        description=description,
    )
    table["calc"] = {"label": calc_label}
    return table


_TABLE_THEORY = {
    "planck": {
        "formulas": [{
            "title": "光电效应法测普朗克常量",
            "steps": [
                {"note": "遏止电压与频率的线性关系：", "formula": r"U_0=\frac{h}{e}\nu-\frac{A}{e}"},
                {"note": "由拟合斜率 k 计算普朗克常量：", "formula": r"h=ek"},
                {"note": "由截距 b 计算逸出功：", "formula": r"A=-eb"},
                {"note": "红限频率与波长：", "formula": r"\nu_0=-\frac{b}{k},\qquad \lambda_0=\frac{c}{\nu_0}"},
            ],
        }],
        "variables": [
            {"symbol": r"\lambda", "description": "入射单色光波长（5 种谱线，由实验指导给定）", "unit": "nm"},
            {"symbol": "U", "description": "遏止电压的绝对值（零电流法与补偿法两种方式测量）", "unit": "V"},
            {"symbol": r"\nu(Hz)", "description": "入射单色光频率（由波长换算，表内数值以 10¹⁴ Hz 为单位）", "unit": "10¹⁴ Hz"},
            {"symbol": "h", "description": "普朗克常量", "unit": "J·s"},
            {"symbol": "A", "description": "光电管阴极材料逸出功", "unit": "J"},
        ],
    },
    "aperture": {
        "formulas": [{
            "title": "改变光阑孔径验证光强关系",
            "steps": [
                {"note": "光阑面积：", "formula": r"S=\frac{\pi\Phi^2}{4}"},
                {"note": "入射光强与通光面积成正比：", "formula": r"P\propto S\propto\Phi^2"},
                {"note": "饱和光电流应与入射光强成正比：", "formula": r"I_M\propto P"},
            ],
        }],
        "variables": [
            {"symbol": r"\Phi", "description": "光阑孔径", "unit": "mm"},
            {"symbol": "S", "description": "光阑通光面积", "unit": "mm²"},
            {"symbol": "nmI", "description": "饱和光电流（该波长列测量），应与光强（光阑面积）成正比", "unit": "10⁻¹⁰ A"},
        ],
    },
    "distance": {
        "formulas": [{
            "title": "改变距离验证光强关系",
            "steps": [
                {"note": "点光源近似下的光强：", "formula": r"P\propto\frac{1}{L^2}"},
                {"note": "因此应当检验：", "formula": r"I_M\propto\frac{1}{L^2}"},
            ],
        }],
        "variables": [
            {"symbol": "nmL", "description": "光电管与光源之间的距离 L（该波长列）", "unit": "cm"},
            {"symbol": "nmI", "description": "饱和光电流（该波长列测量），应与 1/L² 成正比", "unit": "10⁻¹⁰ A"},
            {"symbol": "1/L²(nm)", "description": "距离平方倒数 1/L²，用于验证饱和光电流与距离的平方反比关系", "unit": "cm⁻²"},
        ],
    },
}


def schema():
    return make_schema(
        (
            "本实验研究光电效应并测定普朗克常量，不要求提交实验报告：① 记录各波长单色光照射下的"
            "遏止电压（零电流法与补偿法），由 " r"$U_0$" r"–$\nu$" " 直线拟合求普朗克常量 "
            r"$h$" " 与逸出功；② 改变光阑孔径验证光强关系；③ 改变光源距离验证光强关系。"
            "伏安特性、拐点法等内容请在实验现场完成；光源距离、光阑孔径等固定量请在页面顶部填写。"
        ),
        [
            _table(
                "planck",
                "模块一：遏止电压测普朗克常量",
                ["波长 λ/nm", "零电流法 U₀/V", "补偿法 U₀/V", "频率 ν/(×10¹⁴ Hz)"],
                [
                    [365.0, 1.782, 1.800, ""],
                    [404.7, 1.544, 1.560, ""],
                    [435.8, 1.230, 1.250, ""],
                    [546.1, 0.664, 0.680, ""],
                    [577.0, 0.546, 0.560, ""],
                ],
                (
                    "波长和频率由实验指导固定，无需修改。分别填入5种谱线的零电流法和"
                    "补偿法遏止电压绝对值，后端将对两组数据分别拟合。"
                ),
                "🧮 计算普朗克常量",
                readonly=(0, 3),
            ),
            _table(
                "aperture",
                "模块二：改变光阑孔径测饱和光电流",
                ["光阑孔径 Φ/mm", "435.8 nm：I/(×10⁻¹⁰ A)", "546.1 nm：I/(×10⁻¹⁰ A)", "光阑面积 S/mm²"],
                [
                    [2.0, 0.72, 0.09, ""],
                    [4.0, 2.55, 0.31, ""],
                    [8.0, 10.14, 1.13, ""],
                    [14.3, 29.20, 3.32, ""],
                ],
                "孔径是指导书给定值，光阑面积由后端自动计算。请填入两种波长对应的饱和光电流。",
                "🧮 检验光电流-光阑面积关系",
                readonly=(0, 3),
            ),
            _table(
                "distance",
                "模块三：改变光源距离测饱和光电流",
                [
                    "435.8 nm：L/cm", "435.8 nm：I/(×10⁻¹⁰ A)",
                    "546.1 nm：L/cm", "546.1 nm：I/(×10⁻¹⁰ A)",
                    "435.8 nm：1/L² (cm⁻²)", "546.1 nm：1/L² (cm⁻²)",
                ],
                [
                    [30.0, 5.52, 30.0, 0.65, "", ""],
                    [32.0, 4.58, 32.0, 0.54, "", ""],
                    [34.0, 3.96, 34.0, 0.46, "", ""],
                    [36.0, 3.40, 36.0, 0.40, "", ""],
                    [38.0, 2.95, 38.0, 0.35, "", ""],
                    [40.0, 2.60, 40.0, 0.30, "", ""],
                ],
                (
                    "两种波长分别填写距离和饱和光电流，不强制两组距离完全相同。"
                    "1/L²由后端自动计算。"
                ),
                "🧮 检验光电流-距离平方反比关系",
                readonly=(4, 5),
            ),
        ],
        parameters=[
            {"id": "planck_L_mm", "label": "普朗克常量测量时的光源距离 L", "unit": "mm", "type": "number", "default": 400, "min": 0, "step": "any", "required": True},
            {"id": "planck_phi_mm", "label": "普朗克常量测量时的光阑孔径 Φ", "unit": "mm", "type": "number", "default": 4, "min": 0, "step": "any", "required": True},
            {"id": "aperture_U_V", "label": "改变孔径时的阳极电压 UAK", "unit": "V", "type": "number", "default": 30, "step": "any", "required": True},
            {"id": "aperture_L_mm", "label": "改变孔径时的光源距离 L", "unit": "mm", "type": "number", "default": 400, "min": 0, "step": "any", "required": True},
            {"id": "distance_U_V", "label": "改变距离时的阳极电压 UAK", "unit": "V", "type": "number", "default": 20, "step": "any", "required": True},
            {"id": "distance_phi_mm", "label": "改变距离时的光阑孔径 Φ", "unit": "mm", "type": "number", "default": 4, "min": 0, "step": "any", "required": True},
        ],
        analysis_hints=(
            "检查两种遏止电压方法的拟合斜率、截距和 R²；检查饱和光电流与光阑面积、"
            "距离平方倒数的线性程度。"
        ),
        preview_enabled=True,
        report_enabled=False,
        revision=7,
        formulas=[item["formulas"][0] for item in _TABLE_THEORY.values()],
        variables=[
            {"symbol": "U_0", "description": "遏止电压", "unit": "V"},
            {"symbol": r"\nu", "description": "入射光频率", "unit": "10¹⁴ Hz"},
            {"symbol": "I_M", "description": "饱和光电流", "unit": "10⁻¹⁰ A"},
            {"symbol": r"\Phi", "description": "光阑孔径", "unit": "mm"},
            {"symbol": "L", "description": "光源距离", "unit": "mm 或 cm"},
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


def _linear_fit(x_values: list[float], y_values: list[float]) -> dict[str, float]:
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
        "r_squared": r_squared,
        "correlation": correlation,
        "slope_uncertainty": slope_uncertainty,
    }


def _fit_planck(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(rows) < len(_SPECTRAL_LINES):
        raise ValueError("普朗克常量模块需要5种谱线的完整数据")
    cleaned = []
    zero_values = []
    compensation_values = []
    for index, (wavelength, frequency) in enumerate(_SPECTRAL_LINES):
        row = dict(rows[index])
        row["c0"] = wavelength
        row["c3"] = frequency
        zero_values.append(abs(_number(row.get("c1"), f"{wavelength:.1f} nm 零电流法遏止电压")))
        compensation_values.append(abs(_number(row.get("c2"), f"{wavelength:.1f} nm 补偿法遏止电压")))
        cleaned.append(row)

    frequencies = [item[1] for item in _SPECTRAL_LINES]
    methods = {}
    lines = []
    for method_id, label, values in (
        ("zero", "零电流法", zero_values),
        ("compensation", "补偿法", compensation_values),
    ):
        fit = _linear_fit(frequencies, values)
        slope = fit["slope"]
        if slope <= 0:
            raise ValueError(f"{label}的 U₀-ν 拟合斜率必须为正")
        h_value = _E_CHARGE * slope * 1e-14
        h_uncertainty = _E_CHARGE * fit["slope_uncertainty"] * 1e-14
        relative_error = abs(h_value - _H_REFERENCE) / _H_REFERENCE * 100.0
        work_function_j = -_E_CHARGE * fit["intercept"]
        red_frequency_scaled = -fit["intercept"] / slope
        if red_frequency_scaled <= 0:
            raise ValueError(f"{label}的红限频率计算结果非正，请检查数据")
        red_frequency_hz = red_frequency_scaled * 1e14
        red_wavelength_nm = _LIGHT_SPEED / red_frequency_hz * 1e9
        methods[method_id] = {
            "label": label,
            "x": frequencies,
            "y": values,
            "fit": fit,
        }
        lines.extend([
            f"【{label}】U₀ = {fit['intercept']:.6f} + ({slope:.6f})ν，R² = {fit['r_squared']:.6f}",
            f"斜率标准不确定度 u(k) = {fit['slope_uncertainty']:.6g} V/(10¹⁴ Hz)",
            f"普朗克常量 h = ({h_value:.6g} ± {h_uncertainty:.2g}) J·s",
            f"相对误差 = {relative_error:.3f}%",
            f"逸出功 A = {work_function_j:.6g} J = {-fit['intercept']:.6f} eV",
            f"红限频率 ν₀ = {red_frequency_hz:.6g} Hz，红限波长 λ₀ = {red_wavelength_nm:.3f} nm",
        ])
    return {"lines": lines, "series": methods}, cleaned


def _fit_aperture(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(rows) < 4:
        raise ValueError("光阑孔径模块需要4组完数据")
    cleaned = []
    areas = []
    current_435 = []
    current_546 = []
    for index, diameter in enumerate((2.0, 4.0, 8.0, 14.3)):
        row = dict(rows[index])
        area = math.pi * diameter ** 2 / 4.0
        row["c0"] = diameter
        row["c3"] = f"{area:.6f}"
        areas.append(area)
        current_435.append(_number(row.get("c1"), f"孔径 {diameter:g} mm 的435.8 nm饱和光电流"))
        current_546.append(_number(row.get("c2"), f"孔径 {diameter:g} mm 的546.1 nm饱和光电流"))
        cleaned.append(row)
    series = {}
    lines = []
    for key, label, values in (("435", "435.8 nm", current_435), ("546", "546.1 nm", current_546)):
        fit = _linear_fit(areas, values)
        series[key] = {"label": label, "x": areas, "y": values, "fit": fit}
        lines.append(
            f"【{label}】I = {fit['intercept']:.6f} + ({fit['slope']:.6f})S，R² = {fit['r_squared']:.6f}"
        )
    return {"lines": lines, "series": series}, cleaned


def _fit_distance(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cleaned = []
    values = {"435": ([], []), "546": ([], [])}
    for index, raw_row in enumerate(rows, start=1):
        row = dict(raw_row)
        for key, distance_column, current_column, inverse_column, label in (
            ("435", "c0", "c1", "c4", "435.8 nm"),
            ("546", "c2", "c3", "c5", "546.1 nm"),
        ):
            raw_distance = row.get(distance_column)
            raw_current = row.get(current_column)
            if not _has_value(raw_distance) and not _has_value(raw_current):
                row[inverse_column] = ""
                continue
            if not _has_value(raw_distance) or not _has_value(raw_current):
                raise ValueError(f"第 {index} 行{label}的距离和光电流必须同时填写")
            distance = _number(raw_distance, f"第 {index} 行{label}入射距离", positive=True)
            current = _number(raw_current, f"第 {index} 行{label}饱和光电流")
            inverse = 1.0 / distance ** 2
            row[inverse_column] = f"{inverse:.8f}"
            values[key][0].append(inverse)
            values[key][1].append(current)
        cleaned.append(row)

    series = {}
    lines = []
    for key, label in (("435", "435.8 nm"), ("546", "546.1 nm")):
        x_values, y_values = values[key]
        fit = _linear_fit(x_values, y_values)
        series[key] = {"label": label, "x": x_values, "y": y_values, "fit": fit}
        lines.append(
            f"【{label}】I = {fit['intercept']:.6f} + ({fit['slope']:.6f})/L²，R² = {fit['r_squared']:.6f}"
        )
    return {"lines": lines, "series": series}, cleaned


def preview(payload):
    tables = copied_tables(payload)
    calc_results = {}
    calc_messages = []
    for table_id, calculator in (
        ("planck", _fit_planck),
        ("aperture", _fit_aperture),
        ("distance", _fit_distance),
    ):
        rows = tables.get(table_id, []) or []
        if not any(any(_has_value(value) for value in row.values()) for row in rows):
            continue
        try:
            result, cleaned = calculator(rows)
            tables[table_id] = cleaned
            calc_results[table_id] = result
        except ValueError as exc:
            calc_messages.append(f"{exc}")
    return {"tables": tables, "calc_results": calc_results, "calc_messages": calc_messages}


def _parameter_number(parameters: dict[str, Any], key: str, label: str, *, positive: bool = False) -> float:
    return _number(parameters.get(key), label, positive=positive)


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_combined_chart(
    workpath: str,
    filename: str,
    title: str,
    x_label: str,
    y_label: str,
    series: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    figure, axis = plt.subplots(figsize=(7.4, 5.0))
    colors = ("#d94b40", "#2f7fc1", "#3a9d5d")
    for color, item in zip(colors, series.values()):
        x_values = item["x"]
        y_values = item["y"]
        fit = item["fit"]
        axis.scatter(x_values, y_values, color=color, s=28, label=f"{item['label']} data")
        fit_x = sorted(x_values)
        fit_y = [fit["intercept"] + fit["slope"] * value for value in fit_x]
        axis.plot(fit_x, fit_y, color=color, linewidth=1.5, label=f"{item['label']} fit")
    axis.set_title(title, fontproperties=font)
    axis.set_xlabel(x_label, fontproperties=font)
    axis.set_ylabel(y_label, fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    path = os.path.join(workpath, filename)
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": filename, "title": title, "x_label": x_label, "y_label": y_label}


def handle_structured(workpath, payload):
    parameters = payload.get("parameters") or {}
    try:
        _parameter_number(parameters, "planck_L_mm", "普朗克常量测量时的光源距离", positive=True)
        _parameter_number(parameters, "planck_phi_mm", "普朗克常量测量时的光阑孔径", positive=True)
        _parameter_number(parameters, "aperture_U_V", "改变孔径时的阳极电压")
        _parameter_number(parameters, "aperture_L_mm", "改变孔径时的光源距离", positive=True)
        _parameter_number(parameters, "distance_U_V", "改变距离时的阳极电压")
        _parameter_number(parameters, "distance_phi_mm", "改变距离时的光阑孔径", positive=True)
    except ValueError as exc:
        return {"code": 1, "message": str(exc)}

    result = preview(payload)
    required_ids = ("planck", "aperture", "distance")
    missing = [table_id for table_id in required_ids if table_id not in result["calc_results"]]
    if missing:
        return {"code": 1, "message": "；".join(result["calc_messages"]) or "请完整填写三个必做模块。"}

    os.makedirs(workpath, exist_ok=True)
    charts = [
        _make_combined_chart(workpath, "planck_fit.png", "遏止电压与入射光频率的关系", r"$\nu$ ($10^{14}$ Hz)", r"$U_0$ (V)", result["calc_results"]["planck"]["series"]),
        _make_combined_chart(workpath, "aperture_fit.png", "饱和光电流与光阑面积的关系", r"$S$ (mm$^2$)", r"$I_M$ ($10^{-10}$ A)", result["calc_results"]["aperture"]["series"]),
        _make_combined_chart(workpath, "distance_fit.png", "饱和光电流与距离平方倒数的关系", r"$1/L^2$ (cm$^{-2}$)", r"$I_M$ ($10^{-10}$ A)", result["calc_results"]["distance"]["series"]),
    ]
    summary = []
    for table_id, label in (("planck", "普朗克常量测量"), ("aperture", "改变光阑孔径"), ("distance", "改变光源距离")):
        summary.append(f"【{label}】")
        summary.extend(result["calc_results"][table_id]["lines"])

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath,
        name(),
        schema(),
        enriched,
        summary=summary,
        charts=charts,
    )


def handle(workpath, extension):
    """保留旧插件入口；本实验使用新版三表结构化接口。"""
    return 1
