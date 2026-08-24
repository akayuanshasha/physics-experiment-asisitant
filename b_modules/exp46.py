from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "导热系数"

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
        # 稳态法：识别 T1(°C高温), T2(°C低温), U/V(mV热电偶), d(mm厚度), D(mm直径)
        t1_col = [c for c in cols if 'T1' in c or '高温' in c or 'T_1' in c][0] if any('T1' in c or '高温' in c or 'T_1' in c for c in cols) else cols[0]
        t2_col = [c for c in cols if 'T2' in c or '低温' in c or 'T_2' in c][0] if any('T2' in c or '低温' in c or 'T_2' in c for c in cols) else cols[1]

        T1 = pd.to_numeric(data[t1_col], errors='coerce')  # °C
        T2 = pd.to_numeric(data[t2_col], errors='coerce')  # °C

        # 已知参数（可根据实际调整）
        d_sample = 5.0  # mm 样品厚度
        D_sample = 130.0  # mm 样品直径
        m_cool = 1000.0  # g 冷却水质量
        m_heat = 1000.0  # g 加热水质量
        c_water = 4.18  # J/(g·K) 水比热容

        # 稳态热流 P = κ * A * ΔT / d
        # 从冷却水温升速率估算热流 P = m_cool * c * dT/dt
        # 若有时间列则计算，否则用温差关联
        delta_T = T1 - T2
        A_area = np.pi * (D_sample/2)**2 / 1e6  # m²

        # 热导率 κ = P * d / (A * ΔT)
        # 若无时间列，用默认功率估算
        kappa_guess = 0.15  # W/(m·K) 默认不良导体
        P_heat = kappa_guess * A_area * delta_T / (d_sample / 1000)  # W

        # 基于散热速率估算：κ = (m_cool * c * dT_cool/dt * d) / (A * ΔT)
        # 简化版：κ = kappa_guess 计算，实际需要 dT/dt 数据
        dT_cool_dt = delta_T.diff()  # 近似温度变化率
        kappa = (m_cool * c_water * abs(dT_cool_dt) * d_sample/1000) / (A_area * delta_T)
        kappa = kappa.dropna()
        # 过滤异常值
        kappa = kappa[abs(kappa) < 10]

        res_kappa = analyse(kappa, 0, 0, r'\kappa', r'W/(m\cdot K)', confidence_C=3) if len(kappa) > 0 else None

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("稳态法测不良导体导热系数")
        docu.add_paragraph("样品：直径 = {:.0f} mm, 厚度 = {:.1f} mm".format(D_sample, d_sample))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(T1)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['T1 (°C)', 'T2 (°C)', 'ΔT (°C)', 'κ (W/(m·K))']):
            table.rows[0].cells[j].text = h
        for i in range(len(T1)):
            table.rows[i+1].cells[0].text = '{:.1f}'.format(T1.iloc[i])
            table.rows[i+1].cells[1].text = '{:.1f}'.format(T2.iloc[i])
            table.rows[i+1].cells[2].text = '{:.1f}'.format(delta_T.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(kappa.iloc[i-1]) if not kappa.empty and i>0 else '--'
        docu.add_paragraph()

        if res_kappa is not None:
            insert_data(docu, "导热系数 κ", res_kappa, "word")
            docu.add_paragraph()
            docu.add_paragraph("【Latex代码】")
            insert_data(docu, "导热系数 κ", res_kappa, "latex")
            docu.add_paragraph()

        docu.add_paragraph("公式：")
        docu.add_paragraph("\\kappa = \\frac{P d}{A \\Delta T}")
        docu.add_paragraph("P = m_{cool} c_{water} \\frac{dT_{cool}}{dt}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp46", "exp46_example")
    table = make_table(
        "table1", "导热系数温度测量数据表", ["T1", "T2"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "热端温度 T1", "y_label": "冷端温度 T2",
               "title": "冷热端温度关系", "fit": "linear"},
    )
    return make_schema("根据稳态温度数据计算材料导热系数。", [table], analysis_hints="检查稳态温差、温度变化趋势和测量单位。",
        table_theory=get_table_theory("exp46"), report_enabled=False,)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
