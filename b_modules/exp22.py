"""衍射实验 B 数据处理模块。

按照新版实验指导，本模块提供三个相互独立的定量处理部分：

1. 单缝暗条纹位置线性拟合，计算单缝宽度及相对误差；
2. 双缝亮纹或暗纹位置线性拟合，计算双缝中心间距及相对误差；
3. 根据两组衍射条纹间距，计算弹簧细丝直径和弹簧螺距。

小孔、不同光栅和手机屏幕衍射属于观察或自行设计内容，指导书没有给出
统一的数据记录结构，因此本模块不为它们增加强制输入项。
"""

from __future__ import annotations

from typing import Any

from structured_support import (
    as_number,
    copied_tables,
    make_chart_from_table,
    make_schema,
    make_table,
    structured_result,
)


# He-Ne 激光波长：632.8 nm = 0.0006328 mm。
_WAVELENGTH_NM = 632.8
_WAVELENGTH_MM = 0.0006328


def name():
    return "衍射实验B"


_TABLE_THEORY = {
    "single_slit": {
        "formulas": [
            {
                "title": "单缝暗条纹法测缝宽",
                "steps": [
                    {
                        "note": "暗条纹位置与级次满足线性关系：",
                        "formula": r"x=x_0+s_a k",
                    },
                    {
                        "note": "由拟合斜率计算单缝宽度：",
                        "formula": r"a=\frac{L\lambda}{\left|s_a\right|}",
                    },
                    {
                        "note": "与单缝标称宽度比较：",
                        "formula": r"E_a=\frac{\left|a-a_0\right|}{a_0}\times100\%",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "L", "description": "单缝到观察屏的距离", "unit": "mm"},
            {"symbol": "k", "description": "暗条纹级次；中央主极大填 0，左右两侧分别使用负、正级次", "unit": "无单位"},
            {"symbol": "x", "description": "条纹在观察屏上的位置读数", "unit": "mm"},
            {"symbol": "x_fit", "description": "由 x–k 线性拟合得到的暗条纹位置（拟合值）", "unit": "mm"},
            {"symbol": "x_0", "description": "线性拟合截距，对应中央主极大位置", "unit": "mm"},
            {"symbol": "s_a", "description": "x-k 线性拟合斜率", "unit": "mm"},
            {"symbol": "a", "description": "计算得到的单缝宽度", "unit": "μm"},
            {"symbol": "a_0", "description": "单缝标称宽度", "unit": "μm"},
            {"symbol": r"\lambda", "description": "He-Ne 激光波长，固定为 632.8 nm", "unit": "nm"},
        ],
    },
    "double_slit": {
        "formulas": [
            {
                "title": "双缝条纹法测中心间距",
                "steps": [
                    {
                        "note": "亮纹填整数级次；暗纹填半整数有效级次：",
                        "formula": r"q=n\quad(\text{亮纹}),\qquad q=\pm\left(m-\frac12\right)\quad(\text{暗纹})",
                    },
                    {
                        "note": "条纹位置与有效级次满足线性关系：",
                        "formula": r"x=x_0+s_d q",
                    },
                    {
                        "note": "由拟合斜率计算双缝中心间距：",
                        "formula": r"d=\frac{L\lambda}{\left|s_d\right|}",
                    },
                    {
                        "note": "与双缝中心间距标称值比较：",
                        "formula": r"E_d=\frac{\left|d-d_0\right|}{d_0}\times100\%",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "L", "description": "双缝到观察屏的距离", "unit": "mm"},
            {"symbol": "q", "description": "有效级次；亮纹填整数，暗纹填 ±0.5、±1.5、±2.5……", "unit": "无单位"},
            {"symbol": "x", "description": "亮纹或暗纹在观察屏上的位置读数", "unit": "mm"},
            {"symbol": "x_fit", "description": "由 x–q 线性拟合得到的条纹位置（拟合值）", "unit": "mm"},
            {"symbol": "s_d", "description": "x-q 线性拟合斜率", "unit": "mm"},
            {"symbol": "d", "description": "计算得到的双缝中心间距", "unit": "μm"},
            {"symbol": "d_0", "description": "双缝中心间距标称值", "unit": "μm"},
            {"symbol": r"\lambda", "description": "He-Ne 激光波长，固定为 632.8 nm", "unit": "nm"},
        ],
    },
    "spring": {
        "formulas": [
            {
                "title": "利用衍射测量弹簧参数",
                "steps": [
                    {
                        "note": "分别计算较宽、较窄条纹间距的平均值：",
                        "formula": r"\overline{\Delta x_w}=\frac1N\sum_{i=1}^{N}\Delta x_{w,i},\qquad \overline{\Delta x_n}=\frac1N\sum_{i=1}^{N}\Delta x_{n,i}",
                    },
                    {
                        "note": "较宽条纹对应较小结构尺寸，用于计算细丝直径：",
                        "formula": r"d_{\mathrm{wire}}=\frac{L\lambda}{\overline{\Delta x_w}}",
                    },
                    {
                        "note": "较窄条纹对应较大结构周期，用于计算弹簧螺距：",
                        "formula": r"p=\frac{L\lambda}{\overline{\Delta x_n}}",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "L", "description": "弹簧到观察屏的距离", "unit": "mm"},
            {"symbol": r"\Delta x_w", "description": "较宽衍射条纹的宽度或间距", "unit": "mm"},
            {"symbol": r"\Delta x_n", "description": "较窄衍射条纹的宽度或间距", "unit": "mm"},
            {"symbol": r"d_{\mathrm{wire}}", "description": "弹簧细丝直径", "unit": "mm"},
            {"symbol": "d", "description": "弹簧细丝直径估计值，由较宽条纹间距 Δx_w 计算", "unit": "mm"},
            {"symbol": "p", "description": "弹簧螺距", "unit": "mm"},
            {"symbol": r"\lambda", "description": "He-Ne 激光波长，固定为 632.8 nm", "unit": "nm"},
        ],
    },
}


_GLOBAL_FORMULAS = [theory["formulas"][0] for theory in _TABLE_THEORY.values()]

_GLOBAL_VARIABLES = [
    {"symbol": "L", "description": "衍射元件或弹簧到观察屏的距离", "unit": "mm"},
    {"symbol": "x", "description": "条纹位置或条纹间距", "unit": "mm"},
    {"symbol": r"a,\ d", "description": "单缝宽度和双缝中心间距", "unit": "μm"},
    {"symbol": r"d_{\mathrm{wire}},\ p", "description": "弹簧细丝直径和螺距", "unit": "mm"},
    {"symbol": r"\lambda", "description": "He-Ne 激光波长，固定为 632.8 nm", "unit": "nm"},
]


def _table(
    table_id: str,
    title: str,
    labels: list[str],
    sample: list[list[Any]],
    description: str,
    calc_label: str,
    *,
    chart: dict[str, Any] | None = None,
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
        chart=chart,
        required=True,
        description=description,
    )
    table["calc"] = {"label": calc_label}
    return table


def schema():
    single_chart = {
        "x_column": "c0",
        "y_column": "c1",
        "x_label": "暗条纹级次 k",
        "y_label": "条纹位置 x (mm)",
        "title": "单缝暗条纹位置与级次的线性关系",
        "fit": "linear",
    }
    double_chart = {
        "x_column": "c0",
        "y_column": "c1",
        "x_label": "有效级次 q",
        "y_label": "条纹位置 x (mm)",
        "title": "双缝条纹位置与有效级次的线性关系",
        "fit": "linear",
    }

    return make_schema(
        (
            "衍射实验B：单缝和双缝模块进行线性拟合、结构参数计算与相对误差分析；"
            "弹簧模块计算细丝直径和螺距。He-Ne 激光波长固定为 632.8 nm。"
            "单缝、双缝和弹簧参数三个模块均为必做。各模块的固定实验量请在页面顶部填写，"
            "表格中只记录随测量次数变化的数据。注意任何时候都不要直视激光。"
        ),
        [
            _table(
                "single_slit",
                "模块一：单缝缝宽测量",
                ["暗条纹级次 k", "条纹位置 x/mm", "拟合位置 x_fit/mm"],
                [
                    [0, 14.778, ""],
                    [1, 16.270, ""],
                    [2, 17.654, ""],
                    [3, 20.017, ""],
                    [4, 20.882, ""],
                    [5, 21.779, ""],
                ],
                (
                    "记录中央主极大和各级暗条纹的位置。中央主极大级次填 0；若同时记录左右两侧，"
                    "分别填写负、正级次。屏距 L 和标称缝宽 a₀ 请在页面顶部的实验参数区填写。"
                ),
                "🧮 计算单缝宽度",
                chart=single_chart,
                readonly=(2,),
            ),
            _table(
                "double_slit",
                "模块二：双缝中心间距测量",
                ["有效级次 q", "条纹位置 x/mm", "拟合位置 x_fit/mm"],
                [
                    [1, 16.635, ""],
                    [2, 17.540, ""],
                    [3, 18.421, ""],
                    [4, 19.366, ""],
                    [5, 20.271, ""],
                    [6, 21.228, ""],
                ],
                (
                    "请选择同一种条纹记录：亮纹的有效级次 q 填整数 0、±1、±2……；"
                    "暗纹填半整数 ±0.5、±1.5、±2.5……。不要在同一组数据中混用整数和半整数。"
                    "屏距 L 和标称中心间距 d₀ 请在页面顶部的实验参数区填写。"
                ),
                "🧮 计算双缝中心间距",
                chart=double_chart,
                readonly=(2,),
            ),
            _table(
                "spring",
                "模块三：衍射法测量弹簧参数",
                [
                    "较宽条纹间距 Δxw/mm",
                    "较窄条纹间距 Δxn/mm",
                    "细丝直径估计 d/mm",
                    "弹簧螺距估计 p/mm",
                ],
                [
                    [0.860, 0.075, "", ""],
                    [0.874, 0.079, "", ""],
                    [0.817, 0.057, "", ""],
                    [0.813, 0.053, "", ""],
                    [0.808, 0.071, "", ""],
                ],
                (
                    "分别重复测量较宽和较窄衍射条纹的间距。较宽条纹用于计算弹簧细丝直径，"
                    "较窄条纹用于计算弹簧螺距；屏距 L 请在页面顶部的实验参数区填写。"
                    "本模块只计算，不作图。"
                ),
                "🧮 计算弹簧参数",
                readonly=(2, 3),
            ),
        ],
        parameters=[
            {
                "id": "single_L_mm",
                "label": "单缝实验屏距 L",
                "unit": "mm",
                "type": "number",
                "default": 212.0,
                "min": 0,
                "step": "any",
                "required": True,
            },
            {
                "id": "single_a0_um",
                "label": "单缝标称宽度 a₀",
                "unit": "μm",
                "type": "number",
                "default": 100.0,
                "min": 0,
                "step": "any",
                "required": True,
            },
            {
                "id": "double_L_mm",
                "label": "双缝实验屏距 L",
                "unit": "mm",
                "type": "number",
                "default": 212.0,
                "min": 0,
                "step": "any",
                "required": True,
            },
            {
                "id": "double_d0_um",
                "label": "双缝标称中心间距 d₀",
                "unit": "μm",
                "type": "number",
                "default": 150.0,
                "min": 0,
                "step": "any",
                "required": True,
            },
            {
                "id": "spring_L_mm",
                "label": "弹簧实验屏距 L",
                "unit": "mm",
                "type": "number",
                "default": 264.5,
                "min": 0,
                "step": "any",
                "required": True,
            },
        ],
        analysis_hints=(
            "单缝和双缝应检查条纹位置与级次的线性关系、拟合截距和 R²；"
            "弹簧模块应检查重复测量的离散程度以及宽、窄条纹是否填反。"
        ),
        preview_enabled=True,
        revision=7,
        formulas=_GLOBAL_FORMULAS,
        variables=_GLOBAL_VARIABLES,
        table_theory=_TABLE_THEORY,
    )


_TABLE_COLUMNS = {
    "single_slit": ("c0", "c1"),
    "double_slit": ("c0", "c1"),
    "spring": ("c0", "c1"),
}

_TABLE_LABELS = {
    "single_slit": "单缝缝宽测量",
    "double_slit": "双缝中心间距测量",
    "spring": "弹簧参数测量",
}


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _meaningful_rows(rows: list[dict[str, Any]], table_id: str) -> list[dict[str, Any]]:
    columns = _TABLE_COLUMNS[table_id]
    return [row for row in rows if any(_has_value(row.get(column)) for column in columns)]


def _parameter_value(
    parameters: dict[str, Any],
    parameter_id: str,
    label: str,
) -> tuple[float | None, str | None]:
    value = as_number(parameters.get(parameter_id))
    if value is None:
        return None, f"请填写{label}"
    if value <= 0:
        return None, f"{label}必须大于 0"
    return float(value), None


def _point_values(
    rows: list[dict[str, Any]],
    x_column: str,
    y_column: str,
    x_label: str,
    y_label: str,
) -> tuple[list[float], list[float], str | None]:
    x_values = []
    y_values = []
    for index, row in enumerate(rows, start=1):
        raw_x = row.get(x_column)
        raw_y = row.get(y_column)
        if not _has_value(raw_x) and not _has_value(raw_y):
            continue
        if not _has_value(raw_x) or not _has_value(raw_y):
            return [], [], f"第 {index} 行的{x_label}和{y_label}必须同时填写"
        x_value = as_number(raw_x)
        y_value = as_number(raw_y)
        if x_value is None or y_value is None:
            return [], [], f"第 {index} 行的{x_label}和{y_label}必须填写数字"
        x_values.append(float(x_value))
        y_values.append(float(y_value))
    return x_values, y_values, None


def _linear_fit(x_values: list[float], y_values: list[float]) -> tuple[float, float, float]:
    count = len(x_values)
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    denominator = sum((value - mean_x) ** 2 for value in x_values)
    if denominator <= 0:
        raise ValueError("横坐标不能全部相同")

    slope = sum(
        (x_value - mean_x) * (y_value - mean_y)
        for x_value, y_value in zip(x_values, y_values)
    ) / denominator
    intercept = mean_y - slope * mean_x
    fitted = [intercept + slope * value for value in x_values]
    residual_sum = sum((value - predicted) ** 2 for value, predicted in zip(y_values, fitted))
    total_sum = sum((value - mean_y) ** 2 for value in y_values)
    r_squared = 1.0 if total_sum <= 0 and residual_sum <= 0 else (
        0.0 if total_sum <= 0 else 1.0 - residual_sum / total_sum
    )
    return slope, intercept, r_squared


def _single_slit_result(
    rows: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    screen_distance, error = _parameter_value(parameters, "single_L_mm", "单缝屏距 L")
    if error:
        return None, error
    reference_width, error = _parameter_value(parameters, "single_a0_um", "单缝标称宽度 a₀")
    if error:
        return None, error

    orders, positions, error = _point_values(rows, "c0", "c1", "暗条纹级次 k", "条纹位置 x")
    if error:
        return None, error
    if len(orders) < 3:
        return None, "单缝缝宽测量至少需要 3 组条纹位置数据"
    if any(abs(order - round(order)) > 1e-9 for order in orders):
        return None, "单缝暗条纹级次 k 必须为整数"
    if not any(abs(order) <= 1e-9 for order in orders):
        return None, "单缝数据必须包含级次 k=0 的中央主极大位置"

    try:
        slope, intercept, r_squared = _linear_fit(orders, positions)
    except ValueError as exc:
        return None, str(exc)
    if abs(slope) <= 1e-12:
        return None, "单缝拟合斜率为 0，无法计算缝宽"

    width_mm = float(screen_distance) * _WAVELENGTH_MM / abs(slope)
    width_um = width_mm * 1000.0
    relative_error = abs(width_um - float(reference_width)) / float(reference_width) * 100.0
    return {
        "fit": {"slope": slope, "intercept": intercept},
        "lines": [
            f"He-Ne 激光波长 λ = {_WAVELENGTH_NM:.1f} nm",
            f"线性拟合：x = {intercept:.6f} + ({slope:.6f})k mm",
            f"拟合斜率 sₐ = {slope:.6f} mm，截距 x₀ = {intercept:.6f} mm",
            f"决定系数 R² = {r_squared:.6f}",
            f"单缝宽度 a = {width_mm:.6f} mm = {width_um:.3f} μm",
            f"标称宽度 a₀ = {float(reference_width):.3f} μm",
            f"相对误差 Eₐ = {relative_error:.3f}%",
        ]
    }, None


def _double_slit_result(
    rows: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    screen_distance, error = _parameter_value(parameters, "double_L_mm", "双缝屏距 L")
    if error:
        return None, error
    reference_distance, error = _parameter_value(parameters, "double_d0_um", "双缝标称中心间距 d₀")
    if error:
        return None, error

    orders, positions, error = _point_values(rows, "c0", "c1", "有效级次 q", "条纹位置 x")
    if error:
        return None, error
    if len(orders) < 3:
        return None, "双缝中心间距测量至少需要 3 组条纹位置数据"

    doubled_orders = [round(order * 2) for order in orders]
    if any(abs(order * 2 - doubled) > 1e-9 for order, doubled in zip(orders, doubled_orders)):
        return None, "双缝有效级次 q 必须为整数或半整数"
    parity = {abs(doubled) % 2 for doubled in doubled_orders}
    if len(parity) > 1:
        return None, "同一组双缝数据不能混用亮纹整数级次和暗纹半整数级次"

    try:
        slope, intercept, r_squared = _linear_fit(orders, positions)
    except ValueError as exc:
        return None, str(exc)
    if abs(slope) <= 1e-12:
        return None, "双缝拟合斜率为 0，无法计算中心间距"

    distance_mm = float(screen_distance) * _WAVELENGTH_MM / abs(slope)
    distance_um = distance_mm * 1000.0
    relative_error = (
        abs(distance_um - float(reference_distance)) / float(reference_distance) * 100.0
    )
    fringe_type = "亮条纹（整数级次）" if parity == {0} else "暗条纹（半整数级次）"
    return {
        "fit": {"slope": slope, "intercept": intercept},
        "lines": [
            f"本组采用：{fringe_type}",
            f"He-Ne 激光波长 λ = {_WAVELENGTH_NM:.1f} nm",
            f"线性拟合：x = {intercept:.6f} + ({slope:.6f})q mm",
            f"拟合斜率 s_d = {slope:.6f} mm，截距 x₀ = {intercept:.6f} mm",
            f"决定系数 R² = {r_squared:.6f}",
            f"双缝中心间距 d = {distance_mm:.6f} mm = {distance_um:.3f} μm",
            f"标称中心间距 d₀ = {float(reference_distance):.3f} μm",
            f"相对误差 E_d = {relative_error:.3f}%",
        ]
    }, None


def _spring_result(
    rows: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    screen_distance, error = _parameter_value(parameters, "spring_L_mm", "弹簧屏距 L")
    if error:
        return None, error
    wide_values, narrow_values, error = _point_values(
        rows,
        "c0",
        "c1",
        "较宽条纹间距 Δxw",
        "较窄条纹间距 Δxn",
    )
    if error:
        return None, error
    if len(wide_values) < 3:
        return None, "弹簧参数测量至少需要 3 组宽、窄条纹间距数据"
    if any(value <= 0 for value in wide_values + narrow_values):
        return None, "弹簧的宽、窄条纹间距必须大于 0"

    mean_wide = sum(wide_values) / len(wide_values)
    mean_narrow = sum(narrow_values) / len(narrow_values)
    wire_diameter_mm = float(screen_distance) * _WAVELENGTH_MM / mean_wide
    pitch_mm = float(screen_distance) * _WAVELENGTH_MM / mean_narrow
    return {
        "screen_distance_mm": float(screen_distance),
        "lines": [
            f"He-Ne 激光波长 λ = {_WAVELENGTH_NM:.1f} nm",
            f"较宽条纹平均间距 Δx̄w = {mean_wide:.6f} mm",
            f"较窄条纹平均间距 Δx̄n = {mean_narrow:.6f} mm",
            f"弹簧细丝直径 d_wire = {wire_diameter_mm:.6f} mm = {wire_diameter_mm * 1000.0:.3f} μm",
            f"弹簧螺距 p = {pitch_mm:.6f} mm = {pitch_mm * 1000.0:.3f} μm",
        ]
    }, None


_CALCULATORS = {
    "single_slit": _single_slit_result,
    "double_slit": _double_slit_result,
    "spring": _spring_result,
}


def _fill_computed_columns(
    table_id: str,
    rows: list[dict[str, Any]],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    """将逐行派生量填入最右侧只读列，正式汇总结果仍按整组数据计算。"""
    cleaned = [dict(row) for row in rows]
    if table_id in ("single_slit", "double_slit"):
        fit = result["fit"]
        for row in cleaned:
            order = as_number(row.get("c0"))
            position = as_number(row.get("c1"))
            row["c2"] = (
                f"{fit['intercept'] + fit['slope'] * order:.6f}"
                if order is not None and position is not None else ""
            )
    elif table_id == "spring":
        screen_distance = result["screen_distance_mm"]
        for row in cleaned:
            wide = as_number(row.get("c0"))
            narrow = as_number(row.get("c1"))
            row["c2"] = (
                f"{screen_distance * _WAVELENGTH_MM / wide:.6f}"
                if wide is not None and wide > 0 else ""
            )
            row["c3"] = (
                f"{screen_distance * _WAVELENGTH_MM / narrow:.6f}"
                if narrow is not None and narrow > 0 else ""
            )
    return cleaned


def preview(payload):
    """分别预览已填写模块；生成完整报告时仍要求三个模块全部完成。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results: dict[str, dict[str, Any]] = {}
    calc_messages: list[str] = []

    for table_id, calculator in _CALCULATORS.items():
        rows = _meaningful_rows(tables.get(table_id, []) or [], table_id)
        if not rows:
            continue
        result, error = calculator(rows, parameters)
        if error:
            calc_messages.append(f"{_TABLE_LABELS[table_id]}：{error}")
        elif result is not None:
            calc_results[table_id] = result
            tables[table_id] = _fill_computed_columns(
                table_id,
                tables.get(table_id, []) or [],
                result,
            )

    return {
        "tables": tables,
        "calc_results": calc_results,
        "calc_messages": calc_messages,
    }


def handle_structured(workpath, payload):
    submitted = payload.get("tables") or {}
    active_rows = {
        table_id: _meaningful_rows(submitted.get(table_id, []) or [], table_id)
        for table_id in _CALCULATORS
    }
    required_ids = list(_CALCULATORS)
    missing_ids = [table_id for table_id in required_ids if not active_rows[table_id]]
    if missing_ids:
        missing_labels = "、".join(_TABLE_LABELS[table_id] for table_id in missing_ids)
        return {
            "code": 1,
            "message": f"以下必做模块尚未填写：{missing_labels}。",
        }

    result = preview(payload)
    invalid_ids = [table_id for table_id in required_ids if table_id not in result["calc_results"]]
    if invalid_ids:
        message = "；".join(result["calc_messages"]) or "实验数据未通过计算校验。"
        return {"code": 1, "message": message}

    current_schema = schema()
    table_schemas = {table["id"]: table for table in current_schema["tables"]}
    charts = []
    for table_id, filename in (
        ("single_slit", "single_slit_fit.png"),
        ("double_slit", "double_slit_fit.png"),
    ):
        table_schema = table_schemas[table_id]
        charts.append(
            make_chart_from_table(
                table_schema,
                active_rows[table_id],
                table_schema["chart"],
                workpath,
                chart_filename=filename,
            )
        )

    enriched = dict(payload)
    enriched["tables"] = {
        table_id: _meaningful_rows(result["tables"].get(table_id, []) or [], table_id)
        for table_id in required_ids
    }
    summary = []
    for table_id in required_ids:
        summary.append(f"【{_TABLE_LABELS[table_id]}】")
        summary.extend(result["calc_results"][table_id]["lines"])

    return structured_result(
        workpath,
        name(),
        current_schema,
        enriched,
        summary=summary,
        charts=charts,
    )


def handle(workpath, extension):
    """保留旧插件入口；本实验使用新版多表格结构化接口。"""
    return 1
