"""
介电常数实验插件
===============
二级大物电磁学实验 —— 介电常数

实验内容：
本实验包含三个独立的数据处理模块：
1. 电容表直接法测固体介电常数
2. 固定间距法测固体介电常数（间距 3mm）
3. 电容表法测液体相对介电常数

每个模块包含公式展示、未知量说明和交互式计算功能。
"""

from . import ExperimentPlugin


class DielectricConstant(ExperimentPlugin):
    """介电常数实验插件（三模块交互式计算）"""
    name = "介电常数（实验指导）"
    _mod_name = "exp30"
    category = "二级-电磁学"
    description = "固体/液体相对介电常数测量（三模块交互式计算）"
    required_fields = []
    custom_template = "dielectric.html"

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端进行交互式计算。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过三种方法测量固体和液体的相对介电常数。"
        }
