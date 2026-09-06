from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "空气阻尼"

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
        # 识别：A_i(振幅), t_i(时刻s)
        a_col = [c for c in cols if 'A' in c or '振幅' in c or 'amp' in c.lower()][0] if any('A' in c or '振幅' in c or 'amp' in c.lower() for c in cols) else cols[0]
        t_col = [c for c in cols if 't' in c or '时间' in c or 'time' in c.lower()][0] if any('t' in c or '时间' in c or 'time' in c.lower() for c in cols) else cols[1]

        A_amp = pd.to_numeric(data[a_col], errors='coerce')
        t_time = pd.to_numeric(data[t_col], errors='coerce')

        # 对数减幅 Λ = ln(A_n / A_{n+1})
        ln_ratio = np.log(A_amp.iloc[:-1].values / A_amp.iloc[1:].values)
        Lambda_dec = pd.Series(ln_ratio)

        # 阻尼系数 β = Λ / T (需要周期T的数据，从时间差获取)
        dT = t_time.diff().iloc[1:].values
        T_avg = dT.mean() if len(dT) > 0 else 1.0
        beta = Lambda_dec / T_avg

        res_Lambda = analyse(Lambda_dec, 0, 0, r'\Lambda', '', confidence_C=3)

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("阻尼振动实验：空气阻尼测量")
        docu.add_paragraph("平均周期 T = {:.4f} s".format(T_avg))
        docu.add_paragraph("阻尼系数 β = {:.4f} s⁻¹".format(beta.mean()))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(A_amp)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['t (s)', 'A', 'Λ = ln(A_n/A_{n+1})', 'β (s⁻¹)']):
            table.rows[0].cells[j].text = h
        for i in range(len(A_amp)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(t_time.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(A_amp.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(Lambda_dec.iloc[i-1]) if i>0 else '--'
            table.rows[i+1].cells[3].text = '{:.4f}'.format(beta.iloc[i-1]) if i>0 else '--'
        docu.add_paragraph()

        insert_data(docu, "对数减幅 Λ", res_Lambda, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "对数减幅 Λ", res_Lambda, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("\\Lambda = \\ln\\frac{A_n}{A_{n+1}} = \\beta T")
        docu.add_paragraph("\\beta = \\frac{\\Lambda}{T}")
        docu.add_paragraph("品质因数：Q = \\frac{\\pi}{\\Lambda}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample=load_sample_data_numeric("exp45", "exp45_example")
    table = make_table(
        "table1", "空气阻尼振幅衰减数据表", ["t", "A"], sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "时间 t", "y_label": "振幅 A",
               "title": "空气阻尼振幅衰减曲线", "fit": "auto"},
    )
    return make_schema(
        (
            "本实验研究空气阻尼与风速的规律。请记录振幅随时间衰减的数据（" r"$t$" "、"
            r"$A$" "），由 " r"$\beta = \frac{1}{T}\ln\frac{A_n}{A_{n+1}}$" " 求阻尼系数，"
            "分析风阻与形状、风速的关系。"
        ),
        [table], analysis_hints="检查振幅是否按指数规律衰减以及是否存在突变点。",
        table_theory=get_table_theory("exp45"), report_enabled=False,)


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
