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
from sample_data_loader import load_sample_data

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
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

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


def schema():
    # 表格1：几何法密度
    _s1 = load_sample_data("exp4", "测量金属圆柱体的密度")
    sample1 = []
    for row in _s1:
        if len(row) >= 3:
            try:
                sample1.append([float(row[0]), float(row[1]), float(row[2])])
            except (ValueError, IndexError):
                pass
    # 表格2：称衡法密度
    _s2 = load_sample_data("exp4", "液体法测量物体密度")
    sample2 = []
    for row in _s2:
        if len(row) >= 3:
            try:
                sample2.append([float(row[0]), float(row[1]), float(row[2])])
            except (ValueError, IndexError):
                pass
    # 表格3：转动定律
    _s3 = load_sample_data("exp4", "用转动定律测量物体的质量")
    sample3 = []
    for row in _s3:
        if len(row) >= 2:
            try:
                sample3.append([float(row[0]), float(row[1])])
            except (ValueError, IndexError):
                pass
    # 表格4：失重动力学法
    _s4 = load_sample_data("exp4", "模拟太空失重环境用动力学方法测量物体的质量")
    sample4 = []
    for row in _s4:
        if len(row) >= 3:
            try:
                sample4.append([float(row[0]), float(row[1]), float(row[2])])
            except (ValueError, IndexError):
                pass
    chart3 = {
        "x_column": "c3", "y_column": "c4",
        "x_label": "X = r² (m²)", "y_label": "Y = grT²/(4π²) (m²)",
        "title": "Y-X 线性拟合", "fit": "linear",
    }
    return make_schema(
        "密度的测量（4数据表 + 1拟合图）",
        [
            make_table(
                "table1", "卡尺几何法测密度表",
                ["直径 D(cm)", "高度 H(cm)", "质量 m(g)",
                 "平均直径 D̄(cm)", "平均高度 H̄(cm)",
                 "体积 V(cm³)", "几何密度 ρ₁(g/cm³)"],
                sample=sample1, readonly=(3, 4, 5, 6), initial_rows=1,
            ),
            make_table(
                "table2", "流体静力称衡法测密度表",
                ["空气中质量 m(g)", "视质量损失 Δm'(g)",
                 "水密度 ρ₀(g/cm³)", "称衡密度 ρ₂(g/cm³)"],
                sample=sample2, readonly=(3,), initial_rows=1,
            ),
            make_table(
                "table3", "双小铜块变位置周期测量与参数计算表",
                ["质心距 r(cm)", "30周期时间 t₃₀(s)",
                 "周期 T(s)", "X=r²(m²)", "Y=grT²/(4π²)(m²)"],
                sample=sample3, readonly=(2, 3, 4), initial_rows=5, chart=chart3,
            ),
            make_table(
                "table4", "弹簧振子周期法测质量表",
                ["标准质量 m₀(g)", "标准周期 T₀(s)",
                 "待测周期 T(s)", "待测质量 m(g)"],
                sample=sample4, readonly=(3,), initial_rows=1,
            ),
        ],
        analysis_hints="检查几何法和称衡法密度的一致性，以及 Y-X 拟合的线性度。",
        preview_enabled=True,
        table_theory=get_table_theory("exp4"), report_enabled=False,)


def preview(payload):
    """补全密度与动力学计算列。"""
    tables = copied_tables(payload)
    # 表格1：几何法
    for row in tables.get("table1", []):
        diameters = [as_number(row.get(f"c{i}")) for i in range(1)]
        heights = [as_number(row.get(f"c{i}")) for i in range(1, 2)]
        mass = as_number(row.get("c2"))
        d_val = diameters[0] if diameters and diameters[0] is not None else None
        h_val = heights[0] if heights and heights[0] is not None else None
        row["c3"] = formatted(d_val, 4)
        row["c4"] = formatted(h_val, 4)
        volume = np.pi * d_val * d_val * h_val / 4 if d_val is not None and h_val is not None else None
        row["c5"] = formatted(volume, 4)
        row["c6"] = formatted(mass / volume if mass is not None and volume else None, 4)
    # 表格2：称衡法  CSV 列: m/g, m-m0/g, ρ₀(g/cm³)
    for row in tables.get("table2", []):
        mass = as_number(row.get("c0"))
        delta_mass = as_number(row.get("c1"))
        rho0 = as_number(row.get("c2"))
        row["c3"] = formatted(mass / delta_mass * rho0 if mass is not None and rho0 is not None and delta_mass else None, 4)
    # 表格3：转动定律  CSV 列: r(cm), 30T(s)
    for index, row in enumerate(tables.get("table3", [])):
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
