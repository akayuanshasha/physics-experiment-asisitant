from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "示波器的使用"


def handle(workpath, extension):
    return 1


def schema():
    return make_schema(
        "依照实验指导书附录，将示波器必做和选做项目拆分为独立数据表。",
        [
            make_table(
                "square_wave", "1.1 自备方波周期测量",
                ["时基 ms/div", "波形格数", "直接周期 ms", "光标周期 ms", "自动测量周期 ms"],
                sample=[[0.2, 5.0, 1.00, 1.002, 1.001]],
            ),
            make_table(
                "asymmetric_wave", "1.2 非对称方波测量",
                ["设定频率 Hz", "时基 ms/div", "光标周期 ms", "光标正脉宽 ms", "光标频率 Hz", "光标占空比 %", "自动周期 ms", "自动正脉宽 ms", "自动频率 Hz", "自动占空比 %"],
                sample=[[1000, 0.2, 1.001, 0.300, 999.0, 30.0, 1.000, 0.301, 1000.0, 30.1]],
            ),
            make_table(
                "rise_time", "1.4 上升时间与脉冲宽度",
                ["AWG 上升时间 μs", "时基 μs/div", "光标上升时间 μs", "光标脉冲宽度 μs", "自动上升时间 μs", "自动脉冲宽度 μs"],
                sample=[[0.0168, 0.01, 0.018, 0.500, 0.017, 0.501], [2, 0.5, 2.05, 10.0, 2.02, 10.0], [20, 5, 20.3, 100.0, 20.1, 100.2]],
                required=False,
            ),
            make_table(
                "tdr", "1.5 TDR 同轴线传输时间",
                ["输入频率 MHz", "脉冲宽度 ns", "同轴线长度 m", "反射延迟 ns"],
                sample=[[1.0, 32.6, 10.0, 100.2]],
                required=False,
            ),
            make_table(
                "lissajous", "2.1 李萨如图形参数",
                ["时基 μs/div", "通道 1 峰峰值 V", "通道 2 峰峰值 V", "相位差 °", "频率 1 Hz", "频率 2 Hz"],
                sample=[[25, 2, 2, 0, 1000, 1000], [50, 2, 2, 45, 1000, 1000], [500, 4, 2, 90, 1000, 1000], [10000, 8, 2, 180, 1000, 1000]],
            ),
            make_table(
                "unknown_frequency", "2.2 李萨如图形测未知频率",
                ["已知频率 fx/Hz", "x 方向切点数 nx", "y 方向切点数 ny", "待测频率 fy/Hz"],
                sample=[[1000, 2, 3, 1500], [1000, 1, 2, 2000]],
                required=False,
            ),
        ],
        analysis_hints="分别比较直接读数、光标测量和自动测量结果；TDR 可由往返延迟和电缆长度求传播速度。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["已按照实验指导书附录的项目编号分表保存示波器测量数据；波形截图仍由实验记录另行保留。"],
    )
