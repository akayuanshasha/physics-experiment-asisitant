"""RGB 配色实验模块（一级大物光学实验 —— 配色实验 B）。

实验内容（对应《配色实验B（实验指导）》）：
一、基础内容
  1. LED 正向伏安特性测量：在 I ≤ 100 mA 内分别测量红、绿、蓝 LED 的
     工作电流 I 与工作电压 U 的关系，绘制正向 I-U 特性曲线；
  2. 基于伏安关系计算红、绿、蓝三色 LED 的发光峰值波长
     （λ = 1240/E_g，E_g 取由曲线读出的阈值电压），
     并计算绿光 LED 峰值波长的标准不确定度。
二、提升内容
  1. 绿色 LED 的相对光强 L 与工作电流 I 特性（L-I 曲线）。
三、进阶内容
  1. 两个 LED 相加混色（黄/青/紫），扣除背景光强后给出两基色光强比；
  2. 三个 LED 相加混色（白），扣除背景光强后给出三基色光强比。
四、高阶内容
  1. 白光通过滤光片的颜色变化（定性观察）；
  2. 用三基色 LED 配出颜料创造的色彩，给出基色光强比。

物理公式：
  I = I0·(e^{bU} - 1)          （LED 正向伏安特性，对 I>0 的点做 ln I 对 U 线性拟合）
  λ = 1240 / E_g               （E_g 单位 eV，数值上取阈值电压 U_th/V，λ 单位 nm）
  u_B(U_th) = ΔU / √3          （B 类标准不确定度，ΔU 为万用表电压档分辨率）
  u_A(U_th) = t(n-1)·σ / √n    （同一 LED 多次读数的 A 类不确定度）
  u(λ) = (λ / U_th) · √(u_A² + u_B²)
  L' = L - L0                  （扣除背景光强后的相对光强）

网页流程（新版结构化接口）：
1. schema() 声明六个输入表与实验参数；
2. preview() 实时给出伏安特性指数拟合、峰值波长与不确定度、L-I 线性拟合、
   混色扣背景光强与光强比（含相加混色可加性校核）；
3. handle_structured() 生成 I-U 特性曲线、波长光谱图、L-I 曲线、混色柱状图与 Word 报告。

旧版 CSV 流程 handle() 保留（U 与红/绿/蓝三路电流），供旧接口与 AI 助教调用。
"""

from __future__ import annotations

import math
import os
import traceback
from typing import Any

import numpy as np

from structured_support import as_number, copied_tables, formatted, make_schema, make_table, structured_result
from theory_content import get_table_theory

# ── 常数与判据 ──
_LAM_NM = 1240.0                 # λ = 1240/E_g（E_g 以 eV 计，λ 以 nm 计）
_VISIBLE = (380.0, 780.0)        # 可见光波长范围（nm）
# CIE 标准三基色波长（nm）与相对视敏函数（实验指导）
_CIE_LAM = {"红": 700.0, "绿": 546.1, "蓝": 435.8}
_CIE_V = {"红": 0.0041, "绿": 0.975, "蓝": 0.0173}
# 三基色 LED：（I-U 表列 ID，图例名，绘图颜色）
_COLORS = (
    ("c1", "红色LED", "#E74C3C"),
    ("c2", "绿色LED", "#27AE60"),
    ("c3", "蓝色LED", "#2980B9"),
)
# 置信概率 P=0.95 的 t 因子（按自由度 ν=n-1）
_T95 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45,
        7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23}


def name():
    return "配色实验"


# ──────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────

def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


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


def _t_factor(dof: int) -> float:
    """P=0.95 的 t 因子；自由度超出表范围时用大样本近似 2.0。"""
    return _T95.get(dof, 2.0)


def _fit_diode(u_values: list[float], i_values: list[float]):
    """线性化拟合伏安特性 I = I0·(e^{bU}-1)：对 I>0 的点做 ln I 对 U 拟合。

    返回 (I0, b, r²)；I>0 的有效点不足 3 个时返回 None。
    """
    points = [(u, i) for u, i in zip(u_values, i_values) if i > 0]
    if len(points) < 3:
        return None
    xs = [p[0] for p in points]
    ys = [math.log(p[1]) for p in points]
    fit = _linear_fit(xs, ys)
    return math.exp(fit["intercept"]), fit["slope"], fit["r2"]


def _ratio_text(values):
    """把扣除背景后的光强列表规范成以首项为 1 的光强比文本，如 "1.000 : 0.788"。"""
    if any(v is None for v in values) or any(v <= 0 for v in values):
        return ""
    base = values[0]
    return " : ".join(formatted(v / base, 3) for v in values)


def _led_color(label: str) -> str:
    """按颜色名给 LED 分配绘图颜色。"""
    for key, color in (("红", "#E74C3C"), ("绿", "#27AE60"), ("蓝", "#2980B9")):
        if key in label:
            return color
    return "#8a8f98"


# ──────────────────────────────────────────────
# 各表计算
# ──────────────────────────────────────────────

def _calc_iv(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """三基色 LED 正向伏安特性：指数拟合 I = I0·(e^{bU}-1)。"""
    series: list[dict[str, Any]] = []
    lines: list[str] = []
    for cid, label, color in _COLORS:
        u_values: list[float] = []
        i_values: list[float] = []
        for row in rows:
            u = as_number(row.get("c0"))
            i = as_number(row.get(cid))
            if u is not None and i is not None:
                u_values.append(u)
                i_values.append(i)
        fit = _fit_diode(u_values, i_values)
        if fit is not None:
            i0, b_value, r2 = fit
            lines.append("{}：I = I₀·(e^{{bU}} − 1)，I₀ ≈ {:.3e} mA，b ≈ {:.2f} 1/V，"
                         "ln I–U 线性 r² = {:.5f}".format(label, i0, b_value, r2))
        elif len(u_values) >= 2:
            lines.append("{}：指数拟合失败（I>0 的有效点不足 3 个）。".format(label))
        elif not u_values:
            lines.append("{}：无有效数据。".format(label))
        series.append({"label": label, "color": color, "u": u_values, "i": i_values,
                       "i0": fit[0] if fit else None,
                       "b": fit[1] if fit else None,
                       "r2": fit[2] if fit else None})
    return {"lines": lines, "series": series}


def _threshold_marks(wl_rows: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """从峰值波长表读取各基色阈值电压，供 I-U 图中标出。"""
    marks = []
    for _cid, label, color in _COLORS:
        for row in wl_rows:
            if label[0] in str(row.get("c0") or ""):
                u_th = as_number(row.get("c1"))
                if u_th is not None:
                    marks.append((color, u_th))
                break
    return marks


def _calc_wavelength(rows: list[dict[str, Any]], du: float) -> dict[str, Any]:
    """峰值波长计算：按颜色分组统计阈值电压，λ = 1240/U_th，A 类 + B 类合成不确定度。"""
    groups: dict[str, list[float]] = {}
    order: list[str] = []
    for index, row in enumerate(rows or [], start=1):
        label = str(row.get("c0") or "").strip()
        u_th = as_number(row.get("c1"))
        if not label and u_th is None:
            continue
        if not label:
            raise ValueError("峰值波长表第 {} 行缺少 LED 颜色名称".format(index))
        if u_th is None:
            raise ValueError("峰值波长表第 {} 行缺少阈值电压 U_th".format(index))
        if u_th <= 0:
            raise ValueError("峰值波长表第 {} 行阈值电压必须大于 0".format(index))
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(u_th)
    if not groups:
        raise ValueError("请填写峰值波长表（LED 颜色、阈值电压 U_th）")

    u_b = du / math.sqrt(3.0)
    lines: list[str] = []
    entries: list[dict[str, Any]] = []
    green_line = None
    for label in order:
        values = groups[label]
        count = len(values)
        mean = sum(values) / count
        sigma = 0.0
        if count > 1:
            sigma = math.sqrt(sum((v - mean) ** 2 for v in values) / (count - 1))
        u_a = _t_factor(count - 1) * sigma / math.sqrt(count) if count > 1 and sigma > 0 else 0.0
        u_th_total = math.sqrt(u_a ** 2 + u_b ** 2)
        lam = _LAM_NM / mean
        u_lam = lam / mean * u_th_total
        in_band = _VISIBLE[0] <= lam <= _VISIBLE[1]

        if count > 1:
            lines.append("{}：U_th = ({:.3f} ± {:.3f}) V（{} 次读数，u_A = {:.4f} V，u_B = {:.4f} V）".format(
                label, mean, u_th_total, count, u_a, u_b))
        else:
            lines.append("{}：U_th = {:.3f} V，B 类 u(U_th) = ΔU/√3 = {:.4f} V".format(
                label, mean, u_b))
        lines.append("{}：λ = 1240/U_th = {:.1f} nm，u(λ) = {:.1f} nm{}".format(
            label, lam, u_lam,
            "（在可见光区 380~780 nm 内）" if in_band else "（⚠ 超出可见光区 380~780 nm，请检查阈值电压）"))
        for key, cie_lam in _CIE_LAM.items():
            if key in label:
                lines.append("对照 CIE {}基色波长 {} nm（相对视敏函数 {}）——LED 实测值落在对应色区即合理，"
                             "与 CIE 标准基色的数值差异属固有差异。".format(
                                 key, cie_lam, _CIE_V[key]))
                break
        entries.append({"label": label, "color": _led_color(label),
                        "lam": lam, "u_lam": u_lam, "mean": mean, "u_th": u_th_total})
        if "绿" in label:
            green_line = "绿光 LED 峰值波长 λ = ({:.1f} ± {:.1f}) nm（k=1）".format(lam, u_lam)
    if green_line:
        lines.append(green_line)
    return {"lines": lines, "entries": entries}


def _calc_li(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """绿色 LED 发光强度特性：L 对 I 线性拟合。"""
    i_values: list[float] = []
    l_values: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        if not any(_has_value(row.get(column)) for column in ("c0", "c1")):
            continue
        i = as_number(row.get("c0"))
        l = as_number(row.get("c1"))
        if i is None or l is None:
            raise ValueError("发光强度表第 {} 行数据不完整".format(index))
        i_values.append(i)
        l_values.append(l)
    if not i_values:
        raise ValueError("请填写发光强度特性表（工作电流 I、相对光强 L）")

    fit = _linear_fit(i_values, l_values)
    lines = [
        "L 对 I 拟合：L = {:.3f} + ({:.4f})I，R² = {:.5f}，相关系数 r = {:.5f}".format(
            fit["intercept"], fit["slope"], fit["r2"], fit["correlation"]),
        "低中电流区（约 ≤ 60 mA）发光强度近似随电流线性增长，斜率即光强灵敏度 {:.4f} mV/mA。".format(
            fit["slope"]),
    ]
    return {"lines": lines, "x": i_values, "y": l_values, "fit": fit}


def _mix_components(name_text: str) -> list[tuple[str, str]]:
    """按混色名称推断参与混色的基色（用于绘图配色）。"""
    if "黄" in name_text:
        return [("红", "#E74C3C"), ("绿", "#27AE60")]
    if "青" in name_text:
        return [("绿", "#27AE60"), ("蓝", "#2980B9")]
    if "紫" in name_text:
        return [("蓝", "#2980B9"), ("红", "#E74C3C")]
    return [("基色1", "#2f7fc1"), ("基色2", "#3a9d5d")]


def _calc_mix2(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """两色相加混色：扣除背景光强、光强比、可加性校核（L_混' 与 L1'+L2' 比较）。"""
    lines: list[str] = []
    chart_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows or [], start=1):
        name_text = str(row.get("c0") or "").strip() or "混色{}".format(index)
        l1 = as_number(row.get("c1"))
        l2 = as_number(row.get("c2"))
        l_mix = as_number(row.get("c3"))
        l0 = as_number(row.get("c4"))
        if l1 is None and l2 is None and l_mix is None and l0 is None:
            continue
        if l1 is None or l2 is None or l0 is None:
            raise ValueError("两色混色表第 {} 行基色光强或背景光强不完整".format(index))
        l1p = l1 - l0
        l2p = l2 - l0
        lmp = l_mix - l0 if l_mix is not None else None
        ratio = _ratio_text([l1p, l2p])
        line = "{}：L1' = {:.2f}，L2' = {:.2f} mV，光强比 L1':L2' = {}".format(
            name_text, l1p, l2p, ratio or "无法给出（存在非正光强）")
        comps = _mix_components(name_text)
        if lmp is not None and l1p + l2p > 0:
            deviation = (lmp - (l1p + l2p)) / (l1p + l2p) * 100
            line += "；混色实测 L_混' = {:.2f} mV，与两基色之和 {:.2f} mV 偏差 {:+.1f}%{}".format(
                lmp, l1p + l2p, deviation,
                "" if abs(deviation) <= 10 else "（⚠ 偏差偏大，检查相加混色条件）")
        elif lmp is not None:
            line += "；混色实测 L_混' = {:.2f} mV".format(lmp)
        lines.append(line)
        chart_rows.append({
            "name": name_text,
            "comps": [(comps[0][0], comps[0][1], l1p), (comps[1][0], comps[1][1], l2p)],
            "sum": l1p + l2p if (l1p is not None and l2p is not None) else None,
            "measured": lmp,
        })
    if not lines:
        raise ValueError("请填写两色混色表（混色名称、两基色光强、混色光强、背景光强）")
    return {"lines": lines, "rows": chart_rows}


def _calc_mix3(rows: list[dict[str, Any]], pigment: bool = False) -> dict[str, Any]:
    """三色相加混色（配白 / 颜料色）：扣除背景光强、三基色光强比、可加性校核。"""
    lines: list[str] = []
    chart_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows or [], start=1):
        if pigment:
            name_text = str(row.get("c0") or "").strip() or "色彩{}".format(index)
            value_cols = ("c1", "c2", "c3")
            mix_col, l0_col = "c4", "c5"
            title_prefix = "{}：".format(name_text)
        else:
            name_text = "配白"
            value_cols = ("c0", "c1", "c2")
            mix_col, l0_col = "c3", "c4"
            title_prefix = "白色混色："
        vals = [as_number(row.get(c)) for c in value_cols]
        l_mix = as_number(row.get(mix_col))
        l0 = as_number(row.get(l0_col))
        if all(v is None for v in vals) and l_mix is None and l0 is None:
            continue
        if any(v is None for v in vals) or l0 is None:
            raise ValueError("三色混色表第 {} 行基色光强或背景光强不完整".format(index))
        diffs = [v - l0 for v in vals]
        ratio = _ratio_text(diffs)
        line = title_prefix + "L_R' = {:.2f}，L_G' = {:.2f}，L_B' = {:.2f} mV，光强比 = {}".format(
            diffs[0], diffs[1], diffs[2], ratio or "无法给出（存在非正光强）")
        comps = [("红", "#E74C3C", diffs[0]), ("绿", "#27AE60", diffs[1]), ("蓝", "#2980B9", diffs[2])]
        if l_mix is not None and sum(diffs) > 0:
            deviation = (l_mix - l0 - sum(diffs)) / sum(diffs) * 100
            line += "；混色实测 L_混' = {:.2f} mV，与三基色之和 {:.2f} mV 偏差 {:+.1f}%{}".format(
                l_mix - l0, sum(diffs), deviation,
                "" if abs(deviation) <= 10 else "（⚠ 偏差偏大，检查相加混色条件）")
        elif l_mix is not None:
            line += "；混色实测 L_混' = {:.2f} mV".format(l_mix - l0)
        lines.append(line)
        chart_rows.append({
            "name": name_text,
            "comps": comps,
            "sum": sum(diffs),
            "measured": l_mix - l0 if l_mix is not None else None,
        })
    if not lines:
        raise ValueError("请填写三色混色表（三基色光强、混色光强、背景光强）")
    return {"lines": lines, "rows": chart_rows}


# ──────────────────────────────────────────────
# 结构化接口
# ──────────────────────────────────────────────

def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：补全只读列并给出各表计算结果。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    du = as_number(parameters.get("dU"))
    if du is None:
        du = 0.01
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    fit_notes: dict[str, list[str]] = {}

    # ── 峰值波长表：按颜色分组计算并回填只读列 ──
    wl_rows = tables.get("table2", []) or []
    wavelength_result = None
    if any(_has_value(r.get(c)) for r in wl_rows for c in ("c0", "c1")):
        try:
            wavelength_result = _calc_wavelength(wl_rows, du)
            calc_results["table2"] = wavelength_result
            by_group: dict[str, dict[str, Any]] = {}
            for entry in wavelength_result["entries"]:
                by_group[entry["label"]] = entry
            for row in wl_rows:
                label = str(row.get("c0") or "").strip()
                entry = by_group.get(label)
                if entry is None:
                    continue
                row["c2"] = formatted(entry["lam"], 2)
                row["c3"] = formatted(entry["u_lam"], 2)
                row["c4"] = "{} ± {} nm (k=1)".format(formatted(entry["lam"], 2),
                                                      formatted(entry["u_lam"], 2))
        except ValueError as exc:
            calc_messages.append(str(exc))

    # ── 伏安特性表 ──
    iv_rows = tables.get("table1", []) or []
    if any(_has_value(r.get(c)) for r in iv_rows for c in ("c0", "c1", "c2", "c3")):
        calc_results["table1"] = _calc_iv(iv_rows)

    # ── 发光强度表 ──
    li_rows = tables.get("table3", []) or []
    if any(_has_value(r.get(c)) for r in li_rows for c in ("c0", "c1")):
        try:
            calc_results["table3"] = _calc_li(li_rows)
        except ValueError as exc:
            calc_messages.append(str(exc))

    # ── 混色三表：扣除背景并计算光强比 ──
    mix2_rows = tables.get("table4", []) or []
    if any(_has_value(r.get(c)) for r in mix2_rows for c in ("c0", "c1", "c2", "c3", "c4")):
        try:
            calc_results["table4"] = _calc_mix2(mix2_rows)
            for row in mix2_rows:
                l1 = as_number(row.get("c1"))
                l2 = as_number(row.get("c2"))
                l0 = as_number(row.get("c4"))
                l1p = l1 - l0 if (l1 is not None and l0 is not None) else None
                l2p = l2 - l0 if (l2 is not None and l0 is not None) else None
                row["c5"] = formatted(l1p, 2)
                row["c6"] = formatted(l2p, 2)
                row["c7"] = _ratio_text([l1p, l2p])
        except ValueError as exc:
            calc_messages.append(str(exc))

    mix3_rows = tables.get("table5", []) or []
    if any(_has_value(r.get(c)) for r in mix3_rows for c in ("c0", "c1", "c2", "c3", "c4")):
        try:
            calc_results["table5"] = _calc_mix3(mix3_rows)
            for row in mix3_rows:
                vals = [as_number(row.get(c)) for c in ("c0", "c1", "c2")]
                l0 = as_number(row.get("c4"))
                diffs = [v - l0 if (v is not None and l0 is not None) else None for v in vals]
                row["c5"], row["c6"], row["c7"] = (formatted(v, 2) for v in diffs)
                row["c8"] = _ratio_text(diffs)
        except ValueError as exc:
            calc_messages.append(str(exc))

    pigment_rows = tables.get("table6", []) or []
    if any(_has_value(r.get(c)) for r in pigment_rows for c in ("c0", "c1", "c2", "c3", "c4", "c5")):
        try:
            calc_results["table6"] = _calc_mix3(pigment_rows, pigment=True)
            for row in pigment_rows:
                vals = [as_number(row.get(c)) for c in ("c1", "c2", "c3")]
                l0 = as_number(row.get("c5"))
                diffs = [v - l0 if (v is not None and l0 is not None) else None for v in vals]
                row["c6"], row["c7"], row["c8"] = (formatted(v, 2) for v in diffs)
                row["c9"] = _ratio_text(diffs)
        except ValueError as exc:
            calc_messages.append(str(exc))

    fit_notes = {
        "table1": [
            "LED 正向特性：$I = I_0(e^{bU} - 1)$；对 I>0 的点做 $\\ln I$ 对 U 的线性拟合。",
            "从曲线膝点读出各基色阈值电压 U_th，填入表 2 计算峰值波长。",
        ],
        "table2": [
            "$\\lambda = 1240/E_g$（E_g 取阈值电压 U_th 的 eV 数值）；可见光区 380~780 nm。",
            "B 类 $u_B = \\Delta U/\\sqrt{3}$；同一 LED 多次读数时叠加 A 类 $u_A = t\\,\\sigma/\\sqrt{n}$，合成 $u = \\sqrt{u_A^2 + u_B^2}$。",
        ],
        "table3": [
            "低中电流区 L 与 I 近似线性：$L = kI + b$，相关系数 $|r|$ 应接近 1。",
        ],
        "table4": [
            "扣除背景光强：$L' = L - L_0$；两基色光强比即 $L_1' : L_2'$。",
            "相加混色可加性：$L_{混}' \\approx L_1' + L_2'$。",
        ],
        "table5": [
            "扣除背景光强：$L' = L - L_0$；三基色光强比即 $L_R' : L_G' : L_B'$。",
            "相加混色可加性：$L_{白}' \\approx L_R' + L_G' + L_B'$。",
        ],
        "table6": [
            "扣除背景光强：$L' = L - L_0$；三基色光强比即 $L_R' : L_G' : L_B'$。",
            "相加混色可加性：$L_{混}' \\approx L_R' + L_G' + L_B'$。",
        ],
    }

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


def _make_iv_chart(workpath: str, series: list[dict[str, Any]],
                   u_th_marks: list[tuple[str, float]]) -> dict[str, Any]:
    """三基色 LED 的 I-U 特性曲线（数据点 + 指数拟合 + 阈值电压标记）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    figure, axis = plt.subplots(figsize=(7.8, 5.2))
    note_lines = []
    for item in series:
        if not item["u"]:
            continue
        axis.plot(item["u"], item["i"], "o", color=item["color"], markersize=4,
                  label=item["label"], zorder=5)
        if item["i0"] is not None and item["b"] is not None and item["b"] > 0:
            xs = np.linspace(min(item["u"]), max(item["u"]), 120)
            axis.plot(xs, item["i0"] * (np.exp(item["b"] * xs) - 1), "--",
                      color=item["color"], linewidth=1.3, alpha=0.75,
                      label=item["label"] + "拟合", zorder=4)
            note_lines.append("{}：$I_0$≈{:.2e} mA，b≈{:.2f} 1/V，r²={:.5f}".format(
                item["label"], item["i0"], item["b"], item["r2"]))
    for color, u_th in u_th_marks:
        axis.axvline(u_th, color=color, linestyle=":", linewidth=1.2, alpha=0.6, zorder=3)
        axis.plot([u_th], [0], "v", color=color, markersize=9, zorder=6)
    if note_lines:
        axis.annotate("\n".join(note_lines), xy=(0.03, 0.97), xycoords="axes fraction",
                      va="top", fontsize=9, fontproperties=font,
                      bbox=dict(boxstyle="round,pad=0.4", fc="#f4f7fb", ec="#c6d2e2", alpha=0.92))
    axis.set_xlabel("正向电压 U (V)", fontproperties=font)
    axis.set_ylabel("工作电流 I (mA)", fontproperties=font)
    axis.set_title("LED 正向 I-U 特性曲线", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font, fontsize=9)
    else:
        axis.legend(fontsize=9)
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_iv.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_iv.png", "title": "LED 正向 I-U 特性曲线",
            "x_label": "正向电压 U (V)", "y_label": "工作电流 I (mA)"}


def _make_wavelength_chart(workpath: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """峰值波长光谱图：各 LED 波长在可见光波段内的位置与 CIE 基色对照。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    figure, axis = plt.subplots(figsize=(7.8, 4.6))
    axis.axvspan(_VISIBLE[0], _VISIBLE[1], color="#f2e9c8", alpha=0.55, zorder=0)
    for key, cie_lam in _CIE_LAM.items():
        axis.axvline(cie_lam, color="#8a8f98", linestyle="--", linewidth=1.0,
                     alpha=0.7, zorder=1)
        axis.text(cie_lam, 0.985, "CIE {} {:.1f}".format(key, cie_lam),
                  ha="center", va="bottom", fontsize=8, color="#6b7078", fontproperties=font)
    positions = range(len(entries))
    for pos, entry in zip(positions, entries):
        axis.errorbar(entry["lam"], pos, xerr=entry["u_lam"], fmt="o",
                      color=entry["color"], markersize=9, capsize=4, zorder=5)
        axis.annotate("{} λ = {:.1f} ± {:.1f} nm".format(entry["label"], entry["lam"], entry["u_lam"]),
                      (entry["lam"], pos), textcoords="offset points", xytext=(8, 8),
                      fontsize=9, fontproperties=font, color="#333a45")
    axis.set_yticks(list(positions))
    axis.set_yticklabels([entry["label"] for entry in entries], fontproperties=font, fontsize=10)
    axis.set_ylim(-0.55, len(entries) - 0.35)
    axis.set_xlim(360, 800)
    axis.set_xlabel("波长 λ (nm)", fontproperties=font)
    axis.set_title("LED 发光峰值波长（可见光区 380~780 nm，虚线为 CIE 标准基色波长）",
                   fontproperties=font, fontsize=11.5)
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_wavelength.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_wavelength.png", "title": "LED 发光峰值波长",
            "x_label": "波长 λ (nm)", "y_label": "LED"}


def _make_li_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """绿色 LED 发光强度特性 L-I 曲线（散点 + 线性拟合）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    x_values, y_values, fit = info["x"], info["y"], info["fit"]
    figure, axis = plt.subplots(figsize=(7.8, 5.2))
    axis.scatter(x_values, y_values, s=38, color="#27AE60", zorder=4, label="测量数据")
    xs = np.linspace(min(x_values), max(x_values), 150)
    axis.plot(xs, fit["slope"] * xs + fit["intercept"], "-", color="#E74C3C",
              linewidth=1.6, zorder=3, label="线性拟合")
    axis.annotate("L = {:.3f} + ({:.4f})I\nR² = {:.5f}，r = {:.5f}".format(
        fit["intercept"], fit["slope"], fit["r2"], fit["correlation"]),
        xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=10,
        fontproperties=font,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e6", ec="#e6c88a", alpha=0.9))
    axis.set_xlabel("工作电流 I (mA)", fontproperties=font)
    axis.set_ylabel("相对光强 L (mV)", fontproperties=font)
    axis.set_title("绿色 LED 发光强度特性 L-I 曲线", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "chart_li.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "chart_li.png", "title": "发光强度特性 L-I 曲线",
            "x_label": "工作电流 I (mA)", "y_label": "相对光强 L (mV)"}


def _make_mixing_chart(workpath: str, info: dict[str, Any], filename: str,
                       title: str) -> dict[str, Any]:
    """混色可加性柱状图：各基色 L'、基色之和与混色实测 L' 对比。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    rows = info["rows"]
    figure, axis = plt.subplots(figsize=(7.8, 5.2))
    group_count = len(rows)
    width = 0.8 / 6.0
    x = np.arange(group_count)
    values: list[float] = []
    for row in rows:
        for _label, _color, value in row["comps"]:
            if value is not None:
                values.append(value)
        if row["sum"] is not None:
            values.append(row["sum"])
        if row["measured"] is not None:
            values.append(row["measured"])
    max_value = max(values, default=1.0) or 1.0
    for group_index, row in enumerate(rows):
        bars = [(label, color, value) for label, color, value in row["comps"]] + [
            ("和", "#8a8f98", row["sum"]), ("混色", "#e6a23c", row["measured"])]
        for slot_index, (_label, color, value) in enumerate(bars):
            if value is None:
                continue
            offset = (slot_index - (len(bars) - 1) / 2) * width
            axis.bar(x[group_index] + offset, value, width * 0.86, color=color,
                     alpha=0.88, zorder=3)
            axis.annotate("{:.1f}".format(value),
                          (x[group_index] + offset, value + max_value * 0.02),
                          ha="center", fontsize=8, fontproperties=font)
    axis.set_xticks(x)
    axis.set_xticklabels([row["name"] for row in rows], fontproperties=font, fontsize=10)
    axis.set_ylabel("扣除背景后的相对光强 L' (mV)", fontproperties=font)
    axis.set_title(title, fontproperties=font)
    axis.grid(alpha=0.25, axis="y", zorder=0)
    legend_handles = [plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.88)
                      for _label, color, _value in rows[0]["comps"]]
    legend_labels = [label for label, _color, _value in rows[0]["comps"]]
    legend_handles.append(plt.Rectangle((0, 0), 1, 1, fc="#8a8f98", alpha=0.88))
    legend_labels.append("基色之和")
    legend_handles.append(plt.Rectangle((0, 0), 1, 1, fc="#e6a23c", alpha=0.88))
    legend_labels.append("混色实测")
    if font is not None:
        axis.legend(legend_handles, legend_labels, prop=font, fontsize=9,
                    ncol=len(legend_labels))
    else:
        axis.legend(legend_handles, legend_labels, fontsize=9,
                    ncol=len(legend_labels))
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, filename), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": filename, "title": title,
            "x_label": "混色", "y_label": "扣除背景后的相对光强 L' (mV)"}


def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """新版结构化接口：计算各表数据，输出摘要、图表与 Word 报告。"""
    parameters = payload.get("parameters") or {}
    du_value = parameters.get("dU")
    if _has_value(du_value) and as_number(du_value) is None:
        return {"code": 1, "message": "数字万用表电压档分辨率 ΔU 必须是数字"}
    du = as_number(du_value)
    if du is None:
        du = 0.01
    if du <= 0 or du >= 1:
        return {"code": 1, "message": "数字万用表电压档分辨率 ΔU 应在 0~1 V 之间"}

    result = preview(payload)
    iv_info = result["calc_results"].get("table1")
    if iv_info is None:
        return {"code": 1,
                "message": "；".join(result["calc_messages"]) or "请先填写 LED 正向伏安特性测量表（基础实验）。"}

    os.makedirs(workpath, exist_ok=True)
    tables = result["tables"]
    warnings: list[str] = []

    # ── 峰值波长 ──
    wl_info = result["calc_results"].get("table2")
    if wl_info is None:
        warnings.append("峰值波长计算表为空，请填写三色阈值电压 U_th。")

    # ── 图表 ──
    charts: list[dict[str, Any]] = []
    charts.append(_make_iv_chart(
        workpath, iv_info["series"], _threshold_marks(tables.get("table2") or [])))
    if wl_info is not None:
        charts.append(_make_wavelength_chart(workpath, wl_info["entries"]))
    li_info = result["calc_results"].get("table3")
    if li_info is not None:
        charts.append(_make_li_chart(workpath, li_info))
    mix2_info = result["calc_results"].get("table4")
    if mix2_info is not None:
        charts.append(_make_mixing_chart(workpath, mix2_info, "chart_mix2.png",
                                         "两色相加混色：基色光强与混色实测对比"))
    mix3_info = result["calc_results"].get("table5")
    if mix3_info is not None:
        charts.append(_make_mixing_chart(workpath, mix3_info, "chart_mix3.png",
                                         "三色相加混色配白：基色光强与混色实测对比"))
    pigment_info = result["calc_results"].get("table6")
    if pigment_info is not None:
        charts.append(_make_mixing_chart(workpath, pigment_info, "chart_pigment.png",
                                         "颜料色彩配出：基色光强与混色实测对比"))

    summary: list[str] = []
    for table_id, label in (("table1", "LED 正向伏安特性"),
                            ("table2", "LED 发光峰值波长"),
                            ("table3", "绿色 LED 发光强度特性"),
                            ("table4", "两色相加混色"),
                            ("table5", "三色相加混色配白"),
                            ("table6", "颜料色彩配出")):
        if table_id in result["calc_results"]:
            summary.append("【{}】".format(label))
            summary.extend(result["calc_results"][table_id]["lines"])
    for message in result["calc_messages"]:
        warnings.append(message)

    enriched = dict(payload)
    enriched["tables"] = tables
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        warnings=warnings,
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
    iv = _set_units(
        make_table(
            "table1", "LED正向伏安特性测量数据表（基础）",
            ["U", "I红", "I绿", "I蓝"],
            sample=[
                [1.8, 0.017, 0.0002, ""],
                [1.9, 0.055, 0.0008, ""],
                [2.0, 0.182, 0.0027, ""],
                [2.1, 0.605, 0.009, ""],
                [2.2, 2.01, 0.03, ""],
                [2.3, 6.67, 0.1, 0.0008],
                [2.4, 22.1, 0.33, 0.0027],
                [2.5, 73.5, 1.1, 0.009],
                [2.6, 98.4, 3.66, 0.03],
                [2.7, "", 12.2, 0.1],
                [2.8, "", 40.3, 0.33],
                [2.9, "", 92.0, 1.1],
                [3.0, "", "", 3.66],
                [3.1, "", "", 12.2],
                [3.2, "", "", 40.3],
                [3.3, "", "", 73.5],
                [3.4, "", "", 98.7],
            ],
            min_rows=3, initial_rows=17,
            description=(
                "按图接线，在 I ≤ 100 mA 内分别接红、绿、蓝 LED 测量工作电流 I 与工作电压 U。"
                "三基色可各自在不同电压范围内测量，超出量程的单元格留空即可。"
            ),
            chart={"x_column": "c0", "y_columns": ["c1", "c2", "c3"],
                   "series_labels": ["红色LED", "绿色LED", "蓝色LED"],
                   "series_colors": ["#E74C3C", "#27AE60", "#2980B9"],
                   "x_label": "正向电压 U (V)", "y_label": "工作电流 I (mA)",
                   "title": "LED正向 I-U 特性曲线（红/绿/蓝三基色）",
                   "fit": None, "connect_points": True},
        ),
        ("V", "mA", "mA", "mA"),
    )
    iv["calc"] = {"label": "拟合三基色伏安特性"}

    wl = _set_units(
        make_table(
            "table2", "LED发光峰值波长计算数据表（基础）",
            ["LED颜色", "阈值电压U_th", "峰值波长λ", "标准不确定度u(λ)", "测量结果"],
            sample=[
                ["红", 1.95],
                ["绿", 2.30],
                ["绿", 2.29],
                ["绿", 2.31],
                ["蓝", 2.70],
            ],
            text_columns=(0,),
            readonly=(2, 3, 4),
            min_rows=3, initial_rows=5,
            description=(
                "从 I-U 特性曲线读出各基色阈值电压（曲线膝点），由 λ = 1240/U_th 计算峰值波长"
                "（U_th 以 V 为单位，数值上等于禁带能量 E_g 的 eV 值）。"
                "同一 LED 可多次读数（点“添加行”），自动按颜色分组，"
                "由重复读数的 A 类不确定度与仪器分辨率的 B 类不确定度合成标准不确定度。"
            ),
        ),
        ("", "V", "nm", "nm", ""),
    )
    wl["calc"] = {"label": "计算峰值波长与不确定度"}

    li = _set_units(
        make_table(
            "table3", "绿色LED发光强度特性测量数据表（提升）",
            ["I", "L"],
            sample=[
                [0, 0], [10, 11.5], [20, 22.8], [30, 33.9], [40, 44.8],
                [50, 55.4], [60, 65.7], [70, 75.6], [80, 85.1], [90, 94.2],
                [100, 102.8],
            ],
            min_rows=3, initial_rows=11, required=False,
            description=(
                "调节分压盒，在 I ≤ 100 mA 内测量绿色 LED 的相对光强 L（光电池输出电压）与工作电流 I；"
                "LED 到光电池距离约 20 cm，测量时务必关闭照明光源。"
            ),
            chart={"x_column": "c0", "y_column": "c1",
                   "x_label": "工作电流 I (mA)", "y_label": "相对光强 L (mV)",
                   "title": "绿色LED发光强度特性 L-I 曲线", "fit": "linear"},
        ),
        ("mA", "mV"),
    )
    li["calc"] = {"label": "拟合 L-I 特性"}
    li["enabled_by_default"] = True

    mix2 = _set_units(
        make_table(
            "table4", "两色相加混色相对光强测量数据表（进阶）",
            ["混色", "L_LED1", "L_LED2", "L_混", "背景光强L0", "L1'", "L2'", "光强比L1':L2'"],
            sample=[
                ["黄色（红+绿）", 58.2, 46.5, 101.7, 3.0],
                ["青色（绿+蓝）", 44.1, 30.6, 71.7, 3.0],
                ["紫色（蓝+红）", 32.4, 22.8, 52.2, 3.0],
            ],
            text_columns=(0,),
            readonly=(5, 6, 7),
            min_rows=1, initial_rows=3, required=False,
            description=(
                "用两个 LED 相加混出色卡的黄色（红+绿）、青色（绿+蓝）、紫色（蓝+红），"
                "光电池置于白屏处，分别测量两个 LED 及配色后的相对光强；"
                "背景光强 L0 为全部 LED 熄灭时的读数，L' 为扣除背景后的值。"
            ),
        ),
        ("", "mV", "mV", "mV", "mV", "mV", "mV", ""),
    )
    mix2["calc"] = {"label": "扣除背景并计算光强比"}
    mix2["enabled_by_default"] = True

    mix3 = _set_units(
        make_table(
            "table5", "三色相加混色配白相对光强测量数据表（进阶）",
            ["L_R", "L_G", "L_B", "L_白", "背景光强L0", "L_R'", "L_G'", "L_B'", "光强比L_R':L_G':L_B'"],
            sample=[
                [58.2, 46.5, 32.4, 131.1, 3.0],
            ],
            readonly=(5, 6, 7, 8),
            min_rows=1, initial_rows=1, required=False,
            description=(
                "用三个 LED 相加混出色卡的白色，光电池置于白屏处，测量三个基色 LED 及配白后的"
                "相对光强，给出扣除背景光强后的三基色光强比。"
            ),
        ),
        ("mV", "mV", "mV", "mV", "mV", "mV", "mV", "mV", ""),
    )
    mix3["calc"] = {"label": "扣除背景并计算光强比"}
    mix3["enabled_by_default"] = False

    pigment = _set_units(
        make_table(
            "table6", "颜料色配出相对光强测量数据表（高阶）",
            ["色彩名称", "L_R", "L_G", "L_B", "L_混", "背景光强L0",
             "L_R'", "L_G'", "L_B'", "光强比L_R':L_G':L_B'"],
            sample=[
                ["自定义色", 45.2, 38.6, 52.4, 130.2, 3.0],
            ],
            text_columns=(0,),
            readonly=(6, 7, 8, 9),
            min_rows=1, initial_rows=1, required=False,
            description=(
                "先采用颜料创造一种色彩，再用三基色 LED 光源配出该色彩，测量基色光和混色光的"
                "相对光强，给出扣除背景光强后的光强比值。"
            ),
        ),
        ("", "mV", "mV", "mV", "mV", "mV", "mV", "mV", "mV", ""),
    )
    pigment["calc"] = {"label": "扣除背景并计算光强比"}
    pigment["enabled_by_default"] = False

    theory = get_table_theory("exp16")
    return make_schema(
        "RGB 相加混色实验：测量红、绿、蓝 LED 的正向伏安特性并计算发光峰值波长及标准不确定度；"
        "测量绿色 LED 的光强特性；用两个/三个 LED 相加混出色卡的黄、青、紫、白色及颜料色，"
        "给出扣除背景光强后的基色光强比（含相加混色可加性校核）。",
        [iv, wl, li, mix2, mix3, pigment],
        parameters=[
            {"id": "dU", "label": "数字万用表电压档分辨率 ΔU", "unit": "V",
             "type": "number", "default": 0.01, "min": 0, "step": "any",
             "help": "阈值电压的 B 类不确定度 u_B = ΔU/√3（按万用表所在电压档取）"},
        ],
        parameters_sample={"dU": 0.01},
        analysis_hints=(
            "LED 的 I-U 特性非线性，超过阈值电压后近似按指数规律增长；"
            "峰值波长 λ = 1240/U_th 应落在可见光波段（380~780 nm，即 E_g 在 1.63~3.26 eV）；"
            "红约 620~750 nm、绿约 500~565 nm、蓝约 450~495 nm；"
            "低中电流区 L 与 I 近似成线性关系；"
            "扣除背景光强后的混色光强应近似等于各基色光强之和（相加混色的可加性）。"
        ),
        preview_enabled=True,
        report_enabled=False,
        formulas=theory.get("_global", {}).get("formulas", []),
        variables=theory.get("_global", {}).get("variables", []),
        table_theory=theory,
    )


# ──────────────────────────────────────────────
# 旧版 CSV 流程
# ──────────────────────────────────────────────

def handle(workpath: str, extension: str) -> int:
    """旧版 CSV 流程（U 与红/绿/蓝三路电流，缺失的 LED 列自动跳过）：指数拟合 + 图表 + Word 文档。"""
    import chardet
    import pandas as pd
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Inches

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

        def find_opt(keywords):
            """先精确匹配（去空格、小写），再包含匹配；找不到返回 None。"""
            for keyword in keywords:
                if keyword in normalized:
                    return cols[normalized.index(keyword)]
            for col, norm in zip(cols, normalized):
                if any(keyword in norm for keyword in keywords):
                    return col
            return None

        u_col = find_opt(("u/v", "u", "电压")) or cols[0]
        led_cols = {
            "红色LED": find_opt(("i红", "红")),
            "绿色LED": find_opt(("i绿", "绿")),
            "蓝色LED": find_opt(("i蓝", "蓝")),
        }
        series = []
        docu_lines = []
        for label, color in (("红色LED", "#E74C3C"),
                             ("绿色LED", "#27AE60"),
                             ("蓝色LED", "#2980B9")):
            col = led_cols[label]
            if col is None or col == u_col:
                continue
            u_values = pd.to_numeric(data[u_col], errors='coerce')
            i_values = pd.to_numeric(data[col], errors='coerce')
            valid = u_values.notna() & i_values.notna()
            u_vals = u_values[valid].tolist()
            i_vals = i_values[valid].tolist()
            if not u_vals:
                continue
            fit = _fit_diode(u_vals, i_vals)
            if fit is not None:
                i0, b_value, r2 = fit
                docu_lines.append("{}：I = I₀·(e^{{bU}} − 1)，I₀ ≈ {:.3e} mA，b ≈ {:.2f} 1/V，r² = {:.5f}".format(
                    label, i0, b_value, r2))
            series.append({"label": label, "color": color, "header": str(col),
                           "u": u_vals, "i": i_vals,
                           "i0": fit[0] if fit else None,
                           "b": fit[1] if fit else None,
                           "r2": fit[2] if fit else None})
        if not series:
            raise ValueError("没有可用的数据行（需要 U 与至少一路 LED 电流）")

        docu = Document()
        style_doc_font(docu)
        docu.add_heading(name(), level=0)
        docu.add_paragraph("LED 正向伏安特性（旧版 CSV 流程）")
        docu.add_paragraph()

        rows = max(len(s["u"]) for s in series)
        table = docu.add_table(rows=rows + 1, cols=len(series) + 1, style='Table Grid')
        table.rows[0].cells[0].text = str(u_col)
        for j, s in enumerate(series):
            table.rows[0].cells[j + 1].text = s["header"]
        for i in range(rows):
            table.rows[i + 1].cells[0].text = formatted(series[0]["u"][i], 3) if i < len(series[0]["u"]) else ""
            for j, s in enumerate(series):
                table.rows[i + 1].cells[j + 1].text = formatted(s["i"][i], 3) if i < len(s["i"]) else ""

        fn = _make_iv_chart(workpath, series, [])["filename"]
        docu.add_picture(os.path.join(workpath, fn), width=Inches(6))
        for line in docu_lines:
            docu.add_paragraph(line)
        docu.add_paragraph()
        docu.add_paragraph("公式：")
        docu.add_paragraph("LED 正向伏安特性：I = I₀·(e^{bU} - 1)，对 I>0 的点做 ln I 对 U 的线性拟合")
        docu.add_paragraph("峰值波长：λ = 1240/E_g（E_g 单位 eV，数值上取阈值电压 U_th/V，λ 单位 nm）")

        docu.save(workpath + name() + ".docx")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
