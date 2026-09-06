"""密度的测量实验模块
==============================
本实验包含四部分，共四组数据表 + 一个图表：

第一部分：金属圆柱体密度的测量
  表格1：卡尺几何法测密度表
    → 多次测量 D、H，计算 D̄、H̄、V、ρ₁
  表格2：流体静力称衡法测密度表
    → 计算 Δm、ρ₂

第二部分：利用转动定律测量物体质量
  表格3：双小铜块变位置周期测量与参数计算表（5行）
    → 计算 T、X=r²、Y=grT²/(4π²)
  图表1：Y - X 线性拟合图 → 由截距 b 计算 Ic

第三部分：模拟太空失重动力学法测质量
  表格4：弹簧振子周期法测质量表
    → 计算 m = m₀·T²/T₀²

物理公式：
  V = (π/4)·D̄²·H̄                    （圆柱体积）
  ρ₁ = m/V                           （几何法密度）
  ρ₂ = m/(m-m₁)·ρ₀                  （称衡法密度）
  Y = g·r·T²/(4π²)                   （转动定律参量）
  m = m₀·T²/T₀²                      （失重动力学法质量）
"""

import numpy as np
from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory

def name(): # 返回实验名称
    return "测量金属圆柱体的密度"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["d","h","m"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["d","h","m"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        res_E=analyse_com("ρ=4*m/(pi*d*d*h)",(),(("m",data["m"][0]),("d",data["d"]),("h",data["h"])),"g/cm^3")

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph("测量金属圆柱体的密度") # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("密度")
        docu.add_paragraph()._element.append(latex_to_word(res_E.ansx2))
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph(res_E.ansx)

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1


def _set_units(table, units):
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    chart3 = {
        "x_column": "c3", "y_column": "c4",
        "x_label": "X = r² (m²)", "y_label": "Y = grT²/(4π²) (m²)",
        "title": "Y-X 线性拟合", "fit": "linear",
    }
    # 表格1：卡尺几何法（示例数据取自 exp4 示例 CSV）
    table1 = _set_units(
        make_table(
            "table1", "卡尺几何法测密度表",
            ["直径 D(cm)", "高度 H(cm)", "质量 m(g)",
             "平均直径 D̄(cm)", "平均高度 H̄(cm)",
             "体积 V(cm³)", "几何密度 ρ₁(g/cm³)"],
            sample=[[2.49, 3.994, 163.25, "", "", "", ""]],
            readonly=(3, 4, 5, 6), min_rows=1, initial_rows=1,
            description="输入圆柱体的直径、高度与质量，平均量、体积与密度由后端自动计算。",
        ),
        ["cm", "cm", "g", "cm", "cm", "cm³", "g/cm³"],
    )
    # 表格2：流体静力称衡法（示例数据取自 exp4 示例 CSV）
    table2 = _set_units(
        make_table(
            "table2", "流体静力称衡法测密度表",
            ["空气中质量 m(g)", "视质量损失 Δm'(g)",
             "水密度 ρ₀(g/cm³)", "称衡密度 ρ₂(g/cm³)"],
            sample=[[163.25, 19.35, 0.997, ""]],
            readonly=(3,), min_rows=1, initial_rows=1,
            description="输入空气中的质量、视质量损失与水密度，称衡密度由后端自动计算。",
        ),
        ["g", "g", "g/cm³", "g/cm³"],
    )
    # 表格3：转动定律（示例数据取自 exp4 示例 CSV）
    table3 = _set_units(
        make_table(
            "table3", "双小铜块变位置周期测量与参数计算表",
            ["质心距 r(cm)", "30周期时间 t₃₀(s)",
             "周期 T(s)", "X=r²(m²)", "Y=grT²/(4π²)(m²)"],
            sample=[
                [35.51, 55.50, "", "", ""],
                [31.05, 55.87, "", "", ""],
                [24.52, 58.30, "", "", ""],
                [18.11, 63.30, "", "", ""],
                [12.18, 73.14, "", "", ""],
            ],
            readonly=(2, 3, 4), min_rows=3, initial_rows=5, chart=chart3,
            description="输入质心距 r 与 30 个周期的累积时间，周期与拟合参量由后端自动计算。",
        ),
        ["cm", "s", "s", "m²", "m²"],
    )
    # 表格4：失重动力学法（示例数据取自 exp4 示例 CSV，10T 已转换为周期 T）
    table4 = _set_units(
        make_table(
            "table4", "弹簧振子周期法测质量表",
            ["标准质量 m₀(g)", "标准周期 T₀(s)",
             "待测周期 T(s)", "待测质量 m(g)"],
            sample=[[99.77, 1.719, 1.923, ""]],
            readonly=(3,), min_rows=1, initial_rows=1,
            description="输入标准质量及其周期、待测物体周期，待测质量由后端自动计算。",
        ),
        ["g", "s", "s", "g"],
    )
    return make_schema(
        (
            "本实验研究测量金属棒密度的多种方法：\n① 卡尺几何法（测直径、高度与质量）；"
            "\n② 流体静力称衡法 " r"$\rho = \frac{m}{m-m'}\rho_0$" "；\n③ 转动定律法（移动双小铜块改变"
            "质心位置，测摆动周期）；\n④ 弹簧振子周期法。请完成全部四种方法的数据处理。"
        ),
        [table1, table2, table3, table4],
        analysis_hints="检查几何法和称衡法密度的一致性，以及 Y-X 拟合的线性度。",
        preview_enabled=True,
        formulas=get_formulas("exp4"),
        variables=get_variables("exp4"),
        table_theory=get_table_theory("exp4"),
        report_enabled=False,
    )


def preview(payload):
    """补全密度与动力学计算列。"""
    tables = copied_tables(payload)
    # 表格1：几何法
    for row in tables.get("table1", []):
        d_val = as_number(row.get("c0"))
        h_val = as_number(row.get("c1"))
        mass = as_number(row.get("c2"))
        row["c3"] = formatted(d_val, 4)
        row["c4"] = formatted(h_val, 4)
        volume = np.pi * d_val * d_val * h_val / 4 if d_val is not None and h_val is not None else None
        row["c5"] = formatted(volume, 4)
        row["c6"] = formatted(mass / volume if mass is not None and volume else None, 4)
    # 表格2：称衡法
    for row in tables.get("table2", []):
        mass = as_number(row.get("c0"))
        delta_mass = as_number(row.get("c1"))
        rho0 = as_number(row.get("c2"))
        row["c3"] = formatted(mass / delta_mass * rho0 if mass is not None and rho0 is not None and delta_mass else None, 4)
    # 表格3：转动定律
    for row in tables.get("table3", []):
        r_cm = as_number(row.get("c0"))
        elapsed = as_number(row.get("c1"))
        period = elapsed / 30 if elapsed is not None else None
        r_m = r_cm / 100 if r_cm is not None else None
        row["c2"] = formatted(period, 6)
        row["c3"] = formatted(r_m * r_m if r_m is not None else None, 8)
        value = 9.8 * r_m * period * period / (4 * np.pi * np.pi) if r_m is not None and period is not None else None
        row["c4"] = formatted(value, 8)
    # 表格4：失重动力学法
    for row in tables.get("table4", []):
        mass0 = as_number(row.get("c0"))
        base_period = as_number(row.get("c1"))
        period = as_number(row.get("c2"))
        value = mass0 * period * period / (base_period * base_period) if mass0 is not None and base_period and period is not None else None
        row["c3"] = formatted(value, 4)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["几何法、称衡法密度及转动定律、失重动力学法数据已处理，派生量已由后端计算。"],
    )
