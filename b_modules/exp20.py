"""透镜参数测量实验模块。

按照实验指导书的数据记录表，本模块实现四组固定结构的数据处理：

1. 凸透镜物像距法：物距测量一次，像距测量六次；
2. 凸透镜位移法：物像距离测量一次，透镜位移测量六次；
3. 凸透镜自准直法：焦距直接测量六次；
4. 凹透镜物像距法：借助凸透镜成像，像距测量三次。

本实验只需要计算焦距，不生成数据曲线。
"""

from __future__ import annotations

from typing import Any

from structured_support import (
    as_number,
    copied_tables,
    formatted,
    make_schema,
    make_table,
    structured_result,
)


def name():
    return "透镜参数测量"


_TABLE_THEORY = {
    "convex_object_image": {
        "formulas": [
            {
                "title": "凸透镜物像距法",
                "steps": [
                    {
                        "note": "像距测量六次并取平均：",
                        "formula": r"\bar v=\frac{1}{6}\sum_{i=1}^{6}v_i",
                    },
                    {
                        "note": "按物距和平均像距计算焦距：",
                        "formula": r"\frac{1}{f}=\frac{1}{u}+\frac{1}{\bar v},\qquad f=\frac{u\bar v}{u+\bar v}",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "u", "description": "凸透镜的物距，只测量一次", "unit": "mm"},
            {"symbol": "v_i", "description": "第 i 次测得的像距", "unit": "mm"},
            {"symbol": r"\bar v", "description": "六次像距的平均值", "unit": "mm"},
            {"symbol": "f", "description": "凸透镜焦距", "unit": "mm"},
        ],
    },
    "convex_displacement": {
        "formulas": [
            {
                "title": "凸透镜位移法",
                "steps": [
                    {
                        "note": "透镜位移测量六次并取平均：",
                        "formula": r"\bar l=\frac{1}{6}\sum_{i=1}^{6}l_i",
                    },
                    {
                        "note": "由物像距离和平均位移计算焦距：",
                        "formula": r"f=\frac{L^2-\bar l^2}{4L}",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "L", "description": "物体与像屏之间的固定距离", "unit": "mm"},
            {"symbol": "l_i", "description": "第 i 次测得的两个清晰成像位置之间的透镜位移", "unit": "mm"},
            {"symbol": r"\bar l", "description": "六次透镜位移的平均值", "unit": "mm"},
            {"symbol": "f", "description": "凸透镜焦距", "unit": "mm"},
        ],
    },
    "convex_autocollimation": {
        "formulas": [
            {
                "title": "凸透镜自准直法（平面镜法）",
                "steps": [
                    {
                        "note": "直接测得六次焦距并取平均：",
                        "formula": r"\bar f=\frac{1}{6}\sum_{i=1}^{6}f_i",
                    }
                ],
            }
        ],
        "variables": [
            {"symbol": "f_i", "description": "第 i 次自准直测得的凸透镜焦距", "unit": "mm"},
            {"symbol": r"\bar f", "description": "六次焦距的平均值", "unit": "mm"},
        ],
    },
    "concave_object_image": {
        "formulas": [
            {
                "title": "凹透镜物像距法（凸透镜辅助成像）",
                "steps": [
                    {
                        "note": "像距测量三次并取平均：",
                        "formula": r"\bar p'=\frac{1}{3}\sum_{i=1}^{3}p'_i",
                    },
                    {
                        "note": "使用实验指导书的符号规定计算凹透镜焦距：",
                        "formula": r"\frac{1}{f'}=\frac{1}{\bar p'}-\frac{1}{p},\qquad f'=\frac{p\bar p'}{p-\bar p'}",
                    },
                ],
            }
        ],
        "variables": [
            {"symbol": "p", "description": "凹透镜的物距；按指导书规定输入正值", "unit": "mm"},
            {"symbol": "p'_i", "description": "第 i 次测得的凹透镜像距；按指导书规定输入正值", "unit": "mm"},
            {"symbol": r"\bar p'", "description": "三次像距的平均值", "unit": "mm"},
            {"symbol": "f'", "description": "凹透镜的像方焦距，计算结果应为负值", "unit": "mm"},
        ],
    },
}


_GLOBAL_FORMULAS = [theory["formulas"][0] for theory in _TABLE_THEORY.values()]

_GLOBAL_VARIABLES = [
    {"symbol": r"u,\ v", "description": "凸透镜物距和像距", "unit": "mm"},
    {"symbol": r"L,\ l", "description": "位移法的物像距离和透镜位移", "unit": "mm"},
    {"symbol": r"p,\ p'", "description": "凹透镜物距和像距", "unit": "mm"},
    {"symbol": r"f,\ f'", "description": "凸透镜焦距和凹透镜像方焦距", "unit": "mm"},
]


def _table(
    table_id: str,
    title: str,
    labels: list[str],
    readonly: tuple[int, ...],
    sample: list[float],
    description: str,
    calc_label: str,
) -> dict[str, Any]:
    table = make_table(
        table_id,
        title,
        labels,
        sample=[sample],
        readonly=readonly,
        min_rows=1,
        initial_rows=1,
        description=description,
    )
    for column in table["columns"]:
        column["unit"] = "mm"
    table["calc"] = {"label": calc_label}
    return table


def schema():
    return make_schema(
        "按实验数据记录表完成凸透镜三种测焦距方法和凹透镜物像距法；所有距离统一使用 mm。",
        [
            _table(
                "convex_object_image",
                "凸透镜焦距 - 物像距法",
                [
                    "物距 u", "像距 v₁", "像距 v₂", "像距 v₃", "像距 v₄", "像距 v₅", "像距 v₆",
                    "平均像距 v̄", "焦距 f",
                ],
                (7, 8),
                [300.0, 149.5, 149.8, 150.0, 150.2, 150.4, 150.1],
                "物距测量一次，像距测量六次；平均像距和焦距由后端自动计算。",
                "🧮 计算物像距法焦距",
            ),
            _table(
                "convex_displacement",
                "凸透镜焦距 - 位移法",
                [
                    "物像距离 L", "透镜位移 l₁", "透镜位移 l₂", "透镜位移 l₃",
                    "透镜位移 l₄", "透镜位移 l₅", "透镜位移 l₆", "平均位移 l̄", "焦距 f",
                ],
                (7, 8),
                [500.0, 223.0, 223.2, 223.4, 223.8, 224.0, 224.2],
                "物体与像屏的距离测量一次，两个清晰成像位置之间的透镜位移测量六次。",
                "🧮 计算位移法焦距",
            ),
            _table(
                "convex_autocollimation",
                "凸透镜焦距 - 自准直法（平面镜法）",
                ["焦距 f₁", "焦距 f₂", "焦距 f₃", "焦距 f₄", "焦距 f₅", "焦距 f₆", "平均焦距 f̄"],
                (6,),
                [99.7, 99.9, 100.0, 100.1, 100.2, 100.1],
                "直接测量凸透镜焦距六次，平均焦距由后端自动计算。",
                "🧮 计算自准直法平均焦距",
            ),
            _table(
                "concave_object_image",
                "凹透镜焦距 - 物像距法",
                ["物距 p", "像距 p′₁", "像距 p′₂", "像距 p′₃", "平均像距 p̄′", "焦距 f′"],
                (4, 5),
                [50.0, 99.8, 100.0, 100.2],
                "利用凸透镜辅助成像，物距测量一次、像距测量三次；物距和像距均按指导书输入正值。",
                "🧮 计算凹透镜焦距",
            ),
        ],
        analysis_hints=(
            "检查六次或三次重复测量的离散程度、所有距离的单位是否统一，以及凹透镜焦距的符号。"
        ),
        preview_enabled=True,
        revision=4,
        formulas=_GLOBAL_FORMULAS,
        variables=_GLOBAL_VARIABLES,
        table_theory=_TABLE_THEORY,
    )


def _first_row(tables: dict[str, list[dict[str, Any]]], table_id: str) -> dict[str, Any] | None:
    rows = tables.get(table_id) or []
    return rows[0] if rows else None


def _numbers(row: dict[str, Any], keys: tuple[str, ...]) -> list[float] | None:
    values = [as_number(row.get(key)) for key in keys]
    if any(value is None for value in values):
        return None
    return [float(value) for value in values]


def _set_empty(row: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        row[key] = ""


def _result(lines: list[str]) -> dict[str, list[str]]:
    return {"lines": lines}


def preview(payload):
    """补全四张数据表中的平均值和焦距，并返回每表的计算摘要。"""
    tables = copied_tables(payload)
    calc_results: dict[str, dict[str, list[str]]] = {}
    calc_messages: list[str] = []

    row = _first_row(tables, "convex_object_image")
    if row is not None:
        values = _numbers(row, tuple(f"c{i}" for i in range(7)))
        _set_empty(row, ("c7", "c8"))
        if values is None:
            calc_messages.append("凸透镜物像距法需要填写1个物距和6个像距。")
        elif any(value <= 0 for value in values):
            calc_messages.append("凸透镜物像距法的物距和像距必须为正数。")
        else:
            object_distance, *image_distances = values
            mean_image = sum(image_distances) / len(image_distances)
            focal_length = object_distance * mean_image / (object_distance + mean_image)
            row["c7"] = formatted(mean_image, 3)
            row["c8"] = formatted(focal_length, 3)
            calc_results["convex_object_image"] = _result([
                f"平均像距 v̄ = {mean_image:.3f} mm",
                f"凸透镜焦距 f = {focal_length:.3f} mm",
            ])

    row = _first_row(tables, "convex_displacement")
    if row is not None:
        values = _numbers(row, tuple(f"c{i}" for i in range(7)))
        _set_empty(row, ("c7", "c8"))
        if values is None:
            calc_messages.append("凸透镜位移法需要填写1个物像距离和6个透镜位移。")
        elif any(value <= 0 for value in values):
            calc_messages.append("凸透镜位移法的物像距离和透镜位移必须为正数。")
        else:
            object_screen_distance, *displacements = values
            mean_displacement = sum(displacements) / len(displacements)
            if any(value >= object_screen_distance for value in displacements):
                calc_messages.append("位移法中每次透镜位移都必须小于物像距离 L。")
            else:
                focal_length = (
                    object_screen_distance ** 2 - mean_displacement ** 2
                ) / (4 * object_screen_distance)
                row["c7"] = formatted(mean_displacement, 3)
                row["c8"] = formatted(focal_length, 3)
                calc_results["convex_displacement"] = _result([
                    f"平均透镜位移 l̄ = {mean_displacement:.3f} mm",
                    f"凸透镜焦距 f = {focal_length:.3f} mm",
                ])

    row = _first_row(tables, "convex_autocollimation")
    if row is not None:
        values = _numbers(row, tuple(f"c{i}" for i in range(6)))
        _set_empty(row, ("c6",))
        if values is None:
            calc_messages.append("凸透镜自准直法需要填写6次直接测得的焦距。")
        elif any(value <= 0 for value in values):
            calc_messages.append("凸透镜自准直法测得的焦距必须为正数。")
        else:
            mean_focal_length = sum(values) / len(values)
            row["c6"] = formatted(mean_focal_length, 3)
            calc_results["convex_autocollimation"] = _result([
                f"自准直法平均焦距 f̄ = {mean_focal_length:.3f} mm",
            ])

    row = _first_row(tables, "concave_object_image")
    if row is not None:
        values = _numbers(row, tuple(f"c{i}" for i in range(4)))
        _set_empty(row, ("c4", "c5"))
        if values is None:
            calc_messages.append("凹透镜物像距法需要填写1个物距和3个像距。")
        elif any(value <= 0 for value in values):
            calc_messages.append("凹透镜物像距法的物距和像距必须按指导书输入正数。")
        else:
            object_distance, *image_distances = values
            mean_image = sum(image_distances) / len(image_distances)
            if mean_image <= object_distance:
                calc_messages.append(
                    "按指导书的正值符号规定，凹透镜平均像距应大于物距，计算所得焦距才为负值。"
                )
            else:
                focal_length = object_distance * mean_image / (object_distance - mean_image)
                row["c4"] = formatted(mean_image, 3)
                row["c5"] = formatted(focal_length, 3)
                calc_results["concave_object_image"] = _result([
                    f"平均像距 p̄′ = {mean_image:.3f} mm",
                    f"凹透镜焦距 f′ = {focal_length:.3f} mm",
                    f"凹透镜焦距大小 |f′| = {abs(focal_length):.3f} mm",
                ])

    return {
        "tables": tables,
        "calc_results": calc_results,
        "calc_messages": calc_messages,
    }


_REQUIRED_INPUTS = {
    "convex_object_image": 7,
    "convex_displacement": 7,
    "convex_autocollimation": 6,
    "concave_object_image": 4,
}

_TABLE_LABELS = {
    "convex_object_image": "凸透镜物像距法",
    "convex_displacement": "凸透镜位移法",
    "convex_autocollimation": "凸透镜自准直法",
    "concave_object_image": "凹透镜物像距法",
}


def handle_structured(workpath, payload):
    submitted = payload.get("tables") or {}
    errors = []
    for table_id, input_count in _REQUIRED_INPUTS.items():
        rows = submitted.get(table_id) or []
        if len(rows) != 1:
            errors.append(f"{_TABLE_LABELS[table_id]}必须填写且只能填写一行数据")
            continue
        if _numbers(rows[0], tuple(f"c{i}" for i in range(input_count))) is None:
            errors.append(f"{_TABLE_LABELS[table_id]}的测量数据尚未填写完整")
    if errors:
        return {"code": 1, "message": "；".join(errors)}

    result = preview(payload)
    if len(result["calc_results"]) != len(_REQUIRED_INPUTS):
        message = "；".join(result["calc_messages"]) or "实验数据未通过计算校验。"
        return {"code": 1, "message": message}

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    summary = []
    for table_id in _REQUIRED_INPUTS:
        summary.extend(result["calc_results"][table_id]["lines"])
    return structured_result(
        workpath,
        name(),
        schema(),
        enriched,
        summary=summary,
    )


def handle(workpath, extension):
    """保留旧插件入口；本实验使用新版多表格结构化接口。"""
    return 1
