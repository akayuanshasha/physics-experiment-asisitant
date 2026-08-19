"""
交流谐振电路实验插件
===================
二级大物电磁学实验 —— 交流谐振电路

实验内容：
本实验包含三组数据表：
1. RLC串联电路幅频特性 (R=400Ω) —— 三点法测通频带宽
2. RLC串联电路幅频特性 (R=600Ω) —— 研究电阻对谐振特性的影响
3. 品质因数 Q 的不同方法计算与对比

每组数据独立进行异常检验和图表生成。
"""

from . import ExperimentPlugin


class ACCircuit(ExperimentPlugin):
    """交流谐振电路实验插件（三数据表）"""
    name = "交流谐振电路（实验指导）"
    _mod_name = "exp29"
    category = "二级-电磁学"
    description = "RLC串联谐振电路幅频特性与品质因数测量（三数据表）"
    required_fields = ["f(kHz)", "V<sub>i,pp</sub>(V)", "V<sub>R,pp</sub>(V)", "I<sub>pp</sub>(mA)"]
    custom_template = "ac_circuit.html"

    table_configs = [
        {
            "id": "table1",
            "title": "RLC串联电路幅频特性数据表 (R = 400.0 Ω)",
            "x_label": "频率 f (kHz)",
            "y_label": "回路电流 I<sub>pp</sub> (mA)",
            "columns": ["测量点", "f(kHz)", "V<sub>i,pp</sub>(V)", "V<sub>R,pp</sub>(V)", "I<sub>pp</sub>(mA)"],
            "row_count": 3,
        },
        {
            "id": "table2",
            "title": "RLC串联电路幅频特性数据表 (R = 600.0 Ω)",
            "x_label": "频率 f (kHz)",
            "y_label": "回路电流 I<sub>pp</sub> (mA)",
            "columns": ["测量点", "f(kHz)", "V<sub>i,pp</sub>(V)", "V<sub>R,pp</sub>(V)", "I<sub>pp</sub>(mA)"],
            "row_count": 3,
        },
        {
            "id": "table3",
            "title": "品质因数 Q 的不同方法计算与对比表",
            "x_label": "测定条件",
            "y_label": "Q 值",
            "columns": ["测定条件/参数类型", "R=400.0Ω 测量与计算值", "R=600.0Ω 测量与计算值"],
            "row_count": 3,
        },
    ]

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端填写三组数据后进行分析。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验研究RLC串联谐振电路的幅频特性与品质因数。"
        }
