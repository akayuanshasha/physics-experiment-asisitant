from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "接触角仪"

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
        # 识别：θ(°接触角), h(mm液滴高度), d(mm接触直径)
        theta_col = [c for c in cols if 'θ' in c or '角度' in c or 'theta' in c.lower()][0] if any('θ' in c or '角度' in c or 'theta' in c.lower() for c in cols) else cols[0]
        h_col = [c for c in cols if 'h' in c or '高度' in c][0] if any('h' in c or '高度' in c for c in cols) else (cols[1] if len(cols)>1 else cols[0])
        d_col = [c for c in cols if 'd' in c or '直径' in c or 'D' in c][0] if any('d' in c or '直径' in c or 'D' in c for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        theta = pd.to_numeric(data[theta_col], errors='coerce')  # °
        h = pd.to_numeric(data[h_col], errors='coerce')  # mm
        d = pd.to_numeric(data[d_col], errors='coerce')  # mm

        # 接触角统计
        res_theta = analyse(theta, 0, 0, r'\theta', '°', confidence_C=3)

        # 若 h << d，可用小液滴近似：θ ≈ 2*arctan(2h/d)
        theta_calc = 2 * np.arctan(2 * h / d) * 180 / np.pi
        res_theta_calc = analyse(theta_calc, 0, 0, r'\varphi', '°', confidence_C=3)

        # 表面能 γ_sl = γ_sv - γ_lv*cosθ（Young方程）
        gamma_lv = 72.8  # mN/m 水的表面张力（20°C）
        cos_theta = np.cos(np.deg2rad(theta))
        # 润湿功 Wa = γ_lv(1+cosθ)
        Wa = gamma_lv * (1 + cos_theta)

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("接触角测量实验")
        docu.add_paragraph("水的表面张力 γ_lv = {:.1f} mN/m (20°C)".format(gamma_lv))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(theta)+1, cols=5, style='Table Grid')
        for j, h_disp in enumerate(['θ (°)', 'h (mm)', 'd (mm)', 'θ_calc (°)', 'Wa (mN/m)']):
            table.rows[0].cells[j].text = h_disp
        for i in range(len(theta)):
            table.rows[i+1].cells[0].text = '{:.1f}'.format(theta.iloc[i])
            table.rows[i+1].cells[1].text = '{:.3f}'.format(h.iloc[i])
            table.rows[i+1].cells[2].text = '{:.3f}'.format(d.iloc[i])
            table.rows[i+1].cells[3].text = '{:.1f}'.format(theta_calc.iloc[i])
            table.rows[i+1].cells[4].text = '{:.2f}'.format(Wa.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "接触角 θ", res_theta, "word")
        docu.add_paragraph()
        insert_data(docu, "计算接触角 θ_calc", res_theta_calc, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "接触角 θ", res_theta, "latex")
        docu.add_paragraph()
        insert_data(docu, "计算接触角 θ_calc", res_theta_calc, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("Young方程：\\gamma_{sv} = \\gamma_{sl} + \\gamma_{lv}\\cos\\theta")
        docu.add_paragraph("润湿功：W_a = \\gamma_{lv}(1 + \\cos\\theta)")
        docu.add_paragraph("液滴近似：\\theta \\approx 2\\arctan(\\frac{2h}{d})")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp47", "exp47_example")
    table = make_table(
        "table1", "接触角测量数据表", ["theta", "h", "d"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c1", "y_column": "c0", "x_label": "液滴高度 h", "y_label": "接触角 θ",
               "title": "接触角测量关系", "fit": "auto"},
    )
    return make_schema("根据液滴几何参数测量接触角。", [table], analysis_hints="检查角度与液滴高度、直径之间的几何一致性。",
        table_theory=get_table_theory("exp47"),)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
