"""表面张力实验模块
==============================
本实验包含三部分，共三组数据表 + 两个图表：

第一部分：弹簧劲度系数定标
  表格1：弹簧伸长量与拉力计算表（10行）
    → 计算 Δx = x - x₀，F = m·g
  图表1：F - Δx 线性拟合图 → 由斜率计算弹簧劲度系数 k

第二部分：自来水与洗洁精表面张力测定
  参数输入：金属圈两脚间距 d，劲度系数 k
  表格2：液膜破裂读数及表面张力计算表（2行）
    → 计算 l̄、ΔF、σ

第三部分：不同浓度洗洁精溶液表面张力测定
  表格3：不同浓度表面张力计算表（默认3行）
    → 计算 σ = k(l̄ - l₀) / (2d)
  图表2：σ - C 浓度关系曲线图

物理公式：
  F = m·g                            （拉力）
  Δx = x - x₀                        （伸长量）
  k = ΔF/Δx                          （劲度系数，由拟合斜率得到）
  σ = k·(l̄ - l₀) / (2d)             （表面张力系数）
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory

def name(): # 返回实验名称
    return "表面张力（测量弹簧劲度系数）"

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
        style_doc_font(docu)

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


def _set_units(table, units):
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema():
    chart1 = {
        "x_column": "c2", "y_column": "c3",
        "x_label": "伸长量 Δx (cm)", "y_label": "拉力 F (mN)",
        "title": "弹簧定标 F-Δx", "fit": "linear",
    }
    chart3 = {
        "x_column": "c0", "y_column": "c3",
        "x_label": "浓度 C (%)", "y_label": "表面张力 σ (mN/m)",
        "title": "σ-C 浓度关系", "fit": "auto",
    }
    # 表格1：弹簧定标（示例数据取自 exp2 示例 CSV）
    table1 = _set_units(
        make_table(
            "table1", "弹簧伸长量与拉力计算表",
            ["砝码质量 m(g)", "升降杆读数 x(cm)",
             "伸长量 Δx(cm)", "拉力 F(mN)"],
            sample=[
                [0.0, 1.00, "", ""], [0.5, 1.43, "", ""],
                [1.0, 1.83, "", ""], [1.5, 2.25, "", ""],
                [2.0, 2.82, "", ""], [2.5, 3.16, "", ""],
                [3.0, 3.55, "", ""], [3.5, 3.99, "", ""],
                [4.0, 4.36, "", ""], [4.5, 4.75, "", ""],
                [5.0, 5.19, "", ""],
            ],
            readonly=(2, 3), min_rows=3, initial_rows=11, chart=chart1,
            description="输入砝码质量与升降杆读数，伸长量与拉力由后端自动计算。",
        ),
        ["g", "cm", "cm", "mN"],
    )
    # 表格2：液膜破裂读数（示例数据取自 exp2 示例 CSV）
    table2 = _set_units(
        make_table(
            "table2", "液膜破裂读数及表面张力计算表",
            ["液体类别", "初始读数 l₀(cm)",
             "破裂读数1 l₁(cm)", "破裂读数2 l₂(cm)", "破裂读数3 l₃(cm)",
             "破裂读数4 l₄(cm)", "破裂读数5 l₅(cm)",
             "破裂均值 l̄(cm)", "拉力差 ΔF(mN)", "表面张力 σ(mN/m)"],
            sample=[
                ["自来水", 1.04, 1.28, 1.29, 1.24, 1.31, 1.28, "", "", ""],
                ["洗洁精溶液", 1.04, 1.30, 1.31, 1.29, 1.30, 1.30, "", "", ""],
            ],
            readonly=(7, 8, 9), min_rows=2, initial_rows=2, text_columns=(0,),
            description="输入初始读数 l₀ 与 5 次破裂读数，破裂均值、拉力差与表面张力由后端自动计算。",
        ),
        ["", "cm", "cm", "cm", "cm", "cm", "cm", "cm", "mN", "mN/m"],
    )
    # 表格3：不同浓度表面张力（示例数据为自配 3 个浓度）
    table3 = _set_units(
        make_table(
            "table3", "不同浓度洗洁精表面张力计算表",
            ["浓度 C(%)", "初始读数 l₀(cm)",
             "破裂均值 l̄(cm)", "表面张力 σ(mN/m)"],
            sample=[
                [0.5, 1.04, 1.30, ""],
                [1.0, 1.04, 1.36, ""],
                [2.0, 1.04, 1.45, ""],
            ],
            readonly=(3,), min_rows=2, initial_rows=3, chart=chart3,
            description="输入不同浓度的初始读数与破裂均值，表面张力由后端自动计算。",
        ),
        ["%", "cm", "cm", "mN/m"],
    )
    return make_schema(
        (
            "本实验用拉脱法测量液体表面张力系数。先用砝码对弹簧测力计定标，再记录液膜破裂瞬间读数"
            "（各 5 次）；按 " r"$\alpha = mg/[\pi(D_1+D_2)]$" " 计算表面张力系数，"
            "并测量不同浓度洗洁精的表面张力系数，用图解法处理数据。"
        ),
        [table1, table2, table3],
        parameters=[
            {"id": "k", "label": "弹簧劲度系数 k", "unit": "N/m", "type": "number", "default": 0.5},
            {"id": "d", "label": "金属圈两脚间距 d", "unit": "cm", "type": "number", "default": 3.0},
        ],
        analysis_hints="检查弹簧定标的线性度、表面张力值的合理性，以及浓度对表面张力的影响趋势。",
        preview_enabled=True,
        formulas=get_formulas("exp2"),
        variables=get_variables("exp2"),
        table_theory=get_table_theory("exp2"),
    )


def preview(payload):
    """补全弹簧定标与表面张力计算列。"""
    parameters = payload.get("parameters") or {}
    k = as_number(parameters.get("k")) or 0.5
    distance = as_number(parameters.get("d")) or 3.0
    tables = copied_tables(payload)
    # 表格1：弹簧定标
    first_x = None
    for row in tables.get("table1", []):
        mass, x = as_number(row.get("c0")), as_number(row.get("c1"))
        if first_x is None and x is not None:
            first_x = x
        row["c2"] = formatted(x - first_x if x is not None and first_x is not None else None, 4)
        row["c3"] = formatted(mass * 9.8 if mass is not None else None, 4)
    # 表格2：表面张力
    for index, row in enumerate(tables.get("table2", [])):
        initial = as_number(row.get("c1"))
        readings = [as_number(row.get(f"c{i}")) for i in range(2, 7)]
        readings = [v for v in readings if v is not None]
        mean = sum(readings) / len(readings) if readings else None
        delta_force = k * (mean - initial) * 10 if mean is not None and initial is not None else None
        tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
        labels = ["自来水", "洗洁精溶液"]
        row["c0"] = labels[index] if index < len(labels) else f"待测溶液{index + 1}"
        row["c7"] = formatted(mean, 4)
        row["c8"] = formatted(delta_force, 4)
        row["c9"] = formatted(tension, 4)
    # 表格3：浓度关系
    for row in tables.get("table3", []):
        initial, mean = as_number(row.get("c1")), as_number(row.get("c2"))
        delta_force = k * (mean - initial) * 10 if mean is not None and initial is not None else None
        tension = delta_force / (2 * distance * 0.01) if delta_force is not None and distance else None
        row["c3"] = formatted(tension, 4)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["弹簧定标、表面张力及浓度关系数据已处理，派生量已由后端计算。"],
    )
