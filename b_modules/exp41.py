from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "超声光栅"

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
        # 识别：f(MHz频率), Δx_k(mm第k级条纹间距), k(级次)
        f_col = [c for c in cols if 'f' in c or '频率' in c][0] if any('f' in c or '频率' in c for c in cols) else cols[0]
        dx_col = [c for c in cols if 'Δx' in c or '间距' in c or 'x' in c][0] if any('Δx' in c or '间距' in c or 'x' in c for c in cols) else cols[1]
        k_col = [c for c in cols if 'k' in c or '级次' in c or '级' in c][0] if any('k' in c or '级次' in c or '级' in c for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        f_us = pd.to_numeric(data[f_col], errors='coerce')  # MHz
        delta_x = pd.to_numeric(data[dx_col], errors='coerce')  # mm
        k = pd.to_numeric(data[k_col], errors='coerce') if k_col != dx_col else pd.Series(range(1, len(f_us)+1))

        # 已知参数
        L_dist = 500.0  # mm 液槽到观察屏距离
        lam = 632.8e-6  # mm He-Ne激光波长

        # 衍射角 θ ≈ kλ/Δx，光栅常数 Λ = kλL/Δx
        Lambda = k * lam * L_dist / delta_x  # mm

        # 声速 v = Λ * f
        v_sound = Lambda * f_us * 1e6  # mm/s → m/s
        v_sound_ms = v_sound / 1000  # m/s

        res_v = analyse(v_sound_ms, 0, 0, 'v', 'm/s')

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("超声光栅实验")
        docu.add_paragraph("激光波长 λ = 632.8 nm")
        docu.add_paragraph("液槽到屏幕距离 L = {:.0f} mm".format(L_dist))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(f_us)+1, cols=6, style='Table Grid')
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
        docu.add_paragraph("公式：")
        docu.add_paragraph("\\Lambda = \\frac{k\\lambda}{\\sin\\theta} \\approx \\frac{k\\lambda L}{\\Delta x}")
        docu.add_paragraph("v = \\Lambda \\cdot f")
        docu.add_paragraph("纯水中声速标准值 ~1500 m/s")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp41", "exp41_example")
    table = make_table(
        "table1", "超声光栅测量数据表", ["超声频率 f(MHz)", "衍射条纹间距 Δx(mm)", "衍射级次 k"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "超声频率 f (MHz)", "y_label": "衍射条纹间距 Δx (mm)",
               "title": "超声光栅测量曲线", "fit": "auto"},
    )
    return make_schema(
        (
            "本实验利用超声光栅测量液体中的声速。请记录频率 " r"$f$" "、衍射条纹间距 "
            r"$\Delta x$" " 与衍射级次 " r"$k$" "，由 " r"$\Lambda\sin\theta = k\lambda$" " 计算声速。"
        ),
        [table], analysis_hints="检查衍射级次、频率与条纹间距的物理关系。",
        table_theory=get_table_theory("exp41"),)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
