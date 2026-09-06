from copy import deepcopy

from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *


def name():
    return "迈氏干涉仪"


_WAVELENGTH_SAMPLE = [
    {"measurement_no": index, "position_mm": position}
    for index, position in enumerate(
        [10.01582, 10.03166, 10.04745, 10.06330, 10.07908, 10.09494, 10.11073, 10.12658],
        1,
    )
]

_FILM_SAMPLE = [
    {"measurement_no": 1, "without_mm": 12.500, "with_mm": 12.578, "thickness_reading_mm": 0.152},
    {"measurement_no": 2, "without_mm": 12.496, "with_mm": 12.574, "thickness_reading_mm": 0.151},
    {"measurement_no": 3, "without_mm": 12.503, "with_mm": 12.581, "thickness_reading_mm": 0.153},
]


def schema():
    return {
        "schema_version": 2,
        "schema_revision": 3,
        "preview_enabled": True,
        "report_enabled": False,
        "description": (
            "本实验使用迈克耳孙干涉仪测量氦氖激光波长：基础内容按指导书记录 8 次 "
            r"$M_1$" " 镜位置（相邻两次之间固定数过若干条纹），由位置—测量序号"
            "拟合得到激光波长及拟合标准差；提升内容用 3 次位置与薄片厚度测量"
            "计算透明薄片折射率。两个模块都不要求作图。"
        ),
        "parameters": [
            {
                "id": "fringes_per_interval", "label": "相邻两次测量的条纹数", "type": "number",
                "default": 50, "required": True, "step": "1",
                "help": "指导书记录表按每次连续数50条条纹设计，8次共覆盖400条。",
            },
            {
                "id": "micrometer_zero_mm", "label": "千分尺零点", "unit": "mm", "type": "number",
                "default": 0, "required": False, "step": "0.001",
                "help": "仅用于薄片厚度修正；若仪器无零点误差可填0。",
            },
        ],
        "tables": [
            {
                "id": "wavelength", "title": "表1  He-Ne激光波长测量", "required": True,
                "min_rows": 8, "initial_rows": 8,
                "description": "依次记录8个M₁镜位置；相邻位置差由网页自动计算。",
                "columns": [
                    {"id": "measurement_no", "label": "测量序号", "type": "number", "readonly": True},
                    {"id": "position_mm", "label": "镜位置 Sₙ", "unit": "mm"},
                    {"id": "adjacent_difference_um", "label": "相邻位置差", "unit": "μm", "readonly": True},
                ],
                "sample": deepcopy(_WAVELENGTH_SAMPLE),
            },
            {
                "id": "film", "title": "表2  透明薄片折射率（三次测量）", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "description": "无样品与加样品位置、薄片厚度各测量3次；移动距离和零点修正厚度自动显示。",
                "columns": [
                    {"id": "measurement_no", "label": "次数", "type": "number", "readonly": True},
                    {"id": "without_mm", "label": "无样品时镜位置 S₀", "unit": "mm"},
                    {"id": "with_mm", "label": "加样品时镜位置 S₁", "unit": "mm"},
                    {"id": "mirror_move_mm", "label": "镜移动距离 d", "unit": "mm", "readonly": True},
                    {"id": "thickness_reading_mm", "label": "薄片厚度读数", "unit": "mm"},
                    {"id": "corrected_thickness_mm", "label": "零点修正厚度 l", "unit": "mm", "readonly": True},
                ],
                "sample": deepcopy(_FILM_SAMPLE),
            },
        ],
        "formulas": get_formulas("exp35"),
        "variables": get_variables("exp35"),
        "table_theory": get_table_theory("exp35"),
    }


def _optional_number(row, key):
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def preview(payload):
    tables = deepcopy(payload.get("tables") or {})
    zero_mm = get_parameter(payload, "micrometer_zero_mm", 0.0, False)

    previous_position = None
    for index, row in enumerate(tables.get("wavelength", []) or [], 1):
        row["measurement_no"] = index
        position = _optional_number(row, "position_mm")
        if position is None or previous_position is None:
            row["adjacent_difference_um"] = ""
        else:
            row["adjacent_difference_um"] = f"{(position - previous_position) * 1000.0:.4f}"
        if position is not None:
            previous_position = position

    for index, row in enumerate(tables.get("film", []) or [], 1):
        row["measurement_no"] = index
        without = _optional_number(row, "without_mm")
        with_sample = _optional_number(row, "with_mm")
        thickness = _optional_number(row, "thickness_reading_mm")
        row["mirror_move_mm"] = (
            "" if without is None or with_sample is None else f"{abs(with_sample - without):.6f}"
        )
        row["corrected_thickness_mm"] = (
            "" if thickness is None else f"{abs(thickness - zero_mm):.6f}"
        )
    return {"tables": tables}


def handle_structured(workpath, payload):
    try:
        wave_rows = get_rows(payload, "wavelength", required=True, min_rows=8)
        film_rows = get_rows(payload, "film", required=True, min_rows=3)
        fringes_per_interval = get_parameter(payload, "fringes_per_interval", 50.0, True)
        zero_mm = get_parameter(payload, "micrometer_zero_mm", 0.0, False)
        if fringes_per_interval <= 0:
            raise OpticsInputError("相邻两次测量的条纹数必须为正数")

        positions = numeric_column(wave_rows, "position_mm", "M₁镜位置")
        measurement_no = np.arange(1, len(positions) + 1, dtype=float)
        fit = linear_fit(measurement_no, positions)
        wavelength_nm = abs(2.0 * fit["slope"] * 1e6 / fringes_per_interval)
        wavelength_std_nm = 2.0 * fit["slope_stderr"] * 1e6 / fringes_per_interval
        adjacent_difference_um = np.insert(np.diff(positions) * 1000.0, 0, np.nan)

        without = numeric_column(film_rows, "without_mm", "无样品位置")
        with_sample = numeric_column(film_rows, "with_mm", "加样品位置")
        thickness_reading = numeric_column(film_rows, "thickness_reading_mm", "薄片厚度读数")
        mirror_move = np.abs(with_sample - without)
        thickness = np.abs(thickness_reading - zero_mm)
        if np.any(thickness <= 0):
            raise OpticsInputError("零点修正后的薄片厚度必须大于0")
        mean_move = float(np.mean(mirror_move))
        mean_thickness = float(np.mean(thickness))
        refractive_index = 1.0 + mean_move / mean_thickness

        warnings = []
        if len(wave_rows) != 8:
            warnings.append(f"指导书记录表要求8次位置读数；当前输入了{len(wave_rows)}次。")
        if len(film_rows) != 3:
            warnings.append(f"指导书要求薄片位置和厚度各测量3次；当前输入了{len(film_rows)}次。")
        if not (350 <= wavelength_nm <= 850):
            warnings.append("计算得到的波长超出常见可见光范围，请检查鼓轮方向、单位和条纹计数。")

        summary = [
            f"位置—序号拟合：Sₙ = ({fit['slope']:.9f} mm)n + {fit['intercept']:.6f} mm",
            f"相关系数 r = {fit['r']:.6f}，R² = {fit['r2']:.6f}",
            f"He-Ne激光波长 λ = {wavelength_nm:.3f} nm，拟合标准差 u(λ) = {wavelength_std_nm:.3f} nm",
            f"M₁镜平均移动距离 d̄ = {mean_move:.6f} mm",
            f"薄片平均厚度 l̄ = {mean_thickness:.6f} mm",
            f"薄片折射率 n = 1 + d̄/l̄ = {refractive_index:.5f}",
        ]

        doc = create_document(name())
        wave_table = []
        for index, position in enumerate(positions):
            diff_text = "—" if index == 0 else f"{adjacent_difference_um[index]:.4f}"
            wave_table.append([index + 1, f"{position:.6f}", diff_text])
        add_table(doc, "表1  He-Ne激光波长测量", ["序号", "Sₙ/mm", "相邻位置差/μm"], wave_table)

        film_table = []
        for index in range(len(film_rows)):
            film_table.append([
                index + 1, f"{without[index]:.6f}", f"{with_sample[index]:.6f}",
                f"{mirror_move[index]:.6f}", f"{thickness_reading[index]:.6f}", f"{thickness[index]:.6f}",
            ])
        add_table(doc, "表2  透明薄片折射率", [
            "次数", "无样品位置/mm", "加样品位置/mm", "d/mm", "测厚读数/mm", "零修正厚度/mm"
        ], film_table)
        add_key_values(doc, "测量设置", [
            ("相邻两次条纹数", f"{fringes_per_interval:g}"),
            ("千分尺零点", f"{zero_mm:.6f} mm"),
        ])
        add_summary(doc, summary)
        return finish_report(doc, workpath, name(), summary, charts=[], warnings=warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
