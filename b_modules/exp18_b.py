"""用分光计测三棱镜折射率 —— 外壳实验。

《一级大物实验指导·光学》中收录了本实验，但数据处理功能尚未开发。
当前只提供占位页面（无任何数据表），内部功能之后开发。
"""

from structured_support import make_schema
from theory_content import get_formulas, get_variables, get_table_theory


def name():
    return "用分光计测三棱镜折射率"


def schema():
    structured_schema = make_schema(
        description="🚧 本实验尚未上线：数据表格与自动计算功能正在开发中，敬请期待。",
        tables=[],

        table_theory=get_table_theory("exp18_b"),)
    structured_schema["report_enabled"] = False
    structured_schema["draft_enabled"] = False
    structured_schema["shell"] = True
    return structured_schema


def handle_structured(workpath, payload):
    return {"code": 1, "message": "「用分光计测三棱镜折射率」尚未上线，数据处理功能正在开发中。",
        "formulas": get_formulas("exp18_b"),
        "variables": get_variables("exp18_b"),}
