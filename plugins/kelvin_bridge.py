"""
双臂电桥实验插件
===============
二级大物电磁学实验 —— 双臂电桥

实验内容：
本实验包含四组数据表：
1. 铜棒与铝棒直径测量数据表（6次测量）
2. 30cm铜棒与铝棒电阻及电阻率测量表（3组正反向电流）
3. 不同长度铜棒电阻及均匀性数据表（7个长度）
4. Rx-L关系曲线图（散点+线性拟合）

每组数据独立进行自动计算，
表格4含异常检验和图表生成，
最终合并所有数据生成综合实验报告。
"""

from . import ExperimentPlugin


class KelvinBridge(ExperimentPlugin):
    """双臂电桥实验插件（四数据表）"""
    name = "双臂电桥（实验指导）"
    _mod_name = "exp32"
    category = "二级-电磁学"
    description = "双臂电桥测低电阻（四数据表：直径、电阻、均匀性、R<sub>x</sub>-L拟合）"
    required_fields = []
    custom_template = "kelvin_bridge.html"

    table_configs = [
        {
            "id": "table1",
            "title": "铜棒与铝棒直径测量数据表",
            "x_label": "测量次数",
            "y_label": "直径 (mm)",
            "columns": ["测量次数", "铜棒直径D<sub>Cu</sub>(mm)", "铝棒直径D<sub>Al</sub>(mm)"],
            "row_count": 6,
        },
        {
            "id": "table2",
            "title": "30cm铜棒与铝棒电阻及电阻率测量表",
            "x_label": "测量组别",
            "y_label": "电阻 (Ω)",
            "columns": ["测量组别", "铜棒正向R<sub>Cu+</sub>(Ω)", "铜棒反向R<sub>Cu-</sub>(Ω)",
                        "铝棒正向R<sub>Al+</sub>(Ω)", "铝棒反向R<sub>Al-</sub>(Ω)"],
            "row_count": 3,
        },
        {
            "id": "table3",
            "title": "不同长度铜棒电阻及均匀性数据表",
            "x_label": "电压头间距 L (cm)",
            "y_label": "电阻 R<sub>x</sub> (mΩ)",
            "columns": ["L(cm)", "正向R<sup>+</sup>(Ω)", "反向R<sup>-</sup>(Ω)",
                        "待测电阻R<sub>x</sub>(mΩ)", "单点电阻率ρ(10⁻⁸Ω·m)"],
            "row_count": 7,
        },
        {
            "id": "table4",
            "title": "R<sub>x</sub>-L 关系数据表（拟合用）",
            "x_label": "电压头间距 L (cm)",
            "y_label": "待测电阻 R<sub>x</sub> (mΩ)",
            "columns": ["L(cm)", "正向R<sup>+</sup>(Ω)", "反向R<sup>-</sup>(Ω)",
                        "待测电阻R<sub>x</sub>(mΩ)", "单点电阻率ρ(10⁻⁸Ω·m)"],
            "row_count": 7,
        },
    ]

    def calculate(self, data, constants=None):
        return {
            "status": "info",
            "message": "本实验请在网页端填写数据后进行自动计算与报告生成。"
        }

    def generate_chart(self, data, results, save_dir):
        return []

    def get_report_content(self, data, results):
        return {
            "purpose": "本实验通过测量铜棒和铝棒的直径、电阻等参数，计算其电阻率，并研究电阻与长度的线性关系。"
        }
