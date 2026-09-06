"""霍尔效应实验模块
===============
二级大物电磁学实验 —— 霍尔效应

实验内容：
本实验包含三组独立测量：
1. 霍尔电压 VH 与控制电流 IS 的关系
2. 霍尔电压 VH 与励磁电流 IM 的关系
3. 霍尔系数 RH 随温度 T 的变化（变温霍尔效应）

每组数据独立进行异常检验和图表生成，
最终合并三组数据生成完整实验报告。

物理背景：
霍尔效应：在通有电流的导体或半导体上施加磁场，
则会产生垂直于电流和磁场方向的霍尔电压。
U_H = (R_H * I * B) / d
其中 R_H 为霍尔系数，I 为工作电流，B 为磁感应强度，d 为样品厚度。
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_chart_from_table, make_schema, make_table,
    structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data_numeric

# 基本物理常量
_E_CHARGE = 1.602e-19      # 电子电量 (C)
# 霍尔元件默认参数（与示例数据自洽：d = 0.3 mm、B ≈ 0.3 T）
_DEFAULT_D_MM = 0.3
_DEFAULT_B_T = 0.30
_DEFAULT_IS_MA = 4.50      # 表2 控制电流
_DEFAULT_COIL = 0.667      # 励磁线圈常数 k (T/A)，B = k·IM，使 IM=0.45A → B≈0.30T

def name():
    return "霍尔效应"


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
        # 识别数据列：IS(工作电流mA), V1, V2, V3, V4(四组霍尔电压mV) 或 IM, VH
        is_col = [c for c in cols if 'IS' in c or 'I_S' in c or '工作电流' in c][0] if any('IS' in c or 'I_S' in c or '工作电流' in c for c in cols) else cols[0]
        vh_cols = [c for c in cols if 'V' in c and ('1' in c or '2' in c or '3' in c or '4' in c or 'H' in c)]

        IS = pd.to_numeric(data[is_col], errors='coerce')

        if len(vh_cols) >= 4:
            V1 = pd.to_numeric(data[vh_cols[0]], errors='coerce')
            V2 = pd.to_numeric(data[vh_cols[1]], errors='coerce')
            V3 = pd.to_numeric(data[vh_cols[2]], errors='coerce')
            V4 = pd.to_numeric(data[vh_cols[3]], errors='coerce')
            VH = (abs(V1) + abs(V2) + abs(V3) + abs(V4)) / 4.0
        elif len(vh_cols) >= 1:
            VH = pd.to_numeric(data[vh_cols[0]], errors='coerce')
        else:
            VH = pd.to_numeric(data[cols[1]], errors='coerce')

        # 霍尔元件参数
        d = 0.3  # mm 厚度
        b = 4.0  # mm 宽度
        l = 2.0  # mm 长度

        # 线性拟合 VH-IS
        res_lsm = analyse_lsm(IS, VH, 'I_S', 'V_H', 'mA', 'mV')

        # KH = VH / (IS * B)，若B由IM产生则另行计算
        # 根据实验指导，IM=0.45A时B已知，或直接计算KH
        if len(IS) > 1:
            KH = res_lsm.m  # mV/mA 斜率即 KH*B (在固定B下)
        else:
            KH = VH.iloc[0] / IS.iloc[0]

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()
        docu.add_paragraph("霍尔元件参数：d={:.1f}mm, b={:.1f}mm, l={:.1f}mm".format(d, b, l))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(IS)+1, cols=3, style='Table Grid')
        for j, h in enumerate(['I_S (mA)', 'V_H (mV)', 'V_H/I_S (mV/mA)']):
            table.rows[0].cells[j].text = h
        for i in range(len(IS)):
            table.rows[i+1].cells[0].text = '{:.3f}'.format(IS.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(VH.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(VH.iloc[i]/IS.iloc[i] if IS.iloc[i] != 0 else 0)
        docu.add_paragraph()

        docu.add_paragraph("V_H-I_S 线性拟合")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("霍尔元件参数：d={:.1f}\\,\\mathrm{{mm}},\\ b={:.1f}\\,\\mathrm{{mm}},\\ l={:.1f}\\,\\mathrm{{mm}}".format(d, b, l))
        docu.add_paragraph()
        docu.add_paragraph("V_H-I_S 线性拟合：")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()
        docu.add_paragraph("霍尔灵敏度 K_H = \\frac{{V_H}}{{I_S B}}（需已知磁场B）")
        docu.add_paragraph("载流子浓度 n = \\frac{{1}}{{K_H e d}}")
        docu.add_paragraph("迁移率 \\mu = \\frac{{\\sigma}}{{n e}}")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    _all = load_sample_data_numeric("exp28", "exp28_example")

    table1 = make_table(
        "table1", "霍尔电压与控制电流关系数据表",
        ["IS(mA)", "V1(mV)", "V2(mV)", "V3(mV)", "V4(mV)", "VH(mV)"],
        sample=_all,
        readonly=(5,),
        initial_rows=3,
        chart={"x_column": "c0", "y_column": "c5", "x_label": "控制电流 IS (mA)",
               "y_label": "霍尔电压 VH (mV)", "title": "VH-IS 关系", "fit": "linear"},
    )
    # 表1 专属参数：磁感应强度 B 与样品厚度 d，用于由 VH-IS 斜率求霍尔系数与载流子浓度。
    table1["parameters"] = [
        {"id": "B1", "label": "磁感应强度 B (T)", "default": _DEFAULT_B_T},
        {"id": "d1", "label": "样品厚度 d (mm)", "default": _DEFAULT_D_MM},
    ]
    table1["calc"] = {"label": "提交计算"}
    # 计算按钮与结果置于表格上方（复用模板上方按钮，走 /preview + 本表参数）。
    table1["calc_placement"] = "top"

    table2 = make_table(
        "table2", "霍尔电压与励磁电流关系数据表",
        ["IM(A)", "VH(mV)"],
        # 示例数据：控制电流固定 IS = 4.50 mA，IM 取 0.100~0.450 A（间隔 0.050 A）。
        # VH 与表 1 自洽：IM = 0.45 A 时 VH ≈ 13.65 mV，对应表 1 中 IS = 4.5 mA 的霍尔电压。
        sample=[
            [0.100, 3.02], [0.150, 4.56], [0.200, 6.06], [0.250, 7.59],
            [0.300, 9.11], [0.350, 10.61], [0.400, 12.14], [0.450, 13.65],
        ],
        initial_rows=3,
        chart={"x_column": "c0", "y_column": "c1", "x_label": "励磁电流 IM (A)",
               "y_label": "霍尔电压 VH (mV)", "title": "VH-IM 关系", "fit": "linear"},
    )
    # 表2 专属参数：控制电流 IS 与励磁线圈常数 k (T/A)，用于由 VH-IM 斜率求霍尔灵敏度与磁感应强度。
    table2["parameters"] = [
        {"id": "IS2", "label": "控制电流 IS (mA)", "default": _DEFAULT_IS_MA},
        {"id": "coil", "label": "励磁线圈常数 k (T/A)", "default": _DEFAULT_COIL},
        {"id": "d2", "label": "样品厚度 d (mm)", "default": _DEFAULT_D_MM},
    ]
    table2["calc"] = {"label": "提交计算"}
    table2["calc_placement"] = "top"

    table3 = make_table(
        "table3", "霍尔效应参数随温度变化关系数据表",
        ["T(℃)", "RH(m³/C)"],
        # 示例数据：变温霍尔效应 -10℃~100℃。室温附近 RH ≈ 3.0×10⁻³ m³/C
        # （与表 1 数据按 RH = VH·d/(IS·B)，d = 0.3 mm、B ≈ 0.3 T 自洽）；
        # 升温后载流子浓度增大，RH 单调下降。
        sample=[
            [-10, 0.00305], [0, 0.00304], [10, 0.00303], [20, 0.00301],
            [30, 0.00298], [40, 0.00294], [50, 0.00288], [60, 0.00280],
            [70, 0.00269], [80, 0.00254], [90, 0.00234], [100, 0.00208],
        ],
        initial_rows=3,
        chart={"x_column": "c0", "y_column": "c1", "x_label": "温度 T (℃)",
               "y_label": "霍尔系数 RH (m³/C)", "title": "RH-T 关系", "fit": "auto"},
    )
    table3["calc"] = {"label": "提交计算"}
    table3["calc_placement"] = "top"

    return make_schema(
        (
            "本实验用霍尔效应测量磁场与霍尔元件的特性：① 用对称测量法测量 "
            r"$V_H$" r"–$I_S$" " 关系；② 测量 " r"$V_H$" r"–$I_M$" " 关系并计算磁感应强度；"
            "③ 测量 " r"$R_H$" r"–$T$" " 关系。由霍尔电压正负判断载流子类型，并计算载流子浓度与迁移率。"
        ),
        [table1, table2, table3],
        analysis_hints="检查两组霍尔电压关系的线性以及霍尔系数随温度变化的趋势。",
        preview_enabled=True,
        table_theory=get_table_theory("exp28"),
        parameters_sample={
            "B1": _DEFAULT_B_T, "d1": _DEFAULT_D_MM,
            "IS2": _DEFAULT_IS_MA, "coil": _DEFAULT_COIL, "d2": _DEFAULT_D_MM,
        },
    )


def _calc_table1(tables, params):
    """表1：VH-IS 线性拟合 → 斜率(mV/mA)=KH·B；求霍尔系数 RH、载流子浓度 n。
    公式：V_H = (R_H/d)·I_S·B，故 斜率 = R_H·B/d，
    R_H = 斜率·d/B，霍尔灵敏度 K_H = R_H/d = 斜率/B，
    载流子浓度 n = 1/(R_H·e)。"""
    lines = []
    rows = tables.get("table1", []) or []
    IS, VH = [], []
    for row in rows:
        is_v = as_number(row.get("c0"))
        vh_v = as_number(row.get("c5"))
        if is_v is not None and vh_v is not None:
            IS.append(is_v)
            VH.append(vh_v)
    if len(IS) < 2:
        lines.append("请至少填写 2 行 IS 与 V1~V4 数据（VH 自动计算）。")
        return lines
    k, b, r2 = _linear_fit(IS, VH)
    if k is None:
        lines.append("IS 列不能全部相同，请检查数据。")
        return lines
    lines.append(f"VH-IS 线性拟合：斜率 k = {k:.4f} mV/mA，截距 b = {b:.4f} mV")
    if r2 is not None:
        lines.append(f"判定系数 R² = {r2:.6f}")
    B = as_number(params.get("B1")) or _DEFAULT_B_T
    d_mm = as_number(params.get("d1")) or _DEFAULT_D_MM
    if B <= 0 or d_mm <= 0:
        lines.append("提示：磁感应强度 B 与样品厚度 d 需为正数。")
        return lines
    d_m = d_mm * 1e-3
    KH = k / B                    # mV/(mA·T) = (V/A/T)·1e3/1e3 = V/(A·T)
    RH = k * d_mm / B             # mV·mm/(mA·T) = (1e-3 V)(1e-3 m)/(1e-3 A·T) = 1e-3 m³/C
    RH_si = RH * 1e-3             # 换算到 m³/C
    n = 1.0 / (RH_si * _E_CHARGE) if RH_si > 0 else None
    lines.append(f"磁感应强度 B = {B:.4f} T，样品厚度 d = {d_mm:.2f} mm")
    lines.append(f"霍尔灵敏度 K_H = 斜率/B = {KH:.4f} mV/(mA·T)")
    lines.append(f"霍尔系数 R_H = 斜率·d/B = {RH_si:.4e} m³/C")
    if n is not None:
        lines.append(f"载流子浓度 n = 1/(R_H·e) = {n:.4e} m⁻³")
        # VH 正负判断载流子类型（取首个有效 VH 符号；对称测量已取绝对值，故仅当原始 V1 正负一致时可判）
        lines.append("载流子类型：需结合原始 V1~V4 符号判断（N 型为负、P 型为正）。")
    return lines


def _calc_table2(tables, params):
    """表2：VH-IM 线性拟合 → 斜率(mV/A)=K_H·I_S·k；求霍尔灵敏度 K_H、磁感应强度 B=k·IM。
    由 V_H = K_H·I_S·B = K_H·I_S·(k·I_M)，斜率 = K_H·I_S·k，
    K_H = 斜率/(I_S·k)，B = k·I_M（取最大 IM 处）。"""
    lines = []
    rows = tables.get("table2", []) or []
    IM, VH = [], []
    for row in rows:
        im_v = as_number(row.get("c0"))
        vh_v = as_number(row.get("c1"))
        if im_v is not None and vh_v is not None:
            IM.append(im_v)
            VH.append(vh_v)
    if len(IM) < 2:
        lines.append("请至少填写 2 行 IM 与 VH 数据。")
        return lines
    k_fit, b_fit, r2 = _linear_fit(IM, VH)
    if k_fit is None:
        lines.append("IM 列不能全部相同，请检查数据。")
        return lines
    lines.append(f"VH-IM 线性拟合：斜率 k = {k_fit:.4f} mV/A，截距 b = {b_fit:.4f} mV")
    if r2 is not None:
        lines.append(f"判定系数 R² = {r2:.6f}")
    IS = as_number(params.get("IS2")) or _DEFAULT_IS_MA
    coil = as_number(params.get("coil")) or _DEFAULT_COIL
    d_mm = as_number(params.get("d2")) or _DEFAULT_D_MM
    if IS <= 0 or coil <= 0 or d_mm <= 0:
        lines.append("提示：控制电流 IS、线圈常数 k 与样品厚度 d 需为正数。")
        return lines
    KH = k_fit / (IS * coil)      # mV/(mA·A)·(1/A→T) 综合单位 mV/(mA·T)
    B_max = coil * max(IM)
    lines.append(f"控制电流 IS = {IS:.2f} mA，线圈常数 k = {coil:.4f} T/A，厚度 d = {d_mm:.2f} mm")
    lines.append(f"霍尔灵敏度 K_H = 斜率/(IS·k) = {KH:.4f} mV/(mA·T)")
    lines.append(f"磁感应强度 B = k·IM，最大值 B_max = {B_max:.4f} T（IM={max(IM):.3f} A）")
    RH = KH * d_mm * 1e-3         # mV/(mA·T)·mm → m³/C 量级换算
    lines.append(f"对应霍尔系数 R_H = K_H·d = {RH:.4e} m³/C")
    return lines


def _calc_table3(tables, params):
    """表3：RH-T 关系。计算 RH 区间、随温度的线性变化率、由 RH 反推载流子浓度 n(T)。"""
    lines = []
    rows = tables.get("table3", []) or []
    T, RH = [], []
    for row in rows:
        t_v = as_number(row.get("c0"))
        rh_v = as_number(row.get("c1"))
        if t_v is not None and rh_v is not None:
            T.append(t_v)
            RH.append(rh_v)
    if len(T) < 2:
        lines.append("请至少填写 2 行 T 与 RH 数据。")
        return lines
    lines.append(f"温度范围 T = {min(T):.1f} ~ {max(T):.1f} ℃，共 {len(T)} 个数据点")
    lines.append(f"霍尔系数 R_H 范围 = {min(RH):.4e} ~ {max(RH):.4e} m³/C")
    k, b, r2 = _linear_fit(T, RH)
    if k is not None:
        lines.append(f"R_H-T 线性拟合：斜率 dR_H/dT = {k:.4e} m³/(C·℃)，R² = {r2:.6f}")
        if k < 0:
            lines.append("R_H 随温度升高而下降 → 载流子浓度随温度增大（本征激发增强）。")
        elif k > 0:
            lines.append("R_H 随温度升高而增大 → 载流子浓度随温度减小。")
        else:
            lines.append("R_H 基本不随温度变化。")
    # 由两端点 RH 反推载流子浓度
    rh_lo, rh_hi = min(RH), max(RH)
    n_lo = 1.0 / (rh_hi * _E_CHARGE)
    n_hi = 1.0 / (rh_lo * _E_CHARGE)
    lines.append(f"由 R_H 反推载流子浓度 n = 1/(R_H·e)：")
    lines.append(f"  n(T_min 端) ≈ {n_lo:.4e} m⁻³，n(T_max 端) ≈ {n_hi:.4e} m⁻³")
    return lines


def preview(payload):
    """从四组霍尔电压 V1-V4 计算 VH = (|V1|+|V2|+|V3|+|V4|)/4，
    并为每个表格生成独立的「提交计算」结果（calc_results）。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})

    # 表1：由 V1~V4 对称测量计算 VH
    for row in tables.get("table1", []):
        vs = [abs(v) for v in (as_number(row.get(f"c{i}")) for i in range(1, 5)) if v is not None]
        if vs:
            row["c5"] = formatted(sum(vs) / len(vs), 4)
        else:
            row["c5"] = ""

    # 三表独立的「提交计算」结果
    calc_results = {
        "table1": {"lines": _calc_table1(tables, params)},
        "table2": {"lines": _calc_table2(tables, params)},
        "table3": {"lines": _calc_table3(tables, params)},
    }

    return {"tables": tables, "calc_results": calc_results}


def calc_table(table_id, tables):
    """单表即时计算接口（供表格上方「提交计算」按钮的 /calc-table 通道调用）。

    请求体仅含 {table_id, tables: {tid: rows}}，不带参数；
    本表所需参数缺失时使用与示例数据自洽的默认值（见模块顶部常量）。
    返回 {"summary": [...], "warnings": [...]}；未知表返回 None。
    """
    if table_id not in ("table1", "table2", "table3"):
        return None
    # 单表数据可能不含 table1 的 VH 列，先用 preview 补全 VH 后再交给对应计算函数。
    enriched = preview({"tables": {table_id: tables.get(table_id, [])}})["tables"]
    # preview 只补全传入的表；构造一个仅含目标表的数据视图给计算函数。
    view = {table_id: enriched.get(table_id, tables.get(table_id, []))}
    params = {}  # /calc-table 不带参数，统一用默认值
    if table_id == "table1":
        lines = _calc_table1(view, params)
    elif table_id == "table2":
        lines = _calc_table2(view, params)
    else:
        lines = _calc_table3(view, params)
    return {"summary": lines, "warnings": []}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    calc_results = preview_result.get("calc_results", {})

    _schema = schema()
    summary_lines = ["霍尔效应 — 三组测量数据处理结果："]
    warnings = []
    charts = []

    # 每个表格：生成拟合图像并把该表 calc 结果汇入报告摘要
    for table_schema in _schema.get("tables", []):
        tid = table_schema["id"]
        rows = enriched["tables"].get(tid, []) or []
        nonempty = [r for r in rows if any(as_number(r.get(col["id"])) is not None
                                           for col in table_schema.get("columns", []))]
        info = calc_results.get(tid, {}) or {}
        lines = info.get("lines", []) or []

        summary_lines.append(f"── {table_schema.get('title', tid)} ──")
        if lines:
            summary_lines.extend(f"  {ln}" for ln in lines)
        else:
            summary_lines.append("  尚未填写足够数据。")

        chart_config = table_schema.get("chart")
        if chart_config and len(nonempty) >= 2:
            try:
                charts.append(make_chart_from_table(
                    table_schema, nonempty, chart_config, workpath,
                    chart_filename=f"chart_{tid}.png",
                ))
            except Exception:
                traceback.print_exc()
                warnings.append(f"{table_schema.get('title', tid)} 图表生成失败，请检查数据。")
        elif not nonempty:
            warnings.append(f"{table_schema.get('title', tid)} 未填写数据。")

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        warnings=warnings,
        charts=charts,
    )
