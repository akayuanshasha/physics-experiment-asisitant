from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *


def name():
    return "双光栅"


def schema():
    return {
        "schema_version": 2,
        "report_enabled": False,
        "description": "本模块对应“光栅衍射和双光栅Lau效应”，不再使用速度—拍频模型。基础内容测光栅常数，提升内容用标准样品比较法测折射率。",
        "parameters": [
            {"id": "wavelength_nm", "label": "钠光波长", "unit": "nm", "type": "number", "default": 589.3, "required": True, "step": "0.1"},
            {"id": "standard_index", "label": "标准样品折射率", "type": "number", "default": 1.5263, "required": True, "step": "0.0001"},
            {"id": "standard_thickness_mm", "label": "标准样品厚度", "unit": "mm", "type": "number", "default": 1.000, "required": True, "step": "0.001"},
            {"id": "unknown_thickness_mm", "label": "待测样品厚度", "unit": "mm", "type": "number", "default": 1.200, "required": True, "step": "0.001"},
            {"id": "fringe_count", "label": "折射率测量移动条纹数 m", "type": "number", "default": 10, "required": True, "step": "1"},
            {"id": "double_grating_density", "label": "Lau双光栅线密度", "unit": "gr/mm", "type": "number", "default": 20, "required": True, "step": "1"},
            {
                "id": "first_missing_order", "label": "观察到的第一缺级级次（选填）", "type": "number",
                "default": "", "required": False, "step": "1",
                "help": "例如第4级首先缺级则填4；系统据此估算透光缝宽占光栅周期的比例。",
            },
        ],
        "tables": [
            {
                "id": "grating", "title": "表1  实验测量衍射角", "required": True,
                "min_rows": 1, "initial_rows": 1,
                "description": "角度可输入十进制度，或“123°30′”“123 30”。",
                "columns": [
                    {"id": "plus_left", "label": "+1级左游标", "unit": "°"},
                    {"id": "plus_right", "label": "+1级右游标", "unit": "°"},
                    {"id": "minus_left", "label": "-1级左游标", "unit": "°"},
                    {"id": "minus_right", "label": "-1级右游标", "unit": "°"},
                ],
                "sample": [{"plus_left": "100°00′", "plus_right": "280°00′", "minus_left": "80°00′", "minus_right": "260°00′"}],
            },
            {
                "id": "lau", "title": "表2  标准样品与待测样品入射角（三次）", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "description": "每块样品均记录条纹移动m条前后的左右游标；系统自动处理0°/360°跨界。",
                "columns": [
                    {"id": "std_start_left", "label": "标准初始左", "unit": "°"},
                    {"id": "std_start_right", "label": "标准初始右", "unit": "°"},
                    {"id": "std_end_left", "label": "标准末态左", "unit": "°"},
                    {"id": "std_end_right", "label": "标准末态右", "unit": "°"},
                    {"id": "unk_start_left", "label": "待测初始左", "unit": "°"},
                    {"id": "unk_start_right", "label": "待测初始右", "unit": "°"},
                    {"id": "unk_end_left", "label": "待测末态左", "unit": "°"},
                    {"id": "unk_end_right", "label": "待测末态右", "unit": "°"},
                ],
                "sample": [
                    {"std_start_left": 100.0, "std_start_right": 280.0, "std_end_left": 110.0, "std_end_right": 290.0, "unk_start_left": 120.0, "unk_start_right": 300.0, "unk_end_left": 127.7, "unk_end_right": 307.7},
                    {"std_start_left": 98.0, "std_start_right": 278.0, "std_end_left": 108.1, "std_end_right": 288.1, "unk_start_left": 118.0, "unk_start_right": 298.0, "unk_end_left": 125.8, "unk_end_right": 305.8},
                    {"std_start_left": 102.0, "std_start_right": 282.0, "std_end_left": 111.9, "std_end_right": 291.9, "unk_start_left": 122.0, "unk_start_right": 302.0, "unk_end_left": 129.7, "unk_end_right": 309.7},
                ],
            },
            {
                "id": "thickness_repeats", "title": "进阶：待测样品厚度重复测量", "required": False,
                "enabled_by_default": False, "min_rows": 3, "initial_rows": 3,
                "columns": [{"id": "thickness_mm", "label": "待测样品厚度", "unit": "mm"}],
                "sample": [{"thickness_mm": 1.198}, {"thickness_mm": 1.201}, {"thickness_mm": 1.200}],
            },
            {
                "id": "focal_length", "title": "高阶：利用Lau效应测量透镜焦距", "required": False,
                "enabled_by_default": False, "min_rows": 1, "initial_rows": 1,
                "columns": [
                    {"id": "z0_mm", "label": "双光栅间距 z₀", "unit": "mm"},
                    {"id": "fringe_spacing_mm", "label": "Lau条纹间距 s", "unit": "mm"},
                ],
                "sample": [{"z0_mm": 50.0, "fringe_spacing_mm": 0.50}],
            },
        ],
    
        "formulas": get_formulas("exp38"),
        "variables": get_variables("exp38"),
        "table_theory": get_table_theory("exp38"),}


def _row_angle(row, key, row_index):
    return parse_angle(row.get(key, ""), f"第{row_index}行{key}")


def _lau_factor(theta_deg, refractive_index):
    theta = math.radians(theta_deg)
    sin_theta = math.sin(theta)
    denominator = refractive_index ** 2 - sin_theta ** 2
    if denominator <= 0:
        raise OpticsInputError("折射率与角度组合不满足公式(6)的定义域")
    root = math.sqrt((1.0 - sin_theta ** 2) / denominator)
    return sin_theta * (1.0 - root)


def handle_structured(workpath, payload):
    try:
        grating_rows = get_rows(payload, "grating", required=True, min_rows=1)
        lau_rows = get_rows(payload, "lau", required=True, min_rows=3)
        wavelength_nm = get_parameter(payload, "wavelength_nm", 589.3, True)
        standard_index = get_parameter(payload, "standard_index", 1.5263, True)
        standard_thickness = get_parameter(payload, "standard_thickness_mm", None, True)
        unknown_thickness = get_parameter(payload, "unknown_thickness_mm", None, True)
        fringe_count = get_parameter(payload, "fringe_count", 10, True)
        density = get_parameter(payload, "double_grating_density", 20, True)
        first_missing = get_parameter(payload, "first_missing_order", None, False)
        if min(wavelength_nm, standard_index, standard_thickness, unknown_thickness, fringe_count, density) <= 0:
            raise OpticsInputError("波长、折射率、厚度、条纹数和线密度都必须为正数")

        grating_results = []
        for index, row in enumerate(grating_rows, 1):
            plus_left = _row_angle(row, "plus_left", index)
            plus_right = _row_angle(row, "plus_right", index)
            minus_left = _row_angle(row, "minus_left", index)
            minus_right = _row_angle(row, "minus_right", index)
            theta_left = circular_difference(plus_left, minus_left) / 2.0
            theta_right = circular_difference(plus_right, minus_right) / 2.0
            theta_mean = (theta_left + theta_right) / 2.0
            if not 0 < theta_mean < 90:
                raise OpticsInputError("一级衍射角应在0°到90°之间")
            grating_constant = wavelength_nm * 1e-6 / math.sin(math.radians(theta_mean))
            grating_results.append((plus_left, plus_right, minus_left, minus_right, theta_left, theta_right, theta_mean, grating_constant))
        mean_theta = float(np.mean([item[6] for item in grating_results]))
        mean_grating_constant = float(np.mean([item[7] for item in grating_results]))

        standard_angles = []
        unknown_angles = []
        lau_report_rows = []
        for index, row in enumerate(lau_rows, 1):
            values = {key: _row_angle(row, key, index) for key in [
                "std_start_left", "std_start_right", "std_end_left", "std_end_right",
                "unk_start_left", "unk_start_right", "unk_end_left", "unk_end_right",
            ]}
            std_left = circular_difference(values["std_start_left"], values["std_end_left"])
            std_right = circular_difference(values["std_start_right"], values["std_end_right"])
            unk_left = circular_difference(values["unk_start_left"], values["unk_end_left"])
            unk_right = circular_difference(values["unk_start_right"], values["unk_end_right"])
            std_angle = (std_left + std_right) / 2.0
            unk_angle = (unk_left + unk_right) / 2.0
            standard_angles.append(std_angle)
            unknown_angles.append(unk_angle)
            lau_report_rows.append([
                index, f"{std_left:.5f}", f"{std_right:.5f}", f"{std_angle:.5f}",
                f"{unk_left:.5f}", f"{unk_right:.5f}", f"{unk_angle:.5f}",
            ])
        standard_angles = np.asarray(standard_angles)
        unknown_angles = np.asarray(unknown_angles)
        mean_standard_angle = float(np.mean(standard_angles))
        mean_unknown_angle = float(np.mean(unknown_angles))

        target = standard_thickness * _lau_factor(mean_standard_angle, standard_index) / unknown_thickness
        max_target = math.sin(math.radians(mean_unknown_angle))
        if not 0 < target < max_target:
            raise OpticsInputError("标准与待测样品的数据无法在公式(6)中得到物理解，请核对厚度和转角")

        def equation(index_value):
            return _lau_factor(mean_unknown_angle, index_value) - target

        unknown_index = float(scipy.optimize.brentq(equation, 1.0000001, 5.0))
        ua_std_angle = float(np.std(standard_angles, ddof=1) / math.sqrt(len(standard_angles)))
        ua_unk_angle = float(np.std(unknown_angles, ddof=1) / math.sqrt(len(unknown_angles)))

        thickness_rows = get_rows(payload, "thickness_repeats")
        thickness_ua = None
        if thickness_rows:
            repeated_thickness = numeric_column(thickness_rows, "thickness_mm", "待测样品厚度")
            if np.any(repeated_thickness <= 0):
                raise OpticsInputError("待测样品厚度必须为正数")
            unknown_thickness = float(np.mean(repeated_thickness))
            thickness_ua = float(np.std(repeated_thickness, ddof=1) / math.sqrt(len(repeated_thickness)))
            target = standard_thickness * _lau_factor(mean_standard_angle, standard_index) / unknown_thickness
            unknown_index = float(scipy.optimize.brentq(
                lambda value: _lau_factor(mean_unknown_angle, value) - target, 1.0000001, 5.0
            ))

        warnings = []
        if len(lau_rows) != 3:
            warnings.append(f"指导书要求标准和待测样品各测量3次；当前输入了{len(lau_rows)}次。")
        vernier_differences = []
        for row in lau_report_rows:
            vernier_differences.extend([abs(float(row[1]) - float(row[2])), abs(float(row[4]) - float(row[5]))])
        if max(vernier_differences) > 0.2:
            warnings.append("部分左右游标计算的转角相差超过0.2°，请检查游标读数。")

        duty_text = "未输入第一缺级级次，未计算占空比。"
        if first_missing is not None:
            if first_missing <= 1 or not float(first_missing).is_integer():
                raise OpticsInputError("第一缺级级次应为大于1的整数")
            duty_ratio = 1.0 / first_missing
            duty_text = f"若第{int(first_missing)}级首先缺级，则透光缝宽/光栅周期约为 {duty_ratio:.5f}。"

        focal_rows = get_rows(payload, "focal_length")
        focal_results = []
        grating_period = 1.0 / density
        for index, row in enumerate(focal_rows, 1):
            z0 = float(row.get("z0_mm", ""))
            spacing = float(row.get("fringe_spacing_mm", ""))
            if z0 <= 0 or spacing <= 0:
                raise OpticsInputError("焦距测量中的z₀和条纹间距必须为正数")
            focal_results.append((z0, spacing, spacing * z0 / grating_period))

        summary = [
            f"一级衍射角平均值 θ = {mean_theta:.6f}°",
            f"待测光栅常数 d = {mean_grating_constant:.8f} mm（约 {1/mean_grating_constant:.2f} gr/mm）",
            f"标准样品平均转角 θ = {mean_standard_angle:.6f}°，A类标准不确定度 {ua_std_angle:.6f}°",
            f"待测样品平均转角 θ₁ = {mean_unknown_angle:.6f}°，A类标准不确定度 {ua_unk_angle:.6f}°",
            f"比较法求得待测样品折射率 n = {unknown_index:.6f}",
            duty_text,
        ]
        if thickness_ua is not None:
            summary.append(f"待测厚度平均值 = {unknown_thickness:.6f} mm，A类标准不确定度 = {thickness_ua:.6f} mm")
        for z0, spacing, focal in focal_results:
            summary.append(f"z₀={z0:.4f} mm、s={spacing:.4f} mm时，透镜焦距 f={focal:.4f} mm")

        doc = create_document(name(), "光栅衍射和双光栅Lau效应实验")
        grating_table = [[
            f"{item[0]:.5f}", f"{item[1]:.5f}", f"{item[2]:.5f}", f"{item[3]:.5f}",
            f"{item[4]:.5f}", f"{item[5]:.5f}", f"{item[6]:.5f}", f"{item[7]:.8f}",
        ] for item in grating_results]
        add_table(doc, "表1  衍射角与光栅常数", [
            "+1左/°", "+1右/°", "-1左/°", "-1右/°", "θ左/°", "θ右/°", "平均θ/°", "d/mm"
        ], grating_table)
        add_table(doc, "表2  Lau效应比较法转角", [
            "次数", "标准左/°", "标准右/°", "标准平均/°", "待测左/°", "待测右/°", "待测平均/°"
        ], lau_report_rows)
        add_summary(doc, summary)
        add_text_section(doc, "缺级现象与占空比分析", get_text(payload, "missing_order_observation"))
        add_text_section(doc, "两光栅间距的条纹形貌比较", get_text(payload, "distance_comparison"))
        add_text_section(doc, "实验思考与讨论", get_text(payload, "discussion"))

        configure_plotting()
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        trial = np.arange(1, len(standard_angles) + 1)
        width = 0.36
        ax.bar(trial - width / 2, standard_angles, width, color="#4472C4", label="标准样品")
        ax.bar(trial + width / 2, unknown_angles, width, color="#E67E22", label="待测样品")
        ax.set_xticks(trial)
        ax.set_xlabel("测量次数")
        ax.set_ylabel(f"移动{fringe_count:.0f}条条纹所需转角 / °")
        ax.set_title("标准样品与待测样品转角比较")
        ax.grid(True, axis="y", linestyle="--", alpha=0.35)
        ax.legend()
        chart = save_figure(fig, workpath, "exp38_lau_angle_comparison.png")
        charts = [{"filename": chart, "title": "Lau效应标准样品与待测样品转角比较"}]
        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, OpticsInputError):
            return error_result(exc)
        return error_result(OpticsInputError(f"输入数据格式不正确：{exc}"))
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
