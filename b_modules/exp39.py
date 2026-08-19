from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table

def name():
    return "F-H实验"

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
        # 识别：U(V加速电压), I(pA电流)
        u_col = [c for c in cols if 'U' in c or '电压' in c or '加速' in c][0] if any('U' in c or '电压' in c or '加速' in c for c in cols) else cols[0]
        i_col = [c for c in cols if 'I' in c or '电流' in c or 'pA' in c][0] if any('I' in c or '电流' in c or 'pA' in c for c in cols) else cols[1]

        U = pd.to_numeric(data[u_col], errors='coerce')  # V
        I = pd.to_numeric(data[i_col], errors='coerce')  # pA

        # 找峰值位置（峰位U值）
        # 简单方法：用滑窗找极大值
        peaks = []
        peaks_U = []
        for i in range(1, len(I)-1):
            if I.iloc[i] > I.iloc[i-1] and I.iloc[i] > I.iloc[i+1]:
                # 确认是极大值
                if I.iloc[i] > I.median() * 1.2:  # 需显著高于中位数
                    peaks.append(i)
                    peaks_U.append(U.iloc[i])

        # 相邻峰间距 → 激发电位
        if len(peaks_U) >= 2:
            delta_U_vals = np.diff(peaks_U)
            res_deltaU = analyse(pd.Series(delta_U_vals), 0, 0, r'\Delta U', 'V')
            U_excitation = pd.Series(delta_U_vals).mean()
        else:
            U_excitation = 0
            res_deltaU = None

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("Franck-Hertz 实验：氩原子激发")
        docu.add_paragraph("检测到 {} 个峰".format(len(peaks_U)))
        if len(peaks_U) >= 2:
            docu.add_paragraph("激发电位 U_exc = {:.2f} V".format(U_excitation))
            docu.add_paragraph("各峰位：{}".format(["{:.2f}".format(u) for u in peaks_U]))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=min(len(U)+1, 51), cols=2, style='Table Grid')
        table.rows[0].cells[0].text = 'U (V)'
        table.rows[0].cells[1].text = 'I (pA)'
        for i in range(min(len(U), 50)):
            table.rows[i+1].cells[0].text = '{:.1f}'.format(U.iloc[i])
            table.rows[i+1].cells[1].text = '{:.1f}'.format(I.iloc[i])
        docu.add_paragraph()

        if res_deltaU is not None:
            insert_data(docu, "激发电位 ΔU", res_deltaU, "word")
            docu.add_paragraph()
            docu.add_paragraph("【Latex代码】")
            insert_data(docu, "激发电位 ΔU", res_deltaU, "latex")
            docu.add_paragraph()

        docu.add_paragraph("公式：E = e \\cdot \\Delta U = hc/\\lambda")
        docu.add_paragraph("氩原子第一激发态能量（标准值）：~11.6 eV")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample = [
        [0.0, 0.0], [2.0, 0.1], [4.0, 0.2], [6.0, 0.3], [8.0, 0.5], [10.0, 0.8],
        [11.5, 3.2], [12.0, 2.0], [13.0, 1.2], [14.0, 1.0], [15.0, 1.5], [16.0, 2.8],
        [16.5, 1.5], [17.0, 1.0], [18.0, 1.2], [19.0, 2.5], [19.5, 1.3], [20.0, 0.8],
        [22.0, 1.0], [23.5, 4.5], [24.0, 2.8], [25.0, 1.5], [26.0, 1.2], [27.0, 2.2],
        [28.0, 5.8], [28.5, 3.2], [29.0, 1.8], [30.0, 1.5], [31.0, 2.0], [32.0, 3.5],
        [33.5, 7.2], [34.0, 4.5], [35.0, 2.5], [36.0, 2.0], [37.0, 2.8], [38.0, 4.2],
        [39.0, 8.8], [39.5, 5.5], [40.0, 3.2],
    ]
    table = make_table(
        "table1", "F-H 实验伏安特性数据表", ["U", "I"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "加速电压 U", "y_label": "板极电流 I",
               "title": "F-H 实验伏安特性曲线", "fit": "auto"},
    )
    return make_schema("F-H实验伏安特性与激发电位分析。", [table], analysis_hints="重点识别相邻电流峰的电压间隔。")


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
