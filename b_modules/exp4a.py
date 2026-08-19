from head import * # 导入万能头
import numpy as np
from structured_support import (
    as_number, copied_tables, make_schema, make_table, ordered_rows,
    parameter_values, result_lines, structured_result,
)

def name(): # 返回实验名称
    return "测量金属圆柱体的密度"


def display_name():
    return "密度的测量B（实验指导）"

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
    return make_schema(
        "通过几何法、流体静力称衡法、转动定律和弹簧振子法测量密度或质量。",
        [
            make_table(
                "table1", "卡尺几何法测密度表",
                ["D₁(cm)", "D₂(cm)", "D₃(cm)", "H₁(cm)", "H₂(cm)", "H₃(cm)", "质量 m(g)",
                 "平均直径 D̄(cm)", "平均高度 H̄(cm)", "体积 V(cm³)", "几何密度 ρ₁(g/cm³)"],
                readonly=(7, 8, 9, 10),
                sample=[[2.002, 2.004, 2.003, 4.998, 5.001, 5.000, 123.50, "", "", "", ""]],
            ),
            make_table(
                "table2", "流体静力称衡法测密度表",
                ["水温 t(℃)", "纯水密度 ρ₀(g/cm³)", "空气中质量 m(g)", "水中读数 m₁(g)",
                 "浮力差 Δm(g)", "称衡密度 ρ₂(g/cm³)"],
                readonly=(4, 5), sample=[[20, 0.9982, 123.50, 107.80, "", ""]],
            ),
            make_table(
                "table3", "双小铜块变位置周期测量与参数计算表",
                ["序号", "质心距 r(m)", "30周期时间 t₃₀(s)", "周期 T(s)", "X=r²(m²)", "Y=grT²/(4π²)(m²)"],
                readonly=(0, 3, 4, 5),
                sample=[
                    [1, 0.030, 24.10, "", "", ""], [2, 0.040, 25.00, "", "", ""],
                    [3, 0.050, 26.10, "", "", ""], [4, 0.060, 27.35, "", "", ""],
                    [5, 0.070, 28.72, "", "", ""],
                ],
                chart={
                    "x_column": "c4", "y_column": "c5", "x_label": "X = r² (m²)",
                    "y_label": "Y = grT²/(4π²) (m²)", "title": "转动定律 Y-X 线性拟合", "fit": "linear",
                },
            ),
            make_table(
                "table4", "弹簧振子周期法测质量表",
                ["标准质量 m₀(g)", "标准周期 T₀(s)", "待测周期 T(s)", "待测质量 m(g)"],
                readonly=(3,), sample=[[100, 1.20, 1.70, ""]],
            ),
        ],
        parameters=[
            {"id": "two_m", "label": "两个小铜块总质量 2m", "unit": "g", "type": "number", "default": 0},
        ],
        analysis_hints="比较两种密度测量结果，检查Y-X线性关系以及动力学测质量的一致性。",
        preview_enabled=True,
        revision=4,
    )


def preview(payload):
    tables = copied_tables(payload)
    for row in tables.get("table1", []):
        diameters = [as_number(row.get(f"c{index}")) for index in range(3)]
        heights = [as_number(row.get(f"c{index}")) for index in range(3, 6)]
        diameters = [value for value in diameters if value is not None]
        heights = [value for value in heights if value is not None]
        mass = as_number(row.get("c6"))
        diameter = sum(diameters) / len(diameters) if diameters else None
        height = sum(heights) / len(heights) if heights else None
        volume = np.pi * diameter ** 2 * height / 4 if diameter is not None and height is not None else None
        row["c7"] = f"{diameter:.4f}" if diameter is not None else ""
        row["c8"] = f"{height:.4f}" if height is not None else ""
        row["c9"] = f"{volume:.4f}" if volume is not None else ""
        row["c10"] = f"{mass / volume:.4f}" if mass is not None and volume else ""
    for row in tables.get("table2", []):
        water_density, mass, immersed_mass = (as_number(row.get(key)) for key in ("c1", "c2", "c3"))
        difference = mass - immersed_mass if mass is not None and immersed_mass is not None else None
        row["c4"] = f"{difference:.4f}" if difference is not None else ""
        row["c5"] = f"{mass / difference * water_density:.4f}" if mass is not None and water_density is not None and difference else ""
    for index, row in enumerate(tables.get("table3", [])):
        radius, elapsed = as_number(row.get("c1")), as_number(row.get("c2"))
        period = elapsed / 30 if elapsed is not None else None
        row["c0"] = index + 1
        row["c3"] = f"{period:.6f}" if period is not None else ""
        row["c4"] = f"{radius * radius:.8f}" if radius is not None else ""
        value = 9.8 * radius * period ** 2 / (4 * np.pi ** 2) if radius is not None and period is not None else None
        row["c5"] = f"{value:.8f}" if value is not None else ""
    for row in tables.get("table4", []):
        known_mass, known_period, measured_period = (as_number(row.get(key)) for key in ("c0", "c1", "c2"))
        value = known_mass * measured_period ** 2 / known_period ** 2 if known_mass is not None and known_period and measured_period is not None else None
        row["c3"] = f"{value:.4f}" if value is not None else ""
    return {"tables": tables}


def _calculate_structured(data, constants=None):
    constants = constants or {}
    results = {"steps": {}, "final": {}}
    for row in data.get("table1", []):
        density = as_number(row[10]) if len(row) >= 11 else None
        if density is not None:
            results["final"]["几何法密度 ρ₁"] = f"{density:.4f} g/cm³"
    for row in data.get("table2", []):
        density = as_number(row[5]) if len(row) >= 6 else None
        if density is not None:
            results["final"]["称衡法密度 ρ₂"] = f"{density:.4f} g/cm³"

    x_values, y_values = [], []
    for row in data.get("table3", []):
        x_value = as_number(row[4]) if len(row) >= 6 else None
        y_value = as_number(row[5]) if len(row) >= 6 else None
        if x_value is not None and y_value is not None:
            x_values.append(x_value)
            y_values.append(y_value)
    if len(x_values) >= 2 and np.ptp(x_values) != 0:
        slope, intercept = np.polyfit(np.asarray(x_values), np.asarray(y_values), 1)
        predicted = slope * np.asarray(x_values) + intercept
        residual = float(np.sum((np.asarray(y_values) - predicted) ** 2))
        total = float(np.sum((np.asarray(y_values) - np.mean(y_values)) ** 2))
        results["steps"].update({
            "Y-X 拟合斜率 k": f"{slope:.6f}", "Y-X 拟合截距 b": f"{intercept:.6f} m²",
            "Y-X 拟合优度 R²": f"{1 - residual / total if total else 0:.6f}",
        })
        total_block_mass = as_number(constants.get("two_m"))
        if total_block_mass and total_block_mass > 0:
            results["final"]["木条转动惯量 I_c"] = f"{total_block_mass / 1000 * intercept:.6e} kg·m²"
        else:
            results.setdefault("warnings", []).append("未填写两个小铜块总质量 2m，未计算木条转动惯量。")

    for row in data.get("table4", []):
        measured_mass = as_number(row[3]) if len(row) >= 4 else None
        if measured_mass is not None:
            results["final"]["失重动力学法质量 m"] = f"{measured_mass:.4f} g"
    return results


def handle_structured(workpath, payload):
    prepared = dict(payload)
    prepared["tables"] = preview(payload)["tables"]
    current_schema = schema()
    results = _calculate_structured(ordered_rows(current_schema, prepared), parameter_values(current_schema, prepared))
    summary, warnings = result_lines(results)
    return structured_result(workpath, display_name(), current_schema, prepared, summary=summary, warnings=warnings)
