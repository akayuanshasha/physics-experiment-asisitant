from head import *  # 导入万能头
from structured_support import make_schema, make_table, structured_result


def name():
    return "生活中的物理实验"


def handle(workpath, extension):
    return 1


def schema():
    return make_schema(
        "实验指导要求至少完成 7 个观察项目；网页用编号和完成状态记录，文字现象分析仍在实验记录单中完成。",
        [
            make_table(
                "activity_record", "生活中的物理实验完成记录",
                ["讲义项目编号（1-32）", "完成状态（1=完成）", "定量测量次数", "有效记录数"],
                sample=[[1, 1, 3, 3], [3, 1, 3, 3], [8, 1, 1, 1], [15, 1, 5, 5], [16, 1, 5, 5], [22, 1, 3, 3], [30, 1, 3, 3]],
                min_rows=7,
                initial_rows=7,
                description="每行对应讲义中的一个实验项目；至少填写 7 行。",
            ),
        ],
        analysis_hints="网页只保存结构化完成记录，不替代指导书要求的‘观察到的现象和可能原理’文字记录。",
    )


def handle_structured(workpath, payload):
    rows = (payload.get("tables") or {}).get("activity_record") or []
    completed = sum(1 for row in rows if str(row.get("c1", "")).strip() not in ("", "0", "0.0"))
    warnings = [] if completed >= 7 else [f"当前仅记录 {completed} 个已完成项目，实验指导要求至少 7 个。"]
    return structured_result(
        workpath, name(), schema(), payload,
        summary=[f"已记录 {completed} 个完成项目；现象与原理分析请按实验记录单要求另行填写。"],
        warnings=warnings,
    )
