"""落球法测定液体的粘度实验模块
=================================
本实验用斯托克斯公式测量蓖麻油的粘度，包含一张数据表：

  表格1：落球法测量数据表（6行）
    → 输入液面高度 h、匀速下降区 l、量筒直径 D、小球直径 d、下落时间 t
    → 计算小球匀速下落速度 v = l/t

参数：小球密度 ρ、液体密度 ρ₀、重力加速度 g。

物理公式：
  v = l / t                                        （匀速下落速度）
  η₀ = (1/18)(ρ - ρ₀) g d² / [v(1 + 2.4d/D)(1 + 3.3·(d/2)/h)]   （零级近似）
  Re = v ρ₀ d / η₀                                 （雷诺数）
  一级修正：η₁ = η₀ - (3/16) d v ρ₀                （0.1 < Re < 0.5）
  二级修正：η₂ = ½η₁[1 + √(1 + 19d²vρ₀/(270η₁²))]   （Re > 0.5）
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory

def name(): # 返回实验名称
    return "落球法测定液体的粘度"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["rho","rho0","g","h","l","D","d","t"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["rho","rho0","g","h","l","D","d","t"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        rho=data["rho"][0]*1000
        rho0=data["rho0"][0]*1000
        g=data["g"][0]
        p=0.95

        res_h=analyse(data["h"],0.02,0.05,'h','cm')
        res_l=analyse(data["l"],0.02,0.05,'l','cm')
        res_D=analyse(data["D"],0.02,0,'D','mm',confidence_C=3**0.5)
        res_d=analyse(data["d"],0.02,0,'d','mm',confidence_C=3**0.5)
        res_t=analyse(data["t"],0.01,0.2,'t','s')

        res_v=analyse_com("v=l/t",(),(("l",res_l.average/100),("t",res_t.average)),"m/s")
        v=res_v.ans

        d=res_d.average/1000
        D=res_D.average/1000
        h=res_h.average/100

        res_eta0=analyse_com("eta0=1/18*(rho-rho0)*g*d**2/(v*(1+2.4*d/D)*(1+3.3*d/2/h))",(),(("rho",rho),("rho0",rho0),("g",g),("d",d),("v",v),("D",D),("h",h)),"Pa·s")
        eta0=res_eta0.ans

        res_Re=analyse_com("Re=v*rho0*d/eta0",(),(("v",v),("rho0",rho0),("d",d),("eta0",eta0)),"")
        Re=res_Re.ans

        res_eta1=analyse_com("eta1=eta0-3/16*d*v*rho0",(),(("eta0",eta0),("d",d),("v",v),("rho0",rho0)),"Pa·s")
        eta1=res_eta1.ans

        res_eta2=analyse_com("eta2=1/2*eta1*(1+sqrt(1+19/270*(d*v*rho0/eta1)**2))",(),(("eta1",eta1),("d",d),("v",v),("rho0",rho0),("eta1",eta1)),"Pa·s")
        eta2=res_eta2.ans

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        insert_data(docu, "液面高度h", res_h, "word")
        insert_data(docu, "匀速下降区l", res_l, "word")
        insert_data(docu, "量筒直径D", res_D, "word")
        insert_data(docu, "小球直径d", res_d, "word")
        insert_data(docu, "下落时间t", res_t, "word")

        docu.add_paragraph("小球下落速度")
        docu.add_paragraph()._element.append(latex_to_word(res_v.ansx2))
        docu.add_paragraph("粘度的零级近似值")
        docu.add_paragraph()._element.append(latex_to_word(res_eta0.ansx2))
        docu.add_paragraph("雷诺数")
        docu.add_paragraph()._element.append(latex_to_word(res_Re.ansx2))

        if Re<0.1:
            docu.add_paragraph("Re<0.1，无需修正")
            docu.add_paragraph("粘度 η=η0="+('%.5g'%eta0)+" Pa·s")
        else:
            if Re<0.5:
                docu.add_paragraph("0.1<Re<0.5，进行一级修正：")
                docu.add_paragraph("粘度")
                docu.add_paragraph()._element.append(latex_to_word(res_eta1.ansx2))
            else:
                docu.add_paragraph("Re>0.5，进行二级修正：")
                docu.add_paragraph()._element.append(latex_to_word(res_eta1.ansx2))
                docu.add_paragraph("粘度")
                docu.add_paragraph()._element.append(latex_to_word(res_eta2.ansx2))

        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")

        insert_data(docu, "液面高度h", res_h, "latex")
        insert_data(docu, "匀速下降区l", res_l, "latex")
        insert_data(docu, "量筒直径D", res_D, "latex")
        insert_data(docu, "小球直径d", res_d, "latex")
        insert_data(docu, "下落时间t", res_t, "latex")

        docu.add_paragraph("小球下落速度")
        docu.add_paragraph(res_v.ansx)
        docu.add_paragraph("粘度的零级近似值")
        docu.add_paragraph(res_eta0.ansx)
        docu.add_paragraph("雷诺数")
        docu.add_paragraph(res_Re.ansx)

        if Re<0.1:
            docu.add_paragraph("Re<0.1，无需修正")
            docu.add_paragraph("粘度 η=η0="+('%.5g'%eta0)+" Pa·s")
        else:
            if Re<0.5:
                docu.add_paragraph("0.1<Re<0.5，进行一级修正：")
                docu.add_paragraph("粘度")
                docu.add_paragraph(res_eta1.ansx)
            else:
                docu.add_paragraph("Re>0.5，进行二级修正：")
                docu.add_paragraph(res_eta1.ansx)
                docu.add_paragraph("粘度")
                docu.add_paragraph(res_eta2.ansx)

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
            "table1", "落球法测量数据表",
            ["序号", "液面高度 h(cm)", "匀速下降区 l(cm)",
             "量筒直径 D(mm)", "小球直径 d(mm)", "下落时间 t(s)",
             "速度 v(m/s)"],
            sample=[
                [1, 30.92, 20.02, 89.20, 2.372, 6.22, ""],
                [2, 30.90, 19.98, 89.24, 2.377, 6.24, ""],
                [3, 30.93, 19.99, 89.22, 2.373, 6.20, ""],
                [4, "", "", "", 2.376, 6.33, ""],
                [5, "", "", "", 2.375, 6.28, ""],
                [6, "", "", "", 2.372, 6.32, ""],
            ],
            readonly=(0, 6), min_rows=3, initial_rows=6,
            description="输入液面高度、匀速下降区、量筒直径、小球直径与下落时间，速度由后端自动计算。",
        ),
        ["", "cm", "cm", "mm", "mm", "s", "m/s"],
    )
    return make_schema(
        (
            "本实验用落球法测量液体的粘滞系数。请记录液面高度、匀速下降区长度、量筒直径、"
            "小球直径与下落时间，按斯托克斯公式 " r"$\eta = \frac{2r^2(\rho-\rho_0)g}{9v}$"
            " 计算粘滞系数。注意小球需沿量筒中心轴线释放。"
        ),
        [table1],
        parameters=[
            {"id": "rho", "label": "小球密度 ρ", "unit": "g/cm³", "type": "number", "default": 7.859},
            {"id": "rho0", "label": "液体密度 ρ₀", "unit": "g/cm³", "type": "number", "default": 0.9552},
            {"id": "g", "label": "重力加速度 g", "unit": "m/s²", "type": "number", "default": 9.7947},
        ],
        analysis_hints="检查小球直径与下落时间的重复性，并由雷诺数选择粘度修正等级。",
        preview_enabled=True,
        formulas=get_formulas("exp3"),
        variables=get_variables("exp3"),
        table_theory=get_table_theory("exp3"),
        report_enabled=False,
    )


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def preview(payload):
    """补全序号与每行的小球下落速度 v = l/t。"""
    tables = copied_tables(payload)
    for index, row in enumerate(tables.get("table1", [])):
        row["c0"] = index + 1
        length = as_number(row.get("c2"))   # l/cm
        time_value = as_number(row.get("c5"))  # t/s
        velocity = None
        if length is not None and time_value not in (None, 0):
            velocity = (length / 100.0) / time_value
        row["c6"] = formatted(velocity, 6)
    return {"tables": tables}


def handle_structured(workpath, payload):
    """完成最终计算（含雷诺数修正）并生成处理结果。"""
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]

    parameters = payload.get("parameters") or {}
    rho = (as_number(parameters.get("rho")) or 7.859) * 1000.0   # g/cm³ → kg/m³
    rho0 = (as_number(parameters.get("rho0")) or 0.9552) * 1000.0
    g = as_number(parameters.get("g")) or 9.7947

    rows = enriched["tables"].get("table1", []) or []
    h_vals = [as_number(r.get("c1")) for r in rows]
    l_vals = [as_number(r.get("c2")) for r in rows]
    D_vals = [as_number(r.get("c3")) for r in rows]
    d_vals = [as_number(r.get("c4")) for r in rows]
    t_vals = [as_number(r.get("c5")) for r in rows]

    h = _mean(h_vals)          # cm
    l = _mean(l_vals)          # cm
    D = _mean(D_vals)          # mm
    d = _mean(d_vals)          # mm
    t = _mean(t_vals)          # s

    summary = []
    if d is not None and t is not None:
        d_m, t_s = d / 1000.0, t
        v = (l / 100.0) / t_s if l is not None else None
        D_m = D / 1000.0 if D is not None else None
        h_m = h / 100.0 if h is not None else None
        if v is not None and v != 0 and D_m and h_m:
            eta0 = (1.0 / 18.0) * (rho - rho0) * g * d_m ** 2 / (
                v * (1 + 2.4 * d_m / D_m) * (1 + 3.3 * (d_m / 2.0) / h_m)
            )
            Re = v * rho0 * d_m / eta0 if eta0 != 0 else None
            v_cm = l / t_s if l is not None else None
            summary.append(f"小球匀速下落速度 v = {v:.5f} m/s（对应 l̄ = {v_cm:.3f} cm/s）")
            summary.append(f"粘度零级近似 η₀ = {eta0:.5f} Pa·s")
            if Re is not None:
                summary.append(f"雷诺数 Re = {Re:.5f}")
                if Re < 0.1:
                    summary.append("Re < 0.1，无需修正，粘度 η = η₀")
                elif Re < 0.5:
                    eta1 = eta0 - (3.0 / 16.0) * d_m * v * rho0
                    summary.append(f"0.1 < Re < 0.5，进行一级修正，η₁ = {eta1:.5f} Pa·s")
                else:
                    eta1 = eta0 - (3.0 / 16.0) * d_m * v * rho0
                    inner = 1 + (19.0 / 270.0) * (d_m * v * rho0 / eta1) ** 2 if eta1 != 0 else 1
                    eta2 = 0.5 * eta1 * (1 + inner ** 0.5)
                    summary.append(f"Re > 0.5，进行二级修正，η₂ = {eta2:.5f} Pa·s")
        else:
            summary.append("数据不足，无法完成粘度计算，请检查各测量列是否填写完整。")
    else:
        summary.append("数据不足，无法完成粘度计算。")

    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        warnings=["本实验按要求不生成正式实验报告，此处仅输出数据处理结果。"] if summary else [],
    )
