"""切变模量实验模块（扭摆法）
=================================
本实验用扭摆法测量钢丝的切变模量，包含一张数据表与一组装置参数：

  表格1：钢丝直径重复测量表（8行）
    输入钢丝直径 d 的多次测量值，后端计算平均直径 d̄。
  参数：环内直径 D₁、环外直径 D₂、钢丝长度 L、圆环质量 m、
        空盘转动周期 T₀（累积时间与次数）、加环后周期 T₁（累积时间与次数）。

物理公式：
  T₀ = n₀T₀/n₀，T₁ = n₁T₁/n₁                     （由累积时间求周期）
  D = π² m(D₁² + D₂²) / [2(T₁² - T₀²)]           （扭转模量）
  G = 16π L m(D₁² + D₂²) / [d⁴(T₁² - T₀²)]       （切变模量）
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_chart_from_table, make_schema, make_table,
    structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory

def name(): # 返回实验名称
    return "切变模量"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["D","d1","d2","L","m","T0","n0","T1","n1"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["D","d1","d2","L","m","T0","n0","T1","n1"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        data["T0"]/=data["n0"][0]
        data["T1"]/=data["n1"][0]

        res_d=analyse(data["D"],0.01,0.005,"d","mm")
        res_d1=analyse(data["d1"],0.02,0,"d1","mm",3**0.5)
        res_d2=analyse(data["d2"],0.02,0,"d2","mm",3**0.5)
        res_L=analyse(data["L"],0.1,0.05,"L","cm")
        res_m=analyse(data["m"],1,0.5,"m","g")
        res_t0=analyse(data["T0"],0.0005,0.01,"T0","s")
        res_t1=analyse(data["T1"],0.0005,0.01,"T1","s")

        res_D=analyse_com("D=(pi**2*m*(d1**2+d2**2))/(2*(t1**2-t0**2))",(("m",res_m.average/1000,res_m.unc/1000),("d1",res_d1.average/1000,res_d1.unc/1000),("d2",res_d2.average/1000,res_d2.unc/1000),("t1",res_t1.average,res_t1.unc),("t0",res_t0.average,res_t0.unc)),(),"kg·m^2/s^2")
        res_G=analyse_com("G=(16*pi*L*m*(d1*d1+d2*d2))/((d**4)*(t1*t1-t0*t0))",(("L",res_L.average/100,res_L.unc/100),("m",res_m.average/1000,res_m.unc/1000),("d1",res_d1.average/1000,res_d1.unc/1000),("d2",res_d2.average/1000,res_d2.unc/1000),("d",res_d.average/1000,res_d.unc/1000),("t1",res_t1.average,res_t1.unc),("t0",res_t0.average,res_t0.unc)),(),"kg/(m·s^2)")

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        insert_data(docu, "钢丝直径d", res_d, "word")
        insert_data(docu, "环内直径d1", res_d1, "word")
        insert_data(docu, "环外直径d2", res_d2, "word")
        insert_data(docu, "钢丝长度L", res_L, "word")
        insert_data(docu, "圆环质量m", res_m, "word")
        insert_data(docu, "周期T0", res_t0, "word")
        insert_data(docu, "周期T1", res_t1, "word")

        docu.add_paragraph("扭转模量")
        docu.add_paragraph()._element.append(latex_to_word(res_D.ansx2))
        docu.add_paragraph("扭转模量D的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_D.uncx2))
        docu.add_paragraph("扭转模量最终结果")
        docu.add_paragraph()._element.append(latex_to_word(res_D.finalx2))
        docu.add_paragraph()

        docu.add_paragraph("切变模量")
        docu.add_paragraph()._element.append(latex_to_word(res_G.ansx2))
        docu.add_paragraph("切变模量G的延伸不确定度")
        docu.add_paragraph()._element.append(latex_to_word(res_G.uncx2))
        docu.add_paragraph("切变模量最终结果")
        docu.add_paragraph()._element.append(latex_to_word(res_G.finalx2))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        insert_data(docu, "钢丝直径d", res_d, "latex")
        insert_data(docu, "环内直径d1", res_d1, "latex")
        insert_data(docu, "环外直径d2", res_d2, "latex")
        insert_data(docu, "钢丝长度L", res_L, "latex")
        insert_data(docu, "圆环质量m", res_m, "latex")
        insert_data(docu, "周期T0", res_t0, "latex")
        insert_data(docu, "周期T1", res_t1, "latex")

        docu.add_paragraph("扭转模量")
        docu.add_paragraph(res_D.ansx)
        docu.add_paragraph("扭转模量D的延伸不确定度")
        docu.add_paragraph(res_D.uncx)
        docu.add_paragraph("扭转模量最终结果")
        docu.add_paragraph(res_D.finalx)
        docu.add_paragraph()

        docu.add_paragraph("切变模量")
        docu.add_paragraph(res_G.ansx)
        docu.add_paragraph("切变模量G的延伸不确定度")
        docu.add_paragraph(res_G.uncx)
        docu.add_paragraph("切变模量最终结果")
        docu.add_paragraph(res_G.finalx)
        docu.add_paragraph()

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
    table1 = _set_units(
        make_table(
            "table1", "钢丝直径重复测量表",
            ["序号", "钢丝直径 d(mm)"],
            sample=[
                [1, 0.780], [2, 0.781], [3, 0.781], [4, 0.781],
                [5, 0.780], [6, 0.781], [7, 0.778], [8, 0.779],
            ],
            readonly=(0,), min_rows=3, initial_rows=8,
            description="输入多次用螺旋测微器测得的钢丝直径，平均直径由后端自动计算。",
        ),
        ["", "mm"],
    )
    angle_chart = {
        "x_column": "c1", "y_column": "c8",
        "x_label": "初始扭转角 θ (°)", "y_label": "切变模量 G (GPa)",
        "title": "切变模量 G - 初始扭转角 θ 拟合曲线", "fit": "linear",
    }
    table2 = _set_units(
        make_table(
            "table2", "提升实验：切变模量与扭转角的关系",
            ["序号", "初始扭转角 θ(°)", "空盘累积时间 t₀(s)",
             "空盘次数 n₀", "加环累积时间 t₁(s)", "加环次数 n₁",
             "空盘周期 T₀(s)", "加环周期 T₁(s)", "切变模量 G(GPa)"],
            sample=[
                [1, 30, 49.28, 20, 78.43, 20, 2.4640, 3.9215, 78.72],
                [2, 45, 49.30, 20, 78.46, 20, 2.4650, 3.9230, 78.66],
                [3, 60, 49.31, 20, 78.48, 20, 2.4655, 3.9240, 78.62],
                [4, 75, 49.34, 20, 78.52, 20, 2.4670, 3.9260, 78.55],
                [5, 90, 49.38, 20, 78.58, 20, 2.4690, 3.9290, 78.47],
            ],
            readonly=(0, 6, 7, 8), min_rows=3, initial_rows=5, required=False,
            chart=angle_chart,
            description=("改变初始扭转角，分别测量空盘和加环后的累积周期；"
                         "T₀、T₁ 和 G 自动计算，并对 G-θ 作线性拟合。"),
        ),
        ["", "°", "s", "次", "s", "次", "s", "s", "GPa"],
    )
    return make_schema(
        (
            "本实验用扭摆法测量金属丝的切变模量。请记录钢丝直径、圆环内外径与质量、"
            "空盘与加环后的累积摆动时间，按 "
            r"$G=\frac{16\pi Lm(D_1^2+D_2^2)}{d^4(T_1^2-T_0^2)}$"
            " 计算切变模量，体会“避开难测物理量”的实验设计思想。"
        ),
        [table1, table2],
        parameters=[
            {"id": "d1", "label": "环内直径 D₁", "unit": "mm", "type": "number", "default": 84.08},
            {"id": "d2", "label": "环外直径 D₂", "unit": "mm", "type": "number", "default": 103.94},
            {"id": "L", "label": "钢丝有效长度 L", "unit": "cm", "type": "number", "default": 44.2},
            {"id": "m", "label": "圆环质量 m", "unit": "g", "type": "number", "default": 564.5},
            {"id": "t0", "label": "空盘累积时间 n₀T₀", "unit": "s", "type": "number", "default": 49.29},
            {"id": "n0", "label": "空盘摆动次数 n₀", "unit": "次", "type": "number", "default": 20},
            {"id": "t1", "label": "加环累积时间 n₁T₁", "unit": "s", "type": "number", "default": 78.45},
            {"id": "n1", "label": "加环摆动次数 n₁", "unit": "次", "type": "number", "default": 20},
            {"id": "G_ref", "label": "钢材切变模量参考值 G_ref", "unit": "GPa", "type": "number", "default": 79.0},
        ],
        analysis_hints=("检查钢丝直径的重复性、G 的相对误差，以及提升实验中 "
                        "G-θ 拟合斜率是否接近 0。"),
        preview_enabled=True,
        formulas=get_formulas("exp6"),
        variables=get_variables("exp6"),
        table_theory=get_table_theory("exp6"),
    )


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def preview(payload):
    """补全序号列，并计算提升实验的周期和切变模量。"""
    tables = copied_tables(payload)
    for index, row in enumerate(tables.get("table1", [])):
        row["c0"] = index + 1
    parameters = payload.get("parameters") or {}
    d_values = [as_number(r.get("c1")) for r in tables.get("table1", [])]
    d_mm = _mean(d_values)
    d1_mm = as_number(parameters.get("d1", 84.08))
    d2_mm = as_number(parameters.get("d2", 103.94))
    L_cm = as_number(parameters.get("L", 44.2))
    m_g = as_number(parameters.get("m", 564.5))
    geometry = (d_mm, d1_mm, d2_mm, L_cm, m_g)
    for index, row in enumerate(tables.get("table2", [])):
        row["c0"] = index + 1
        t0, n0, t1, n1 = (as_number(row.get(key)) for key in ("c2", "c3", "c4", "c5"))
        T0 = t0 / n0 if t0 is not None and n0 else None
        T1 = t1 / n1 if t1 is not None and n1 else None
        row["c6"] = formatted(T0, 5)
        row["c7"] = formatted(T1, 5)
        G = _calculate_g(*geometry, T0, T1)
        row["c8"] = formatted(G / 1e9 if G is not None else None, 5)
    return {"tables": tables}


def _calculate_g(d_mm, d1_mm, d2_mm, L_cm, m_g, T0, T1):
    if any(value is None for value in (d_mm, d1_mm, d2_mm, L_cm, m_g, T0, T1)):
        return None
    denom = T1 ** 2 - T0 ** 2
    if d_mm <= 0 or denom <= 0:
        return None
    return (16 * np.pi * (L_cm / 100) * (m_g / 1000)
            * ((d1_mm / 1000) ** 2 + (d2_mm / 1000) ** 2)
            / ((d_mm / 1000) ** 4 * denom))


def handle_structured(workpath, payload):
    """完成最终计算并生成处理结果。"""
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]

    parameters = payload.get("parameters") or {}
    d1_mm = as_number(parameters.get("d1")) or 84.08
    d2_mm = as_number(parameters.get("d2")) or 103.94
    L_cm = as_number(parameters.get("L")) or 44.2
    m_g = as_number(parameters.get("m")) or 564.5
    t0_accum = as_number(parameters.get("t0")) or 49.29
    n0 = as_number(parameters.get("n0")) or 20
    t1_accum = as_number(parameters.get("t1")) or 78.45
    n1 = as_number(parameters.get("n1")) or 20
    G_ref_gpa = as_number(parameters.get("G_ref"))

    d_mm = _mean(
        [as_number(r.get("c1")) for r in (enriched["tables"].get("table1", []) or [])]
    )

    summary = []
    if d_mm is not None and n0 and n1:
        d_m = d_mm / 1000.0
        d1_m, d2_m = d1_mm / 1000.0, d2_mm / 1000.0
        L_m, m_kg = L_cm / 100.0, m_g / 1000.0
        T0 = t0_accum / n0
        T1 = t1_accum / n1
        denom = T1 ** 2 - T0 ** 2
        if denom > 0 and d_mm > 0:
            D_mod = (np.pi ** 2 * m_kg * (d1_m ** 2 + d2_m ** 2)) / (2 * denom)
            G_mod = (16 * np.pi * L_m * m_kg * (d1_m ** 2 + d2_m ** 2)) / (d_m ** 4 * denom)
            summary.append(f"钢丝平均直径 d̄ = {d_mm:.4f} mm")
            summary.append(f"空盘周期 T₀ = {T0:.5f} s，加环周期 T₁ = {T1:.5f} s")
            summary.append(f"扭转模量 D = {D_mod:.5f} kg·m²/s²")
            summary.append(f"切变模量 G = {G_mod:.5f} kg/(m·s²)")
            if G_ref_gpa is not None and G_ref_gpa > 0:
                relative_error = abs(G_mod / 1e9 - G_ref_gpa) / G_ref_gpa * 100
                summary.append(
                    f"与参考值 G_ref = {G_ref_gpa:.4f} GPa 比较，"
                    f"相对误差 E_r = |G-G_ref|/G_ref×100% = {relative_error:.3f}%"
                )
        else:
            summary.append("T₁² - T₀² 必须大于零且钢丝直径必须为正，请检查输入。")
    else:
        summary.append("数据不足，无法完成切变模量计算，请检查钢丝直径与摆动参数。")

    charts = []
    angle_rows = enriched["tables"].get("table2", []) or []
    valid_angle_rows = [r for r in angle_rows
                        if as_number(r.get("c1")) is not None and as_number(r.get("c8")) is not None]
    if len(valid_angle_rows) >= 2:
        table2_schema = next(t for t in schema()["tables"] if t["id"] == "table2")
        chart = make_chart_from_table(
            table2_schema, valid_angle_rows, table2_schema["chart"], workpath,
            "shear_modulus_vs_angle.png",
        )
        charts.append(chart)
        fit = chart.get("fit_result") or {}
        if fit:
            summary.append(
                "提升实验 G-θ 线性拟合：{}，R² = {}"
                .format(fit.get("equation", ""), fit.get("R2", ""))
            )

    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary, charts=charts,
    )
