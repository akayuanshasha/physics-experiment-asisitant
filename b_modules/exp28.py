from head import * # 导入万能头
from structured_support import make_schema, make_table, structured_result

def name():
    return "霍尔效应"

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
        # 识别数据列：IS(工作电流mA), V1, V2, V3, V4(四组霍尔电压mV) 或 IM, VH
        is_col = [c for c in cols if 'IS' in c or 'I_S' in c or '工作电流' in c][0] if any('IS' in c or 'I_S' in c or '工作电流' in c for c in cols) else cols[0]
        vh_cols = [c for c in cols if 'V' in c and ('1' in c or '2' in c or '3' in c or '4' in c or 'H' in c)]

        IS = pd.to_numeric(data[is_col], errors='coerce')

        if len(vh_cols) >= 4:
            V1 = pd.to_numeric(data[vh_cols[0]], errors='coerce')
            V2 = pd.to_numeric(data[vh_cols[1]], errors='coerce')
            V3 = pd.to_numeric(data[vh_cols[2]], errors='coerce')
            V4 = pd.to_numeric(data[vh_cols[3]], errors='coerce')
            VH = (abs(V1) + abs(V2) + abs(V3) + abs(V4)) / 4.0
        elif len(vh_cols) >= 1:
            VH = pd.to_numeric(data[vh_cols[0]], errors='coerce')
        else:
            VH = pd.to_numeric(data[cols[1]], errors='coerce')

        # 霍尔元件参数
        d = 0.3  # mm 厚度
        b = 4.0  # mm 宽度
        l = 2.0  # mm 长度

        # 线性拟合 VH-IS
        res_lsm = analyse_lsm(IS, VH, 'I_S', 'V_H', 'mA', 'mV')

        # KH = VH / (IS * B)，若B由IM产生则另行计算
        # 根据实验指导，IM=0.45A时B已知，或直接计算KH
        if len(IS) > 1:
            KH = res_lsm.m  # mV/mA 斜率即 KH*B (在固定B下)
        else:
            KH = VH.iloc[0] / IS.iloc[0]

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()
        docu.add_paragraph("霍尔元件参数：d={:.1f}mm, b={:.1f}mm, l={:.1f}mm".format(d, b, l))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(IS)+1, cols=3, style='Table Grid')
        for j, h in enumerate(['I_S (mA)', 'V_H (mV)', 'V_H/I_S (mV/mA)']):
            table.rows[0].cells[j].text = h
        for i in range(len(IS)):
            table.rows[i+1].cells[0].text = '{:.3f}'.format(IS.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(VH.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(VH.iloc[i]/IS.iloc[i] if IS.iloc[i] != 0 else 0)
        docu.add_paragraph()

        docu.add_paragraph("V_H-I_S 线性拟合")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("霍尔元件参数：d={:.1f}\\,\\mathrm{{mm}},\\ b={:.1f}\\,\\mathrm{{mm}},\\ l={:.1f}\\,\\mathrm{{mm}}".format(d, b, l))
        docu.add_paragraph()
        docu.add_paragraph("V_H-I_S 线性拟合：")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()
        docu.add_paragraph("霍尔灵敏度 K_H = \\frac{{V_H}}{{I_S B}}（需已知磁场B）")
        docu.add_paragraph("载流子浓度 n = \\frac{{1}}{{K_H e d}}")
        docu.add_paragraph("迁移率 \\mu = \\frac{{\\sigma}}{{n e}}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    return make_schema(
        "霍尔效应实验（三数据表：VH-IS、VH-IM、RH-T）",
        [
            make_table(
                "table1", "霍尔电压与控制电流关系数据表",
                ["IS(mA)", "VH(mV)"],
                sample=[[1, 2.12], [2, 4.25], [3, 6.37], [4, 8.49], [5, 10.62]],
                initial_rows=3,
                chart={"x_column": "c0", "y_column": "c1", "x_label": "控制电流 IS (mA)",
                       "y_label": "霍尔电压 VH (mV)", "title": "霍尔电压与控制电流关系数据表", "fit": "linear"},
            ),
            make_table(
                "table2", "霍尔电压与励磁电流关系数据表",
                ["IM(A)", "VH(mV)"],
                sample=[[0.10, 1.35], [0.20, 2.70], [0.30, 4.06], [0.40, 5.39], [0.50, 6.76]],
                initial_rows=3,
                chart={"x_column": "c0", "y_column": "c1", "x_label": "励磁电流 IM (A)",
                       "y_label": "霍尔电压 VH (mV)", "title": "霍尔电压与励磁电流关系数据表", "fit": "linear"},
            ),
            make_table(
                "table3", "霍尔效应参数随温度变化关系数据表",
                ["T(℃)", "RH(m³/C)"],
                sample=[[20, 3.80e-4], [30, 3.72e-4], [40, 3.64e-4], [50, 3.56e-4], [60, 3.49e-4]],
                initial_rows=3,
                chart={"x_column": "c0", "y_column": "c1", "x_label": "温度 T (℃)",
                       "y_label": "霍尔系数 RH (m³/C)", "title": "霍尔效应参数随温度变化关系数据表", "fit": "auto"},
            ),
        ],
        analysis_hints="检查两组霍尔电压关系的线性以及霍尔系数随温度变化的趋势。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["三组霍尔效应数据已接收，可分别分析 VH-IS、VH-IM 和 RH-T 关系。"],
    )
