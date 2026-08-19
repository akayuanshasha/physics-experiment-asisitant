"""
单摆法测重力加速度实验插件
==============================
本实验包含两部分，共两组数据表：

第一部分：基础内容（重复测量与不确定度计算）
  表格1：单摆重复测量表（6行，纯数据计算，不绘图）
    → 计算摆长均值 l̄、周期均值 T̄、重力加速度 g 及不确定度

第二部分：提升内容（多摆长拟合求 g）
  表格2：不同摆长与周期平方计算表（6行，纯数据计算，不绘图）
  图表1：l - T² 线性拟合图 → 由斜率 k 计算 g = 4π²k

物理公式：
  g = 4π² l̄ / T²                    （平均值法）
  g = 4π² · k                        （拟合斜率法，k = Δl/ΔT²）
"""

import numpy as np
from . import ExperimentPlugin


class Pendulum(ExperimentPlugin):
    name = "单摆法测重力加速度B（实验指导）"
    _mod_name = "exp1b"
    category = "一级-力学"
    description = "单摆法测重力加速度（2数据表 + 1拟合图）"
    required_fields = ["摆线长x(cm)", "摆球直径d(mm)"]
    custom_template = "pendulum.html"

    # ── 两组数据表配置 ──
    table_configs = [
        {
            "id": "table1",
            "title": "单摆重复测量及不确定度计算表（不绘图）",
            "columns": [
                "序号", "摆线长 x(cm)", "摆球直径 d(mm)",
                "实际摆长 l(cm)", "累积时间 t(s)", "周期 T(s)"
            ],
            "row_count": 6,
        },
        {
            "id": "table2",
            "title": "不同摆长与周期平方计算表（不绘图）",
            "columns": [
                "序号", "摆长 l(cm)", "累积时间 t(s)",
                "周期 T(s)", "周期平方 T²(s²)"
            ],
            "row_count": 6,
        },
    ]

    def preview(self, payload):
        """在后端补全序号、实际摆长、周期及周期平方。"""
        from copy import deepcopy

        tables = deepcopy(payload.get("tables") or {})

        def number(value):
            try:
                return float(value) if str(value).strip() else None
            except (TypeError, ValueError):
                return None

        for index, row in enumerate(tables.get("table1", [])):
            x, diameter, elapsed = (number(row.get(key)) for key in ("c1", "c2", "c4"))
            row["c0"] = index + 1
            row["c3"] = f"{x + diameter / 20:.4f}" if x is not None and diameter is not None else ""
            row["c5"] = f"{elapsed / 50:.5f}" if elapsed is not None else ""
        for index, row in enumerate(tables.get("table2", [])):
            elapsed = number(row.get("c2"))
            period = elapsed / 50 if elapsed is not None else None
            row["c0"] = index + 1
            row["c3"] = f"{period:.5f}" if period is not None else ""
            row["c4"] = f"{period * period:.6f}" if period is not None else ""
        return {"tables": tables}

    def calculate(self, data, constants=None):
        """根据两表格数据计算重力加速度

        data 格式:
        {
            "table1": [[no, x, d, l, t, T], ...],   # 重复测量
            "table2": [[no, l, t, T, T2], ...],      # 不同摆长
        }
        """
        if constants is None:
            constants = {}

        results = {"steps": {}, "final": {}}

        # ════════════════════════════════════════
        # 第一部分：平均值法
        # ════════════════════════════════════════
        t1 = data.get("table1", [])

        lengths = []
        periods = []
        for row in t1:
            if not row or len(row) < 6:
                continue
            try:
                l_val = float(row[3]) if row[3].strip() else None
                T_val = float(row[5]) if row[5].strip() else None
                if l_val is not None and T_val is not None:
                    lengths.append(l_val)
                    periods.append(T_val)
            except (ValueError, IndexError):
                continue

        if len(lengths) < 2:
            results["final"]["平均值法"] = "数据不足，无法计算"
        else:
            l_arr = np.array(lengths)
            T_arr = np.array(periods)

            l_mean = np.mean(l_arr)
            T_mean = np.mean(T_arr)
            l_std = np.std(l_arr, ddof=1)
            T_std = np.std(T_arr, ddof=1)

            # g = 4π² l̄ / T̄²  (l in cm → m)
            l_mean_m = l_mean / 100.0
            g_val = 4 * np.pi**2 * l_mean_m / T_mean**2

            # 不确定度（简化）
            u_l_A = l_std / np.sqrt(len(l_arr))  # cm
            u_T_A = T_std / np.sqrt(len(T_arr))  # s
            # 仪器不确定度
            u_l_B = 0.05  # cm (钢卷尺估计误差)
            u_T_B = 0.002  # s (秒表估计误差 / N)
            u_l = np.sqrt(u_l_A**2 + u_l_B**2)  # cm
            u_T = np.sqrt(u_T_A**2 + u_T_B**2)  # s

            # 相对不确定度
            ur_l = u_l / l_mean
            ur_T = u_T / T_mean
            ur_g = np.sqrt(ur_l**2 + (2 * ur_T)**2)
            u_g = g_val * ur_g

            results["steps"]["摆长均值 l̄"] = f"{l_mean:.4f} cm"
            results["steps"]["周期均值 T̄"] = f"{T_mean:.4f} s"
            results["steps"]["摆长不确定度 u_l"] = f"{u_l:.4f} cm"
            results["steps"]["周期不确定度 u_T"] = f"{u_T:.4f} s"
            results["final"]["重力加速度 g"] = f"{g_val:.4f} m/s²"
            results["final"]["g 的标准不确定度 u_g"] = f"{u_g:.4f} m/s²"
            results["final"]["g 的相对不确定度 u_r(g)"] = f"{ur_g * 100:.2f}%"

        # ════════════════════════════════════════
        # 第二部分：拟合斜率法
        # ════════════════════════════════════════
        t2 = data.get("table2", [])

        lengths2 = []
        T2_values = []
        for row in t2:
            if not row or len(row) < 5:
                continue
            try:
                l_val = float(row[1]) if row[1].strip() else None
                T2_val = float(row[4]) if row[4].strip() else None
                if l_val is not None and T2_val is not None:
                    lengths2.append(l_val / 100.0)  # cm → m
                    T2_values.append(T2_val)
            except (ValueError, IndexError):
                continue

        if len(lengths2) < 2:
            results["final"]["拟合斜率法"] = "数据不足，无法计算"
        else:
            l2_arr = np.array(lengths2)
            T2_arr = np.array(T2_values)

            # 线性拟合 l = k·T² + b
            n = len(l2_arr)
            T2_mean = np.mean(T2_arr)
            l2_mean = np.mean(l2_arr)
            k_num = np.sum((T2_arr - T2_mean) * (l2_arr - l2_mean))
            k_den = np.sum((T2_arr - T2_mean)**2)
            k_slope = k_num / k_den  # m/s²

            y_pred = k_slope * T2_arr + (l2_mean - k_slope * T2_mean)
            ss_res = np.sum((l2_arr - y_pred)**2)
            ss_tot = np.sum((l2_arr - l2_mean)**2)
            R2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0

            g_fit = 4 * np.pi**2 * k_slope

            results["steps"]["l-T² 拟合斜率 k"] = f"{k_slope:.4f} m/s²"
            results["steps"]["拟合优度 R²"] = f"{R2:.6f}"
            results["final"]["拟合斜率法重力加速度 g"] = f"{g_fit:.4f} m/s²"

        return results

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过单摆法测量当地重力加速度。分别使用重复测量平均值法和多摆长线性拟合法求得重力加速度 g。"
        }
