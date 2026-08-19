from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "透镜参数测量"


def handle(workpath, extension):
    return 1


def schema():
    return make_schema(
        "按照实验数据记录页，将凸透镜和凹透镜的不同测量方法分别录入。",
        [
            make_table(
                "convex_object_image", "凸透镜焦距：物像距法",
                ["序号", "物距 u/mm", "像距 v/mm"],
                sample=[[1, 300, 151.2], [2, 300, 150.8], [3, 300, 151.0], [4, 300, 150.9], [5, 300, 151.1], [6, 300, 150.7]],
                min_rows=6,
            ),
            make_table(
                "convex_displacement", "凸透镜焦距：位移法",
                ["序号", "物屏距离 L/mm", "透镜位移 l/mm"],
                sample=[[1, 600, 346.2], [2, 600, 345.8], [3, 600, 346.0], [4, 600, 345.9], [5, 600, 346.1], [6, 600, 345.7]],
                min_rows=6,
            ),
            make_table(
                "convex_autocollimation", "凸透镜焦距：自准直法",
                ["序号", "透镜焦距 f/mm"],
                sample=[[1, 100.2], [2, 99.8], [3, 100.1], [4, 100.0], [5, 99.9], [6, 100.1]],
                min_rows=6,
            ),
            make_table(
                "concave_object_image", "凹透镜焦距：物像距法",
                ["序号", "虚物距 u/mm", "虚像距 v/mm"],
                sample=[[1, 80.0, 48.1], [2, 80.0, 47.9], [3, 80.0, 48.0]],
                min_rows=3,
            ),
            make_table(
                "concave_autocollimation", "凹透镜焦距：自准直法",
                ["序号", "组合系统位置 x1/mm", "凹透镜位置 x2/mm", "辅助凸透镜焦距 f0/mm"],
                sample=[[1, 420.0, 470.2, 100.0], [2, 420.0, 469.8, 100.0], [3, 420.0, 470.1, 100.0]],
                min_rows=3,
                required=False,
            ),
        ],
        analysis_hints="物像距法用 1/f=1/u+1/v；位移法用 f=(L²-l²)/(4L)。重复测量应先求平均值。",
    )


def handle_structured(workpath, payload):
    return structured_result(
        workpath, name(), schema(), payload,
        summary=["已按物像距法、位移法和自准直法分别保存凸透镜与凹透镜数据；当前模块尚无自动焦距计算公式。"],
    )
