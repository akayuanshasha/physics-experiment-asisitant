"""
密度的测量实验插件
==============================
本实验包含三部分，共四组数据表 + 一个图表：

第一部分：金属圆柱体密度的测量
  表格1：卡尺几何法测密度表（不绘图）
    → 多次测量 D、H，计算 D̄、H̄、V、ρ₁
  表格2：流体静力称衡法测密度表（不绘图）
    → 计算 Δm、ρ₂

第二部分：利用转动定律测量物体质量
  表格3：双小铜块变位置周期测量与参数计算表（5行，不绘图）
    → 计算 T、X=r²、Y=grT²/(4π²)
  图表1：Y - X 线性拟合图 → 由截距 b 计算 Ic，再由棒数据求 m₁

第三部分：模拟太空失重动力学法测质量
  表格4：弹簧振子周期法测质量表（不绘图）
    → 计算 m = m₀·T²/T₀²

物理公式：
  V = (π/4)·D̄²·H̄                    （圆柱体积）
  ρ₁ = m/V                           （几何法密度）
  ₂ = m/(m-m₁)·ρ₀                  （称衡法密度）
  Y = g·r·T²/(4π²)                   （转动定律参量）
  Ic = 2m·b                          （木条转动惯量，b为截距）
  m = m₀·T²/T₀²                      （失重动力学法质量）
"""

import numpy as np
from . import ExperimentPlugin


class DensityMeasurement(ExperimentPlugin):
    name = "密度的测量B（实验指导）"
    _mod_name = "exp4a"
    category = "一级-力学"
    description = "密度的测量（4数据表 + 1拟合图）"
    required_fields = ["直径D(cm)", "高度H(cm)", "质量m(g)"]
    custom_template = "density_measurement.html"

    # ── 四组数据表配置 ──
    table_configs = [
        {
            "id": "table1",
            "title": "卡尺几何法测密度表（不绘图）",
            "columns": [
                "D₁(cm)", "D₂(cm)", "D(cm)",
                "H₁(cm)", "H₂(cm)", "H₃(cm)",
                "质量 m(g)",
                "平均直径 D̄(cm)", "平均高度 H̄(cm)",
                "体积 V(cm³)", "几何密度 ρ₁(g/cm³)"
            ],
            "row_count": 1,
        },
        {
            "id": "table2",
            "title": "流体静力称衡法测密度表（不绘图）",
            "columns": [
                "水温 t(℃)", "纯水密度 ρ₀(g/cm³)",
                "空气中质量 m(g)", "水中读数 m₁(g)",
                "浮力差 Δm(g)", "称衡密度 ρ₂(g/cm³)"
            ],
            "row_count": 1,
        },
        {
            "id": "table3",
            "title": "双小铜块变位置周期测量与参数计算表（不绘图）",
            "columns": [
                "序号", "质心距 r(m)", "30周期时间 t₃₀(s)",
                "周期 T(s)", "X=r²(m²)", "Y=grT²/(4π²)(m²)"
            ],
            "row_count": 5,
        },
        {
            "id": "table4",
            "title": "弹簧振子周期法测质量表（不绘图）",
            "columns": [
                "标准质量 m₀(g)", "标准周期 T₀(s)",
                "待测周期 T(s)", "待测质量 m(g)"
            ],
            "row_count": 1,
        },
    ]

    def preview(self, payload):
        """在后端补全密度与动力学计算列。"""
        from copy import deepcopy

        tables = deepcopy(payload.get("tables") or {})

        def number(value):
            try:
                return float(value) if str(value).strip() else None
            except (TypeError, ValueError):
                return None

        for row in tables.get("table1", []):
            diameters = [number(row.get(f"c{i}")) for i in range(3)]
            heights = [number(row.get(f"c{i}")) for i in range(3, 6)]
            diameters = [value for value in diameters if value is not None]
            heights = [value for value in heights if value is not None]
            mass = number(row.get("c6"))
            diameter = sum(diameters) / len(diameters) if diameters else None
            height = sum(heights) / len(heights) if heights else None
            volume = np.pi * diameter * diameter * height / 4 if diameter is not None and height is not None else None
            row["c7"] = f"{diameter:.4f}" if diameter is not None else ""
            row["c8"] = f"{height:.4f}" if height is not None else ""
            row["c9"] = f"{volume:.4f}" if volume is not None else ""
            row["c10"] = f"{mass / volume:.4f}" if mass is not None and volume else ""
        for row in tables.get("table2", []):
            rho0, mass, water_mass = (number(row.get(key)) for key in ("c1", "c2", "c3"))
            delta = mass - water_mass if mass is not None and water_mass is not None else None
            row["c4"] = f"{delta:.4f}" if delta is not None else ""
            row["c5"] = f"{mass / delta * rho0:.4f}" if mass is not None and rho0 is not None and delta else ""
        for index, row in enumerate(tables.get("table3", [])):
            radius, elapsed = number(row.get("c1")), number(row.get("c2"))
            period = elapsed / 30 if elapsed is not None else None
            row["c0"] = index + 1
            row["c3"] = f"{period:.6f}" if period is not None else ""
            row["c4"] = f"{radius * radius:.8f}" if radius is not None else ""
            value = 9.8 * radius * period * period / (4 * np.pi * np.pi) if radius is not None and period is not None else None
            row["c5"] = f"{value:.8f}" if value is not None else ""
        for row in tables.get("table4", []):
            mass, base_period, period = (number(row.get(key)) for key in ("c0", "c1", "c2"))
            value = mass * period * period / (base_period * base_period) if mass is not None and base_period and period is not None else None
            row["c3"] = f"{value:.4f}" if value is not None else ""
        return {"tables": tables}

    def calculate(self, data, constants=None):
        """根据四表格数据计算密度和质量

        data 格式:
        {
            "table1": [[D1,D2,D3,H1,H2,H3,m,D̄,H̄,V,ρ₁]],
            "table2": [[t,ρ₀,m,m1,Δm,ρ₂]],
            "table3": [[no,r,t30,T,X,Y], ...],
            "table4": [[m0,T0,T,m]],
        }
        """
        if constants is None:
            constants = {}

        results = {"steps": {}, "final": {}}
        g = 9.80  # m/s²

        # ═══════════════════════════════════════
        # 第一部分：几何法密度
        # ════════════════════════════════════════
        t1 = data.get("table1", [])
        for row in t1:
            if not row or len(row) < 11:
                continue
            try:
                rho1 = float(row[10]) if row[10].strip() else None
                if rho1 is not None:
                    results["final"]["几何法密度 ρ₁"] = f"{rho1:.4f} g/cm³"
            except (ValueError, IndexError):
                pass

        # ════════════════════════════════════════
        # 第一部分：称衡法密度
        # ════════════════════════════════════════
        t2 = data.get("table2", [])
        for row in t2:
            if not row or len(row) < 6:
                continue
            try:
                rho2 = float(row[5]) if row[5].strip() else None
                if rho2 is not None:
                    results["final"]["称衡法密度 ρ₂"] = f"{rho2:.4f} g/cm³"
            except (ValueError, IndexError):
                pass

        # ════════════════════════════════════════
        # 第二部分：转动定律（由前端拟合得到）
        # ═══════════════════════════════════════
        t3 = data.get("table3", [])
        x_vals = []
        y_vals = []
        for row in t3:
            if not row or len(row) < 6:
                continue
            try:
                x_val = float(row[4]) if row[4].strip() else None
                y_val = float(row[5]) if row[5].strip() else None
                if x_val is not None and y_val is not None:
                    x_vals.append(x_val)
                    y_vals.append(y_val)
            except (ValueError, IndexError):
                continue

        if len(x_vals) >= 2:
            x_arr = np.array(x_vals)
            y_arr = np.array(y_vals)
            n = len(x_arr)
            x_mean = np.mean(x_arr)
            y_mean = np.mean(y_arr)
            k_num = np.sum((x_arr - x_mean) * (y_arr - y_mean))
            k_den = np.sum((x_arr - x_mean) ** 2)
            if k_den != 0:
                slope = k_num / k_den
                intercept = y_mean - slope * x_mean
                results["steps"]["Y-X 拟合斜率 k"] = f"{slope:.6f}"
                results["steps"]["Y-X 拟合截距 b"] = f"{intercept:.6f} m²"

                # Ic = 2m·b (需要用户输入小铜块总质量 2m)
                two_m = float(constants.get("two_m", 0))  # g
                if two_m > 0:
                    Ic = 2 * (two_m / 1000.0) * intercept  # kg·m²
                    results["steps"]["木条转动惯量 Ic"] = f"{Ic:.6e} kg·m²"

        # ════════════════════════════════════════
        # 第三部分：失重动力学法质量
        # ═══════════════════════════════════════
        t4 = data.get("table4", [])
        for row in t4:
            if not row or len(row) < 4:
                continue
            try:
                m_val = float(row[3]) if row[3].strip() else None
                if m_val is not None:
                    results["final"]["失重动力学法质量 m"] = f"{m_val:.4f} g"
            except (ValueError, IndexError):
                pass

        return results

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过三种方法测量物体密度和质量：卡尺几何法、流体静力称衡法、"
                       "转动定律法和失重动力学法。"
        }
