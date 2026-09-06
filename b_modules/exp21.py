"""显微镜的使用实验模块。

本实验的数据测量和图像拍摄均在显微镜配套软件中完成，网站只展示实验入口，
不提供数据表格、计算、作图或报告生成功能。
"""

from structured_support import make_schema


def name():
    return "显微镜的使用"


def schema():
    result = make_schema(
        description=(
            "本实验以显微镜操作、软件定标、尺寸测量和图像拍摄为主，"
            "无需在网站中进行数据处理。"
        ),
        tables=[],
        report_enabled=False,
    )
    result["draft_enabled"] = False
    result["shell"] = True
    return result


def handle_structured(workpath, payload):
    return {
        "code": 1,
        "message": "本实验无需在网站中提交或处理数据。",
    }


def handle(workpath, extension):
    return 1
