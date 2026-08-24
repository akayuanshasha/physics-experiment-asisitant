from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *


def name():
    return "偏振光"


def _malus_sample():
    rows = []
    for angle in range(-90, 91, 6):
        intensity = 100.0 * math.cos(math.radians(angle)) ** 2 + 0.2
        rows.append({"theta_deg": angle, "intensity": round(intensity, 3)})
    return rows


def schema():
    return {
        "schema_version": 2,
        "description": "依照指导书分为半导体激光器偏振度、马吕斯定律和布儒斯特角三部分；马吕斯定律对正、负角度分别进行线性拟合。",
        "parameters": [
            {
                "id": "angle_resolution_deg", "label": "布儒斯特角仪器分度值", "unit": "°",
                "type": "number", "default": 1, "required": True, "step": "0.1",
                "help": "按均匀分布以分度值/√3计入B类角度不确定度。",
            },
            {
                "id": "incident_index", "label": "入射介质折射率", "type": "number",
                "default": 1.000, "required": True, "step": "0.001",
            },
        ],
        "tables": [
            {
                "id": "polarization_degree", "title": "表1  半导体激光器偏振度", "required": True,
                "min_rows": 1, "initial_rows": 2,
                "columns": [
                    {"id": "imax", "label": "光强极大值 Imax"},
                    {"id": "theta_max_deg", "label": "极大值角度", "unit": "°"},
                    {"id": "imin", "label": "光强极小值 Imin"},
                    {"id": "theta_min_deg", "label": "极小值角度", "unit": "°"},
                ],
                "sample": [
                    {"imax": 100.2, "theta_max_deg": 0, "imin": 0.35, "theta_min_deg": 90},
                    {"imax": 100.0, "theta_max_deg": 180, "imin": 0.40, "theta_min_deg": 270},
                ],
            },
            {
                "id": "malus", "title": "表2  验证马吕斯定律", "required": True,
                "min_rows": 10, "initial_rows": 31,
                "description": "指导书要求检偏方向夹角从90°至-90°，每隔6°测量。",
                "columns": [
                    {"id": "theta_deg", "label": "透振方向夹角 θ", "unit": "°"},
                    {"id": "intensity", "label": "透射光强 I"},
                ],
                "sample": _malus_sample(),
            },
            {
                "id": "brewster", "title": "表3  布儒斯特角重复测量", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "description": "输入自行设计实验得到的布儒斯特角；至少3次才能计算A类不确定度。",
                "columns": [{"id": "theta_b_deg", "label": "布儒斯特角 θB", "unit": "°"}],
                "sample": [
                    {"theta_b_deg": 56.4}, {"theta_b_deg": 56.6}, {"theta_b_deg": 56.5}
                ],
            },
        ],
    
        "formulas": get_formulas("exp36"),
        "variables": get_variables("exp36"),
        "table_theory": get_table_theory("exp36"),}


def _residual_std(fit):
    n = len(fit["x"])
    return float(np.sqrt(np.sum(fit["residuals"] ** 2) / (n - 2))) if n > 2 else 0.0


def handle_structured(workpath, payload):
    try:
        pol_rows = get_rows(payload, "polarization_degree", required=True, min_rows=1)
        malus_rows = get_rows(payload, "malus", required=True, min_rows=10)
        brewster_rows = get_rows(payload, "brewster", required=True, min_rows=3)
        resolution_deg = get_parameter(payload, "angle_resolution_deg", 1.0, True)
        incident_index = get_parameter(payload, "incident_index", 1.0, True)
        if resolution_deg <= 0 or incident_index <= 0:
            raise OpticsInputError("角度分度值和入射介质折射率必须为正数")

        imax = numeric_column(pol_rows, "imax", "光强极大值")
        imin = numeric_column(pol_rows, "imin", "光强极小值")
        theta_max = numeric_column(pol_rows, "theta_max_deg", "极大值角度")
        theta_min = numeric_column(pol_rows, "theta_min_deg", "极小值角度")
        if np.any(imax <= 0) or np.any(imin < 0) or np.any(imax < imin):
            raise OpticsInputError("偏振度表应满足 Imax>0 且 Imax≥Imin≥0")
        mean_imax = float(np.mean(imax))
        mean_imin = float(np.mean(imin))
        polarization = (mean_imax - mean_imin) / (mean_imax + mean_imin)

        theta = numeric_column(malus_rows, "theta_deg", "透振方向夹角")
        intensity = numeric_column(malus_rows, "intensity", "透射光强")
        if np.any(intensity < 0):
            raise OpticsInputError("透射光强不能为负数")
        zero_indices = np.where(np.isclose(theta, 0.0, atol=1e-8))[0]
        warnings = []
        if len(zero_indices):
            i0 = float(np.mean(intensity[zero_indices]))
        else:
            i0 = float(np.max(intensity))
            warnings.append("马吕斯数据中没有θ=0°测量点，暂以最大光强代替I₀；建议补测0°数据。")
        if i0 <= 0:
            raise OpticsInputError("I₀必须大于0")
        cos_squared = np.cos(np.deg2rad(theta)) ** 2
        normalized = intensity / i0
        positive_mask = theta >= 0
        negative_mask = theta <= 0
        fit_positive = linear_fit(cos_squared[positive_mask], normalized[positive_mask])
        fit_negative = linear_fit(cos_squared[negative_mask], normalized[negative_mask])

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

        sorted_unique = np.sort(np.unique(theta))
        if len(sorted_unique) > 1:
            median_step = float(np.median(np.diff(sorted_unique)))
            if not math.isclose(median_step, 6.0, rel_tol=0.05, abs_tol=0.2):
                warnings.append(f"指导书建议每隔6°测量；当前角度的典型步长约为{median_step:.2f}°。")
        if np.min(theta) > -89 or np.max(theta) < 89:
            warnings.append("马吕斯数据没有完整覆盖-90°至90°，请确认是否录入完整。")

        summary = [
            f"平均Imax={mean_imax:.5g}，平均Imin={mean_imin:.5g}",
            f"半导体激光器偏振度 P = {polarization:.6f}（{polarization * 100:.3f}%）",
            f"0°～90°拟合：I/I₀ = {fit_positive['slope']:.6f}cos²θ + {fit_positive['intercept']:.6f}，r={fit_positive['r']:.6f}",
            f"0°～-90°拟合：I/I₀ = {fit_negative['slope']:.6f}cos²θ + {fit_negative['intercept']:.6f}，r={fit_negative['r']:.6f}",
            f"正角度拟合标准差={_residual_std(fit_positive):.6f}，负角度拟合标准差={_residual_std(fit_negative):.6f}",
            f"布儒斯特角 θB = ({mean_theta_b:.4f} ± {combined_theta:.4f})°",
            f"玻璃折射率 n = {refractive_index:.5f} ± {refractive_uncertainty:.5f}",
        ]

        doc = create_document(name())
        pol_table = [
            [index + 1, f"{imax[index]:.6g}", f"{theta_max[index]:.3f}", f"{imin[index]:.6g}", f"{theta_min[index]:.3f}"]
            for index in range(len(pol_rows))
        ]
        add_table(doc, "表1  半导体激光器偏振度", ["次数", "Imax", "极大角/°", "Imin", "极小角/°"], pol_table)
        malus_table = [
            [f"{theta[index]:.3f}", f"{intensity[index]:.6g}", f"{cos_squared[index]:.6f}", f"{normalized[index]:.6f}"]
            for index in range(len(theta))
        ]
        add_table(doc, "表2  马吕斯定律", ["θ/°", "I", "cos²θ", "I/I₀"], malus_table)
        brewster_table = [[index + 1, f"{theta_b[index]:.5f}"] for index in range(len(theta_b))]
        add_table(doc, "表3  布儒斯特角", ["次数", "θB/°"], brewster_table)
        add_summary(doc, summary)
        add_text_section(doc, "布儒斯特角实验方案", get_text(payload, "brewster_plan"))
        add_text_section(doc, "显示屏或其他光源的偏振状态判断", get_text(payload, "polarization_state"))
        add_text_section(doc, "实验思考与讨论", get_text(payload, "discussion"))

        configure_plotting()
        fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
        order = np.argsort(theta)
        axes[0].plot(theta[order], normalized[order], "o-", color="#4472C4", markersize=4)
        axes[0].set_xlabel("透振方向夹角 θ / °")
        axes[0].set_ylabel("归一化光强 I/I0")
        axes[0].set_title("马吕斯定律原始角度响应")
        axes[0].grid(True, linestyle="--", alpha=0.35)
        for fit, label, color in [
            (fit_positive, "0°～90°", "#E74C3C"),
            (fit_negative, "0°～-90°", "#2ECC71"),
        ]:
            axes[1].scatter(fit["x"], fit["y"], s=34, color=color, alpha=0.8, label=f"{label}数据")
            x_line = np.linspace(0, 1, 120)
            axes[1].plot(x_line, fit["slope"] * x_line + fit["intercept"], color=color,
                         label=f"{label}拟合，r={fit['r']:.4f}")
        axes[1].set_xlabel("cos²θ")
        axes[1].set_ylabel("I/I0")
        axes[1].set_title("正、负角度分别线性拟合")
        axes[1].grid(True, linestyle="--", alpha=0.35)
        axes[1].legend(fontsize=8)
        chart = save_figure(fig, workpath, "exp36_malus_fit.png")
        charts = [{"filename": chart, "title": "马吕斯定律原始响应与正负角度线性拟合"}]
        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
