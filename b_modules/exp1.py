"""单摆法测重力加速度实验模块
==============================
本实验包含两部分，共两组数据表：

第一部分：基础内容（重复测量与不确定度计算）
  表格1：单摆重复测量表（6行）
    → 计算摆长均值 l̄、周期均值 T̄、重力加速度 g 及不确定度

第二部分：提升内容（多摆长拟合求 g）
  表格2：不同摆长与周期平方计算表（6行）
  图表1：l - T² 线性拟合图 → 由斜率 k 计算 g = 4π²k

物理公式：
  g = 4π² l̄ / T̄²                    （平均值法）
  g = 4π² · k                        （拟合斜率法，k = Δl/ΔT²）
"""

from head import * # 导入万能头
import math
import numpy as np
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_table_theory

def name(): # 返回实验名称
    return "单摆法测重力加速度"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["l","d","T","n"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["l","d","T","n"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        data["T"]/=data["n"][0] # Pandas Series支持整体运算，相当于数组中的每个元素都做同样的操作

        res_l=analyse(data["l"],0.2,0.05,'l','cm') # 摆线长度的相关值计算
        res_d=analyse(data["d"],0.02,0,'d','mm',confidence_C=3**0.5) # 摆球直径的相关值计算
        res_T=analyse(data["T"],0.01/data["n"][0],0.2/data["n"][0],'T','s') # 周期的相关值计算

        res_L=analyse_com("L=l+d",(("l",res_l.average,res_l.unc),("d",res_d.average/20,res_d.unc/20)),(),"cm")
        res_g=analyse_com("g=4*pi**2*L/T**2",(("L",res_L.ans/100,res_L.unc/100),("T",res_T.average,res_T.unc)),(),"m/s^2")

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("钢卷尺的最大允差为0.2cm，游标卡尺的最大允差为0.002cm，秒表的最大允差为0.01s")
        docu.add_paragraph("钢卷尺和游标卡尺的估计误差为最小分度值的一半，分别为0.05cm和0.001cm")
        docu.add_paragraph("秒表的估计误差为0.2s")
        docu.add_paragraph()

        insert_data(docu, "摆线长度l", res_l, "word")
        insert_data(docu, "摆球直径d", res_d, "word")

        docu.add_paragraph("摆长L")
        docu.add_paragraph()._element.append(latex_to_word(res_L.ansx2))
        docu.add_paragraph("摆长L的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_L.uncx2))

        insert_data(docu, "周期T", res_T, "word")

        docu.add_paragraph("重力加速度g")
        docu.add_paragraph()._element.append(latex_to_word(res_g.ansx2))
        docu.add_paragraph("重力加速度g的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_g.uncx2))
        docu.add_paragraph("重力加速度g最终结果")
        docu.add_paragraph()._element.append(latex_to_word(res_g.finalx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        insert_data(docu, "摆线长度l", res_l, "latex")
        insert_data(docu, "摆球直径d", res_d, "latex")

        docu.add_paragraph("摆长L")
        docu.add_paragraph(res_L.ansx)
        docu.add_paragraph("摆长L的延伸不确定度")
        docu.add_paragraph(res_L.uncx)

        insert_data(docu, "周期T", res_T, "latex")

        docu.add_paragraph("重力加速度g")
        docu.add_paragraph(res_g.ansx)
        docu.add_paragraph("重力加速度g的延伸不确定度")
        docu.add_paragraph(res_g.uncx)
        docu.add_paragraph("重力加速度g最终结果")
        docu.add_paragraph(res_g.finalx)

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1


def _set_units(table, units):
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    # 示例数据：摆线长 x(cm)、摆球直径 d(mm)、累积时间 t(s)、周期数 n。
    # 实际摆长 l = x + d/20，周期 T = t/n，均由后端自动计算。
    table1 = _set_units(
        make_table(
            "table1", "单摆重复测量及不确定度计算表",
            ["序号", "摆线长 x(cm)", "摆球直径 d(mm)",
             "实际摆长 l(cm)", "累积时间 t(s)", "周期数 n", "周期 T(s)"],
            sample=[
                [1, 80.01, 22.00, 81.11, 90.21, 50, 1.8042],
                [2, 80.13, 22.05, 81.2325, 90.30, 50, 1.8060],
                [3, 79.96, 22.02, 81.0610, 90.25, 50, 1.8050],
                [4, 79.99, 22.05, 81.0925, 90.19, 50, 1.8038],
                [5, 80.12, 21.98, 81.2190, 90.14, 50, 1.8028],
            ],
            readonly=(0, 3, 6), min_rows=6, initial_rows=6,
            description="输入摆线长度 x、摆球直径 d、累积时间 t 与周期数 n，实际摆长与周期由后端自动计算。",
        ),
        ["", "cm", "mm", "cm", "s", "", "s"],
    )
    table1["calc"] = {"label": "计算 g 与不确定度", "table": "table1"}
    # 计算按钮与结果置于表格上方（复用模板上方按钮，走 /preview 的 calc_results），
    # 不在表格下方重复生成按钮。
    table1["calc_placement"] = "top"
    chart = {
        "x_column": "c5", "y_column": "c1",
        "x_label": "周期平方 T² (s²)", "y_label": "摆长 l (cm)",
        "title": "l - T² 线性拟合", "fit": "linear",
    }
    table2 = _set_units(
        make_table(
            "table2", "不同摆长与周期平方计算表",
            ["序号", "摆长 l(cm)", "累积时间 t(s)", "周期数 n",
             "周期 T(s)", "周期平方 T²(s²)"],
            sample=[
                [1, 40.0, 63.49, 50, 1.26980, 1.612392],
                [2, 50.0, 70.98, 50, 1.41960, 2.015264],
                [3, 60.0, 77.76, 50, 1.55520, 2.418647],
                [4, 70.0, 83.99, 50, 1.67980, 2.821728],
                [5, 80.0, 89.79, 50, 1.79580, 3.224898],
                [6, 90.0, 95.23, 50, 1.90460, 3.627501],
            ],
            readonly=(0, 4, 5), min_rows=6, initial_rows=6, chart=chart,
            description="输入不同摆长对应的累积时间与周期数，周期与周期平方由后端自动计算。",
        ),
        ["", "cm", "s", "", "s", "s²"],
    )
    table2["calc"] = {"label": "计算 g（拟合斜率法）", "table": "table2"}
    # 同 table1：按钮与结果置于表格上方，不在表格下方重复生成按钮。
    table2["calc_placement"] = "top"
    return make_schema(
        (
            "本实验用单摆测量当地重力加速度。请测量摆线长与摆球直径，用累积放大法记录多次全振动的"
            "总时间，计算各摆长下的周期；由 " r"$L$" r"–$T^2$" " 线性拟合斜率求得 "
            r"$g = 4\pi^2 k$" "。注意摆角控制在 " r"$5^\circ$" " 以内。"
        ),
        [table1, table2],
        analysis_hints="检查摆长和周期的测量不确定度，以及 l-T² 拟合的线性度。",
        preview_enabled=True,
        table_theory=get_table_theory("exp1"),
    )


def _linear_fit(xs, ys):
    """最小二乘线性回归，返回 (k, b, r2)。数据点 < 2 或 x 全等返回 (None, None, None)。"""
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pts)
    if n < 2:
        return None, None, None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return None, None, None
    k = num / den
    b = y_mean - k * x_mean
    # 判定系数 R²
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((ys[i] - (k * xs[i] + b)) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    return k, b, r2


def _compute_gravity(tables):
    """由 table1 重复测量数据计算重力加速度 g 及不确定度（平均值法）。

    公式：g = 4π²·L̄ / T̄²，其中实际摆长 L̄ = x̄ + d̄/20（cm→m），周期 T = t/n。
    不确定度按相对不确定度合成：u_r(g) = √[u_r(L)² + (2·u_r(T))²]。
    返回 (summary 行列表, warnings 列表)。数据不足时给出对应提示。
    """
    warnings = []
    rows = tables.get("table1", []) or []
    lengths, periods, counts = [], [], []
    for row in rows:
        x = as_number(row.get("c1"))      # 摆线长 x(cm)
        d = as_number(row.get("c2"))      # 摆球直径 d(mm)
        t = as_number(row.get("c4"))      # 累积时间 t(s)
        n = as_number(row.get("c5"))      # 周期数 n
        if x is None or d is None or t is None or not n:
            continue
        lengths.append(x + d / 20.0)      # 实际摆长 l(cm)
        periods.append(t / n)             # 周期 T(s) = 累积时间/周期数
        counts.append(n)

    if len(lengths) < 2:
        return [], warnings

    l_arr = np.array(lengths, dtype=float)
    T_arr = np.array(periods, dtype=float)
    n = len(l_arr)

    l_mean = float(np.mean(l_arr))        # cm
    T_mean = float(np.mean(T_arr))        # s
    if T_mean == 0 or l_mean == 0:
        warnings.append("摆长或周期均值为 0，无法计算 g。")
        return [], warnings

    # A 类不确定度（样本标准差/√n）
    u_l_A = float(np.std(l_arr, ddof=1) / math.sqrt(n))
    u_T_A = float(np.std(T_arr, ddof=1) / math.sqrt(n))
    # B 类不确定度：钢卷尺估计误差 0.05 cm；秒表估计误差 0.2s 分摊到平均周期数
    u_l_B, u_T_B = 0.05, 0.2 / float(np.mean(counts))
    u_l = math.hypot(u_l_A, u_l_B)        # cm
    u_T = math.hypot(u_T_A, u_T_B)        # s

    g_val = 4 * math.pi ** 2 * (l_mean / 100.0) / T_mean ** 2  # m/s²
    ur_l, ur_T = u_l / l_mean, u_T / T_mean
    ur_g = math.hypot(ur_l, 2 * ur_T)
    u_g = g_val * ur_g                                   # m/s²

    if ur_g > 0.05:
        warnings.append(f"g 的相对不确定度 {ur_g * 100:.1f}% 偏大，请检查数据一致性。")

    return [
        f"平均值法：摆长均值 L̄ = {l_mean:.4f} cm，周期均值 T̄ = {T_mean:.4f} s",
        f"重力加速度 g = {g_val:.4f} m/s²",
        f"g 的标准不确定度 u(g) = {u_g:.4f} m/s²，相对不确定度 u_r(g) = {ur_g * 100:.2f}%",
    ], warnings


def _calc_table1(tables):
    """表1：平均值法 g 与不确定度，整理为 calc_results 的行列表。"""
    summary, warnings = _compute_gravity(tables)
    if not summary:
        if any("均值为 0" in w for w in warnings):
            return ["摆长或周期均值为 0，无法计算 g。"]
        return ["请至少填写 2 行有效数据（摆线长 x、摆球直径 d、累积时间 t、周期数 n）。"]
    return summary + [f"⚠ {w}" for w in warnings]


def _calc_table2(tables, params):
    """表2：l–T² 线性拟合求 g（拟合斜率法）。

    由 T² = 4π²L/g 得 L = (g/4π²)T²，斜率 k = ΔL/ΔT²（cm/s²），
    故 g = 4π²·k/100 (m/s²)。不确定度取斜率标准误差
    se(k) = sqrt(Σ(lᵢ-l̂ᵢ)² / ((n-2)·Σ(T²ᵢ-T̄²)²))，u(g) = 4π²·se(k)/100。
    """
    lines = []
    rows = tables.get("table2", []) or []
    lengths, periods_sq = [], []
    for row in rows:
        l_v = as_number(row.get("c1"))    # 摆长 l(cm)
        t2_v = as_number(row.get("c5"))   # 周期平方 T²(s²)，由 preview 从 t/n 计算
        if l_v is None or t2_v is None:
            continue
        lengths.append(l_v)
        periods_sq.append(t2_v)
    if len(lengths) < 2:
        lines.append("请至少填写 2 行摆长 l、累积时间 t 与周期数 n（T² 由后端自动计算）。")
        return lines
    k, b, r2 = _linear_fit(periods_sq, lengths)   # l = k·T² + b，k 单位 cm/s²
    if k is None:
        lines.append("T² 列不能全部相同，请检查数据。")
        return lines
    lines.append(f"l-T² 线性拟合：斜率 k = {k:.4f} cm/s²，截距 b = {b:.4f} cm")
    if r2 is not None:
        lines.append(f"判定系数 R² = {r2:.6f}")
    g_fit = 4 * math.pi ** 2 * k / 100.0    # m/s²
    n = len(lengths)
    if n > 2:
        l_arr = np.array(lengths, dtype=float)
        t2_arr = np.array(periods_sq, dtype=float)
        resid = l_arr - (k * t2_arr + b)
        ss_res = float(np.sum(resid ** 2))
        ss_x = float(np.sum((t2_arr - t2_arr.mean()) ** 2))
        if ss_x > 0:
            se_k = math.sqrt(ss_res / ((n - 2) * ss_x))
            u_g = 4 * math.pi ** 2 * se_k / 100.0
            lines.append(f"重力加速度 g = 4π²k = {g_fit:.4f} m/s²")
            lines.append(f"g 的标准不确定度 u(g) = {u_g:.4f} m/s²，"
                         f"相对不确定度 u_r(g) = {se_k / k * 100:.2f}%")
        else:
            lines.append(f"重力加速度 g = 4π²k = {g_fit:.4f} m/s²")
    else:
        lines.append(f"重力加速度 g = 4π²k = {g_fit:.4f} m/s²（仅 2 个数据点，无法估计不确定度）")
    return lines


def calc_table(table_id, tables):
    """单表计算接口：按某张表的数据即时计算并返回结果摘要。

    table1 为平均值法，table2 为拟合斜率法。
    返回 {"summary": [...], "warnings": [...]}；不支持的表返回 None。
    """
    if table_id not in ("table1", "table2"):
        return None
    enriched = preview({"tables": {table_id: tables.get(table_id, [])}})["tables"]
    if table_id == "table1":
        summary, warnings = _compute_gravity(enriched)
        if not summary:
            summary = ["数据不足（至少 2 行有效数据），无法计算 g。"]
        return {"summary": summary, "warnings": warnings}
    return {"summary": _calc_table2(enriched, {}), "warnings": []}


def preview(payload):
    """补全序号、实际摆长、周期及周期平方，并生成各表「提交计算」结果（calc_results）。"""
    tables = copied_tables(payload)
    for index, row in enumerate(tables.get("table1", [])):
        x, diameter, elapsed, periods = (as_number(row.get(key)) for key in ("c1", "c2", "c4", "c5"))
        row["c0"] = index + 1
        row["c3"] = formatted(x + diameter / 20 if x is not None and diameter is not None else None, 4)
        row["c6"] = formatted(
            elapsed / periods if elapsed is not None and periods else None, 5)
    for index, row in enumerate(tables.get("table2", [])):
        elapsed, periods = as_number(row.get("c2")), as_number(row.get("c3"))
        period = elapsed / periods if elapsed is not None and periods else None
        row["c0"] = index + 1
        row["c4"] = formatted(period, 5)
        row["c5"] = formatted(period * period if period is not None else None, 6)
    calc_results = {
        "table1": {"lines": _calc_table1(tables)},
        "table2": {"lines": _calc_table2(tables, {})},
    }
    return {"tables": tables, "calc_results": calc_results}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    calc_results = preview_result.get("calc_results", {})
    g_summary, g_warnings = _compute_gravity(enriched["tables"])
    summary = ["单摆重复测量数据及多摆长拟合数据已处理，序号和派生量已由后端计算。"]
    summary.extend(g_summary)
    table2_lines = (calc_results.get("table2", {}) or {}).get("lines", []) or []
    if table2_lines:
        summary.append("── 表2 拟合斜率法 ──")
        summary.extend(f"  {ln}" for ln in table2_lines)
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        warnings=g_warnings,
    )
