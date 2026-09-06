"""生活中的物理实验模块。

本实验以现场观察和操作体验为主，网站只展示实验入口，不提供数据表格、
计算、作图或报告生成功能。
"""

from structured_support import make_schema


def name():
    return "生活中的物理实验"


def schema():
    result = make_schema(
        description="本实验以现场观察和操作体验为主，无需在网站中进行数据处理。",
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
