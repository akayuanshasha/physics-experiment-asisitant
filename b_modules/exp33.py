from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *


def name():
    return "对切透镜的光学实验"


def schema():
    return {
        "schema_version": 2,
        "description": "按指导书分别处理比列对切透镜基础/提升内容和梅斯林进阶内容。比列实验必须测量3次，并记录成像放大的两段距离。",
        "parameters": [
            {
                "id": "part", "label": "实验内容", "type": "select", "default": "billet_basic",
                "required": True,
                "options": [
                    {"value": "billet_basic", "label": "比列对切透镜：光源距离 f（基础）"},
                    {"value": "billet_enhanced", "label": "比列对切透镜：光源距离 1.5f（提升）"},
                    {"value": "maslin_advanced", "label": "梅斯林对切透镜：条纹半径（进阶）"},
                ],
            },
            {"id": "wavelength_nm", "label": "激光波长", "unit": "nm", "type": "number", "default": 632.8, "required": True, "step": "0.1"},
            {
                "id": "cut_focal_cm", "label": "对切透镜实测焦距 f", "unit": "cm", "type": "number",
                "default": 10, "required": True, "step": "1",
                "help": "这是对切透镜焦距，不是3.5 cm的成像透镜焦距；按指导书精度保留到1 cm。",
            },
            {"id": "imaging_focal_cm", "label": "成像透镜焦距 f₁", "unit": "cm", "type": "number", "default": 3.5, "required": True, "step": "0.1"},
        ],
        "tables": [
            {
                "id": "billet_measurements", "title": "比列对切透镜的三次测量", "required": True,
                "condition": {"parameter": "part", "in": ["billet_basic", "billet_enhanced"]},
                "min_rows": 3, "initial_rows": 3,
                "description": "每次改变成像透镜或屏的位置。总长度应跨越多个完整条纹间隔，以减小读数误差。",
                "columns": [
                    {"id": "span_mm", "label": "放大后多周期总长度", "unit": "mm"},
                    {"id": "periods", "label": "对应条纹间隔数 N"},
                    {"id": "object_distance_cm", "label": "对切透镜至成像透镜距离 p", "unit": "cm"},
                    {"id": "image_distance_cm", "label": "成像透镜至屏距离 q", "unit": "cm"},
                ],
                "sample": [
                    {"span_mm": 12.60, "periods": 20, "object_distance_cm": 7.0, "image_distance_cm": 14.0},
                    {"span_mm": 16.10, "periods": 20, "object_distance_cm": 8.0, "image_distance_cm": 20.0},
                    {"span_mm": 20.80, "periods": 20, "object_distance_cm": 9.0, "image_distance_cm": 30.0},
                ],
            },
            {
                "id": "maslin_f", "title": "梅斯林条纹半径：光源距离 f", "required": True,
                "condition": {"parameter": "part", "equals": "maslin_advanced"},
                "min_rows": 4, "initial_rows": 8,
                "columns": [
                    {"id": "k", "label": "级次 K"},
                    {"id": "r_k_mm", "label": "第K级半径 Lₖ", "unit": "mm"},
                    {"id": "r_k1_mm", "label": "第K+1级半径 Lₖ₊₁", "unit": "mm"},
                ],
                "sample": [
                    {"k": 1, "r_k_mm": 4.20, "r_k1_mm": 5.91},
                    {"k": 2, "r_k_mm": 5.91, "r_k1_mm": 7.22},
                    {"k": 3, "r_k_mm": 7.22, "r_k1_mm": 8.32},
                    {"k": 4, "r_k_mm": 8.32, "r_k1_mm": 9.29},
                ],
            },
            {
                "id": "maslin_1_3f", "title": "梅斯林条纹半径：光源距离 1.3f", "required": True,
                "condition": {"parameter": "part", "equals": "maslin_advanced"},
                "min_rows": 4, "initial_rows": 8,
                "columns": [
                    {"id": "k", "label": "级次 K"},
                    {"id": "r_k_mm", "label": "第K级半径 Lₖ", "unit": "mm"},
                    {"id": "r_k1_mm", "label": "第K+1级半径 Lₖ₊₁", "unit": "mm"},
                ],
                "sample": [
                    {"k": 1, "r_k_mm": 5.00, "r_k1_mm": 7.04},
                    {"k": 2, "r_k_mm": 7.04, "r_k1_mm": 8.60},
                    {"k": 3, "r_k_mm": 8.60, "r_k1_mm": 9.91},
                    {"k": 4, "r_k_mm": 9.91, "r_k1_mm": 11.06},
                ],
            },
        ],
    
        "formulas": get_formulas("exp33"),
        "variables": get_variables("exp33"),
        "table_theory": get_table_theory("exp33"),}


def _handle_billet(workpath, payload, part):
    rows = get_rows(payload, "billet_measurements", required=True, min_rows=3)
    wavelength_nm = get_parameter(payload, "wavelength_nm", 632.8, True)
    focal_cm = get_parameter(payload, "cut_focal_cm", None, True)
    imaging_focal_cm = get_parameter(payload, "imaging_focal_cm", 3.5, True)
    if wavelength_nm <= 0 or focal_cm <= 0 or imaging_focal_cm <= 0:
        raise OpticsInputError("波长和两个焦距必须为正数")

    span = numeric_column(rows, "span_mm", "放大后多周期总长度")
    periods = numeric_column(rows, "periods", "条纹间隔数")
    p_cm = numeric_column(rows, "object_distance_cm", "对切透镜至成像透镜距离")
    q_cm = numeric_column(rows, "image_distance_cm", "成像透镜至屏距离")
    if np.any(span <= 0) or np.any(periods <= 0) or np.any(p_cm <= 0) or np.any(q_cm <= 0):
        raise OpticsInputError("总长度、条纹间隔数和两段距离都必须为正数")

    magnification = q_cm / p_cm
    enlarged_spacing = span / periods
    original_spacing = enlarged_spacing / magnification
    wavelength_mm = wavelength_nm * 1e-6
    focal_mm = focal_cm * 10.0
    if part == "billet_basic":
        cut_width = focal_mm * wavelength_mm / original_spacing
        formula_label = "a=fλ/Δx（公式7）"
    else:
        source_distance = 1.5 * focal_mm
        observation_distance = p_cm * 10.0
        numerator = focal_mm * source_distance - observation_distance * source_distance + observation_distance * focal_mm
        cut_width = np.abs(numerator * wavelength_mm / (source_distance * original_spacing))
        formula_label = "a=|(fL-DL+Df)λ/(LΔx)|（由公式2变形）"

    mean_width = float(np.mean(cut_width))
    warnings = []
    if len(rows) != 3:
        warnings.append(f"指导书要求测量3次；当前输入了{len(rows)}次，结果仍按全部数据求平均。")
    lens_balance = np.abs(1 / imaging_focal_cm - 1 / p_cm - 1 / q_cm) / (1 / imaging_focal_cm)
    for index, imbalance in enumerate(lens_balance, 1):
        if imbalance > 0.25:
            warnings.append(f"第{index}次的 p、q 与 f₁ 偏离薄透镜成像关系较大，请核对距离定义或读数。")

    report_rows = []
    for index in range(len(rows)):
        report_rows.append([
            index + 1, f"{span[index]:.4f}", f"{periods[index]:.0f}", f"{p_cm[index]:.3f}",
            f"{q_cm[index]:.3f}", f"{magnification[index]:.4f}",
            f"{original_spacing[index]:.6f}", f"{cut_width[index]:.6f}",
        ])

    title = "基础内容（光源距离 f）" if part == "billet_basic" else "提升内容（光源距离 1.5f）"
    summary = [
        f"处理内容：{title}",
        f"计算公式：{formula_label}",
        f"切去部分宽度平均值 ā = {mean_width:.6f} mm（按指导书仅报告平均值）",
    ]
    doc = create_document(name(), title)
    add_key_values(doc, "实验常量", [
        ("激光波长 λ", f"{wavelength_nm:.1f} nm"),
        ("对切透镜实测焦距 f", f"{focal_cm:.1f} cm"),
        ("成像透镜焦距 f₁", f"{imaging_focal_cm:.2f} cm"),
    ])
    add_table(doc, "原始数据与计算", [
        "次数", "总长度/mm", "N", "p/cm", "q/cm", "放大倍率q/p", "原始Δx/mm", "a/mm"
    ], report_rows)
    add_summary(doc, summary)
    add_text_section(doc, "条纹形貌与实验现象", get_text(payload, "fringe_description"))

    configure_plotting()
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    indexes = np.arange(1, len(cut_width) + 1)
    ax.scatter(indexes, cut_width, s=58, color="#4472C4", label="各次测量")
    ax.axhline(mean_width, color="#E74C3C", linestyle="--", label=f"平均值 {mean_width:.6f} mm")
    ax.set_xticks(indexes)
    ax.set_xlabel("测量次数")
    ax.set_ylabel("切去部分宽度 a / mm")
    ax.set_title("比列对切透镜切去宽度的重复测量")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    chart = save_figure(fig, workpath, "exp33_billet_width.png")
    charts = [{"filename": chart, "title": "比列对切透镜切去宽度的重复测量"}]
    return finish_report(doc, workpath, name(), summary, charts, warnings)


def _maslin_dataset(payload, table_id, label):
    rows = get_rows(payload, table_id, required=True, min_rows=4)
    k = numeric_column(rows, "k", f"{label}级次")
    r_k = numeric_column(rows, "r_k_mm", f"{label}第K级半径")
    r_k1 = numeric_column(rows, "r_k1_mm", f"{label}第K+1级半径")
    if np.any(k < 0) or np.any(r_k < 0) or np.any(r_k1 < 0):
        raise OpticsInputError("梅斯林条纹级次和半径不能为负数")
    delta_rho = r_k1 - r_k
    x_value = np.sqrt(k + 1) - np.sqrt(k)
    fit = linear_fit(x_value, delta_rho)
    return rows, k, r_k, r_k1, delta_rho, x_value, fit


def _handle_maslin(workpath, payload):
    first = _maslin_dataset(payload, "maslin_f", "光源距离f")
    second = _maslin_dataset(payload, "maslin_1_3f", "光源距离1.3f")
    datasets = [("光源距离 f", first), ("光源距离 1.3f", second)]
    summary = []
    doc = create_document(name(), "梅斯林对切透镜进阶内容")
    for label, dataset in datasets:
        _, k, r_k, r_k1, delta_rho, x_value, fit = dataset
        rows = [
            [f"{k[i]:.0f}", f"{x_value[i]:.6f}", f"{r_k[i]:.4f}", f"{r_k1[i]:.4f}", f"{delta_rho[i]:.4f}"]
            for i in range(len(k))
        ]
        add_table(doc, label, ["K", "√(K+1)-√K", "Lₖ/mm", "Lₖ₊₁/mm", "Δρ/mm"], rows)
        line = f"{label}：Δρ = {fit['slope']:.5f}x + {fit['intercept']:.5f}，R²={fit['r2']:.5f}"
        summary.append(line)
    add_summary(doc, summary)
    add_text_section(doc, "条纹形貌与实验现象", get_text(payload, "fringe_description"))

    configure_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    for ax, (label, dataset), color in zip(axes, datasets, ["#4472C4", "#E67E22"]):
        _, _, _, _, delta_rho, x_value, fit = dataset
        ax.scatter(x_value, delta_rho, color=color, s=48, label="实验数据")
        x_line = np.linspace(np.min(x_value), np.max(x_value), 150)
        ax.plot(x_line, fit["slope"] * x_line + fit["intercept"], color="#E74C3C",
                label=f"线性拟合 R²={fit['r2']:.4f}")
        ax.set_xlabel("√(K+1)-√K")
        ax.set_ylabel("相邻条纹半径差 Δρ / mm")
        ax.set_title(label)
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend(fontsize=9)
    chart = save_figure(fig, workpath, "exp33_maslin_linearity.png")
    charts = [{"filename": chart, "title": "梅斯林条纹半径差的线性检验"}]
    return finish_report(doc, workpath, name(), summary, charts)


def handle_structured(workpath, payload):
    try:
        part = get_parameter(payload, "part", "billet_basic", True, cast=str)
        if part in ("billet_basic", "billet_enhanced"):
            return _handle_billet(workpath, payload, part)
        if part == "maslin_advanced":
            return _handle_maslin(workpath, payload)
        raise OpticsInputError("未识别的实验内容")
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    """保留旧单表入口；网页已改用 handle_structured。"""
    return 1
