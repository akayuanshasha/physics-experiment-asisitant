"""
数字表改装实验插件
=================
二级大物电磁学实验 —— 数字表改装

实验内容：
本实验包含两组数据表：
1. 多量程直流数字电压表电路参数表（5个量程）
2. 20V量程电压表内阻影响测试表（3组测试）

每组数据独立进行异常检验。
"""

from . import ExperimentPlugin


class DigitalMeter(ExperimentPlugin):
    """数字表改装实验插件（双数据表）"""
    name = "数字表改装（实验指导）"
    _mod_name = "exp31"
    category = "二级-电磁学"
    description = "多量程直流数字电压表组装与测试（双数据表）"
    required_fields = []
    custom_template = "digital_meter.html"

    table_configs = [
        {
            "id": "table1",
            "title": "多量程直流数字电压表电路参数表",
            "x_label": "电压量程",
            "y_label": "分压电阻阻值",
            "columns": ["电压量程(mV/V)", "分压电阻阻值(kΩ/MΩ)", "组装表内阻R<sub>g</sub>(kΩ/MΩ)"],
            "row_count": 5,
        },
        {
            "id": "table2",
            "title": "20V量程电压表内阻影响测试表",
            "x_label": "待测电路等效电阻 R<sub>s</sub>",
            "y_label": "相对误差",
            "columns": ["R<sub>s</sub>(kΩ/MΩ)", "U<sub>s1</sub>(V)", "U<sub>o1</sub>(V)", "相对误差(%)"],
            "row_count": 3,
        },
    ]

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端填写数据后进行异常分析。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验进行多量程直流数字电压表的组装与测试。"
        }
