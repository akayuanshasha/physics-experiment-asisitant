"""数字体温计实验模块（一级大物热学实验 —— 数字体温计 B）。

实验内容（对应《数字体温计B（实验指导）》）：
一、基础内容
  1. 掌握基本仪器（直流信号源、数字万用表、磁力搅拌器等）的使用；
  2. 观测平衡电桥的灵敏度（sensitivity 表：ΔR–U 逐点灵敏度与理论灵敏度对比）；
  3. 掌握非平衡电桥的线性特性（bridge 表 δ、U_理论、相对偏差列）。
二、提升内容
  1. 设计制作 30.00~45.00 ℃ 的数字体温计（bridge 表 U–t 线性拟合）；
  2. 测量 Pt1000 的电阻温度系数 α；
  3. 确定 Pt1000 在 0 ℃ 时的电阻值 R(0℃)。
三、进阶内容
  1. 对制作的数字体温计进行校准（calib 表：标准表/数字表逐点比对，求修正量）；
  2. 调整电路参数使数字万用表 200 mV 档电压值与温度值相同
     （37.00 ℃ ↔ 37.00 mV，由 t_target / u_target 参数计算所需激励电压 E）。
四、高阶内容
  1. 定量研究非平衡电桥的线性与非线性特性（nonlinear 表：大 δ 范围
     实测输出与精确电桥输出对比，理论偏差 δ/(1+K)）。

物理公式：
  电桥输出（分压原理）：U = (R2·Rx − R1·R3)/[(R1+Rx)(R2+R3)]·E
  预调平衡条件：R1·R3 = R2·Rx（起始点 U = 0）
  设 K = R2/R3，δ = ΔRx/R0：U = Kδ/[(1+K+δ)(1+K)]·E
  线性近似（δ≪1）：U = Kδ/(1+K)²·E，K = 1 时 U = E·δ/4
  Pt1000 铂热电阻：Rt = R0[1 + α(t − t0)]，δ = α(t − t0)
  由 U–t 拟合斜率 m：α = m(1+K)²/(K·E)
  Rx(t0) = R1·R3/R2，R(0℃) = Rx(t0)/(1 + α·t0)
  平衡电桥灵敏度：S0 = E·K/[(1+K)²·R0]
  线性近似相对精确输出的偏差：δ/(1+K)（K = 1 时 δ/2）

网页流程（新版结构化接口）：
1. schema() 声明四个输入表与桥路/进阶参数；
2. preview() 实时回填只读列并给出 U–t 拟合、α 与 R(0℃)、电桥灵敏度、
   校准修正量、非线性定量分析（calc_results + fit_notes）；
3. handle_structured() 生成 U–t 曲线（含 37 ℃↔37 mV 目标点）、灵敏度曲线、
   校准曲线、非线性对比图与 Word 报告。

旧版 CSV 流程 handle() 保留（T/U/R1/R2(=R3)/E 五列），供旧接口与 AI 助教调用。
"""

import math
import os
import traceback
from typing import Any

import numpy as np

from head import *  # 万能头：np/pd/plt/chardet/Document/qn/analyse_lsm/analyse_com/insert_data_* 等
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    structured_result,
)
from theory_content import get_table_theory

# 桥路参数默认值（与示例数据一致：30℃ 预调平衡，R1=1021Ω，R2=R3=1000Ω，E=2V）
_R1_DEFAULT = 1021.0
_R2_DEFAULT = 1000.0
_R3_DEFAULT = 1000.0
_E_DEFAULT = 2.0
_T_TARGET_DEFAULT = 37.0
_U_TARGET_DEFAULT = 37.0

# 置信概率 P=0.95 的 t 因子（按自由度 ν=n-1）
_T95 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45,
        7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23}

# 示例数据（与 b_static/experiment/exp17/数字体温计（示例数据）.csv 一致）
_BRIDGE_SAMPLE = [
    [30, 0.00], [31, 0.99], [32, 1.77], [33, 2.44], [34, 3.37], [35, 4.17],
    [36, 5.10], [37, 6.26], [38, 7.65], [39, 8.39], [40, 9.77], [41, 11.11],
    [42, 12.49], [43, 14.06], [44, 15.61], [45, 17.24],
]
# 平衡点附近改变 ΔR 观测输出（R0 = R1·R3/R2 = 1021 Ω，S0 = E/(4R0) ≈ 0.4897 mV/Ω）
_SENS_SAMPLE = [[5, 2.45], [10, 4.90], [15, 7.34], [20, 9.79], [25, 12.23]]
# 校准比对（数字表读数系统性偏高约 0.21 ℃）
_CALIB_SAMPLE = [
    [31, 31.23], [33, 33.18], [35, 35.25], [37, 37.16],
    [39, 39.22], [41, 41.19], [43, 43.24],
]
# 大 δ 范围（30~60 ℃，U 按线性模型 500δ 生成，δ = 0.00229867·(t−30)）
_NONLIN_SAMPLE = [
    [30, 0.00], [32, 2.30], [34, 4.60], [36, 6.90], [38, 9.19], [40, 11.49],
    [42, 13.79], [44, 16.09], [46, 18.39], [48, 20.69], [50, 22.99], [52, 25.29],
    [54, 27.58], [56, 29.88], [58, 32.18], [60, 34.48],
]


def name():  # 返回实验名称
    return "数字体温计"


# ─────────────────────────────────────────────
# 通用辅助函数
# ─────────────────────────────────────────────
def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _t_factor(dof: int) -> float:
    """P=0.95 的 t 因子；自由度超出表范围时用大样本近似 2.0。"""
    return _T95.get(dof, 2.0)


def _param_number(parameters: dict[str, Any], key: str, label: str,
                  default: float | None = None) -> float | None:
    """读取参数数值；缺失时用默认值，非数字时报错。"""
    raw = (parameters or {}).get(key)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError("{}必须为数字".format(label))


def _bridge_params(parameters: dict[str, Any]) -> dict[str, float]:
    """读取桥路参数，返回 {r1, r2, r3, e_v, K=R2/R3, e_mv}。"""
    return {
        "r1": _param_number(parameters, "R1", "平衡电阻 R1", _R1_DEFAULT),
        "r2": _param_number(parameters, "R2", "桥臂电阻 R2", _R2_DEFAULT),
        "r3": _param_number(parameters, "R3", "桥臂电阻 R3", _R3_DEFAULT),
        "e_v": _param_number(parameters, "E", "激励电压 E", _E_DEFAULT),
    }


def _k_e(parameters: dict[str, Any]) -> tuple[float, float, float]:
    """返回 (K, e_mv, r0)，r0 为平衡时被测臂阻值 R1·R3/R2。"""
    params = _bridge_params(parameters)
    k_value = params["r2"] / params["r3"] if params["r3"] else 0.0
    return k_value, params["e_v"] * 1000.0, params["r1"] * params["r3"] / params["r2"] if params["r2"] else 0.0


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


def _xy_pairs(rows, x_col, y_col):
    """从行对象中提取 (x, y) 数值对，跳过缺失项。"""
    xs, ys = [], []
    for r in rows:
        x = as_number(r.get(x_col))
        y = as_number(r.get(y_col))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    return np.array(xs, dtype=float), np.array(ys, dtype=float)


def _row_derived(u, k_value, e_mv):
    """单数据点的自动列：(δ, U_理论/mV, 相对偏差/%)。

    δ 按线性关系 δ = U(1+K)²/(K·E) 由实测 U 反算；
    U_理论 为电桥精确输出 U = E·K·δ/[(1+K+δ)(1+K)]；
    相对偏差 = (U − U_理论)/U_理论 × 100%，逐点量化电桥非线性。
    """
    if u is None or k_value <= 0 or e_mv <= 0:
        return "", "", ""
    delta = u * (1 + k_value) ** 2 / (k_value * e_mv)
    if delta == 0:
        return formatted(0.0, 5), formatted(0.0, 4), "0.00"
    denom = (1 + k_value + delta) * (1 + k_value)
    if denom == 0:
        return formatted(delta, 5), "", ""
    u_exact = e_mv * k_value * delta / denom
    dev = (u - u_exact) / u_exact * 100.0 if u_exact else None
    return formatted(delta, 5), formatted(u_exact, 4), formatted(dev, 2)


# ─────────────────────────────────────────────
# 各表计算
# ─────────────────────────────────────────────
def _calc_bridge(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """U–t 线性拟合：灵敏度 m、电阻温度系数 α、0 ℃ 阻值 R(0℃)、进阶目标点校准。"""
    t_arr, u_arr = _xy_pairs(rows, "c0", "c1")
    if len(t_arr) < 3:
        raise ValueError("电桥输出–温度表有效数据点不足（至少 3 个），无法拟合")
    k_value, e_mv, _ = _k_e(parameters)
    if k_value <= 0 or e_mv <= 0:
        raise ValueError("桥路参数 K = R2/R3 与激励电压 E 必须大于 0")

    params = _bridge_params(parameters)
    fit = _linear_fit(list(t_arr), list(u_arr))
    t0 = float(t_arr[int(np.argmin(np.abs(u_arr)))])
    alpha = fit["slope"] * (1 + k_value) ** 2 / (k_value * e_mv)
    alpha_unc = abs(alpha * fit["slope_unc"] / fit["slope"]) if fit["slope"] else 0.0
    rx_t0 = params["r1"] * params["r3"] / params["r2"]
    denom = 1 + alpha * t0
    r0 = rx_t0 / denom if denom else None
    r0_unc = abs(r0 * t0 * alpha_unc / denom) if (r0 is not None and denom) else 0.0

    lines: list[str] = []
    lines.append("拟合方程：U = {:.4f}·t {:+.4f} mV，r = {:.6f}，R² = {:.6f}".format(
        fit["slope"], fit["intercept"], fit["correlation"], fit["r2"]))
    lines.append("灵敏度（斜率）m ≈ {:.4f} mV/℃，u_m ≈ {:.4f} mV/℃（P=0.95）".format(
        fit["slope"], fit["slope_unc"]))
    lines.append("电阻温度系数 α = m(1+K)²/(K·E) ≈ {:.6f} ℃⁻¹（{:.2e} ℃⁻¹），u_α ≈ {:.2e} ℃⁻¹".format(
        alpha, alpha, alpha_unc))
    lines.append("预调平衡温度 t0 = {:.2f} ℃（|U| 最小的点），Rx(t0) = R1·R3/R2 = {:.1f} Ω".format(
        t0, rx_t0))
    lines.append("0 ℃ 时阻值 R(0℃) = Rx(t0)/(1+α·t0) ≈ {:.1f} Ω，u_R ≈ {:.1f} Ω".format(
        r0, r0_unc))

    # 进阶：电压值与温度值相同（37.00 ℃ ↔ 37.00 mV）
    t_target = _param_number(parameters, "t_target", "目标温度 t_target", _T_TARGET_DEFAULT)
    u_target = _param_number(parameters, "u_target", "目标电压 u_target", _U_TARGET_DEFAULT)
    if t_target is not None and u_target is not None and u_target > 0 and alpha:
        if abs(t_target - t0) > 1e-9:
            e_target_mv = u_target * (1 + k_value) ** 2 / ((t_target - t0) * k_value * alpha)
            lines.append("进阶·单点校准：使 {:.2f} ℃ ↔ {:.2f} mV，所需激励电压 E ≈ {:.3f} V".format(
                t_target, u_target, e_target_mv / 1000.0))
        e_1mv = (1 + k_value) ** 2 / (k_value * alpha)
        lines.append("进阶·灵敏度校准：E = (1+K)²/(K·α) ≈ {:.3f} V 时灵敏度恰为 1 mV/℃，"
                     "读数数值 = t − t0".format(e_1mv / 1000.0))

    return {"lines": lines, "t": list(t_arr), "u": list(u_arr), "fit": fit,
            "alpha": alpha, "alpha_unc": alpha_unc, "r0": r0, "r0_unc": r0_unc,
            "t0": t0, "rx_t0": rx_t0, "k": k_value, "e_mv": e_mv}


def _calc_sensitivity(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """平衡电桥灵敏度：逐点 S = U/ΔR，平均并与理论 S0 = E·K/[(1+K)²·R0] 对比。"""
    pairs: list[tuple[float, float]] = []
    for index, row in enumerate(rows or [], start=1):
        dr = as_number(row.get("c0"))
        u = as_number(row.get("c1"))
        if dr is None and u is None:
            continue
        if dr is None or u is None:
            raise ValueError("灵敏度表第 {} 行数据不完整".format(index))
        if dr == 0:
            raise ValueError("灵敏度表第 {} 行 ΔR 为 0，无法计算灵敏度".format(index))
        pairs.append((dr, u))
    if len(pairs) < 2:
        raise ValueError("灵敏度表有效数据不足（至少 2 行）")

    k_value, e_mv, r0_bridge = _k_e(parameters)
    if k_value <= 0 or e_mv <= 0 or r0_bridge <= 0:
        raise ValueError("桥路参数 K = R2/R3 与激励电压 E 必须大于 0")

    s_values = [u / dr for dr, u in pairs]
    s_mean = sum(s_values) / len(s_values)
    sigma = math.sqrt(sum((s - s_mean) ** 2 for s in s_values) / max(1, len(s_values) - 1))
    u_a = _t_factor(len(s_values) - 1) * sigma / math.sqrt(len(s_values))
    s0 = e_mv * k_value / ((1 + k_value) ** 2 * r0_bridge)

    lines: list[str] = []
    lines.append("逐点灵敏度 S = U/ΔR（mV/Ω）：{}".format("，".join(formatted(s, 4) for s in s_values)))
    lines.append("平均灵敏度 S̄ = {:.4f} mV/Ω，σ = {:.4f} mV/Ω，u_A = {:.4f} mV/Ω（P=0.95，n={}）".format(
        s_mean, sigma, u_a, len(s_values)))
    lines.append("理论灵敏度 S0 = E·K/[(1+K)²·R0] = {:.4f} mV/Ω"
                 "（R0 = Rx(t0) = R1·R3/R2 = {:.1f} Ω）".format(s0, r0_bridge))
    rel = (s_mean - s0) / s0 * 100.0
    lines.append("相对偏差 (S̄−S0)/S0 = {:.2f}%{}".format(
        rel, "，灵敏度与理论一致" if abs(rel) <= 2 else "，偏差偏大，请检查桥臂电阻与读数"))
    return {"lines": lines, "dr": [p[0] for p in pairs], "u": [p[1] for p in pairs],
            "s_mean": s_mean, "s_unc": u_a, "s0": s0, "rel": rel}


def _calc_calib(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """校准：修正量 Δt = t_标准 − t_读数，平均修正公式与线性修正拟合。"""
    pairs: list[tuple[float, float]] = []
    for index, row in enumerate(rows or [], start=1):
        t_std = as_number(row.get("c0"))
        t_dig = as_number(row.get("c1"))
        if t_std is None and t_dig is None:
            continue
        if t_std is None or t_dig is None:
            raise ValueError("校准表第 {} 行数据不完整".format(index))
        pairs.append((t_std, t_dig))
    if len(pairs) < 2:
        raise ValueError("校准表有效数据不足（至少 2 行）")

    dts = [a - b for a, b in pairs]
    dt_mean = sum(dts) / len(dts)
    sigma = math.sqrt(sum((d - dt_mean) ** 2 for d in dts) / max(1, len(dts) - 1))
    u_a = _t_factor(len(dts) - 1) * sigma / math.sqrt(len(dts))

    lines: list[str] = []
    lines.append("修正量 Δt = t_标准 − t_读数（n={}）：Δt̄ = {:.3f} ℃，σ = {:.3f} ℃，u_A = {:.3f} ℃（P=0.95）".format(
        len(dts), dt_mean, sigma, u_a))
    if dt_mean >= 0:
        lines.append("修正公式：t = t_读数 + {:.3f} ℃（读数偏低，应加修正量）".format(dt_mean))
    else:
        lines.append("修正公式：t = t_读数 − {:.3f} ℃（读数偏高，应减修正量）".format(-dt_mean))

    fit = None
    if len(pairs) >= 3:
        fit = _linear_fit([b for a, b in pairs], [a for a, b in pairs])
        lines.append("线性修正 t_标准 = a + b·t_读数：a = {:.3f} ℃，b = {:.4f}，r = {:.6f}".format(
            fit["intercept"], fit["slope"], fit["correlation"]))
        if abs(fit["slope"] - 1) > 0.01:
            lines.append("⚠ b 偏离 1 超过 0.01，灵敏度标定存在系统偏差，宜采用线性修正。")
    else:
        lines.append("数据不足 3 行，未做线性修正拟合。")
    return {"lines": lines, "x": [b for a, b in pairs], "y": [a for a, b in pairs],
            "dt_mean": dt_mean, "dt_unc": u_a, "fit": fit}


def _calc_nonlinear(rows: list[dict[str, Any]], parameters: dict[str, Any]) -> dict[str, Any]:
    """大 δ 范围：实测输出与精确电桥输出对比，理论偏差 δ/(1+K)。"""
    pairs: list[tuple[float, float]] = []
    for index, row in enumerate(rows or [], start=1):
        t = as_number(row.get("c0"))
        u = as_number(row.get("c1"))
        if t is None and u is None:
            continue
        if t is None or u is None:
            raise ValueError("非线性表第 {} 行数据不完整".format(index))
        pairs.append((t, u))
    if len(pairs) < 2:
        raise ValueError("非线性表有效数据不足（至少 2 行）")

    k_value, e_mv, _ = _k_e(parameters)
    if k_value <= 0 or e_mv <= 0:
        raise ValueError("桥路参数 K = R2/R3 与激励电压 E 必须大于 0")

    ts = [p[0] for p in pairs]
    deltas: list[float] = []
    u_exact: list[float] = []
    devs: list[float] = []
    for u in (p[1] for p in pairs):
        delta = u * (1 + k_value) ** 2 / (k_value * e_mv)
        u_e = 0.0 if delta == 0 else e_mv * k_value * delta / ((1 + k_value + delta) * (1 + k_value))
        deltas.append(delta)
        u_exact.append(u_e)
        devs.append((u - u_e) / u_e * 100.0 if u_e else 0.0)

    max_index = int(np.argmax(np.abs(np.array(devs, dtype=float))))
    delta_max = max(deltas)
    expect_max = delta_max / (1 + k_value) * 100.0

    lines: list[str] = []
    lines.append("测量范围 δ = {} ~ {:.5f}（δ = U(1+K)²/(K·E) 由实测 U 反算）".format(
        formatted(min(deltas), 5), delta_max))
    lines.append("最大电桥偏差 (U − U_精确)/U_精确 = {:.2f}%（t = {:.2f} ℃），"
                 "理论预期 δ/(1+K) = {:.2f}%".format(abs(devs[max_index]), ts[max_index], expect_max))
    if delta_max <= 0.01:
        lines.append("δ ≤ 0.01，线性近似偏差小于 1%，电桥处于线性区。")
    else:
        lines.append("δ 已超过 0.01，非线性随 δ 增大逐渐显现；实测偏差与理论 δ/(1+K) 一致即属正常。")
    return {"lines": lines, "t": ts, "u": [p[1] for p in pairs], "u_exact": u_exact,
            "devs": devs, "deltas": deltas,
            "expect": [d / (1 + k_value) * 100.0 for d in deltas]}


# ─────────────────────────────────────────────
# 结构化接口
# ─────────────────────────────────────────────
def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：回填只读列 + 各表计算结果。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    fit_notes: dict[str, list[str]] = {}

    # ── 回填只读列 ──
    try:
        k_value, e_mv, _ = _k_e(parameters)
    except ValueError:
        k_value, e_mv = 0.0, 0.0
    for row in tables.get("bridge", []):
        row["c2"], row["c3"], row["c4"] = _row_derived(as_number(row.get("c1")), k_value, e_mv)
    for row in tables.get("sensitivity", []):
        dr = as_number(row.get("c0"))
        u = as_number(row.get("c1"))
        row["c2"] = formatted(u / dr, 4) if (dr is not None and u is not None and dr != 0) else ""
    calib_rows = tables.get("calib", [])
    dts = [as_number(r.get("c0")) - as_number(r.get("c1")) for r in calib_rows
           if as_number(r.get("c0")) is not None and as_number(r.get("c1")) is not None]
    dt_mean = sum(dts) / len(dts) if len(dts) >= 2 else None
    for row in calib_rows:
        t_std = as_number(row.get("c0"))
        t_dig = as_number(row.get("c1"))
        if t_std is not None and t_dig is not None:
            row["c2"] = formatted(t_std - t_dig, 3)
            row["c3"] = formatted(t_dig + dt_mean, 3) if dt_mean is not None else ""
        else:
            row["c2"], row["c3"] = "", ""
    for row in tables.get("nonlinear", []):
        row["c2"], row["c3"], row["c4"] = _row_derived(as_number(row.get("c1")), k_value, e_mv)

    # ── 各表计算 ──
    handlers = {
        "bridge": (_calc_bridge, ("c0", "c1"), [
            "起始点（如 30.00 ℃）预调电桥平衡（U = 0）：$R_1R_3 = R_2R_x$，电桥输出只反映被测臂 Rx 的变化。",
            "设 K = R2/R3、δ = ΔRx/R0：$U = \\frac{E K \\delta}{(1+K+\\delta)(1+K)}$；δ ≪ 1 时 $U \\approx \\frac{E K \\delta}{(1+K)^2}$，K = 1 时 $U = E\\delta/4$。",
            "Pt1000 铂热电阻：$R_t = R_0[1+\\alpha(t-t_0)]$，故 $m = \\frac{E K \\alpha}{(1+K)^2}$，$\\alpha = \\frac{m(1+K)^2}{KE}$。",
            "0 ℃ 阻值外推：$R_x(t_0)=\\frac{R_1R_3}{R_2}$，$R(0℃)=\\frac{R_x(t_0)}{1+\\alpha t_0}$。",
            "⚠ 拟合相关系数 r 应接近 1；相对偏差 = (U − U_理论)/U_理论 随 δ 增大而增大。",
        ]),
        "sensitivity": (_calc_sensitivity, ("c0", "c1"), [
            "在平衡点附近把被测桥臂电阻改变一个小量 ΔR，测对应输出 U，逐点灵敏度 $S = U/\\Delta R$。",
            "理论灵敏度 $S_0 = \\frac{E K}{(1+K)^2 R_0}$，其中 $R_0$ 为平衡时被测臂阻值 $R_x(t_0) = \\frac{R_1R_3}{R_2}$。",
            "K = 1 时 $S_0 = E/4R_0$：增大 E 或减小 R0 可提高电桥灵敏度。",
            "⚠ ΔR 应保持小量（δ ≪ 1），使输出落在电桥线性区。",
        ]),
        "calib": (_calc_calib, ("c0", "c1"), [
            "以水银温度计为标准，对制作的数字体温计逐点校准，修正量 $\\Delta t = t_{标准} - t_{读数}$。",
            "取平均得修正公式 $t = t_{读数} + \\overline{\\Delta t}$（Δt̄ < 0 表示读数偏高，应减去修正量）。",
            "也可拟合 $t_{标准} = a + b\\,t_{读数}$：斜率 b 接近 1、截距 a 接近 0 说明系统误差小。",
            "⚠ 若 |Δt| 随温度明显增大，说明灵敏度标定有偏差，宜采用线性修正 t = a + b·t_读数。",
        ]),
        "nonlinear": (_calc_nonlinear, ("c0", "c1"), [
            "在大温度范围（如 30~60 ℃）测量，δ 不再远小于 1，线性近似与精确输出出现可观测偏差。",
            "精确输出 $U = \\frac{E K \\delta}{(1+K+\\delta)(1+K)}$，线性近似 $U_0 = \\frac{E K \\delta}{(1+K)^2}$，两者相对偏差 $\\frac{U_0-U}{U} = \\frac{\\delta}{1+K}$（K = 1 时 δ/2）。",
            "δ ≲ 0.01 时偏差小于 1%，可视作线性；δ 增大后非线性逐渐显现，属正常现象。",
            "⚠ 若实测 U 明显偏离精确公式，检查桥臂电阻是否随温度漂移或起始点是否重新调平衡。",
        ]),
    }
    for table_id, (handler, columns, notes) in handlers.items():
        rows = tables.get(table_id, []) or []
        if not any(_has_value(row.get(column)) for row in rows for column in columns):
            continue
        try:
            if handler is _calc_calib:
                calc_results[table_id] = handler(rows)
            else:
                calc_results[table_id] = handler(rows, parameters)
            fit_notes[table_id] = list(notes)
        except ValueError as exc:
            calc_messages.append(str(exc))

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_u_t_chart(workpath: str, info: dict[str, Any], t_target: float | None,
                    u_target: float | None) -> dict[str, Any]:
    """U–t 散点 + 最小二乘拟合直线 + 37 ℃↔37 mV 目标点。"""
    font = _font_properties()
    t_values, u_values, fit = info["t"], info["u"], info["fit"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(t_values, u_values, s=40, color="#2f7fc1", zorder=4, label="测量点")
    t_min, t_max = min(t_values), max(t_values)
    if t_max > t_min:
        xs = np.linspace(t_min, t_max, 200)
        axis.plot(xs, fit["slope"] * xs + fit["intercept"], "-", color="#d94b40",
                  linewidth=1.5, zorder=3, label="最小二乘拟合直线")
    if (t_target is not None and u_target is not None
            and t_min - 2 <= t_target <= t_max + 2):
        axis.plot([t_target], [u_target], marker="*", ms=18, mfc="#e6a23c", mec="#e6a23c",
                  ls="", zorder=5, label="目标点 {:.2f} ℃ ↔ {:.2f} mV".format(t_target, u_target))
    axis.annotate(
        "U = {:.3f}·t {:+.3f}\nm = {:.4f} mV/℃，r = {:.6f}\n$\\alpha$ = {:.2e} ℃$^{{-1}}$".format(
            fit["slope"], fit["intercept"], fit["slope"], fit["correlation"], info["alpha"]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9),
    )
    axis.set_xlabel("温度 t (°C)", fontproperties=font)
    axis.set_ylabel("桥路输出 U (mV)", fontproperties=font)
    axis.set_title("桥路输出–温度关系曲线 U–t", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_u_t.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_u_t.png", "title": "U–t 关系曲线（含目标点）",
            "x_label": "温度 t (°C)", "y_label": "U (mV)"}


def _make_sensitivity_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """灵敏度观测：ΔR–U 散点 + 过原点拟合直线 + 理论直线。"""
    font = _font_properties()
    dr_values, u_values = info["dr"], info["u"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(dr_values, u_values, s=40, color="#2f7fc1", zorder=4, label="测量点")
    x_max = max(dr_values) * 1.08
    xs = np.linspace(0, x_max, 100)
    axis.plot(xs, info["s_mean"] * xs, "-", color="#d94b40", linewidth=1.5,
              zorder=3, label="过原点拟合 U = S̄·ΔR")
    if info["s0"] is not None:
        axis.plot(xs, info["s0"] * xs, "--", color="#3a9d5d", linewidth=1.2,
                  zorder=3, label="理论直线 U = S0·ΔR")
    text = r"$\bar S$ = {:.4f} ± {:.4f} mV/Ω".format(info["s_mean"], info["s_unc"])
    if info["s0"] is not None:
        text += "\n" + r"$S_0$ = {:.4f} mV/Ω，相对偏差 {:.2f}%".format(info["s0"], info["rel"])
    axis.annotate(text, xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
                  fontproperties=font,
                  bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9))
    axis.set_xlim(0, x_max)
    axis.set_ylim(0, max(u_values) * 1.12)
    axis.set_xlabel("ΔR (Ω)", fontproperties=font)
    axis.set_ylabel("U (mV)", fontproperties=font)
    axis.set_title("平衡电桥灵敏度观测：U–ΔR 关系", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_sensitivity.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_sensitivity.png", "title": "电桥灵敏度观测曲线",
            "x_label": "ΔR (Ω)", "y_label": "U (mV)"}


def _make_calib_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """校准曲线：数字表读数–标准表读数散点 + y=x 参考线 + 线性修正。"""
    font = _font_properties()
    x_values, y_values = info["x"], info["y"]
    lower = min(min(x_values), min(y_values)) - 0.2
    upper = max(max(x_values), max(y_values)) + 0.2

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(x_values, y_values, s=40, color="#2f7fc1", zorder=4, label="测量点")
    axis.plot([lower, upper], [lower, upper], "--", color="#d94b40", linewidth=1.2,
              zorder=3, label="y = x（完全一致）")
    fit = info["fit"]
    text = "Δt̄ = {:.3f} ± {:.3f} ℃".format(info["dt_mean"], info["dt_unc"])
    if fit is not None:
        xs = np.linspace(lower, upper, 100)
        axis.plot(xs, fit["slope"] * xs + fit["intercept"], "-", color="#3a9d5d",
                  linewidth=1.2, zorder=3, label="线性修正 t_标准 = a + b·t_读数")
        text += "\nt_标准 = {:.3f} + ({:.4f})t_读数，r = {:.6f}".format(
            fit["intercept"], fit["slope"], fit["correlation"])
    axis.annotate(text, xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
                  fontproperties=font,
                  bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9))
    axis.set_xlim(lower, upper)
    axis.set_ylim(lower, upper)
    axis.set_xlabel("数字体温计读数 t_读数 (°C)", fontproperties=font)
    axis.set_ylabel("水银温度计读数 t_标准 (°C)", fontproperties=font)
    axis.set_title("数字体温计校准曲线", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_calib.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_calib.png", "title": "数字体温计校准曲线",
            "x_label": "t_读数 (°C)", "y_label": "t_标准 (°C)"}


def _make_nonlinear_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """非平衡电桥线性/非线性：上图为 U–t 实测与精确输出对比，下图为偏差与理论预期。"""
    font = _font_properties()
    t_values = np.array(info["t"], dtype=float)
    u_values = np.array(info["u"], dtype=float)
    u_exact = np.array(info["u_exact"], dtype=float)
    devs = np.array(info["devs"], dtype=float)
    expect = np.array(info["expect"], dtype=float)

    figure, (axis_u, axis_dev) = plt.subplots(2, 1, figsize=(7.6, 7.2), sharex=True)
    axis_u.scatter(t_values, u_values, s=36, color="#2f7fc1", zorder=4, label="实测输出 U")
    axis_u.plot(t_values, u_exact, "-", color="#d94b40", linewidth=1.5, zorder=3,
                label="精确电桥输出 U_精确")
    axis_u.set_ylabel("U (mV)", fontproperties=font)
    axis_u.set_title("非平衡电桥线性与非线性特性（高阶）", fontproperties=font)
    axis_u.grid(alpha=0.25)
    if font is not None:
        axis_u.legend(prop=font)
    else:
        axis_u.legend()

    axis_dev.scatter(t_values, devs, s=36, color="#2f7fc1", zorder=4,
                     label="实测偏差 (U−U_精确)/U_精确")
    axis_dev.plot(t_values, expect, "--", color="#e6a23c", linewidth=1.5, zorder=3,
                  label="理论预期 δ/(1+K)")
    max_index = int(np.argmax(np.abs(devs)))
    axis_dev.annotate(
        "最大偏差 {:.2f}%（t = {:.2f} °C）".format(abs(devs[max_index]), t_values[max_index]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9),
    )
    axis_dev.set_xlabel("温度 t (°C)", fontproperties=font)
    axis_dev.set_ylabel("偏差 (%)", fontproperties=font)
    axis_dev.grid(alpha=0.25)
    if font is not None:
        axis_dev.legend(prop=font)
    else:
        axis_dev.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_nonlinear.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_nonlinear.png", "title": "非平衡电桥线性/非线性特性",
            "x_label": "温度 t (°C)", "y_label": "U (mV) / 偏差 (%)"}


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    parameters = payload.get("parameters") or {}
    try:
        for key, label in (("R1", "平衡电阻 R1"), ("R2", "桥臂电阻 R2"),
                           ("R3", "桥臂电阻 R3"), ("E", "激励电压 E")):
            value = _param_number(parameters, key, label)
            if value is None or value <= 0:
                raise ValueError("{}必须大于 0".format(label))
        u_target = _param_number(parameters, "u_target", "目标电压 u_target")
        if u_target is not None and u_target <= 0:
            raise ValueError("目标电压 u_target 必须大于 0")
    except ValueError as exc:
        return {"code": 1, "message": str(exc)}

    result = preview(payload)
    bridge_info = result["calc_results"].get("bridge")
    if bridge_info is None:
        return {"code": 1, "message": "；".join(result["calc_messages"])
                or "请先填写电桥输出–温度测量表（提升实验核心）。"}

    os.makedirs(workpath, exist_ok=True)
    charts: list[dict[str, Any]] = []
    t_target = _param_number(parameters, "t_target", "目标温度 t_target", _T_TARGET_DEFAULT)
    charts.append(_make_u_t_chart(workpath, bridge_info, t_target, u_target))

    sensitivity_info = result["calc_results"].get("sensitivity")
    if sensitivity_info is not None:
        charts.append(_make_sensitivity_chart(workpath, sensitivity_info))
    calib_info = result["calc_results"].get("calib")
    if calib_info is not None:
        charts.append(_make_calib_chart(workpath, calib_info))
    nonlinear_info = result["calc_results"].get("nonlinear")
    if nonlinear_info is not None:
        charts.append(_make_nonlinear_chart(workpath, nonlinear_info))

    warnings: list[str] = []
    correlation = bridge_info["fit"]["correlation"]
    if abs(correlation) < 0.99:
        warnings.append("U–t 相关系数 |r| = {:.4f} < 0.99，线性度欠佳，请检查预调平衡与读数。".format(
            correlation))
    if nonlinear_info is not None and nonlinear_info["devs"]:
        max_dev = max(abs(d) for d in nonlinear_info["devs"])
        if max_dev > 5:
            warnings.append("非线性表最大偏差 {:.2f}% 明显超过 5%，请检查桥臂电阻是否随温度漂移。".format(
                max_dev))

    summary: list[str] = []
    for table_id, label in (("bridge", "电桥输出–温度测量与 Pt1000 参数"),
                            ("sensitivity", "平衡电桥灵敏度"),
                            ("calib", "数字体温计校准"),
                            ("nonlinear", "非平衡电桥线性/非线性特性")):
        if table_id in result["calc_results"]:
            summary.append("【{}】".format(label))
            summary.extend(result["calc_results"][table_id]["lines"])

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        warnings=warnings,
        charts=charts,
    )


# ─────────────────────────────────────────────
# 表结构与示例数据
# ─────────────────────────────────────────────
def _set_units(table: dict[str, Any], units: tuple[str, ...]) -> dict[str, Any]:
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema() -> dict[str, Any]:
    bridge = _set_units(
        make_table(
            "bridge", "电桥输出–温度测量表（提升实验：设计制作 30~45 ℃ 数字体温计）",
            ["温度 t", "桥路输出 U", "δ=ΔR/R₀", "U_理论", "相对偏差"],
            sample=_BRIDGE_SAMPLE,
            readonly=(2, 3, 4),
            min_rows=3, initial_rows=16,
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "温度 t (°C)", "y_label": "桥路输出 U (mV)",
                "title": "U–t 关系曲线", "fit": "linear",
            },
            description=(
                "先在起始点（如 30.00 ℃）预调电桥平衡（U = 0），把 R1/R2/R3 与 E 填入顶部参数栏；"
                "再缓慢加热并开启磁力搅拌，用数字万用表 200 mV 档逐点测量 30~45 ℃ 的桥路输出电压 U。"
                "δ、U_理论、相对偏差由系统自动计算，无需填写。"
            ),
        ),
        ("℃", "mV", "1", "mV", "%"),
    )
    bridge["calc"] = {"label": "拟合 U–t 求 α 与 R(0℃)"}

    sensitivity = _set_units(
        make_table(
            "sensitivity", "平衡电桥灵敏度观测表（基础实验）",
            ["电阻改变量 ΔR", "桥路输出 U", "灵敏度 S=U/ΔR"],
            sample=_SENS_SAMPLE,
            readonly=(2,),
            min_rows=2, initial_rows=5, required=False,
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "ΔR (Ω)", "y_label": "U (mV)",
                "title": "电桥灵敏度观测：U–ΔR 关系", "fit": "linear",
            },
            description=(
                "电桥在起始点预调平衡后，用电阻箱把被测桥臂电阻改变一个小量 ΔR（保持 δ ≪ 1），"
                "用数字万用表 200 mV 档记录对应输出电压 U，逐点计算灵敏度 S = U/ΔR，"
                "并与理论灵敏度 S0 = E·K/[(1+K)²·R0] 对比。"
            ),
        ),
        ("Ω", "mV", "mV/Ω"),
    )
    sensitivity["calc"] = {"label": "计算电桥灵敏度"}

    calib = _set_units(
        make_table(
            "calib", "数字体温计校准表（进阶实验）",
            ["标准表读数 t_标准", "数字表读数 t_读数", "修正量 Δt", "修正后温度 t_修正"],
            sample=_CALIB_SAMPLE,
            readonly=(2, 3),
            min_rows=2, initial_rows=7, required=False,
            chart={
                "x_column": "c1", "y_column": "c0",
                "x_label": "数字表读数 t_读数 (°C)", "y_label": "标准表读数 t_标准 (°C)",
                "title": "数字体温计校准曲线", "fit": "linear",
            },
            description=(
                "以水银温度计为标准，在 31~43 ℃ 内逐点比较标准表与制作的数字体温计的读数，"
                "求修正量 Δt = t_标准 − t_读数，给出修正公式 t = t_读数 + Δt̄。"
            ),
        ),
        ("℃", "℃", "℃", "℃"),
    )
    calib["calc"] = {"label": "计算修正量"}

    nonlinear = _set_units(
        make_table(
            "nonlinear", "非平衡电桥线性/非线性特性研究表（高阶实验）",
            ["温度 t", "桥路输出 U", "δ=ΔR/R₀", "U_精确", "电桥偏差"],
            sample=_NONLIN_SAMPLE,
            readonly=(2, 3, 4),
            min_rows=2, initial_rows=16, required=False,
            chart={
                "x_column": "c0", "y_column": "c1",
                "x_label": "温度 t (°C)", "y_label": "U (mV)",
                "title": "大范围 U–t 关系", "fit": "linear",
            },
            description=(
                "把温度范围扩大到 30~60 ℃（δ 不再远小于 1），逐点测量桥路输出 U，"
                "对比线性近似与精确电桥输出，定量研究非平衡电桥的线性与非线性特性。"
            ),
        ),
        ("℃", "mV", "1", "mV", "%"),
    )
    nonlinear["calc"] = {"label": "定量分析非线性"}
    nonlinear["enabled_by_default"] = False

    parameters = [
        {"id": "R1", "label": "平衡电阻 R1", "unit": "Ω", "type": "number",
         "default": _R1_DEFAULT, "min": 0, "step": "any", "required": True,
         "help": "平衡时桥臂电阻：R1·R3 = R2·Rx，默认与示例数据一致"},
        {"id": "R2", "label": "桥臂电阻 R2", "unit": "Ω", "type": "number",
         "default": _R2_DEFAULT, "min": 0, "step": "any", "required": True,
         "help": "电桥比率 K = R2/R3"},
        {"id": "R3", "label": "桥臂电阻 R3", "unit": "Ω", "type": "number",
         "default": _R3_DEFAULT, "min": 0, "step": "any", "required": True,
         "help": "电桥比率 K = R2/R3"},
        {"id": "E", "label": "激励电压 E", "unit": "V", "type": "number",
         "default": _E_DEFAULT, "min": 0, "step": "any", "required": True,
         "help": "直流信号源输出电压（计算时换算为 mV）"},
        {"id": "t_target", "label": "目标温度 t_target（进阶）", "unit": "℃", "type": "number",
         "default": _T_TARGET_DEFAULT, "step": "any", "required": False,
         "help": "要求电压值与温度值相同：37.00 ℃ 对应 37.00 mV"},
        {"id": "u_target", "label": "目标电压 u_target（进阶）", "unit": "mV", "type": "number",
         "default": _U_TARGET_DEFAULT, "min": 0, "step": "any", "required": False,
         "help": "数字万用表 200 mV 档读数与温度数值相等时的电压值"},
    ]

    theory = get_table_theory("exp17")
    return make_schema(
        (
            "数字体温计：直流非平衡电桥 + Pt1000 铂热电阻。起始点预调电桥平衡后，"
            "测量 30~45 ℃ 的桥路输出电压 " r"$U$" " 与温度 " r"$t$" "，由 "
            r"$U$" r"–$t$" " 直线拟合求 Pt1000 的电阻温度系数 " r"$\alpha$"
            " 与 0 ℃ 时的电阻值 " r"$R(0)$" "；观测平衡电桥灵敏度，对制作的"
            "数字体温计进行校准，并定量研究非平衡电桥的线性与非线性特性。"
        ),
        [bridge, sensitivity, calib, nonlinear],
        parameters=parameters,
        parameters_sample={"R1": _R1_DEFAULT, "R2": _R2_DEFAULT, "R3": _R3_DEFAULT,
                           "E": _E_DEFAULT, "t_target": _T_TARGET_DEFAULT,
                           "u_target": _U_TARGET_DEFAULT},
        analysis_hints=(
            "U–t 数据应近似线性（相关系数 r 接近 1）；由拟合斜率 m 得 α = m(1+K)²/(K·E)，"
            "K = R2/R3；由预调平衡条件 R1R3 = R2·Rx 得 Rx(t0)（t0 为 |U| 最小的温度），"
            "再外推 R(0℃) = Rx(t0)/(1+α·t0)；相对偏差随 δ 增大而增大，"
            "偏差 ≈ δ/(1+K)（K=1 时 δ/2），用于定量判断电桥的线性特性。"
            "思考题：① 取 E = (1+K)²/(K·α)（或按单点校准 E = u_target·(1+K)²/[(t_target−t0)·K·α]），"
            "可使电压读数数值与温度数值相等；② 由相对偏差或 δ 的大小判断线性特性；"
            "③ 在不同温度区间分段拟合斜率，由 α = m(1+K)²/(K·E) 得 α 随温度的变化。"
        ),
        preview_enabled=True,
        report_enabled=False,
        formulas=theory.get("_global", {}).get("formulas", []),
        variables=theory.get("_global", {}).get("variables", []),
        table_theory=theory,
    )


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def _font():
    """返回思源黑体 FontProperties，找不到则返回 None（用 matplotlib 默认字体）。"""
    path = os.environ.get('_B_FONT_PATH')
    if path and os.path.exists(path):
        return matplotlib.font_manager.FontProperties(fname=path)
    return None


def _decorate(ax, title, xlabel, ylabel):
    zhfont = _font()
    if zhfont:
        ax.set_title(title, fontproperties=zhfont, fontsize=14)
        ax.set_xlabel(xlabel, fontproperties=zhfont, fontsize=12)
        ax.set_ylabel(ylabel, fontproperties=zhfont, fontsize=12)
        ax.legend(prop=zhfont, fontsize=10)
    else:
        ax.set_title(title, fontsize=14)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(fontsize=10)


def _save_chart(workpath, filename, title, xlabel, ylabel, x, y,
                fit_x=None, fit_y=None, fit_label=None):
    """绘制散点 + 拟合线并保存到 workpath，返回文件名。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, 'o', color='#4472C4', markersize=5, label='测量数据', zorder=5)
    if fit_x is not None and fit_y is not None:
        ax.plot(fit_x, fit_y, '-', color='#E74C3C', linewidth=2,
                label=fit_label or '拟合曲线')
    _decorate(ax, title, xlabel, ylabel)
    ax.grid(True, linestyle='--', alpha=0.4)
    fig.tight_layout()
    path = os.path.join(workpath, filename)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def _first_number(series):
    """取数列中第一个有效数值，无则返回 None。"""
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.iloc[0]) if len(s) else None


def _pick_column(data, *keywords):
    """按关键字找列：先精确匹配（小写），再包含匹配；找不到返回 None。"""
    lowered = [str(c).strip().lower() for c in data.columns]
    for keyword in keywords:
        if keyword in lowered:
            return data.columns[lowered.index(keyword)]
    for keyword in keywords:
        for c, low in zip(data.columns, lowered):
            if keyword in low:
                return c
    return None


def handle(workpath, extension):
    """旧版单表接口（兼容 b_adapter 等旧调用路径）：
    读取 T/U/R1/R2(=R3)/E → U–t 拟合、α、R(0℃) → Word。
    缺少 R1/R2/E 列时用默认桥路参数（K=1）。"""
    try:
        excelpath = workpath + name() + '.' + extension

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        t_col = _pick_column(data, "t/℃", "t", "温度")
        u_col = _pick_column(data, "u/mv", "u", "电压")
        r1_col = _pick_column(data, "r1/ω", "r1")
        r2_col = _pick_column(data, "r2(=r3)", "r2")
        e_col = _pick_column(data, "e/v", "e")
        if t_col is None or u_col is None:
            raise ValueError("未找到温度/电压列（至少需要 T 与 U 两列）")

        r1 = (_first_number(data[r1_col]) if r1_col is not None else None) or _R1_DEFAULT
        r2 = (_first_number(data[r2_col]) if r2_col is not None else None) or _R2_DEFAULT
        e_v = (_first_number(data[e_col]) if e_col is not None else None) or _E_DEFAULT
        # 旧 CSV 表头为 R2(=R3)，故 R3 = R2，K = 1
        K = 1.0
        e_mv = e_v * 1000.0

        t = pd.to_numeric(data[t_col], errors="coerce")
        u = pd.to_numeric(data[u_col], errors="coerce")
        mask = t.notna() & u.notna()
        t_arr = t[mask].to_numpy(dtype=float)
        u_arr = u[mask].to_numpy(dtype=float)
        if t_arr.size < 2:
            raise ValueError("有效数据点不足（至少 2 个）")

        res_lsm = analyse_lsm(t_arr, u_arr, "t", "U", "mV/℃", "mV")
        t0 = float(t_arr[int(np.argmin(np.abs(u_arr)))])

        imgpath = workpath + "img.jpg"
        t_fit = np.linspace(t_arr.min(), t_arr.max(), 200)
        _save_chart(workpath, "img.jpg",
                    "电压与温度 U–T 关系曲线",
                    "T / ℃", "U / mV", t_arr, u_arr,
                    t_fit, res_lsm.m * t_fit + res_lsm.b, "线性拟合")

        # α = m(1+K)²/(K·E)，E_s = E×1000（mV）
        res_a = analyse_com(r"α=m*(1+K)^2/(K*E_s)", (("m", res_lsm.m, res_lsm.u_m),),
                            (("K", K), ("E_s", e_mv)), "℃^{-1}")
        # 预调平衡时 Rx(t0) = R1R3/R2 = R1（K=1），R(0℃) = Rx(t0)/(1+α·t0)
        res_r0 = analyse_com(r"R_0=R_1/(1+α*t_0)",
                             (("α", float(res_a.ans), float(res_a.unc)),),
                             (("R_1", r1), ("t_0", t0)), "Ω")

        docu = Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("实验参数：R1 = {} Ω，R2 = R3 = {} Ω，E = {} V，预调平衡温度 t0 = {} ℃".format(
            formatted(r1, 2), formatted(r2, 2), formatted(e_v, 3), formatted(t0, 2)))
        docu.add_paragraph()
        docu.add_picture(imgpath)
        docu.add_paragraph()

        insert_data_lsm(docu, res_lsm, "word")
        docu.add_paragraph("由 m = K·α·E/(1+K)² 得 Pt1000 电阻温度系数")
        insert_data_com(docu, "α", res_a, "word")
        docu.add_paragraph("由平衡条件 R1R3 = R2Rx，Rx(t0) = R1R3/R2 = {} Ω".format(formatted(r1, 2)))
        insert_data_com(docu, "Pt1000 在 0℃ 时的电阻值 R(0℃)", res_r0, "word")

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("斜率")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph("截距")
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph("相关系数")
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph("电阻温度系数")
        docu.add_paragraph(res_a.ansx)
        docu.add_paragraph(res_a.uncx)
        docu.add_paragraph(res_a.finalx)
        docu.add_paragraph("零摄氏度时的阻值")
        docu.add_paragraph(res_r0.ansx)
        docu.add_paragraph(res_r0.uncx)
        docu.add_paragraph(res_r0.finalx)

        docu.save(workpath + name() + ".docx")

        os.remove(imgpath)
        return 0  # 若成功，返回0
    except Exception:
        traceback.print_exc()  # 打印错误
        return 1  # 若失败，返回1
