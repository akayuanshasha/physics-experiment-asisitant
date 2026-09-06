"""对切透镜的光学实验2：梅斯林（Maslin）对切透镜。

B 类课程只需完成基础内容和提升内容，两部分均为光路搭建、条纹观察、
清晰度调节及教师检查，不要求在网站中录入或处理数值数据。实验指导明确
说明实验2不写实验报告，因此本模块采用无表格、无计算、无作图的实验外壳。
"""

from structured_support import make_schema


def name():
    return "对切透镜的光学实验2"


def schema():
    result = make_schema(
        description=(
            "本实验的B类必做内容无需在网站中处理数据。基础内容：光源到梅斯林透镜L₁"
            "的距离为1倍焦距，L₁到L₂的距离为1倍焦距，调节并观察清晰条纹，思考条纹"
            "形状及其原因。提升内容：把光源到L₁的距离改为1.3倍焦距，L₁到L₂仍为1倍"
            "焦距，再次调节至条纹最清晰并请老师检查。实验常量为He-Ne激光波长632.8 nm、"
            "成像透镜焦距3.5 cm、梅斯林对切透镜焦距10 cm。"
        ),
        tables=[],
        report_enabled=False,
    )
    result["draft_enabled"] = False
    result["preview_enabled"] = False
    result["shell"] = True
    return result


def handle_structured(workpath, payload):
    return {
        "code": 1,
        "message": "实验2的B类必做内容无需在网站中提交或处理数据。",
    }


def handle(workpath, extension):
    return 1
