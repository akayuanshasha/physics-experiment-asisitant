"""
杨氏模量实验插件（光杠杆法 + 单缝衍射法）
==========================================
本实验包含两种测量方法，共三组数据表：

第一部分：光杠杆法
  表格1：钢丝直径 d 的多次测量（5次，求平均，不绘图）
  表格2：光杠杆拉伸形变数据（7行，加减砝码读数，不绘图）
  图表1：b - F 线性拟合图 → 由斜率 M 计算 E

第二部分：单缝衍射法
  表格3：单缝衍射伸长量计算（5行，纯数据处理，不绘图）
  图表2：ΔL - F 线性拟合图 → 由斜率计算 E

物理公式：
  E = 8DL / (π d̄² l M)    （光杠杆法）
  E = 8DL / (π d̄² l k)    （单缝衍射法，k = ΔL/F 斜率）
"""

import numpy as np
from . import ExperimentPlugin


class YoungModulus(ExperimentPlugin):
    name = "杨氏模量B（实验指导）"
    _mod_name = "exp5"
    category = "一级-力学"
    description = "光杠杆法 + 单缝衍射法测量钢丝杨氏模量（3数据表 + 2拟合图）"
    required_fields = ["d<sub>i</sub>(mm)"]
    custom_template = "young_modulus.html"

    # ── 三组数据表配置 ──
    table_configs = [
        {
            "id": "table1",
            "title": "钢丝直径测量表（不绘图）",
            "columns": ["d<sub>i</sub>(mm)"],
            "row_count": 5,
        },
        {
            "id": "table2",
            "title": "光杠杆拉伸形变数据表（不绘图）",
            "columns": [
                "砝码(kg)", "b<sub>+</sub>(mm)", "b<sub>-</sub>(mm)",
                "b\u0304(mm)", "b(mm)"
            ],
            "row_count": 7,
        },
        {
            "id": "table3",
            "title": "单缝衍射伸长量计算表（不绘图）",
            "columns": [
                "砝码(kg)", "条纹宽度 x(mm)", "伸长量 ΔL(μm)"
            ],
            "row_count": 5,
        },
    ]

    def preview(self, payload):
        """在后端补全光杠杆平均值、位移和衍射伸长量。"""
        from copy import deepcopy

        tables = deepcopy(payload.get("tables") or {})
        parameters = payload.get("parameters") or {}

        def number(value, fallback=None):
            try:
                return float(value) if str(value).strip() else fallback
            except (TypeError, ValueError):
                return fallback

        rows = tables.get("table2", [])
        first_average = None
        for index, row in enumerate(rows):
            plus, minus = number(row.get("c1")), number(row.get("c2"))
            average = (plus + minus) / 2 if plus is not None and minus is not None else None
            if index == 0:
                first_average = average
            row["c3"] = f"{average:.3f}" if average is not None else ""
            row["c4"] = f"{average - first_average:.3f}" if average is not None and first_average is not None else ""
        wavelength = number(parameters.get("wavelength"), 632.8) * 1e-9
        screen_distance = number(parameters.get("screen_distance"), 100.0) * 1e-2
        diffraction_rows = tables.get("table3", [])
        first_width = number(diffraction_rows[0].get("c1")) if diffraction_rows else None
        for row in diffraction_rows:
            width = number(row.get("c1"))
            value = None
            if width and first_width:
                value = wavelength * screen_distance * (1 / (width * 1e-3) - 1 / (first_width * 1e-3)) * 1e6
            row["c2"] = f"{value:.4f}" if value is not None else ""
        return {"tables": tables}

    def calculate(self, data, constants=None):
        """根据三表格数据计算杨氏模量

        data 格式:
        {
            "table1": [[d1], [d2], ...],          # 钢丝直径
            "table2": [[m, b+, b-, b_avg, b], ...], # 光杠杆数据
            "table3": [[m, x, deltaL], ...],       # 单缝衍射数据
        }
        """
        if constants is None:
            constants = {}

        # ── 物理常数 ──
        L_cm = constants.get("钢丝原长L(cm)", 50.0)
        D_cm = constants.get("镜尺距D(cm)", 100.0)
        l_cm = constants.get("臂长l(cm)", 4.0)
        g = 9.8

        L_m = L_cm / 100.0
        D_m = D_cm / 100.0
        l_m = l_cm / 100.0

        results = {"steps": {}, "final": {}}

        # ════════════════════════════════════════
        # 第一部分：光杠杆法
        # ════════════════════════════════════════
        t1 = data.get("table1", [])
        t2 = data.get("table2", [])

        # 表格1：直径平均值
        diameters = []
        for row in t1:
            if row and row[0].strip():
                try:
                    diameters.append(float(row[0]))
                except ValueError:
                    pass

        if len(diameters) < 2:
            return {"status": "error", "message": "表格1至少需要2个有效直径数据"}

        d_arr = np.array(diameters)
        d_mean = np.mean(d_arr)
        d_std = np.std(d_arr, ddof=1)
        d_mean_m = d_mean / 1000.0
        A = np.pi * (d_mean_m / 2.0) ** 2

        results["steps"]["直径平均值 d̄"] = f"{d_mean:.4f} mm"
        results["steps"]["直径标准差 σ_d"] = f"{d_std:.4f} mm"
        results["steps"]["截面积 A"] = f"{A:.4e} m²"

        # 表格2：光杠杆数据处理
        forces = []
        b_values = []
        for row in t2:
            if not row or len(row) < 5:
                continue
            try:
                mass = float(row[0]) if row[0].strip() else None
                b_plus = float(row[1]) if row[1].strip() else None
                b_minus = float(row[2]) if row[2].strip() else None
                b_val = float(row[4]) if len(row) > 4 and row[4].strip() else None
                if mass is not None and b_val is not None:
                    forces.append(mass * g)
                    b_values.append(b_val)
            except (ValueError, IndexError):
                continue

        if len(forces) < 2:
            results["final"]["光杠杆法"] = "数据不足，无法计算"
        else:
            F_arr = np.array(forces)
            b_arr = np.array(b_values)

            # 线性拟合 b = M·F + b0
            n = len(F_arr)
            F_mean = np.mean(F_arr)
            b_mean_val = np.mean(b_arr)
            k_num = np.sum((F_arr - F_mean) * (b_arr - b_mean_val))
            k_den = np.sum((F_arr - F_mean) ** 2)
            M_slope = k_num / k_den  # 斜率 mm/N

            # R²
            y_pred = M_slope * F_arr + (b_mean_val - M_slope * F_mean)
            ss_res = np.sum((b_arr - y_pred) ** 2)
            ss_tot = np.sum((b_arr - b_mean_val) ** 2)
            R2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0

            # E = 8DL / (π d̄² l M)
            # 注意 M 单位是 mm/N，需转为 m/N
            M_slope_m = M_slope / 1000.0
            if M_slope_m > 0:
                E_lever = 8 * D_m * L_m / (np.pi * d_mean_m**2 * l_m * M_slope_m)
            else:
                E_lever = 0

            results["steps"]["b-F 拟合斜率 M"] = f"{M_slope:.4f} mm/N"
            results["steps"]["拟合优度 R²"] = f"{R2:.6f}"
            results["final"]["光杠杆法杨氏模量 E"] = f"{E_lever:.3e} Pa"

        # ════════════════════════════════════════
        # 第二部分：单缝衍射法
        # ════════════════════════════════════════
        t3 = data.get("table3", [])

        forces_dl = []
        dl_values = []
        for row in t3:
            if not row or len(row) < 3:
                continue
            try:
                mass = float(row[0]) if row[0].strip() else None
                dl = float(row[2]) if row[2].strip() else None
                if mass is not None and dl is not None:
                    forces_dl.append(mass * g)
                    dl_values.append(dl)
            except (ValueError, IndexError):
                continue

        if len(forces_dl) < 2:
            results["final"]["单缝衍射法"] = "数据不足，无法计算"
        else:
            F_dl = np.array(forces_dl)
            dl_arr = np.array(dl_values)

            # 线性拟合 ΔL = k·F + c
            F_dl_mean = np.mean(F_dl)
            dl_mean_val = np.mean(dl_arr)
            k_num2 = np.sum((F_dl - F_dl_mean) * (dl_arr - dl_mean_val))
            k_den2 = np.sum((F_dl - F_dl_mean) ** 2)
            k_slope = k_num2 / k_den2  # μm/N

            y_pred2 = k_slope * F_dl + (dl_mean_val - k_slope * F_dl_mean)
            ss_res2 = np.sum((dl_arr - y_pred2) ** 2)
            ss_tot2 = np.sum((dl_arr - dl_mean_val) ** 2)
            R2_dl = 1 - ss_res2 / ss_tot2 if ss_tot2 != 0 else 0

            # E = 8DL / (π d̄² l k)
            # k 单位 μm/N → m/N
            k_slope_m = k_slope * 1e-6
            if k_slope_m > 0:
                E_diff = 8 * D_m * L_m / (np.pi * d_mean_m**2 * l_m * k_slope_m)
            else:
                E_diff = 0

            results["steps"]["ΔL-F 拟合斜率 k"] = f"{k_slope:.4f} μm/N"
            results["steps"]["ΔL-F 拟合 R²"] = f"{R2_dl:.6f}"
            results["final"]["单缝衍射法杨氏模量 E"] = f"{E_diff:.3e} Pa"

        # 实验参数
        results["steps"]["钢丝原长 L"] = f"{L_cm} cm"
        results["steps"]["镜尺距 D"] = f"{D_cm} cm"
        results["steps"]["臂长 l"] = f"{l_cm} cm"

        return results

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过拉伸法测量钢丝的杨氏模量。分别使用光杠杆法和单缝衍射法测量微小伸长量，"
                       "通过线性拟合法求得杨氏模量 E。"
        }
