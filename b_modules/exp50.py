"""医学物理实验（温度传感器特性及人体温度测量）数据处理模块。

实验内容（指导书）：
- 基础：测量温度传感器输出特性（30~80 °C 每隔 10 °C），作图拟合求灵敏度与相关系数；
  三种传感器任选其一——NTC 热敏电阻（恒压源电流法测 Rt，ln Rt 与 1/T 拟合求材料常数 B）、
  PN 结（U ≈ BT + Ugo，温度系数约 -2.3 mV/°C）、LM35（U0 = 10.0 mV/°C · t）；
- 提升：组装数字式电子温度表并定标，测量线性度 δ = ΔY_max/Y × 100%，
  以及人体各部位（眉心、掌心等）温度分布；
- 进阶（附录 2）：MPS3100 气体压力传感器特性（4~32 kPa 测 8 点），
  柯氏音法测血压与心率；
- 选做：波意耳定律验证（PV = 常数）；附录 3 人耳听阈曲线（半对数坐标，零位修正）；
  附录 4 人体反应时间测试（汽车/自行车/声音，各 6 次取平均）。

网页流程（新版结构化接口）：
1. schema() 声明各子实验的输入表与实验参数；
2. preview() 实时给出传感器拟合（灵敏度/材料常数/相关系数）、线性度、血压心率统计等；
3. handle_structured() 生成特性拟合图、定标校核图、听阈曲线等图表与 Word 报告。

旧版 CSV 流程 handle() 保留，供旧接口与 AI 助教调用。
"""

from __future__ import annotations

import math
import os
import traceback
from typing import Any

import numpy as np

from structured_support import as_number, copied_tables, make_schema, make_table, structured_result
from theory_content import get_table_theory

# ── 常数与判据 ──
_KELVIN = 273.15            # 摄氏温度转热力学温度
_LM35_COEFF_REF = 10.0      # LM35 输出电压温度系数（mV/°C）
_PN_COEFF_REF = -2.3        # PN 结正向电压温度系数（mV/°C）
_NTC_B_RANGE = (2000.0, 6000.0)   # NTC 材料常数 B 典型范围（K）
_BP_MMHG_TO_KPA = 0.1333    # 1 mmHg 对应的 kPa
# 正常参考范围：收缩压/舒张压（kPa）、静息心率（次/分）
_BP_NORMAL = ((12.0, 18.7), (8.0, 12.0), (60, 100))


def name():
    return "医学物理实验"


# ──────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────

def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _param_number(parameters: dict[str, Any], key: str, label: str,
                  default: float | None = None) -> float | None:
    """读取数值参数；未填写返回 default，填写但非数字则报错。"""
    value = parameters.get(key)
    if not _has_value(value):
        return default
    number = as_number(value)
    if number is None:
        raise ValueError(f"{label}必须是数字")
    return number


def _linear_fit(x_values: list[float], y_values: list[float]) -> dict[str, float]:
    """最小二乘线性拟合，返回斜率、截距、R²、相关系数与斜率标准不确定度。"""
    if len(x_values) != len(y_values) or len(x_values) < 3:
        raise ValueError("线性拟合至少需要 3 组完整数据")
    count = len(x_values)
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    ss_x = sum((value - mean_x) ** 2 for value in x_values)
    ss_y = sum((value - mean_y) ** 2 for value in y_values)
    if ss_x <= 0:
        raise ValueError("拟合横坐标不能全部相同")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / ss_x
    intercept = mean_y - slope * mean_x
    residual = sum((y - intercept - slope * x) ** 2 for x, y in zip(x_values, y_values))
    r_squared = 1.0 if ss_y <= 0 and residual <= 0 else (0.0 if ss_y <= 0 else 1.0 - residual / ss_y)
    correlation = 0.0 if ss_y <= 0 else sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)
    ) / math.sqrt(ss_x * ss_y)
    slope_uncertainty = 0.0
    if count > 2 and abs(correlation) > 1e-15:
        slope_uncertainty = abs(slope) * math.sqrt(
            max(0.0, (1.0 / correlation ** 2 - 1.0) / (count - 2)))
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r_squared,
        "correlation": correlation,
        "slope_unc": slope_uncertainty,
    }


def _mean_sigma(values: list[float]) -> tuple[float, float]:
    """平均值与样本标准差。"""
    count = len(values)
    mean = sum(values) / count
    sigma = 0.0
    if count > 1:
        sigma = math.sqrt(sum((value - mean) ** 2 for value in values) / (count - 1))
    return mean, sigma


def _sensor_classify(slope: float, sensor_type: str) -> str:
    """根据斜率与参数判断传感器类型（自动识别）。"""
    if sensor_type == "ntc":
        return "NTC 热敏电阻"
    if sensor_type == "pn":
        return "PN 结"
    if sensor_type == "lm35":
        return "LM35 集成温度传感器"
    if abs(slope - _LM35_COEFF_REF) < 2.0:
        return "LM35 集成温度传感器"
    if abs(slope - _PN_COEFF_REF) < 0.8:
        return "PN 结"
    return "未知/放大定标输出"


# ──────────────────────────────────────────────
# 各表计算
# ──────────────────────────────────────────────

def _calc_sensor(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """温度传感器输出特性：NTC 恒压源电流法或电压型线性拟合。

    参考电压 U_R1 列有数据时按 NTC 处理（Rt = R1·U_Rt/U_R1，ln Rt 对 1/T 拟合求 B）；
    否则按电压输出型处理（U 对 t 线性拟合求灵敏度与相关系数）。
    """
    temps: list[float] = []
    outputs: list[float] = []
    refs: list[float | None] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1", "c2")):
            continue
        try:
            temp = float(row.get("c0"))
            output = float(row.get("c1"))
        except (TypeError, ValueError):
            raise ValueError("传感器特性表第 {} 行温度/输出数据不是数字".format(index))
        reference = None
        if _has_value(row.get("c2")):
            try:
                reference = float(row.get("c2"))
            except (TypeError, ValueError):
                raise ValueError("传感器特性表第 {} 行参考电压数据不是数字".format(index))
        temps.append(temp)
        outputs.append(output)
        refs.append(reference)
    if not temps:
        raise ValueError("请填写传感器特性表（温度 t、传感器输出 U）")

    has_ref = [ref is not None for ref in refs]
    lines: list[str] = []
    result: dict[str, Any] = {"lines": lines}

    if any(has_ref):
        # ── NTC 恒压源电流法 ──
        if not all(has_ref):
            raise ValueError("传感器特性表部分行缺少参考电压 U_R1，请补全或全部留空")
        r1 = _param_number(parameters, "r1", "固定电阻 R1", 1.0)
        t0_ref = _param_number(parameters, "t0_ref", "NTC 参考温度 T0", 25.0)
        r0_ref = _param_number(parameters, "r0_ref", "NTC 参考电阻 R0", 1.0)
        if r1 is None or r1 <= 0:
            raise ValueError("NTC 模式需要填写固定电阻 R1（必须大于 0）")

        resistances = [r1 * output / ref for output, ref in zip(outputs, refs)]
        kelvin = [temp + _KELVIN for temp in temps]
        x_values = [1.0 / t for t in kelvin]
        y_values = [math.log(r) for r in resistances]
        fit = _linear_fit(x_values, y_values)
        b_value = fit["slope"]
        r0_fit = math.exp(fit["intercept"] + b_value / (t0_ref + _KELVIN))
        rel_err = abs(r0_fit - r0_ref) / r0_ref * 100 if r0_ref else 0.0
        alpha_pct = -b_value / (t0_ref + _KELVIN) ** 2 * 100  # 电阻温度系数（%/K）
        b_check = "在典型范围 2000~6000 K 内" if _NTC_B_RANGE[0] <= b_value <= _NTC_B_RANGE[1] \
            else "超出典型范围 2000~6000 K，请检查数据"
        lines.append("NTC 恒压源电流法：R_t = R1·U_Rt/U_R1（R1 = {:.2f} kΩ）".format(r1))
        lines.append("ln(R_t) 对 1/T 拟合：ln R_t = {:.4f} + ({:.2f})(1/T)，相关系数 r = {:.5f}".format(
            fit["intercept"], b_value, fit["correlation"]))
        lines.append("材料常数 B = {:.1f} K（{}）；电阻温度系数 α = {:.3f} %/K（{} °C）".format(
            b_value, b_check, alpha_pct, t0_ref))
        lines.append("由截距反推 R0 = {:.3f} kΩ（参考值 {:.2f} kΩ @ {} °C，相对误差 {:.2f}%）".format(
            r0_fit, r0_ref, t0_ref, rel_err))
        result.update({"mode": "ntc", "x": x_values, "y": y_values, "fit": fit})
    else:
        # ── 电压输出型（PN 结 / LM35 / 放大定标输出）──
        fit = _linear_fit(temps, outputs)
        slope = fit["slope"]
        kind = _sensor_classify(slope, str(parameters.get("sensor_type") or "auto"))
        lines.append("U 对 t 拟合：U = {:.3f} + ({:.4f})t，R² = {:.5f}，相关系数 r = {:.5f}".format(
            fit["intercept"], slope, fit["r2"], fit["correlation"]))
        lines.append("传感器灵敏度 K = ΔU/Δt = {:.4f} mV/°C → 判断为：{}".format(slope, kind))
        if kind.startswith("LM35"):
            rel = abs(slope - _LM35_COEFF_REF) / _LM35_COEFF_REF * 100
            lines.append("LM35 参考温度系数 10.0 mV/°C，相对误差 {:.2f}%".format(rel))
        elif kind.startswith("PN"):
            rel = abs(slope - _PN_COEFF_REF) / abs(_PN_COEFF_REF) * 100
            lines.append("PN 结参考温度系数约 -2.3 mV/°C，相对误差 {:.2f}%".format(rel))
        else:
            lines.append("斜率不匹配 LM35/PN 结典型值，可能为放大定标输出（目标 10 mV/°C）。")
        result.update({"mode": "voltage", "x": temps, "y": outputs, "fit": fit})
    return result


def _calc_calib(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """组装数字式电子温度表定标：Δt 与线性度 δ = ΔY_max/Y × 100%。"""
    t_set: list[float] = []
    t_std: list[float] = []
    t_assem: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1", "c2")):
            continue
        try:
            t_set.append(float(row.get("c0")))
            t_std.append(float(row.get("c1")))
            t_assem.append(float(row.get("c2")))
        except (TypeError, ValueError):
            raise ValueError("定标表第 {} 行数据不完整或不是数字".format(index))
    if not t_set:
        raise ValueError("请填写定标表（设定温度、标准表示数、组装表示数）")

    diffs = [assem - std for assem, std in zip(t_assem, t_std)]
    max_abs_diff = max(abs(diff) for diff in diffs)
    max_index = diffs.index(max(diffs, key=abs)) + 1
    span = max(t_assem) - min(t_assem)
    linearity = max_abs_diff / span * 100 if span > 0 else 0.0
    fit = _linear_fit(t_std, t_assem)

    lines = [
        "各点差值 Δt = t_组装 − t_标准：{} °C".format(
            "、".join("{:+.1f}".format(diff) for diff in diffs) if len(diffs) <= 16
            else "共 {} 组".format(len(diffs))),
        "最大差值 |Δt|_max = {:.1f} °C（第 {} 组），组装表量程 Y = {:.1f} °C".format(
            max_abs_diff, max_index, span),
        "线性度 δ = ΔY_max/Y × 100% = {:.1f} / {:.1f} × 100% = {:.2f}%".format(
            max_abs_diff, span, linearity),
        "t_组装 对 t_标准 拟合：t_组装 = {:.3f} + ({:.4f})t_标准，r = {:.5f}".format(
            fit["intercept"], fit["slope"], fit["correlation"]),
        "斜率接近 1、截距接近 0 说明组装温度表与标准表同步。",
    ]
    return {"lines": lines, "x": t_std, "y": t_assem, "fit": fit}


def _calc_body_temp(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """人体各部位温度分布：分部位统计与温差。"""
    groups: dict[str, list[float]] = {}
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1")):
            continue
        part = str(row.get("c0") or "").strip() or "部位{}".format(index)
        try:
            temp = float(row.get("c1"))
        except (TypeError, ValueError):
            raise ValueError("人体温度表第 {} 行温度数据不是数字".format(index))
        if not 30 <= temp <= 42:
            raise ValueError("人体温度表第 {} 行温度 {:.1f} °C 不在合理范围（30~42 °C），请检查".format(index, temp))
        groups.setdefault(part, []).append(temp)
    if not groups:
        raise ValueError("请填写人体各部位温度表（部位、温度）")

    lines: list[str] = []
    stats = []
    for part, temps in groups.items():
        mean, sigma = _mean_sigma(temps)
        lines.append("部位「{}」共 {} 次：t̄ = {:.2f} °C，σ = {:.2f} °C".format(
            part, len(temps), mean, sigma))
        stats.append({"name": part, "mean": mean, "unc": sigma})
    if len(groups) > 1:
        warmest = max(stats, key=lambda item: item["mean"])
        coldest = min(stats, key=lambda item: item["mean"])
        lines.append("部位间最大温差：{}（{:.2f} °C）− {}（{:.2f} °C）= {:.2f} °C".format(
            warmest["name"], warmest["mean"], coldest["name"], coldest["mean"],
            warmest["mean"] - coldest["mean"]))
        lines.append("体表（眉心、掌心等）温度通常低于核心部位（腋下、口腔），可据此讨论人体散热与血液循环。")
    return {"lines": lines, "groups": stats}


def _calc_pressure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """MPS3100 压力传感器特性：U 对 P 线性拟合求灵敏度与相关系数。"""
    pressures: list[float] = []
    outputs: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1")):
            continue
        try:
            pressures.append(float(row.get("c0")))
            outputs.append(float(row.get("c1")))
        except (TypeError, ValueError):
            raise ValueError("压力特性表第 {} 行数据不是数字".format(index))
    if not pressures:
        raise ValueError("请填写压力特性表（压强 P、输出电压 U）")
    if any(not 4 <= p <= 32 for p in pressures):
        raise ValueError("压强超出微压表可靠量程 4~32 kPa（严禁超过 36 kPa），请检查数据")

    fit = _linear_fit(pressures, outputs)
    span = max(outputs) - min(outputs)
    max_dev = 0.0
    if span > 0:
        max_dev = max(
            abs(u - (fit["slope"] * p + fit["intercept"]))
            for p, u in zip(pressures, outputs)) / span * 100

    lines = [
        "U 对 P 拟合：U = {:.3f} + ({:.4f})P，R² = {:.5f}，相关系数 r = {:.5f}".format(
            fit["intercept"], fit["slope"], fit["r2"], fit["correlation"]),
        "传感器灵敏度 K = ΔU/ΔP = {:.3f} mV/kPa".format(fit["slope"]),
        "非线性度 = 最大偏差/满量程输出 × 100% = {:.2f}%（MPS3100 典型值 0.3%F.S.）".format(max_dev),
    ]
    return {"lines": lines, "x": pressures, "y": outputs, "fit": fit}


def _calc_blood(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """血压与心率（柯氏音法）：三次测量的均值、标准差与正常范围对照。"""
    systolic: list[float] = []
    diastolic: list[float] = []
    heart_rate: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1", "c2")):
            continue
        try:
            systolic.append(float(row.get("c0")))
            diastolic.append(float(row.get("c1")))
            heart_rate.append(float(row.get("c2")))
        except (TypeError, ValueError):
            raise ValueError("血压心率表第 {} 行数据不是数字".format(index))
    if not systolic:
        raise ValueError("请填写血压心率表（收缩压、舒张压、心率）")

    def stats(values):
        mean, sigma = _mean_sigma(values)
        return mean, sigma

    s_mean, s_sigma = stats(systolic)
    d_mean, d_sigma = stats(diastolic)
    h_mean, h_sigma = stats(heart_rate)
    pulse_pressure = s_mean - d_mean

    lines = [
        "收缩压：{:.1f} ± {:.1f} kPa；舒张压：{:.1f} ± {:.1f} kPa；脉压差 = {:.1f} kPa".format(
            s_mean, s_sigma, d_mean, d_sigma, pulse_pressure),
        "心率：{:.1f} ± {:.1f} 次/分".format(h_mean, h_sigma),
        "正常参考：收缩压 {:.0f}~{:.1f} kPa（{:.0f}~{:.0f} mmHg），舒张压 {:.0f}~{:.0f} kPa（{:.0f}~{:.0f} mmHg），静息心率 {}~{} 次/分".format(
            _BP_NORMAL[0][0], _BP_NORMAL[0][1], _BP_NORMAL[0][0] / _BP_MMHG_TO_KPA,
            _BP_NORMAL[0][1] / _BP_MMHG_TO_KPA, _BP_NORMAL[1][0], _BP_NORMAL[1][1],
            _BP_NORMAL[1][0] / _BP_MMHG_TO_KPA, _BP_NORMAL[1][1] / _BP_MMHG_TO_KPA,
            _BP_NORMAL[2][0], _BP_NORMAL[2][1]),
    ]
    if not _BP_NORMAL[0][0] <= s_mean <= _BP_NORMAL[0][1]:
        lines.append("注意：收缩压超出正常参考范围。")
    if not _BP_NORMAL[1][0] <= d_mean <= _BP_NORMAL[1][1]:
        lines.append("注意：舒张压超出正常参考范围。")
    if not _BP_NORMAL[2][0] <= h_mean <= _BP_NORMAL[2][1]:
        lines.append("注意：心率超出静息正常范围（测量后应静坐休息再测）。")
    return {"lines": lines}


def _calc_boyle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """波意耳定律验证：P·V 恒定性检查 + P 对 1/V 拟合。"""
    volumes: list[float] = []
    pressures: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1")):
            continue
        try:
            volumes.append(float(row.get("c0")))
            pressures.append(float(row.get("c1")))
        except (TypeError, ValueError):
            raise ValueError("波意耳表第 {} 行数据不是数字".format(index))
    if not volumes:
        raise ValueError("请填写波意耳定律表（体积 V、压强 P）")
    if any(v <= 0 for v in volumes):
        raise ValueError("波意耳表体积 V 必须大于 0")

    products = [p * v for p, v in zip(pressures, volumes)]
    mean_pv, sigma_pv = _mean_sigma(products)
    rel_devs = [abs(pv - mean_pv) / mean_pv * 100 for pv in products]
    x_values = [1.0 / v for v in volumes]
    fit = _linear_fit(x_values, pressures)

    lines = [
        "各组 P·V：{} kPa·ml".format("、".join("{:.1f}".format(pv) for pv in products)
                                      if len(products) <= 16 else "共 {} 组".format(len(products))),
        "P·V 平均值 = {:.1f} kPa·ml，σ = {:.1f}，最大相对偏差 {:.2f}%".format(
            mean_pv, sigma_pv, max(rel_devs)),
        "P 对 1/V 拟合：P = {:.2f} + ({:.2f})(1/V)，r = {:.5f}，斜率即 PV 常数".format(
            fit["intercept"], fit["slope"], fit["correlation"]),
        "P·V 近似为常数且 P-1/V 线性良好，验证波意耳定律成立。",
    ]
    return {"lines": lines, "x": x_values, "y": pressures, "fit": fit}


def _calc_hearing(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """听阈曲线：渐增/渐减法平均、零位修正（以 1000 Hz 为基准）。"""
    freqs: list[float] = []
    levels: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1", "c2")):
            continue
        try:
            freq = float(row.get("c0"))
            l1 = float(row.get("c1"))
            l2 = float(row.get("c2"))
        except (TypeError, ValueError):
            raise ValueError("听阈表第 {} 行数据不是数字".format(index))
        freqs.append(freq)
        levels.append((l1 + l2) / 2)
    if not freqs:
        raise ValueError("请填写听阈表（频率 f、渐增法 L1、渐减法 L2）")

    # 零位修正：优先取 1000 Hz 行的平均值，否则用参数 L0
    base = None
    base_text = ""
    for freq, level in zip(freqs, levels):
        if abs(freq - 1000) < 1:
            base = level
            base_text = "1000 Hz 行平均"
            break
    if base is None:
        base = _param_number(parameters, "l0", "听阈基准 L0", None)
        base_text = "参数 L0"
    relative = [level - base for level in levels] if base is not None else levels
    corrected = base is not None

    best_index = int(np.argmin(relative))
    lines = []
    if corrected:
        lines.append("零位修正基准 L0 = {:.1f} dB（{}），L_测 = (L1+L2)/2 − L0".format(base, base_text))
    else:
        lines.append("未找到 1000 Hz 行且未填写基准 L0 参数，以下为未修正的绝对声强级。")
    lines.append("各频率听阈 L_测：{}".format("、".join(
        "{:.0f} Hz→{:.1f} dB".format(freq, level)
        for freq, level in zip(freqs, relative))))
    lines.append("最敏感频率：{:.0f} Hz（L_测 = {:.1f} dB），人耳通常对 2~4 kHz 最敏感".format(
        freqs[best_index], relative[best_index]))
    if abs(freqs[best_index] - 1000) < 1 and corrected:
        lines.append("1000 Hz 处 L_测 = 0 dB，为定义基准。")
    return {"lines": lines, "freqs": freqs, "levels": relative}


def _calc_reaction(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """人体反应时间：分测试项目统计（指导书要求各测 6 次取平均）。"""
    groups: dict[str, list[float]] = {}
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1")):
            continue
        project = str(row.get("c0") or "").strip() or "项目{}".format(index)
        try:
            time = float(row.get("c1"))
        except (TypeError, ValueError):
            raise ValueError("反应时间表第 {} 行时间数据不是数字".format(index))
        groups.setdefault(project, []).append(time)
    if not groups:
        raise ValueError("请填写反应时间表（测试项目、反应时间）")

    lines: list[str] = []
    stats = []
    for project, times in groups.items():
        mean, sigma = _mean_sigma(times)
        lines.append("「{}」共 {} 次：t̄ = {:.1f} ms，σ = {:.1f} ms，范围 {:.1f}~{:.1f} ms".format(
            project, len(times), mean, sigma, min(times), max(times)))
        stats.append({"name": project, "mean": mean, "unc": sigma})
    if len(groups) > 1:
        ranked = sorted(stats, key=lambda item: item["mean"])
        lines.append("各项目平均反应时间排序：" + " ＜ ".join(
            "{} {:.1f} ms".format(item["name"], item["mean"]) for item in ranked))
        lines.append("听觉反应通常比视觉反应快约 100~200 ms，可据此讨论不同刺激通路的差异。")
    return {"lines": lines, "groups": stats}


# ──────────────────────────────────────────────
# 结构化接口
# ──────────────────────────────────────────────

def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：传感器拟合、定标线性度、血压心率统计等。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    fit_notes: dict[str, list[str]] = {}

    handlers = {
        "sensor": (_calc_sensor, ("c0", "c1", "c2"), [
            "NTC：ln(R_t) 与 1/T 成线性，斜率即材料常数 B（典型 2000~6000 K）。",
            "PN 结：U ≈ BT + U_go，温度系数约 -2.3 mV/°C；LM35：U0 = 10.0 mV/°C · t。",
        ]),
        "calib": (_calc_calib, ("c0", "c1", "c2"), [
            "线性度 δ = ΔY_max/Y × 100%，ΔY_max 取 |Δt| 最大值，Y 为组装表测量范围。",
        ]),
        "body_temp": (_calc_body_temp, ("c0", "c1"), [
            "体表温度通常低于核心温度，部位间温差反映血液循环与散热。",
        ]),
        "pressure": (_calc_pressure, ("c0", "c1"), [
            "MPS3100 线性度典型 0.3%F.S.；可靠量程 4~32 kPa，严禁超过 36 kPa。",
        ]),
        "blood": (_calc_blood, ("c0", "c1", "c2"), [
            "1 mmHg ≈ 0.1333 kPa；柯氏音法：第一声为收缩压，最后一声为舒张压。",
        ]),
        "boyle": (_calc_boyle, ("c0", "c1"), [
            "等温过程 P·V = 常数，P 与 1/V 成正比。",
        ]),
        "hearing": (_calc_hearing, ("c0", "c1", "c2"), [
            "听阈曲线用半对数坐标（横轴 lg f）；以 1000 Hz 阈值作零位修正。",
        ]),
        "reaction": (_calc_reaction, ("c0", "c1"), [
            "各项目测 6 次取平均；听觉反应通常快于视觉反应。",
        ]),
    }
    for table_id, (handler, columns, notes) in handlers.items():
        rows = tables.get(table_id, []) or []
        if not any(_has_value(row.get(column)) for row in rows for column in columns):
            continue
        try:
            if handler is _calc_sensor or handler is _calc_hearing:
                calc_results[table_id] = handler(rows, parameters)
            else:
                calc_results[table_id] = handler(rows)
            fit_notes[table_id] = list(notes)
        except ValueError as exc:
            calc_messages.append(str(exc))

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_fit_chart(workpath: str, info: dict[str, Any], x_label: str, y_label: str,
                    title: str, filename: str) -> dict[str, Any]:
    """散点 + 最小二乘拟合直线（用于传感器特性、压力特性、波意耳验证）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    x_values, y_values, fit = info["x"], info["y"], info["fit"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(x_values, y_values, s=40, color="#2f7fc1", zorder=4, label="测量点")
    x_min, x_max = min(x_values), max(x_values)
    if x_max > x_min:
        xs = np.linspace(x_min, x_max, 200)
        axis.plot(xs, fit["slope"] * xs + fit["intercept"], "-", color="#d94b40",
                  linewidth=1.5, zorder=3, label="最小二乘拟合直线")
    axis.annotate(
        "y = {:.4f} + ({:.5f})x\nR² = {:.5f}，r = {:.5f}".format(
            fit["intercept"], fit["slope"], fit["r2"], fit["correlation"]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9),
    )
    axis.set_xlabel(x_label, fontproperties=font)
    axis.set_ylabel(y_label, fontproperties=font)
    axis.set_title(title, fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, filename), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": filename, "title": title, "x_label": x_label, "y_label": y_label}


def _make_calib_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """定标校核：组装表示数对标准表示数散点 + 恒等线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    x_values, y_values = info["x"], info["y"]
    lower = min(min(x_values), min(y_values)) - 0.2
    upper = max(max(x_values), max(y_values)) + 0.2

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(x_values, y_values, s=40, color="#2f7fc1", zorder=4, label="测量点")
    axis.plot([lower, upper], [lower, upper], "--", color="#d94b40", linewidth=1.2,
              zorder=3, label="y = x（完全同步）")
    axis.annotate(
        "t_组装 = {:.3f} + ({:.4f})t_标准，r = {:.5f}\n（斜率接近 1、截距接近 0 说明两表同步）".format(
            info["fit"]["intercept"], info["fit"]["slope"], info["fit"]["correlation"]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9),
    )
    axis.set_xlim(lower, upper)
    axis.set_ylim(lower, upper)
    axis.set_xlabel("标准温度表示数 t_标准 (°C)", fontproperties=font)
    axis.set_ylabel("组装温度表示数 t_组装 (°C)", fontproperties=font)
    axis.set_title("组装数字式电子温度表定标校核", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "med_calib.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "med_calib.png", "title": "电子温度表定标校核",
            "x_label": "标准表示数 (°C)", "y_label": "组装表示数 (°C)"}


def _make_group_bar_chart(workpath: str, info: dict[str, Any], y_label: str,
                          title: str, filename: str) -> dict[str, Any]:
    """分项目/部位统计柱状图（人体温度、反应时间）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    groups = info["groups"]
    names = [item["name"] for item in groups]
    means = [item["mean"] for item in groups]
    uncs = [item["unc"] for item in groups]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    x = np.arange(len(names))
    axis.bar(x, means, yerr=uncs, capsize=5, color="#2f7fc1", alpha=0.85, zorder=3)
    for xi, item in enumerate(groups):
        axis.annotate("{:.2f}±{:.2f}".format(item["mean"], item["unc"]),
                      (xi, item["mean"] + item["unc"] + max(0.02, (max(means) - min(means)) * 0.03)),
                      ha="center", fontsize=9, fontproperties=font)
    axis.set_xticks(x)
    if len(names) > 5:
        axis.set_xticklabels(names, rotation=20, ha="right", fontproperties=font, fontsize=9)
    else:
        axis.set_xticklabels(names, fontproperties=font, fontsize=9)
    axis.set_ylabel(y_label, fontproperties=font)
    axis.set_xlabel("项目", fontproperties=font)
    axis.set_title(title, fontproperties=font)
    axis.grid(alpha=0.25, axis="y", zorder=0)
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, filename), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": filename, "title": title, "x_label": "项目", "y_label": y_label}


def _make_hearing_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """听阈曲线（半对数坐标：横轴对数频率）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    freqs, levels = info["freqs"], info["levels"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.plot(freqs, levels, "-o", color="#2f7fc1", linewidth=1.2, zorder=4, label="听阈 L_测")
    best_index = int(np.argmin(levels))
    axis.annotate("最敏感 {:.0f} Hz\n{:.1f} dB".format(freqs[best_index], levels[best_index]),
                  (freqs[best_index], levels[best_index]), textcoords="offset points",
                  xytext=(0, -26), ha="center", fontsize=9, color="#d94b40", fontproperties=font)
    axis.set_xscale("log")
    axis.set_xticks(freqs)
    axis.set_xticklabels(["{:.0f}".format(freq) if freq < 1000 else "{:.0f}k".format(freq / 1000)
                          for freq in freqs], fontsize=9)
    axis.set_xlabel("频率 f (Hz，对数坐标)", fontproperties=font)
    axis.set_ylabel("相对声强级 L_测 (dB)", fontproperties=font)
    axis.set_title("人耳听阈曲线（半对数坐标系）", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "med_hearing.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "med_hearing.png", "title": "人耳听阈曲线",
            "x_label": "频率 f (Hz)", "y_label": "相对声强级 L_测 (dB)"}


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """新版结构化接口：计算各子实验数据，输出摘要与图表。"""
    parameters = payload.get("parameters") or {}
    try:
        for key, label in (("r1", "固定电阻 R1"), ("t0_ref", "NTC 参考温度 T0"),
                           ("r0_ref", "NTC 参考电阻 R0"), ("l0", "听阈基准 L0")):
            value = _param_number(parameters, key, label)
            if value is not None and value <= 0:
                raise ValueError(f"{label}必须大于 0")
    except ValueError as exc:
        return {"code": 1, "message": str(exc)}

    result = preview(payload)
    sensor_info = result["calc_results"].get("sensor")
    if sensor_info is None:
        return {"code": 1, "message": "；".join(result["calc_messages"]) or "请先填写温度传感器特性测量表（基础实验）。"}

    os.makedirs(workpath, exist_ok=True)
    charts: list[dict[str, Any]] = []
    if sensor_info["mode"] == "ntc":
        charts.append(_make_fit_chart(workpath, sensor_info,
                                      r"$1/T$ (K$^{-1}$)", r"$\ln R_t$ (kΩ)",
                                      "NTC 热敏电阻 ln R_t — 1/T 特性曲线", "med_sensor_ntc.png"))
    else:
        charts.append(_make_fit_chart(workpath, sensor_info,
                                      "温度 t (°C)", "输出电压 U (mV)",
                                      "温度传感器输出特性曲线", "med_sensor_u.png"))
    calib_info = result["calc_results"].get("calib")
    if calib_info is not None:
        charts.append(_make_calib_chart(workpath, calib_info))
    body_info = result["calc_results"].get("body_temp")
    if body_info is not None:
        charts.append(_make_group_bar_chart(workpath, body_info, "温度 t (°C)",
                                            "人体各部位温度分布", "med_body_temp.png"))
    pressure_info = result["calc_results"].get("pressure")
    if pressure_info is not None:
        charts.append(_make_fit_chart(workpath, pressure_info,
                                      "压强 P (kPa)", "输出电压 U (mV)",
                                      "MPS3100 压力传感器特性曲线", "med_pressure.png"))
    boyle_info = result["calc_results"].get("boyle")
    if boyle_info is not None:
        charts.append(_make_fit_chart(workpath, boyle_info,
                                      r"$1/V$ (ml$^{-1}$)", "压强 P (kPa)",
                                      "波意耳定律验证：P — 1/V 关系", "med_boyle.png"))
    hearing_info = result["calc_results"].get("hearing")
    if hearing_info is not None:
        charts.append(_make_hearing_chart(workpath, hearing_info))
    reaction_info = result["calc_results"].get("reaction")
    if reaction_info is not None:
        charts.append(_make_group_bar_chart(workpath, reaction_info, "反应时间 t (ms)",
                                            "人体反应时间测试", "med_reaction.png"))

    summary: list[str] = []
    for table_id, label in (("sensor", "温度传感器输出特性"),
                            ("calib", "电子温度表定标与线性度"),
                            ("body_temp", "人体各部位温度"),
                            ("pressure", "压力传感器特性"),
                            ("blood", "血压与心率"),
                            ("boyle", "波意耳定律验证"),
                            ("hearing", "听阈曲线"),
                            ("reaction", "反应时间")):
        if table_id in result["calc_results"]:
            summary.append("【{}】".format(label))
            summary.extend(result["calc_results"][table_id]["lines"])

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        charts=charts,
    )


# ──────────────────────────────────────────────
# 表结构与示例数据
# ──────────────────────────────────────────────

def _set_units(table: dict[str, Any], units: tuple[str, ...]) -> dict[str, Any]:
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema() -> dict[str, Any]:
    sensor = _set_units(
        make_table(
            "sensor", "温度传感器特性测量表（基础实验）",
            ["控温仪温度 t", "传感器输出 U", "参考电压 U_R1（可留空）"],
            sample=[
                [30, 2259, 2741],
                [40, 1815, 3185],
                [50, 1437, 3563],
                [60, 1128, 3872],
                [70, 883, 4117],
                [80, 692, 4308],
            ],
            min_rows=3, initial_rows=6,
            description=(
                "从 30.0 °C 起每隔 10.0 °C 设置控温系统温度至 80.0 °C，待稳定后记录传感器输出。"
                "NTC 热敏电阻用恒压源电流法：同时记录 R1 上的参考电压 U_R1；"
                "PN 结记录正向电压 U_be；LM35 记录输出电压 U0（U_R1 列留空）。"
            ),
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "温度 t (°C)", "y_label": "传感器输出 U (mV)",
                "title": "温度传感器输出特性", "fit": "auto",
            },
        ),
        ("°C", "mV", "mV"),
    )
    sensor["calc"] = {"label": "拟合输出特性"}

    calib = _set_units(
        make_table(
            "calib", "组装数字式电子温度表定标与线性度表（提升实验）",
            ["设定温度 t_设定", "标准表示数 t_标准", "组装表示数 t_组装"],
            sample=[
                [35.0, 34.9, 35.1],
                [36.0, 35.9, 36.1],
                [37.0, 37.0, 36.9],
                [38.0, 37.9, 38.1],
                [39.0, 39.0, 38.9],
                [40.0, 39.9, 40.1],
                [41.0, 40.9, 41.1],
                [42.0, 41.9, 42.0],
            ],
            min_rows=3, initial_rows=8, required=False,
            description=(
                "从 35.0 °C 到 42.0 °C 每隔 0.5 或 1 °C 设置控温仪温度，"
                "分别记录组装数字式电子温度计与标准温度表的示数。"
            ),
            chart={
                "x_column": "c1", "y_column": "c2",
                "x_label": "标准表示数 t_标准 (°C)", "y_label": "组装表示数 t_组装 (°C)",
                "title": "组装温度表定标曲线", "fit": "linear",
            },
        ),
        ("°C", "°C", "°C"),
    )
    calib["calc"] = {"label": "计算线性度"}

    body_temp = _set_units(
        make_table(
            "body_temp", "人体各部位温度分布表（提升实验）",
            ["部位名称", "温度 t"],
            sample=[
                ["眉心", 34.9],
                ["眉心", 35.0],
                ["掌心", 34.5],
                ["掌心", 34.6],
                ["腋下", 36.4],
                ["腋下", 36.5],
            ],
            text_columns=(0,), min_rows=1, initial_rows=6, required=False,
            description=(
                "用组装数字式电子温度计测量人体各部位（眉心、掌心、腋下等）的温度，"
                "每个部位可测 2~3 次，了解人体各部位温差。"
            ),
        ),
        ("", "°C"),
    )
    body_temp["calc"] = {"label": "统计部位温差"}

    pressure = _set_units(
        make_table(
            "pressure", "MPS3100 气体压力传感器特性表（进阶实验，选做）",
            ["压强 P", "输出电压 U"],
            sample=[
                [4, 13.0],
                [8, 21.0],
                [12, 29.0],
                [16, 37.0],
                [20, 45.0],
                [24, 53.0],
                [28, 61.0],
                [32, 69.0],
            ],
            min_rows=3, initial_rows=8, required=False,
            description=(
                "用 10 ml 注射器改变管路内气体压强，在 4~32 kPa 范围内测 8 点，"
                "记录指针式压力表读数与传感器输出电压。严禁加压超过 36 kPa。"
            ),
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "压强 P (kPa)", "y_label": "输出电压 U (mV)",
                "title": "压力传感器特性曲线", "fit": "linear",
            },
        ),
        ("kPa", "mV"),
    )
    pressure["calc"] = {"label": "拟合压力特性"}
    pressure["enabled_by_default"] = False

    blood = _set_units(
        make_table(
            "blood", "血压与心率测量表（进阶实验，柯氏音法，选做）",
            ["收缩压", "舒张压", "心率"],
            sample=[
                [16.0, 10.7, 72],
                [15.9, 10.5, 74],
                [16.1, 10.9, 73],
            ],
            min_rows=1, initial_rows=3, required=False,
            description=(
                "柯氏音法测血压：袖套充气至约 20 kPa 后缓慢放气，第一声柯氏音对应收缩压，"
                "最后一声对应舒张压；同时用智能脉搏计数器测心率。各重复测量 3 次。"
            ),
        ),
        ("kPa", "kPa", "次/分"),
    )
    blood["calc"] = {"label": "统计血压心率"}
    blood["enabled_by_default"] = False

    boyle = _set_units(
        make_table(
            "boyle", "波意耳定律验证表（选做）",
            ["气体体积 V", "压强 P"],
            sample=[
                [10, 9.6],
                [9, 10.7],
                [8, 12.0],
                [7, 13.7],
                [6, 16.0],
                [5, 19.2],
            ],
            min_rows=3, initial_rows=6, required=False,
            description=(
                "用注射器改变管路内气体体积，记录对应压强，验证等温条件下 P·V 为常数。"
            ),
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "气体体积 V (ml)", "y_label": "压强 P (kPa)",
                "title": "P-V 关系曲线", "fit": "auto",
            },
        ),
        ("ml", "kPa"),
    )
    boyle["calc"] = {"label": "验证波意耳定律"}
    boyle["enabled_by_default"] = False

    hearing = _set_units(
        make_table(
            "hearing", "人耳听阈曲线测量表（附录 3，选做）",
            ["频率 f", "渐增法 L1", "渐减法 L2"],
            sample=[
                [64, 58.0, 58.5],
                [128, 46.5, 47.0],
                [256, 39.0, 39.5],
                [512, 31.5, 32.0],
                [1000, 28.0, 28.5],
                [2000, 24.5, 25.0],
                [4000, 23.0, 23.5],
                [8000, 26.0, 26.5],
                [16000, 36.0, 37.0],
            ],
            min_rows=3, initial_rows=9, required=False,
            description=(
                "对 64 Hz、128 Hz、256 Hz、512 Hz、1 kHz、2 kHz、4 kHz、8 kHz、16 kHz "
                "九个频率，分别用渐增法和渐减法测定听阈 L1、L2。"
                "以 1000 Hz 行为基准自动零位修正（L_测 = (L1+L2)/2 − L0）。"
            ),
        ),
        ("Hz", "dB", "dB"),
    )
    hearing["calc"] = {"label": "计算听阈曲线"}
    hearing["enabled_by_default"] = False

    reaction = _set_units(
        make_table(
            "reaction", "人体反应时间测试表（附录 4，选做）",
            ["测试项目", "反应时间 t"],
            sample=[
                ["汽车", 480],
                ["汽车", 452],
                ["汽车", 511],
                ["汽车", 468],
                ["汽车", 495],
                ["汽车", 503],
                ["声音", 268],
                ["声音", 291],
                ["声音", 275],
                ["声音", 312],
                ["声音", 284],
                ["声音", 296],
            ],
            text_columns=(0,), min_rows=1, initial_rows=12, required=False,
            description=(
                "汽车测试（红灯亮后踩刹车）、自行车测试（红灯亮后捏手刹）、声音测试（喇叭响后捏手刹），"
                "各项目测量 6 次取平均。"
            ),
        ),
        ("", "ms"),
    )
    reaction["calc"] = {"label": "统计反应时间"}
    reaction["enabled_by_default"] = False

    parameters = [
        {"id": "sensor_type", "label": "传感器类型", "type": "select",
         "default": "auto", "required": True,
         "options": [
             {"value": "auto", "label": "自动识别"},
             {"value": "ntc", "label": "NTC 热敏电阻"},
             {"value": "pn", "label": "PN 结"},
             {"value": "lm35", "label": "LM35 集成温度传感器"},
         ],
         "help": "用于电压型输出的参考值对照；NTC 模式由参考电压列自动识别"},
        {"id": "r1", "label": "固定电阻 R1", "unit": "kΩ", "type": "number",
         "default": 1.0, "min": 0, "step": "any", "required": False,
         "condition": {"parameter": "sensor_type", "in": ["auto", "ntc"]},
         "help": "NTC 恒压源电流法：与热敏电阻串联的固定电阻（面板标称 1 kΩ）"},
        {"id": "t0_ref", "label": "NTC 参考温度 T0", "unit": "°C", "type": "number",
         "default": 25.0, "min": 0, "step": "any", "required": False,
         "condition": {"parameter": "sensor_type", "in": ["auto", "ntc"]},
         "help": "R0 对应的温度，通常 25 °C"},
        {"id": "r0_ref", "label": "NTC 参考电阻 R0", "unit": "kΩ", "type": "number",
         "default": 1.0, "min": 0, "step": "any", "required": False,
         "condition": {"parameter": "sensor_type", "in": ["auto", "ntc"]},
         "help": "T0 时的阻值，NTC1K 为 1 kΩ"},
        {"id": "l0", "label": "听阈基准 L0", "unit": "dB", "type": "number",
         "min": 0, "step": "any", "required": False,
         "help": "1000 Hz 绝对声强级；留空时自动取表中 1000 Hz 行"},
    ]

    theory = get_table_theory("exp50")
    return make_schema(
        (
            "温度传感器特性及人体温度测量：测量传感器电压（或电阻）与温度的关系，"
            "求灵敏度与相关系数；组装数字式电子温度表并定标、测量线性度；"
            "测量人体各部位温度分布。进阶实验：MPS3100 压力传感器特性与柯氏音法测血压心率；"
            "选做：波意耳定律验证、人耳听阈曲线、人体反应时间。"
        ),
        [sensor, calib, body_temp, pressure, blood, boyle, hearing, reaction],
        parameters=parameters,
        parameters_sample={"sensor_type": "auto", "r1": 1.0, "t0_ref": 25.0,
                           "r0_ref": 1.0, "l0": ""},
        analysis_hints=(
            "NTC：ln R_t 对 1/T 应成良好直线，B 典型 2000~6000 K；"
            "PN 结温度系数约 -2.3 mV/°C，LM35 为 +10.0 mV/°C；"
            "拟合相关系数 |r| 应接近 1；"
            "定标表斜率应接近 1、截距接近 0；"
            "压力传感器可靠量程 4~32 kPa，严禁超过 36 kPa；"
            "听阈曲线最敏感点通常在 2~4 kHz；反应时间各项目应测 6 次。"
        ),
        preview_enabled=True,
        formulas=theory.get("_global", {}).get("formulas", []),
        variables=theory.get("_global", {}).get("variables", []),
        table_theory=theory,
    )


def handle(workpath: str, extension: str) -> int:
    """旧版 CSV 流程（温度/输出/参考电压三列）：生成 Word 文档，供旧接口与 AI 助教调用。"""
    import chardet
    import pandas as pd
    from docx import Document
    from docx.oxml.ns import qn

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
        normalized = [str(c).strip().lower().replace(" ", "") for c in cols]

        def find(keywords, fallback):
            for keyword in keywords:
                if keyword in normalized:
                    return cols[normalized.index(keyword)]
            for c, norm in zip(cols, normalized):
                if any(k in norm for k in ("温度", "时间", "t(")):
                    if keywords[0] in ("t",):
                        return c
            return cols[fallback] if fallback < len(cols) else cols[0]

        temp_col = find(("t", "t(°c)", "温度"), 0)
        out_col = find(("u", "u(mv)", "电压", "输出"), 1)
        ref_col = find(("ur1", "u_r1", "参考电压"), 2) if len(cols) > 2 else None

        temps = pd.to_numeric(data[temp_col], errors='coerce')
        outputs = pd.to_numeric(data[out_col], errors='coerce')
        refs = pd.to_numeric(data[ref_col], errors='coerce') if ref_col else None
        if ref_col:
            valid = temps.notna() & outputs.notna() & refs.notna()
        else:
            valid = temps.notna() & outputs.notna()
        temps = temps[valid].reset_index(drop=True)
        outputs = outputs[valid].reset_index(drop=True)
        if ref_col:
            refs = refs[valid].reset_index(drop=True)
        if len(temps) == 0:
            raise ValueError("没有可用的数据行")

        docu = Document()
        style_doc_font(docu)
        docu.add_heading(name(), level=0)
        docu.add_paragraph("温度传感器特性（旧版 CSV 流程）")
        docu.add_paragraph()

        table = docu.add_table(rows=len(temps) + 1, cols=3 if ref_col else 2, style='Table Grid')
        headers = [str(temp_col), str(out_col)] + ([str(ref_col)] if ref_col else [])
        for j, header in enumerate(headers):
            table.rows[0].cells[j].text = header
        for i in range(len(temps)):
            table.rows[i + 1].cells[0].text = '{:.1f}'.format(temps.iloc[i])
            table.rows[i + 1].cells[1].text = '{:.1f}'.format(outputs.iloc[i])
            if ref_col:
                table.rows[i + 1].cells[2].text = '{:.1f}'.format(refs.iloc[i])
        docu.add_paragraph()

        if ref_col and refs.notna().all():
            r1 = 1.0
            resistances = [r1 * u / r for u, r in zip(outputs, refs)]
            x_values = [1.0 / (t + _KELVIN) for t in temps]
            y_values = [math.log(r) for r in resistances]
            fit = _linear_fit(x_values, y_values)
            docu.add_paragraph("NTC 恒压源电流法：R_t = R1·U_Rt/U_R1（R1 = 1.0 kΩ）")
            docu.add_paragraph("ln(R_t) 对 1/T 拟合：ln R_t = {:.4f} + ({:.2f})(1/T)，r = {:.5f}".format(
                fit["intercept"], fit["slope"], fit["correlation"]))
            docu.add_paragraph("材料常数 B = {:.1f} K".format(fit["slope"]))
        else:
            fit = _linear_fit(list(temps), list(outputs))
            kind = _sensor_classify(fit["slope"], "auto")
            docu.add_paragraph("U 对 t 拟合：U = {:.3f} + ({:.4f})t，R² = {:.5f}，r = {:.5f}".format(
                fit["intercept"], fit["slope"], fit["r2"], fit["correlation"]))
            docu.add_paragraph("灵敏度 K = ΔU/Δt = {:.4f} mV/°C → {}".format(fit["slope"], kind))
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("NTC：R_t = R_0 e^{B(1/T - 1/T_0)}，\\ln R_t = B(1/T - 1/T_0) + \\ln R_0")
        docu.add_paragraph("PN 结：U = BT + U_{go}；LM35：U_0 = (10 mV/°C)·t")
        docu.add_paragraph("灵敏度：K = \\Delta U / \\Delta t")

        docu.save(workpath + name() + ".docx")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
