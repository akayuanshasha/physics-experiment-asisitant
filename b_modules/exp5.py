from head import * # 导入万能头
import numpy as np
from structured_support import (
    as_number, copied_tables, make_schema, make_table, ordered_rows,
    parameter_values, result_lines, structured_result,
)

def name(): # 返回实验名称
    return "用拉伸法测量钢丝的杨氏模量"


def display_name():
    return "杨氏模量B（实验指导）"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["D","l","L","d","n","b1","b2"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["D","l","L","d","n","b1","b2"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        res_D=analyse(data["D"], 0.12, 0.05, "D", "cm")
        res_l=analyse(data["l"], 0.12, 0.05, "l", "cm")
        res_L=analyse(data["L"], 0.12, 0.05, "L", "cm")
        res_d=analyse(data["d"], 0.004, 0.005, "d", "mm")

        data["砝码总质量m/g"]=[n*500 for n in data["n"]]
        data["金属丝受拉力F/N"]=[m/1000*9.8 for m in data["砝码总质量m/g"]]
        data["标尺读数平均值b/cm"]=[(data["b1"][i]+data["b2"][i])/2 for i in range(len(data["b1"]))]

        res_lsm=analyse_lsm(data["金属丝受拉力F/N"], data["标尺读数平均值b/cm"], "F", "b", "cm/N", "cm") # 线性回归

        res_E=analyse_com("E=(8*D*L)/(pi*d**2*l*m)",(("D",res_D.average,res_D.unc),("L",res_L.average,res_L.unc),("d",res_d.average/10,res_d.unc/10),("l",res_l.average,res_l.unc),("m",abs(res_lsm.m),res_lsm.u_m)),(),"N/cm^2")

        fig, ax = plt.subplots()  # 新建绘图对象

        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        # 设置副刻度为主刻度的一半

        ax.plot(data["金属丝受拉力F/N"], data["标尺读数平均值b/cm"], "o", color='r', markersize=3) # 绘制数据点
        ax.plot(data["金属丝受拉力F/N"], res_lsm.b + res_lsm.m*data["金属丝受拉力F/N"], color='b', linewidth=1.5) # 拟合直线
        # 作图，详见 https://www.runoob.com/matplotlib/matplotlib-marker.html 和 https://www.runoob.com/matplotlib/matplotlib-line.html
        ax.set_title("标尺读数与金属丝受拉力 b-F 关系曲线", fontproperties=zhfont) # 若有中文，需加fontproperties=zhfont
        ax.set_xlabel("金属丝受拉力 F/N", fontproperties=zhfont)
        ax.set_ylabel("标尺读数 b/cm", fontproperties=zhfont)
        # 添加标题和轴标签，详见 https://www.runoob.com/matplotlib/matplotlib-label.html

        imgpath=workpath+"img.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        insert_data(docu, "标尺到平面镜的距离D", res_D, "word")
        insert_data(docu, "光杠杆的臂长l", res_l, "word")
        insert_data(docu, "钢丝原长L", res_L, "word")
        insert_data(docu, "钢丝直径d", res_d, "word")

        docu.add_paragraph("金属丝受拉力F与标尺读数b的关系：")
        table = docu.add_table(rows=len(data["砝码总质量m/g"])+1, cols=3, style="Table Grid") # 在Word文档中插入表格
        table.cell(0,0).text = '砝码总质量m/g'
        table.cell(0,1).text = '金属丝受拉力F/N'
        table.cell(0,2).text = '标尺读数平均值b/cm'
        for i in range(len(data["砝码总质量m/g"])):
            table.cell(i+1,0).text = ('%.5g' % data["砝码总质量m/g"][i])
            table.cell(i+1,1).text = ('%.5g' % data["金属丝受拉力F/N"][i])
            table.cell(i+1,2).text = ('%.5g' % data["标尺读数平均值b/cm"][i])
        docu.add_paragraph()

        docu.add_paragraph("最小二乘法拟合：")
        docu.add_picture(imgpath) # 在Word文档中添加图片
        insert_data_lsm(docu, res_lsm, "word")

        docu.add_paragraph("杨氏模量")
        docu.add_paragraph()._element.append(latex_to_word(res_E.ansx2))
        docu.add_paragraph("杨氏模量E的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_E.uncx2))
        docu.add_paragraph("杨氏模量最终结果")
        docu.add_paragraph()._element.append(latex_to_word(res_E.finalx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        insert_data(docu, "标尺到平面镜的距离D", res_D, "latex")
        insert_data(docu, "光杠杆的臂长l", res_l, "latex")
        insert_data(docu, "钢丝原长L", res_L, "latex")
        insert_data(docu, "钢丝直径d", res_d, "latex")

        docu.add_paragraph("金属丝受拉力F与标尺读数b的关系：")
        table = docu.add_table(rows=len(data["砝码总质量m/g"])+1, cols=3, style="Table Grid") # 在Word文档中插入表格
        table.cell(0,0).text = '砝码总质量m/g'
        table.cell(0,1).text = '金属丝受拉力F/N'
        table.cell(0,2).text = '标尺读数平均值b/cm'
        for i in range(len(data["砝码总质量m/g"])):
            table.cell(i+1,0).text = ('%.5g' % data["砝码总质量m/g"][i])
            table.cell(i+1,1).text = ('%.5g' % data["金属丝受拉力F/N"][i])
            table.cell(i+1,2).text = ('%.5g' % data["标尺读数平均值b/cm"][i])
        docu.add_paragraph()

        docu.add_paragraph("最小二乘法拟合：")
        docu.add_picture(imgpath) # 在Word文档中添加图片
        insert_data_lsm(docu, res_lsm, "latex")

        docu.add_paragraph("杨氏模量")
        docu.add_paragraph(res_E.ansx)
        docu.add_paragraph("杨氏模量E的延伸不确定度")
        docu.add_paragraph(res_E.uncx)
        docu.add_paragraph("杨氏模量最终结果")
        docu.add_paragraph(res_E.finalx)
        docu.add_paragraph()

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        os.remove(imgpath) # 删除刚才保存的图像

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1


def schema():
    parameters = [
        {"id": "L", "label": "钢丝原长 L", "unit": "cm", "type": "number", "default": 50, "backend_key": "钢丝原长L(cm)"},
        {"id": "D", "label": "镜尺距 D", "unit": "cm", "type": "number", "default": 100, "backend_key": "镜尺距D(cm)"},
        {"id": "l", "label": "光杠杆臂长 l", "unit": "cm", "type": "number", "default": 4, "backend_key": "臂长l(cm)"},
        {"id": "wavelength", "label": "激光波长 λ", "unit": "nm", "type": "number", "default": 632.8},
        {"id": "screen_distance", "label": "衍射屏距 Ds", "unit": "cm", "type": "number", "default": 100},
    ]
    return make_schema(
        "使用光杠杆法和单缝衍射法测量钢丝的杨氏模量。",
        [
            make_table(
                "table1", "钢丝直径测量表", ["dᵢ(mm)"],
                sample=[[0.495], [0.497], [0.496], [0.498], [0.496]],
            ),
            make_table(
                "table2", "光杠杆拉伸形变数据表",
                ["砝码(kg)", "b₊(mm)", "b₋(mm)", "b̄(mm)", "b(mm)"],
                readonly=(3, 4),
                sample=[
                    [0, 5.20, 5.18, "", ""], [1, 5.50, 5.52, "", ""], [2, 5.82, 5.80, "", ""],
                    [3, 6.12, 6.14, "", ""], [4, 6.44, 6.42, "", ""], [5, 6.74, 6.76, "", ""],
                    [6, 7.06, 7.04, "", ""],
                ],
                chart={
                    "x_column": "c0", "y_column": "c4", "x_label": "砝码质量 (kg)",
                    "y_label": "位移 b (mm)", "title": "光杠杆位移-载荷关系", "fit": "linear",
                },
            ),
            make_table(
                "table3", "单缝衍射伸长量计算表",
                ["砝码(kg)", "条纹宽度 x(mm)", "伸长量 ΔL(μm)"],
                readonly=(2,),
                sample=[[0, 2.500, ""], [1, 2.480, ""], [2, 2.460, ""], [3, 2.440, ""], [4, 2.420, ""]],
                chart={
                    "x_column": "c0", "y_column": "c2", "x_label": "砝码质量 (kg)",
                    "y_label": "伸长量 ΔL (μm)", "title": "单缝衍射伸长量-载荷关系", "fit": "linear",
                },
            ),
        ],
        parameters=parameters,
        analysis_hints="重点检查钢丝直径重复性、两种方法的线性拟合质量及杨氏模量是否处于钢材合理范围。",
        preview_enabled=True,
        revision=4,
    )


def preview(payload):
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    rows = tables.get("table2", [])
    first_average = None
    for row in rows:
        plus, minus = as_number(row.get("c1")), as_number(row.get("c2"))
        average = (plus + minus) / 2 if plus is not None and minus is not None else None
        if first_average is None and average is not None:
            first_average = average
        row["c3"] = f"{average:.3f}" if average is not None else ""
        row["c4"] = f"{average - first_average:.3f}" if average is not None and first_average is not None else ""

    wavelength = as_number(parameters.get("wavelength"))
    screen_distance = as_number(parameters.get("screen_distance"))
    wavelength = (632.8 if wavelength is None else wavelength) * 1e-9
    screen_distance = (100 if screen_distance is None else screen_distance) * 1e-2
    diffraction_rows = tables.get("table3", [])
    first_width = as_number(diffraction_rows[0].get("c1")) if diffraction_rows else None
    for row in diffraction_rows:
        width = as_number(row.get("c1"))
        value = None
        if width and first_width:
            value = wavelength * screen_distance * (1 / (width * 1e-3) - 1 / (first_width * 1e-3)) * 1e6
        row["c2"] = f"{value:.4f}" if value is not None else ""
    return {"tables": tables}


def _fit_result(x_values, y_values):
    if len(x_values) < 2 or np.ptp(x_values) == 0:
        return None
    x_array, y_array = np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float)
    slope, intercept = np.polyfit(x_array, y_array, 1)
    predicted = slope * x_array + intercept
    residual = float(np.sum((y_array - predicted) ** 2))
    total = float(np.sum((y_array - np.mean(y_array)) ** 2))
    return float(slope), 1 - residual / total if total else 0


def _calculate_structured(data, constants=None):
    constants = constants or {}
    length_cm = as_number(constants.get("钢丝原长L(cm)")) or 50.0
    distance_cm = as_number(constants.get("镜尺距D(cm)")) or 100.0
    arm_cm = as_number(constants.get("臂长l(cm)")) or 4.0
    results = {"steps": {}, "final": {}}

    diameters = [as_number(row[0]) for row in data.get("table1", []) if row]
    diameters = [value for value in diameters if value is not None]
    if len(diameters) < 2:
        return {"status": "error", "message": "钢丝直径测量表至少需要2个有效数据。"}
    diameter_mean = float(np.mean(diameters))
    diameter_std = float(np.std(diameters, ddof=1))
    diameter_m = diameter_mean / 1000
    results["steps"].update({
        "直径平均值 d̄": f"{diameter_mean:.4f} mm", "直径标准差 σ_d": f"{diameter_std:.4f} mm",
        "截面积 A": f"{np.pi * (diameter_m / 2) ** 2:.4e} m²",
    })

    forces, displacements = [], []
    for row in data.get("table2", []):
        if len(row) < 5:
            continue
        mass, displacement = as_number(row[0]), as_number(row[4])
        if mass is not None and displacement is not None:
            forces.append(mass * 9.8)
            displacements.append(displacement)
    lever_fit = _fit_result(forces, displacements)
    if lever_fit:
        slope, r_squared = lever_fit
        slope_m = slope / 1000
        modulus = 8 * (distance_cm / 100) * (length_cm / 100) / (np.pi * diameter_m ** 2 * (arm_cm / 100) * slope_m) if slope_m > 0 else 0
        results["steps"].update({"b-F 拟合斜率 M": f"{slope:.4f} mm/N", "b-F 拟合优度 R²": f"{r_squared:.6f}"})
        results["final"]["光杠杆法杨氏模量 E"] = f"{modulus:.3e} Pa"
    else:
        results["final"]["光杠杆法"] = "数据不足，无法计算"

    diffraction_forces, elongations = [], []
    for row in data.get("table3", []):
        if len(row) < 3:
            continue
        mass, elongation = as_number(row[0]), as_number(row[2])
        if mass is not None and elongation is not None:
            diffraction_forces.append(mass * 9.8)
            elongations.append(elongation)
    diffraction_fit = _fit_result(diffraction_forces, elongations)
    if diffraction_fit:
        slope, r_squared = diffraction_fit
        slope_m = slope * 1e-6
        modulus = 8 * (distance_cm / 100) * (length_cm / 100) / (np.pi * diameter_m ** 2 * (arm_cm / 100) * slope_m) if slope_m > 0 else 0
        results["steps"].update({"ΔL-F 拟合斜率 k": f"{slope:.4f} μm/N", "ΔL-F 拟合优度 R²": f"{r_squared:.6f}"})
        results["final"]["单缝衍射法杨氏模量 E"] = f"{modulus:.3e} Pa"
    else:
        results["final"]["单缝衍射法"] = "数据不足，无法计算"
    results["steps"].update({"钢丝原长 L": f"{length_cm} cm", "镜尺距 D": f"{distance_cm} cm", "臂长 l": f"{arm_cm} cm"})
    return results


def handle_structured(workpath, payload):
    prepared = dict(payload)
    prepared["tables"] = preview(payload)["tables"]
    current_schema = schema()
    results = _calculate_structured(ordered_rows(current_schema, prepared), parameter_values(current_schema, prepared))
    if results.get("status") == "error":
        return {"code": 1, "message": results.get("message", "实验计算失败")}
    summary, warnings = result_lines(results)
    return structured_result(workpath, display_name(), current_schema, prepared, summary=summary, warnings=warnings)
