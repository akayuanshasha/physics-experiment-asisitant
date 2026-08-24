"""
非平衡电桥实验插件
=================
二级大物电磁学实验 —— 非平衡电桥

实验内容：
测量非平衡电桥输出电压 Ug 与电阻相对变化 δ=ΔR/R₀ 的关系。
本实验包含两组独立测量（不同桥臂电阻条件），
每组数据独立进行异常检验和图表生成，
最终合并两组数据生成完整实验报告。

物理背景：
非平衡电桥是一种常用的测量电路，当桥臂电阻发生变化时，
电桥失去平衡，输出端产生电压差 Ug。
在小变化条件下，Ug 与 δ=ΔR/R₀ 近似成线性关系：
    Ug ≈ (E/4) · δ
其中 E 为激励电压。不同桥臂电阻 R₀ 会影响灵敏度和线性范围。
"""

from . import ExperimentPlugin


class UnbalancedBridge(ExperimentPlugin):
    """非平衡电桥实验插件"""
    name = "非平衡电桥（实验指导）"
    _mod_name = "exp27"
    category = "二级-电磁学"
    description = "测量非平衡电桥输出特性曲线（双数据表）"
    required_fields = ["δ=ΔR/R<sub>0</sub>", "U<sub>g</sub>(mV)"]
    custom_template = "unbalanced_bridge.html"

    # 两组数据表的配置
    table_configs = [
        {
            "id": "table1",
            "title": "非平衡电桥输出电压与电阻相对变化关系数据表",
            "x_label": "电阻相对变化 δ=ΔR/R<sub>0</sub>",
            "y_label": "桥路输出电压 U<sub>g</sub> (mV)",
            "columns": ["δ=ΔR/R<sub>0</sub>", "U<sub>g</sub>(mV)"],
            "row_count": 3,
        },
        {
            "id": "table2",
            "title": "不同桥臂电阻下非平衡电桥输出特性数据表",
            "x_label": "电阻相对变化 δ=ΔR/R<sub>0</sub>",
            "y_label": "桥路输出电压 U<sub>g</sub> (mV)",
            "columns": ["δ=ΔR/R<sub>0</sub>", "U<sub>g</sub>(mV)"],
            "row_count": 3,
        },
    ]

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端填写两组数据后生成综合报告。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验研究非平衡电桥的输出特性，测量桥路输出电压 Ug 与电阻相对变化 δ=ΔR/R₀ 的关系。"
        }
