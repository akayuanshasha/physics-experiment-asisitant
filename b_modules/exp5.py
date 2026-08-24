"""杨氏模量实验模块（光杠杆法）
==========================================
本实验包含三组数据表：

  表格1：钢丝直径 d 的多次测量（5次，求平均）
  表格2：光杠杆拉伸形变数据（7行，加减砝码读数）
    → 计算 b̄ = (b₊+b₋)/2，Δb = b̄ - b̄₀
  图表1：b - F 线性拟合图 → 由斜率 M 计算 E

物理公式：
  E = 8DL / (π d̄² l M)
  其中 D 为镜尺距，L 为钢丝原长，l 为光杠杆臂长，
  M 为 b-F 拟合斜率。
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data

def name(): # 返回实验名称
    return "用拉伸法测量钢丝的杨氏模量"

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
    _raw = load_sample_data("exp5", "用拉伸法测量钢丝的杨氏模量")
    # CSV 列: D/cm, l/cm, L/cm, d/mm, 砝码个数, b1, b2
    # 提取参数和砝码数据
    D_val, l_val, L_val = None, None, None
    diameters = []
    masses = []
    b_readings = []
    for row in _raw:
        if len(row) >= 7:
            try:
                if row[0].strip():
                    D_val = float(row[0])
                if row[1].strip():
                    l_val = float(row[1])
                if row[2].strip():
                    L_val = float(row[2])
                if row[3].strip():
                    diameters.append(float(row[3]))
                mass_idx = int(float(row[4])) if row[4].strip() else None
                b1 = float(row[5]) if row[5].strip() else None
                b2 = float(row[6]) if row[6].strip() else None
                if mass_idx is not None and b1 is not None and b2 is not None:
                    masses.append(mass_idx)
                    b_readings.append([b1, b2])
            except (ValueError, IndexError):
                pass
    # 表格1：钢丝直径
    sample1 = [[d] for d in diameters[:5]]
    # 表格2：光杠杆数据
    sample2 = []
    for m, br in zip(masses[:7], b_readings[:7]):
        sample2.append([br[0], br[1]])  # b₊, b₋
    chart = {
        "x_column": "c0", "y_column": "c2",
        "x_label": "序号", "y_label": "标尺读数 b̄ (cm)",
        "title": "b̄-序号 关系图", "fit": "linear",
    }
    return make_schema(
        "杨氏模量（3数据表 + 1拟合图）",
        [
            make_table(
                "table1", "钢丝直径测量表",
                ["d_i(mm)"],
                sample=sample1, initial_rows=5,
            ),
            make_table(
                "table2", "光杠杆拉伸形变数据表",
                ["b₊(cm)", "b₋(cm)",
                 "b̄(cm)", "Δb(cm)"],
                sample=sample2, readonly=(2, 3), initial_rows=7, chart=chart,
            ),
        ],
        parameters=[
            {"id": "D", "label": "镜尺距 D", "unit": "cm", "type": "number", "default": D_val or 128.0},
            {"id": "l", "label": "光杠杆臂长 l", "unit": "cm", "type": "number", "default": l_val or 7.2},
            {"id": "L", "label": "钢丝原长 L", "unit": "cm", "type": "number", "default": L_val or 100.5},
        ],
        analysis_hints="检查钢丝直径的重复性、光杠杆数据的线性度，以及杨氏模量的合理性。",
        preview_enabled=True,
        table_theory=get_table_theory("exp5"),)


def preview(payload):
    """补全光杠杆平均值 b̄ 和位移 Δb。"""
    tables = copied_tables(payload)
    rows = tables.get("table2", [])
    first_average = None
    for index, row in enumerate(rows):
        plus, minus = as_number(row.get("c0")), as_number(row.get("c1"))
        average = (plus + minus) / 2 if plus is not None and minus is not None else None
        if index == 0:
            first_average = average
        row["c2"] = formatted(average, 3)
        row["c3"] = formatted(average - first_average if average is not None and first_average is not None else None, 3)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["钢丝直径、光杠杆数据已处理，b̄ 和 Δb 已由后端计算。"],
    )
