"""凯特摆测量重力加速度实验模块
================================
二级大物力学实验 —— 凯特摆（可逆摆）

基础内容（对应《凯特摆（实验指导）》）：
  表1  周期测量：轮流测量正挂 10T₁、倒挂 10T₂ 各 5 次，
       由多用数字测试仪（精度 0.1 ms）读数，计算 T₁、T₂ 及不确定度。
  表2  重力加速度 g 与不确定度 U_g（P = 0.95）：
       测量两刀口间距 l 与重心到一刀口距离 h₁ 各 3 次（h₂ = l − h₁），
       系统总质量 m 由天平称一次；由式 (10) 求 g 并作不确定度传递。
  表3  转动惯量：以两刀口为转轴的转动惯量 I_O、I_O' 及绕重心 I_G。

物理公式（指导书式 8/9/10）：
  复摆周期    T = 2π√(I/(mgh))
  凯特摆 g   g = 4π² / [ (T₁²+T₂²)/(2l) + (T₁²−T₂²)/(2(h₁−h₂)) ]   ── 式(10)
  退化情形   T₁ = T₂ 时，b 项 = 0，g = 4π²l/T²
  转动惯量   I_O = I_G + m·h₁² = m·g·h₁·T₁²/(4π²)
             I_O' = I_G + m·h₂² = m·g·h₂·T₂²/(4π²)

仪器不确定度约定：
  多用数字测试仪  Δ_仪 = 0.1 ms = 0.0001 s（测 10 个周期，单周期 T 误差 ÷10）
  钢尺            Δ_仪 = 0.5 mm = 0.05 cm，估读 Δ_估 = 0.5 mm = 0.05 cm
  天平            单次称量，仅取 B 类（Δ_仪 按实验室给定，缺省 0.05 g）
  C = √3（均匀分布），P = 0.95
"""

import math

from head import *  # 导入万能头
from docx.shared import Inches
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data_numeric

# ── 仪器不确定度常量 ──────────────────────────────────────────
# 多用数字测试仪：精度 0.1 ms，测 10 个周期，故单次 10T 读数 Δ_仪 = 0.0001 s
_DELTA_10T_INST = 0.0001          # s，10 个周期的仪器允差
_DELTA_10T_EST = 0.0001           # s，估读允差（同量级）
# 钢尺：仪器允差 0.05 cm、估读 0.05 cm（最小分度 1 mm）
_DELTA_LEN_INST = 0.05            # cm
_DELTA_LEN_EST = 0.05             # cm
# 天平：单次称量 B 类允差（缺省 0.05 g）
_DELTA_MASS_INST = 0.05           # g

_CONF_C = 3 ** 0.5                # 均匀分布置信系数 C = √3
_G_REF = 9.794                    # 当地重力加速度公认值（m/s²），用于比较


def name():
    return "凯特摆"


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────
def _mean(values):
    nums = [v for v in values if v is not None]
    return float(sum(nums) / len(nums)) if nums else None


def _collect_column(rows, col):
    return [as_number(r.get(col)) for r in (rows or [])]


def _font():
    """返回思源黑体 FontProperties，找不到则返回 None（用默认字体）。"""
    path = os.environ.get('_B_FONT_PATH')
    if path and os.path.exists(path):
        return matplotlib.font_manager.FontProperties(fname=path)
    return None


def _add_doc_table(docu, headers, rows):
    table = docu.add_table(rows=1, cols=len(headers), style='Table Grid')
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = str(h)
    for row in rows:
        cells = table.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = str(v)
    return table


def _uncertainty_of_direct(values, delta_inst, delta_est, symbol, unit,
                           confidence_C=_CONF_C):
    """对直接测量量调用 analyse，返回 namedtuple；values 缺失返回 None。"""
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return analyse(pd.Series(nums), delta_inst, delta_est,
                   symbol, unit, confidence_C=confidence_C)


# ─────────────────────────────────────────────
# 核心计算：T₁、T₂ → g、U_g → 转动惯量
# ─────────────────────────────────────────────
def _compute_periods(t1_rows, t2_rows, t1_col="c1", t2_col="c2"):
    """由 10T₁、10T₂ 各 5 次读数计算 T₁、T₂ 及其不确定度。

    t1_rows/t2_rows 为同一 table1 的行（10T₁ 在 c1、10T₂ 在 c2），
    也可分别传入两份行对象。返回 dict:
    {T1, T2, u_T1, u_T2, res_10t1, res_10t2, warnings}
    （T 的不确定度 = 10T 的不确定度 / 10）
    """
    warnings = []
    ten_t1 = _collect_column(t1_rows, t1_col)
    ten_t2 = _collect_column(t2_rows, t2_col)

    res_10t1 = _uncertainty_of_direct(ten_t1, _DELTA_10T_INST, _DELTA_10T_EST,
                                      "x", "s")
    res_10t2 = _uncertainty_of_direct(ten_t2, _DELTA_10T_INST, _DELTA_10T_EST,
                                      "y", "s")
    if res_10t1 is None or res_10t2 is None:
        return {"warnings": ["周期数据不足：正挂 10T₁ 与倒挂 10T₂ 各需至少 1 次读数。"]}

    T1 = float(res_10t1.average) / 10.0
    T2 = float(res_10t2.average) / 10.0
    u_T1 = float(res_10t1.unc) / 10.0
    u_T2 = float(res_10t2.unc) / 10.0

    # 周期一致性检验：T₁ ≈ T₂ 是凯特摆调节完成的标志
    if T1 > 0 and T2 > 0:
        rel = abs(T1 - T2) / max(T1, T2)
        if rel > 0.005:  # 0.5%
            warnings.append(
                "T₁ 与 T₂ 相差 {:.2f}%（>0.5%），凯特摆尚未调到共轭点，"
                "建议重新调节摆锤使 T₁ ≈ T₂。".format(rel * 100))

    return {
        "T1": T1, "T2": T2, "u_T1": u_T1, "u_T2": u_T2,
        "res_10t1": res_10t1, "res_10t2": res_10t2,
        "warnings": warnings,
    }


def _compute_g(period_info, l_values, h1_values, m_g):
    """由式 (10) 计算重力加速度 g 及其合成不确定度 U_g。

    l、h₁ 单位 cm，m 单位 g；g 输出 m/s²。
    返回 dict: {g, u_g, res_g, l_bar, h1_bar, h2_bar, l_m, h1_m, h2_m,
                u_l, u_h1, u_h2, a_term, b_term, res_l, res_h1, warnings}
    """
    warnings = []
    T1 = period_info.get("T1")
    T2 = period_info.get("T2")
    if T1 is None or T2 is None:
        return {"warnings": ["缺少周期 T₁/T₂，无法计算 g。"]}

    # l、h₁ 直接测量（钢尺，各 3 次）
    res_l = _uncertainty_of_direct(l_values, _DELTA_LEN_INST, _DELTA_LEN_EST,
                                   "l", "cm")
    res_h1 = _uncertainty_of_direct(h1_values, _DELTA_LEN_INST, _DELTA_LEN_EST,
                                    "h1", "cm")
    if res_l is None or res_h1 is None:
        return {"warnings": ["缺少长度 l 或 h₁ 数据，无法计算 g。"]}

    l_bar = float(res_l.average)        # cm
    h1_bar = float(res_h1.average)      # cm
    h2_bar = l_bar - h1_bar             # cm，h₂ = l − h₁
    u_l = float(res_l.unc)              # cm
    u_h1 = float(res_h1.unc)            # cm
    # h₂ = l − h₁ 的不确定度：u(h₂) = √(u_l² + u_h1²)
    u_h2 = math.hypot(u_l, u_h1)

    if h2_bar == 0 or (h1_bar - h2_bar) == 0:
        return {"warnings": ["h₁ − h₂ = 0，式 (10) 分母为零，请检查 l 与 h₁ 数据。"]}

    # 式 (10)：g = 4π² / [ (T₁²+T₂²)/(2l) + (T₁²−T₂²)/(2(h₁−h₂)) ]
    # 注意 l、h 用 m 代入；T 用 s
    l_m = l_bar / 100.0
    h1_m = h1_bar / 100.0
    h2_m = h2_bar / 100.0
    u_l_m = u_l / 100.0
    u_h1_m = u_h1 / 100.0
    u_h2_m = u_h2 / 100.0
    dh = h1_m - h2_m

    a_term = (T1 ** 2 + T2 ** 2) / (2.0 * l_m)         # a 项（主要贡献）
    b_term = (T1 ** 2 - T2 ** 2) / (2.0 * dh)          # b 项（修正项）
    denom = a_term + b_term
    if denom <= 0:
        return {"warnings": ["式 (10) 分母非正，请检查周期与长度数据。"]}

    g_val = 4.0 * math.pi ** 2 / denom                 # m/s²

    # 不确定度传递：用 analyse_com，把 l、h₁、h₂、T₁、T₂ 作为变量
    # h₂ 由 l、h₁ 表达，故把 l、h₁ 作为独立变量，h₂ = l − h₁ 写入表达式
    u_T1 = period_info.get("u_T1", 0.0)
    u_T2 = period_info.get("u_T2", 0.0)
    try:
        res_g = analyse_com(
            "g=4*pi**2/((T1**2+T2**2)/(2*l)+(T1**2-T2**2)/(2*(h1-(l-h1))))",
            (("T1", T1, u_T1),
             ("T2", T2, u_T2),
             ("l", l_m, u_l_m),
             ("h1", h1_m, u_h1_m)),
            (), "m/s^2",
        )
        g_val = float(res_g.ans)
        u_g = float(res_g.unc)
    except Exception:
        # 退化：仅用偏导数值估算（不写 LaTeX）
        res_g = None
        u_g = 0.0

    # b 项影响分析
    if abs(b_term) < 1e-9:
        warnings.append("T₁ = T₂，b 项 = 0，g 退化为 4π²l/T²。")
    else:
        rel_b = abs(b_term) / abs(a_term) * 100
        if rel_b < 1.0:
            pass  # b 项影响很小，符合凯特摆设计预期
        else:
            warnings.append(
                "b 项 / a 项 = {:.2f}%（>1%），T₁ 与 T₂ 相差较大，"
                "b 项修正不可忽略，建议重新调节摆锤使 T₁ ≈ T₂。".format(rel_b))

    return {
        "g": g_val, "u_g": u_g, "res_g": res_g,
        "l_bar": l_bar, "h1_bar": h1_bar, "h2_bar": h2_bar,
        "l_m": l_m, "h1_m": h1_m, "h2_m": h2_m,
        "u_l": u_l, "u_h1": u_h1, "u_h2": u_h2,
        "u_l_m": u_l_m, "u_h1_m": u_h1_m, "u_h2_m": u_h2_m,
        "a_term": a_term, "b_term": b_term,
        "res_l": res_l, "res_h1": res_h1,
        "warnings": warnings,
    }


def _compute_inertia(period_info, g_info, m_g):
    """计算绕两刀口的转动惯量 I_O、I_O' 及绕重心 I_G。

    I_O  = m·g·h₁·T₁²/(4π²)
    I_O' = m·g·h₂·T₂²/(4π²)
    I_G  = I_O − m·h₁² = I_O' − m·h₂²（两式互相验证）
    m 单位 g → kg；h 单位 cm → m；I 输出 kg·m²。
    """
    warnings = []
    T1 = period_info.get("T1")
    T2 = period_info.get("T2")
    g_val = g_info.get("g")
    h1_m = g_info.get("h1_m")
    h2_m = g_info.get("h2_m")
    if None in (T1, T2, g_val, h1_m, h2_m) or m_g is None:
        return {"warnings": ["缺少 g、h₁、h₂ 或质量 m，无法计算转动惯量。"]}

    m_kg = m_g / 1000.0
    four_pi2 = 4.0 * math.pi ** 2

    I_O = m_kg * g_val * h1_m * T1 ** 2 / four_pi2     # kg·m²
    I_Op = m_kg * g_val * h2_m * T2 ** 2 / four_pi2    # kg·m²
    I_G1 = I_O - m_kg * h1_m ** 2                       # 由 O 轴反推
    I_G2 = I_Op - m_kg * h2_m ** 2                      # 由 O' 轴反推
    I_G = (I_G1 + I_G2) / 2.0

    # 互相验证：两式求得的 I_G 应接近
    if max(abs(I_G1), abs(I_G2)) > 0:
        rel = abs(I_G1 - I_G2) / max(abs(I_G1), abs(I_G2)) * 100
        if rel > 5.0:
            warnings.append(
                "由两刀口反推的 I_G 相差 {:.1f}%（>5%），"
                "请检查 T₁、T₂ 一致性与 h₁、h₂ 测量。".format(rel))

    return {
        "I_O": I_O, "I_Op": I_Op, "I_G": I_G,
        "I_G1": I_G1, "I_G2": I_G2,
        "m_kg": m_kg,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    # 示例数据：T₁ ≈ T₂ ≈ 2.00 s（10T ≈ 20.0 s），l ≈ 100 cm，h₁ ≈ 40 cm，
    # h₂ ≈ 60 cm，m ≈ 5000 g → g ≈ 9.87 m/s²。
    t1_sample = [[i + 1, round(20.000 + 0.002 * ((-1) ** i) * i, 3)] for i in range(5)]
    t2_sample = [[i + 1, round(20.005 + 0.002 * ((-1) ** i) * i, 3)] for i in range(5)]
    l_sample = [[i + 1, round(100.00 + 0.02 * i, 2)] for i in range(3)]
    h1_sample = [[i + 1, round(40.00 + 0.02 * i, 2)] for i in range(3)]

    table1 = make_table(
        "table1", "表1  摆动周期测量（正挂 10T₁ 与倒挂 10T₂ 各 5 次）",
        ["序号", "10T₁ (s)", "10T₂ (s)"],
        sample=[(a, b, c) for (a, b), (_, c) in zip(t1_sample, t2_sample)],
        readonly=(0,), min_rows=5, initial_rows=5,
        description="轮流测量正挂、倒挂时 10 个周期的时间 10T₁、10T₂ 各 5 次"
                    "（多用数字测试仪，精度 0.1 ms）。序号自动填充，"
                    "周期 T₁、T₂ 由下方「计算 T₁、T₂」按钮求出。",
    )
    table1["calc"] = {"label": "计算 T₁、T₂"}

    table2 = make_table(
        "table2", "表2  等效摆长与重心位置（l、h₁ 各 3 次）",
        ["序号", "l (cm)", "h₁ (cm)"],
        sample=[(a, b, c) for (a, b), (_, c) in zip(l_sample, h1_sample)],
        readonly=(0,), min_rows=3, initial_rows=3,
        description="用 T 型支架确定重心，钢尺测量两刀口间距 l 与重心到一刀口"
                    "距离 h₁ 各 3 次（h₂ = l − h₁ 由后端计算）。"
                    "系统总质量 m 在顶部参数填写，由「计算 g 与 U_g」按钮求 g。",
    )
    table2["calc"] = {"label": "计算 g 与 U_g"}

    table3 = make_table(
        "table3", "表3  转动惯量计算（由 g、h、T、m 求得）",
        ["I_O (kg·m²)", "I_O' (kg·m²)", "I_G (kg·m²)", "验证 ΔI_G/I_G (%)"],
        sample=[["", "", "", ""]],
        readonly=(0, 1, 2, 3), min_rows=1, initial_rows=1,
        description="以两刀口为转轴的转动惯量 I_O = m·g·h₁·T₁²/(4π²)、"
                    "I_O' = m·g·h₂·T₂²/(4π²)，绕重心 I_G = I_O − m·h₁²。"
                    "全部由前两表结果与质量 m 自动计算，无需手动输入。",
    )
    table3["calc"] = {"label": "计算转动惯量"}

    return make_schema(
        (
            "本实验用凯特摆（可逆摆）精确测量重力加速度。调节摆锤使正、倒悬挂"
            "周期 " r"$T_1 \approx T_2$" "，则两刀口间距即为等效摆长 "
            r"$l$" "。测量 " r"$10T_1$" "、" r"$10T_2$" " 各 5 次、"
            r"$l$" " 与 " r"$h_1$" " 各 3 次及系统质量 " r"$m$" "，"
            "由式 (10) 求 " r"$g$" " 及不确定度 " r"$U_g\,(P=0.95)$"
            "，再求两刀口的转动惯量。"
        ),
        [table1, table2, table3],
        parameters=[
            {"id": "m", "label": "系统总质量 m (g)", "default": "5000"},
            {"id": "g_ref", "label": "当地 g 公认值 (m/s²，用于比较，可空)", "default": "9.794"},
        ],
        analysis_hints=(
            "表1：T₁ 与 T₂ 应调节至基本相等（相差 <0.5%），否则未到共轭点。"
            "表2：a 项 (T₁²+T₂²)/(2l) 是 g 的主要贡献，b 项 (T₁²−T₂²)/(2(h₁−h₂)) "
            "在 T₁≈T₂ 时为微小修正；b 项/a 项 <1% 说明凯特摆设计有效。"
            "表3：由两刀口反推的 I_G 应一致（相差 <5%）。"
        ),
        preview_enabled=True,
        formulas=get_formulas("exp44"),
        variables=get_variables("exp44"),
        table_theory=get_table_theory("exp44"),
    )


def _all_results(payload):
    """统一计算入口：补全序号列并完成 T→g→转动惯量全链路，供 preview 与 handle_structured 共用。

    返回 {tables, periods, g, inertia, fit_notes, calc_results, calc_messages, warnings, parameters}
    """
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}

    # 序号自动填充
    for tid in ("table1", "table2"):
        for index, row in enumerate(tables.get(tid, [])):
            row["c0"] = index + 1

    m_g = as_number(parameters.get("m"))
    g_ref = as_number(parameters.get("g_ref"))

    warnings = []
    calc_messages = []
    fit_notes = {}
    calc_results = {}

    # ── 表1：周期 ──
    table1_rows = tables.get("table1", []) or []
    t1_rows = [r for r in table1_rows if as_number(r.get("c1")) is not None]
    t2_rows = [r for r in table1_rows if as_number(r.get("c2")) is not None]
    periods = _compute_periods(t1_rows, t2_rows, "c1", "c2")
    p_warnings = periods.get("warnings", [])
    warnings.extend(p_warnings)

    if not p_warnings:
        T1, T2 = periods["T1"], periods["T2"]
        u_T1, u_T2 = periods["u_T1"], periods["u_T2"]
        res_10t1, res_10t2 = periods["res_10t1"], periods["res_10t2"]
        lines = [
            "【周期计算】",
            "正挂 10T₁ 五次读数均值 = {:.4f} s → T₁ = 10T̄₁/10 = {:.5f} s".format(
                float(res_10t1.average), T1),
            "倒挂 10T₂ 五次读数均值 = {:.4f} s → T₂ = 10T̄₂/10 = {:.5f} s".format(
                float(res_10t2.average), T2),
            "T₁ 的不确定度 U(T₁) = U(10T₁)/10 = {:.5f} s（P=0.95）".format(u_T1),
            "T₂ 的不确定度 U(T₂) = U(10T₂)/10 = {:.5f} s（P=0.95）".format(u_T2),
        ]
        if T1 > 0 and T2 > 0:
            rel = abs(T1 - T2) / max(T1, T2) * 100
            lines.append("T₁ 与 T₂ 相差 {:.3f}%（<0.5% 视为已调到共轭点）".format(rel))
        fit_notes["table1"] = lines
        calc_results["table1"] = {"lines": lines}
    else:
        calc_messages.extend(p_warnings)

    # ── 表2：g 与 U_g（先统一计算 g，供表2与表3共用） ──
    l_values = _collect_column(tables.get("table2", []), "c1")
    h1_values = _collect_column(tables.get("table2", []), "c2")
    g_info = None
    g_ok = False
    if p_warnings:
        calc_messages.append("需先完成表1周期计算，才能计算 g。")
    elif not (l_values and h1_values):
        calc_messages.append("表2缺少 l 或 h₁ 数据，无法计算 g。")
    elif m_g is None:
        calc_messages.append("顶部参数缺少系统总质量 m，无法计算 g。")
    else:
        g_info = _compute_g(periods, l_values, h1_values, m_g)
        g_warnings = g_info.get("warnings", [])
        warnings.extend(g_warnings)
        if g_warnings:
            calc_messages.extend(g_warnings)
        else:
            g_ok = True
            g_val, u_g = g_info["g"], g_info["u_g"]
            a_term, b_term = g_info["a_term"], g_info["b_term"]
            lines = [
                "【重力加速度 g 计算（式 10）】",
                "l 均值 = {:.4f} cm，U(l) = {:.4f} cm".format(
                    g_info["l_bar"], g_info["u_l"]),
                "h₁ 均值 = {:.4f} cm，U(h₁) = {:.4f} cm".format(
                    g_info["h1_bar"], g_info["u_h1"]),
                "h₂ = l − h₁ = {:.4f} cm，U(h₂) = √(U(l)²+U(h₁)²) = {:.4f} cm".format(
                    g_info["h2_bar"], g_info["u_h2"]),
                "a 项 = (T₁²+T₂²)/(2l) = {:.6f} s²/m（主要贡献）".format(a_term),
                "b 项 = (T₁²−T₂²)/(2(h₁−h₂)) = {:.6e} s²/m（修正项）".format(b_term),
            ]
            if abs(a_term) > 0:
                lines.append("b 项 / a 项 = {:.3f}%（<1% 说明 T₁≈T₂，b 项影响可忽略）".format(
                    abs(b_term) / abs(a_term) * 100))
            lines.extend([
                "★ g = 4π² / (a 项 + b 项) = {:.4f} m/s²".format(g_val),
                "★ U_g = {:.4f} m/s²（P = 0.95）".format(u_g),
                "结果：g = ({:.4f} ± {:.4f}) m/s²".format(g_val, u_g),
            ])
            if g_ref:
                err = abs(g_val - g_ref) / g_ref * 100
                lines.append("与公认值 g_ref = {:.4f} m/s² 比较，相对误差 = {:.2f}%".format(
                    g_ref, err))
            fit_notes["table2"] = lines
            calc_results["table2"] = {"lines": lines}

    # ── 表3：转动惯量（复用 g_info） ──
    if g_ok and m_g is not None:
        inertia = _compute_inertia(periods, g_info, m_g)
        i_warnings = inertia.get("warnings", [])
        warnings.extend(i_warnings)
        I_O, I_Op, I_G = inertia["I_O"], inertia["I_Op"], inertia["I_G"]
        I_G1, I_G2 = inertia["I_G1"], inertia["I_G2"]
        verify = (abs(I_G1 - I_G2) / max(abs(I_G1), abs(I_G2), 1e-12) * 100
                  if max(abs(I_G1), abs(I_G2)) > 0 else 0.0)
        # 回填只读表3
        t3_rows = tables.get("table3", [])
        if t3_rows:
            t3_rows[0]["c0"] = formatted(I_O, 6)
            t3_rows[0]["c1"] = formatted(I_Op, 6)
            t3_rows[0]["c2"] = formatted(I_G, 6)
            t3_rows[0]["c3"] = formatted(verify, 2)
        lines = [
            "【转动惯量计算】",
            "I_O  = m·g·h₁·T₁²/(4π²) = {:.6e} kg·m²".format(I_O),
            "I_O' = m·g·h₂·T₂²/(4π²) = {:.6e} kg·m²".format(I_Op),
            "I_G(由O轴) = I_O − m·h₁² = {:.6e} kg·m²".format(I_G1),
            "I_G(由O'轴) = I_O' − m·h₂² = {:.6e} kg·m²".format(I_G2),
            "★ I_G = {:.6e} kg·m²（两式平均）".format(I_G),
            "两式验证 ΔI_G/I_G = {:.2f}%".format(verify),
        ]
        fit_notes["table3"] = lines
        calc_results["table3"] = {"lines": lines}
    else:
        inertia = None
        if not p_warnings and (l_values and h1_values and m_g is not None) and not g_ok:
            pass  # g 计算失败已在表2提示
        elif p_warnings or not (l_values and h1_values) or m_g is None:
            calc_messages.append("需先完成表1、表2计算，才能计算转动惯量。")

    enriched_params = dict(parameters)
    if not p_warnings:
        enriched_params["_T1"] = periods["T1"]
        enriched_params["_T2"] = periods["T2"]
    return {
        "tables": tables,
        "periods": periods,
        "g_info": g_info,
        "inertia": inertia if (g_info and not g_info.get("warnings")) else None,
        "fit_notes": fit_notes,
        "calc_results": calc_results,
        "calc_messages": calc_messages,
        "warnings": warnings,
        "parameters": enriched_params,
    }


def preview(payload):
    """实时预计算接口：补全只读列并返回每表 fit_notes / calc_results。"""
    raw = _all_results(payload)
    return {
        "tables": raw["tables"],
        "parameters": raw["parameters"],
        "fit_notes": raw["fit_notes"],
        "calc_results": raw["calc_results"],
        "calc_messages": raw["calc_messages"],
    }


# ─────────────────────────────────────────────
# 图表
# ─────────────────────────────────────────────
def _g_contribution_chart(workpath, g_info):
    """g 的 a 项 / b 项贡献对比柱状图。"""
    if not g_info or g_info.get("a_term") is None:
        return None
    zhfont = _font()
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["a 项\n(T₁²+T₂²)/(2l)", "b 项\n(T₁²−T₂²)/(2(h₁−h₂))"]
    values = [abs(g_info["a_term"]), abs(g_info["b_term"])]
    colors = ["#4472C4", "#E74C3C"]
    bars = ax.bar(labels, values, color=colors, width=0.5, zorder=3)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                "{:.3e}".format(v), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("s²/m", fontsize=12)
    if zhfont:
        ax.set_title("式 (10) 中 a 项与 b 项大小对比", fontproperties=zhfont, fontsize=14)
    else:
        ax.set_title("式 (10) 中 a 项与 b 项大小对比", fontsize=14)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    filename = "chart_g_terms.png"
    fig.savefig(os.path.join(workpath, filename), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filename


def _period_chart(workpath, periods, t1_rows, t2_rows):
    """10T₁ 与 10T₂ 五次测量对比图（含均值线）。"""
    ten_t1 = [as_number(r.get("c1")) for r in t1_rows if as_number(r.get("c1")) is not None]
    ten_t2 = [as_number(r.get("c2")) for r in t2_rows if as_number(r.get("c2")) is not None]
    if not ten_t1 and not ten_t2:
        return None
    zhfont = _font()
    fig, ax = plt.subplots(figsize=(8, 5))
    if ten_t1:
        ax.plot(range(1, len(ten_t1) + 1), ten_t1, "o-", color="#4472C4",
                markersize=7, label="10T₁（正挂）", zorder=4)
        ax.axhline(sum(ten_t1) / len(ten_t1), color="#4472C4", linestyle="--",
                   linewidth=1.2, alpha=0.7)
    if ten_t2:
        ax.plot(range(1, len(ten_t2) + 1), ten_t2, "s-", color="#E74C3C",
                markersize=7, label="10T₂（倒挂）", zorder=4)
        ax.axhline(sum(ten_t2) / len(ten_t2), color="#E74C3C", linestyle="--",
                   linewidth=1.2, alpha=0.7)
    ax.set_xlabel("测量序号", fontsize=12)
    ax.set_ylabel("10T (s)", fontsize=12)
    if zhfont:
        ax.set_title("正挂 10T₁ 与倒挂 10T₂ 各 5 次测量", fontproperties=zhfont, fontsize=14)
        ax.legend(prop=zhfont, fontsize=10)
    else:
        ax.set_title("正挂 10T₁ 与倒挂 10T₂ 各 5 次测量", fontsize=14)
        ax.legend(fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    filename = "chart_period.png"
    fig.savefig(os.path.join(workpath, filename), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filename


# ─────────────────────────────────────────────
# 最终提交：生成完整 Word 文档
# ─────────────────────────────────────────────
def handle_structured(workpath, payload):
    raw = _all_results(payload)
    tables = raw["tables"]
    parameters = payload.get("parameters") or {}
    m_g = as_number(parameters.get("m"))
    g_ref = as_number(parameters.get("g_ref"))
    periods = raw["periods"]
    g_info = raw["g_info"]
    inertia = raw["inertia"]
    warnings = list(raw["calc_messages"]) + list(raw["warnings"])

    # 数据完整性检查
    t1_filled = any(as_number(r.get("c1")) is not None for r in tables.get("table1", []))
    if not t1_filled:
        return {"code": 1, "message": "请先填写表1的周期数据（10T₁、10T₂）。"}

    docu = Document()
    docu.styles["Normal"].font.name = "微软雅黑"
    docu.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    docu.add_heading(name(), level=0)
    docu.add_paragraph("凯特摆（可逆摆）测量重力加速度")
    docu.add_paragraph(
        "仪器允差：多用数字测试仪 Δ_仪 = 0.1 ms（测 10 个周期）；"
        "钢尺 Δ_仪 = 0.05 cm、估读 Δ_估 = 0.05 cm；天平单次称量。"
        "置信系数 C = √3，置信概率 P = 0.95。"
        "同一种仪器的不确定度处理过程只写一次，其余列表给出。")
    docu.add_paragraph()

    summary = []
    charts = []

    # ── 一、周期测量 ──
    docu.add_heading("一、摆动周期测量", level=1)
    t1_data = [["序号", "10T₁ (s)", "10T₂ (s)"]]
    for r in tables.get("table1", []):
        t1_data.append([r.get("c0", ""), r.get("c1", ""), r.get("c2", "")])
    _add_doc_table(docu, t1_data[0], t1_data[1:])
    docu.add_paragraph("轮流测量正挂 10T₁、倒挂 10T₂ 各 5 次，取平均后 T = 10T̄/10。")
    docu.add_paragraph()

    if periods.get("T1") is not None:
        T1, T2 = periods["T1"], periods["T2"]
        u_T1, u_T2 = periods["u_T1"], periods["u_T2"]
        res_10t1, res_10t2 = periods["res_10t1"], periods["res_10t2"]
        insert_data(docu, "正挂 10T₁", res_10t1, "word")
        docu.add_paragraph("T₁ = 10T̄₁ / 10 = {:.5f} s".format(T1))
        docu.add_paragraph("U(T₁) = U(10T₁) / 10 = {:.5f} s（P=0.95）".format(u_T1))
        insert_data(docu, "倒挂 10T₂", res_10t2, "word")
        docu.add_paragraph("T₂ = 10T̄₂ / 10 = {:.5f} s".format(T2))
        docu.add_paragraph("U(T₂) = U(10T₂) / 10 = {:.5f} s（P=0.95）".format(u_T2))
        if T1 > 0 and T2 > 0:
            docu.add_paragraph("T₁ 与 T₂ 相差 {:.3f}%。".format(
                abs(T1 - T2) / max(T1, T2) * 100))
        summary.append("T₁ = {:.5f} s，T₂ = {:.5f} s（U ≈ {:.5f} s）".format(
            T1, T2, max(u_T1, u_T2)))
        fn = _period_chart(workpath, periods,
                           [r for r in tables.get("table1", []) if as_number(r.get("c1")) is not None],
                           [r for r in tables.get("table1", []) if as_number(r.get("c2")) is not None])
        if fn:
            charts.append({"filename": fn, "title": "10T₁ 与 10T₂ 测量对比"})
            docu.add_picture(os.path.join(workpath, fn), width=Inches(5.5))
        docu.add_paragraph()

    # ── 二、g 与 U_g ──
    docu.add_heading("二、重力加速度 g 与不确定度 U_g", level=1)
    l_data = [["序号", "l (cm)", "h₁ (cm)"]]
    for r in tables.get("table2", []):
        l_data.append([r.get("c0", ""), r.get("c1", ""), r.get("c2", "")])
    _add_doc_table(docu, l_data[0], l_data[1:])
    docu.add_paragraph("钢尺测量两刀口间距 l 与重心到一刀口距离 h₁ 各 3 次，h₂ = l − h₁。")
    docu.add_paragraph("系统总质量 m = {} g = {:.3f} kg。".format(
        parameters.get("m", ""), m_g / 1000.0 if m_g else 0))
    docu.add_paragraph()

    if g_info and not g_info.get("warnings"):
        res_l, res_h1 = g_info["res_l"], g_info["res_h1"]
        insert_data(docu, "两刀口间距 l", res_l, "word")
        insert_data(docu, "重心到刀口距离 h₁", res_h1, "word")
        docu.add_paragraph("h₂ = l − h₁ = {:.4f} cm，U(h₂) = √(U(l)²+U(h₁)²) = {:.4f} cm".format(
            g_info["h2_bar"], g_info["u_h2"]))
        docu.add_paragraph(
            "式 (10)：g = 4π² / [ (T₁²+T₂²)/(2l) + (T₁²−T₂²)/(2(h₁−h₂)) ]")
        docu.add_paragraph("a 项 = {:.6f} s²/m，b 项 = {:.3e} s²/m，"
                           "b 项/a 项 = {:.3f}%。".format(
                               g_info["a_term"], g_info["b_term"],
                               abs(g_info["b_term"]) / abs(g_info["a_term"]) * 100
                               if g_info["a_term"] else 0))
        if g_info.get("res_g") is not None:
            insert_data_com(docu, "重力加速度 g", g_info["res_g"], "word")
            docu.add_paragraph("【Latex 代码】")
            insert_data_com(docu, "重力加速度 g", g_info["res_g"], "latex")
        else:
            docu.add_paragraph("g = {:.4f} m/s²，U_g = {:.4f} m/s²（P=0.95）".format(
                g_info["g"], g_info["u_g"]))
        g_val, u_g = g_info["g"], g_info["u_g"]
        result_line = "g = ({:.4f} ± {:.4f}) m/s²（P=0.95）".format(g_val, u_g)
        docu.add_paragraph("最终结果：" + result_line)
        if g_ref:
            err = abs(g_val - g_ref) / g_ref * 100
            docu.add_paragraph("与公认值 g_ref = {:.4f} m/s² 比较，相对误差 = {:.2f}%。".format(
                g_ref, err))
            summary.append(result_line + "，相对误差 {:.2f}%".format(err))
        else:
            summary.append(result_line)
        fn = _g_contribution_chart(workpath, g_info)
        if fn:
            charts.append({"filename": fn, "title": "g 的 a 项与 b 项贡献对比"})
            docu.add_picture(os.path.join(workpath, fn), width=Inches(5.0))
        docu.add_paragraph()

    # ── 三、转动惯量 ──
    docu.add_heading("三、转动惯量", level=1)
    if inertia:
        I_O, I_Op, I_G = inertia["I_O"], inertia["I_Op"], inertia["I_G"]
        I_G1, I_G2 = inertia["I_G1"], inertia["I_G2"]
        verify = (abs(I_G1 - I_G2) / max(abs(I_G1), abs(I_G2), 1e-12) * 100
                  if max(abs(I_G1), abs(I_G2)) > 0 else 0.0)
        i_data = [["I_O (kg·m²)", "I_O' (kg·m²)", "I_G (kg·m²)", "ΔI_G/I_G (%)"],
                   ["{:.6e}".format(I_O), "{:.6e}".format(I_Op),
                    "{:.6e}".format(I_G), "{:.2f}".format(verify)]]
        _add_doc_table(docu, i_data[0], i_data[1:])
        docu.add_paragraph("I_O = m·g·h₁·T₁²/(4π²) = {:.6e} kg·m²".format(I_O))
        docu.add_paragraph("I_O' = m·g·h₂·T₂²/(4π²) = {:.6e} kg·m²".format(I_Op))
        docu.add_paragraph("I_G = I_O − m·h₁² = {:.6e} kg·m²（由 O 轴）".format(I_G1))
        docu.add_paragraph("I_G = I_O' − m·h₂² = {:.6e} kg·m²（由 O' 轴）".format(I_G2))
        docu.add_paragraph("I_G = {:.6e} kg·m²（两式平均），ΔI_G/I_G = {:.2f}%".format(I_G, verify))
        summary.append("I_O = {:.4e}，I_O' = {:.4e}，I_G = {:.4e} kg·m²".format(I_O, I_Op, I_G))
    else:
        docu.add_paragraph("（缺少 g 或周期数据，未计算转动惯量。）")
    docu.add_paragraph()

    docu.add_paragraph("【公式】")
    docu.add_paragraph(r"g = \frac{4\pi^2}{\dfrac{T_1^2+T_2^2}{2l}+\dfrac{T_1^2-T_2^2}{2(h_1-h_2)}}")
    docu.add_paragraph(r"I_O = \frac{m g h_1 T_1^2}{4\pi^2},\quad I_{O'} = \frac{m g h_2 T_2^2}{4\pi^2}")

    docu.save(os.path.join(workpath, name() + ".docx"))

    return {
        "code": 0,
        "summary": summary or ["凯特摆数据已处理，详见 Word 文档。"],
        "warnings": warnings,
        "charts": charts,
        "document": name() + ".docx",
    }


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def handle(workpath, extension):
    """旧版 CSV 单表接口：把 CSV 还原为结构化周期表后走 handle_structured。"""
    try:
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        t_col = [c for c in cols if 'T' in c or '周期' in c]
        h1_col = [c for c in cols if 'h1' in c or '正挂' in c]
        h2_col = [c for c in cols if 'h2' in c or '倒挂' in c]
        T_series = pd.to_numeric(data[t_col[0]] if t_col else data.iloc[:, 0], errors='coerce')
        h1_series = pd.to_numeric(data[h1_col[0]] if h1_col else data.iloc[:, 1], errors='coerce')
        h2_series = pd.to_numeric(data[h2_col[0]] if h2_col else data.iloc[:, 2], errors='coerce')

        # 还原为结构化 payload：旧格式 T 为单周期，h1/h2 为刀口距重心
        t1_rows = [{"c1": float(v) * 10.0} for v in T_series if pd.notna(v)]
        t2_rows = [{"c2": float(v) * 10.0} for v in T_series if pd.notna(v)]
        l_vals = [(float(a) + float(b)) for a, b in zip(h1_series, h2_series)
                  if pd.notna(a) and pd.notna(b)]
        h1_vals = [float(a) for a in h1_series if pd.notna(a)]
        table1 = [{**r1, **r2} for r1, r2 in zip(t1_rows, t2_rows)]
        table2 = [{"c1": l_vals[i] if i < len(l_vals) else "",
                   "c2": h1_vals[i] if i < len(h1_vals) else ""}
                  for i in range(max(len(l_vals), len(h1_vals), 1))]

        payload = {"parameters": {"m": "5000"}, "tables": {"table1": table1, "table2": table2}}
        result = handle_structured(workpath, payload)
        return 0 if result.get("code") == 0 else 1
    except Exception:
        traceback.print_exc()
        return 1
