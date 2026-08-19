"""
表面张力实验插件
==============================
本实验包含三部分，共三组数据表 + 两个图表：

第一部分：弹簧劲度系数定标
  表格1：弹簧伸长量与拉力计算表（10行，纯数据计算，不绘图）
    → 计算 Δx = x - x0，F = m·g
  图表1：F - Δx 线性拟合图 → 由斜率计算弹簧劲度系数 k

第二部分：自来水与洗洁精表面张力测定
  参数输入：金属圈两脚间距 d，劲度系数 k
  表格2：液膜破裂读数及表面张力计算表（2行，纯数据计算，不绘图）
    → 计算 l̄、ΔF、σ

第三部分：不同浓度洗洁精溶液表面张力测定
  表格3：不同浓度表面张力计算表（默认3行，纯数据计算，不绘图）
    → 计算 σ = k(l̄ - l0) / (2d)
  图表2：σ - C 浓度关系曲线图

物理公式：
  F = m·g                            （拉力）
  Δx = x - x0                        （伸长量）
  k = ΔF/Δx                          （劲度系数，由拟合斜率得到）
  σ = k·(l̄ - l0) / (2d)             （表面张力系数）
"""

import numpy as np
from . import ExperimentPlugin


class SurfaceTension(ExperimentPlugin):
    name = "表面张力B（实验指导）"
    _mod_name = "exp2a"
    category = "一级-力学"
    description = "表面张力（3数据表 + 2图表）"
    required_fields = ["砝码质量m(g)", "升降杆位置读数x(cm)"]
    custom_template = "surface_tension.html"

    # ── 三组数据表配置 ──
    table_configs = [
        {
            "id": "table1",
            "title": "弹簧伸长量与拉力计算表（不绘图）",
            "columns": [
                "砝码质量 m(g)", "升降杆读数 x(cm)",
                "伸长量 Δx(cm)", "拉力 F(mN)"
            ],
            "row_count": 10,
        },
        {
            "id": "table2",
            "title": "液膜破裂读数及表面张力计算表（不绘图）",
            "columns": [
                "液体类别", "初始读数 l₀(cm)",
                "破裂读数1(cm)", "破裂读数2(cm)", "破裂读数3(cm)",
                "破裂读数4(cm)", "破裂读数5(cm)",
                "破裂均值 l̄(cm)", "拉力差 ΔF(mN)", "表面张力 σ(mN/m)"
            ],
            "row_count": 2,
        },
        {
            "id": "table3",
            "title": "不同浓度洗洁精表面张力计算表（不绘图）",
            "columns": [
                "浓度 C(%)", "初始读数 l₀(cm)",
                "破裂均值 l̄(cm)", "表面张力 σ(mN/m)"
            ],
            "row_count": 3,
        },
    ]

    def preview(self, payload):
        """在后端补全弹簧定标与表面张力计算列。"""
        from copy import deepcopy

        tables = deepcopy(payload.get("tables") or {})
        parameters = payload.get("parameters") or {}

        def number(value, fallback=None):
            try:
                return float(value) if str(value).strip() else fallback
            except (TypeError, ValueError):
                return fallback

        k = number(parameters.get("k"), 0.5)
        distance = number(parameters.get("d"), 3.0)
        first_x = None
        for row in tables.get("table1", []):
            mass, x = number(row.get("c0")), number(row.get("c1"))
            if first_x is None and x is not None:
                first_x = x
            row["c2"] = f"{x - first_x:.4f}" if x is not None and first_x is not None else ""
            row["c3"] = f"{mass * 9.8:.4f}" if mass is not None else ""
        for index, row in enumerate(tables.get("table2", [])):
            initial = number(row.get("c1"))
            readings = [number(row.get(f"c{i}")) for i in range(2, 7)]
            readings = [value for value in readings if value is not None]
            mean = sum(readings) / len(readings) if readings else None
            delta_force = k * (mean - initial) * 10 if mean is not None and initial is not None else None
            tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
            row["c0"] = "自来水" if index == 0 else ("洗洁精溶液" if index == 1 else f"待测溶液{index + 1}")
            row["c7"] = f"{mean:.4f}" if mean is not None else ""
            row["c8"] = f"{delta_force:.4f}" if delta_force is not None else ""
            row["c9"] = f"{tension:.4f}" if tension is not None else ""
        for row in tables.get("table3", []):
            initial, mean = number(row.get("c1")), number(row.get("c2"))
            delta_force = k * (mean - initial) * 10 if mean is not None and initial is not None else None
            tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
            row["c3"] = f"{tension:.4f}" if tension is not None else ""
        return {"tables": tables}

    def calculate(self, data, constants=None):
        """根据三表格数据计算弹簧劲度系数和表面张力系数

        data 格式:
        {
            "table1": [[m, x, Δx, F], ...],          # 弹簧定标
            "table2": [[液体, l0, r1~r5, l̄, ΔF, σ], ...],  # 表面张力
            "table3": [[C, l0, l̄, σ], ...],          # 浓度关系
        }
        """
        if constants is None:
            constants = {}

        results = {"steps": {}, "final": {}}
        g = 9.80  # m/s²

        # ════════════════════════════════════════
        # 第一部分：弹簧劲度系数（由前端拟合得到）
        # ════════════════════════════════════════
        t1 = data.get("table1", [])
        masses = []
        forces = []
        dx_values = []
        for row in t1:
            if not row or len(row) < 4:
                continue
            try:
                m_val = float(row[0]) if row[0].strip() else None
                dx_val = float(row[2]) if row[2].strip() else None
                f_val = float(row[3]) if row[3].strip() else None
                if m_val is not None and dx_val is not None and f_val is not None:
                    masses.append(m_val)
                    dx_values.append(dx_val)
                    forces.append(f_val)
            except (ValueError, IndexError):
                continue

        if len(forces) >= 2:
            dx_arr = np.array(dx_values) / 100.0  # cm → m
            f_arr = np.array(forces) / 1000.0      # mN → N
            # 线性拟合 F = k·Δx
            n = len(dx_arr)
            dx_mean = np.mean(dx_arr)
            f_mean = np.mean(f_arr)
            k_num = np.sum((dx_arr - dx_mean) * (f_arr - f_mean))
            k_den = np.sum((dx_arr - dx_mean) ** 2)
            if k_den != 0:
                k_slope = k_num / k_den  # N/m
                results["steps"]["弹簧劲度系数 k（拟合）"] = f"{k_slope:.4f} N/m"
                results["final"]["弹簧劲度系数 k"] = f"{k_slope:.4f} N/m"
        else:
            results["final"]["弹簧劲度系数 k"] = "数据不足"

        # ════════════════════════════════════════
        # 第二部分：表面张力
        # ════════════════════════════════════════
        k_val = float(constants.get("k", results.get("final", {}).get("弹簧劲度系数 k", "0").split()[0]))
        d_val = float(constants.get("d", 0))  # cm

        t2 = data.get("table2", [])
        for row in t2:
            if not row or len(row) < 10:
                continue
            liquid = row[0].strip() if row[0].strip() else "未知"
            try:
                sigma = float(row[9]) if row[9].strip() else None
                if sigma is not None:
                    results["final"][f"{liquid} 表面张力系数 σ"] = f"{sigma:.4f} mN/m"
            except (ValueError, IndexError):
                pass

        # ════════════════════════════════════════
        # 第三部分：浓度关系
        # ════════════════════════════════════════
        t3 = data.get("table3", [])
        concentrations = []
        sigmas = []
        for row in t3:
            if not row or len(row) < 4:
                continue
            try:
                c_val = float(row[0]) if row[0].strip() else None
                sigma_val = float(row[3]) if row[3].strip() else None
                if c_val is not None and sigma_val is not None:
                    concentrations.append(c_val)
                    sigmas.append(sigma_val)
            except (ValueError, IndexError):
                continue

        if concentrations:
            results["steps"]["浓度-表面张力数据点"] = f"{len(concentrations)} 个"

        return results

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过弹簧劲度系数定标和液膜破裂法测量不同液体的表面张力系数，"
                       "并研究洗洁精浓度对表面张力的影响。"
        }
