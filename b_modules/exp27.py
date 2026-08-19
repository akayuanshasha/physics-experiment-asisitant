from head import * # 导入万能头
from structured_support import make_schema, make_table, structured_result

def name(): # 返回实验名称
    return "非平衡电桥"

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
        # 自动识别列
        r4_col = [c for c in cols if 'R4' in c or 'R_4' in c][0] if any('R4' in c or 'R_4' in c for c in cols) else cols[0]
        ug_col = [c for c in cols if 'Ug' in c or 'U_g' in c or '电压' in c][0] if any('Ug' in c or 'U_g' in c or '电压' in c for c in cols) else cols[1]

        R4 = pd.to_numeric(data[r4_col], errors='coerce')
        Ug = pd.to_numeric(data[ug_col], errors='coerce')

        # 找出R0（Ug最接近0时的R4）和Us（电源电压，从列名或数据推断）
        R0 = R4.iloc[Ug.abs().idxmin()]
        Us = 5.0  # 默认电源电压5V

        delta_R = R4 - R0
        delta = delta_R / R0

        # 理论非平衡电压：Ug_theory = Us/4 * delta / (1 + delta/2)
        Ug_theory = (Us / 4.0) * delta / (1.0 + delta / 2.0)

        # 线性近似：Ug_linear = Us/4 * delta
        Ug_linear = (Us / 4.0) * delta

        # 线性范围的判定：相对偏差 < 5%
        rel_err = abs(Ug_linear - Ug) / abs(Ug_linear.where(abs(Ug_linear) > 1e-10, 1e-10))

        # 零点的绝对灵敏度
        idx_near_zero = delta.abs().argsort()[:5]
        S_Ua = np.mean([abs(Ug.iloc[i] / delta_R.iloc[i]) if abs(delta_R.iloc[i]) > 1e-10 else 0 for i in idx_near_zero])

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("平衡点 R0 = {:.2f} Ω".format(R0))
        docu.add_paragraph("电源电压 Us = {:.1f} V".format(Us))
        docu.add_paragraph("零点绝对灵敏度 S_Ua = {:.4f} mV/Ω".format(S_Ua * 1000))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(R4)+1, cols=6, style='Table Grid')
        headers = ['R4 (Ω)', 'ΔR (Ω)', 'δ=ΔR/R0', 'Ug实测(mV)', 'Ug线性(mV)', '相对偏差(%)']
        for j, h in enumerate(headers):
            table.rows[0].cells[j].text = h
        for i in range(len(R4)):
            table.rows[i+1].cells[0].text = '{:.2f}'.format(R4.iloc[i])
            table.rows[i+1].cells[1].text = '{:.2f}'.format(delta_R.iloc[i])
            table.rows[i+1].cells[2].text = '{:.5f}'.format(delta.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(Ug.iloc[i])
            table.rows[i+1].cells[4].text = '{:.4f}'.format(Ug_linear.iloc[i])
            table.rows[i+1].cells[5].text = '{:.2f}'.format(rel_err.iloc[i] * 100)
        docu.add_paragraph()

        # 线性范围
        linear_range = delta_R[rel_err <= 0.05]
        if len(linear_range) > 0:
            docu.add_paragraph("线性范围（相对偏差 ≤ 5%）：ΔR ∈ [{:.2f}, {:.2f}] Ω".format(
                linear_range.min(), linear_range.max()))

        docu.add_paragraph()
        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("平衡点 R_0 = {:.2f} \\Omega".format(R0))
        docu.add_paragraph("零点绝对灵敏度 S_{U_a} = {:.4f} mV/\\Omega".format(S_Ua * 1000))
        docu.add_paragraph()
        docu.add_paragraph("非平衡电桥输出电压公式：")
        docu.add_paragraph("U_g = \\frac{U_s}{4}\\cdot\\frac{\\delta}{1+\\delta/2},\\quad \\delta = \\frac{\\Delta R}{R_0}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample1 = [[-0.04, -40.1], [-0.02, -20.0], [0, 0.1], [0.02, 20.2], [0.04, 39.9]]
    sample2 = [[-0.04, -31.8], [-0.02, -16.0], [0, 0], [0.02, 16.1], [0.04, 32.0]]
    chart = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "ΔR/R0", "y_label": "Ug (mV)",
        "title": "非平衡电桥输出特性", "fit": "linear",
    }
    return make_schema(
        "测量非平衡电桥输出特性曲线（双数据表）",
        [
            make_table("table1", "非平衡电桥输出电压与电阻相对变化关系数据表",
                       ["δ=ΔR/R0", "Ug(mV)"], sample=sample1, initial_rows=3, chart=chart),
            make_table("table2", "不同桥臂电阻下非平衡电桥输出特性数据表",
                       ["δ=ΔR/R0", "Ug(mV)"], sample=sample2, initial_rows=3, chart=chart),
        ],
        analysis_hints="分别检查两组输出曲线的线性、零点偏移、灵敏度及线性范围。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["两组非平衡电桥数据已接收，可分别拟合输出电压与相对电阻变化的关系。"],
    )
