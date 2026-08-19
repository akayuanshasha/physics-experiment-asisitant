from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)

def name():
    return "交流谐振电路"

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
        # 识别：f(kHz), V_Rpp(V), V_ipp(V) 或 R(Ω)
        f_col = [c for c in cols if 'f' in c or '频率' in c][0] if any('f' in c or '频率' in c for c in cols) else cols[0]
        vr_col = [c for c in cols if 'V_R' in c or 'VR' in c][0] if any('V_R' in c or 'VR' in c for c in cols) else cols[1]
        vi_col = [c for c in cols if 'V_i' in c or 'VI' in c or '输入' in c][0] if any('V_i' in c or 'VI' in c or '输入' in c for c in cols) else (cols[2] if len(cols) > 2 else cols[1])

        f = pd.to_numeric(data[f_col], errors='coerce')  # kHz
        VR = pd.to_numeric(data[vr_col], errors='coerce')  # Vpp
        VI = pd.to_numeric(data[vi_col], errors='coerce') if vi_col != vr_col else pd.Series([2.0]*len(f))

        # 已知参数
        R_val = 400.0  # Ω，默认R=400Ω
        L = 10.0  # mH
        C_val = 0.1  # μF

        # 找谐振频率（VR最大值对应的频率）
        idx_max = VR.idxmax()
        f0 = f.iloc[idx_max]
        I_pp = VR / R_val  # 电流峰峰值

        # Q值计算（多种方法）
        # 方法6：f0/Δf（带宽法，从0.707*I_max处取）
        I_max = I_pp.max()
        half_power = I_max / np.sqrt(2)
        # 找半功率点
        above_hp = np.where(I_pp >= half_power)[0]
        if len(above_hp) > 1:
            f1 = f.iloc[above_hp[0]]
            f2 = f.iloc[above_hp[-1]]
            delta_f = f2 - f1
            Q6 = f0 / delta_f if delta_f > 0 else 0
        else:
            Q6 = 0
            delta_f = 0

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("谐振频率 f0 = {:.4f} kHz".format(f0))
        docu.add_paragraph("通频带宽度 Δf = {:.4f} kHz".format(delta_f))
        docu.add_paragraph("品质因数 Q = f0/Δf = {:.2f}".format(Q6))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(f)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['f (kHz)', 'V_Rpp (V)', 'V_ipp (V)', 'I_pp (mA)']):
            table.rows[0].cells[j].text = h
        for i in range(len(f)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(f.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(VR.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(VI.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(I_pp.iloc[i] * 1000)
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("谐振频率 f_0 = {:.4f} \\,\\mathrm{{kHz}}".format(f0))
        docu.add_paragraph("通频带宽度 \\Delta f = {:.4f} \\,\\mathrm{{kHz}}".format(delta_f))
        docu.add_paragraph("品质因数 Q = \\frac{{f_0}}{{\\Delta f}} = {:.2f}".format(Q6))
        docu.add_paragraph()
        docu.add_paragraph("RLC串联谐振特性：")
        docu.add_paragraph("f_0 = \\frac{{1}}{{2\\pi\\sqrt{{LC}}}}")
        docu.add_paragraph("Q = \\frac{{\\omega_0 L}}{{R}} = \\frac{{1}}{{\\omega_0 C R}} = \\frac{{f_0}}{{\\Delta f}}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    common_labels = ["测量点", "f(kHz)", "Vi,pp(V)", "VR,pp(V)", "Ipp(mA)"]
    return make_schema(
        "RLC串联谐振电路幅频特性与品质因数测量（三数据表）",
        [
            make_table(
                "table1", "RLC串联电路幅频特性数据表 (R = 400.0 Ω)", common_labels,
                sample=[["低频点", 4.1, 2.0, 1.40, ""], ["谐振点", 5.0, 2.0, 1.95, ""], ["高频点", 6.2, 2.0, 1.38, ""]],
                readonly=(0, 4), text_columns=(0,), initial_rows=3,
                chart={"x_column": "c1", "y_column": "c4", "x_label": "频率 f (kHz)",
                       "y_label": "回路电流 Ipp (mA)", "title": "R=400Ω 幅频特性", "fit": "auto"},
            ),
            make_table(
                "table2", "RLC串联电路幅频特性数据表 (R = 600.0 Ω)", common_labels,
                sample=[["低频点", 3.8, 2.0, 1.25, ""], ["谐振点", 5.0, 2.0, 1.88, ""], ["高频点", 6.8, 2.0, 1.22, ""]],
                readonly=(0, 4), text_columns=(0,), initial_rows=3,
                chart={"x_column": "c1", "y_column": "c4", "x_label": "频率 f (kHz)",
                       "y_label": "回路电流 Ipp (mA)", "title": "R=600Ω 幅频特性", "fit": "auto"},
            ),
            make_table(
                "table3", "品质因数 Q 的不同方法计算与对比表",
                ["测定条件/参数类型", "R=400.0Ω 测量与计算值", "R=600.0Ω 测量与计算值"],
                sample=[["三点法", "", ""], ["电压法", "", ""], ["理论值", "", ""]],
                readonly=(0,), text_columns=(0,), initial_rows=3,
            ),
        ],
        analysis_hints="检查两条幅频曲线的谐振峰、带宽和不同方法得到的品质因数是否一致。",
        preview_enabled=True,
    )


def preview(payload):
    tables = copied_tables(payload)
    labels = ["低频点", "谐振点", "高频点"]
    for table_id, resistance in (("table1", 400.0), ("table2", 600.0)):
        for index, row in enumerate(tables.get(table_id, [])):
            voltage = as_number(row.get("c3"))
            row["c0"] = labels[index] if index < len(labels) else f"测量点{index + 1}"
            row["c4"] = formatted(voltage * 1000 / resistance if voltage is not None else None, 5)
    methods = ["三点法", "电压法", "理论值"]
    for index, row in enumerate(tables.get("table3", [])):
        row["c0"] = methods[index] if index < len(methods) else f"方法{index + 1}"
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["两组幅频数据及品质因数对比数据已处理，回路电流已由模块后端计算。"],
    )
