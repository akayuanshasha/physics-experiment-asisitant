from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)

def name():
    return "介电常数"

def handle(workpath,extension):
    try:
        excelpath=workpath+name()+'.'+extension

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"]
            data=pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data=pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        # 识别列：d(mm), S(mm²), C_air(pF), C_sample(pF)
        d_col = [c for c in cols if 'd' in c or '厚度' in c][0] if any('d' in c or '厚度' in c for c in cols) else cols[0]
        s_col = [c for c in cols if 'S' in c or '面积' in c][0] if any('S' in c or '面积' in c for c in cols) else (cols[1] if len(cols)>1 else cols[0])
        ca_col = [c for c in cols if 'C_a' in c or '空气' in c or 'C_air' in c][0] if any('C_a' in c or '空气' in c or 'C_air' in c for c in cols) else (cols[2] if len(cols)>2 else cols[0])
        cs_col = [c for c in cols if 'C_s' in c or '样品' in c or 'sample' in c.lower()][0] if any('C_s' in c or '样品' in c or 'sample' in c.lower() for c in cols) else (cols[3] if len(cols)>3 else cols[0])

        d = pd.to_numeric(data[d_col], errors='coerce')
        S = pd.to_numeric(data[s_col], errors='coerce')
        C_air = pd.to_numeric(data[ca_col], errors='coerce')
        C_sample = pd.to_numeric(data[cs_col], errors='coerce')

        # 相对介电常数 εr = C_sample / C_air
        epsilon_r = C_sample / C_air

        res_er = analyse(epsilon_r, 0, 0, r'\varepsilon_r', '', confidence_C=3)

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(d)+1, cols=5, style='Table Grid')
        for j, h in enumerate(['d (mm)', 'S (mm²)', 'C_air (pF)', 'C_sample (pF)', 'ε_r']):
            table.rows[0].cells[j].text = h
        for i in range(len(d)):
            table.rows[i+1].cells[0].text = '{:.3f}'.format(d.iloc[i])
            table.rows[i+1].cells[1].text = '{:.2f}'.format(S.iloc[i])
            table.rows[i+1].cells[2].text = '{:.2f}'.format(C_air.iloc[i])
            table.rows[i+1].cells[3].text = '{:.2f}'.format(C_sample.iloc[i])
            table.rows[i+1].cells[4].text = '{:.4f}'.format(epsilon_r.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "相对介电常数 ε_r", res_er, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "相对介电常数 ε_r", res_er, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("C = \\varepsilon_0 \\varepsilon_r \\frac{S}{d}")
        docu.add_paragraph("\\varepsilon_r = \\frac{C_{sample}}{C_{air}}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def _set_units(table, units):
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    table1 = _set_units(make_table(
        "table1", "电容表直接法测固体相对介电常数",
        ["电容 C", "样品厚度 d", "极板有效面积 S", "相对介电常数 εr"],
        sample=[[35.4, 2.00, 20.0, ""]], readonly=(3,), initial_rows=1,
    ), ["pF", "mm", "cm²", ""])
    table2 = _set_units(make_table(
        "table2", "固定极板间距法（D = 3 mm）",
        ["样品厚度 d", "极板有效面积 S", "无样品电容 C1", "有样品电容 C2", "相对介电常数 εr"],
        sample=[[2.00, 20.0, 18.5, 25.0, ""]], readonly=(4,), initial_rows=1,
    ), ["mm", "cm²", "pF", "pF", ""])
    table3 = _set_units(make_table(
        "table3", "液体相对介电常数比较法",
        ["空气初态 C11", "空气终态 C12", "液体初态 C21", "液体终态 C22", "相对介电常数 εr"],
        sample=[[12.0, 25.0, 15.0, 48.0, ""]], readonly=(4,), initial_rows=1,
    ), ["pF", "pF", "pF", "pF", ""])
    return make_schema(
        "电容表直接法、固定极板间距法和液体比较法分别计算相对介电常数。所有计算结果会在输入时自动更新。",
        [table1, table2, table3],
        analysis_hints="分别检查三个方法的量纲、分母是否接近零，以及相对介电常数是否为合理正值。",
        preview_enabled=True,
    )


def preview(payload):
    epsilon0 = 8.8541878128e-12
    tables = copied_tables(payload)
    for row in tables.get("table1", []):
        capacitance, thickness, area = (as_number(row.get(key)) for key in ("c0", "c1", "c2"))
        value = None
        if capacitance is not None and thickness is not None and area not in (None, 0):
            value = capacitance * 1e-12 * thickness * 1e-3 / (epsilon0 * area * 1e-4)
        row["c3"] = formatted(value, 5)
    for row in tables.get("table2", []):
        d, area, c1, c2 = (as_number(row.get(key)) for key in ("c0", "c1", "c2", "c3"))
        value = None
        if None not in (d, area, c1, c2):
            d_m, area_m, distance = d * 1e-3, area * 1e-4, 3e-3
            c02 = epsilon0 * area_m / distance + (c2 - c1) * 1e-12
            denominator = epsilon0 * area_m - c02 * (distance - d_m)
            if denominator != 0:
                value = d_m * c02 / denominator
        row["c4"] = formatted(value, 5)
    for row in tables.get("table3", []):
        c11, c12, c21, c22 = (as_number(row.get(key)) for key in ("c0", "c1", "c2", "c3"))
        value = None
        if None not in (c11, c12, c21, c22) and c12 != c11:
            value = (c22 - c21) / (c12 - c11)
        row["c4"] = formatted(value, 5)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["三种介电常数测量方法已由模块后端完成计算。"],
    )
