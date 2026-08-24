"""b_modules 结构化实验的通用辅助函数。

本文件只提供与实验无关的 schema 构造、数据复制、Word 输出和旧单表
``handle`` 兼容能力。具体实验的表格、示例数据和物理公式必须留在各自的
``expXX.py`` 中，确保同学只修改对应模块即可完成实验开发。
"""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Any, Callable, Iterable


def rows_from_values(columns: list[dict[str, Any]], values: Iterable[Iterable[Any]]) -> list[dict[str, Any]]:
    column_ids = [column["id"] for column in columns]
    return [
        {
            column_id: row[index] if index < len(row) else ""
            for index, column_id in enumerate(column_ids)
        }
        for raw_row in values
        for row in [list(raw_row)]
    ]


def make_table(
    table_id: str,
    title: str,
    labels: list[str],
    *,
    sample: Iterable[Iterable[Any]] = (),
    readonly: Iterable[int] = (),
    text_columns: Iterable[int] = (),
    min_rows: int = 1,
    initial_rows: int | None = None,
    chart: dict[str, Any] | None = None,
    required: bool = True,
    description: str = "",
) -> dict[str, Any]:
    readonly_set = set(readonly)
    text_set = set(text_columns)
    columns = []
    for index, label in enumerate(labels):
        column = {
            "id": f"c{index}",
            "label": label,
            "type": "text" if index in text_set else "number",
        }
        if index in readonly_set:
            column["readonly"] = True
        columns.append(column)

    sample_rows = rows_from_values(columns, sample)
    table = {
        "id": table_id,
        "title": title,
        "description": description,
        "required": required,
        "min_rows": min_rows,
        "initial_rows": max(min_rows, initial_rows if initial_rows is not None else len(sample_rows)),
        "columns": columns,
        "sample": sample_rows,
    }
    if chart:
        table["chart"] = deepcopy(chart)
    return table


def make_schema(
    description: str,
    tables: list[dict[str, Any]],
    *,
    parameters: list[dict[str, Any]] | None = None,
    analysis_hints: str = "",
    preview_enabled: bool = False,
    report_enabled: bool = True,
    revision: int = 3,
    formulas: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
    table_theory: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "schema_revision": revision,
        "draft_enabled": True,
        "report_enabled": report_enabled,
        "preview_enabled": preview_enabled,
        "description": description,
        "parameters": deepcopy(parameters or []),
        "analysis_hints": analysis_hints,
        "tables": deepcopy(tables),
        "formulas": deepcopy(formulas or []),
        "variables": deepcopy(variables or []),
        "table_theory": deepcopy(table_theory or {}),
    }


def copied_tables(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return deepcopy(payload.get("tables") or {})


def as_number(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def formatted(value: float | None, digits: int = 4) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def ordered_rows(schema: dict[str, Any], payload: dict[str, Any]) -> dict[str, list[list[str]]]:
    """按 schema 列顺序把浏览器提交的行对象转换为二维列表。"""
    submitted = payload.get("tables") or {}
    result: dict[str, list[list[str]]] = {}
    for table in schema.get("tables", []):
        table_id = table["id"]
        column_ids = [column["id"] for column in table.get("columns", [])]
        result[table_id] = [
            [str(row.get(column_id, "")) for column_id in column_ids]
            for row in submitted.get(table_id, []) or []
        ]
    return result


def parameter_values(schema: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """读取实验参数，并同时提供模块声明的 backend_key 别名。"""
    submitted = payload.get("parameters") or {}
    result: dict[str, Any] = {}
    for parameter in schema.get("parameters", []):
        parameter_id = parameter["id"]
        value = submitted.get(parameter_id, parameter.get("default", ""))
        result[parameter_id] = value
        backend_key = parameter.get("backend_key")
        if backend_key:
            result[backend_key] = value
    return result


def result_lines(results: Any) -> tuple[list[str], list[str]]:
    """把模块计算结果整理成统一报告摘要和警告列表。"""
    if not isinstance(results, dict):
        return [str(results)], []
    summary: list[str] = []
    for section_name in ("steps", "final"):
        section = results.get(section_name)
        if isinstance(section, dict):
            summary.extend(f"{key}：{value}" for key, value in section.items())
    if results.get("message"):
        summary.append(str(results["message"]))
    warnings = [str(item) for item in results.get("warnings", [])]
    return summary or ["数据已按实验模块的结构化接口处理完成。"], warnings


def _write_structured_document(
    workpath: str,
    experiment_name: str,
    schema: dict[str, Any],
    payload: dict[str, Any],
    summary: list[str],
) -> str:
    from docx import Document
    from docx.oxml.ns import qn

    document = Document()
    document.styles["Normal"].font.name = "微软雅黑"
    document.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    document.add_heading(experiment_name, level=0)

    parameters = payload.get("parameters") or {}
    if parameters:
        document.add_heading("实验参数", level=1)
        for parameter in schema.get("parameters", []):
            parameter_id = parameter.get("id")
            if parameter_id not in parameters:
                continue
            unit = parameter.get("unit", "")
            document.add_paragraph(
                f"{parameter.get('label', parameter_id)}：{parameters[parameter_id]} {unit}".strip()
            )

    submitted = payload.get("tables") or {}
    for table_schema in schema.get("tables", []):
        rows = submitted.get(table_schema["id"], []) or []
        if not rows:
            continue
        document.add_heading(table_schema.get("title", table_schema["id"]), level=1)
        columns = table_schema.get("columns", [])
        table = document.add_table(rows=1, cols=len(columns), style="Table Grid")
        for index, column in enumerate(columns):
            unit = column.get("unit", "")
            table.cell(0, index).text = (
                f"{column.get('label', column.get('id', ''))} / {unit}" if unit else
                str(column.get("label", column.get("id", "")))
            )
        for raw_row in rows:
            cells = table.add_row().cells
            for index, column in enumerate(columns):
                cells[index].text = str(raw_row.get(column.get("id"), ""))

    document.add_heading("计算与处理结果", level=1)
    for item in summary:
        document.add_paragraph(str(item))

    filename = f"{experiment_name}.docx"
    document.save(os.path.join(workpath, filename))
    return filename


def structured_result(
    workpath: str,
    experiment_name: str,
    schema: dict[str, Any],
    payload: dict[str, Any],
    *,
    summary: list[str] | None = None,
    warnings: list[str] | None = None,
    charts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summary = list(summary or ["数据已按实验模块的结构化接口处理完成。"])
    filename = _write_structured_document(workpath, experiment_name, schema, payload, summary)
    return {
        "code": 0,
        "summary": summary,
        "warnings": list(warnings or []),
        "charts": list(charts or []),
        "document": filename,
    }


def handle_legacy_single_table(
    workpath: str,
    payload: dict[str, Any],
    schema: dict[str, Any],
    experiment_name: str,
    legacy_handle: Callable[[str, str], int],
    *,
    include_header: bool = True,
) -> dict[str, Any]:
    """把结构化单表还原为旧 CSV 输入，再调用模块原有 handle。"""
    import pandas as pd

    table_schema = schema["tables"][0]
    columns = table_schema.get("columns", [])
    rows = payload.get("tables", {}).get(table_schema["id"], []) or []
    # 直接用二维行和显式列名构造 DataFrame，避免 LED、密立根等实验中
    # 合法的重复表头被 dict 悄悄合并。
    frame = pd.DataFrame(
        [[row.get(column["id"], "") for column in columns] for row in rows],
        columns=[column["label"] for column in columns],
    )
    csv_path = os.path.join(workpath, f"{experiment_name}.csv")
    frame.to_csv(csv_path, index=False, header=include_header, encoding="utf-8-sig")
    result = legacy_handle(workpath, "csv")
    if result != 0:
        return {"code": 1, "message": "旧版实验计算流程执行失败，请检查输入数据。"}
    return {
        "code": 0,
        "summary": ["数据已通过模块内的统一结构化接口处理，详细结果见 Word 文档。"],
        "warnings": [],
        "charts": [],
        "document": f"{experiment_name}.docx",
    }


def make_chart_from_table(
    table_schema: dict[str, Any],
    rows: list[dict[str, Any]],
    chart_config: dict[str, Any],
    workpath: str,
    chart_filename: str = "chart_0.png",
) -> dict[str, Any]:
    """利用 chart_generator 的多模型拟合能力，从结构化表格数据生成图表。

    参数:
        table_schema: make_table 返回的表格描述（含 columns / labels）
        rows: preview 计算后的行数据（dict 列表，key 为 c0, c1, …）
        chart_config: 图表配置，至少包含 x_column / y_column；
                      可选 fit: linear | quadratic | exponential | power | log | inverse | auto
        workpath: 图表输出目录（通常为 handle_structured 的 workpath）
        chart_filename: 输出文件名

    返回:
        dict  可直接放入 structured_result(charts=[...]) 的 chart 描述，
        包含 filename / title / fit_result / url 等字段。
    """
    import shutil as _shutil
    from chart_generator import generate_chart

    schema_columns = table_schema.get("columns", [])
    col_id_to_index = {col["id"]: idx for idx, col in enumerate(schema_columns)}
    labels = [col["label"] for col in schema_columns]
    data_rows = []
    for row in rows:
        data_row = [str(row.get(col["id"], "")) for col in schema_columns]
        data_rows.append(data_row)

    config = dict(chart_config)
    # 将列 ID（如 c0、c2）转换为整数索引，以便 generate_chart 正确定位数据列
    for key in ("x_column", "y_column"):
        col_id = config.get(key)
        if isinstance(col_id, str) and col_id in col_id_to_index:
            config[key.replace("_column", "_col")] = col_id_to_index[col_id]
            config.pop(key, None)
    config.setdefault("x_label", labels[0] if labels else "x")
    config.setdefault("y_label", labels[1] if len(labels) > 1 else "y")

    result = generate_chart(labels, data_rows, config, save_name=chart_filename)

    # generate_chart 保存到自身 OUTPUT_DIR，需要复制到 workpath 供前端访问
    src_path = result.get("path")
    dst_path = os.path.join(workpath, chart_filename)
    if src_path and os.path.exists(src_path):
        os.makedirs(workpath, exist_ok=True)
        _shutil.copy2(src_path, dst_path)

    return {
        "filename": chart_filename,
        "title": config.get("title", ""),
        "fit_result": result.get("fit_result"),
        "x_label": result.get("x_label", ""),
        "y_label": result.get("y_label", ""),
    }
