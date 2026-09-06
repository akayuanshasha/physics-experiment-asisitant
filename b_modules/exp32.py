"""双臂电桥实验模块
===============
二级大物电磁学实验 —— 双臂电桥

实验内容：
本实验包含四组数据表：
1. 铜棒与铝棒直径测量数据表（6次测量）
2. 30cm铜棒与铝棒电阻及电阻率测量表（3组正反向电流）
3. 不同长度铜棒电阻及均匀性数据表（7个长度）
4. Rx-L关系曲线图（散点+线性拟合）

每组数据独立进行自动计算，
表格4含异常检验和图表生成，
最终合并所有数据生成综合实验报告。

物理背景：
双臂电桥（开尔文电桥）适用于测量低电阻（10⁻⁶~10² Ω）。
通过四端钮接线消除接触电阻和引线电阻的影响。
电阻率公式：ρ = Rx·S/L = Rx·πD²/(4L)
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "双臂电桥"

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
        # 识别列：L(cm), R(Ω), D(mm)
        l_col = [c for c in cols if 'L' in c or '长度' in c][0] if any('L' in c or '长度' in c for c in cols) else cols[0]
        r_col = [c for c in cols if 'R' in c or '电阻' in c][0] if any('R' in c or '电阻' in c for c in cols) else cols[1]
        d_col = [c for c in cols if 'D' in c or '直径' in c][0] if any('D' in c or '直径' in c for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        L = pd.to_numeric(data[l_col], errors='coerce')  # cm
        R = pd.to_numeric(data[r_col], errors='coerce')  # Ω
        D = pd.to_numeric(data[d_col], errors='coerce')  # mm

        # R1=R2=1000Ω, Rn=0.001Ω
        R1 = 1000.0
        Rn = 0.001
        # Rx = R/R1 * Rn
        Rx = R / R1 * Rn

        # 截面积 S = πD²/4
        S_area = np.pi * (D/1000)**2 / 4  # m²

        # 电阻率 ρ = Rx * S / L
        rho = Rx * S_area / (L / 100)  # Ω·m

        res_rho = analyse(rho, 0, 0, r'\rho', r'\Omega\cdot m', confidence_C=3)

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("双臂电桥参数：R1=R2={:.0f}Ω, Rn={:.4f}Ω".format(R1, Rn))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(L)+1, cols=6, style='Table Grid')
        for j, h in enumerate(['L (cm)', 'R (Ω)', 'D (mm)', 'Rx (Ω)', 'S (m²)', 'ρ (Ω·m)']):
            table.rows[0].cells[j].text = h
        for i in range(len(L)):
            table.rows[i+1].cells[0].text = '{:.1f}'.format(L.iloc[i])
            table.rows[i+1].cells[1].text = '{:.6f}'.format(R.iloc[i])
            table.rows[i+1].cells[2].text = '{:.3f}'.format(D.iloc[i])
            table.rows[i+1].cells[3].text = '{:.8f}'.format(Rx.iloc[i])
            table.rows[i+1].cells[4].text = '{:.10f}'.format(S_area.iloc[i])
            table.rows[i+1].cells[5].text = '{:.4e}'.format(rho.iloc[i])
        docu.add_paragraph()

        insert_data(docu, "电阻率 ρ", res_rho, "word")
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        insert_data(docu, "电阻率 ρ", res_rho, "latex")
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("R_x = \\frac{R}{R_1} R_n")
        docu.add_paragraph("\\rho = R_x \\frac{S}{L} = R_x \\frac{\\pi D^2}{4L}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    _s1 = load_sample_data_numeric("exp32", "exp32_table1")
    _s2 = load_sample_data_numeric("exp32", "exp32_table2")
    _s3 = load_sample_data_numeric("exp32", "exp32_table3")
    _s4 = load_sample_data_numeric("exp32", "exp32_table4")
    resistance_labels = ["L(cm)", "正向R+(Ω)", "反向R-(Ω)", "待测电阻Rx(mΩ)", "单点电阻率ρ(10⁻⁸Ω·m)"]
    chart = {"x_column": "c0", "y_column": "c3", "x_label": "电压头间距 L (cm)",
             "y_label": "待测电阻 Rx (mΩ)", "title": "Rx-L 线性关系", "fit": "linear"}
    return make_schema(
        (
            "本实验用双臂电桥测量低电阻：① 测量铜、铝棒直径；② 正反向测量 30 cm 电阻；"
            "③ 测量不同长度下的电阻均匀性；④ 由 " r"$R_x$" r"–$L$" " 线性拟合计算电阻率 "
            r"$\rho = R_x S/L$" "。"
        ),
        [
            make_table(
                "table1", "铜棒与铝棒直径测量数据表",
                ["测量次数", "铜棒直径DCu(mm)", "铝棒直径DAl(mm)"],
                sample=_s1,
                readonly=(0,), initial_rows=6,
            ),
            make_table(
                "table2", "30cm铜棒与铝棒电阻及电阻率测量表",
                ["测量组别", "铜棒正向RCu+(Ω)", "铜棒反向RCu-(Ω)", "铝棒正向RAl+(Ω)", "铝棒反向RAl-(Ω)"],
                sample=_s2,
                readonly=(0,), initial_rows=3,
            ),
            make_table("table3", "不同长度铜棒电阻及均匀性数据表", resistance_labels,
                       sample=_s3, readonly=(3, 4), initial_rows=7, chart=chart),
            make_table("table4", "Rx-L 关系数据表（拟合用）", resistance_labels,
                       sample=_s4, readonly=(3, 4), initial_rows=7, chart=chart),
        ],
        analysis_hints="检查直径重复性、正反向电阻的一致性、电阻率合理性及 Rx-L 线性关系。",
        preview_enabled=True,
        table_theory=get_table_theory("exp32"),)


def preview(payload):
    tables = copied_tables(payload)
    diameters = [as_number(row.get("c1")) for row in tables.get("table1", [])]
    diameters = [value for value in diameters if value is not None]
    diameter = sum(diameters) / len(diameters) if diameters else None
    for index, row in enumerate(tables.get("table1", [])):
        row["c0"] = index + 1
    for index, row in enumerate(tables.get("table2", [])):
        row["c0"] = index + 1
    for table_id in ("table3", "table4"):
        for row in tables.get(table_id, []):
            length, positive, negative = (as_number(row.get(key)) for key in ("c0", "c1", "c2"))
            measured = (positive + negative) / 2 if positive is not None and negative is not None else None
            rx_ohm = measured * 1e-6 if measured is not None else None
            rx_milliohm = rx_ohm * 1000 if rx_ohm is not None else None
            rho = None
            if rx_ohm is not None and diameter not in (None, 0) and length not in (None, 0):
                rho = rx_ohm * np.pi * (diameter * 1e-3) ** 2 / (4 * length * 1e-2) * 1e8
            row["c3"] = formatted(rx_milliohm, 6)
            row["c4"] = formatted(rho, 4)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["序号、待测电阻和单点电阻率已由模块后端计算。"],
    )
