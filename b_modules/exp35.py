from head import *
from optics_common import *


def name():
    return "迈氏干涉仪"


def schema():
    return {
        "schema_version": 2,
        "description": "基础内容用累计条纹数与M₁镜位置进行最小二乘拟合；提高内容另用三次位置和厚度读数计算透明薄片折射率。",
        "parameters": [
            {
                "id": "micrometer_zero_mm", "label": "千分尺零点", "unit": "mm", "type": "number",
                "default": 0, "required": False, "step": "0.001",
                "help": "仅用于薄片厚度修正；若仪器无零点误差可填0。",
            }
        ],
        "tables": [
            {
                "id": "wavelength", "title": "表1  He-Ne激光波长测量", "required": True,
                "min_rows": 5, "initial_rows": 8,
                "description": "N填累计吞入或吐出的条纹数；指导书要求累计范围不小于400条。",
                "columns": [
                    {"id": "N", "label": "累计条纹数 N"},
                    {"id": "position_mm", "label": "M₁镜位置 Sₙ", "unit": "mm"},
                ],
                "sample": [
                    {"N": 50, "position_mm": 10.01582},
                    {"N": 100, "position_mm": 10.03166},
                    {"N": 150, "position_mm": 10.04745},
                    {"N": 200, "position_mm": 10.06330},
                    {"N": 250, "position_mm": 10.07908},
                    {"N": 300, "position_mm": 10.09494},
                    {"N": 350, "position_mm": 10.11073},
                    {"N": 400, "position_mm": 10.12658},
                ],
            },
            {
                "id": "film", "title": "表2  透明薄片折射率（三次测量）", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "columns": [
                    {"id": "without_mm", "label": "无样品时M₁镜位置", "unit": "mm"},
                    {"id": "with_mm", "label": "加样品时M₁镜位置", "unit": "mm"},
                    {"id": "thickness_reading_mm", "label": "薄片厚度读数", "unit": "mm"},
                ],
                "sample": [
                    {"without_mm": 12.500, "with_mm": 12.578, "thickness_reading_mm": 0.152},
                    {"without_mm": 12.496, "with_mm": 12.574, "thickness_reading_mm": 0.151},
                    {"without_mm": 12.503, "with_mm": 12.581, "thickness_reading_mm": 0.153},
                ],
            },
        ],
    }


def handle_structured(workpath, payload):
    try:
        wave_rows = get_rows(payload, "wavelength", required=True, min_rows=5)
        film_rows = get_rows(payload, "film", required=True, min_rows=3)
        zero_mm = get_parameter(payload, "micrometer_zero_mm", 0.0, False)

        counts = numeric_column(wave_rows, "N", "累计条纹数N")
        positions = numeric_column(wave_rows, "position_mm", "M₁镜位置")
        if np.any(counts < 0):
            raise OpticsInputError("累计条纹数不能为负数")
        fit = linear_fit(counts, positions)
        wavelength_nm = abs(2.0 * fit["slope"] * 1e6)
        wavelength_std_nm = 2.0 * fit["slope_stderr"] * 1e6

        without = numeric_column(film_rows, "without_mm", "无样品位置")
        with_sample = numeric_column(film_rows, "with_mm", "加样品位置")
        thickness_reading = numeric_column(film_rows, "thickness_reading_mm", "薄片厚度读数")
        mirror_move = np.abs(with_sample - without)
        thickness = np.abs(thickness_reading - zero_mm)
        if np.any(thickness <= 0):
            raise OpticsInputError("零点修正后的薄片厚度必须大于0")
        mean_move = float(np.mean(mirror_move))
        mean_thickness = float(np.mean(thickness))
        refractive_index = 1.0 + mean_move / mean_thickness

        warnings = []
        if float(np.max(counts) - np.min(counts)) < 350 and float(np.max(counts)) < 400:
            warnings.append("指导书要求累计条纹数不少于400；当前数据覆盖范围不足，请确认是否录入完整。")
        if len(film_rows) != 3:
            warnings.append(f"指导书要求薄片位置和厚度各测量3次；当前输入了{len(film_rows)}次。")
        if not (350 <= wavelength_nm <= 850):
            warnings.append("拟合得到的波长超出常见可见光范围，请检查鼓轮方向、单位和累计条纹数。")

        summary = [
            f"最小二乘拟合：Sₙ = ({fit['slope']:.9f} mm)N + {fit['intercept']:.6f} mm",
            f"相关系数 r = {fit['r']:.6f}，R² = {fit['r2']:.6f}",
            f"He-Ne激光波长 λ = {wavelength_nm:.3f} nm，拟合标准差 u(λ) = {wavelength_std_nm:.3f} nm",
            f"M₁镜平均移动距离 d̄ = {mean_move:.6f} mm",
            f"薄片平均厚度 l̄ = {mean_thickness:.6f} mm",
            f"薄片折射率 n = 1 + d̄/l̄ = {refractive_index:.5f}",
        ]

        doc = create_document(name())
        wave_table = []
        order = np.argsort(counts)
        sorted_counts = counts[order]
        sorted_positions = positions[order]
        differences_um = np.insert(np.diff(sorted_positions) * 1000.0, 0, np.nan)
        for index in range(len(sorted_counts)):
            diff_text = "—" if index == 0 else f"{differences_um[index]:.4f}"
            wave_table.append([f"{sorted_counts[index]:.0f}", f"{sorted_positions[index]:.6f}", diff_text])
        add_table(doc, "表1  He-Ne激光波长测量", ["累计N", "Sₙ/mm", "相邻位置差/μm"], wave_table)

        film_table = []
        for index in range(len(film_rows)):
            film_table.append([
                index + 1, f"{without[index]:.6f}", f"{with_sample[index]:.6f}",
                f"{mirror_move[index]:.6f}", f"{thickness_reading[index]:.6f}", f"{thickness[index]:.6f}",
            ])
        add_table(doc, "表2  透明薄片折射率", [
            "次数", "无样品位置/mm", "加样品位置/mm", "d/mm", "测厚读数/mm", "零修正厚度/mm"
        ], film_table)
        add_key_values(doc, "仪器修正", [("千分尺零点", f"{zero_mm:.6f} mm")])
        add_summary(doc, summary)
        add_text_section(doc, "干涉条纹变化规律", get_text(payload, "fringe_observation"))
        add_text_section(doc, "实验思考与讨论", get_text(payload, "discussion"))

        configure_plotting()
        fig, axes = plt.subplots(2, 1, figsize=(7.5, 7.2), gridspec_kw={"height_ratios": [2.2, 1]})
        ax = axes[0]
        ax.scatter(fit["x"], fit["y"], s=52, color="#4472C4", label="测量数据")
        x_line = np.linspace(np.min(fit["x"]), np.max(fit["x"]), 200)
        ax.plot(x_line, fit["slope"] * x_line + fit["intercept"], color="#E74C3C",
                label=f"最小二乘拟合，R²={fit['r2']:.6f}")
        ax.set_xlabel("累计条纹数 N")
        ax.set_ylabel("M1镜位置 S_n / mm")
        ax.set_title("He-Ne激光波长的最小二乘测量")
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend()
        axes[1].axhline(0, color="#555555", linewidth=1)
        axes[1].scatter(fit["x"], fit["residuals"] * 1e6, color="#2ECC71", s=42)
        axes[1].set_xlabel("累计条纹数 N")
        axes[1].set_ylabel("残差 / nm（镜面位移等效）")
        axes[1].set_title("拟合残差")
        axes[1].grid(True, linestyle="--", alpha=0.35)
        chart = save_figure(fig, workpath, "exp35_wavelength_fit.png")
        charts = [{"filename": chart, "title": "He-Ne激光波长最小二乘拟合及残差"}]
        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
