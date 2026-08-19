from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table

def name():
    return "凯特摆"

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
        # 识别：T(s周期), h1(cm正挂), h2(cm倒挂), l(cm周期等效摆长)
        t_col = [c for c in cols if 'T' in c or '周期' in c][0] if any('T' in c or '周期' in c for c in cols) else cols[0]
        h1_col = [c for c in cols if 'h1' in c or '正挂' in c][0] if any('h1' in c or '正挂' in c for c in cols) else (cols[1] if len(cols)>1 else cols[0])
        h2_col = [c for c in cols if 'h2' in c or '倒挂' in c][0] if any('h2' in c or '倒挂' in c for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        T_val = pd.to_numeric(data[t_col], errors='coerce')  # s
        h1 = pd.to_numeric(data[h1_col], errors='coerce')  # cm
        h2 = pd.to_numeric(data[h2_col], errors='coerce')  # cm

        # 等效摆长 l = h1 + h2 (可逆摆条件)
        l_eq = h1 + h2  # cm

        # 正挂 T₁、倒挂 T₂，应接近相等
        # 重力加速度 g = 4π²l / T²
        # 若 T1≈T2，取平均 T
        g_calc = 4 * np.pi**2 * l_eq / (T_val**2)  # cm/s²
        g_calc_ms2 = g_calc / 100  # m/s²

        res_g = analyse(g_calc_ms2, 0, 0, 'g', 'm/s^2')

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("凯特摆（可逆摆）测重力加速度")
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(T_val)+1, cols=5, style='Table Grid')
        for j, h in enumerate(['T (s)', 'h1 (cm)', 'h2 (cm)', 'l_eq (cm)', 'g (m/s²)']):
            table.rows[0].cells[j].text = h
        for i in range(len(T_val)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(T_val.iloc[i])
            table.rows[i+1].cells[1].text = '{:.2f}'.format(h1.iloc[i])
            table.rows[i+1].cells[2].text = '{:.2f}'.format(h2.iloc[i])
            table.rows[i+1].cells[3].text = '{:.2f}'.format(l_eq.iloc[i])
            table.rows[i+1].cells[4].text = '{:.4f}'.format(g_calc_ms2.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "重力加速度 g", res_g, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "重力加速度 g", res_g, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("l_{eq} = h_1 + h_2")
        docu.add_paragraph("g = \\frac{4\\pi^2 l}{T^2}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample = [[1.52, 30.0, 42.5], [1.518, 30.0, 42.5], [1.521, 30.0, 42.5],
              [1.519, 30.0, 42.5], [1.522, 30.0, 42.5]]
    table = make_table(
        "table1", "凯特摆测量数据表", ["T", "h1", "h2"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "周期 T", "y_label": "刀口位置 h1",
               "title": "凯特摆测量数据检查", "fit": "auto"},
    )
    return make_schema("利用凯特摆周期与刀口位置测量重力加速度。", [table], analysis_hints="检查周期重复性及两个刀口位置的记录一致性。")


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
