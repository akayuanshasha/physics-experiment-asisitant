from head import * # 导入万能头
import numpy as np
from structured_support import (
    as_number, copied_tables, make_schema, make_table, ordered_rows,
    parameter_values, result_lines, structured_result,
)

def name(): # 返回实验名称
    return "单摆法测重力加速度"


def display_name():
    return "单摆法测重力加速度B（实验指导）"

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
    return make_schema(
        "通过重复测量和多摆长线性拟合两种方法测量重力加速度。",
        [
            make_table(
                "table1", "单摆重复测量及不确定度计算表",
                ["序号", "摆线长 x(cm)", "摆球直径 d(mm)", "实际摆长 l(cm)", "累积时间 t(s)", "周期 T(s)"],
                readonly=(0, 3, 5),
                sample=[
                    [1, 80.00, 22.00, "", 90.15, ""], [2, 80.00, 22.02, "", 90.18, ""],
                    [3, 80.00, 22.01, "", 90.22, ""], [4, 80.00, 22.00, "", 90.20, ""],
                    [5, 80.00, 22.03, "", 90.17, ""], [6, 80.00, 22.01, "", 90.21, ""],
                ],
            ),
            make_table(
                "table2", "不同摆长与周期平方计算表",
                ["序号", "摆长 l(cm)", "累积时间 t(s)", "周期 T(s)", "周期平方 T²(s²)"],
                readonly=(0, 3, 4),
                sample=[
                    [1, 60, 77.80, "", ""], [2, 70, 84.10, "", ""], [3, 80, 89.95, "", ""],
                    [4, 90, 95.42, "", ""], [5, 100, 100.62, "", ""], [6, 110, 105.58, "", ""],
                ],
                chart={
                    "x_column": "c4", "y_column": "c1", "x_label": "T² (s²)",
                    "y_label": "摆长 l (cm)", "title": "摆长 l 与周期平方 T² 的线性关系",
                    "fit": "linear",
                },
            ),
        ],
        analysis_hints="重点检查重复测量离散性、l-T²线性关系及由斜率得到的重力加速度。",
        preview_enabled=True,
        revision=4,
    )


def preview(payload):
    tables = copied_tables(payload)
    for index, row in enumerate(tables.get("table1", [])):
        line_length = as_number(row.get("c1"))
        diameter = as_number(row.get("c2"))
        elapsed = as_number(row.get("c4"))
        row["c0"] = index + 1
        row["c3"] = f"{line_length + diameter / 20:.4f}" if line_length is not None and diameter is not None else ""
        row["c5"] = f"{elapsed / 50:.5f}" if elapsed is not None else ""
    for index, row in enumerate(tables.get("table2", [])):
        elapsed = as_number(row.get("c2"))
        period = elapsed / 50 if elapsed is not None else None
        row["c0"] = index + 1
        row["c3"] = f"{period:.5f}" if period is not None else ""
        row["c4"] = f"{period * period:.6f}" if period is not None else ""
    return {"tables": tables}


def _calculate_structured(data, constants=None):
    results = {"steps": {}, "final": {}}
    lengths, periods = [], []
    for row in data.get("table1", []):
        if len(row) < 6:
            continue
        length, period = as_number(row[3]), as_number(row[5])
        if length is not None and period is not None:
            lengths.append(length)
            periods.append(period)

    if len(lengths) < 2:
        results["final"]["平均值法"] = "数据不足，无法计算"
    else:
        length_values = np.asarray(lengths, dtype=float)
        period_values = np.asarray(periods, dtype=float)
        length_mean = float(np.mean(length_values))
        period_mean = float(np.mean(period_values))
        length_std = float(np.std(length_values, ddof=1))
        period_std = float(np.std(period_values, ddof=1))
        gravity = 4 * np.pi ** 2 * (length_mean / 100) / period_mean ** 2
        u_length = np.sqrt((length_std / np.sqrt(len(length_values))) ** 2 + 0.05 ** 2)
        u_period = np.sqrt((period_std / np.sqrt(len(period_values))) ** 2 + 0.002 ** 2)
        relative = np.sqrt((u_length / length_mean) ** 2 + (2 * u_period / period_mean) ** 2)
        results["steps"].update({
            "摆长均值 l̄": f"{length_mean:.4f} cm", "周期均值 T̄": f"{period_mean:.4f} s",
            "摆长不确定度 u_l": f"{u_length:.4f} cm", "周期不确定度 u_T": f"{u_period:.4f} s",
        })
        results["final"].update({
            "重力加速度 g": f"{gravity:.4f} m/s²",
            "g 的标准不确定度 u_g": f"{gravity * relative:.4f} m/s²",
            "g 的相对不确定度 u_r(g)": f"{relative * 100:.2f}%",
        })

    fit_lengths, squared_periods = [], []
    for row in data.get("table2", []):
        if len(row) < 5:
            continue
        length, squared_period = as_number(row[1]), as_number(row[4])
        if length is not None and squared_period is not None:
            fit_lengths.append(length / 100)
            squared_periods.append(squared_period)
    if len(fit_lengths) < 2 or np.ptp(squared_periods) == 0:
        results["final"]["拟合斜率法"] = "数据不足，无法计算"
    else:
        slope, intercept = np.polyfit(np.asarray(squared_periods), np.asarray(fit_lengths), 1)
        predicted = slope * np.asarray(squared_periods) + intercept
        residual = float(np.sum((np.asarray(fit_lengths) - predicted) ** 2))
        total = float(np.sum((np.asarray(fit_lengths) - np.mean(fit_lengths)) ** 2))
        r_squared = 1 - residual / total if total else 0
        results["steps"]["l-T² 拟合斜率 k"] = f"{slope:.4f} m/s²"
        results["steps"]["拟合优度 R²"] = f"{r_squared:.6f}"
        results["final"]["拟合斜率法重力加速度 g"] = f"{4 * np.pi ** 2 * slope:.4f} m/s²"
    return results


def handle_structured(workpath, payload):
    prepared = dict(payload)
    prepared["tables"] = preview(payload)["tables"]
    results = _calculate_structured(ordered_rows(schema(), prepared), parameter_values(schema(), prepared))
    summary, warnings = result_lines(results)
    return structured_result(workpath, display_name(), schema(), prepared, summary=summary, warnings=warnings)
