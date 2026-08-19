from head import * # 导入万能头
from structured_support import make_schema, make_table, structured_result

def name(): # 返回实验名称
    return "磁阻效应"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径，extension为扩展名（csv/xls/xlsx）
    try:
        excelpath=workpath+name()+'.'+extension

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"]
            data=pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data=pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        # 读取数据列：I_M（励磁电流/A），R（电阻/Ω）
        cols = list(data.columns)
        # 自动识别列名
        im_col = [c for c in cols if 'I' in c and 'M' in c or '励磁' in c or '电流' in c][0] if any('I' in c and 'M' in c or '励磁' in c for c in cols) else cols[0]
        r_col = [c for c in cols if 'R' in c or '电阻' in c][0] if any('R' in c or '电阻' in c for c in cols) else cols[1]

        I_M = pd.to_numeric(data[im_col], errors='coerce')
        R = pd.to_numeric(data[r_col], errors='coerce')

        # R(0)为零磁场下的电阻（第一个数据点）
        R0 = R.iloc[0]
        delta_R = R - R0
        delta_R_rel = delta_R / R0

        # 对 delta_R/R0 进行统计分析
        res_rel = analyse(delta_R_rel, 0, 0, r'\frac{\Delta R}{R_0}', '', confidence_C=3)

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("零磁场电阻 R(0) = {:.4f} Ω".format(R0))
        docu.add_paragraph("励磁电流 I_M 范围：{:.3f} ~ {:.3f} A".format(I_M.min(), I_M.max()))
        docu.add_paragraph()

        # 数据表格
        docu.add_paragraph("实验测量数据：")
        table = docu.add_table(rows=len(I_M)+1, cols=4, style='Table Grid')
        headers = ['I_M (A)', 'R (Ω)', 'ΔR (Ω)', 'ΔR/R₀']
        for j, h in enumerate(headers):
            table.rows[0].cells[j].text = h
        for i in range(len(I_M)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(I_M.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(R.iloc[i])
            table.rows[i+1].cells[2].text = '{:.6f}'.format(delta_R.iloc[i])
            table.rows[i+1].cells[3].text = '{:.6f}'.format(delta_R_rel.iloc[i])
        docu.add_paragraph()

        # 结果分析
        docu.add_paragraph("ΔR/R₀ 统计分析")
        docu.add_paragraph()._element.append(latex_to_word(res_rel.averagex2))
        docu.add_paragraph("ΔR/R₀ 标准差")
        docu.add_paragraph()._element.append(latex_to_word(res_rel.sigmax2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        docu.add_paragraph("零磁场电阻 R(0) = {:.4f} \\Omega".format(R0))
        docu.add_paragraph()

        docu.add_paragraph("ΔR/R₀ 平均值")
        docu.add_paragraph(res_rel.averagex)
        docu.add_paragraph("ΔR/R₀ 标准差")
        docu.add_paragraph(res_rel.sigmax)
        docu.add_paragraph()

        docu.add_paragraph("磁阻效应结论：ΔR/R₀ 随磁场（励磁电流）增大而变化，")
        docu.add_paragraph("在弱磁场下 ΔR/R₀ ∝ B²，强磁场下 ∝ B。")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample1 = [[0, 0], [0.10, 0.012], [0.20, 0.048], [0.30, 0.109], [0.40, 0.194]]
    sample2 = [[0, 0], [0.10, 0.010], [0.20, 0.041], [0.30, 0.093], [0.40, 0.166]]
    chart = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "磁感应强度 B (T)", "y_label": "ΔR/R(0)",
        "title": "磁阻效应曲线", "fit": "quadratic",
    }
    return make_schema(
        "测量磁阻相对变化与磁感应强度的关系（双数据表）",
        [
            make_table("table1", "磁阻相对变化与磁感应强度关系数据表",
                       ["B(T)", "ΔR/R(0)"], sample=sample1, initial_rows=3, chart=chart),
            make_table("table2", "磁阻相对变化与磁感应强度关系数据表（另一组测量）",
                       ["B(T)", "ΔR/R(0)"], sample=sample2, initial_rows=3, chart=chart),
        ],
        analysis_hints="分别检查两组数据的单调性、弱磁场下与 B² 的近似关系以及两组测量的一致性。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["两组磁阻效应数据已接收，可分别绘制 ΔR/R(0)-B 曲线并比较。"],
    )
