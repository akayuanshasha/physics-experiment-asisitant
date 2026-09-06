"""F-H（弗兰克-赫兹）实验数据处理模块。

网页流程（新版结构化接口）：
1. schema() 声明输入表格（U_G2K / I_p，带单位）与实验参数；
2. preview() 在学生输入时实时识别电流峰、计算第一激发电位；
3. handle_structured() 生成激发曲线（峰位标注）与峰位-序数拟合两张图，
   并输出包含峰位、间隔、ΔŪ、激发能的摘要。

旧版 CSV 流程 handle() 保留，供旧接口与 AI 助教调用。
"""

from head import *  # 导入万能头
from structured_support import copied_tables, make_schema, make_table, structured_result
from theory_content import get_table_theory
from sample_data_loader import load_sample_data_numeric

# ── 物理常数与识别判据 ──
_E_REFERENCE_V = 11.55          # 氩原子第一激发电位标准值（常引用 11.5~11.6 V）
_MIN_PEAK_SEPARATION_V = 8.0    # 最小峰间距：第一激发电位约 11.6 V，8 V 可排除噪声波纹
_PEAK_WINDOW_V = 4.0            # 峰突出度计算的单侧窗口
_MIN_PEAK_PROMINENCE_RATIO = 0.15  # 峰相对全局幅度的最小突出度


def name():
    return "F-H实验"


def _detect_peaks(u_values, i_values):
    """在非均匀采样点上检测电流峰并精化峰位。

    判据（按序）：
    1. 局部极大值（平台峰取最左点）；
    2. 突出度（相对两侧 ±4 V 窗口内谷底的高度差）不低于全局幅度的 15%；
    3. 按峰高贪心保留，保证峰间距 ≥ 8 V；
    4. 抛物线插值精化峰位（不越过相邻采样点）。

    返回 (peak_u, peak_i) 两个列表，按 U 升序。
    """
    u = np.asarray(u_values, dtype=float)
    i = np.asarray(i_values, dtype=float)
    if len(u) < 3:
        return [], []
    order = np.argsort(u)
    u, i = u[order], i[order]

    # 1. 局部极大值
    candidates = [k for k in range(1, len(i) - 1)
                  if i[k] > i[k - 1] and i[k] >= i[k + 1]]
    if not candidates:
        return [], []

    amplitude = float(i.max() - i.min())
    if amplitude <= 0:
        return [], []
    prominence_threshold = _MIN_PEAK_PROMINENCE_RATIO * amplitude

    # 2. 突出度筛选。
    #    数据边界附近的峰（如起点 10 V 处的第一个峰）只有一侧谷底在测量范围内，
    #    此时只要求可见一侧有足够突出度，避免边界峰被整体幅度判据误杀。
    peaked = []
    for k in candidates:
        left_mask = (u >= u[k] - _PEAK_WINDOW_V) & (u <= u[k])
        right_mask = (u >= u[k]) & (u <= u[k] + _PEAK_WINDOW_V)
        left_valley = float(i[left_mask].min()) if left_mask.any() else None
        right_valley = float(i[right_mask].min()) if right_mask.any() else None
        if left_valley is None and right_valley is None:
            continue
        left_cut = u[k] - _PEAK_WINDOW_V < u[0]
        right_cut = u[k] + _PEAK_WINDOW_V > u[-1]
        if left_cut and not right_cut and right_valley is not None:
            prominence = float(i[k]) - right_valley
        elif right_cut and not left_cut and left_valley is not None:
            prominence = float(i[k]) - left_valley
        else:
            prominence = float(i[k]) - max(
                left_valley if left_valley is not None else float(i[k]),
                right_valley if right_valley is not None else float(i[k]))
        if prominence >= prominence_threshold:
            peaked.append((k, float(i[k]), prominence))

    # 3. 按峰高贪心保留，保证最小间距
    peaked.sort(key=lambda item: -item[1])
    kept = []
    for k, height, prominence in peaked:
        if all(abs(u[k] - u[j]) >= _MIN_PEAK_SEPARATION_V for j, _, _ in kept):
            kept.append((k, height, prominence))
    kept.sort(key=lambda item: u[item[0]])

    # 4. 抛物线精化峰位与峰高
    peak_u, peak_i = [], []
    for k, height, _ in kept:
        if 0 < k < len(i) - 1:
            poly = np.polyfit(u[k - 1:k + 2], i[k - 1:k + 2], 2)
            if poly[0] != 0:
                refined = -poly[1] / (2 * poly[0])
                refined = min(max(refined, u[k - 1]), u[k + 1])
                peak_u.append(float(refined))
                peak_i.append(float(np.polyval(poly, refined)))
                continue
        peak_u.append(float(u[k]))
        peak_i.append(height)
    return peak_u, peak_i


def _analyze(u_values, i_values):
    """识别峰位并计算第一激发电位，返回结构化计算结果。"""
    peak_u, peak_i = _detect_peaks(u_values, i_values)
    if len(peak_u) < 2:
        raise ValueError(
            "仅检出 {} 个电流峰（至少需要 2 个）。"
            "请检查数据是否覆盖 10~95 V、峰谷变化是否明显。".format(len(peak_u))
        )

    u_arr = np.asarray(u_values, dtype=float)
    i_arr = np.asarray(i_values, dtype=float)
    order = np.argsort(u_arr)
    u_sorted = u_arr[order].tolist()
    i_sorted = i_arr[order].tolist()

    intervals = [round(b - a, 4) for a, b in zip(peak_u[:-1], peak_u[1:])]
    mean_du = float(np.mean(intervals))
    std_du = float(np.std(intervals, ddof=1)) if len(intervals) > 1 else 0.0

    # 峰位-序数最小二乘拟合（教科书相差曲线法）：U_n = b + k·n，斜率 k = 第一激发电位
    n_arr = np.arange(1, len(peak_u) + 1, dtype=float)
    peak_u_arr = np.asarray(peak_u)
    A = np.vstack([n_arr, np.ones_like(n_arr)]).T
    k, b = np.linalg.lstsq(A, peak_u_arr, rcond=None)[0]
    residual = peak_u_arr - (k * n_arr + b)
    if len(peak_u) > 2:
        ss_tot = np.sum((peak_u_arr - peak_u_arr.mean()) ** 2)
        r2 = float(1 - np.sum(residual ** 2) / ss_tot) if ss_tot > 0 else 0.0
        s_res = np.sqrt(np.sum(residual ** 2) / (len(peak_u) - 2))
        denom = np.sqrt(np.sum((n_arr - n_arr.mean()) ** 2))
        k_unc = float(s_res / denom) if denom > 0 else 0.0
    else:
        r2, k_unc = 0.0, 0.0

    # 激发能（eV 数值上等于激发电位 V）与相对误差
    e_ev = float(k)
    rel_err = abs(e_ev - _E_REFERENCE_V) / _E_REFERENCE_V * 100
    lambda_nm = 1240.0 / e_ev if e_ev > 0 else None

    lines = [
        "检出 {} 个电流峰，峰位：{} V".format(
            len(peak_u), "、".join("{:.2f}".format(value) for value in peak_u)),
        "相邻峰位间隔 ΔU：{} V".format(
            "、".join("{:.3f}".format(value) for value in intervals)),
        "第一激发电位（间隔平均）ΔŪ = {:.3f} V，标准偏差 s = {:.3f} V".format(mean_du, std_du),
        "峰位-序数最小二乘拟合：U_n = {:.3f} + ({:.3f})n，R² = {:.5f}，斜率不确定度 u(k) = {:.4f} V".format(b, k, r2, k_unc),
        "第一激发能 E = e·ΔŪ = {:.3f} eV（标准值 {:.2f} V，相对误差 {:.2f}%）".format(e_ev, _E_REFERENCE_V, rel_err),
    ]
    if lambda_nm is not None:
        lines.append("退激辐射波长 λ = hc/E ≈ {:.1f} nm".format(lambda_nm))

    return {
        "lines": lines,
        "peak_u": peak_u,
        "peak_i": peak_i,
        "intervals": intervals,
        "mean_du": mean_du,
        "std_du": std_du,
        "fit": {"slope": float(k), "intercept": float(b), "r2": r2, "slope_unc": k_unc},
        "excitation_ev": e_ev,
        "relative_error_pct": rel_err,
        "u": u_sorted,
        "i": i_sorted,
    }


def _has_value(value):
    return value is not None and str(value).strip() != ""


def preview(payload):
    """网页输入时的实时预计算：识别峰位并计算第一激发电位。"""
    tables = copied_tables(payload)
    calc_results = {}
    calc_messages = []
    fit_notes = {}

    rows = tables.get("table1", []) or []
    u_values, i_values = [], []
    bad_rows = []
    for index, row in enumerate(rows, start=1):
        raw_u = row.get("c0")
        raw_i = row.get("c1")
        if not _has_value(raw_u) and not _has_value(raw_i):
            continue
        if not _has_value(raw_u) or not _has_value(raw_i):
            bad_rows.append(index)
            continue
        try:
            u_values.append(float(raw_u))
            i_values.append(float(raw_i))
        except (TypeError, ValueError):
            bad_rows.append(index)

    if bad_rows:
        calc_messages.append(
            "第 {} 行数据不完整或不是数字，已跳过。".format("、".join(map(str, bad_rows)))
        )

    if len(u_values) >= 6:
        try:
            info = _analyze(u_values, i_values)
            calc_results["table1"] = info
            fit_notes["table1"] = [
                "峰位识别：最小峰间距 {} V、突出度阈值 {}%×幅度、抛物线精化。".format(
                    _MIN_PEAK_SEPARATION_V, int(_MIN_PEAK_PROMINENCE_RATIO * 100)),
                "当前检出 {} 个峰，数据覆盖 {:.1f}~{:.1f} V（指导书要求 10~95 V、6 个完整峰谷）。".format(
                    len(info["peak_u"]), min(u_values), max(u_values)),
            ]
        except ValueError as exc:
            calc_messages.append(str(exc))

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_excitation_chart(workpath, info):
    """激发曲线：测量点折线 + 峰位标注 + 相邻间隔标注。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.plot(info["u"], info["i"], "-", color="#2f7fc1", linewidth=1.2, alpha=0.9, zorder=3)
    axis.scatter(info["u"], info["i"], s=14, color="#2f7fc1", zorder=4, label="测量数据")

    for index, (u_peak, i_peak) in enumerate(zip(info["peak_u"], info["peak_i"]), start=1):
        axis.plot([u_peak], [i_peak], marker="v", color="#d94b40", markersize=9, zorder=5)
        axis.annotate("U{} = {:.1f} V".format(index, u_peak), (u_peak, i_peak),
                      textcoords="offset points", xytext=(0, 12), ha="center",
                      fontsize=9, color="#d94b40", fontproperties=font)

    # 相邻峰间隔标注（放在曲线顶部，错开高度避免重叠）
    amplitude = max(info["i"]) - min(info["i"])
    for index, (a, b) in enumerate(zip(info["peak_u"][:-1], info["peak_u"][1:])):
        mid = (a + b) / 2
        height = max(info["i"]) + amplitude * (0.12 + 0.10 * (index % 2))
        axis.annotate("ΔU = {:.2f} V".format(b - a), (mid, height), ha="center",
                      fontsize=9, color="#3a9d5d", fontproperties=font,
                      bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8))

    axis.set_ylim(min(info["i"]) - amplitude * 0.05, max(info["i"]) + amplitude * 0.45)
    axis.set_xlabel("第二栅极电压 U_G2K (V)", fontproperties=font)
    axis.set_ylabel("板极电流 I_p (nA)", fontproperties=font)
    axis.set_title("氩原子 F-H 激发曲线（峰位标注）", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    path = os.path.join(workpath, "f-h_excitation_curve.png")
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "f-h_excitation_curve.png", "title": "氩原子 F-H 激发曲线",
            "x_label": "第二栅极电压 U_G2K (V)", "y_label": "板极电流 I_p (nA)"}


def _make_peak_fit_chart(workpath, info):
    """峰位-序数最小二乘拟合图：斜率即第一激发电位（教科书相差曲线法）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    peak_u = info["peak_u"]
    n_arr = np.arange(1, len(peak_u) + 1, dtype=float)
    k = info["fit"]["slope"]
    b = info["fit"]["intercept"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(n_arr, peak_u, s=30, color="#2f7fc1", zorder=4, label="峰位 U_n")
    axis.plot(n_arr, k * n_arr + b, "-", color="#d94b40", linewidth=1.5, zorder=3,
              label="最小二乘拟合直线")
    axis.annotate(
        "U_n = {:.3f} + ({:.3f})n\n第一激发电位 ΔU = k = {:.3f} V\nR² = {:.5f}".format(
            b, k, k, info["fit"]["r2"]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9),
    )
    axis.set_xlabel("峰序 n", fontproperties=font)
    axis.set_ylabel("峰位电压 U_n (V)", fontproperties=font)
    axis.set_title("峰位-序数最小二乘拟合（第一激发电位）", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    path = os.path.join(workpath, "f-h_peak_fit.png")
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "f-h_peak_fit.png", "title": "峰位-序数最小二乘拟合",
            "x_label": "峰序 n", "y_label": "峰位电压 U_n (V)"}


def _optional_number(value, label):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("{}必须填写数字".format(label))


def handle_structured(workpath, payload):
    """新版结构化接口：计算峰位与第一激发电位，输出摘要与两张图。"""
    parameters = payload.get("parameters") or {}
    try:
        for key, label in (("uf", "灯丝电压 U_F"),
                           ("ug1k", "第一栅极电压 U_G1K"),
                           ("ug2p", "拒斥电压 U_G2P")):
            _optional_number(parameters.get(key), label)
    except ValueError as exc:
        return {"code": 1, "message": str(exc)}

    result = preview(payload)
    info = result["calc_results"].get("table1")
    if info is None:
        return {"code": 1, "message": "；".join(result["calc_messages"]) or "请先填写 U_G2K 和 I_p 数据。"}

    os.makedirs(workpath, exist_ok=True)
    charts = [
        _make_excitation_chart(workpath, info),
        _make_peak_fit_chart(workpath, info),
    ]
    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=info["lines"],
        charts=charts,
    )


def _set_units(table, units):
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    sample = load_sample_data_numeric("exp39", "exp39_example")
    table = _set_units(
        make_table(
            "table1",
            "氩原子 F-H 实验伏安特性数据表",
            ["第二栅极电压 U_G2K", "板极电流 I_p"],
            sample=sample,
            initial_rows=len(sample),
            description=(
                "在 10.0~95.0 V 范围内改变加速电压 U_G2K（峰、谷附近以 0.5 V 为步长加密），"
                "记录微电流仪显示的板极电流 I_p，测量 6 个完整的峰、谷。"
                "后端自动识别电流峰并计算第一激发电位。"
            ),
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "第二栅极电压 U_G2K (V)", "y_label": "板极电流 I_p (nA)",
                "title": "氩原子 F-H 激发曲线",
                "fit": None, "connect_points": True,
            },
        ),
        ("V", "nA"),
    )
    table["calc"] = {"label": "计算第一激发电位"}
    return make_schema(
        (
            "F-H 实验（氩管）：测定氩原子第一激发电位，验证原子能级量子化。"
            "请记录 " r"$U_{G2K}$" r"–$I_p$" " 伏安特性曲线，由相邻峰位间隔"
            "（约 11.5~11.6 V）计算第一激发电位，并由 " r"$E = e\Delta U$" "、"
            r"$\lambda = hc/E$" " 估算对应波长。"
        ),
        [table],
        parameters=[
            {"id": "uf", "label": "灯丝电压 U_F", "unit": "V", "type": "number",
             "step": "any", "required": False},
            {"id": "ug1k", "label": "第一栅极电压 U_G1K", "unit": "V", "type": "number",
             "step": "any", "required": False},
            {"id": "ug2p", "label": "拒斥电压 U_G2P", "unit": "V", "type": "number",
             "step": "any", "required": False},
        ],
        analysis_hints=(
            "重点检查：峰位识别是否合理（相邻峰间隔应接近 11.5~11.6 V，"
            "若检出间隔明显偏小说明噪声波纹被误判为峰）；"
            "第一激发电位与标准值的相对误差；峰位-序数拟合的 R²。"
        ),
        preview_enabled=True,
        table_theory=get_table_theory("exp39"),
    )


def handle(workpath, extension):
    """旧版 CSV 流程：生成 Word 文档。网页结构化流程已改走 handle_structured。"""
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
        u_col = [c for c in cols if 'U' in c or '电压' in c or '加速' in c][0] \
            if any('U' in c or '电压' in c or '加速' in c for c in cols) else cols[0]
        i_col = [c for c in cols if 'I' in c or '电流' in c or 'pA' in c or 'nA' in c][0] \
            if any('I' in c or '电流' in c or 'pA' in c or 'nA' in c for c in cols) else cols[1]

        U = pd.to_numeric(data[u_col], errors='coerce')  # V
        I = pd.to_numeric(data[i_col], errors='coerce')  # nA
        valid = pd.notna(U) & pd.notna(I)
        U = U[valid].reset_index(drop=True)
        I = I[valid].reset_index(drop=True)

        peak_u, peak_i = _detect_peaks(U.to_numpy(), I.to_numpy())

        docu = Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()
        docu.add_paragraph("Franck-Hertz 实验：氩原子激发")
        docu.add_paragraph("检测到 {} 个峰".format(len(peak_u)))
        if len(peak_u) >= 2:
            intervals = np.diff(peak_u)
            mean_du = float(np.mean(intervals))
            docu.add_paragraph("各峰位：{}".format(["{:.2f}".format(value) for value in peak_u]))
            docu.add_paragraph("相邻峰位间隔：{}".format(["{:.3f}".format(value) for value in intervals]))
            docu.add_paragraph("第一激发电位 ΔŪ = {:.3f} V".format(mean_du))
            docu.add_paragraph("激发能 E = e·ΔŪ = {:.3f} eV（标准值 ~11.55 V）".format(mean_du))
        docu.add_paragraph()

        # 数据表格：写入全部有效行，不再截断到 50 行
        table = docu.add_table(rows=len(U) + 1, cols=2, style='Table Grid')
        table.rows[0].cells[0].text = 'U_G2K (V)'
        table.rows[0].cells[1].text = 'I_p (nA)'
        for i in range(len(U)):
            table.rows[i + 1].cells[0].text = '{:.1f}'.format(U.iloc[i])
            table.rows[i + 1].cells[1].text = '{:.1f}'.format(I.iloc[i])
        docu.add_paragraph()

        docu.add_paragraph("公式：E = e \\cdot \\Delta U = hc/\\lambda")
        docu.add_paragraph("氩原子第一激发态能量（标准值）：~11.6 eV")

        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1
