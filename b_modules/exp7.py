"""固体比热与冷却法测量金属比热实验模块
========================================
一级大物热学实验 —— 同一份《固体比热（实验指导）》包含两个实验，
通过顶部「实验内容」下拉切换（与 exp37 摄谱仪与单色仪相同的交互方式）：

实验一：混合法测定固体比热容（锌粒）
  采用雷诺校正（外推法）求修正初温 T1 和修正末温 T2：
    阶段一（倒入前）线性拟合 → AB 延长至 t_G
    阶段三（降温期）线性拟合 → CD 回延至 t_G
    T1 = AB(t_G)，T2 = CD(t_G)
  热平衡方程：
    cx = [(m·c + m1·c1 + 1.9·V)·(T2 − T1)] / [mx·(T' − T2)]
    其中质量单位统一为 kg（输入为 g，需 ÷1000）

实验二：冷却法测量金属比热容
  三种样品（铜、铁、铝）加热到约 200 ℃ 后在防风圆筒内自然冷却，
  记录温度从 102 ℃ 降到 98 ℃ 所需时间 Δt，每种样品重复测量 2 次取平均。
  以铜为标准样品（C_Cu = 0.0940 cal/(g·℃)）：
    C_2 = C_1 × (M_1 · Δt_2) / (M_2 · Δt_1)
  分别求出铁、铝的比热容并与标准值比较求相对误差。
"""

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data, load_sample_data_numeric
from optics_common import (
    OpticsInputError,
    add_key_values,
    add_summary,
    add_table,
    configure_plotting,
    create_document,
    error_result,
    finish_report,
    get_parameter,
    get_rows,
    save_figure,
)

# ── 实验内容选择 ──
_PART_MIXING = {"parameter": "part", "equals": "mixing"}
_PART_COOLING = {"parameter": "part", "equals": "cooling"}

# ── 实验一（混合法）物理常数 ──
_C_W = 4187.0       # 水的比热容 J/(kg·°C)
_C_C = 385.0        # 量热器(铜)比热容 J/(kg·°C)
_C_X_STD = 386.0    # 锌的标准比热容 J/(kg·°C)

# ── 三阶段预设时间 (min)，仅作记录参考 ──
_PHASE1_TIMES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
_PHASE2_TIMES = [5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
_PHASE3_TIMES = [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
_ALL_TIMES = _PHASE1_TIMES + _PHASE2_TIMES + _PHASE3_TIMES

# ── 实验二（冷却法）物理常数 ──
_METALS = ("铜", "铁", "铝")

# 100 ℃ 时三种金属的标准比热容 cal/(g·℃)（指导书表 1）
_C_CU_STD = 0.0940
_C_FE_STD = 0.110
_C_AL_STD = 0.230

# 冷却法金属比热容测定仪技术指标：与公认值的百分差小于 5%
_MAX_DELTA_PERCENT = 5.0


def _extract_phase(rows):
    """从表格行提取 (t, T) 数据点，跳过时间为空的行。"""
    pts = []
    for row in rows:
        t_val = as_number(row.get("c0"))
        T_val = as_number(row.get("c1"))
        if t_val is not None:
            pts.append((t_val, T_val))
    return pts


def _linear_fit(xs, ys):
    """最小二乘线性回归，返回 (k, b)。"""
    n = len(xs)
    if n < 2:
        return None, None
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return None, None
    k = num / den
    b = y_mean - k * x_mean
    return k, b


def _split_sample_phases(rows):
    """把固体比热（示例数据）.csv 的完整 T-t 记录按阶段拆开：
    倒入前（t ≤ 0）、混合升温（0 < t ≤ 3）、均匀降温（t > 3）。"""
    phase1, phase2, phase3 = [], [], []
    for row in rows:
        if len(row) < 2:
            continue
        try:
            t = float(row[0])
        except (TypeError, ValueError):
            continue
        if t <= 0:
            phase1.append(row)
        elif t <= 3:
            phase2.append(row)
        else:
            phase3.append(row)
    return phase1, phase2, phase3


def _cooling_sample():
    """示例数据：Δθ = 102 ℃ → 98 ℃，每种样品重复 2 次。

    优先读取 b_static/experiment/exp7/冷却法（示例数据）.csv，缺失时回退到内置数据。
    """
    raw = load_sample_data_numeric("exp7", "冷却法（示例数据）")
    rows = [row for row in raw if len(row) >= 3 and row[0] and row[1] != "" and row[2] != ""]
    if rows:
        return [{"sample": row[0], "dt1": row[1], "dt2": row[2]} for row in rows]
    return [
        {"sample": "铜", "dt1": 12.1, "dt2": 11.9},
        {"sample": "铁", "dt1": 12.5, "dt2": 12.3},
        {"sample": "铝", "dt1": 9.1, "dt2": 8.9},
    ]


def name():
    return "固体比热与冷却法测量金属比热"


def handle(workpath, extension):
    """旧版 CSV 接口。"""
    try:
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)
        os.remove(excelpath)
        docu = Document()
        style_doc_font(docu)
        docu.add_paragraph(name())
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    sample_p1, sample_p2, sample_p3 = _split_sample_phases(
        load_sample_data("exp7", "固体比热")
    )

    columns = ["t(min)", "T(°C)"]

    # 阶段一图表：单独查看倒入前的温度趋势（可选）
    chart_p1 = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "t (min)",
        "y_label": "T (°C)",
        "title": "阶段一：倒入前温度趋势",
        "fit": "linear",
    }

    part_parameter = {
        "id": "part", "label": "实验内容", "type": "select", "default": "mixing",
        "required": True,
        "options": [
            {"value": "mixing", "label": "实验一：混合法测定固体比热容（锌粒）"},
            {"value": "cooling", "label": "实验二：冷却法测量金属比热容"},
        ],
    }

    mixing_parameters = [
        {"id": "t_room", "label": "室温 T室 (°C)", "default": "", "condition": _PART_MIXING},
        {"id": "mx", "label": "锌粒质量 mx (g)", "default": "", "condition": _PART_MIXING},
        {"id": "m1", "label": "量热器内筒+搅拌器质量 m1 (g)", "default": "", "condition": _PART_MIXING},
        {"id": "m", "label": "水的质量 m (g)", "default": "", "condition": _PART_MIXING},
        {"id": "T_prime", "label": "锌粒加热温度 T' (°C)（沸点）", "default": "", "condition": _PART_MIXING},
        {"id": "V", "label": "温度计浸入水中体积 V (cm³)", "default": "2.0", "condition": _PART_MIXING},
        {"id": "c_w", "label": "水的比热容 c (J/(kg·°C))", "default": "4187", "condition": _PART_MIXING},
        {"id": "c1", "label": "量热器(铜)比热容 c1 (J/(kg·°C))", "default": "385", "condition": _PART_MIXING},
    ]

    mixing_tables = [
        make_table(
            "table1", "阶段一：倒入锌粒前（每隔 1 分钟记录）",
            columns,
            sample=sample_p1,
            readonly=(),
            initial_rows=6,
            chart=chart_p1,
            description="倒入锌粒前，每隔 1 分钟记录一次水温，"
                        "共 6 个点。用于拟合 AB 直线。",
        ),
        make_table(
            "table2", "阶段二：混合升温期（每隔 0.5 分钟记录）",
            columns,
            sample=sample_p2,
            readonly=(),
            initial_rows=6,
            description="锌粒倒入量热器后温度迅速上升，每隔 0.5 分钟记录一次。"
                        "用于确定特征时刻 t_G（升温曲线穿过室温线的时刻）。",
        ),
        make_table(
            "table3", "阶段三：均匀降温期（每隔 1 分钟记录）",
            columns,
            sample=sample_p3,
            readonly=(),
            initial_rows=7,
            description="升温停止后恢复每 1 分钟记录一次，"
                        "共 7 个点。用于拟合 CD 直线。",
        ),
    ]
    for table in mixing_tables:
        table["condition"] = _PART_MIXING

    cooling_parameters = [
        {"id": "m_cu", "label": "铜样品质量 M_Cu", "unit": "g", "type": "number",
         "required": True, "step": "0.01", "help": "用天平称出铜（标准）样品质量。",
         "condition": _PART_COOLING},
        {"id": "m_fe", "label": "铁样品质量 M_Fe", "unit": "g", "type": "number",
         "required": True, "step": "0.01", "help": "用天平称出铁（待测）样品质量。",
         "condition": _PART_COOLING},
        {"id": "m_al", "label": "铝样品质量 M_Al", "unit": "g", "type": "number",
         "required": True, "step": "0.01", "help": "用天平称出铝（待测）样品质量。",
         "condition": _PART_COOLING},
    ]

    # 冷却区间与 100 ℃ 标准比热容均为指导书固定值，不作为可修改参数，
    # 在冷却时间表上方列出（计算时使用模块内置常数）。
    _COOLING_CONSTANTS = (
        "冷却区间固定为 102 ℃ → 98 ℃（Δθ = 4 ℃）；"
        "100 ℃ 标准比热容固定为：铜 C_Cu = 0.0940、铁 C_Fe = 0.110、"
        "铝 C_Al = 0.230 cal/(g·℃)。"
    )

    cooling_table = {
        "id": "cooling_time",
        "title": "冷却时间测量（102 ℃ → 98 ℃，重复2次）",
        "required": True,
        "min_rows": 3,
        "initial_rows": 3,
        "condition": _PART_COOLING,
        "description": (
            _COOLING_CONSTANTS
            + "每行对应一种样品：先测铜（标准样品），再测铁、铝。"
            "同一样品在相同温度区间内冷却，重复测量 2 次，结果取平均。"
        ),
        "columns": [
            {"id": "sample", "label": "样品", "type": "text"},
            {"id": "dt1", "label": "第1次 Δt", "unit": "s"},
            {"id": "dt2", "label": "第2次 Δt", "unit": "s"},
        ],
        "sample": _cooling_sample(),
    }

    # 理论内容：混合法按表提供（exp7），冷却法挂在 cooling_time 表上（exp7_b）
    table_theory = dict(get_table_theory("exp7"))
    cooling_theory = get_table_theory("exp7_b").get("_global")
    if cooling_theory:
        table_theory["cooling_time"] = cooling_theory

    return make_schema(
        (
            "本实验包含同一指导书的两个项目，请先在顶部「实验内容」中选择。"
            "实验一（混合法，锌粒）：记录三阶段升温的温度-时间数据，"
            "用雷诺外推法求 " r"$T_1$" "、" r"$T_2$" "，按 "
            r"$c_x = \frac{(mc + m_1c_1 + 1.9V)(T_2 - T_1)}{m_x(T' - T_2)}$"
            " 计算锌的比热容；实验二（冷却法，金属）：以铜为标准，"
            "记录铁、铝样品由 102 ℃ 冷却到 98 ℃ 的两次计时，计算铁、铝的比热容及相对误差。"
        ),
        mixing_tables + [cooling_table],
        parameters=[part_parameter] + mixing_parameters + cooling_parameters,
        analysis_hints="本页包含同一指导书的两个实验，请先在顶部「实验内容」中选择。"
                       "实验一（混合法）：三个表格分别对应三个阶段，各表可独立添加/删除行、"
                       "填入示例数据，系统自动用雷诺外推法求 T1、T2，"
                       "由 cx = [(m·c + m1·c1 + 1.9·V)·(T2−T1)] / [mx·(T'−T2)] 计算锌比热容。"
                       "实验二（冷却法）：填写铜、铁、铝样品质量与各自从 102 ℃ 冷却到 98 ℃ 的"
                       "两次计时，以铜为标准样品计算铁、铝的比热容及相对误差。",
        preview_enabled=True,
        table_theory=table_theory,
        report_enabled=False,
        parameters_sample={
            # 实验一：混合法
            "t_room": "20.5", "mx": "80.0", "m1": "120.0", "m": "200.0",
            "T_prime": "100.0", "V": "2.0", "c_w": "4187", "c1": "385",
            # 实验二：冷却法（冷却区间与标准比热容为固定值，无需填写）
            "m_cu": "62.1", "m_fe": "57.8", "m_al": "21.9",
        },
    )


def preview(payload):
    """按所选实验内容返回预计算结果；冷却法无实时预计算，原样返回表格。"""
    part = (payload.get("parameters") or {}).get("part", "mixing")
    if part == "cooling":
        return {
            "tables": copied_tables(payload),
            "parameters": dict(payload.get("parameters") or {}),
        }
    return _preview_mixing(payload)


def _preview_mixing(payload):
    """雷诺校正（外推法）求 T1、T2，再计算 cx 和 δ。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})

    # ── 从参数提取直接测量量 ──
    t_room = as_number(params.get("t_room"))
    mx = as_number(params.get("mx"))
    m1 = as_number(params.get("m1"))
    m = as_number(params.get("m"))
    T_prime = as_number(params.get("T_prime"))
    V = as_number(params.get("V", "2.0")) or 2.0
    c_w = as_number(params.get("c_w", "4187")) or _C_W
    c1 = as_number(params.get("c1", "385")) or _C_C

    # ── 从三个表格提取温度-时间数据 ──
    phase1 = _extract_phase(tables.get("table1", []))
    phase2 = _extract_phase(tables.get("table2", []))
    phase3 = _extract_phase(tables.get("table3", []))

    # ── 步骤 2：线性拟合 ──
    k1, b1 = None, None
    k2, b2 = None, None
    p1_valid = [(t, T) for t, T in phase1 if T is not None]
    p3_valid = [(t, T) for t, T in phase3 if T is not None]
    if len(p1_valid) >= 2:
        k1, b1 = _linear_fit([t for t, _ in p1_valid], [T for _, T in p1_valid])
    if len(p3_valid) >= 2:
        k2, b2 = _linear_fit([t for t, _ in p3_valid], [T for _, T in p3_valid])

    # ── 步骤 3：确定特征时刻 t_G ──
    t_G = None
    p2_valid = [(t, T) for t, T in phase2 if T is not None]
    fallback_note = ""
    if t_room is not None and p2_valid:
        for i in range(len(p2_valid) - 1):
            t_a, T_a = p2_valid[i]
            t_b, T_b = p2_valid[i + 1]
            if T_a < t_room <= T_b:
                # 线性插值求 t_G
                frac = (t_room - T_a) / (T_b - T_a) if T_b != T_a else 0
                t_G = t_a + frac * (t_b - t_a)
                break
            elif T_a == t_room:
                t_G = t_a
                break
        if t_G is None:
            # 检查是否有任何点 >= T室
            has_above = any(T >= t_room for _, T in p2_valid)
            if not has_above:
                t_G = 5.0
                fallback_note = "升温段未达到室温，已使用倒入时刻作为校正基准"
            else:
                t_G = 5.0
    elif t_room is None:
        t_G = 5.0
        fallback_note = "未填写室温，已使用倒入时刻作为校正基准"

    # ── 步骤 4：求 T1 和 T2 ──
    T1 = None
    T2 = None
    if k1 is not None and b1 is not None and t_G is not None:
        T1 = k1 * t_G + b1
    if k2 is not None and b2 is not None and t_G is not None:
        T2 = k2 * t_G + b2

    # ── 五、比热容计算 ──
    cx = None
    delta = None
    if all(v is not None for v in (mx, m, m1, T1, T2, T_prime, V)):
        denom_kg = (mx / 1000.0) * (T_prime - T2)
        if denom_kg > 0:
            numer = ((m / 1000.0) * c_w + (m1 / 1000.0) * c1 + 1.9 * V) * (T2 - T1)
            cx = numer / denom_kg
            delta = abs(cx - _C_X_STD) / _C_X_STD * 100

    # ── 写入计算结果 ──
    enriched_params = dict(params)
    enriched_params.update({
        "_k1": formatted(k1, 4) if k1 is not None else "",
        "_b1": formatted(b1, 4) if b1 is not None else "",
        "_k2": formatted(k2, 4) if k2 is not None else "",
        "_b2": formatted(b2, 4) if b2 is not None else "",
        "_t_G": formatted(t_G, 2) if t_G is not None else "",
        "_T1": formatted(T1, 2) if T1 is not None else "",
        "_T2": formatted(T2, 2) if T2 is not None else "",
        "_dT": formatted(T2 - T1, 2) if (T1 is not None and T2 is not None) else "",
        "_cx": formatted(cx, 2) if cx is not None else "",
        "_delta": formatted(delta, 2) if delta is not None else "",
        "_fallback_note": fallback_note,
        # 供图表使用
        "_phase1": p1_valid,
        "_phase2": p2_valid,
        "_phase3": p3_valid,
        "_k1_raw": k1,
        "_b1_raw": b1,
        "_k2_raw": k2,
        "_b2_raw": b2,
        "_t_G_raw": t_G,
        "_T1_raw": T1,
        "_T2_raw": T2,
        "_t_room_raw": t_room,
    })

    return {"tables": tables, "parameters": enriched_params}


def _generate_Tt_chart(enriched_params, workpath):
    """自定义 T-t 曲线图（含雷诺校正辅助线）。"""
    try:
        zhfont = matplotlib.font_manager.FontProperties(
            fname=os.path.join(os.path.dirname(__file__), "SourceHanSansSC-Regular.otf")
        )
    except Exception:
        zhfont = matplotlib.font_manager.FontProperties()

    phase1 = enriched_params.get("_phase1", [])
    phase2 = enriched_params.get("_phase2", [])
    phase3 = enriched_params.get("_phase3", [])
    k1 = enriched_params.get("_k1_raw")
    b1 = enriched_params.get("_b1_raw")
    k2 = enriched_params.get("_k2_raw")
    b2 = enriched_params.get("_b2_raw")
    t_G = enriched_params.get("_t_G_raw")
    T1 = enriched_params.get("_T1_raw")
    T2 = enriched_params.get("_T2_raw")
    t_room = enriched_params.get("_t_room_raw")

    all_pts = phase1 + phase2 + phase3
    if len(all_pts) < 3:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    # ── 阶段背景色 ──
    ax.axvspan(-0.3, 5.25, alpha=0.08, color='blue', label='_nolegend_')
    ax.axvspan(5.25, 8.25, alpha=0.08, color='orange', label='_nolegend_')
    ax.axvspan(8.25, 15.5, alpha=0.08, color='green', label='_nolegend_')
    ax.text(2.5, ax.get_ylim()[1] if ax.get_ylim()[1] else 20, '倒入前',
            ha='center', va='bottom', fontsize=9, color='blue', alpha=0.6,
            fontproperties=zhfont)
    ax.text(6.75, ax.get_ylim()[1] if ax.get_ylim()[1] else 20, '混合升温',
            ha='center', va='bottom', fontsize=9, color='orange', alpha=0.6,
            fontproperties=zhfont)
    ax.text(12.25, ax.get_ylim()[1] if ax.get_ylim()[1] else 20, '降温期',
            ha='center', va='bottom', fontsize=9, color='green', alpha=0.6,
            fontproperties=zhfont)

    # ── 原始数据点 ──
    ts = [t for t, _ in all_pts]
    Ts = [T for _, T in all_pts]
    ax.plot(ts, Ts, 'ko-', markersize=4, linewidth=1, label='T-t 数据', zorder=3)

    # ── 室温水平线 ──
    if t_room is not None:
        ax.axhline(y=t_room, color='gray', linestyle='--', linewidth=1,
                    label=f'T室 = {t_room}°C', zorder=1)

    # ── 阶段一拟合直线 AB（红色虚线，延长到 t_G）──
    if k1 is not None and b1 is not None:
        t_start = min(t for t, _ in phase1) if phase1 else 0
        t_end = t_G if t_G is not None else 5.0
        t_fit = [t_start, t_end]
        T_fit = [k1 * t + b1 for t in t_fit]
        ax.plot(t_fit, T_fit, 'r--', linewidth=1.5,
                label=f'AB: T = {k1:.4f}t + {b1:.4f}', zorder=2)

    # ── 阶段三拟合直线 CD（蓝色虚线，回延到 t_G）──
    if k2 is not None and b2 is not None:
        t_start = t_G if t_G is not None else 8.0
        t_end = max(t for t, _ in phase3) if phase3 else 15.0
        t_fit = [t_start, t_end]
        T_fit = [k2 * t + b2 for t in t_fit]
        ax.plot(t_fit, T_fit, 'b--', linewidth=1.5,
                label=f'CD: T = {k2:.4f}t + {b2:.4f}', zorder=2)

    # ── t_G 竖直辅助线 ──
    if t_G is not None:
        ax.axvline(x=t_G, color='gray', linestyle='-.', linewidth=1,
                    label=f't_G = {t_G:.2f} min', zorder=1)

    # ── E 点 (T1) 和 F 点 (T2) ──
    if t_G is not None and T1 is not None:
        ax.plot(t_G, T1, 'rs', markersize=10, zorder=5)
        ax.annotate(f'T1 = {T1:.2f}°C',
                    xy=(t_G, T1), xytext=(t_G + 0.8, T1 - 0.3),
                    fontsize=10, fontweight='bold', color='red',
                    fontproperties=zhfont,
                    arrowprops=dict(arrowstyle='->', color='red'))
    if t_G is not None and T2 is not None:
        ax.plot(t_G, T2, 'bs', markersize=10, zorder=5)
        ax.annotate(f'T2 = {T2:.2f}°C',
                    xy=(t_G, T2), xytext=(t_G + 0.8, T2 + 0.3),
                    fontsize=10, fontweight='bold', color='blue',
                    fontproperties=zhfont,
                    arrowprops=dict(arrowstyle='->', color='blue'))

    # ── 重新调整背景文字位置（需要知道 y 轴范围）──
    y_min, y_max = ax.get_ylim()
    for txt in ax.texts:
        txt.set_position((txt.get_position()[0], y_max - 0.1))

    ax.set_xlabel('t (min)', fontsize=12, fontproperties=zhfont)
    ax.set_ylabel('T (°C)', fontsize=12, fontproperties=zhfont)
    ax.set_title('温度-时间曲线（雷诺校正）', fontsize=14, fontproperties=zhfont)
    ax.legend(loc='upper right', fontsize=8, prop=zhfont)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    imgpath = os.path.join(workpath, "chart_Tt_reynolds.png")
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


# ─────────────────────────────────────────────
# 实验二：冷却法测量金属比热容
# ─────────────────────────────────────────────
def _match_metal(label):
    """按样品名中的关键字识别金属；无法识别返回 None。"""
    for metal in _METALS:
        if metal in str(label):
            return metal
    return None


def _collect_times(rows):
    """把冷却时间表整理成 {金属: [各次 Δt, ...]}，并完成数值校验。"""
    per_metal = {}
    for index, row in enumerate(rows, 1):
        label = str(row.get("sample", "")).strip()
        metal = _match_metal(label)
        if metal is None:
            raise OpticsInputError(
                f"第{index}行“样品”无法识别：请填写含“铜”“铁”或“铝”的样品名（当前：{label or '空'}）"
            )
        times = []
        for key in ("dt1", "dt2"):
            raw = str(row.get(key, "")).strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise OpticsInputError(f"第{index}行{metal}样品的冷却时间不是有效数字：{raw}") from exc
            if not np.isfinite(value) or value <= 0:
                raise OpticsInputError(f"第{index}行{metal}样品的冷却时间必须为正数")
            times.append(value)
        if not times:
            raise OpticsInputError(f"第{index}行{metal}样品至少需要填写一次冷却时间")
        per_metal.setdefault(metal, []).extend(times)
    return per_metal


def _handle_cooling(workpath, payload):
    try:
        masses = {
            "铜": get_parameter(payload, "m_cu", None, True),
            "铁": get_parameter(payload, "m_fe", None, True),
            "铝": get_parameter(payload, "m_al", None, True),
        }
        for metal, mass in masses.items():
            if mass <= 0:
                raise OpticsInputError(f"{metal}样品质量必须大于 0")

        # 冷却区间与标准比热容为固定常数，不再从前端参数读取
        c_cu = get_parameter(payload, "c_cu", _C_CU_STD)
        c_std = {
            "铁": get_parameter(payload, "c_fe_std", _C_FE_STD),
            "铝": get_parameter(payload, "c_al_std", _C_AL_STD),
        }
        if c_cu <= 0 or any(value <= 0 for value in c_std.values()):
            raise OpticsInputError("标准比热容必须大于 0")

        t_start = get_parameter(payload, "t_start", 102.0)
        t_end = get_parameter(payload, "t_end", 98.0)
        if t_start <= t_end:
            raise OpticsInputError("起始温度必须高于终止温度")

        rows = get_rows(payload, "cooling_time", required=True, min_rows=3)
        per_metal = _collect_times(rows)

        missing = [metal for metal in _METALS if metal not in per_metal]
        if missing:
            raise OpticsInputError("缺少样品的冷却时间：" + "、".join(missing))
        dt_avg = {metal: float(np.mean(values)) for metal, values in per_metal.items()}

        # ── 待求量：铁、铝的比热容 ──
        c_fe = c_cu * (masses["铜"] * dt_avg["铁"]) / (masses["铁"] * dt_avg["铜"])
        c_al = c_cu * (masses["铜"] * dt_avg["铝"]) / (masses["铝"] * dt_avg["铜"])
        delta_fe = abs(c_fe - c_std["铁"]) / c_std["铁"] * 100.0
        delta_al = abs(c_al - c_std["铝"]) / c_std["铝"] * 100.0

        warnings = []
        for metal, delta in (("铁", delta_fe), ("铝", delta_al)):
            if delta > _MAX_DELTA_PERCENT:
                warnings.append(
                    f"{metal}的比热容相对误差为 {delta:.2f}%，超过仪器指标 {_MAX_DELTA_PERCENT:.0f}%，"
                    "请检查质量称量、热电偶读数与冷却时间计时。"
                )

        summary = [
            f"冷却区间：{t_start:g} ℃ → {t_end:g} ℃（Δθ = {t_start - t_end:g} ℃）",
            f"平均冷却时间：铜 Δt̄ = {dt_avg['铜']:.3f} s，铁 Δt̄ = {dt_avg['铁']:.3f} s，"
            f"铝 Δt̄ = {dt_avg['铝']:.3f} s",
            f"铁的比热容 C_Fe = {c_fe:.4f} cal/(g·℃)"
            f"（标准值 {c_std['铁']:.3f}，相对误差 δ = {delta_fe:.2f}%）",
            f"铝的比热容 C_Al = {c_al:.4f} cal/(g·℃)"
            f"（标准值 {c_std['铝']:.3f}，相对误差 δ = {delta_al:.2f}%）",
        ]

        # ── Word 文档 ──
        doc = create_document(name(), "实验二：冷却法测量金属比热容")
        add_key_values(doc, "实验参数", [
            ("铜样品质量 M_Cu", f"{masses['铜']:g} g"),
            ("铁样品质量 M_Fe", f"{masses['铁']:g} g"),
            ("铝样品质量 M_Al", f"{masses['铝']:g} g"),
            ("铜的标准比热容 C_Cu", f"{c_cu:.4f} cal/(g·℃)"),
        ])
        add_table(doc, "表1  冷却时间测量与平均", ["样品", "各次 Δt / s", "平均 Δt̄ / s"], [
            [metal, "、".join(f"{value:.3f}" for value in per_metal[metal]), f"{dt_avg[metal]:.3f}"]
            for metal in _METALS
        ])
        add_table(doc, "表2  比热容计算结果与相对误差",
                  ["样品", "质量 M / g", "测量值 C / cal/(g·℃)", "标准值 / cal/(g·℃)", "相对误差 δ / %"], [
            ["铜", f"{masses['铜']:g}", f"{c_cu:.4f}", f"{c_cu:.4f}", "（标准样品）"],
            ["铁", f"{masses['铁']:g}", f"{c_fe:.4f}", f"{c_std['铁']:.3f}", f"{delta_fe:.2f}"],
            ["铝", f"{masses['铝']:g}", f"{c_al:.4f}", f"{c_std['铝']:.3f}", f"{delta_al:.2f}"],
        ])
        add_summary(doc, summary)

        # ── 图表：测量值与标准值对比 ──
        configure_plotting()
        fig, ax = plt.subplots(figsize=(7.2, 4.6))
        labels = ["铁", "铝"]
        measured = [c_fe, c_al]
        standard = [c_std["铁"], c_std["铝"]]
        deltas = [delta_fe, delta_al]
        x = np.arange(len(labels))
        width = 0.32
        offset = 0.165
        # 分类色槽 1（蓝）= 测量值，槽 2（橙）= 标准值
        bars_measured = ax.bar(x - offset, measured, width, color="#2a78d6", label="测量值")
        bars_standard = ax.bar(x + offset, standard, width, color="#eb6834", label="标准值")
        for bars in (bars_measured, bars_standard):
            for rect in bars:
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_height(),
                    f"{rect.get_height():.4f}",
                    ha="center", va="bottom", fontsize=8.5, color="#0b0b0b",
                )
        ax.set_xticks(x)
        ax.set_xticklabels([f"{label}\nδ = {delta:.2f} %" for label, delta in zip(labels, deltas)])
        ax.set_xlabel("待测样品（100 ℃）")
        ax.set_ylabel("比热容 C / (cal/(g·℃))")
        ax.set_title("冷却法测定铁、铝的比热容")
        ax.set_ylim(0, max(max(measured), max(standard)) * 1.22)
        ax.grid(True, axis="y", linestyle="--", alpha=0.25)
        ax.legend(loc="upper right", fontsize=9)
        fig.tight_layout()
        chart = save_figure(fig, workpath, "exp7_cooling_specific_heat.png")

        return finish_report(
            doc, workpath, name(), summary,
            [{"filename": chart, "title": "铁、铝比热容测量值与标准值对比"}],
            warnings,
        )
    except Exception as exc:
        return error_result(exc)


# ─────────────────────────────────────────────
# 统一入口：按「实验内容」分派
# ─────────────────────────────────────────────
def handle_structured(workpath, payload):
    part = (payload.get("parameters") or {}).get("part", "mixing")
    if part == "cooling":
        return _handle_cooling(workpath, payload)
    return _handle_mixing(workpath, payload)


def _handle_mixing(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    enriched["parameters"] = preview_result["parameters"]

    _schema = schema()
    charts = []
    params = enriched.get("parameters", {})

    # ── 自定义 T-t 雷诺校正图 ──
    chart_path = _generate_Tt_chart(params, workpath)
    if chart_path:
        charts.append({
            "filename": "chart_Tt_reynolds.png",
            "title": "温度-时间曲线（雷诺校正）",
            "url": chart_path,
        })

    # ── 汇总 ──
    summary_lines = [
        "混合法测锌粒比热容 —— 雷诺校正结果：",
    ]

    # 拟合参数
    if params.get("_k1"):
        summary_lines.append(f"阶段一拟合：T = {params['_k1']}·t + {params['_b1']}")
    if params.get("_k2"):
        summary_lines.append(f"阶段三拟合：T = {params['_k2']}·t + {params['_b2']}")
    if params.get("_t_G"):
        summary_lines.append(f"特征时刻 t_G = {params['_t_G']} min")
    if params.get("_fallback_note"):
        summary_lines.append(f"⚠ {params['_fallback_note']}")

    # 修正温度
    if params.get("_T1"):
        summary_lines.append(f"修正初温 T1 = {params['_T1']} °C")
    if params.get("_T2"):
        summary_lines.append(f"修正末温 T2 = {params['_T2']} °C")
    if params.get("_dT"):
        summary_lines.append(f"温度变化 ΔT = T2 − T1 = {params['_dT']} °C")

    # 比热容
    if params.get("_cx"):
        summary_lines.extend([
            f"锌的比热容 cx = {params['_cx']} J/(kg·°C)",
            f"标准值 c₀ = {_C_X_STD:.0f} J/(kg·°C)，相对误差 δ = {params.get('_delta', '?')}%",
        ])

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        charts=charts,
    )
