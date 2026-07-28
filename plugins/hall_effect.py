"""
霍尔效应实验插件
===============
B同学负责写具体物理公式的实现。

物理背景：
霍尔效应：在通有电流的导体或半导体上施加磁场，则会产生垂直于电流和磁场方向的霍尔电压。
U_H = (R_H * I * B) / d
其中 U_H 是霍尔电压，R_H 是霍尔系数，I 是工作电流，B 是磁感应强度，d 是样品厚度。

本实验通过改变励磁电流来改变磁场强度，测量对应的霍尔电压，
从而计算霍尔元件的灵敏度 K_H = U_H / (I * B) 或 霍尔系数 R_H。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from . import ExperimentPlugin, PluginRegistry


@PluginRegistry.register
class HallEffect(ExperimentPlugin):
    """霍尔效应实验插件"""
    name = "霍尔效应"
    category = "电磁学"
    description = "霍尔效应实验，测量霍尔电压与磁场的关系"
    required_fields = ["励磁电流(A)", "霍尔电压(mV)", "工作电流(mA)"]

    def calculate(self, data, constants=None):
        """霍尔效应计算

        参数 data 格式:
        {
            "励磁电流(A)": [0.1, 0.2, 0.3, 0.4, 0.5],
            "霍尔电压(mV)": [2.1, 4.3, 6.4, 8.6, 10.7],
            "工作电流(mA)": [5.0] 或 [5.0, 5.0, 5.0, 5.0, 5.0]
        }
        """
        import warnings

        I_mag = np.array(data.get("励磁电流(A)", []), dtype=float)      # 励磁电流
        U_H = np.array(data.get("霍尔电压(mV)", []), dtype=float)       # 霍尔电压
        I_work = np.array(data.get("工作电流(mA)", []), dtype=float)    # 工作电流

        if len(I_mag) == 0 or len(U_H) == 0:
            raise ValueError("缺少必要的实验数据，请确保提供了励磁电流和霍尔电压")

        # 如果工作电流只有一个值（恒定不变），扩展为与励磁电流相同长度
        if len(I_work) == 1:
            I_work = np.full_like(I_mag, I_work[0])

        # 1. 计算灵敏度 K_H = U_H / (I_work * B)
        # 这里假设磁场 B 与励磁电流成正比（螺线管中 B = μ₀*n*I），因此 K = U_H / (I_work * I_mag)
        # 实际实验中如有定标曲线，应使用定标磁场值
        I_product = I_work * I_mag / 1000.0  # I_work 是 mA，除以1000转为A

        # 线性拟合：U_H = K * (I_work * I_mag)
        # 斜率 K 即为霍尔元件灵敏度 (mV/A²·A)
        x = I_product
        y = U_H

        n = len(x)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        k_num = np.sum((x - x_mean) * (y - y_mean))
        k_den = np.sum((x - x_mean) ** 2)

        if k_den == 0:
            raise ValueError("工作电流与励磁电流的乘积无变化，无法拟合")

        slope = k_num / k_den
        y_pred = slope * x
        residuals = y - y_pred
        s_res = np.sqrt(np.sum(residuals ** 2) / (n - 2)) if n > 2 else 0
        slope_std = s_res / np.sqrt(k_den)

        # 拟合优度
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        steps = {
            "励磁电流范围": f"{I_mag.min():.2f} ~ {I_mag.max():.2f} A",
            "工作电流": f"{np.mean(I_work):.2f} mA",
            "数据点数": f"{n}",
            "U_H 范围": f"{U_H.min():.2f} ~ {U_H.max():.2f} mV",
        }

        final = {
            "霍尔元件灵敏度 K_H": f"({slope:.4f} ± {slope_std:.4f}) mV/(mA·A)",
            "单位说明": "K_H = U_H / (I_work * I_mag)",
            "拟合优度 R²": f"{r_squared:.4f}",
        }

        return {"steps": steps, "final": final}

    def generate_chart(self, data, results, save_dir):
        """生成 U_H - (I_work * I_mag) 关系图"""
        I_mag = np.array(data.get("励磁电流(A)", []), dtype=float)
        U_H = np.array(data.get("霍尔电压(mV)", []), dtype=float)
        I_work = np.array(data.get("工作电流(mA)", []), dtype=float)

        if len(I_work) == 1:
            I_work = np.full_like(I_mag, I_work[0])

        I_product = I_work * I_mag / 1000.0

        final = results.get("final", {})
        k_str = final.get("霍尔元件灵敏度 K_H", "N/A")
        r2_str = final.get("拟合优度 R²", "N/A")

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(I_product, U_H, color='#2ca02c', s=50, label='实验数据点', zorder=5)

        # 拟合直线
        x_mean = np.mean(I_product)
        y_mean = np.mean(U_H)
        k = np.sum((I_product - x_mean) * (U_H - y_mean)) / np.sum((I_product - x_mean) ** 2)
        x_line = np.linspace(min(I_product), max(I_product), 100)
        y_line = k * x_line
        ax.plot(x_line, y_line, 'r--', linewidth=2, label='拟合直线')

        ax.set_xlabel('I_work · I_mag (A·A)', fontsize=12)
        ax.set_ylabel('霍尔电压 U_H (mV)', fontsize=12)
        ax.set_title('霍尔效应 — 霍尔电压与工作电流×励磁电流关系', fontsize=14)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        text = f"灵敏度 K_H = {k_str}\n拟合优度 R² = {r2_str}"
        ax.text(0.05, 0.95, text, transform=ax.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        save_path = Path(save_dir) / "hall_effect_fit.png"
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
        return [str(save_path)]

    def get_report_content(self, data, results):
        steps_info = results.get("steps", {})
        final_info = results.get("final", {})

        table_rows = ""
        I_mag = data.get("励磁电流(A)", [])
        U_H = data.get("霍尔电压(mV)", [])
        for i, (im, uh) in enumerate(zip(I_mag, U_H)):
            table_rows += f"  {i+1}. 励磁电流 {im} A → 霍尔电压 {uh} mV\n"

        return {
            "purpose": "本实验通过霍尔效应测量霍尔元件的灵敏度。霍尔效应是电磁学中的重要现象，"
                       "广泛应用于磁场测量、电流检测和传感器技术中。",
            "principle": "当通有电流的半导体置于磁场中时，载流子受到洛伦兹力作用，在垂直于电流和磁场的方向上"
                        "产生电势差，称为霍尔电压。U_H = (R_H · I · B) / d = K_H · I · B，"
                        "其中 K_H = R_H / d 为霍尔元件灵敏度。\n"
                        "本实验通过改变励磁电流来改变磁场，测量对应的霍尔电压。",
            "steps": f"实验测量数据：\n{table_rows}\n"
                     + "\n".join(f"  {k}: {v}" for k, v in steps_info.items()),
            "final": "\n".join(f"  {k}: {v}" for k, v in final_info.items()),
            "analysis": f"霍尔电压与工作电流和励磁电流的乘积呈良好的线性关系。\n"
                        f"拟合优度 R² = {final_info.get('拟合优度 R²', 'N/A')}。\n"
                        f"实验结果验证了霍尔效应的基本原理。"
        }