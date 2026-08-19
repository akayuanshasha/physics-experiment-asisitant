from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "磁力摆"


def handle(workpath, extension):
    return 1


def schema():
    return make_schema(
        "记录亥姆霍兹线圈磁场、地磁场、磁力摆运动以及双磁针耦合运动数据。",
        [
            make_table(
                "coil_field", "亥姆霍兹线圈轴向磁场分布",
                ["位置 x/cm", "线圈电流 I/A", "磁感应强度 B/mT"],
                sample=[[-10, 0.50, 0.31], [-5, 0.50, 0.42], [0, 0.50, 0.46], [5, 0.50, 0.42], [10, 0.50, 0.31]],
                chart={"x_column": "c0", "y_column": "c2", "x_label": "x (cm)", "y_label": "B (mT)", "title": "线圈轴向磁场分布", "fit": "line"},
            ),
            make_table(
                "geomagnetic_field", "局域地磁场水平分量测量",
                ["测量序号", "线圈电流 I/A", "偏转角 θ/°", "线圈磁场 B/mT"],
                sample=[[1, 0.08, 30, 0.074], [2, 0.12, 45, 0.111], [3, 0.18, 60, 0.166]],
            ),
            make_table(
                "magnetic_pendulum", "小磁针振动特性",
                ["磁场 B/mT", "初始角度 θ0/°", "振动次数 n", "总时间 nT/s"],
                sample=[[0.05, 5, 20, 37.8], [0.10, 5, 20, 27.1], [0.15, 5, 20, 22.3], [0.20, 5, 20, 19.4]],
                chart={"x_column": "c0", "y_column": "c3", "x_label": "B (mT)", "y_label": "nT (s)", "title": "磁场与振动时间", "fit": "line"},
            ),
            make_table(
                "coupled_pendulums", "双磁针耦合运动",
                ["磁针间距 d/cm", "同相 20T+/s", "反相 20T-/s", "拍周期 Tb/s"],
                sample=[[8, 36.2, 28.4, 65.0], [10, 37.0, 30.1, 78.5], [12, 37.5, 32.0, 96.2]],
                required=False,
            ),
        ],
        analysis_hints="基础部分比较线圈磁场的空间分布并求地磁场水平分量；提升与进阶部分分析周期、磁场和耦合间距的关系。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["已分表保存磁场分布、地磁场测量、单磁针振动和双磁针耦合数据；当前模块尚无自动拟合公式。"],
    )
