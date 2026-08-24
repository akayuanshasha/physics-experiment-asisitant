from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "电子小制作"

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
        # 电子制作综合实验：可涉及焊接、电路调试等
        # 数据列可能是测量结果验证：f(Hz), U(V), I(mA), R(Ω)
        # 灵活识别
        val1_col = cols[0]
        val2_col = cols[1] if len(cols) > 1 else cols[0]

        val1 = pd.to_numeric(data[val1_col], errors='coerce')
        val2 = pd.to_numeric(data[val2_col], errors='coerce')

        name1 = val1_col.strip()
        name2 = val2_col.strip()

        # 根据列名推断实验类型
        # 如果涉及电阻，计算 R = U/I
        if ('U' in name1.upper() or 'V' in name1.upper() or '电压' in name1) and \
           ('I' in name2.upper() or 'A' in name2.upper() or '电流' in name2):
            R_calc = val1 / val2.where(abs(val2) > 1e-10, 1e-10)
            res_R = analyse(R_calc, 0, 0, 'R', r'\Omega')
        else:
            res_R = None

        # 统计分析
        res_val1 = analyse(val1, 0, 0, name1, '', confidence_C=3)

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("电子小制作：综合实验")
        docu.add_paragraph("测量数据统计")
        docu.add_paragraph()

        # 数据表格
        n_cols = min(len(cols), 4)
        table = docu.add_table(rows=len(val1)+1, cols=n_cols, style='Table Grid')
        for j in range(n_cols):
            table.rows[0].cells[j].text = cols[j]
        for i in range(len(val1)):
            for j in range(n_cols):
                try:
                    val = pd.to_numeric(data[cols[j]], errors='coerce').iloc[i]
                    table.rows[i+1].cells[j].text = '{:.4f}'.format(val)
                except:
                    table.rows[i+1].cells[j].text = str(data[cols[j]].iloc[i])
        docu.add_paragraph()

        insert_data(docu, "{} 统计".format(name1), res_val1, "word")
        docu.add_paragraph()

        if res_R is not None:
            insert_data(docu, "计算电阻 R", res_R, "word")
            docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "{} 统计".format(name1), res_val1, "latex")
        if res_R is not None:
            docu.add_paragraph()
            insert_data(docu, "计算电阻 R", res_R, "latex")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp49", "exp49_example")
    table = make_table(
        "table1", "电子小制作伏安特性数据表", ["U", "I"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "电压 U", "y_label": "电流 I",
               "title": "伏安特性曲线", "fit": "linear"},
    )
    return make_schema("根据电压、电流数据分析电子制作电路的特性。", [table], analysis_hints="检查伏安关系、等效电阻及异常测量点。",
        table_theory=get_table_theory("exp49"), report_enabled=False,)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
