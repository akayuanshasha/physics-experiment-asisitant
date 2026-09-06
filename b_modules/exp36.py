from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *
from structured_support import copied_tables


def name():
    return "偏振光"


def _malus_sample(start, stop, step):
    rows = []
    for angle in range(start, stop, step):
        intensity = 100.0 * math.cos(math.radians(angle)) ** 2 + 0.2
        rows.append({"theta_deg": angle, "intensity": round(intensity, 3)})
    return rows


def _malus_pos_sample():
    return _malus_sample(0, 91, 6)


def _malus_neg_sample():
    return _malus_sample(0, -91, -6)


def schema():
    formulas = get_formulas("exp36") + [
        {
            "title": "布儒斯特角测玻璃折射率及其不确定度",
            "steps": [
                {"note": "玻璃折射率：", "formula": r"n = n_1 \tan\theta_B"},
                {"note": "重复测量的A类不确定度：", "formula": r"u_A(\theta_B) = \frac{s(\theta_B)}{\sqrt{m}}"},
                {"note": "仪器分度值按均匀分布计算B类不确定度：", "formula": r"u_B(\theta_B) = \frac{\Delta\theta}{\sqrt{3}}"},
                {"note": "合成角度不确定度：", "formula": r"u(\theta_B) = \sqrt{u_A^2(\theta_B) + u_B^2(\theta_B)}"},
                {"note": "折射率不确定度（角度须换算为弧度）：", "formula": r"u(n) = n_1\sec^2\theta_B\,u(\theta_B)"},
            ],
        }
    ]
    variables = get_variables("exp36") + [
        {"symbol": "n", "description": "由布儒斯特角求得的玻璃折射率", "unit": "无单位"},
        {"symbol": "n_1", "description": "入射介质折射率", "unit": "无单位"},
        {"symbol": r"\theta_B", "description": "多次测量的布儒斯特角", "unit": "°"},
        {"symbol": r"\Delta\theta", "description": "测角仪器分度值", "unit": "°"},
        {"symbol": "m", "description": "布儒斯特角重复测量次数，至少3次", "unit": "无单位"},
    ]
    return {
        "schema_version": 2,
        "schema_revision": 4,
        "description": (
            "本实验完成偏振光的两项数据处理：① 马吕斯定律验证——检偏方向夹角在 0° 到 +90° 与 "
            "0° 到 −90° 两个方向每隔 6° 记录光强，分别验证 " r"$I = I_0\cos^2\theta$" "；② 布儒斯特角法测折射率——"
            "至少测量 3 次，由 " r"$n = n_1\tan\theta_B$" " 计算折射率，并用仪器分度值计算 B 类不确定度。"
        ),
        "parameters": [
            {
                "id": "angle_resolution_deg", "label": "布儒斯特角仪器分度值", "unit": "°",
                "type": "number", "default": 1, "required": True, "step": "0.1",
                "help": "至少测量3次，并用仪器分度值按均匀分布以Δθ/√3计算B类不确定度。",
            },
            {
                "id": "incident_index", "label": "入射介质折射率", "type": "number",
                "default": 1.000, "required": True, "step": "0.001",
            },
        ],
        "tables": [
            {
                "id": "malus_pos", "title": "表1  马吕斯定律（0°～+90°）", "required": True,
                "min_rows": 6, "initial_rows": 16,
                "description": "成功：检偏方向夹角从0°至+90°，建议每隔6°测量透射光强，验证 I = I₀cos²θ。",
                "columns": [
                    {"id": "theta_deg", "label": "透振方向夹角 θ", "unit": "°"},
                    {"id": "intensity", "label": "透射光强 I"},
                ],
                "sample": _malus_pos_sample(),
                "calc": {"label": "提交计算"},
                "chart": {"x_column": "theta_deg", "y_column": "intensity",
                          "x_label": "透振方向夹角 θ (deg)", "y_label": "透射光强 I",
                          "title": "马吕斯定律正角度响应（0°~+90°）",
                          "fit": None, "connect_points": True},
            },
            {
                "id": "malus_neg", "title": "表2  马吕斯定律（0°～-90°）", "required": True,
                "min_rows": 6, "initial_rows": 16,
                "description": "提升：检偏方向夹角从0°至-90°，建议每隔6°测量透射光强，验证 I = I₀cos²θ。",
                "columns": [
                    {"id": "theta_deg", "label": "透振方向夹角 θ", "unit": "°"},
                    {"id": "intensity", "label": "透射光强 I"},
                ],
                "sample": _malus_neg_sample(),
                "calc": {"label": "提交计算"},
                "chart": {"x_column": "theta_deg", "y_column": "intensity",
                          "x_label": "透振方向夹角 θ (deg)", "y_label": "透射光强 I",
                          "title": "马吕斯定律负角度响应（0°~-90°）",
                          "fit": None, "connect_points": True},
            },
            {
                "id": "brewster", "title": "表3  布儒斯特角重复测量", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "description": "至少测量3次，并用仪器分度值计算B类不确定度。",
                "columns": [{"id": "theta_b_deg", "label": "布儒斯特角 θB", "unit": "°"}],
                "sample": [
                    {"theta_b_deg": 56.4}, {"theta_b_deg": 56.6}, {"theta_b_deg": 56.5}
                ],
            },
        ],
    
        "formulas": formulas,
        "variables": variables,
        "table_theory": get_table_theory("exp36"),}


def _residual_std(fit):
    n = len(fit["x"])
    return float(np.sqrt(np.sum(fit["residuals"] ** 2) / (n - 2))) if n > 2 else 0.0


def _brewster_calc(payload, brewster_rows):
    """布儒斯特角均值、A/B 类不确定度、折射率及其不确定度。"""
    resolution_deg = get_parameter(payload, "angle_resolution_deg", 1.0, True)
    incident_index = get_parameter(payload, "incident_index", 1.0, True)
    if resolution_deg <= 0 or incident_index <= 0:
        raise OpticsInputError("角度分度值和入射介质折射率必须为正数")
    theta_b = numeric_column(brewster_rows, "theta_b_deg", "布儒斯特角")
    if np.any((theta_b <= 0) | (theta_b >= 90)):
        raise OpticsInputError("布儒斯特角应位于0°到90°之间")
    mean_theta_b = float(np.mean(theta_b))
    ua_theta = float(np.std(theta_b, ddof=1) / math.sqrt(len(theta_b)))
    ub_theta = float(resolution_deg / math.sqrt(3.0))
    combined_theta = math.sqrt(ua_theta ** 2 + ub_theta ** 2)
    theta_rad = math.radians(mean_theta_b)
    refractive_index = incident_index * math.tan(theta_rad)
    refractive_uncertainty = incident_index / math.cos(theta_rad) ** 2 * math.radians(combined_theta)
    return {
        "mean": mean_theta_b, "combined": combined_theta,
        "n": refractive_index, "u_n": refractive_uncertainty,
    }


def malus_fit_for(rows, label):
    """对一份马吕斯数据做 I/I0 对 cos²θ 的线性拟合。

    返回 (数组字典, lines, chart)。供 preview 与 handle_structured 共用。
    """
    theta = numeric_column(rows, "theta_deg", "透振方向夹角")
    intensity = numeric_column(rows, "intensity", "透射光强")
    if np.any(intensity < 0):
        raise OpticsInputError("透射光强不能为负数")
    zero_indices = np.where(np.isclose(theta, 0.0, atol=1e-8))[0]
    if len(zero_indices):
        i0 = float(np.mean(intensity[zero_indices]))
    else:
        i0 = float(np.max(intensity))
    if i0 <= 0:
        raise OpticsInputError("I₀必须大于0")
    cos_squared = np.cos(np.deg2rad(theta)) ** 2
    normalized = intensity / i0
    fit = linear_fit(cos_squared, normalized)
    lines = [
        f"{label}拟合：I/I₀ = {fit['slope']:.6f}cos²θ + {fit['intercept']:.6f}，r = {fit['r']:.6f}",
        f"{label}拟合标准差 = {_residual_std(fit):.6f}",
    ]
    order = np.argsort(theta)
    chart = {
        "title": f"马吕斯定律{label}角度响应（归一化光强）",
        "x_label": "透振方向夹角 θ (deg)",
        "y_label": "归一化光强 I/I₀",
        "x": [float(v) for v in theta[order]],
        "y": [float(v) for v in normalized[order]],
    }
    return {"theta": theta, "intensity": intensity, "cos_squared": cos_squared,
            "normalized": normalized, "fit": fit, "i0": i0, "lines": lines, "chart": chart}


def preview(payload):
    """实时预计算：正、负角度马吕斯表各自独立的拟合结果，供每表「提交计算」按钮显示。"""
    tables = copied_tables(payload)
    calc_results = {}
    for table_id, label in (("malus_pos", "0°～+90°"), ("malus_neg", "0°～-90°")):
        rows = tables.get(table_id) or []
        if not rows:
            calc_results[table_id] = {
                "lines": ["请先在表内填写角度与光强数据（可点「填入本表全部示例数据」）。"]}
            continue
        try:
            theta = numeric_column(rows, "theta_deg", "透振方向夹角")
            result = malus_fit_for(rows, label)
            lines = list(result["lines"])
            if not np.any(np.isclose(theta, 0.0, atol=1e-8)):
                lines.append("提示：本表没有 θ=0° 测量点，已暂以最大光强代替 I₀，建议补测 0° 数据。")
            calc_results[table_id] = {"lines": lines, "chart": result["chart"]}
        except OpticsInputError as exc:
            calc_results[table_id] = {"lines": [f"无法计算：{exc}"]}
    return {"tables": tables, "calc_results": calc_results}


def handle_structured(workpath, payload):
    try:
        malus_pos_rows = get_rows(payload, "malus_pos", required=True, min_rows=6)
        malus_neg_rows = get_rows(payload, "malus_neg", required=True, min_rows=6)
        brewster_rows = get_rows(payload, "brewster", required=True, min_rows=3)
        brewster = _brewster_calc(payload, brewster_rows)

        pos = malus_fit_for(malus_pos_rows, "0°～+90°")
        neg = malus_fit_for(malus_neg_rows, "0°～-90°")

        warnings = []
        for side, result, expected_sign in (("正角度", pos, +1), ("负角度", neg, -1)):
            theta = result["theta"]
            if len(theta) > 1:
                median_step = float(np.median(np.diff(np.sort(np.unique(theta)))))
                if not math.isclose(median_step, 6.0, rel_tol=0.05, abs_tol=0.2):
                    warnings.append(f"指导书建议每隔6°测量；{side}当前角度的典型步长约为{median_step:.2f}°。")
            if len(theta):
                extreme = float(np.max(theta)) if expected_sign > 0 else float(np.min(theta))
                reach = expected_sign * extreme
                if reach < 85:
                    warnings.append(
                        f"{side}数据未完整覆盖期望的角度范围（0° 至 {int(expected_sign * 90)}°），"
                        f"目前最远仅到 {extreme:.0f}°，请确认是否录入完整。")

        summary = [
            f"表1（0°～+90°）拟合：I/I₀ = {pos['fit']['slope']:.6f}cos²θ + {pos['fit']['intercept']:.6f}，"
            f"r = {pos['fit']['r']:.6f}，拟合标准差 = {_residual_std(pos['fit']):.6f}",
            f"表2（0°～-90°）拟合：I/I₀ = {neg['fit']['slope']:.6f}cos²θ + {neg['fit']['intercept']:.6f}，"
            f"r = {neg['fit']['r']:.6f}，拟合标准差 = {_residual_std(neg['fit']):.6f}",
            f"布儒斯特角 θB = ({brewster['mean']:.4f} ± {brewster['combined']:.4f})°",
            f"玻璃折射率 n = {brewster['n']:.5f} ± {brewster['u_n']:.5f}",
        ]

        doc = create_document(name())
        for title, result, table_label in (
                ("表1  马吕斯定律（0°～+90°）", pos, "正角度"),
                ("表2  马吕斯定律（0°～-90°）", neg, "负角度")):
            rows = [[
                f"{result['theta'][index]:.3f}", f"{result['intensity'][index]:.6g}",
                f"{result['cos_squared'][index]:.6f}", f"{result['normalized'][index]:.6f}",
            ] for index in range(len(result["theta"]))]
            add_table(doc, title, ["θ/°", "I", "cos²θ", "I/I₀"], rows)
        brewster_table = [[index + 1, f"{brewster_v:.5f}"] for index, brewster_v in enumerate(
            numeric_column(brewster_rows, "theta_b_deg", "布儒斯特角"))]
        add_table(doc, "表3  布儒斯特角", ["次数", "θB/°"], brewster_table)
        add_summary(doc, summary)

        configure_plotting()
        charts = []
        for filename, result, label, color in (
                ("exp36_malus_pos_fit.png", pos, "0°～+90°", "#E74C3C"),
                ("exp36_malus_neg_fit.png", neg, "0°～-90°", "#2ECC71")):
            fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
            order = np.argsort(result["theta"])
            axes[0].plot(result["theta"][order], result["normalized"][order], "o-", color=color, markersize=4)
            axes[0].set_xlabel("透振方向夹角 θ / °")
            axes[0].set_ylabel("归一化光强 I/I0")
            axes[0].set_title(f"马吕斯定律{label}原始角度响应")
            axes[0].grid(True, linestyle="--", alpha=0.35)
            fit = result["fit"]
            axes[1].scatter(fit["x"], fit["y"], s=34, color=color, alpha=0.8, label="数据")
            x_line = np.linspace(0, 1, 120)
            axes[1].plot(x_line, fit["slope"] * x_line + fit["intercept"], color=color,
                         label=f"线性拟合，r={fit['r']:.4f}")
            axes[1].set_xlabel("cos²θ")
            axes[1].set_ylabel("I/I0")
            axes[1].set_title(f"马吕斯定律{label}线性拟合")
            axes[1].grid(True, linestyle="--", alpha=0.35)
            axes[1].legend(fontsize=9)
            charts.append({"filename": save_figure(fig, workpath, filename),
                           "title": f"马吕斯定律{label}原始响应与线性拟合"})
        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
