from head import *
from optics_common import *


def name():
    return "双光栅"


_GRATING_FORMULAS = [{
    "title": "基础内容：衍射光栅常数与占空比",
    "steps": [
        {"note": "光栅方程：", "formula": r"d_g\sin\theta=m\lambda"},
        {"note": "本实验使用一级亮纹（m=1）：", "formula": r"d_g=\frac{\lambda}{\sin\theta}"},
        {"note": "若第k₀级首先缺级，透光缝宽a与光栅周期d_g之比：", "formula": r"\frac{a}{d_g}=\frac{1}{k_0}"},
    ],
}]

_LAU_FORMULAS = [{
    "title": "提升内容：比较法测平行板玻璃折射率",
    "steps": [
        {
            "note": "定义样品转角、折射率对应的几何因子：",
            "formula": r"F(\theta,n)=\sin\theta\left[1-\sqrt{\frac{1-\sin^2\theta}{n^2-\sin^2\theta}}\right]",
        },
        {
            "note": "标准样品与待测样品移动相同条纹数时：",
            "formula": r"d_sF(\theta_s,n_s)=d_uF(\theta_u,n_u)",
        },
        {"note": "代入两块样品厚度、平均转角及标准折射率，数值求解n_u。"},
    ],
}]

_GRATING_VARIABLES = [
    {"symbol": r"d_g", "description": "待测衍射光栅的光栅常数", "unit": "mm"},
    {"symbol": r"\theta", "description": "由+1级和-1级亮纹位置求得的一级衍射角", "unit": "°"},
    {"symbol": r"\lambda", "description": "钠光波长", "unit": "nm"},
    {"symbol": r"k_0", "description": "观察到的第一缺级级次", "unit": "无单位"},
    {"symbol": "a", "description": "光栅透光缝宽", "unit": "mm"},
]

_LAU_VARIABLES = [
    {"symbol": r"d_s,d_u", "description": "标准样品、待测样品厚度", "unit": "mm"},
    {"symbol": r"\theta_s,\theta_u", "description": "移动相同条纹数时两块样品的平均转角", "unit": "°"},
    {"symbol": r"n_s", "description": "标准样品折射率", "unit": "无单位"},
    {"symbol": r"n_u", "description": "待测样品折射率", "unit": "无单位"},
]


def schema():
    return {
        "schema_version": 2,
        "schema_revision": 3,
        "report_enabled": False,
        "description": (
            "本实验完成双光栅实验需要提交的数据处理：基础内容计算光栅常数，并由第一缺级判断占空比；"
            "提升内容记录标准、待测样品各 3 次转角，以比较法计算待测平行板玻璃的折射率。"
        ),
        "parameters": [
            {
                "id": "wavelength_nm", "label": "钠光波长 λ", "unit": "nm", "type": "number",
                "default": 589.3, "required": True, "step": "0.1",
            },
            {
                "id": "first_missing_order", "label": "观察到的第一缺级级次 k₀", "type": "number",
                "default": 4, "required": True, "step": "1",
                "help": "例如第4级首先缺级则填4，系统计算a/d_g=1/k₀。",
            },
            {
                "id": "standard_index", "label": "标准样品折射率 nₛ", "type": "number",
                "default": 1.5263, "required": True, "step": "0.0001",
            },
            {
                "id": "standard_thickness_mm", "label": "标准样品厚度 dₛ", "unit": "mm", "type": "number",
                "default": 1.000, "required": True, "step": "0.001",
            },
            {
                "id": "unknown_thickness_mm", "label": "待测样品厚度 dᵤ", "unit": "mm", "type": "number",
                "default": 1.200, "required": True, "step": "0.001",
            },
            {
                "id": "fringe_count", "label": "折射率测量移动条纹数 m", "type": "number",
                "default": 10, "required": True, "step": "1",
                "help": "指导书建议标准样品和待测样品都测量条纹移动10条时的转角。",
            },
        ],
        "tables": [
            {
                "id": "grating", "title": "表1  一级衍射角与光栅常数", "required": True,
                "min_rows": 1, "initial_rows": 1,
                "description": "角度可输入十进制度，或“123°30′”“123 30”。",
                "columns": [
                    {"id": "plus_left", "label": "+1级左游标 θ", "unit": "°"},
                    {"id": "plus_right", "label": "+1级右游标 θ", "unit": "°"},
                    {"id": "minus_left", "label": "-1级左游标 θ", "unit": "°"},
                    {"id": "minus_right", "label": "-1级右游标 θ", "unit": "°"},
                ],
                "sample": [{
                    "plus_left": "100°00′", "plus_right": "280°00′",
                    "minus_left": "80°00′", "minus_right": "260°00′",
                }],
            },
            {
                "id": "lau", "title": "表2  比较法测平行板玻璃折射率", "required": True,
                "min_rows": 3, "initial_rows": 3,
                "description": (
                    "标准样品和待测样品均记录条纹移动m条前后的左右游标读数，各测量3次；"
                    "系统自动处理0°/360°跨界并计算平均转角。"
                ),
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
        ],
        "formulas": _GRATING_FORMULAS + _LAU_FORMULAS,
        "variables": _GRATING_VARIABLES + _LAU_VARIABLES,
        "table_theory": {
            "grating": {"formulas": _GRATING_FORMULAS, "variables": _GRATING_VARIABLES},
            "lau": {"formulas": _LAU_FORMULAS, "variables": _LAU_VARIABLES},
        },
    }


def _row_angle(row, key, row_index):
    return parse_angle(row.get(key, ""), f"第{row_index}行{key}")


def _lau_factor(theta_deg, refractive_index):
    theta = math.radians(theta_deg)
    sin_theta = math.sin(theta)
    denominator = refractive_index ** 2 - sin_theta ** 2
    if denominator <= 0:
        raise OpticsInputError("折射率与角度组合不满足比较法公式的定义域")
    root = math.sqrt((1.0 - sin_theta ** 2) / denominator)
    return sin_theta * (1.0 - root)


def handle_structured(workpath, payload):
    try:
        grating_rows = get_rows(payload, "grating", required=True, min_rows=1)
        lau_rows = get_rows(payload, "lau", required=True, min_rows=3)
        wavelength_nm = get_parameter(payload, "wavelength_nm", 589.3, True)
        first_missing = get_parameter(payload, "first_missing_order", None, True)
        standard_index = get_parameter(payload, "standard_index", 1.5263, True)
        standard_thickness = get_parameter(payload, "standard_thickness_mm", None, True)
        unknown_thickness = get_parameter(payload, "unknown_thickness_mm", None, True)
        fringe_count = get_parameter(payload, "fringe_count", 10, True)
        if min(wavelength_nm, standard_index, standard_thickness, unknown_thickness, fringe_count) <= 0:
            raise OpticsInputError("波长、折射率、样品厚度和条纹数都必须为正数")
        if first_missing <= 1 or not float(first_missing).is_integer():
            raise OpticsInputError("第一缺级级次应为大于1的整数")
        if not float(fringe_count).is_integer():
            raise OpticsInputError("移动条纹数应为正整数")

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
            grating_results.append((
                plus_left, plus_right, minus_left, minus_right,
                theta_left, theta_right, theta_mean, grating_constant,
            ))
        mean_theta = float(np.mean([item[6] for item in grating_results]))
        mean_grating_constant = float(np.mean([item[7] for item in grating_results]))
        duty_ratio = 1.0 / float(first_missing)

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
            if not 0 < std_angle < 90 or not 0 < unk_angle < 90:
                raise OpticsInputError("标准样品和待测样品的转角都应位于0°到90°之间")
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
            raise OpticsInputError("标准与待测样品数据无法得到物理解，请核对厚度和转角")
        unknown_index = float(scipy.optimize.brentq(
            lambda value: _lau_factor(mean_unknown_angle, value) - target,
            1.0000001,
            5.0,
        ))

        warnings = []
        if len(lau_rows) != 3:
            warnings.append(f"指导书要求标准和待测样品各测量3次；当前输入了{len(lau_rows)}次。")
        vernier_differences = []
        for row in lau_report_rows:
            vernier_differences.extend([
                abs(float(row[1]) - float(row[2])),
                abs(float(row[4]) - float(row[5])),
            ])
        if max(vernier_differences) > 0.2:
            warnings.append("部分左右游标计算的转角相差超过0.2°，请检查游标读数。")

        summary = [
            f"一级衍射角平均值 θ = {mean_theta:.6f}°",
            f"待测光栅常数 d_g = {mean_grating_constant:.8f} mm（约 {1 / mean_grating_constant:.2f} gr/mm）",
            f"第{int(first_missing)}级首先缺级，光栅占空比 a/d_g = {duty_ratio:.5f}",
            f"标准样品移动{int(fringe_count)}条条纹的平均转角 θₛ = {mean_standard_angle:.6f}°",
            f"待测样品移动{int(fringe_count)}条条纹的平均转角 θᵤ = {mean_unknown_angle:.6f}°",
            f"比较法求得待测样品折射率 nᵤ = {unknown_index:.6f}",
        ]

        doc = create_document(name(), "光栅衍射和双光栅Lau效应实验")
        grating_table = [[
            f"{item[0]:.5f}", f"{item[1]:.5f}", f"{item[2]:.5f}", f"{item[3]:.5f}",
            f"{item[4]:.5f}", f"{item[5]:.5f}", f"{item[6]:.5f}", f"{item[7]:.8f}",
        ] for item in grating_results]
        add_table(doc, "表1  衍射角与光栅常数", [
            "+1左/°", "+1右/°", "-1左/°", "-1右/°", "θ左/°", "θ右/°", "平均θ/°", "d_g/mm",
        ], grating_table)
        add_table(doc, "表2  Lau效应比较法转角", [
            "次数", "标准左/°", "标准右/°", "标准平均/°", "待测左/°", "待测右/°", "待测平均/°",
        ], lau_report_rows)
        add_summary(doc, summary)
        return finish_report(doc, workpath, name(), summary, charts=[], warnings=warnings)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, OpticsInputError):
            return error_result(exc)
        return error_result(OpticsInputError(f"输入数据格式不正确：{exc}"))
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
