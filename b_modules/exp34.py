from head import *
from theory_content import get_formulas, get_variables, get_table_theory
from optics_common import *


def name():
    return "光纤传感器"


def _sample_curve(positions, values):
    return [
        {"position_mm": round(float(position), 5), "power": round(float(value), 6)}
        for position, value in zip(positions, values)
    ]


def schema():
    long_x = np.arange(10.0, 11.25, 0.05)
    long_y = 1.0 / (1.0 + ((long_x - 10.0) / 0.55) ** 2)
    transverse_offset = np.arange(0.0, 0.16, 0.01)
    transverse_y = np.exp(-(transverse_offset / 0.085) ** 2)
    reflection_x = np.arange(0.0, 3.01, 0.15)
    reflection_y = (reflection_x + 0.03) * np.exp(-reflection_x / 0.55)
    micro_x = np.arange(5.0, 7.61, 0.13)
    micro_y = np.clip(1.0 - 0.36 * (micro_x - 5.0), 0.03, None)
    return {
        "schema_version": 2,
        "schema_revision": 3,
        "report_enabled": True,
        "description": (
            "本实验研究光纤传感器的传感原理。请按指导书完成纵向与横向透射、反射、微弯、电压和"
            "电流传感的数据处理，系统将根据 7 组原始数据生成 6 类响应曲线；"
            "温度传感属于高阶内容，不在网页中处理。"
        ),
        "parameters": [
            {
                "id": "power_unit", "label": "功率计读数单位", "type": "select", "default": "任意单位",
                "required": True,
                "options": [
                    {"value": "任意单位", "label": "任意单位（保持仪器原读数）"},
                    {"value": "mW", "label": "mW"},
                    {"value": "μW", "label": "μW"},
                    {"value": "nW", "label": "nW"},
                ],
            },
            {
                "id": "crystal_thickness_mm", "label": "电光晶体加电场方向厚度 d", "unit": "mm",
                "type": "number", "default": "", "required": False, "step": "0.01",
                "help": "若要按指导书公式(16)计算理论半波电压，请从晶体规格读取并填写d和L。",
            },
            {
                "id": "crystal_length_mm", "label": "电光晶体通光方向长度 L", "unit": "mm",
                "type": "number", "default": "", "required": False, "step": "0.01",
            },
            {
                "id": "crystal_wavelength_nm", "label": "电压传感实验激光波长 λ", "unit": "nm",
                "type": "number", "default": 650, "required": False, "step": "0.1",
            },
            {
                "id": "ordinary_index", "label": "LiNbO₃普通光折射率 n₀", "type": "number",
                "default": 2.286, "required": False, "step": "0.001",
            },
            {
                "id": "electro_optic_r22_pm_v", "label": "电光系数 r₂₂", "unit": "pm/V",
                "type": "number", "default": 3.4, "required": False, "step": "0.1",
                "help": "指导书给出LiNbO₃的r₂₂=3.4×10⁻¹⁰ cm/V，即3.4 pm/V。",
            },
        ],
        "tables": [
            {
                "id": "transmission_longitudinal", "title": "表1A  透射式纵向位移", "required": True,
                "min_rows": 15, "initial_rows": 25,
                "description": "以功率最大处X₀为起点，指导书建议0.05 mm步长，至少测至1.2 mm。",
                "columns": [{"id": "position_mm", "label": "纵向位置读数", "unit": "mm"}, {"id": "power", "label": "功率"}],
                "sample": _sample_curve(long_x, long_y),
            },
            {
                "id": "transmission_left", "title": "表1B  透射式横向左移", "required": True,
                "min_rows": 10, "initial_rows": 16,
                "description": "以功率最大处y₀为第一行，随后向左每次约0.01 mm。",
                "columns": [{"id": "position_mm", "label": "横向位置读数", "unit": "mm"}, {"id": "power", "label": "功率"}],
                "sample": _sample_curve(10.0 - transverse_offset, transverse_y),
            },
            {
                "id": "transmission_right", "title": "表1C  透射式横向右移", "required": True,
                "min_rows": 10, "initial_rows": 16,
                "description": "以功率最大处y₀为第一行，随后向右每次约0.01 mm。",
                "columns": [{"id": "position_mm", "label": "横向位置读数", "unit": "mm"}, {"id": "power", "label": "功率"}],
                "sample": _sample_curve(10.0 + transverse_offset, transverse_y * 0.995),
            },
            {
                "id": "reflection", "title": "表2  反射式位移传感", "required": True,
                "min_rows": 15, "initial_rows": 21,
                "description": "从探头最接近反射镜处开始，测量到约3 mm；正文建议0.05 mm步长，记录模板标注0.1 mm，请以实际原始记录为准。",
                "columns": [{"id": "position_mm", "label": "纵向位置读数", "unit": "mm"}, {"id": "power", "label": "功率"}],
                "sample": _sample_curve(reflection_x, reflection_y),
            },
            {
                "id": "microbend", "title": "表3  微弯位移传感", "required": True,
                "min_rows": 15, "initial_rows": 21,
                "description": "指导书建议0.05 mm步长、约2.6 mm范围，测到光强接近零。",
                "columns": [{"id": "position_mm", "label": "微弯位移读数", "unit": "mm"}, {"id": "power", "label": "功率"}],
                "sample": _sample_curve(micro_x, micro_y),
            },
            {
                "id": "voltage", "title": "表4  光纤电压传感", "required": True,
                "min_rows": 8, "initial_rows": 15,
                "description": "记录外加电压与接收光功率，曲线相邻极大、极小位置之差用于估算半波电压。",
                "columns": [{"id": "voltage_v", "label": "电压", "unit": "V"}, {"id": "power", "label": "功率"}],
                "sample": [{"voltage_v": value, "power": round(math.sin(math.pi * value / 600) ** 2, 6)} for value in range(0, 701, 50)],
            },
            {
                "id": "current", "title": "表5  光纤电流传感", "required": True,
                "min_rows": 8, "initial_rows": 15,
                "columns": [{"id": "current_a", "label": "电流", "unit": "A"}, {"id": "power", "label": "功率"}],
                "sample": [
                    {"current_a": round(float(value), 2), "power": round(float(0.02 + 0.8 * value ** 2), 6)}
                    for value in np.arange(0, 0.71, 0.05)
                ],
            },
        ],
    
        "formulas": get_formulas("exp34") + [{
            "title": "电光晶体半波电压（指导书公式16）",
            "steps": [
                {"note": "由晶体尺寸和电光参数计算理论半波电压：", "formula": r"V_\pi=\frac{\lambda d}{2n_0^3r_{22}L}"},
                {"note": "实验曲线上，相邻光强极大值和极小值对应的电压差也可用于估算Vπ。"},
            ],
        }],
        "variables": get_variables("exp34") + [
            {"symbol": r"V_\pi", "description": "电光晶体半波电压", "unit": "V"},
            {"symbol": "d", "description": "晶体沿加电场方向的厚度", "unit": "mm"},
            {"symbol": "L", "description": "晶体沿通光方向的长度", "unit": "mm"},
            {"symbol": r"r_{22}", "description": "LiNbO₃电光系数", "unit": "pm/V"},
        ],
        "table_theory": get_table_theory("exp34"),}


def _read_curve(payload, table_id, required=True, min_rows=0, x_key="position_mm", x_label="位置"):
    rows = get_rows(payload, table_id, required=required, min_rows=min_rows)
    if not rows:
        return None
    x = numeric_column(rows, x_key, x_label)
    y = numeric_column(rows, "power", "功率")
    if np.any(y < 0):
        raise OpticsInputError(f"{table_id}中的功率不能为负数")
    order = np.argsort(x)
    return {"rows": rows, "x": x[order], "y": y[order]}


def _curve_summary(label, curve, unit, x_symbol="x", x_unit="mm"):
    x = curve["x"]
    y = curve["y"]
    peak = int(np.argmax(y))
    dx = np.diff(x)
    dy = np.diff(y)
    finite_slopes = dy[np.abs(dx) > 1e-12] / dx[np.abs(dx) > 1e-12]
    max_slope = float(np.max(np.abs(finite_slopes))) if len(finite_slopes) else 0.0
    return (
        f"{label}：峰值{np.max(y):.6g} {unit}位于{x_symbol}={x[peak]:.5g} {x_unit}；"
        f"响应范围{np.max(y)-np.min(y):.6g} {unit}，相邻点最大响应斜率={max_slope:.6g} {unit}/{x_unit}"
    )


def _add_curve_table(doc, title, curve, x_label, x_unit, unit):
    rows = [[f"{x:.6g}", f"{y:.6g}", f"{(y / np.max(curve['y']) if np.max(curve['y']) else 0):.6f}"]
            for x, y in zip(curve["x"], curve["y"])]
    add_table(doc, title, [f"{x_label}/{x_unit}", f"功率/{unit}", "归一化功率"], rows)


def _estimate_half_wave_voltage(curve):
    """用光强曲线中相邻极大/极小点的电压差估算半波电压。"""
    x = curve["x"]
    y = curve["y"]
    extrema = []
    if len(x) >= 2 and not math.isclose(float(y[0]), float(y[1])):
        extrema.append(0)
    for index in range(1, len(x) - 1):
        left = float(y[index] - y[index - 1])
        right = float(y[index + 1] - y[index])
        if left * right < 0:
            extrema.append(index)
    if len(x) >= 2 and not math.isclose(float(y[-1]), float(y[-2])):
        extrema.append(len(x) - 1)
    extrema = sorted(set(extrema))
    if len(extrema) < 2:
        return None, []
    intervals = np.abs(np.diff(x[extrema]))
    intervals = intervals[intervals > 0]
    if not len(intervals):
        return None, []
    return float(np.median(intervals)), [float(value) for value in intervals]


def handle_structured(workpath, payload):
    try:
        power_unit = get_parameter(payload, "power_unit", "任意单位", True, cast=str)
        crystal_thickness = get_parameter(payload, "crystal_thickness_mm", None, False)
        crystal_length = get_parameter(payload, "crystal_length_mm", None, False)
        crystal_wavelength = get_parameter(payload, "crystal_wavelength_nm", 650.0, False)
        ordinary_index = get_parameter(payload, "ordinary_index", 2.286, False)
        electro_optic_r22 = get_parameter(payload, "electro_optic_r22_pm_v", 3.4, False)
        curves = {
            "longitudinal": _read_curve(payload, "transmission_longitudinal", True, 15),
            "left": _read_curve(payload, "transmission_left", True, 10),
            "right": _read_curve(payload, "transmission_right", True, 10),
            "reflection": _read_curve(payload, "reflection", True, 15),
            "microbend": _read_curve(payload, "microbend", True, 15),
        }
        voltage = _read_curve(payload, "voltage", True, 8, "voltage_v", "电压")
        current = _read_curve(payload, "current", True, 8, "current_a", "电流")

        summary = [
            _curve_summary("透射式纵向", curves["longitudinal"], power_unit),
            _curve_summary("透射式横向左移", curves["left"], power_unit),
            _curve_summary("透射式横向右移", curves["right"], power_unit),
            _curve_summary("反射式位移", curves["reflection"], power_unit),
            _curve_summary("微弯位移", curves["microbend"], power_unit),
        ]
        warnings = []
        x0_left = curves["left"]["x"][np.argmax(curves["left"]["y"])]
        x0_right = curves["right"]["x"][np.argmax(curves["right"]["y"])]
        x0 = float((x0_left + x0_right) / 2.0)
        left_displacement = curves["left"]["x"] - x0
        right_displacement = curves["right"]["x"] - x0
        if abs(x0_left - x0_right) > 0.02:
            warnings.append("横向左、右数据的最大功率位置相差超过0.02 mm，请核对两组是否使用同一y₀。")

        half_wave, half_wave_intervals = _estimate_half_wave_voltage(voltage)
        if half_wave is None:
            warnings.append("电压—光强曲线中未识别到至少两个相邻极值，暂不能估算半波电压。")
        else:
            summary.append(
                f"电压传感：由相邻极大、极小位置差估算半波电压 Vπ = {half_wave:.6g} V"
            )
            if len(half_wave_intervals) > 1:
                relative_spread = float(np.std(half_wave_intervals, ddof=1) / half_wave)
                if relative_spread > 0.1:
                    warnings.append("电压曲线各相邻极值间隔离散超过10%，建议检查极值附近采样是否足够密集。")
        summary.append(_curve_summary("电流传感", current, power_unit, "I", "A"))
        if crystal_thickness is not None or crystal_length is not None:
            if crystal_thickness is None or crystal_length is None:
                warnings.append("按公式(16)计算理论半波电压时，晶体厚度d和通光长度L必须同时填写。")
            elif min(crystal_thickness, crystal_length, crystal_wavelength, ordinary_index, electro_optic_r22) <= 0:
                raise OpticsInputError("公式(16)所用晶体尺寸、波长、折射率和电光系数必须为正数")
            else:
                theoretical_half_wave = (
                    crystal_wavelength * 1e-9 * crystal_thickness * 1e-3
                    / (2.0 * ordinary_index ** 3 * electro_optic_r22 * 1e-12 * crystal_length * 1e-3)
                )
                summary.append(f"按指导书公式(16)计算理论半波电压 Vπ = {theoretical_half_wave:.6g} V")

        doc = create_document(name())
        _add_curve_table(doc, "表1A  透射式纵向位移", curves["longitudinal"], "纵向位置", "mm", power_unit)
        _add_curve_table(doc, "表1B  透射式横向左移", curves["left"], "横向位置", "mm", power_unit)
        _add_curve_table(doc, "表1C  透射式横向右移", curves["right"], "横向位置", "mm", power_unit)
        _add_curve_table(doc, "表2  反射式位移传感", curves["reflection"], "纵向位置", "mm", power_unit)
        _add_curve_table(doc, "表3  微弯位移传感", curves["microbend"], "微弯位移", "mm", power_unit)
        _add_curve_table(doc, "表4  光纤电压传感", voltage, "电压", "V", power_unit)
        _add_curve_table(doc, "表5  光纤电流传感", current, "电流", "A", power_unit)
        add_summary(doc, summary)

        configure_plotting()
        charts = []
        fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
        axes[0].plot(curves["longitudinal"]["x"], curves["longitudinal"]["y"], "o-", markersize=4, color="#4472C4")
        axes[0].set_xlabel("纵向位置读数 / mm")
        axes[0].set_ylabel(f"功率 / {power_unit}")
        axes[0].set_title("透射式纵向位移响应")
        axes[1].plot(left_displacement, curves["left"]["y"], "o-", markersize=4, label="左移", color="#2ECC71")
        axes[1].plot(right_displacement, curves["right"]["y"], "s-", markersize=4, label="右移", color="#E67E22")
        axes[1].set_xlabel("相对最大功率位置的横向位移 / mm")
        axes[1].set_ylabel(f"功率 / {power_unit}")
        axes[1].set_title("透射式横向位移响应")
        axes[1].legend()
        for ax in axes:
            ax.grid(True, linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp34_transmission.png")
        charts.append({"filename": filename, "title": "透射式光纤纵向与横向位移响应"})

        fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
        axes[0].plot(curves["reflection"]["x"], curves["reflection"]["y"], "o-", markersize=4, color="#9B59B6")
        axes[0].set_xlabel("纵向位置读数 / mm")
        axes[0].set_ylabel(f"功率 / {power_unit}")
        axes[0].set_title("反射式位移传感响应")
        axes[1].plot(curves["microbend"]["x"], curves["microbend"]["y"], "o-", markersize=4, color="#E74C3C")
        axes[1].set_xlabel("微弯位移读数 / mm")
        axes[1].set_ylabel(f"功率 / {power_unit}")
        axes[1].set_title("微弯位移传感响应")
        for ax in axes:
            ax.grid(True, linestyle="--", alpha=0.35)
        filename = save_figure(fig, workpath, "exp34_reflection_microbend.png")
        charts.append({"filename": filename, "title": "反射式与微弯式光纤位移响应"})

        sensor_curves = [
            ("电压 / V", voltage, "光纤电压传感"),
            ("电流 / A", current, "光纤电流传感"),
        ]
        for index, (xlabel, curve, title) in enumerate(sensor_curves, 1):
            fig, ax = plt.subplots(figsize=(7.2, 4.5))
            ax.plot(curve["x"], curve["y"], "o-", color="#1ABC9C", markersize=4)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(f"功率 / {power_unit}")
            ax.set_title(title)
            ax.grid(True, linestyle="--", alpha=0.35)
            filename = save_figure(fig, workpath, f"exp34_sensor_{index}.png")
            charts.append({"filename": filename, "title": title})

        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
