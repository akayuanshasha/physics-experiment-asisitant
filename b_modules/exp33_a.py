"""对切透镜的光学实验1：比列（Billet）对切透镜。

依据实验指导，B 类课程必须同时完成基础内容（光源距透镜 ``f``）和
提升内容（光源距透镜 ``1.5f``）。两部分均测量三次，每次改变成像
透镜或屏的位置，并由成像关系还原原始条纹间距，最后只报告切去宽度
``a`` 的平均值。
"""

from copy import deepcopy

import numpy as np

from optics_common import (
    OpticsInputError,
    add_key_values,
    add_summary,
    add_table,
    create_document,
    error_result,
    finish_report,
    get_parameter,
    get_rows,
)


_TABLE_IDS = ("billet_basic", "billet_enhanced")


def name():
    return "对切透镜的光学实验1"


def _columns():
    return [
        {"id": "span_mm", "label": "放大后多周期总长度 S", "unit": "mm", "type": "number"},
        {"id": "periods", "label": "条纹间隔数 N", "type": "number"},
        {
            "id": "lens_distance_cm",
            "label": "比列透镜至成像透镜距离 p",
            "unit": "cm",
            "type": "number",
        },
        {
            "id": "screen_distance_cm",
            "label": "成像透镜至屏距离 q",
            "unit": "cm",
            "type": "number",
        },
        {
            "id": "original_spacing_mm",
            "label": "原始条纹间距 Δx",
            "unit": "mm",
            "type": "number",
            "readonly": True,
        },
        {
            "id": "cut_width_mm",
            "label": "切去部分宽度 a",
            "unit": "mm",
            "type": "number",
            "readonly": True,
        },
    ]


_BASIC_SAMPLE = [
    {"span_mm": 12.656, "periods": 20, "lens_distance_cm": 7.0, "screen_distance_cm": 14.0},
    {"span_mm": 16.875, "periods": 20, "lens_distance_cm": 8.0, "screen_distance_cm": 17.5},
    {"span_mm": 29.531, "periods": 20, "lens_distance_cm": 9.0, "screen_distance_cm": 28.0},
]

_ENHANCED_SAMPLE = [
    {"span_mm": 11.670, "periods": 20, "lens_distance_cm": 7.0, "screen_distance_cm": 14.0},
    {"span_mm": 14.834, "periods": 20, "lens_distance_cm": 8.0, "screen_distance_cm": 17.5},
    {"span_mm": 24.609, "periods": 20, "lens_distance_cm": 9.0, "screen_distance_cm": 28.0},
]


def _table(table_id, title, description, sample):
    return {
        "id": table_id,
        "title": title,
        "description": description,
        "required": True,
        "min_rows": 3,
        "initial_rows": 3,
        "columns": _columns(),
        "sample": deepcopy(sample),
    }


_VARIABLES = [
    {"symbol": "S", "description": "光屏上测得的多周期条纹总长度", "unit": "mm"},
    {"symbol": "N", "description": "总长度 S 所包含的完整条纹间隔数", "unit": "无单位"},
    {"symbol": "p", "description": "比列对切透镜到成像透镜的距离", "unit": "cm"},
    {"symbol": "q", "description": "成像透镜到光屏的距离", "unit": "cm"},
    {"symbol": "u", "description": "原始干涉条纹面到成像透镜的物距", "unit": "cm"},
    {"symbol": "M", "description": "成像透镜对条纹的线放大率，M=q/u", "unit": "无单位"},
    {"symbol": r"\Delta x", "description": "还原后的原始干涉条纹间距", "unit": "mm"},
    {"symbol": "a", "description": "比列对切透镜中间切去部分的宽度", "unit": "mm"},
]

_IMAGING_STEPS = [
    {"note": "由成像透镜焦距 f₁ 和像距 q 求原始条纹面的物距：", "formula": r"u=\frac{f_1q}{q-f_1}"},
    {"note": "成像放大率：", "formula": r"M=\frac{q}{u}"},
    {"note": "由多周期测量值还原原始条纹间距：", "formula": r"\Delta x=\frac{S/N}{M}"},
]

_TABLE_THEORY = {
    "billet_basic": {
        "formulas": [{
            "title": "基础内容：光源距离为 f",
            "steps": _IMAGING_STEPS + [
                {"note": "按实验指导公式(7)计算切去宽度：", "formula": r"a=\frac{f\lambda}{\Delta x}"},
            ],
        }],
        "variables": _VARIABLES,
    },
    "billet_enhanced": {
        "formulas": [{
            "title": "提升内容：光源距离为 L=1.5f",
            "steps": _IMAGING_STEPS + [
                {"note": "原始条纹面到比列透镜的距离：", "formula": r"D=p-u"},
                {
                    "note": "由实验指导公式(2)变形计算切去宽度：",
                    "formula": r"a=\frac{(fL-DL+Df)\lambda}{L\Delta x}",
                },
            ],
        }],
        "variables": _VARIABLES + [
            {"symbol": "L", "description": "等效点光源到比列透镜的距离，本表取 1.5f", "unit": "mm"},
            {"symbol": "D", "description": "比列透镜到原始干涉条纹面的距离，D=p-u", "unit": "mm"},
        ],
    },
}


def schema():
    return {
        "schema_version": 2,
        "schema_revision": 4,
        "draft_enabled": True,
        "preview_enabled": True,
        "report_enabled": True,
        "description": (
            "实验 1 的基础内容和提升内容均为 B 类必做项目。请分别完成两个表格，"
            "每个表格严格记录 3 次测量；每次改变成像透镜或屏的位置。系统将根据"
            "成像关系还原原始条纹间距，并分别计算切去宽度 " r"$a$" " 及其平均值。"
        ),
        "parameters": [
            {
                "id": "wavelength_nm",
                "label": "He-Ne激光波长 λ",
                "unit": "nm",
                "type": "number",
                "default": 632.8,
                "required": True,
                "step": "0.1",
            },
            {
                "id": "cut_focal_cm",
                "label": "比列对切透镜实测焦距 f",
                "unit": "cm",
                "type": "number",
                "default": 10,
                "required": True,
                "step": "1",
                "help": "用汇聚法测量，按实验指导保留到1 cm。",
            },
            {
                "id": "imaging_focal_cm",
                "label": "成像透镜焦距 f₁",
                "unit": "cm",
                "type": "number",
                "default": 3.5,
                "required": True,
                "step": "0.1",
            },
        ],
        "tables": [
            _table(
                "billet_basic",
                "基础内容：光源与比列透镜距离为 f",
                "测量放大后的多个完整条纹间隔；共测3次，每次改变成像透镜或屏的位置。",
                _BASIC_SAMPLE,
            ),
            _table(
                "billet_enhanced",
                "提升内容：光源与比列透镜距离为 1.5f",
                "保持多周期测量方法；共测3次，每次改变成像透镜或屏的位置。",
                _ENHANCED_SAMPLE,
            ),
        ],
        "formulas": [],
        "variables": [],
        "table_theory": deepcopy(_TABLE_THEORY),
        "analysis_hints": (
            "同一部分三次测得的a应基本一致。若离散明显，优先检查条纹间隔数N、"
            "p/q距离定义以及屏上总长度是否覆盖了完整周期。"
        ),
    }


def _number(row, key, label, *, allow_incomplete=False):
    raw = row.get(key, "")
    if raw is None or str(raw).strip() == "":
        if allow_incomplete:
            return None
        raise OpticsInputError(f"{label}不能为空")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise OpticsInputError(f"{label}不是有效数字：{raw}") from exc
    if not np.isfinite(value):
        raise OpticsInputError(f"{label}必须是有限数字")
    return value


def _calculate_row(row, parameters, enhanced, *, allow_incomplete=False):
    span_mm = _number(row, "span_mm", "多周期总长度S", allow_incomplete=allow_incomplete)
    periods = _number(row, "periods", "条纹间隔数N", allow_incomplete=allow_incomplete)
    p_cm = _number(row, "lens_distance_cm", "比列透镜至成像透镜距离p", allow_incomplete=allow_incomplete)
    q_cm = _number(row, "screen_distance_cm", "成像透镜至屏距离q", allow_incomplete=allow_incomplete)
    if any(value is None for value in (span_mm, periods, p_cm, q_cm)):
        return None
    if span_mm <= 0 or periods <= 0 or p_cm <= 0 or q_cm <= 0:
        raise OpticsInputError("总长度、间隔数以及p、q距离都必须为正数")

    wavelength_nm, focal_cm, imaging_focal_cm = parameters
    if q_cm <= imaging_focal_cm:
        raise OpticsInputError("成像透镜到屏的距离q必须大于成像透镜焦距f₁")

    # 成像透镜把其前方的原始干涉条纹面放大成像到屏上。
    object_distance_cm = imaging_focal_cm * q_cm / (q_cm - imaging_focal_cm)
    if p_cm <= object_distance_cm:
        raise OpticsInputError("距离p必须大于原始条纹面到成像透镜的物距u，请核对p、q定义")
    magnification = q_cm / object_distance_cm
    original_spacing_mm = (span_mm / periods) / magnification

    focal_mm = focal_cm * 10.0
    wavelength_mm = wavelength_nm * 1e-6
    fringe_plane_distance_mm = (p_cm - object_distance_cm) * 10.0
    if enhanced:
        source_distance_mm = 1.5 * focal_mm
        numerator = (
            focal_mm * source_distance_mm
            - fringe_plane_distance_mm * source_distance_mm
            + fringe_plane_distance_mm * focal_mm
        )
        if numerator <= 0:
            raise OpticsInputError("当前几何距离使公式(2)的有效传播因子不为正，请核对p、q和焦距")
        cut_width_mm = numerator * wavelength_mm / (source_distance_mm * original_spacing_mm)
    else:
        cut_width_mm = focal_mm * wavelength_mm / original_spacing_mm

    return {
        "span_mm": span_mm,
        "periods": periods,
        "p_cm": p_cm,
        "q_cm": q_cm,
        "u_cm": object_distance_cm,
        "magnification": magnification,
        "fringe_plane_distance_mm": fringe_plane_distance_mm,
        "original_spacing_mm": original_spacing_mm,
        "cut_width_mm": cut_width_mm,
    }


def _parameters(payload, *, required):
    wavelength_nm = get_parameter(payload, "wavelength_nm", 632.8, required)
    focal_cm = get_parameter(payload, "cut_focal_cm", 10.0, required)
    imaging_focal_cm = get_parameter(payload, "imaging_focal_cm", 3.5, required)
    if wavelength_nm <= 0 or focal_cm <= 0 or imaging_focal_cm <= 0:
        raise OpticsInputError("波长和两个焦距都必须为正数")
    return wavelength_nm, focal_cm, imaging_focal_cm


def preview(payload):
    parameters = _parameters(payload, required=False)
    tables = deepcopy(payload.get("tables") or {})
    for table_id, enhanced in (("billet_basic", False), ("billet_enhanced", True)):
        for row in tables.get(table_id, []) or []:
            result = _calculate_row(row, parameters, enhanced, allow_incomplete=True)
            row["original_spacing_mm"] = "" if result is None else f"{result['original_spacing_mm']:.6f}"
            row["cut_width_mm"] = "" if result is None else f"{result['cut_width_mm']:.6f}"
    return {"tables": tables}


def _complete_dataset(payload, table_id, enhanced, parameters):
    rows = get_rows(payload, table_id, required=True, min_rows=3)
    if len(rows) != 3:
        raise OpticsInputError(f"数据表“{table_id}”按实验指导必须恰好填写3行有效数据")
    return [_calculate_row(row, parameters, enhanced) for row in rows]


def _report_rows(results):
    return [
        [
            index,
            f"{item['span_mm']:.4f}",
            f"{item['periods']:.0f}",
            f"{item['p_cm']:.3f}",
            f"{item['q_cm']:.3f}",
            f"{item['u_cm']:.4f}",
            f"{item['magnification']:.4f}",
            f"{item['fringe_plane_distance_mm']:.4f}",
            f"{item['original_spacing_mm']:.6f}",
            f"{item['cut_width_mm']:.6f}",
        ]
        for index, item in enumerate(results, 1)
    ]


def handle_structured(workpath, payload):
    try:
        parameters = _parameters(payload, required=True)
        basic = _complete_dataset(payload, "billet_basic", False, parameters)
        enhanced = _complete_dataset(payload, "billet_enhanced", True, parameters)
        basic_mean = float(np.mean([item["cut_width_mm"] for item in basic]))
        enhanced_mean = float(np.mean([item["cut_width_mm"] for item in enhanced]))

        summary = [
            f"基础内容（光源距离f）：切去宽度平均值 ā = {basic_mean:.6f} mm",
            f"提升内容（光源距离1.5f）：切去宽度平均值 ā = {enhanced_mean:.6f} mm",
        ]
        document = create_document(name(), "比列（Billet）对切透镜")
        add_key_values(document, "实验常量", [
            ("He-Ne激光波长 λ", f"{parameters[0]:.1f} nm"),
            ("比列对切透镜实测焦距 f", f"{parameters[1]:.1f} cm"),
            ("成像透镜焦距 f₁", f"{parameters[2]:.2f} cm"),
        ])
        headers = [
            "次数", "S/mm", "N", "p/cm", "q/cm", "u/cm", "M=q/u",
            "D/mm", "原始Δx/mm", "a/mm",
        ]
        add_table(document, "基础内容：光源距离为 f", headers, _report_rows(basic))
        add_table(document, "提升内容：光源距离为 1.5f", headers, _report_rows(enhanced))
        add_summary(document, summary)
        return finish_report(document, workpath, name(), summary)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    """保留旧入口；网页使用结构化多表接口。"""
    return 1
