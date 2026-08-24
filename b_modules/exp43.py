from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "刚体转动惯量"

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
        # 三线摆法：识别 T(s周期), m(g质量), R(mm半径), r(mm中心半径), h(mm高度)
        # 或落体法：m, a(加速度), h, t
        # 通用识别
        t_col = [c for c in cols if 'T' in c or '周期' in c][0] if any('T' in c or '周期' in c for c in cols) else cols[0]
        m_col = [c for c in cols if 'm' in c or '质量' in c or 'M' in c][0] if any('m' in c or '质量' in c or 'M' in c for c in cols) else (cols[1] if len(cols)>1 else cols[0])
        h_col = [c for c in cols if 'h' in c or '高度' in c][0] if any('h' in c or '高度' in c for c in cols) else (cols[2] if len(cols)>2 else cols[0])
        r_col = [c for c in cols if 'R' in c or '半径' in c or 'r' in c][0] if any('R' in c or '半径' in c or 'r' in c for c in cols) else (cols[3] if len(cols)>3 else cols[0])

        T = pd.to_numeric(data[t_col], errors='coerce')  # s
        m = pd.to_numeric(data[m_col], errors='coerce')  # g
        h = pd.to_numeric(data[h_col], errors='coerce') if h_col != cols[0] else pd.Series([50.0]*len(T))  # mm
        R_radius = pd.to_numeric(data[r_col], errors='coerce') if r_col != cols[0] else pd.Series([60.0]*len(T))  # mm

        # 默认三线摆参数：r=30mm（上盘）, R=60mm（下盘）
        r_small = 30.0  # mm
        R_big = R_radius  # 下盘半径 mm（从数据获取）

        g = 9.8 * 1000  # mm/s²

        # 转动惯量 I = mgRrT² / (4π²H)
        I_exp = m * g * R_big * r_small * T**2 / (4 * np.pi**2 * h)  # g·mm²

        # 理论转动惯量（圆盘）I_theory = 1/2 * m * R²
        I_theory = 0.5 * m * R_big**2

        # 相对误差
        rel_err = abs(I_exp - I_theory) / I_theory * 100

        res_I = analyse(I_exp, 0, 0, 'I', r'g\cdot mm^2')

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("三线摆法测刚体转动惯量")
        docu.add_paragraph("参数：上盘半径 r = {:.1f} mm".format(r_small))
        docu.add_paragraph("重力加速度 g = 9.8 m/s²")
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(T)+1, cols=7, style='Table Grid')
        for j, header in enumerate(['T (s)', 'm (g)', 'h (mm)', 'R (mm)', 'I_exp (g·mm²)', 'I_theory', '偏差(%)']):
            table.rows[0].cells[j].text = header
        for i in range(len(T)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(T.iloc[i])
            table.rows[i+1].cells[1].text = '{:.2f}'.format(m.iloc[i])
            table.rows[i+1].cells[2].text = '{:.1f}'.format(h.iloc[i])
            table.rows[i+1].cells[3].text = '{:.1f}'.format(R_big.iloc[i])
            table.rows[i+1].cells[4].text = '{:.2e}'.format(I_exp.iloc[i])
            table.rows[i+1].cells[5].text = '{:.2e}'.format(I_theory.iloc[i])
            table.rows[i+1].cells[6].text = '{:.2f}'.format(rel_err.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "转动惯量 I", res_I, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "转动惯量 I", res_I, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("I = \\frac{mgRr}{4\\pi^2 H} T^2")
        docu.add_paragraph("I_{theory} = \\frac{1}{2} m R^2 \\quad \\text{(圆盘)}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp43", "exp43_example")
    table = make_table(
        "table1", "刚体转动惯量测量数据表", ["T", "m", "h", "R"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "周期 T", "y_label": "质量 m",
               "title": "转动惯量测量数据检查", "fit": "auto"},
    )
    return make_schema("利用周期、质量和几何参数测量刚体转动惯量。", [table], analysis_hints="重点检查周期重复测量的离散性和单位一致性。",
        table_theory=get_table_theory("exp43"), report_enabled=False,)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
