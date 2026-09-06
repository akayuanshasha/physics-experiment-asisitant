"""声速测量实验模块
==================
一级大物波动学实验 —— 同一份《声速测量B（实验指导）》按顺序排布两个表格：

表1：驻波法（共振干涉法）测空气中声速
  移动接收换能器 S2，逐个记下示波器上出现振幅最大（波腹）时的位置读数 L_i，
  共 12 个位置点。用最小二乘法对 n-L 数据线性拟合，斜率 m 的绝对值乘以 2
  得波长 λ = 2|m|，由 v = f·λ 计算声速，与理论值 v_t = 331.45√(1+t/273.15)
  比较求相对误差。

表2：相位比较法测水中声速（提升实验，方法与空气类似）
  置示波器于 X-Y 方式，移动 S2，依次测出李萨如图形斜率正、负变化的直线
  出现时 S2 的位置 L_j，共 8 个位置值。相邻直线位置间距为 λ/2，
  对 j-L 线性拟合，λ = 2|斜率|，v = f·λ。

报告、示例数据与图表同时包含空气与水两个部分。
"""

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data

# 20 ℃ 纯水中声速标准值（用于相位比较法的理论值比较）
_V_WATER_STD = 1480.0


def name():
    return "声速测量"


def handle(workpath, extension):
    """旧版 CSV 接口：保留原始逻辑。"""
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf")
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, names=["L", "f", "t"], encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0, names=["L", "f", "t"])
        os.remove(excelpath)

        data["n"] = range(1, data["L"].size + 1)
        res_lsm = analyse_lsm(data["n"], data["L"], "n", "L", "cm", "cm")
        res_f = analyse(data["f"], 0.001, 0, "f", "Hz")

        fig, ax = plt.subplots()
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.plot(data["n"], data["L"], "o", color='r', markersize=3)
        ax.plot(data["n"], res_lsm.b + res_lsm.m * data["n"], color='b', linewidth=1.5)
        ax.set_title("共振干涉法测空气中声速的最小二乘法拟合图", fontproperties=zhfont)
        ax.set_xlabel("n")
        ax.set_ylabel("The nth Position (cm)")
        imgpath = workpath + "img.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu = Document()
        style_doc_font(docu)
        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        os.remove(imgpath)
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 示例数据
# ─────────────────────────────────────────────
def _standing_sample():
    """驻波法示例：CSV 列为 L/cm、f/Hz、t/℃，转为序号 n 与位置 L(mm)。"""
    raw = load_sample_data("exp9", "共振干涉法（驻波法）测空气中声速")
    rows = []
    for index, row in enumerate(raw):
        if len(row) < 1 or not row[0]:
            continue
        try:
            l_cm = float(row[0])
        except (TypeError, ValueError):
            continue
        rows.append([str(index), f"{l_cm * 10:.2f}"])
    return rows


def _phase_sample():
    """相位比较法示例：CSV 列为 L/cm、f/Hz，转为序号 j 与位置 L(cm)。"""
    raw = load_sample_data("exp9", "相位比较法测水中声速")
    rows = []
    for index, row in enumerate(raw):
        if len(row) < 1 or not row[0]:
            continue
        try:
            float(row[0])
        except (TypeError, ValueError):
            continue
        rows.append([str(index), row[0]])
    return rows


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    # 空气图表：n - L 线性拟合 → 斜率 m，λ = 2|m|
    chart_standing = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "波节序号 n",
        "y_label": "共振位置 L (mm)",
        "title": "n - L 线性拟合求空气中波长",
        "fit": "linear",
    }

    # 水中图表：j - L 线性拟合 → 斜率 b1，λ = 2|b1|
    chart_phase = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "序号 j",
        "y_label": "位置 L (cm)",
        "title": "j - L 线性拟合求水中波长",
        "fit": "linear",
    }

    standing_table = make_table(
        "table1", "表1  共振干涉法位置数据（驻波法，空气）",
        [
            "波节序号 n",      # c0
            "位置 L(mm)",      # c1
        ],
        sample=_standing_sample(),
        readonly=(),
        initial_rows=12,
        chart=chart_standing,
        description="调节信号发生器频率，当示波器上接收到的电压幅度最大时，读取频率值 f。"
                    "移动接收换能器 S2，逐个记下示波器上出现振幅最大（波腹）时的位置读数。"
                    "共需记录 12 个位置点（L_0, L_1, ..., L_11）。"
                    "用最小二乘法对 n-L 数据进行线性拟合，斜率 m 的绝对值乘以 2 得波长 λ = 2|m|。"
                    "点击本表下方的「提交计算」即可计算波长、声速及与理论值 "
                    "v_t = 331.45√(1+t/273.15) 的误差。",
    )
    phase_table = make_table(
        "phase_position", "表2  相位比较法位置数据（水中）",
        [
            "序号 j",          # c0
            "位置 L(cm)",      # c1
        ],
        sample=_phase_sample(),
        readonly=(),
        initial_rows=8,
        chart=chart_phase,
        description="提升实验：方法与空气中类似。置示波器于 X-Y 方式，移动 S2，依次测出"
                    "李萨如图形斜率正、负变化的直线出现时 S2 的位置 L_j，共记录 8 个位置值。"
                    "相邻直线位置间距为 λ/2，对 j-L 线性拟合，波长 λ = 2|斜率|，v = f·λ。"
                    "点击本表下方的「提交计算」即可计算水中波长、声速及与理论值 "
                    f"v_t = {_V_WATER_STD:g} m/s（20 ℃ 纯水中声速标准值）的误差。",
    )
    # 水中谐振频率输入框放在水中表格的上方
    phase_table["parameters"] = [
        {"id": "freq_water", "label": "谐振频率 f (Hz)（水中）", "default": ""},
    ]

    # 每个表格下方独立的「提交计算」按钮（计算波长、声速及与理论值的误差）
    standing_table["calc"] = {"label": "提交计算"}
    phase_table["calc"] = {"label": "提交计算"}

    parameters = [
        {"id": "freq", "label": "谐振频率 f (Hz)（空气）", "default": ""},
        {"id": "temp", "label": "室温 t (°C)（空气）", "default": ""},
    ]

    return make_schema(
        (
            "本实验用驻波法与相位比较法测量空气中的声速。请记录各波节（驻波法）与各相位点"
            "（比较法）的位置，由 " r"$\lambda = 2|\text{斜率}|$" " 求波长，按 "
            r"$v = f\lambda$" " 计算声速，并与理论值 " r"$v_t = 331.45\sqrt{1+t/273.15}$" " 比较。"
        ),
        [standing_table, phase_table],
        parameters=parameters,
        analysis_hints="表1（驻波法，空气）：填入谐振频率 f 和室温 t，记录 12 个共振位置，"
                       "n-L 线性拟合求 λ = 2|m|，v = f·λ，与理论值比较。"
                       "表2（相位比较法，水）：方法与空气类似，记录 8 个李萨如图形直线位置，"
                       "j-L 线性拟合求 λ = 2|斜率|，v = f·λ。",
        preview_enabled=True,
        table_theory=get_table_theory("exp9"),
        parameters_sample={
            # 驻波法（空气）
            "freq": "37180", "temp": "26",
            # 相位比较法（水）
            "freq_water": "36770",
        },
    )


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


def preview(payload):
    """同时预计算空气（驻波法）与水（相位比较法）的波长和声速。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})

    # ── 表1：驻波法（空气）──
    freq = as_number(params.get("freq"))
    temp = as_number(params.get("temp"))
    lam = None
    v_meas = None
    v_t = None
    delta = None

    ns, Ls = [], []
    for row in tables.get("table1", []):
        n_val = as_number(row.get("c0"))
        L_val = as_number(row.get("c1"))
        if n_val is not None and L_val is not None:
            ns.append(n_val)
            Ls.append(L_val)
    if len(ns) >= 2:
        m, _ = _linear_fit(ns, Ls)
        if m is not None:
            lam = 2 * abs(m)  # 波长 mm
            if freq is not None and freq > 0:
                v_meas = freq * lam * 1e-3  # 声速 m/s
                if temp is not None:
                    v_t = 331.45 * (1 + temp / 273.15) ** 0.5
                    delta = abs(v_meas - v_t) / v_t * 100

    # ── 表2：相位比较法（水）──
    freq_water = as_number(params.get("freq_water"))
    lam_water = None
    v_water = None

    js, Lws = [], []
    for row in tables.get("phase_position", []):
        j_val = as_number(row.get("c0"))
        L_val = as_number(row.get("c1"))
        if j_val is not None and L_val is not None:
            js.append(j_val)
            Lws.append(L_val)
    if len(js) >= 2:
        k, _ = _linear_fit(js, Lws)
        if k is not None:
            lam_water = 2 * abs(k)  # 波长 cm
            if freq_water is not None and freq_water > 0:
                v_water = freq_water * lam_water * 1e-2  # 声速 m/s

    delta_water = None
    if v_water is not None:
        delta_water = abs(v_water - _V_WATER_STD) / _V_WATER_STD * 100

    enriched_params = dict(params)
    enriched_params.update({
        "_lam": formatted(lam, 4),
        "_v_meas": formatted(v_meas, 2),
        "_v_t": formatted(v_t, 2),
        "_delta": formatted(delta, 2),
        "_lam_water": formatted(lam_water, 4),
        "_v_water": formatted(v_water, 2),
        "_delta_water": formatted(delta_water, 2),
    })

    # ── 各表独立的「提交计算」结果（纯文本，供表格下方按钮显示）──
    calc_air_lines = []
    if lam is not None:
        calc_air_lines.append(f"波长 λ = {lam:.4f} mm")
    if v_meas is not None:
        calc_air_lines.append(f"声速测量值 v = {v_meas:.2f} m/s")
    if v_t is not None:
        calc_air_lines.append(f"理论值 v_t = {v_t:.2f} m/s")
    if delta is not None:
        calc_air_lines.append(f"相对误差 δ = {delta:.2f}%")
    if not calc_air_lines:
        calc_air_lines.append("请先在表1填写位置数据（可点「填入本表全部示例数据」）。")
    elif v_meas is None:
        calc_air_lines.append("提示：填写谐振频率 f 后可计算声速及误差。")
    elif delta is None:
        calc_air_lines.append("提示：填写室温 t 后可计算与理论值的误差。")

    calc_water_lines = []
    if lam_water is not None:
        calc_water_lines.append(f"水中波长 λ = {lam_water:.4f} cm")
    if v_water is not None:
        calc_water_lines.append(f"水中声速 v = {v_water:.2f} m/s")
        calc_water_lines.append(
            f"理论值 v_t = {_V_WATER_STD:g} m/s（20 ℃ 纯水），相对误差 δ = {delta_water:.2f}%")
    if not calc_water_lines:
        calc_water_lines.append("请先在表2填写位置数据（可点「填入本表全部示例数据」）。")
    elif v_water is None:
        calc_water_lines.append("提示：填写谐振频率 f 后可计算水中声速及误差。")

    return {
        "tables": tables,
        "parameters": enriched_params,
        "calc_results": {
            "table1": {"lines": calc_air_lines},
            "phase_position": {"lines": calc_water_lines},
        },
    }


def handle_structured(workpath, payload):
    try:
        enriched = dict(payload)
        preview_result = preview(payload)
        enriched["tables"] = preview_result["tables"]
        enriched["parameters"] = preview_result["parameters"]

        _schema = schema()
        params = enriched.get("parameters", {})
        charts = []
        summary_lines = []
        warnings = []

        # ── 表1：驻波法（空气）──
        if enriched["tables"].get("table1"):
            t1_schema = next(table for table in _schema["tables"] if table["id"] == "table1")
            chart_config = t1_schema.get("chart")
            if chart_config:
                charts.append(make_chart_from_table(
                    t1_schema, enriched["tables"]["table1"], chart_config,
                    workpath, chart_filename="chart_n_vs_L.png",
                ))
            summary_lines.append("── 驻波法（共振干涉法）测空气中声速 ──")
            if params.get("freq"):
                summary_lines.append(f"谐振频率 f = {params['freq']} Hz")
            if params.get("temp"):
                summary_lines.append(f"室温 t = {params['temp']} °C")
            if params.get("_lam"):
                summary_lines.append(f"波长 λ = {params['_lam']} mm")
            if params.get("_v_meas"):
                summary_lines.append(f"声速测量值 v = {params['_v_meas']} m/s")
            if params.get("_v_t"):
                summary_lines.append(f"声速理论值 v_t = {params['_v_t']} m/s")
            if params.get("_delta"):
                summary_lines.append(f"相对误差 δ = {params['_delta']}%")
            if not params.get("_v_meas"):
                warnings.append("空气部分未完成计算：请检查频率、室温与位置数据是否完整。")
        else:
            warnings.append("表1（驻波法，空气）未填写数据。")

        # ── 表2：相位比较法（水）──
        if enriched["tables"].get("phase_position"):
            t2_schema = next(table for table in _schema["tables"] if table["id"] == "phase_position")
            chart_config = t2_schema.get("chart")
            if chart_config:
                charts.append(make_chart_from_table(
                    t2_schema, enriched["tables"]["phase_position"], chart_config,
                    workpath, chart_filename="chart_phase.png",
                ))
            summary_lines.append("── 相位比较法测水中声速 ──")
            if params.get("freq_water"):
                summary_lines.append(f"谐振频率 f = {params['freq_water']} Hz")
            if params.get("_lam_water"):
                summary_lines.append(f"水中波长 λ = {params['_lam_water']} cm")
            if params.get("_v_water"):
                summary_lines.append(f"水中声速 v = {params['_v_water']} m/s")
            if params.get("_delta_water"):
                summary_lines.append(
                    f"理论值 v_t = {_V_WATER_STD:g} m/s（20 ℃ 纯水），相对误差 δ = {params['_delta_water']}%")
            if not params.get("_v_water"):
                warnings.append("水中部分未完成计算：请检查频率与位置数据是否完整。")
        else:
            warnings.append("表2（相位比较法，水中）未填写数据。")

        if not summary_lines:
            summary_lines.append("尚未填写任何数据。")

        return structured_result(
            workpath, name(), _schema, enriched,
            summary=summary_lines,
            warnings=warnings,
            charts=charts,
        )
    except Exception as exc:
        return {"code": 1, "message": f"处理出错：{exc}"}
