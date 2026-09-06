"""平均值、标准差、不确定度计算（基础工具）模块
==============================================
本模块是一级大物实验的公共数据处理工具，包含三张输入表：

  表格1：平均值、标准差与不确定度计算表
    → 由多次测量值计算算术平均值 x̄、样本标准差 s、A 类不确定度 u_A、
      合成不确定度 u（含 B 类仪器允差），并按指定置信系数给出结果。
  表格2：最小二乘法线性回归计算表
    → 对 (x, y) 数据作线性拟合 y = a + b x，输出斜率 b、截距 a、相关系数 r。
  表格3：表达式及合成不确定度计算表
    → 由各输入量的数值与标准不确定度，按误差传播公式合成不确定度。

物理公式：
  x̄ = (1/n)Σxᵢ
  s = √( Σ(xᵢ - x̄)² / (n - 1) )
  u_A = s / √n
  u = √(u_A² + u_B²)，u_B = Δ_inst / √3  （近似认为仪器误差服从均匀分布）
  线性拟合：b = [nΣxy - ΣxΣy] / [nΣx² - (Σx)²]
"""

from head import *  # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory


def name():  # 返回实验名称
    return "平均值、标准差、不确定度计算"


def _set_units(table, units):
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    # 表格1：平均值、标准差与不确定度（示例数据取自 exp0 示例 CSV）
    table1 = _set_units(
        make_table(
            "table1",
            "平均值与不确定度计算表",
            ["序号", "测量值 x", "偏差 x-x̄", "偏差平方 (x-x̄)²"],
            sample=[
                [1, 80.01, "", ""],
                [2, 80.13, "", ""],
                [3, 79.96, "", ""],
                [4, 79.99, "", ""],
                [5, 80.12, "", ""],
            ],
            readonly=(0, 2, 3),
            min_rows=5,
            initial_rows=5,
            description="输入多次等精度测量的数值，平均、标准差与不确定度由后端自动计算。",
        ),
        ["", "与测量值相同", "", ""],
    )
    # 表格2：最小二乘法线性回归（示例数据取自 exp0 示例 CSV）
    table2 = _set_units(
        make_table(
            "table2",
            "最小二乘法线性回归计算表",
            ["序号", "x", "y", "拟合值 ŷ", "残差 y-ŷ"],
            sample=[
                [1, 10, 11, "", ""],
                [2, 20, 20, "", ""],
                [3, 30, 29, "", ""],
                [4, 40, 44, "", ""],
                [5, 50, 51, "", ""],
                [6, 60, 60, "", ""],
                [7, 70, 72, "", ""],
                [8, 80, 81, "", ""],
            ],
            readonly=(0, 3, 4),
            min_rows=3,
            initial_rows=8,
            chart={
                "x_column": "c1",
                "y_column": "c2",
                "x_label": "x",
                "y_label": "y",
                "title": "最小二乘法线性拟合",
                "fit": "linear",
            },
            description="输入成对的 (x, y) 数据，斜率、截距与相关系数由后端最小二乘拟合得到。",
        ),
        ["", "自变量 x", "因变量 y", "", ""],
    )
    # 表格3：表达式及合成不确定度（示例数据取自 exp0 示例 CSV）
    table3 = _set_units(
        make_table(
            "table3",
            "表达式及合成不确定度计算表",
            ["变量名", "数值", "标准不确定度 u"],
            sample=[
                ["a", 0.6976, 0.0021],
                ["b", 1.677, 0.0064],
                ["c", 1.567, ""],
            ],
            readonly=(),
            min_rows=2,
            initial_rows=3,
            text_columns=(0,),
            description="输入独立变量的数值与标准不确定度，后端按误差传播公式合成结果。",
        ),
        ["", "与变量相同", "与变量相同"],
    )

    return make_schema(
        (
            "本工具用于基础实验数据处理：① 多次测量求平均值、标准差及 A/B 类与合成不确定度；"
            "② 最小二乘法线性回归求斜率、截距与相关系数；③ 由变量表达式合成不确定度。"
            "计算结果可直接用于实验报告。"
        ),
        [table1, table2, table3],
        parameters=[
            {"id": "unit", "label": "测量值单位", "type": "text", "default": "m"},
            {"id": "delta_b1", "label": "仪器允差 Δ₁", "type": "number", "default": 0.02},
            {"id": "delta_b2", "label": "仪器允差 Δ₂", "type": "number", "default": 0.05},
            {"id": "confidence_C", "label": "置信系数 C", "type": "number", "default": 3},
            {"id": "confidence_P", "label": "置信概率 P", "type": "number", "default": 0.95},
        ],
        analysis_hints="检查测量值的分散性、标准差与不确定度的合理性，以及线性回归的相关系数是否接近 1。",
        preview_enabled=True,
        formulas=get_formulas("exp0"),
        variables=get_variables("exp0"),
        table_theory=get_table_theory("exp0"),
    )


def _lsm(xs, ys):
    """最小二乘线性拟合 y = a + bx，返回 (斜率 b, 截距 a, 相关系数 r)。"""
    n = len(xs)
    if n < 2:
        return None, None, None
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    syy = sum((y - y_mean) ** 2 for y in ys)
    if sxx == 0:
        return None, None, None
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    r = sxy / ((sxx * syy) ** 0.5) if sxx > 0 and syy > 0 else None
    return slope, intercept, r


def preview(payload):
    """实时补全平均值表的偏差列与回归表的拟合列。"""
    tables = copied_tables(payload)

    # 表格1：平均值、偏差与偏差平方
    rows1 = tables.get("table1", [])
    xs = [as_number(row.get("c1")) for row in rows1]
    xs = [v for v in xs if v is not None]
    mean = sum(xs) / len(xs) if xs else None
    for index, row in enumerate(rows1):
        row["c0"] = index + 1
        x = as_number(row.get("c1"))
        if x is not None and mean is not None:
            row["c2"] = formatted(x - mean, 4)
            row["c3"] = formatted((x - mean) ** 2, 4)
        else:
            row["c2"] = row["c3"] = ""

    # 表格2：线性回归拟合值 ŷ 与残差
    rows2 = tables.get("table2", [])
    xs2 = [as_number(row.get("c1")) for row in rows2]
    ys2 = [as_number(row.get("c2")) for row in rows2]
    slope, intercept, _ = _lsm(xs2, ys2)
    for index, row in enumerate(rows2):
        row["c0"] = index + 1
        x = as_number(row.get("c1"))
        y = as_number(row.get("c2"))
        if x is not None and slope is not None and intercept is not None:
            yhat = slope * x + intercept
            row["c3"] = formatted(yhat, 4)
            row["c4"] = formatted(y - yhat if y is not None else None, 4)
        else:
            row["c3"] = row["c4"] = ""

    # 表格3：仅保留用户输入（序号不适用，不做处理）
    for index, row in enumerate(tables.get("table3", [])):
        row.setdefault("c0", row.get("c0", ""))

    return {"tables": tables}


def handle_structured(workpath, payload):
    """完成最终计算并生成实验报告。"""
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]

    parameters = payload.get("parameters") or {}
    summary = []

    # 表格1：平均值、标准差、A 类与合成不确定度
    rows1 = enriched["tables"].get("table1", []) or []
    xs = [as_number(r.get("c1")) for r in rows1]
    xs = [v for v in xs if v is not None]
    if len(xs) >= 2:
        n = len(xs)
        mean = sum(xs) / n
        s = (sum((x - mean) ** 2 for x in xs) / (n - 1)) ** 0.5
        u_a = s / n ** 0.5
        delta_b1 = as_number(parameters.get("delta_b1")) or 0.0
        delta_b2 = as_number(parameters.get("delta_b2")) or 0.0
        delta_inst = max(delta_b1, delta_b2)
        u_b = delta_inst / 3 ** 0.5
        u = (u_a ** 2 + u_b ** 2) ** 0.5
        summary.append(f"算术平均值 x̄ = {mean:.4f}")
        summary.append(f"样本标准差 s = {s:.4f}")
        summary.append(f"A 类不确定度 u_A = {u_a:.4f}")
        summary.append(f"B 类不确定度 u_B = {u_b:.4f}（仪器允差 Δ_inst = {delta_inst}）")
        summary.append(f"合成不确定度 u = {u:.4f}")

    # 表格2：线性回归
    rows2 = enriched["tables"].get("table2", []) or []
    xs2 = [as_number(r.get("c1")) for r in rows2]
    ys2 = [as_number(r.get("c2")) for r in rows2]
    slope, intercept, r = _lsm(xs2, ys2)
    if slope is not None:
        summary.append(f"线性回归：斜率 b = {slope:.4f}，截距 a = {intercept:.4f}")
        if r is not None:
            summary.append(f"相关系数 r = {r:.4f}（|r| 越接近 1 线性越好）")

    # 表格3：表达式合成不确定度（误差传播示例）
    rows3 = enriched["tables"].get("table3", []) or []
    variables = []
    for row in rows3:
        var = str(row.get("c0", "")).strip()
        value = as_number(row.get("c1"))
        unc = as_number(row.get("c2"))
        if var and value is not None and unc is not None:
            variables.append((var, value, unc))
    if len(variables) >= 2:
        rel = (sum((u / v) ** 2 for _, v, u in variables)) ** 0.5
        summary.append(
            "表达式合成相对不确定度（各变量独立、取方和根）："
            + "u_r = " + f"{rel * 100:.2f}%"
        )

    if not summary:
        summary = ["数据已按基础工具模块处理完成。"]

    return structured_result(
        workpath,
        name(),
        schema(),
        enriched,
        summary=summary,
    )


def handle(workpath, extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        excelpath = workpath + name() + '.' + extension  # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]  # 判断编码格式
            data = pd.read_csv(excelpath, header=None, names=["x", "unit", "delta_b1", "delta_b2", "confidence_C", "confidence_P"], encoding=encode)  # 读取csv文件
        else:
            data = pd.read_excel(excelpath, header=None, names=["x", "unit", "delta_b1", "delta_b2", "confidence_C", "confidence_P"])  # 读取xls/xlsx文件

        os.remove(excelpath)  # 读取Excel数据后删除文件

        res = analyse(pd.Series([float(x) for x in data["x"][1:]]), float(data["delta_b1"][1]), float(data["delta_b2"][1]),
            data["x"][0], data["unit"][1], float(data["confidence_C"][1]), float(data["confidence_P"][1]))

        docu = Document()
        style_doc_font(docu)

        docu.add_paragraph(name())  # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        insert_data(docu, data["x"][0], res, "word")

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, data["x"][0], res, "latex")

        docu.save(workpath + name() + ".docx")  # 保存Word文档，注意文件名必须与name()函数返回值一致

        return 0  # 若成功，返回0
    except:
        traceback.print_exc()  # 打印错误
        return 1  # 若失败，返回1
