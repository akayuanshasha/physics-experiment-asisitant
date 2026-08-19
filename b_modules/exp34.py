from head import *
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
        "description": "按指导书将透射纵向、透射横向左右、反射式和微弯式数据分开记录；各曲线按其实际非线性形状分析，不再对全部数据强行直线拟合。",
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
            }
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
                "id": "voltage", "title": "选做：光纤电压传感", "required": False,
                "enabled_by_default": False, "min_rows": 8, "initial_rows": 15,
                "columns": [{"id": "voltage_v", "label": "电压", "unit": "V"}, {"id": "power", "label": "功率"}],
                "sample": [{"voltage_v": value, "power": round(math.sin(math.pi * value / 600) ** 2, 6)} for value in range(0, 701, 50)],
            },
            {
                "id": "current", "title": "选做：光纤电流传感", "required": False,
                "enabled_by_default": False, "min_rows": 8, "initial_rows": 15,
                "columns": [{"id": "current_a", "label": "电流", "unit": "A"}, {"id": "power", "label": "功率"}],
                "sample": [
                    {"current_a": round(float(value), 2), "power": round(float(0.02 + 0.8 * value ** 2), 6)}
                    for value in np.arange(0, 0.71, 0.05)
                ],
            },
            {
                "id": "temperature", "title": "选做：光纤温度传感", "required": False,
                "enabled_by_default": False, "min_rows": 5, "initial_rows": 10,
                "columns": [{"id": "temperature_c", "label": "温度", "unit": "℃"}, {"id": "fringe_count", "label": "累计条纹移动数"}],
                "sample": [{"temperature_c": value, "fringe_count": round((value - 20) * 0.42, 2)} for value in range(20, 61, 5)],
            },
        ],
    }


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


def handle_structured(workpath, payload):
    try:
        power_unit = get_parameter(payload, "power_unit", "任意单位", True, cast=str)
        curves = {
            "longitudinal": _read_curve(payload, "transmission_longitudinal", True, 15),
            "left": _read_curve(payload, "transmission_left", True, 10),
            "right": _read_curve(payload, "transmission_right", True, 10),
            "reflection": _read_curve(payload, "reflection", True, 15),
            "microbend": _read_curve(payload, "microbend", True, 15),
        }
        voltage = _read_curve(payload, "voltage", False, 8, "voltage_v", "电压")
        current = _read_curve(payload, "current", False, 8, "current_a", "电流")
        temperature_rows = get_rows(payload, "temperature", required=False, min_rows=5)

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

        voltage_result = None
        if voltage:
            y = voltage["y"]
            x = voltage["x"]
            max_index = int(np.argmax(y))
            min_index = int(np.argmin(y))
            half_wave = abs(float(x[max_index] - x[min_index]))
            voltage_result = half_wave
            summary.append(f"电压传感：相邻极值估算半波电压约为 {half_wave:.6g} V（需结合完整周期曲线复核）")
        if current:
            summary.append(_curve_summary("电流传感", current, power_unit, "I", "A"))

        temperature = None
        if temperature_rows:
            temp = numeric_column(temperature_rows, "temperature_c", "温度")
            fringe = numeric_column(temperature_rows, "fringe_count", "累计条纹移动数")
            order = np.argsort(temp)
            temp = temp[order]
            fringe = fringe[order]
            phase = 2 * np.pi * fringe
            temperature = {"x": temp, "y": fringe, "phase": phase}
            fit = linear_fit(temp, phase)
            temperature["fit"] = fit
            summary.append(f"温度传感：相位—温度拟合斜率 {fit['slope']:.6g} rad/℃，R²={fit['r2']:.6f}")

        doc = create_document(name())
        _add_curve_table(doc, "表1A  透射式纵向位移", curves["longitudinal"], "纵向位置", "mm", power_unit)
        _add_curve_table(doc, "表1B  透射式横向左移", curves["left"], "横向位置", "mm", power_unit)
        _add_curve_table(doc, "表1C  透射式横向右移", curves["right"], "横向位置", "mm", power_unit)
        _add_curve_table(doc, "表2  反射式位移传感", curves["reflection"], "纵向位置", "mm", power_unit)
        _add_curve_table(doc, "表3  微弯位移传感", curves["microbend"], "微弯位移", "mm", power_unit)
        if voltage:
            _add_curve_table(doc, "选做：光纤电压传感", voltage, "电压", "V", power_unit)
        if current:
            _add_curve_table(doc, "选做：光纤电流传感", current, "电流", "A", power_unit)
        if temperature:
            add_table(doc, "选做：光纤温度传感", ["温度/℃", "累计条纹数", "相位变化/rad"], [
                [f"{temperature['x'][i]:.6g}", f"{temperature['y'][i]:.6g}", f"{temperature['phase'][i]:.6g}"]
                for i in range(len(temperature["x"]))
            ])
        add_summary(doc, summary)
        add_text_section(doc, "曲线变化规律与实验现象", get_text(payload, "observations"))
        add_text_section(doc, "实验思考与讨论", get_text(payload, "discussion"))

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

        optional_curves = []
        if voltage:
            optional_curves.append(("电压 / V", voltage, "光纤电压传感"))
        if current:
            optional_curves.append(("电流 / A", current, "光纤电流传感"))
        if temperature:
            optional_curves.append(("温度 / ℃", {"x": temperature["x"], "y": temperature["phase"]}, "光纤温度传感（相位变化）"))
        for index, (xlabel, curve, title) in enumerate(optional_curves, 1):
            fig, ax = plt.subplots(figsize=(7.2, 4.5))
            ax.plot(curve["x"], curve["y"], "o-", color="#1ABC9C", markersize=4)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("相位变化 / rad" if "温度" in title else f"功率 / {power_unit}")
            ax.set_title(title)
            ax.grid(True, linestyle="--", alpha=0.35)
            filename = save_figure(fig, workpath, f"exp34_optional_{index}.png")
            charts.append({"filename": filename, "title": title})

        return finish_report(doc, workpath, name(), summary, charts, warnings)
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    return 1
