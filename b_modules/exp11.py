"""半导体温度计实验模块
===================
一级大物电磁学实验 —— 半导体温度计的设计与定标

原理：
  NTC 热敏电阻阻值随温度升高而指数下降；将其接入非平衡电桥的一个桥臂，
  温度变化引起电桥失衡，微安表电流随之变化，从而把电流刻度转换为温度读数。

页面结构（四个区块纵向排列，对应指导书 Tab1~Tab4）：
  表 1【基础内容】R-T 特性表（按台号自动填充）+ 电路参数计算（式3）
  表 2【提升内容-标定】温度计表盘标定（I-T 数据 + 三次多项式拟合）
  表 3【提升内容-测试】测温误差分析（局部线性插值反算 + 多项式反算对比）
  提交后汇总：台号信息 / 电路参数 / 标定拟合 / 测温结果

硬编码数据：20 个台号的微安表内阻 RG 和热敏电阻 R-T 特性（21 个温度点）。
"""

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data

# ─────────────────────────────────────────────
# 硬编码数据（20 个台号，不得从外部读取）
# ─────────────────────────────────────────────
# 温度点共 21 个（°C）
T_LIST = [20.0, 22.5, 25.0, 27.5, 30.0, 32.5, 35.0, 37.5, 40.0, 42.5,
          45.0, 47.5, 50.0, 52.5, 55.0, 57.5, 60.0, 62.5, 65.0, 67.5, 70.0]

# 标定温度点（每隔 5°C，共 11 个）
CAL_T = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0]

# 台号数据：RG 为微安表内阻 (Ω)，RT 为 21 个温度点对应的热敏电阻阻值 (Ω)
EXPERIMENT_DATA = {
    "1": {"RG": 5252, "RT": [3700, 3301, 2973, 2677, 2485, 2063, 1958, 1753, 1589, 1432, 1321, 1300, 1275, 1155, 1051, 942, 841, 774, 703, 623, 578]},
    "2": {"RG": 3453, "RT": [3693, 3299, 2870, 2475, 2358, 2074, 1897, 1717, 1547, 1386, 1253, 1161, 1053, 961, 873, 790, 729, 648, 601, 549, 504]},
    "3": {"RG": 5233, "RT": [3652, 3280, 2776, 2455, 2294, 2040, 1849, 1675, 1530, 1401, 1253, 1142, 1056, 956, 871, 797, 726, 662, 606, 557, 506]},
    "4": {"RG": 5385, "RT": [3712, 3314, 2879, 2443, 2242, 2023, 1867, 1676, 1520, 1387, 1246, 1132, 1033, 951, 869, 783, 724, 652, 594, 549, 502]},
    "5": {"RG": 5278, "RT": [3690, 3309, 2649, 2436, 2236, 2028, 1859, 1680, 1511, 1372, 1265, 1151, 1043, 946, 859, 771, 707, 648, 585, 542, 498]},
    "6": {"RG": 5264, "RT": [3732, 3297, 3006, 2726, 2404, 2121, 1982, 1792, 1604, 1457, 1312, 1187, 1087, 976, 889, 806, 731, 664, 605, 550, 508]},
    "7": {"RG": 5234, "RT": [3684, 3305, 2570, 2347, 2187, 1867, 1802, 1758, 1464, 1335, 1210, 1105, 1007, 899, 824, 752, 689, 621, 573, 517, 480]},
    "8": {"RG": 5279, "RT": [3651, 3283, 2744, 2624, 2324, 2109, 1937, 1679, 1512, 1402, 1263, 1147, 1055, 957, 858, 787, 714, 645, 591, 540, 497]},
    "9": {"RG": 5267, "RT": [3819, 3386, 3013, 2704, 2426, 2164, 1950, 1753, 1594, 1414, 1290, 1166, 1063, 960, 879, 793, 729, 664, 604, 549, 514]},
    "10": {"RG": 5244, "RT": [3630, 3304, 2919, 2627, 2357, 2117, 1937, 1710, 1547, 1380, 1281, 1153, 1050, 939, 857, 784, 716, 651, 596, 540, 506]},
    "11": {"RG": 5546, "RT": [3600, 3291, 2966, 2661, 2374, 2113, 1924, 1710, 1551, 1389, 1269, 1153, 1046, 947, 861, 789, 711, 656, 600, 544, 501]},
    "12": {"RG": 5291, "RT": [3508, 3193, 2851, 2583, 2304, 2046, 1852, 1688, 1533, 1400, 1256, 1150, 1038, 947, 848, 775, 692, 637, 575, 534, 483]},
    "13": {"RG": 3455, "RT": [3700, 3130, 2797, 2498, 2232, 1988, 1806, 1676, 1472, 1377, 1266, 1132, 1028, 921, 833, 779, 710, 640, 588, 535, 490]},
    "14": {"RG": 3462, "RT": [3520, 3147, 2852, 2609, 2333, 2067, 1872, 1714, 1529, 1390, 1255, 1147, 1037, 942, 853, 780, 703, 641, 584, 540, 485]},
    "15": {"RG": 3422, "RT": [3491, 3152, 2778, 2501, 2222, 2036, 1815, 1623, 1500, 1349, 1225, 1140, 1014, 930, 840, 765, 682, 639, 572, 530, 481]},
    "16": {"RG": 2914, "RT": [3636, 3255, 2921, 2622, 2336, 2086, 1878, 1678, 1521, 1370, 1230, 1107, 1003, 920, 845, 762, 698, 638, 583, 530, 490]},
    "17": {"RG": 2922, "RT": [3445, 3097, 2800, 2504, 2246, 2032, 1860, 1694, 1535, 1374, 1260, 1118, 1030, 944, 857, 760, 706, 651, 595, 543, 488]},
    "18": {"RG": 3410, "RT": [3562, 3105, 2700, 2412, 2162, 1918, 1756, 1620, 1450, 1320, 1220, 1088, 995, 902, 819, 754, 691, 631, 578, 533, 485]},
    "19": {"RG": 3512, "RT": [3302, 3008, 2730, 2425, 2173, 1952, 1767, 1602, 1451, 1303, 1182, 1090, 990, 908, 830, 754, 684, 626, 571, 524, 478]},
    "20": {"RG": 3440, "RT": [3432, 3130, 2817, 2550, 2312, 2088, 1878, 1656, 1490, 1360, 1231, 1110, 1018, 930, 840, 770, 695, 646, 596, 542, 491]},
}


def name():
    return "半导体温度计"


def handle(workpath, extension):
    """旧版 CSV 接口：保留兼容占位。"""
    try:
        excelpath = workpath + name() + '.' + extension
        if os.path.exists(excelpath):
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
# 固定参数（指导书规定，不可修改，展示在台号下方）
# ─────────────────────────────────────────────
_T1 = 20.0      # 测温下限 °C
_T2 = 70.0      # 测温上限 °C
_V_CD = 1.0     # 桥端电压 V
_I_G_UA = 50.0  # 满量程电流 μA
_E = 1.5        # 电源电动势 V


def _sig6(x):
    """6 位有效数字格式化。"""
    if x is None or x == 0:
        return "0"
    return f"{x:.6g}"


def _sci_latex(x):
    """科学计数法数值 → LaTeX 形式，如 5.0e-05 → 5.0\\times 10^{-5}。"""
    mant, exp = f"{x:.1e}".split("e")
    return f"{mant}\\times 10^{{{int(exp)}}}"


def _poly_eval(coeffs, x):
    """coeffs = [a0, a1, a2, a3]，求 a0 + a1·x + a2·x² + a3·x³。"""
    return coeffs[0] + coeffs[1] * x + coeffs[2] * x * x + coeffs[3] * x ** 3


def _cubic_fit(xs, ys):
    """三次多项式最小二乘拟合，返回 (coeffs=[a0,a1,a2,a3], R²)。"""
    coeffs = np.polyfit(xs, ys, 3)          # [a3, a2, a1, a0]
    a3, a2, a1, a0 = coeffs
    y_pred = np.polyval(coeffs, xs)
    ss_res = float(sum((ys[i] - y_pred[i]) ** 2 for i in range(len(xs))))
    y_mean = sum(ys) / len(ys)
    ss_tot = float(sum((y - y_mean) ** 2 for y in ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return [a0, a1, a2, a3], r2


def _interp_back(cal_pts, I_meas):
    """局部线性插值反算温度。cal_pts 为 [(T, I), ...]。

    返回 (T_测, 是否超出标定范围)。
    """
    pts = sorted(cal_pts, key=lambda p: p[1])
    I_min, I_max = pts[0][1], pts[-1][1]
    out_of_range = I_meas < I_min or I_meas > I_max
    if I_meas <= I_min:
        (T_a, I_a), (T_b, I_b) = pts[0], pts[1]
    elif I_meas >= I_max:
        (T_a, I_a), (T_b, I_b) = pts[-2], pts[-1]
    else:
        for k in range(len(pts) - 1):
            if pts[k][1] <= I_meas <= pts[k + 1][1]:
                (T_a, I_a), (T_b, I_b) = pts[k], pts[k + 1]
                break
    if I_b == I_a:
        return T_a, out_of_range
    T_meas = T_a + (T_b - T_a) * (I_meas - I_a) / (I_b - I_a)
    return T_meas, out_of_range


def _poly_back(coeffs, I_meas, lo=20.0, hi=70.0):
    """二分法数值求解 I(T) = I_meas。无解时返回端点估计值。"""
    def f(x):
        return _poly_eval(coeffs, x) - I_meas

    f_lo, f_hi = f(lo), f(hi)
    if f_lo * f_hi > 0:
        # 区间内无根：返回更接近的端点
        return lo if abs(f_lo) < abs(f_hi) else hi
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    # 示例数据：表1 用台号 1 的 R-T 特性；表2 用 CSV 的 11 个标定电流；表3 用插值电流
    station1 = EXPERIMENT_DATA["1"]
    sample_rt = [[formatted(T_LIST[i], 1), str(station1["RT"][i])] for i in range(len(T_LIST))]
    cal_i = load_sample_data("exp11", "半导体温度计")
    i_values = [row[0] for row in cal_i if row and row[0]]
    sample_cal = []
    for i, t_cal in enumerate(CAL_T):
        rt_idx = max(0, min(int(round((t_cal - 20.0) / 2.5)), len(station1["RT"]) - 1))
        sample_cal.append([
            formatted(t_cal, 1),
            str(station1["RT"][rt_idx]),
            i_values[i] if i < len(i_values) else "",
        ])
    sample_test = [
        ["1", "32", "14.4"],
        ["2", "58", "41.3"],
    ]

    tables = [
        make_table(
            "table1", "【基础内容】表1  热敏电阻 R-T 特性（按台号自动填充）",
            [
                "T (°C)",      # c0 只读
                "R_T (Ω)",     # c1 只读（按台号自动查表）
            ],
            sample=sample_rt,
            readonly=(0, 1),
            initial_rows=21,
            chart={
                "x_column": "c0",
                "y_column": "c1",
                "x_label": "T (°C)",
                "y_label": "R_T (Ω)",
                "title": "热敏电阻温度-阻值特性曲线",
                "fit": "exponential",
            },
            description="选择台号后，21 个温度点的阻值由该台号的硬编码 R-T 特性表自动填充。"
                        "点击本表下方的「提交计算」即按式(3)计算桥臂电阻 R1=R2、R3，"
                        "无需等全部实验完成。提交后生成 R-T 特性曲线图。",
        ),
        make_table(
            "table2", "【提升内容-标定】表2  温度计表盘标定（I-T 数据）",
            [
                "T (°C)",      # c0 只读
                "R_T (Ω)",     # c1 只读（自动查表）
                "I (μA)",      # c2 用户填写
            ],
            sample=sample_cal,
            readonly=(0, 1),
            initial_rows=11,
            description="温度点固定为每隔 5°C（20～70°C，共 11 个点）。"
                        "T 与 R_T 列按台号自动填充，只需填写微安表电流 I。"
                        "点击本表下方的「提交计算」：满 5 组数据后做三次多项式拟合 "
                        "I = a0 + a1·T + a2·T² + a3·T³。",
        ),
        make_table(
            "table3", "【提升内容-测试】表3  温度计测温误差分析",
            [
                "测试点",            # c0 只读
                "T_标 (°C)",         # c1 只读（32 / 58）
                "I_测 (μA)",         # c2 用户填写
                "T_测 (°C)",         # c3 只读（局部线性插值反算）
                "ΔT (°C)",           # c4 只读（绝对误差）
                "相对误差 δ(%)",      # c5 只读（按摄氏温度）
            ],
            sample=sample_test,
            readonly=(0, 1, 3, 4, 5),
            initial_rows=2,
            description="用制作好的温度计测量恒温水浴的 32°C 和 58°C 两个标准点，"
                        "记录微安表读数。反算温度采用标定数据的局部线性插值，"
                        "点击本表下方的「提交计算」即给出误差分析结果"
                        "（含三次多项式数值反算对比）。",
        ),
    ]
    # 每个表格下方独立的「提交计算」按钮（渐进计算，无需等全部测完）
    for table in tables:
        table["calc"] = {"label": "提交计算"}
    # 表 1 的按钮同时生成 R-T 特性曲线
    tables[0]["calc"]["label"] = "提交计算并生成 R-T 曲线"

    return make_schema(
        (
            "本实验利用热敏电阻设计与定标半导体温度计。请测量热敏电阻的 R–T 特性（按实验台号）、"
            "表盘标定的 I–T 数据，并完成测温误差分析。调平衡时不要开启搅拌与加热。"
        ),
        tables,
        parameters=[
            {"id": "station", "label": "实验台号（1~20）", "default": "1",
             "note": f"测温下限 T1 = {_T1:g} ℃，测温上限 T2 = {_T2:g} ℃；"
                     f"桥端电压 V_CD = {_V_CD:g} V；满量程电流 I_G = {_I_G_UA:g} μA；"
                     f"电源电动势 E = {_E:g} V（以上为固定值）"},
        ],
        analysis_hints="选择实验台号后，表 1 自动填充该台号的 R-T 特性；"
                       "每个表格下方都有独立的「提交计算」按钮，可分段计算，"
                       "无需等全部实验完成。表 1 计算桥臂电阻 R1=R2、R3；"
                       "表 2 填电流后做三次多项式标定拟合；"
                       "表 3 填实测电流后自动用局部线性插值反算温度并给出误差（含多项式反算对比）。",
        preview_enabled=True,
        table_theory=get_table_theory("exp11"),
        report_enabled=False,
        parameters_sample={
            "station": "1",
        },
    )


def preview(payload):
    """实时计算：台号数据填充、电路参数、标定拟合、反算温度与误差。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})
    fit_notes = {}
    enriched = dict(params)
    warnings = []

    # ── 台号与电路参数 ──
    station_raw = as_number(params.get("station"))
    station = int(station_raw) if station_raw is not None else 1
    if station not in range(1, 21):
        station = 1
        warnings.append("台号应在 1~20 之间，已按台号 1 处理")
    data = EXPERIMENT_DATA[str(station)]
    RG = data["RG"]
    RT_LIST = data["RT"]
    RT1 = RT_LIST[0]    # 20°C
    RT2 = RT_LIST[-1]   # 70°C

    V_CD = as_number(params.get("V_CD")) or _V_CD
    I_G_uA = as_number(params.get("I_G")) or _I_G_UA
    I_G = I_G_uA * 1e-6

    enriched.update({"_station": station, "_RG": RG, "_RT1": RT1, "_RT2": RT2})

    # ── 表 1：按台号填充 R-T 特性 + 电路参数计算（式3）──
    t1_rows = tables.get("table1", [])
    for i, row in enumerate(t1_rows[:len(T_LIST)]):
        row["c0"] = formatted(T_LIST[i], 1)
        row["c1"] = str(RT_LIST[i])

    term1 = (2 * V_CD / I_G) * (0.5 - RT2 / (RT1 + RT2))
    term2 = 2 * (RG + RT1 * RT2 / (RT1 + RT2))
    R1 = term1 - term2
    R3 = RT1
    enriched.update({"_R1": R1, "_R3": R3})
    rt_par = RT1 * RT2 / (RT1 + RT2)
    fit_notes["table1"] = [
        f"台号 {station}：$R_G = {RG}\\,\\Omega$，"
        f"$R_{{T1}}(20^{{\\circ}}\\mathrm{{C}}) = {RT1}\\,\\Omega$，"
        f"$R_{{T2}}(70^{{\\circ}}\\mathrm{{C}}) = {RT2}\\,\\Omega$",
        "式(3) 代入过程：",
        r"$$R_1 = R_2 = \frac{2V_{CD}}{I_G}\left(\frac{1}{2} - \frac{R_{T2}}{R_{T1}+R_{T2}}\right) - 2\left(R_G + \frac{R_{T1}R_{T2}}{R_{T1}+R_{T2}}\right)$$",
        rf"$$= \frac{{2\times {V_CD:g}}}{{{_sci_latex(I_G)}}} \times \left(0.5 - \frac{{{RT2}}}{{{RT1 + RT2}}}\right) - 2 \times \left({RG} + {rt_par:.1f}\right)$$",
        rf"$$= {term1:.1f} - {term2:.1f} = {R1:.1f}\ \Omega$$",
        rf"★ $R_1 = R_2 \approx {round(R1)}\ \Omega$（实际可取比计算值略小的整数）；$R_3 = R_{{T1}} = {R3}\ \Omega$",
    ]

    # ── 各表独立的「提交计算」结果（纯文本，供表格下方按钮显示）──
    calc_results = {
        "table1": {
            "lines": [
                f"台号 {station}，微安表内阻 R_G = {RG} Ω",
                f"R_T1(20 ℃) = {RT1} Ω，R_T2(70 ℃) = {RT2} Ω",
                f"R1 = R2 ≈ {round(R1)} Ω（计算值 {R1:.1f} Ω，实际可取比计算值略小的整数）",
                f"R3 = R_T1 = {R3} Ω",
            ],
            # 供前端直接在「提交计算」结果框内展示 R-T 特性曲线
            "chart": {
                "title": f"热敏电阻温度-阻值特性曲线（台号{station}）",
                "x_label": "T (°C)",
                "y_label": "R_T (Ω)",
                "x": T_LIST,
                "y": RT_LIST,
            },
        },
    }

    # ── 表 2：填充 T / R_T，收集 (T, I) 标定数据并拟合 ──
    t2_rows = tables.get("table2", [])
    cal_pts = []
    for i, row in enumerate(t2_rows[:len(CAL_T)]):
        T_cal = CAL_T[i]
        row["c0"] = formatted(T_cal, 1)
        rt_idx = int(round((T_cal - 20.0) / 2.5))
        rt_idx = max(0, min(rt_idx, len(RT_LIST) - 1))
        row["c1"] = str(RT_LIST[rt_idx])
        I_val = as_number(row.get("c2"))
        if I_val is not None:
            cal_pts.append((T_cal, I_val))

    coeffs = None
    if len(cal_pts) >= 5:
        coeffs, r2_cal = _cubic_fit([p[0] for p in cal_pts], [p[1] for p in cal_pts])
        enriched.update({"_coeffs": coeffs, "_r2_cal": r2_cal, "_cal_pts": cal_pts})
        fit_notes["table2"] = [
            f"三次多项式拟合（{len(cal_pts)} 个有效点）：",
            f"I = {_sig6(coeffs[0])} + {_sig6(coeffs[1])}·T + {_sig6(coeffs[2])}·T² + {_sig6(coeffs[3])}·T³",
            f"相关系数 R² = {r2_cal:.4f}",
        ]
        calc_results["table2"] = {"lines": list(fit_notes["table2"])}
    elif cal_pts:
        fit_notes["table2"] = [f"已输入 {len(cal_pts)} 组数据，满 5 组后自动开始拟合。"]
        calc_results["table2"] = {"lines": list(fit_notes["table2"])}
    else:
        calc_results["table2"] = {
            "lines": ["请先在表2填写各温度点的微安表电流 I（可点「填入本表全部示例数据」）。"]}

    # ── 表 3：反算温度与误差 ──
    t3_rows = tables.get("table3", [])
    test_std = [32.0, 58.0]
    test_results = []
    calc_table3_lines = []
    for i, row in enumerate(t3_rows[:2]):
        row["c0"] = str(i + 1)
        row["c1"] = formatted(test_std[i], 1)
        T_std = test_std[i]
        I_meas = as_number(row.get("c2"))
        if I_meas is None:
            row["c3"] = row["c4"] = row["c5"] = ""
            continue

        note_lines = []
        if len(cal_pts) >= 2:
            T_lin, out_of_range = _interp_back(cal_pts, I_meas)
            if out_of_range:
                warnings.append(f"测试点 {i + 1}：电流超出标定范围，结果不可靠（已用端点外推）")
        else:
            T_lin = None
            note_lines.append("表 2 至少需要 2 组标定数据才能反算温度")

        T_poly = _poly_back(coeffs, I_meas) if coeffs is not None else None

        if T_lin is not None:
            dT = abs(T_lin - T_std)
            rel_C = dT / T_std * 100
            rel_K = dT / (T_std + 273.15) * 100
            row["c3"] = formatted(T_lin, 2)
            row["c4"] = formatted(dT, 2)
            row["c5"] = formatted(rel_C, 2)
            line = f"测试点 {i + 1}（T_标 = {T_std:.1f}°C，I_测 = {I_meas:.2f} μA）：" \
                   f"局部线性反算 T_测 = {T_lin:.2f}°C，ΔT = {dT:.2f}°C，" \
                   f"相对误差 = {rel_C:.2f}%（按摄氏）/ {rel_K:.3f}%（按开尔文）"
            if T_poly is not None:
                line += f"；多项式反算 T = {T_poly:.2f}°C"
            fit_notes.setdefault("table3", []).append(line)
            calc_table3_lines.append(line)
            test_results.append({"T_std": T_std, "I": I_meas, "T_lin": T_lin,
                                 "T_poly": T_poly, "rel_C": rel_C})
        else:
            row["c3"] = row["c4"] = row["c5"] = ""
        if note_lines:
            fit_notes.setdefault("table3", []).extend(note_lines)
            calc_table3_lines.extend(note_lines)

    if not calc_table3_lines:
        calc_table3_lines.append("请先在表3填写测试点电流 I_测（需表2至少 2 组标定数据才能反算温度）。")
    calc_results["table3"] = {"lines": calc_table3_lines}

    enriched["_test_results"] = test_results
    for warning in warnings:
        fit_notes.setdefault("table3", []).append(f"⚠ {warning}")
    enriched["_warnings"] = warnings

    return {
        "tables": tables,
        "parameters": enriched,
        "fit_notes": fit_notes,
        "calc_results": calc_results,
    }


# ─────────────────────────────────────────────
# 图表生成
# ─────────────────────────────────────────────
def _zhfont():
    try:
        return matplotlib.font_manager.FontProperties(
            fname=os.path.join(os.path.dirname(__file__), "SourceHanSansSC-Regular.otf"))
    except Exception:
        return matplotlib.font_manager.FontProperties()


def _generate_RT_chart(params, workpath):
    """图1：热敏电阻温度-阻值特性曲线（台号X）。"""
    station = params.get("_station", 1)
    RT_LIST = EXPERIMENT_DATA[str(station)]["RT"]

    zhfont = _zhfont()
    fig, ax = plt.subplots(figsize=(9, 5.5))

    # 平滑曲线（三次样条插值）
    T_fine = np.linspace(T_LIST[0], T_LIST[-1], 300)
    try:
        from scipy.interpolate import CubicSpline
        cs = CubicSpline(T_LIST, RT_LIST)
        ax.plot(T_fine, cs(T_fine), '-', color='tab:blue', linewidth=1.5,
                label='平滑曲线', zorder=2)
    except Exception:
        ax.plot(T_LIST, RT_LIST, '-', color='tab:blue', linewidth=1.5, zorder=2)

    ax.plot(T_LIST, RT_LIST, 'o', color='tab:blue', markersize=5,
            label='数据点', zorder=3)

    # 标注 20°C 与 70°C 关键点
    ax.annotate(f'20°C: {RT_LIST[0]} Ω',
                xy=(T_LIST[0], RT_LIST[0]), xytext=(T_LIST[0] + 4, RT_LIST[0] * 0.92),
                fontsize=9, color='darkred', fontproperties=zhfont,
                arrowprops=dict(arrowstyle='->', color='darkred'))
    ax.annotate(f'70°C: {RT_LIST[-1]} Ω',
                xy=(T_LIST[-1], RT_LIST[-1]), xytext=(T_LIST[-1] - 14, RT_LIST[-1] * 1.9),
                fontsize=9, color='darkred', fontproperties=zhfont,
                arrowprops=dict(arrowstyle='->', color='darkred'))

    ax.set_xlim(18, 72)
    ax.set_xlabel('T (°C)', fontsize=12, fontproperties=zhfont)
    ax.set_ylabel('R_T (Ω)', fontsize=12, fontproperties=zhfont)
    ax.set_title(f'热敏电阻温度-阻值特性曲线（台号{station}）',
                 fontsize=13, fontproperties=zhfont)
    ax.legend(loc='upper right', fontsize=9, prop=zhfont)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    imgpath = os.path.join(workpath, "chart_RT_characteristic.png")
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


def _generate_calibration_chart(params, workpath):
    """图2：温度计标定曲线 I-T（含测试点反查标注）。"""
    coeffs = params.get("_coeffs")
    cal_pts = params.get("_cal_pts", [])
    test_results = params.get("_test_results", [])
    if not cal_pts:
        return None

    zhfont = _zhfont()
    fig, ax = plt.subplots(figsize=(9.5, 6))

    Ts = [p[0] for p in cal_pts]
    Is = [p[1] for p in cal_pts]
    ax.plot(Ts, Is, 'o', color='tab:blue', markersize=6, label='标定数据点', zorder=4)

    # 拟合曲线（或平滑连线）
    T_fine = np.linspace(20.0, 70.0, 300)
    if coeffs is not None:
        I_fine = [_poly_eval(coeffs, t) for t in T_fine]
        ax.plot(T_fine, I_fine, '-', color='tab:blue', linewidth=1.5,
                label='三次多项式拟合曲线', zorder=3)
    else:
        ax.plot(sorted(Ts), [i for _, i in sorted(cal_pts)], '-',
                color='tab:blue', linewidth=1.2, zorder=3)

    # 设计端点标注（实际数据接近 20°C→0μA、70°C→50μA 时）
    I_at_20 = next((p[1] for p in cal_pts if abs(p[0] - 20.0) < 1e-6), None)
    I_at_70 = next((p[1] for p in cal_pts if abs(p[0] - 70.0) < 1e-6), None)
    if I_at_20 is not None and abs(I_at_20 - 0.0) <= 2.5:
        ax.annotate('设计端点：20°C → 0 μA', xy=(20.0, I_at_20),
                    xytext=(23.0, max(Is) * 0.12), fontsize=9, color='green',
                    fontproperties=zhfont, arrowprops=dict(arrowstyle='->', color='green'))
    if I_at_70 is not None and abs(I_at_70 - 50.0) <= 2.5:
        ax.annotate('设计端点：70°C → 50 μA', xy=(70.0, I_at_70),
                    xytext=(55.0, max(Is) * 1.02), fontsize=9, color='green',
                    fontproperties=zhfont, arrowprops=dict(arrowstyle='->', color='green'))

    # 测试点反查标注（读电流 → 反查温度）
    colors = ['tab:orange', 'tab:purple']
    for idx, res in enumerate(test_results[:2]):
        color = colors[idx % len(colors)]
        T_meas, I_meas = res["T_lin"], res["I"]
        ax.plot(T_meas, I_meas, 's', color=color, markersize=8, zorder=5,
                label=f'测试点 {idx + 1}（{res["T_std"]:.0f}°C）')
        ax.plot([0, T_meas], [I_meas, I_meas], '--', color=color, linewidth=1, zorder=2)
        ax.plot([T_meas, T_meas], [0, I_meas], '--', color=color, linewidth=1, zorder=2)
        ax.annotate(f'I = {I_meas:.1f} μA → T_测 = {T_meas:.1f}°C',
                    xy=(T_meas, I_meas), xytext=(T_meas + 1.5, I_meas - max(Is) * 0.1),
                    fontsize=8.5, color=color, fontproperties=zhfont)

    ax.set_xlim(18, 72)
    ax.set_ylim(bottom=0)
    ax.set_xlabel('T (°C)', fontsize=12, fontproperties=zhfont)
    ax.set_ylabel('I (μA)', fontsize=12, fontproperties=zhfont)
    title = f'温度计标定曲线 I-T（台号{params.get("_station", 1)}）'
    if coeffs is not None:
        title += f'，R² = {params.get("_r2_cal", 0):.4f}'
    ax.set_title(title, fontsize=13, fontproperties=zhfont)
    ax.legend(loc='lower right', fontsize=8.5, prop=zhfont)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    imgpath = os.path.join(workpath, "chart_calibration_IT.png")
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


def handle_structured(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    enriched["parameters"] = preview_result["parameters"]

    _schema = schema()
    params = enriched.get("parameters", {})
    charts = []

    # ── 图 1：R-T 特性曲线 ──
    chart_rt = _generate_RT_chart(params, workpath)
    if chart_rt:
        charts.append({
            "filename": "chart_RT_characteristic.png",
            "title": f"热敏电阻温度-阻值特性曲线（台号{params.get('_station', 1)}）",
            "url": chart_rt,
        })

    # ── 图 2：标定曲线 + 测试点 ──
    chart_cal = _generate_calibration_chart(params, workpath)
    if chart_cal:
        charts.append({
            "filename": "chart_calibration_IT.png",
            "title": "温度计标定曲线 I-T（含测试点反查）",
            "url": chart_cal,
        })

    # ── Tab4 结果汇总（卡片式）──
    station = params.get("_station", 1)
    summary_lines = [
        "半导体温度计设计与定标结果：",
        "【台号信息】",
        f"台号 {station}，微安表内阻 R_G = {params.get('_RG', '')} Ω",
        "【电路参数】",
        f"R1 = R2 ≈ {round(params.get('_R1', 0))} Ω（计算值 {params.get('_R1', 0):.1f} Ω，"
        f"实际可取比计算值略小的整数），R3 = {params.get('_R3', '')} Ω",
        f"R_T1(20°C) = {params.get('_RT1', '')} Ω，R_T2(70°C) = {params.get('_RT2', '')} Ω",
    ]
    coeffs = params.get("_coeffs")
    if coeffs is not None:
        summary_lines.extend([
            "【标定拟合】",
            f"I = {_sig6(coeffs[0])} + {_sig6(coeffs[1])}·T + {_sig6(coeffs[2])}·T² "
            f"+ {_sig6(coeffs[3])}·T³，R² = {params.get('_r2_cal', 0):.4f}",
        ])
    test_results = params.get("_test_results", [])
    if test_results:
        summary_lines.append("【测温结果】")
        for res in test_results:
            poly_part = f"（多项式反算 {res['T_poly']:.1f}°C）" if res.get("T_poly") is not None else ""
            summary_lines.append(
                f"{res['T_std']:.0f}°C 点：I = {res['I']:.1f} μA → "
                f"T_测 = {res['T_lin']:.1f}°C{poly_part}，相对误差 = {res['rel_C']:.2f}%"
            )

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        warnings=params.get("_warnings", []),
        charts=charts,
    )
