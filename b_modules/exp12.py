"""示波器的使用实验模块
===================
一级大物电磁学实验 —— 数字示波器的原理与使用

页面采用公共实验模板（templates/experiment.html），本模块通过统一的
结构化数据接口提供输入、预览、AI 助教和报告数据，共四张表：

  表 1 示波器自备方波周期测量（三种方法 × 三种时基对比）
       → T_直接 = n(cm) × 时基 t_div(μs/cm) ÷ 1000 (ms)
       → 以“测量功能”为基准的相对偏差分析 + 结论
  表 2 信号发生器方波频率测量与线性拟合
       → f_meas = 1000 / T(ms)，f_meas-f_set 最小二乘线性拟合
  表 3 1000Hz 正弦信号峰峰值电压测量（双对数拟合）
       → log10(y) = k·log10(x) + b，即 y = 10^b · x^k
  表 4 李萨如图形测未知信号频率
       → f_x = f_y × n_y(垂直) / n_x(水平)

物理公式：
  T = n · t_div            （周期 = 波形厘米数 × 时基）
  f = 1000 / T(ms)         （频率）
  f_x / f_y = n_y / n_x    （李萨如图形频率比 = 切点数反比）
"""

import os

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data

# 三档时基（μs/cm）与模块三设定电压档（V）
TIMEBASES = [100.0, 250.0, 500.0]
VPP_SET = [0.002, 0.004, 0.016, 0.064, 0.256, 1.0, 4.0, 16.0]


def name():
    return "示波器的使用"


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
        docu.add_paragraph()
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 拟合工具（最小二乘，公式与前端页面一致）
#   k = (nΣxy − ΣxΣy) / (nΣx² − (Σx)²)
#   b = (Σy − kΣx) / n
#   R² = 1 − Σ(y−ŷ)² / Σ(y−ȳ)²
# ─────────────────────────────────────────────
def _linear_fit(xs, ys):
    """线性拟合，返回 (k, b, r2)；数据不足返回 None。"""
    n = len(xs)
    if n < 2:
        return None
    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    sx, sy = x_arr.sum(), y_arr.sum()
    denom = n * (x_arr ** 2).sum() - sx * sx
    if abs(denom) < 1e-15:
        return None
    k = (n * (x_arr * y_arr).sum() - sx * sy) / denom
    b = (sy - k * sx) / n
    y_pred = k * x_arr + b
    ss_res = ((y_arr - y_pred) ** 2).sum()
    ss_tot = ((y_arr - y_arr.mean()) ** 2).sum()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return k, b, r2


def _module1_notes(rows):
    """模块一分析：以“测量功能”读数为基准的相对偏差 + 结论。"""
    data = []  # (时基, T_直接, T_光标, T_测量)
    for row in rows:
        tb = as_number(row.get("c0"))
        if tb is None:
            continue
        data.append((tb, as_number(row.get("c2")),
                     as_number(row.get("c3")), as_number(row.get("c4"))))
    if not data:
        return []
    notes = ["以“测量功能”读数为基准的相对偏差 δ = (测量值 − 基准)/基准 × 100%："]
    dev_d, dev_c = [], []
    for tb, td, tc, ta in data:
        fd = (td - ta) / ta * 100 if (td is not None and ta) else None
        fc = (tc - ta) / ta * 100 if (tc is not None and ta) else None
        if fd is not None:
            dev_d.append(fd)
        if fc is not None:
            dev_c.append(fc)
        notes.append(
            f"  时基 {tb:.0f} μs/cm：直接读数 {fd if fd is None else round(fd, 2)}%，"
            f"光标测量 {fc if fc is None else round(fc, 2)}%")
    if dev_d or dev_c:
        mean_d = sum(abs(v) for v in dev_d) / len(dev_d) if dev_d else None
        mean_c = sum(abs(v) for v in dev_c) / len(dev_c) if dev_c else None
        notes.append("平均绝对偏差：直接读数 "
                     + (f"{mean_d:.2f}%" if mean_d is not None else "—")
                     + "，光标测量 " + (f"{mean_c:.2f}%" if mean_c is not None else "—"))
    notes.append("★ 结论：时基越小（波形越宽），直接读数法精度越高；"
                 "测量功能法精度最高且受时基影响最小。")
    return notes


def _module2_notes(rows):
    """模块二：f_meas-f_set 线性拟合（斜率≈1 验证频率测量线性度）。"""
    xs, ys = [], []
    for row in rows:
        fx = as_number(row.get("c0"))
        fm = as_number(row.get("c2"))
        if fx is not None and fm is not None:
            xs.append(fx)
            ys.append(fm)
    fit = _linear_fit(xs, ys)
    if fit is None:
        return ["填入至少 2 组（设定频率、测得频率）数据后自动进行线性拟合。"]
    k, b, r2 = fit
    return [
        f"最小二乘线性拟合（{len(xs)} 个有效点）：f_meas = {k:.4f} × f_set + {b:.3f}",
        f"斜率 k = {k:.5f}，截距 b = {b:.3f} Hz，相关系数 R² = {r2:.5f}",
        "理想情况 k ≈ 1、b ≈ 0。斜率偏离 1 反映示波器时基（晶振）的系统误差，"
        "截距不为 0 提示存在固定零点偏差。",
    ]


def _module3_notes(rows):
    """模块三：双对数拟合 log10(y) = k·log10(x) + b。"""
    xs, ys = [], []
    for row in rows:
        x = as_number(row.get("c0"))
        y = as_number(row.get("c1"))
        if x is not None and y is not None and x > 0 and y > 0:
            xs.append(x)
            ys.append(y)
    fit = _linear_fit(np.log10(xs), np.log10(ys)) if len(xs) >= 2 else None
    if fit is None:
        return ["填入至少 2 组正电压数据后自动进行双对数拟合（单位统一为 V）。"]
    k, b10, r2 = fit
    notes = [
        f"双对数拟合（{len(xs)} 个有效点）：log10(y) = {k:.4f}·log10(x) + {b10:.4f}",
        f"即 y = {10 ** b10:.4g} · x^{k:.4f}；斜率 k = {k:.4f}，R² = {r2:.5f}",
    ]
    # 小信号段（≤4mV）偏离检测
    small = [(x, y) for x, y in zip(xs, ys) if x <= 0.004]
    if small:
        devs = [(y - 10 ** b10 * x ** k) / (10 ** b10 * x ** k) * 100 for x, y in small]
        if min(abs(d) for d in devs) > 3:
            notes.append("⚠ 小信号段（2 mV / 4 mV）明显偏离拟合直线，"
                         "说明示波器小电压档位存在衰减或噪声影响。")
    notes.append("理想情况 k ≈ 1（测量值与设定值成正比）。")
    return notes


def _module4_notes(rows):
    """模块四：李萨如图形测未知频率，逐行给出计算式。"""
    notes = []
    for row in rows:
        fy = as_number(row.get("c0"))
        nx = as_number(row.get("c1"))
        ny = as_number(row.get("c2"))
        if fy is None or not nx or not ny:
            continue
        fx = fy * ny / nx
        notes.append(f"fy = {fy:g} Hz，水平切点 {nx:g}、垂直切点 {ny:g} → "
                     f"fx = {fy:g} × {ny:g}/{nx:g} = {fx:.4g} Hz")
    if not notes:
        notes = ["填入本地频率与两个方向的切点数后自动计算未知频率 "
                 "fx = fy × (Y轴垂直切点数) / (X轴水平切点数)。"]
    return notes


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    sample1 = load_sample_data("exp12", "示波器自备方波周期测量")
    sample2 = load_sample_data("exp12", "信号发生器频率校准")
    sample3 = load_sample_data("exp12", "示波器电压测量")
    sample4 = load_sample_data("exp12", "李萨如图形测频率")

    # 表 2 图表：f_meas vs f_set 线性拟合（斜率 ≈ 1）
    chart_cal = {
        "x_column": "c0", "y_column": "c2",
        "x_label": "f_set (Hz)",
        "y_label": "f_meas (Hz)",
        "title": "示波器频率校准曲线",
        "fit": "linear",
    }

    return make_schema(
        (
            "本实验学习数字示波器的使用：① 用直接读数、光标、自动测量三种方法在三种时基下"
            "测方波周期并对比精度；② 测量信号发生器各设定频率下的周期，验证 "
            r"$f_{meas}$" r"–$f_{set}$" " 线性拟合斜率接近 1；③ 测量信号峰峰值并做双对数拟合；"
            "④ 用李萨如图形测量正弦波频率。"
        ),
        [
            make_table(
                "table1", "模块一：示波器自备方波周期测量（三种方法对比）",
                [
                    "时基 t_div(μs/cm)",       # c0 时基设置（100/250/500）
                    "波形厘米数 n (cm)",  # c1 用户读数
                    "T_直接(ms)",        # c2 = n × 时基 ÷ 1000（只读）
                    "T_光标(ms)",        # c3 光标测量
                    "T_测量功能(ms)",     # c4 自动测量（偏差基准）
                ],
                sample=sample1,
                readonly=(0, 2),
                initial_rows=3,
                description="测量示波器自备校准方波的周期，比较直接读数、光标、"
                            "自动测量三种方法在三种时基下的精度。"
                            "T_直接 = n × 时基（μs ÷ 1000 转 ms），表格下方自动给出"
                            "以测量功能为基准的相对偏差与结论。",
            ),
            make_table(
                "table2", "模块二：信号发生器方波频率测量与线性拟合",
                [
                    "f_set(Hz)",       # c0 信号发生器设定频率
                    "T_测(ms)",        # c1 示波器测得周期
                    "f_meas(Hz)",      # c2 = 1000/T_测（只读）
                ],
                sample=sample2,
                readonly=(2,),
                initial_rows=10,
                chart=chart_cal,
                description="信号发生器输出对称方波，Vpp=1.0V，频率 200~2000 Hz"
                            "（间隔 200 Hz）。f_meas = 1000/T(ms)，"
                            "对 f_meas-f_set 做线性拟合验证斜率 ≈ 1。",
            ),
            make_table(
                "table3", "模块三：1000Hz 正弦信号峰峰值电压测量（双对数拟合）",
                [
                    "Vpp_设置(V)",     # c0 设定档位（2mV~16V，统一用 V）
                    "Vpp_测量(V)",     # c1 示波器测得值
                ],
                sample=sample3,
                readonly=(0,),
                initial_rows=8,
                description="信号发生器输出 1000 Hz 正弦波，改变输出档 Vpp"
                            "（2mV, 4mV, 16mV, 64mV, 256mV, 1V, 4V, 16V）。"
                            "单位统一为 V（2mV=0.002V）。"
                            "对双对数坐标做线性拟合：log10(y) = k·log10(x) + b，"
                            "理想 k ≈ 1，小信号段偏离说明档位衰减或噪声。",
            ),
            make_table(
                "table4", "模块四：李萨如图形测未知信号频率",
                [
                    "fy(Hz)",          # c0 本地信号源频率（已知）
                    "n_x(水平切点)",    # c1 X 轴水平切点数（对应 fy）
                    "n_y(垂直切点)",    # c2 Y 轴垂直切点数（对应 fx）
                    "fx(Hz)",          # c3 = fy × n_y / n_x（只读）
                ],
                sample=sample4,
                readonly=(3,),
                initial_rows=3,
                description="公用信号源（未知频率）接 CH1（X 轴），本地可调信号源接 "
                            "CH2（Y 轴）。fy/fx = 水平切点数/垂直切点数，"
                            "故 fx = fy × (Y轴垂直切点数) / (X轴水平切点数)。",
            ),
        ],
        analysis_hints="表1: 三种时基 × 三种方法测自备方波周期，自动比较精度；"
                       "表2: f_meas-f_set 线性拟合，斜率 ≈ 1；"
                       "表3: 双对数拟合验证电压测量线性度；"
                       "表4: 李萨如图形切点数比测未知频率。",
        preview_enabled=True,
        table_theory=get_table_theory("exp12"),
    )


def preview(payload):
    """实时计算：表 1 直接读数周期、表 2 频率换算、表 4 未知频率 + 各表拟合标注。"""
    tables = copied_tables(payload)
    fit_notes = {}

    # ── 表 1：T_直接 = n(cm) × 时基 t_div(μs/cm) ÷ 1000 → ms ──
    for row in tables.get("table1", []):
        tb = as_number(row.get("c0"))
        n = as_number(row.get("c1"))
        if tb is not None and n is not None:
            row["c2"] = formatted(tb * n / 1000, 4)
        else:
            row["c2"] = ""

    # ── 表 2：f_meas = 1000 / T(ms) ──
    for row in tables.get("table2", []):
        T_ms = as_number(row.get("c1"))
        if T_ms is not None and T_ms > 0:
            row["c2"] = formatted(1000.0 / T_ms, 2)
        else:
            row["c2"] = ""

    # ── 表 4：fx = fy × n_y / n_x ──
    for row in tables.get("table4", []):
        fy = as_number(row.get("c0"))
        nx = as_number(row.get("c1"))
        ny = as_number(row.get("c2"))
        if fy is not None and nx and ny:
            row["c3"] = formatted(fy * ny / nx, 4)
        else:
            row["c3"] = ""

    notes1 = _module1_notes(tables.get("table1", []))
    if notes1:
        fit_notes["table1"] = notes1
    fit_notes["table2"] = _module2_notes(tables.get("table2", []))
    fit_notes["table3"] = _module3_notes(tables.get("table3", []))
    fit_notes["table4"] = _module4_notes(tables.get("table4", []))

    return {"tables": tables, "fit_notes": fit_notes}


# ─────────────────────────────────────────────
# 自定义图表（matplotlib + 思源黑体，与 exp11 同风格）
# ─────────────────────────────────────────────
def _font(size=12):
    from matplotlib.font_manager import FontProperties
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "SourceHanSansSC-Regular.otf")
    return FontProperties(fname=path, size=size)


def _bar_chart(workpath, rows):
    """模块一：三种时基 × 三种方法的周期柱状对比图。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cats, direct, cursor, auto = [], [], [], []
    for row in rows:
        tb = as_number(row.get("c0"))
        if tb is None:
            continue
        cats.append(f"{tb:.0f} μs/cm")
        direct.append(as_number(row.get("c2")))
        cursor.append(as_number(row.get("c3")))
        auto.append(as_number(row.get("c4")))
    if not cats or not any(direct + cursor + auto):
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.arange(len(cats))
    series = [("直接读数", "#1a365d", direct),
              ("光标测量", "#dd6b20", cursor),
              ("测量功能", "#38a169", auto)]
    width = 0.8 / len(series)
    for i, (nm, color, vals) in enumerate(series):
        plot_vals = [v if v is not None else 0.0 for v in vals]
        offset = (i - 1) * width
        ax.bar(xs + offset, plot_vals, width, label=nm, color=color)
        for xi, v in zip(xs, plot_vals):
            if v:
                ax.text(xi + offset, v, f"{v:.3f}", ha="center", va="bottom",
                        fontproperties=_font(8))
    ax.set_xticks(xs)
    ax.set_xticklabels(cats, fontproperties=_font(11))
    for lb in ax.get_yticklabels():
        lb.set_fontproperties(_font(10))
    ax.set_xlabel("时基", fontproperties=_font(12))
    ax.set_ylabel("周期 T (ms)", fontproperties=_font(12))
    ax.set_title("三种时基下不同方法测得的周期对比", fontproperties=_font(14))
    ax.legend(prop=_font(10))
    ax.grid(axis="y", ls="--", alpha=0.4)
    fig.tight_layout()
    filename = "chart_period_comparison.png"
    fig.savefig(os.path.join(workpath, filename), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return {"filename": filename, "title": "三种方法周期对比柱状图"}


def _loglog_chart(workpath, rows):
    """模块三：Vpp 双对数散点 + 幂函数拟合线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs, ys = [], []
    for row in rows:
        x = as_number(row.get("c0"))
        y = as_number(row.get("c1"))
        if x is not None and y is not None and x > 0 and y > 0:
            xs.append(x)
            ys.append(y)
    if len(xs) < 2:
        return None
    fit = _linear_fit(np.log10(xs), np.log10(ys))
    k, b10, r2 = fit

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.scatter(xs, ys, color="#1a365d", s=50, zorder=5,
               edgecolors="white", linewidth=0.5, label="测量数据")
    xl = np.logspace(np.log10(min(xs)) - 0.15, np.log10(max(xs)) + 0.15, 100)
    yl = 10 ** b10 * xl ** k
    ax.plot(xl, yl, color="#dd6b20", linewidth=2,
            label=f"幂函数拟合: y = {10 ** b10:.3g}·x^{k:.3f}, R² = {r2:.4f}")
    for lb in ax.get_xticklabels() + ax.get_yticklabels():
        lb.set_fontproperties(_font(9))
    ax.set_xlabel("信号发生器 Vpp (V，对数刻度)", fontproperties=_font(12))
    ax.set_ylabel("示波器测得 Vpp (V，对数刻度)", fontproperties=_font(12))
    ax.set_title("示波器 Vpp 测量双对数曲线", fontproperties=_font(14))
    ax.legend(prop=_font(10))
    ax.grid(True, which="both", ls="--", alpha=0.35)
    fig.tight_layout()
    filename = "chart_vpp_loglog.png"
    fig.savefig(os.path.join(workpath, filename), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return {
        "filename": filename,
        "title": "Vpp 测量双对数曲线",
        "fit_result": {
            "type": "power", "label": "幂函数（双对数线性）",
            "equation": f"y = {10 ** b10:.4g}·x^{k:.4f}",
            "R2": round(float(r2), 6),
            "params": {"k": round(float(k), 6), "log10_b": round(float(b10), 6)},
        },
    }


def handle_structured(workpath, payload):
    enriched = dict(payload)
    prev = preview(payload)
    enriched["tables"] = prev["tables"]
    fit_notes = prev.get("fit_notes", {})

    _schema = schema()
    charts = []

    # 图 1：三种方法周期对比柱状图（模块一）
    bar = _bar_chart(workpath, enriched["tables"].get("table1", []))
    if bar:
        charts.append(bar)

    # 图 2：频率校准线性拟合（模块二）
    t2_schema = _schema["tables"][1]
    t2_rows = enriched["tables"].get("table2", [])
    c_cal_config = t2_schema.get("chart")
    if c_cal_config and t2_rows:
        charts.append(make_chart_from_table(
            t2_schema, t2_rows, c_cal_config,
            workpath, chart_filename="chart_freq_calibration.png",
        ))

    # 图 3：Vpp 双对数曲线（模块三）
    loglog = _loglog_chart(workpath, enriched["tables"].get("table3", []))
    if loglog:
        charts.append(loglog)

    # 汇总：卡片式【模块一】~【模块四】
    summary_lines = ["数字示波器的原理与使用 — 数据处理结果：",
                     "【模块一】自备方波周期测量（三种方法 × 三种时基）"]
    summary_lines += [f"  {ln}" for ln in fit_notes.get("table1", [])]
    summary_lines.append("【模块二】信号发生器频率线性拟合")
    summary_lines += [f"  {ln}" for ln in fit_notes.get("table2", [])]
    summary_lines.append("【模块三】Vpp 双对数拟合")
    summary_lines += [f"  {ln}" for ln in fit_notes.get("table3", [])]
    summary_lines.append("【模块四】李萨如图形测未知频率")
    summary_lines += [f"  {ln}" for ln in fit_notes.get("table4", [])]

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        charts=charts,
    )
