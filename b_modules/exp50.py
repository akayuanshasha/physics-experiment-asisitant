from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table

def name():
    return "医学物理实验"

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
        # 医学物理实验：可能涉及超声A超/B超，X射线衰减，血流测量等
        # 灵活识别数据列，做通用统计处理
        x_col = cols[0]
        y_col = cols[1] if len(cols) > 1 else cols[0]

        x_val = pd.to_numeric(data[x_col], errors='coerce')
        y_val = pd.to_numeric(data[y_col], errors='coerce')

        # 尝试识别实验类型
        # 如果是半衰期数据：时间和计数 → ln(N) vs t
        if any('t' in x_col.lower() or '时间' in x_col or 'T' in x_col.upper() for _ in [1]):
            # 可能是放射性衰变：ln(y) vs x
            if (y_val > 0).all():
                ln_y = np.log(y_val)
                res_lsm = analyse_lsm(x_val, ln_y, x_col, r'\ln('+y_col+')', '', '')
                # 衰变常数 λ = -slope, 半衰期 T1/2 = ln2/λ
                lam = -res_lsm.b
                t_half = np.log(2) / lam if abs(lam) > 1e-10 else 0
                is_decay = True
            else:
                is_decay = False
        else:
            is_decay = False

        # 通用：线性拟合
        res_lsm = analyse_lsm(x_val, y_val, x_col, y_col, '', '')

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("医学物理综合实验")
        docu.add_paragraph()

        if is_decay:
            docu.add_paragraph("放射性衰变分析：")
            docu.add_paragraph("衰变常数 λ = {:.6f} s⁻¹".format(lam))
            docu.add_paragraph("半衰期 T₁/₂ = {:.2f} s".format(t_half))
            docu.add_paragraph()

        docu.add_paragraph("数据线性拟合")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(x_val)+1, cols=len(cols), style='Table Grid')
        for j in range(len(cols)):
            table.rows[0].cells[j].text = cols[j]
        for i in range(len(x_val)):
            for j in range(len(cols)):
                try:
                    v = pd.to_numeric(data[cols[j]], errors='coerce').iloc[i]
                    table.rows[i+1].cells[j].text = '{:.4f}'.format(v)
                except:
                    table.rows[i+1].cells[j].text = str(data[cols[j]].iloc[i])
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()

        if is_decay:
            docu.add_paragraph("衰变规律：N = N_0 e^{-\\lambda t}")
            docu.add_paragraph("\\lambda = {:.6f} \\,\\mathrm{{s^{{-1}}}}".format(lam))
            docu.add_paragraph("T_{{1/2}} = \\frac{{\\ln 2}}{{\\lambda}} = {:.2f} \\,\\mathrm{{s}}".format(t_half))

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample = [[0, 1000], [30, 856], [60, 732], [90, 626], [120, 536], [150, 459],
              [180, 393], [210, 336], [240, 288], [270, 246], [300, 211]]
    table = make_table(
        "table1", "医学物理计数衰减数据表", ["t", "N"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "时间 t", "y_label": "计数 N",
               "title": "计数随时间衰减曲线", "fit": "auto"},
    )
    return make_schema("根据计数随时间的变化分析医学物理衰减过程。", [table], analysis_hints="检查本底、计数统计涨落和指数衰减规律。")


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
