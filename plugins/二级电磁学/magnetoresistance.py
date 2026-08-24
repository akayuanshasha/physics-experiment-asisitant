"""
磁阻效应实验插件
===============
二级大物电磁学实验 —— 磁阻效应

实验内容：
测量磁阻相对变化 ΔR/R(0) 与磁感应强度 B 的关系。
本实验包含两组独立测量，每组数据独立进行异常检验和图表生成，
最终合并两组数据生成完整实验报告。

物理背景：
磁阻效应是指材料的电阻在外加磁场下发生变化的现象。
在弱磁场下，磁阻与 B² 近似成正比：
    ΔR/R(0) = α·B²
其中 α 为磁阻系数，R(0) 为零磁场电阻。
"""

from . import ExperimentPlugin


class Magnetoresistance(ExperimentPlugin):
    """磁阻效应实验插件"""
    name = "磁阻效应（实验指导）"
    _mod_name = "exp26"
    category = "二级-电磁学"
    description = "测量磁阻相对变化与磁感应强度的关系（双数据表）"
    required_fields = ["B(T)", "ΔR/R<sub>(0)</sub>"]
    custom_template = "magnetoresistance.html"

    # 两组数据表的配置
    table_configs = [
        {
            "id": "table1",
            "title": "磁阻相对变化与磁感应强度关系数据表",
            "x_label": "磁感应强度 B (T)",
            "y_label": "相对磁阻变化 ΔR/R<sub>(0)</sub>",
            "columns": ["B(T)", "ΔR/R<sub>(0)</sub>"],
            "row_count": 3,
        },
        {
            "id": "table2",
            "title": "磁阻相对变化与磁感应强度关系数据表（另一组测量）",
            "x_label": "磁感应强度 B (T)",
            "y_label": "相对磁阻变化 ΔR/R<sub>(0)</sub>",
            "columns": ["B(T)", "ΔR/R<sub>(0)</sub>"],
            "row_count": 3,
        },
    ]

    def calculate(self, data, constants=None):
        """磁阻效应计算（两组数据合并）"""
        return {
            "status": "info",
            "message": "本实验请在网页端填写两组数据后生成综合报告。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验研究磁阻效应，测量磁阻相对变化 ΔR/R(0) 与磁感应强度 B 的关系。"
        }
