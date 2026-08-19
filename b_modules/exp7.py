from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "固体比热"


def handle(workpath, extension):
    return 1


def schema():
    cooling_chart = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "时间 (min)", "y_label": "温度 (℃)",
        "title": "温度-时间曲线", "fit": "line",
    }
    return make_schema(
        "按实验指导书分别记录混合法和冷却法测量固体比热所需的数据。",
        [
            make_table(
                "mixing_constants", "混合法质量与环境参数",
                ["锌粒质量 mx/g", "量热器质量 m1/g", "量热器加水后质量 (m1+m)/g", "大气压强 p/kPa", "沸点 T′/℃"],
                sample=[[120.0, 85.6, 235.6, 100.8, 99.8]],
                description="质量和气压均按实验现场读数填写。",
            ),
            make_table(
                "mixing_curve", "混合法温度-时间记录",
                ["时间 t/min", "水温 T/℃"],
                sample=[[-5, 20.1], [-4, 20.2], [-3, 20.3], [-2, 20.4], [-1, 20.5],
                        [0, 35.8], [1, 34.9], [2, 34.2], [3, 33.6], [5, 32.8], [10, 31.1], [15, 29.9]],
                chart=cooling_chart,
            ),
            make_table(
                "reference_cooling", "冷却法标准铜样品记录",
                ["温度 θ/℃", "通过温区所需时间 Δt/s", "样品质量 M/g"],
                sample=[[110, 42.1, 45.0], [105, 46.8, 45.0], [100, 52.4, 45.0], [95, 59.3, 45.0], [90, 67.8, 45.0]],
                required=False,
            ),
            make_table(
                "sample_cooling", "冷却法待测金属记录",
                ["温度 θ/℃", "通过温区所需时间 Δt/s", "样品质量 M/g"],
                sample=[[110, 47.6, 45.0], [105, 52.9, 45.0], [100, 59.0, 45.0], [95, 66.7, 45.0], [90, 75.6, 45.0]],
                required=False,
            ),
        ],
        analysis_hints="混合法应由温度-时间曲线外推混合前后温度；冷却法应在相同温度区间比较标准样品与待测样品的冷却时间。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["已按实验指导书分表保存混合法与冷却法数据；当前模块尚无自动比热计算公式。"],
    )
