from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "显微镜的使用"


def handle(workpath, extension):
    return 1


def schema():
    return make_schema(
        "记录显微镜在不同物镜倍率下的定标结果，以及衍射元件和样品尺寸测量值。",
        [
            make_table(
                "calibration", "物镜定标",
                ["物镜倍率", "标尺实际长度 μm", "图像像素长度 px", "标定系数 μm/px"],
                sample=[[4, 1000, 820, 1.2195], [10, 500, 1025, 0.4878], [40, 100, 820, 0.1220]],
            ),
            make_table(
                "diffraction_elements", "衍射元件参数",
                ["单缝缝宽 μm", "双缝中心间距 μm", "小孔直径 μm"],
                sample=[[102.4, 251.8, 198.6]],
            ),
            make_table(
                "specimens", "待测样品尺寸",
                ["单模光纤直径 μm", "头发直径 μm", "孢子长度 μm", "孢子宽度 μm"],
                sample=[[125.1, 72.8, 38.6, 24.2]],
            ),
        ],
        analysis_hints="每次测量必须使用与当前物镜倍率匹配的定标系数；样品尺寸建议重复测量后取平均。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["已保存物镜定标、衍射元件和样品尺寸数据；显微图像仍由原显微镜软件负责拍摄与测量。"],
    )
