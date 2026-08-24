"""
霍尔效应实验插件
===============
二级大物电磁学实验 —— 霍尔效应

实验内容：
本实验包含三组独立测量：
1. 霍尔电压 VH 与控制电流 IS 的关系
2. 霍尔电压 VH 与励磁电流 IM 的关系
3. 霍尔系数 RH 随温度 T 的变化（变温霍尔效应）

每组数据独立进行异常检验和图表生成，
最终合并三组数据生成完整实验报告。

物理背景：
霍尔效应：在通有电流的导体或半导体上施加磁场，
则会产生垂直于电流和磁场方向的霍尔电压。
U_H = (R_H * I * B) / d
其中 R_H 为霍尔系数，I 为工作电流，B 为磁感应强度，d 为样品厚度。
"""

from . import ExperimentPlugin


class HallEffect(ExperimentPlugin):
    """霍尔效应实验插件（三数据表）"""
    name = "霍尔效应（实验指导）"
    _mod_name = "exp28"
    category = "二级-电磁学"
    description = "霍尔效应实验（三数据表：V<sub>H</sub>-I<sub>S</sub>、V<sub>H</sub>-I<sub>M</sub>、R<sub>H</sub>-T）"
    required_fields = ["I<sub>S</sub>(mA)", "V<sub>H</sub>(mV)"]
    custom_template = "hall_effect.html"

    # 三组数据表的配置
    table_configs = [
        {
            "id": "table1",
            "title": "霍尔电压与控制电流关系数据表",
            "x_label": "控制电流 I<sub>S</sub> (mA)",
            "y_label": "霍尔电压 V<sub>H</sub> (mV)",
            "columns": ["I<sub>S</sub>(mA)", "V<sub>H</sub>(mV)"],
            "row_count": 3,
        },
        {
            "id": "table2",
            "title": "霍尔电压与励磁电流关系数据表",
            "x_label": "励磁电流 I<sub>M</sub> (A)",
            "y_label": "霍尔电压 V<sub>H</sub> (mV)",
            "columns": ["I<sub>M</sub>(A)", "V<sub>H</sub>(mV)"],
            "row_count": 3,
        },
        {
            "id": "table3",
            "title": "霍尔效应参数随温度变化关系数据表",
            "x_label": "温度 T (℃)",
            "y_label": "霍尔系数 R<sub>H</sub> (m³/C)",
            "columns": ["T(℃)", "R<sub>H</sub>(m³/C)"],
            "row_count": 3,
        },
    ]

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端填写三组数据后生成综合报告。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验研究霍尔效应，测量霍尔电压与控制电流、励磁电流的关系，以及变温条件下霍尔系数随温度的变化。"
        }
