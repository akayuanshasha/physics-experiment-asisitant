from head import * # 导入万能头
import numpy as np
from structured_support import (
    as_number, copied_tables, make_schema, make_table, ordered_rows,
    parameter_values, result_lines, structured_result,
)

def name(): # 返回实验名称
    return "表面张力（测量弹簧劲度系数）"


def display_name():
    return "表面张力B（实验指导）"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["砝码总质量m/g", "弹簧长度l/cm"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["砝码总质量m/g", "弹簧长度l/cm"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        g = 9.7947
        data["砝码重量G/N"]=[n/1000*g for n in data["砝码总质量m/g"]]
        data["弹簧长度l/m"]=[m/100 for m in data["弹簧长度l/cm"]]

        res_lsm=analyse_lsm(data["弹簧长度l/m"], data["砝码重量G/N"], "F", "l", "N/m", "N") # 线性回归

        fig, ax = plt.subplots()  # 新建绘图对象

        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        # 设置副刻度为主刻度的一半

        ax.plot(data["弹簧长度l/m"], data["砝码重量G/N"], "o", color='r', markersize=3) # 绘制数据点
        ax.plot(data["弹簧长度l/m"], res_lsm.b + res_lsm.m*data["弹簧长度l/m"], color='b', linewidth=1.5) # 拟合直线
        # 作图，详见 https://www.runoob.com/matplotlib/matplotlib-marker.html 和 https://www.runoob.com/matplotlib/matplotlib-line.html
        ax.set_title("砝码重量和弹簧长度 G-l 关系曲线", fontproperties=zhfont) # 若有中文，需加fontproperties=zhfont
        ax.set_xlabel("弹簧长度 l/m", fontproperties=zhfont)
        ax.set_ylabel("砝码重量 G/N", fontproperties=zhfont)
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

        docu.add_paragraph("砝码总质量 m 和弹簧长度 l 的关系：")
        table = docu.add_table(rows=len(data["砝码总质量m/g"])+1, cols=3, style="Table Grid") # 在Word文档中插入表格
        table.cell(0,0).text = '弹簧长度l/cm'
        table.cell(0,1).text = '砝码总质量m/g'
        table.cell(0,2).text = '砝码重量G/N'
        for i in range(len(data["砝码总质量m/g"])):
            table.cell(i+1,0).text = ('%.5g' % data["弹簧长度l/cm"][i])
            table.cell(i+1,1).text = ('%.5g' % data["砝码总质量m/g"][i])
            table.cell(i+1,2).text = ('%.5g' % data["砝码重量G/N"][i])
        docu.add_paragraph()

        docu.add_paragraph("最小二乘法拟合：")
        docu.add_picture(imgpath) # 在Word文档中添加图片
        insert_data_lsm(docu, res_lsm, "word")

        docu.add_paragraph("弹簧的劲度系数为：" + '%.5g' % res_lsm.m + ' N/m')
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        docu.add_paragraph("最小二乘法拟合：")
        docu.add_picture(imgpath) # 在Word文档中添加图片
        insert_data_lsm(docu, res_lsm, "latex")

        docu.add_paragraph("弹簧的劲度系数为：" + '%.5g' % res_lsm.m + ' N/m')

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        os.remove(imgpath) # 删除刚才保存的图像

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1


def schema():
    parameters = [
        {"id": "k", "label": "弹簧劲度系数 k", "unit": "N/m", "type": "number", "default": 0.50, "backend_key": "k"},
        {"id": "d", "label": "金属圈两脚间距 d", "unit": "cm", "type": "number", "default": 3.00, "backend_key": "d"},
    ]
    return make_schema(
        "完成弹簧定标，并测量不同液体及不同浓度洗洁精溶液的表面张力。",
        [
            make_table(
                "table1", "弹簧伸长量与拉力计算表",
                ["砝码质量 m(g)", "升降杆读数 x(cm)", "伸长量 Δx(cm)", "拉力 F(mN)"],
                readonly=(2, 3),
                sample=[
                    [0, 2.00, "", ""], [5, 2.10, "", ""], [10, 2.20, "", ""], [15, 2.30, "", ""],
                    [20, 2.40, "", ""], [25, 2.50, "", ""], [30, 2.60, "", ""], [35, 2.70, "", ""],
                    [40, 2.80, "", ""], [45, 2.90, "", ""],
                ],
                chart={
                    "x_column": "c2", "y_column": "c3", "x_label": "伸长量 Δx (cm)",
                    "y_label": "拉力 F (mN)", "title": "弹簧定标曲线", "fit": "linear",
                },
            ),
            make_table(
                "table2", "液膜破裂读数及表面张力计算表",
                ["液体类别", "初始读数 l₀(cm)", "破裂读数1(cm)", "破裂读数2(cm)", "破裂读数3(cm)",
                 "破裂读数4(cm)", "破裂读数5(cm)", "破裂均值 l̄(cm)", "拉力差 ΔF(mN)", "表面张力 σ(mN/m)"],
                readonly=(0, 7, 8, 9), text_columns=(0,),
                sample=[
                    ["自来水", 2.00, 6.25, 6.30, 6.28, 6.27, 6.29, "", "", ""],
                    ["洗洁精溶液", 2.00, 4.10, 4.08, 4.12, 4.09, 4.11, "", "", ""],
                ],
            ),
            make_table(
                "table3", "不同浓度洗洁精表面张力计算表",
                ["浓度 C(%)", "初始读数 l₀(cm)", "破裂均值 l̄(cm)", "表面张力 σ(mN/m)"],
                readonly=(3,),
                sample=[[0, 2.00, 6.28, ""], [0.5, 2.00, 5.10, ""], [1.0, 2.00, 4.45, ""], [2.0, 2.00, 4.10, ""]],
                chart={
                    "x_column": "c0", "y_column": "c3", "x_label": "浓度 C (%)",
                    "y_label": "表面张力 σ (mN/m)", "title": "表面张力随浓度变化", "fit": "auto",
                },
            ),
        ],
        parameters=parameters,
        analysis_hints="检查弹簧定标线性、破裂读数离散程度和表面张力随浓度的变化趋势。",
        preview_enabled=True,
        revision=4,
    )


def preview(payload):
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    stiffness = as_number(parameters.get("k"))
    distance = as_number(parameters.get("d"))
    stiffness = 0.50 if stiffness is None else stiffness
    distance = 3.00 if distance is None else distance

    first_position = None
    for row in tables.get("table1", []):
        mass, position = as_number(row.get("c0")), as_number(row.get("c1"))
        if first_position is None and position is not None:
            first_position = position
        row["c2"] = f"{position - first_position:.4f}" if position is not None and first_position is not None else ""
        row["c3"] = f"{mass * 9.8:.4f}" if mass is not None else ""
    for index, row in enumerate(tables.get("table2", [])):
        initial = as_number(row.get("c1"))
        readings = [as_number(row.get(f"c{column}")) for column in range(2, 7)]
        readings = [value for value in readings if value is not None]
        mean = sum(readings) / len(readings) if readings else None
        delta_force = stiffness * (mean - initial) * 10 if mean is not None and initial is not None else None
        tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
        row["c0"] = "自来水" if index == 0 else ("洗洁精溶液" if index == 1 else f"待测溶液{index + 1}")
        row["c7"] = f"{mean:.4f}" if mean is not None else ""
        row["c8"] = f"{delta_force:.4f}" if delta_force is not None else ""
        row["c9"] = f"{tension:.4f}" if tension is not None else ""
    for row in tables.get("table3", []):
        initial, mean = as_number(row.get("c1")), as_number(row.get("c2"))
        delta_force = stiffness * (mean - initial) * 10 if mean is not None and initial is not None else None
        tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
        row["c3"] = f"{tension:.4f}" if tension is not None else ""
    return {"tables": tables}


def _calculate_structured(data, constants=None):
    results = {"steps": {}, "final": {}}
    extension_values, forces = [], []
    for row in data.get("table1", []):
        if len(row) < 4:
            continue
        extension, force = as_number(row[2]), as_number(row[3])
        if extension is not None and force is not None:
            extension_values.append(extension / 100)
            forces.append(force / 1000)
    if len(forces) >= 2 and np.ptp(extension_values) != 0:
        slope, intercept = np.polyfit(np.asarray(extension_values), np.asarray(forces), 1)
        results["steps"]["弹簧定标截距"] = f"{intercept:.6f} N"
        results["final"]["弹簧劲度系数 k"] = f"{slope:.4f} N/m"
    else:
        results["final"]["弹簧劲度系数 k"] = "数据不足"

    for row in data.get("table2", []):
        if len(row) < 10:
            continue
        liquid, tension = row[0].strip() or "未知液体", as_number(row[9])
        if tension is not None:
            results["final"][f"{liquid}表面张力系数 σ"] = f"{tension:.4f} mN/m"
    concentration_count = sum(
        1 for row in data.get("table3", [])
        if len(row) >= 4 and as_number(row[0]) is not None and as_number(row[3]) is not None
    )
    if concentration_count:
        results["steps"]["浓度-表面张力数据点"] = f"{concentration_count} 个"
    return results


def handle_structured(workpath, payload):
    prepared = dict(payload)
    prepared["tables"] = preview(payload)["tables"]
    current_schema = schema()
    results = _calculate_structured(ordered_rows(current_schema, prepared), parameter_values(current_schema, prepared))
    summary, warnings = result_lines(results)
    return structured_result(workpath, display_name(), current_schema, prepared, summary=summary, warnings=warnings)
