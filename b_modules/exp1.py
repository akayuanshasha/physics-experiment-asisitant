"""单摆法测重力加速度实验模块
==============================
本实验包含两部分，共两组数据表：

第一部分：基础内容（重复测量与不确定度计算）
  表格1：单摆重复测量表（6行）
    → 计算摆长均值 l̄、周期均值 T̄、重力加速度 g 及不确定度

第二部分：提升内容（多摆长拟合求 g）
  表格2：不同摆长与周期平方计算表（6行）
  图表1：l - T² 线性拟合图 → 由斜率 k 计算 g = 4π²k

物理公式：
  g = 4π² l̄ / T̄²                    （平均值法）
  g = 4π² · k                        （拟合斜率法，k = Δl/ΔT²）
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data

def name(): # 返回实验名称
    return "单摆法测重力加速度"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["l","d","T","n"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["l","d","T","n"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        data["T"]/=data["n"][0] # Pandas Series支持整体运算，相当于数组中的每个元素都做同样的操作

        res_l=analyse(data["l"],0.2,0.05,'l','cm') # 摆线长度的相关值计算
        res_d=analyse(data["d"],0.02,0,'d','mm',confidence_C=3**0.5) # 摆球直径的相关值计算
        res_T=analyse(data["T"],0.01/data["n"][0],0.2/data["n"][0],'T','s') # 周期的相关值计算

        res_L=analyse_com("L=l+d",(("l",res_l.average,res_l.unc),("d",res_d.average/20,res_d.unc/20)),(),"cm")
        res_g=analyse_com("g=4*pi**2*L/T**2",(("L",res_L.ans/100,res_L.unc/100),("T",res_T.average,res_T.unc)),(),"m/s^2")
    
        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("钢卷尺的最大允差为0.2cm，游标卡尺的最大允差为0.002cm，秒表的最大允差为0.01s")
        docu.add_paragraph("钢卷尺和游标卡尺的估计误差为最小分度值的一半，分别为0.05cm和0.001cm")
        docu.add_paragraph("秒表的估计误差为0.2s")
        docu.add_paragraph()

        insert_data(docu, "摆线长度l", res_l, "word")
        insert_data(docu, "摆球直径d", res_d, "word")

        docu.add_paragraph("摆长L")
        docu.add_paragraph()._element.append(latex_to_word(res_L.ansx2))
        docu.add_paragraph("摆长L的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_L.uncx2))

        insert_data(docu, "周期T", res_T, "word")

        docu.add_paragraph("重力加速度g")
        docu.add_paragraph()._element.append(latex_to_word(res_g.ansx2))
        docu.add_paragraph("重力加速度g的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_g.uncx2))
        docu.add_paragraph("重力加速度g最终结果")
        docu.add_paragraph()._element.append(latex_to_word(res_g.finalx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        
        insert_data(docu, "摆线长度l", res_l, "latex")
        insert_data(docu, "摆球直径d", res_d, "latex")

        docu.add_paragraph("摆长L")
        docu.add_paragraph(res_L.ansx)
        docu.add_paragraph("摆长L的延伸不确定度")
        docu.add_paragraph(res_L.uncx)

        insert_data(docu, "周期T", res_T, "latex")

        docu.add_paragraph("重力加速度g")
        docu.add_paragraph(res_g.ansx)
        docu.add_paragraph("重力加速度g的延伸不确定度")
        docu.add_paragraph(res_g.uncx)
        docu.add_paragraph("重力加速度g最终结果")
        docu.add_paragraph(res_g.finalx)

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1


def schema():
    _raw = load_sample_data("exp1", "单摆法测重力加速度")
    # CSV 列: l/cm, d/mm, nT/s, n → 转换为表格列: 序号, 摆线长, 摆球直径, 实际摆长, 累积时间, 周期
    sample = []
    for idx, row in enumerate(_raw):
        if len(row) >= 4:
            try:
                l_val = float(row[0])
                d_val = float(row[1])
                nt_val = float(row[2])
                n_val = float(row[3])
                period = nt_val / n_val if n_val != 0 else 0
                sample.append([idx + 1, l_val, d_val, l_val + d_val / 20, nt_val, period])
            except (ValueError, IndexError):
                pass
    chart = {
        "x_column": "c5", "y_column": "c3",
        "x_label": "周期平方 T² (s²)", "y_label": "摆长 l (cm)",
        "title": "l - T² 线性拟合", "fit": "linear",
    }
    return make_schema(
        "单摆法测重力加速度（2数据表 + 1拟合图）",
        [
            make_table(
                "table1", "单摆重复测量及不确定度计算表",
                ["序号", "摆线长 x(cm)", "摆球直径 d(mm)",
                 "实际摆长 l(cm)", "累积时间 t(s)", "周期 T(s)"],
                sample=sample, readonly=(0, 3, 5), initial_rows=6,
            ),
            make_table(
                "table2", "不同摆长与周期平方计算表",
                ["序号", "摆长 l(cm)", "累积时间 t(s)",
                 "周期 T(s)", "周期平方 T²(s²)"],
                sample=(), readonly=(0, 3, 4), initial_rows=6, chart=chart,
            ),
        ],
        analysis_hints="检查摆长和周期的测量不确定度，以及 l-T² 拟合的线性度。",
        preview_enabled=True,
    
        table_theory=get_table_theory("exp1"),)


def preview(payload):
    """补全序号、实际摆长、周期及周期平方。"""
    tables = copied_tables(payload)
    for index, row in enumerate(tables.get("table1", [])):
        x, diameter, elapsed = (as_number(row.get(key)) for key in ("c1", "c2", "c4"))
        row["c0"] = index + 1
        row["c3"] = formatted(x + diameter / 20 if x is not None and diameter is not None else None, 4)
        row["c5"] = formatted(elapsed / 50 if elapsed is not None else None, 5)
    for index, row in enumerate(tables.get("table2", [])):
        elapsed = as_number(row.get("c2"))
        period = elapsed / 50 if elapsed is not None else None
        row["c0"] = index + 1
        row["c3"] = formatted(period, 5)
        row["c4"] = formatted(period * period if period is not None else None, 6)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["单摆重复测量数据及多摆长拟合数据已处理，序号和派生量已由后端计算。"],
    )
