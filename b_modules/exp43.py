"""exp43：刚体转动惯量（三线摆法）的三项必做实验。"""
from __future__ import annotations

import math
from statistics import mean

from head import *  # noqa: F401,F403
from structured_support import as_number, copied_tables, formatted, make_chart_from_table, make_schema, make_table, structured_result
from theory_content import get_table_theory


def name():
    return "刚体转动惯量"


def _units(table, units):
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def _n(row, key):
    return as_number(row.get(key))


def _avg(values):
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def _period(value):
    return value / 50.0 if value is not None and value > 0 else None


def _inertia(mass, gravity, R, r, period, H):
    if None in (mass, gravity, R, r, period, H) or H <= 0:
        return None
    return mass * gravity * R * r * period ** 2 / (4 * math.pi ** 2 * H)


def _linear_fit(points):
    if len(points) < 2:
        return None
    xs, ys = zip(*points)
    x_bar, y_bar = mean(xs), mean(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope = sum((x - x_bar) * (y - y_bar) for x, y in points) / denominator
    intercept = y_bar - slope * x_bar
    total = sum((y - y_bar) ** 2 for y in ys)
    residual = sum((y - slope * x - intercept) ** 2 for x, y in points)
    return slope, intercept, 1 - residual / total if total else 1.0


def _compute(payload):
    tables = copied_tables(payload)
    params = payload.get("parameters") or {}
    m0, m1 = as_number(params.get("m0")), as_number(params.get("m1"))
    m_pair = as_number(params.get("m_pair"))
    gravity = as_number(params.get("g")) or 980.0  # cm/s²
    notes = {}

    # a、b 是三条悬线构成的等边三角形边长，r=a/√3、R=b/√3。
    geometry, periods, inertias = [], [], []
    for index, row in enumerate(tables.get("table1", [])):
        row["c0"] = index + 1
        a, b = _n(row, "c1"), _n(row, "c3")
        r = a / math.sqrt(3) if a and a > 0 else None
        R = b / math.sqrt(3) if b and b > 0 else None
        H, T0 = _n(row, "c5"), _period(_n(row, "c6"))
        I0 = _inertia(m0, gravity, R, r, T0, H)
        row.update(c2=formatted(r, 4), c4=formatted(R, 4), c7=formatted(T0, 5), c8=formatted(I0, 4))
        if r is not None and R is not None and H is not None:
            geometry.append((r, R, H))
        if T0 is not None:
            periods.append(T0)
        if I0 is not None:
            inertias.append(I0)
    r_avg, R_avg, H_avg = (_avg([item[i] for item in geometry]) for i in range(3)) if geometry else (None, None, None)
    T0_avg, I0_avg = _avg(periods), _avg(inertias)
    if I0_avg is not None:
        notes["table1"] = [
            f"平均值：r̄={formatted(r_avg, 4)} cm，R̄={formatted(R_avg, 4)} cm，H̄={formatted(H_avg, 4)} cm，T̄₀={formatted(T0_avg, 5)} s。",
            f"圆盘转动惯量 I₀={formatted(I0_avg, 4)} g·cm²；r=a/√3，R=b/√3。",
        ]

    # 圆环：I环=I1-I0，理论值=m1(D内²+D外²)/8。
    ring_values = []
    for index, row in enumerate(tables.get("table2", [])):
        row["c0"] = index + 1
        T1 = _period(_n(row, "c1"))
        I_ring = None
        if None not in (m0, m1, gravity, R_avg, r_avg, H_avg, T1, T0_avg, I0_avg):
            I_ring = _inertia(m0 + m1, gravity, R_avg, r_avg, T1, H_avg) - I0_avg
        D_in, D_out = _n(row, "c3"), _n(row, "c4")
        I_theory = m1 * (D_in ** 2 + D_out ** 2) / 8 if None not in (m1, D_in, D_out) else None
        error = (I_ring - I_theory) / I_theory * 100 if I_ring is not None and I_theory else None
        row.update(c2=formatted(T1, 5), c5=formatted(I_ring, 4), c6=formatted(I_theory, 4), c7=formatted(error, 3))
        if None not in (I_ring, I_theory, error):
            ring_values.append((I_ring, I_theory, error))
    ring_result = None
    if ring_values:
        I_ring = _avg([item[0] for item in ring_values])
        I_theory = _avg([item[1] for item in ring_values])
        error = (I_ring - I_theory) / I_theory * 100 if I_theory else None
        ring_result = (I_ring, I_theory, error)
        notes["table2"] = [
            f"三次测量平均：I环={formatted(I_ring, 4)} g·cm²，"
            f"I理论={formatted(I_theory, 4)} g·cm²，相对误差={formatted(error, 3)}%。"
        ]

    # 平行轴定理：I_d 对 d² 线性拟合，斜率与两圆柱总质量比较。
    points = []
    for row in tables.get("table3", []):
        d = _n(row, "c0")
        Ts = [_period(_n(row, key)) for key in ("c1", "c2", "c3")]
        T_d, d2, I_d = _avg(Ts), d * d if d is not None else None, None
        if None not in (m0, m_pair, gravity, R_avg, r_avg, H_avg, T_d, T0_avg, I0_avg):
            I_d = _inertia(m0 + m_pair, gravity, R_avg, r_avg, T_d, H_avg) - I0_avg
        row.update(c4=formatted(T_d, 5), c5=formatted(d2, 4), c6=formatted(I_d, 4))
        if d2 is not None and I_d is not None:
            points.append((d2, I_d))
    fit = _linear_fit(points)
    if fit:
        slope, intercept, r2 = fit
        notes["table3"] = [
            f"最小二乘拟合：I_d={slope:.6f}d²+{intercept:.6f}（g·cm²），R²={r2:.6f}。",
            f"拟合质量 m拟合={slope:.4f} g；与输入的两圆柱总质量 {formatted(m_pair, 4)} g 比较。",
            "平行轴定理：I_d=I_c+m d²。",
        ]
    return tables, {"I0": I0_avg, "T0": T0_avg, "ring": ring_result, "fit": fit, "notes": notes}


def schema():
    table1 = _units(make_table(
        "table1", "测量圆盘转动惯量数据表", ["次数", "a", "r", "b", "R", "H", "50T₀", "T₀", "I盘"],
        sample=[[1, 6.70, "", 12.39, "", 38.70, 83.96, "", ""], [2, 6.71, "", 12.38, "", 38.75, 84.11, "", ""], [3, 6.70, "", 12.39, "", 38.72, 84.02, "", ""]],
        readonly=(0, 2, 4, 7, 8), min_rows=3, initial_rows=3,
        description="输入三次 a、b、H 和空盘 50T₀；r、R、T₀、I盘自动计算。"),
        ["", "cm", "cm", "cm", "cm", "cm", "s", "s", "g·cm²"])
    table2 = _units(make_table(
        "table2", "测量圆环转动惯量数据表", ["次数", "50T₁", "T₁", "D内", "D外", "I环", "I理论", "相对误差"],
        sample=[[1, 74.31, "", 6.70, 12.00, "", "", ""], [2, 74.45, "", 6.71, 11.99, "", "", ""], [3, 74.39, "", 6.70, 12.00, "", "", ""]],
        readonly=(0, 2, 5, 6, 7), min_rows=3, initial_rows=3,
        description="输入三次加圆环后的 50T₁ 及圆环内外直径；I环、I理论和相对误差自动计算，结果取三次平均。"),
        ["", "s", "s", "cm", "cm", "g·cm²", "g·cm²", "%"])
    table3 = _units(make_table(
        "table3", "验证平行轴定理数据表", ["d", "50T₁", "50T₂", "50T₃", "平均T", "d²", "I_d"],
        sample=[[0, 67.89, 68.06, 67.96, "", "", ""], [2, 69.27, 69.43, 69.39, "", "", ""], [3, 71.08, 71.25, 71.19, "", "", ""], [4, 73.41, 73.56, 73.53, "", "", ""], [5, 76.42, 76.60, 76.54, "", "", ""], [6, 79.82, 79.98, 79.92, "", "", ""], [7, 83.80, 83.95, 83.91, "", "", ""]],
        readonly=(4, 5, 6), min_rows=2, initial_rows=7,
        chart={"x_column": "c5", "y_column": "c6", "x_label": "d² (cm²)", "y_label": "I_d (g·cm²)", "title": "平行轴定理：I_d-d² 线性拟合", "fit": "linear"},
        description="改变 d，输入三次 50T；自动计算平均周期、d²、I_d 并进行线性拟合。"),
        ["cm", "s", "s", "s", "s", "cm²", "g·cm²"])
    return make_schema(
        "本实验只处理指导书中的必做内容：测量圆盘、圆环的转动惯量，并通过 I_d-d² 线性拟合验证平行轴定理。",
        [table1, table2, table3], parameters=[
            {"id": "m0", "label": "下圆盘质量 m₀", "unit": "g", "type": "number", "default": 499.68, "required": True},
            {"id": "m1", "label": "圆环质量 m₁", "unit": "g", "type": "number", "default": 350.24, "required": True},
            {"id": "m_pair", "label": "两圆柱总质量 m柱", "unit": "g", "type": "number", "default": 274.00, "required": True},
            {"id": "g", "label": "重力加速度 g", "unit": "cm/s²", "type": "number", "default": 979.8, "required": True}],
        analysis_hints="检查装置水平和 50 个周期累计时间；观察 I_d 与 d² 的线性及拟合斜率与两圆柱总质量的差异。",
        preview_enabled=True, report_enabled=False, revision=5, table_theory=get_table_theory("exp43"))


def preview(payload):
    tables, result = _compute(payload)
    return {"tables": tables, "fit_notes": result["notes"]}


def handle_structured(workpath, payload):
    tables, result = _compute(payload)
    if result["I0"] is None and not result["ring"] and not result["fit"]:
        return {"code": 1, "message": "请至少填写圆盘表中的有效数据，并检查质量、H 和 50T₀。"}
    final_payload = dict(payload)
    final_payload["tables"] = tables
    summary = []
    if result["I0"] is not None:
        summary.append(f"圆盘平均转动惯量 I₀={result['I0']:.4f} g·cm²，T₀={result['T0']:.5f} s。")
    if result["ring"]:
        ring = result["ring"]
        summary.append(f"圆环 I环={ring[0]:.4f} g·cm²，理论值={ring[1]:.4f} g·cm²，相对误差={ring[2]:.3f}%。")
    if result["fit"]:
        slope, intercept, r2 = result["fit"]
        summary.append(f"I_d-d² 拟合：I_d={slope:.6f}d²+{intercept:.6f}，R²={r2:.6f}；拟合质量={slope:.4f} g。")
    charts = []
    if result["fit"]:
        table = schema()["tables"][2]
        charts.append(make_chart_from_table(table, tables["table3"], table["chart"], workpath, "chart_exp43_parallel.png"))
    return structured_result(workpath, name(), schema(), final_payload, summary=summary, charts=charts)


def handle(workpath, extension):
    # 旧版上传入口已由结构化实验页替代，保留符号避免旧适配器导入失败。
    return 1
