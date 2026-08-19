from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table

def name():
    return "超声定位与形貌成像"

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
        # 超声光栅变体：可能使用不同液体或不同频率组合
        f_col = [c for c in cols if 'f' in c or '频率' in c][0] if any('f' in c or '频率' in c for c in cols) else cols[0]
        dx_col = [c for c in cols if 'Δx' in c or '间距' in c or 'x' in c][0] if any('Δx' in c or '间距' in c or 'x' in c for c in cols) else cols[1]
        k_col = [c for c in cols if 'k' in c or '级次' in c][0] if any('k' in c or '级次' in c for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        f_us = pd.to_numeric(data[f_col], errors='coerce')
        delta_x = pd.to_numeric(data[dx_col], errors='coerce')
        k = pd.to_numeric(data[k_col], errors='coerce') if k_col != dx_col else pd.Series(range(1, len(f_us)+1))

        L_dist = 500.0
        lam = 632.8e-6

        Lambda = k * lam * L_dist / delta_x
        v_sound_ms = Lambda * f_us * 1e6 / 1000

        res_v = analyse(v_sound_ms, 0, 0, 'v', 'm/s')

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("超声光栅实验（变体）")
        docu.add_paragraph("激光波长 λ = 632.8 nm")
        docu.add_paragraph()

        table = docu.add_table(rows=len(f_us)+1, cols=5, style='Table Grid')
        for j, h in enumerate(['f (MHz)', 'Δx (mm)', 'k', 'Λ (mm)', 'v (m/s)']):
            table.rows[0].cells[j].text = h
        for i in range(len(f_us)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(f_us.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(delta_x.iloc[i])
            table.rows[i+1].cells[2].text = '{:.0f}'.format(k.iloc[i])
            table.rows[i+1].cells[3].text = '{:.6f}'.format(Lambda.iloc[i])
            table.rows[i+1].cells[4].text = '{:.2f}'.format(v_sound_ms.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "声速 v", res_v, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "声速 v", res_v, "latex")
        docu.add_paragraph()
        docu.add_paragraph("v = \\Lambda \\cdot f = \\frac{k\\lambda L}{\\Delta x} \\cdot f")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample = [[2.0, 30.2, 2], [3.0, 20.1, 2], [4.0, 15.1, 2], [5.0, 12.1, 2]]
    table = make_table(
        "table1", "超声定位与形貌成像数据表", ["f", "delta_x", "k"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "超声频率 f", "y_label": "测量间距 Δx",
               "title": "超声定位测量曲线", "fit": "auto"},
    )
    return make_schema("利用超声传播参数进行定位与形貌测量。", [table], analysis_hints="检查级次、频率和测量间距的一致性。")


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
