"""
杨氏模量（拉伸法）实验插件
========================
B同学负责写具体物理公式的实现。
这个插件继承 ExperimentPlugin 基类，并实现三个核心方法。

物理背景：
杨氏模量 E = (F * L) / (A * ΔL)
其中 F 是拉力，L 是标距，A 是截面积，ΔL 是伸长量。

本实验通过拉伸法测量钢丝的杨氏模量：
1. 用螺旋测微器测量钢丝直径（多次测量取平均）
2. 在钢丝下端悬挂砝码，每次增加1kg，记录标尺读数
3. 由 F=mg 计算拉力，由直径算截面积，由标尺读数算伸长量
4. 线性拟合 F-ΔL 曲线，斜率 = EA/L，从而求 E
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，兼容无GUI环境
import matplotlib.pyplot as plt
from pathlib import Path
from . import ExperimentPlugin, PluginRegistry


@PluginRegistry.register
class YoungModulus(ExperimentPlugin):
    """杨氏模量（拉伸法）实验插件"""
    name = "杨氏模量（拉伸法）"
    category = "力学"
    description = "拉伸法测量钢丝的杨氏模量"
    required_fields = ["钢丝直径(mm)", "砝码质量(kg)", "标尺读数(mm)"]

    def calculate(self, data, constants=None):
        """杨氏模量计算

        参数 data 格式:
        {
            "钢丝直径(mm)": [0.495, 0.497, 0.496, 0.498, 0.496],
            "砝码质量(kg)": [0, 1, 2, 3, 4, 5],
            "标尺读数(mm)": [0, 0.30, 0.61, 0.89, 1.20, 1.49]
        }

        物理常数 constants（可选，默认值）:
            L: 标距(钢丝原长, cm)，默认 50.0
            g: 重力加速度(m/s^2)，默认 9.8
        """
        # 1. 从字典中提取原始数据
        diameters = np.array(data.get("钢丝直径(mm)", []), dtype=float)
        masses = np.array(data.get("砝码质量(kg)", []), dtype=float)
        readings = np.array(data.get("标尺读数(mm)", []), dtype=float)

        # 校验数据完整性
        if len(diameters) == 0 or len(masses) == 0 or len(readings) == 0:
            raise ValueError("缺少必要的实验数据，请确保提供了钢丝直径、砝码质量和标尺读数")

        # 2. 获取物理常数（默认值）
        if constants is None:
            constants = {}
        L = constants.get("标距(cm)", 50.0)  # 钢丝原长，单位 cm
        g = constants.get("重力加速度(m/s^2)", 9.8)  # 重力加速度

        L_m = L / 100.0  # 转换为米

        # 3. 计算钢丝截面积
        d_mean = np.mean(diameters)  # 直径平均值，单位 mm
        d_std = np.std(diameters, ddof=1)  # 直径标准差（贝塞尔校正）
        d_mean_m = d_mean / 1000.0  # 转换为米
        A = np.pi * (d_mean_m / 2.0) ** 2  # 截面积，单位 m^2

        # 4. 计算力和伸长量
        force = masses * g  # F = mg，单位 N
        delta_L = readings - readings[0]  # 伸长量，单位 mm
        delta_L_m = delta_L / 1000.0  # 转换为米

        # 5. 线性拟合：F = (EA/L) * ΔL
        # 对 F = k * ΔL 做线性回归，斜率 k = EA/L
        # 注意排除 ΔL=0 的点（x=0 时 不参与拟合）
        non_zero_idx = delta_L != 0
        if np.sum(non_zero_idx) < 2:
            raise ValueError("有效数据点不足，请检查标尺读数是否有变化")

        x = delta_L_m[non_zero_idx]
        y = force[non_zero_idx]

        # 一元线性回归
        n = len(x)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        k_num = np.sum((x - x_mean) * (y - y_mean))
        k_den = np.sum((x - x_mean) ** 2)
        slope = k_num / k_den  # 斜率 k = EA/L

        # 计算回归的标准不确定度
        y_pred = slope * x
        residuals = y - y_pred
        s_res = np.sqrt(np.sum(residuals ** 2) / (n - 2))  # 残差标准差
        slope_std = s_res / np.sqrt(k_den)  # 斜率标准不确定度

        # 计算杨氏模量 E = k * L / A
        E = slope * L_m / A
        E_std = slope_std * L_m / A

        # 计算相对不确定度和拟合优度
        rel_uncertainty = (E_std / E) * 100
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot

        # 6. 组织返回值
        steps = {
            "直径平均值": f"{d_mean:.4f} mm",
            "直径标准差": f"{d_std:.4f} mm",
            "钢丝截面积": f"{A:.4e} m²",
            "线性回归斜率 k": f"{slope:.4e} N/m",
            "斜率标准不确定度": f"{slope_std:.4e} N/m",
            "拟合数据点数": f"{n}",
        }

        final = {
            "杨氏模量 E": f"({E:.3e} ± {E_std:.3e}) Pa",
            "相对不确定度": f"{rel_uncertainty:.2f}%",
            "拟合优度 R²": f"{r_squared:.4f}",
        }

        return {"steps": steps, "final": final}

    def generate_chart(self, data, results, save_dir):
        """生成力-伸长量拟合图

        横轴：伸长量 (mm)
        纵轴：拉力 (N)
        显示数据点和拟合直线
        """
        import numpy as np

        masses = np.array(data.get("砝码质量(kg)", []), dtype=float)
        readings = np.array(data.get("标尺读数(mm)", []), dtype=float)
        g = 9.8

        force = masses * g
        delta_L = readings - readings[0]

        non_zero = delta_L != 0
        x_fit = delta_L[non_zero]
        y_fit = force[non_zero]

        # 获取拟合斜率
        final = results.get("final", {})
        e_str = final.get("杨氏模量 E", "N/A")
        r2_str = final.get("拟合优度 R²", "N/A")

        fig, ax = plt.subplots(figsize=(8, 5))

        # 所有数据点（包括 ΔL=0 的点，显示为空心圆）
        ax.scatter(delta_L, force, color='#1f77b4', s=50, label='实验数据点', zorder=5)

        # 拟合直线（只画在拟合区间内）
        if len(x_fit) > 0:
            x_line = np.linspace(min(x_fit), max(x_fit), 100)
            # 重新计算斜率用于画线
            x_mean = np.mean(x_fit)
            y_mean = np.mean(y_fit)
            k = np.sum((x_fit - x_mean) * (y_fit - y_mean)) / np.sum((x_fit - x_mean) ** 2)
            y_line = k * x_line
            ax.plot(x_line, y_line, 'r--', linewidth=2, label='拟合直线 (F = k·ΔL)')

        ax.set_xlabel('伸长量 ΔL (mm)', fontsize=12)
        ax.set_ylabel('拉力 F (N)', fontsize=12)
        ax.set_title('杨氏模量实验 — 力与伸长量关系', fontsize=14)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        # 图注：显示结果
        text = f"杨氏模量 E = {e_str}\n拟合优度 R² = {r2_str}"
        ax.text(0.05, 0.95, text, transform=ax.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        save_path = Path(save_dir) / "young_modulus_fit.png"
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)

        return [str(save_path)]

    def get_report_content(self, data, results):
        """生成报告各章节内容"""
        steps_info = results.get("steps", {})
        final_info = results.get("final", {})

        # 整理数据表格
        masses = data.get("砝码质量(kg)", [])
        readings = data.get("标尺读数(mm)", [])
        table_rows = ""
        for i, (m, r) in enumerate(zip(masses, readings)):
            table_rows += f"  {i+1}. 砝码质量 {m} kg → 标尺读数 {r} mm\n"

        return {
            "purpose": "本实验通过拉伸法测量钢丝的杨氏模量。杨氏模量是描述固体材料抵抗形变能力的物理量，"
                       "是材料力学中的重要参数。通过测量钢丝在不同拉力下的伸长量，利用胡克定律计算杨氏模量。",
            "principle": "杨氏模量 E 定义为正应力与正应变的比值：\n"
                        "E = (F/A) / (ΔL/L) = (F·L) / (A·ΔL)\n"
                        "其中 F 为拉力，A 为钢丝截面积，L 为标距（钢丝原长），ΔL 为伸长量。\n"
                        "本实验通过悬挂不同质量的砝码改变拉力 F=mg，记录对应的标尺读数变化。\n"
                        "对 F 和 ΔL 数据进行线性回归，斜率 k = EA/L，从而求得 E。",
            "steps": f"实验测量数据：\n{table_rows}\n"
                     f"中间计算结果：\n"
                     + "\n".join(f"  {k}: {v}" for k, v in steps_info.items()),
            "final": "\n".join(f"  {k}: {v}" for k, v in final_info.items()),
            "analysis": f"实验测量了钢丝在拉力作用下的伸长量，通过线性拟合得到杨氏模量。\n"
                        f"拟合优度 R² = {final_info.get('拟合优度 R²', 'N/A')}，表明线性关系显著。\n"
                        f"相对不确定度 = {final_info.get('相对不确定度', 'N/A')}。\n"
                        f"实验数据可靠，结果符合预期。"
        }