"""非平衡电桥实验模块
=================
二级大物电磁学实验 —— 非平衡电桥

实验内容：
测量非平衡电桥输出电压 Ug 与电阻相对变化 δ=ΔR/R₀ 的关系。
本实验包含两组独立测量（不同桥臂电阻条件），
每组数据独立进行异常检验和图表生成，
最终合并两组数据生成完整实验报告。

物理背景：
非平衡电桥是一种常用的测量电路，当桥臂电阻发生变化时，
电桥失去平衡，输出端产生电压差 Ug。
在小变化条件下，Ug 与 δ=ΔR/R₀ 近似成线性关系：
    Ug ≈ (E/4) · δ
其中 E 为激励电压。不同桥臂电阻 R₀ 会影响灵敏度和线性范围。
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

def name(): # 返回实验名称
    return "非平衡电桥"

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
        # 自动识别列
        r4_col = [c for c in cols if 'R4' in c or 'R_4' in c][0] if any('R4' in c or 'R_4' in c for c in cols) else cols[0]
        ug_col = [c for c in cols if 'Ug' in c or 'U_g' in c or '电压' in c][0] if any('Ug' in c or 'U_g' in c or '电压' in c for c in cols) else cols[1]

        R4 = pd.to_numeric(data[r4_col], errors='coerce')
        Ug = pd.to_numeric(data[ug_col], errors='coerce')

        # 找出R0（Ug最接近0时的R4）和Us（电源电压，从列名或数据推断）
        R0 = R4.iloc[Ug.abs().idxmin()]
        Us = 5.0  # 默认电源电压5V

        delta_R = R4 - R0
        delta = delta_R / R0

        # 理论非平衡电压：Ug_theory = Us/4 * delta / (1 + delta/2)
        Ug_theory = (Us / 4.0) * delta / (1.0 + delta / 2.0)

        # 线性近似：Ug_linear = Us/4 * delta
        Ug_linear = (Us / 4.0) * delta

        # 线性范围的判定：相对偏差 < 5%
        rel_err = abs(Ug_linear - Ug) / abs(Ug_linear.where(abs(Ug_linear) > 1e-10, 1e-10))

        # 零点的绝对灵敏度
        idx_near_zero = delta.abs().argsort()[:5]
        S_Ua = np.mean([abs(Ug.iloc[i] / delta_R.iloc[i]) if abs(delta_R.iloc[i]) > 1e-10 else 0 for i in idx_near_zero])

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("平衡点 R0 = {:.2f} Ω".format(R0))
        docu.add_paragraph("电源电压 Us = {:.1f} V".format(Us))
        docu.add_paragraph("零点绝对灵敏度 S_Ua = {:.4f} mV/Ω".format(S_Ua * 1000))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(R4)+1, cols=6, style='Table Grid')
        headers = ['R4 (Ω)', 'ΔR (Ω)', 'δ=ΔR/R0', 'Ug实测(mV)', 'Ug线性(mV)', '相对偏差 δ_lin(%)']
        for j, h in enumerate(headers):
            table.rows[0].cells[j].text = h
        for i in range(len(R4)):
            table.rows[i+1].cells[0].text = '{:.2f}'.format(R4.iloc[i])
            table.rows[i+1].cells[1].text = '{:.2f}'.format(delta_R.iloc[i])
            table.rows[i+1].cells[2].text = '{:.5f}'.format(delta.iloc[i])
            table.rows[i+1].cells[3].text = '{:.4f}'.format(Ug.iloc[i])
            table.rows[i+1].cells[4].text = '{:.4f}'.format(Ug_linear.iloc[i])
            table.rows[i+1].cells[5].text = '{:.2f}'.format(rel_err.iloc[i] * 100)
        docu.add_paragraph()

        # 线性范围
        linear_range = delta_R[rel_err <= 0.05]
        if len(linear_range) > 0:
            docu.add_paragraph("线性范围（相对偏差 ≤ 5%）：ΔR ∈ [{:.2f}, {:.2f}] Ω".format(
                linear_range.min(), linear_range.max()))

        docu.add_paragraph()
        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("平衡点 R_0 = {:.2f} \\Omega".format(R0))
        docu.add_paragraph("零点绝对灵敏度 S_{U_a} = {:.4f} mV/\\Omega".format(S_Ua * 1000))
        docu.add_paragraph()
        docu.add_paragraph("非平衡电桥输出电压公式：")
        docu.add_paragraph("U_g = \\frac{U_s}{4}\\cdot\\frac{\\delta}{1+\\delta/2},\\quad \\delta = \\frac{\\Delta R}{R_0}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    _all = load_sample_data_numeric("exp27", "exp27_example")
    _mid = len(_all) // 2
    sample1 = _all[:_mid] or _all
    sample2 = _all[_mid:] or _all
    chart = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "R4 (Ω)", "y_label": "Ug (mV)",
        "title": "非平衡电桥输出特性", "fit": "linear",
    }
    return make_schema(
        (
            "本实验研究非平衡电桥：外接电阻箱改变桥臂电阻，记录桥路输出电压 " r"$U_g$"
            " 与电阻改变量，计算 " r"$\delta = \Delta R/R_0$" "，分析输出电压的线性关系、"
            "灵敏度与线性范围，并测量铜丝电阻的温度系数。"
        ),
        [
            make_table("table1", "非平衡电桥输出电压与电阻相对变化关系数据表",
                       ["R4(Ω)", "Ug(mV)", "δ=ΔR/R₀", "线性近似电压 Ug_lin(mV)", "相对偏差 δ_lin(%)"],
                       sample=sample1, readonly=(2, 3, 4), initial_rows=3, chart=chart),
            make_table("table2", "不同桥臂电阻下非平衡电桥输出特性数据表",
                       ["R4(Ω)", "Ug(mV)", "δ=ΔR/R₀", "线性近似电压 Ug_lin(mV)", "相对偏差 δ_lin(%)"],
                       sample=sample2, readonly=(2, 3, 4), initial_rows=3, chart=chart),
        ],
        analysis_hints="分别检查两组输出曲线的线性、零点偏移、灵敏度及线性范围。",
        preview_enabled=True,
        table_theory=get_table_theory("exp27"),)


def preview(payload):
    """实时计算 δ=ΔR/R₀、Ug_线性和相对偏差。

    取 Ug 最接近 0 时的 R4 作为 R₀，默认电源电压 Us=5V。
    """
    Us = 5.0  # 默认电源电压
    tables = copied_tables(payload)
    for table_id in ("table1", "table2"):
        rows = tables.get(table_id, [])
        # 第一遍：找 R0（Ug 最接近 0 时的 R4）
        r0, min_ug = None, float('inf')
        for row in rows:
            r4 = as_number(row.get("c0"))
            ug = as_number(row.get("c1"))
            if r4 is not None and ug is not None and abs(ug) < min_ug:
                min_ug = abs(ug)
                r0 = r4
        # 第二遍：计算派生值
        for row in rows:
            r4 = as_number(row.get("c0"))
            ug = as_number(row.get("c1"))
            if r4 is not None and r0 not in (None, 0):
                delta = (r4 - r0) / r0
                row["c2"] = formatted(delta, 5)
                if ug is not None:
                    ug_linear = (Us / 4.0) * delta
                    row["c3"] = formatted(ug_linear, 4)
                    if abs(ug_linear) > 1e-10:
                        row["c4"] = formatted(abs(ug - ug_linear) / abs(ug_linear) * 100, 2)
                    else:
                        row["c4"] = ""
                else:
                    row["c3"] = ""
                    row["c4"] = ""
            else:
                row["c2"] = ""
                row["c3"] = ""
                row["c4"] = ""
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["两组非平衡电桥数据已接收，可分别拟合输出电压与相对电阻变化的关系。"],
    )
