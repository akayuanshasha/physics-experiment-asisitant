from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "传感器实验"

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
        # 多种传感器综合实验，常见数据列：x(位移/压力/温度输入), U(mV输出)
        x_col = [c for c in cols if 'x' in c or '输入' in c or '位移' in c or '压力' in c or 'T' in c.upper()][0] if any('x' in c or '输入' in c or '位移' in c or '压力' in c or 'T' in c.upper() for c in cols) else cols[0]
        u_col = [c for c in cols if 'U' in c or '输出' in c or '电压' in c or 'V' in c][0] if any('U' in c or '输出' in c or '电压' in c or 'V' in c for c in cols) else cols[1]

        x = pd.to_numeric(data[x_col], errors='coerce')
        U_out = pd.to_numeric(data[u_col], errors='coerce')

        # 线性拟合（传感器特性曲线）
        res_lsm = analyse_lsm(x, U_out, 'x', 'U_{out}', '', 'mV')

        # 灵敏度
        sensitivity = res_lsm.m

        # 线性度 = max|Δy| / (满量程输出) * 100%
        y_fit = res_lsm.m * x + res_lsm.b
        linearity = abs(U_out - y_fit).max() / (U_out.max() - U_out.min()) * 100 if (U_out.max() - U_out.min()) > 1e-10 else 0

        # 迟滞（如果有上升/下降两组数据）
        # 简化处理：仅做单向

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("传感器特性实验")
        docu.add_paragraph("灵敏度 S = {:.4f} mV/单位".format(sensitivity))
        docu.add_paragraph("线性度 = {:.3f}%".format(linearity))
        docu.add_paragraph()

        docu.add_paragraph("传感器输入-输出特性曲线")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(x)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['输入 x', '输出 U (mV)', '拟合 U_fit', '偏差']):
            table.rows[0].cells[j].text = h
        for i in range(len(x)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(x.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(U_out.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(y_fit.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(U_out.iloc[i] - y_fit.iloc[i])
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()
        docu.add_paragraph("灵敏度：S = \\frac{\\Delta U}{\\Delta x}")
        docu.add_paragraph("线性度：\\delta_L = \\frac{\\max|\\Delta y|}{Y_{FS}} \\times 100\\%")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp48", "exp48_example")
    table = make_table(
        "table1", "传感器标定数据表", ["x", "U"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "输入量 x", "y_label": "输出电压 U",
               "title": "传感器标定曲线", "fit": "linear"},
    )
    return make_schema("通过输入量与输出电压关系标定传感器。", [table], analysis_hints="检查灵敏度、零点偏移、线性和迟滞误差。",
        table_theory=get_table_theory("exp48"), report_enabled=False,)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
