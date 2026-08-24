"""匀加速运动实验模块
===================
一级大物力力学实验 —— 匀变速运动中速度与加速度的测量

包含三个子实验：
  表 1：匀变速运动中速度与加速度的测量
        滑块从斜面不同位置滑下，用光电门测量瞬时速度，
        作 v²-2s 图线性拟合求加速度 a，再由 g = aL/h 求重力加速度。
  表 2：验证牛顿第二定律
        改变悬挂质量（总质量不变），测量加速度，
        作 a-m_hang 图验证线性关系。
  表 3：研究三种碰撞状态下的守恒定律
        完全非弹性碰撞、弹性碰撞、非完全弹性碰撞，
        验证动量守恒。

物理公式：
  v = Δs / Δt （光电门测速）
  v² = 2as    （匀加速运动）
  a = m_hang · g / M_total （牛顿第二定律）
  p = mv       （动量）
"""

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def name():
    return "匀变速运动中速度与加速度的测量"


def handle(workpath, extension):
    """旧版 CSV 接口：保留原始逻辑。"""
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf")
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, names=["b", "s", "t1", "t2", "t3"], encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0, names=["b", "s", "t1", "t2", "t3"])
        os.remove(excelpath)

        delta_s = float(data["b"][0])
        h = float(data["b"][2])
        L = float(data["b"][4])
        data.dropna(inplace=True)
        data["两倍距离2s(m)"] = data["s"] / 50
        data["速度平方v^2(m^2/s^2)"] = (delta_s / ((data["t1"] + data["t2"] + data["t3"]) / 3)) ** 2

        res_lsm = analyse_lsm(data["两倍距离2s(m)"], data["速度平方v^2(m^2/s^2)"],
                              'X', 'Y', 'm/s^2', 'm^2/s^2')
        res_g = analyse_com("g=m*L/h", (), (("m", res_lsm.m), ("L", L), ("h", h)), "m/s^2")

        fig, ax = plt.subplots()
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.plot(data["两倍距离2s(m)"], data["速度平方v^2(m^2/s^2)"], "o", color='r', markersize=3)
        ax.plot(data["两倍距离2s(m)"], res_lsm.b + res_lsm.m * data["两倍距离2s(m)"], color='b', linewidth=1.5)
        ax.set_title("速度平方与两倍距离 $v^2-2s$ 关系曲线", fontproperties=zhfont)
        ax.set_xlabel("两倍距离 $2s\\rm{(m)}$", fontproperties=zhfont)
        ax.set_ylabel("速度平方 $v^2\\rm{(m^2/s^2)}$", fontproperties=zhfont)
        imgpath = workpath + "img.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu = Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        os.remove(imgpath)
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    sample1 = load_sample_data("exp8", "速度与加速度测量")
    sample2 = load_sample_data("exp8", "验证牛顿第二定律")
    sample3 = load_sample_data("exp8", "碰撞守恒定律")

    # 表 1 图表：v² vs 2s 线性拟合 → 斜率 = 加速度 a
    chart1 = {
        "x_column": "c7", "y_column": "c6",
        "x_label": "2s (m)", "y_label": "v^2 (m^2/s^2)",
        "title": "v^2 - 2s 线性拟合求加速度",
        "fit": "linear",
    }

    # 表 2 图表：a vs m_hang 线性拟合 → 验证牛顿第二定律
    chart2 = {
        "x_column": "c5", "y_column": "c6",
        "x_label": "m_hang (kg)", "y_label": "a (m/s^2)",
        "title": "a - m_hang 线性拟合（验证牛顿第二定律）",
        "fit": "linear",
    }

    return make_schema(
        "匀加速运动实验：测量速度加速度、验证牛顿第二定律、研究碰撞守恒",
        [
            make_table(
                "table1", "匀变速运动中速度与加速度的测量",
                [
                    "s/cm", "t1/ms", "t2/ms", "t3/ms",
                    "t_avg/ms", "v/(m/s)", "v^2/(m^2/s^2)", "2s/m",
                ],
                sample=sample1,
                readonly=(4, 5, 6, 7),
                initial_rows=5,
                chart=chart1,
                description="滑块从不同位置 s 滑下，光电门测量瞬时速度。"
                            "v^2 与 2s 成线性关系，斜率即为加速度 a，再由 g = aL/h 求重力加速度。",
            ),
            make_table(
                "table2", "验证牛顿第二定律",
                [
                    "m_hang/g", "s/cm", "t1/ms", "t2/ms", "t3/ms",
                    "m_hang/kg", "a/(m/s^2)",
                ],
                sample=sample2,
                readonly=(5, 6),
                initial_rows=5,
                chart=chart2,
                description="改变悬挂物质量（总质量不变），测量加速度。"
                            "a 与 m_hang 成线性关系，验证 F = Ma。",
            ),
            make_table(
                "table3", "研究三种碰撞状态下的守恒定律",
                [
                    "碰撞类型",
                    "Δt10/ms", "Δt1/ms", "Δt2/ms",
                    "v1/(m/s)", "v1'/(m/s)", "v2'/(m/s)",
                    "p_before/(kg*m/s)", "p_after/(kg*m/s)",
                ],
                sample=sample3,
                readonly=(4, 5, 6, 7, 8),
                text_columns=(0,),
                initial_rows=3,
                description="三种碰撞类型：完全非弹性、弹性、非完全弹性。"
                            "v1 = Δs1/Δt10（碰前），v1' = Δs1/Δt1、v2' = Δs2/Δt2（碰后）。"
                            "验证动量守恒 m1v1 = m1v1' + m2v2'。",
            ),
        ],
        parameters=[
            {"id": "delta_s", "label": "挡光宽度 Δs1 (mm)", "default": "10.1"},
            {"id": "h", "label": "垫块高 h (cm)", "default": "1.498"},
            {"id": "L", "label": "斜面长 L (cm)", "default": "86.1"},
            {"id": "delta_s2", "label": "挡光宽度 Δs2 (mm)", "default": "4.993"},
            {"id": "m1", "label": "滑块1质量 m1 (g)", "default": "329.8"},
            {"id": "m2", "label": "滑块2质量 m2 (g)", "default": "174.0"},
            {"id": "m_total", "label": "系统总质量 M (g)", "default": "500"},
            {"id": "s_fixed", "label": "表2固定距离 s (cm)", "default": "50"},
        ],
        analysis_hints="表1: 检查 v^2-2s 线性度，由斜率求 a，再计算 g = aL/h；"
                       "表2: 检查 a-m_hang 线性度；"
                       "表3: 比较碰前碰后动量，分析不同碰撞类型的守恒情况。",
        preview_enabled=True,
        table_theory=get_table_theory("exp8"), report_enabled=False,)


def preview(payload):
    """实时计算各表的派生量。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})

    # ── 公共参数 ──
    delta_s_mm = as_number(params.get("delta_s", "10.1")) or 10.1
    delta_s_m = delta_s_mm * 1e-3
    h_cm = as_number(params.get("h", "1.498")) or 1.498
    L_cm = as_number(params.get("L", "86.1")) or 86.1
    delta_s2_mm = as_number(params.get("delta_s2", "4.993")) or 4.993
    delta_s2_m = delta_s2_mm * 1e-3
    m1_g = as_number(params.get("m1", "329.8")) or 329.8
    m1_kg = m1_g * 1e-3
    m2_g = as_number(params.get("m2", "174.0")) or 174.0
    m2_kg = m2_g * 1e-3
    m_total_g = as_number(params.get("m_total", "500")) or 500
    m_total_kg = m_total_g * 1e-3
    s_fixed_cm = as_number(params.get("s_fixed", "50")) or 50
    s_fixed_m = s_fixed_cm * 1e-2

    # ── 表 1：t_avg、v、v^2、2s ──
    for row in tables.get("table1", []):
        t1 = as_number(row.get("c1"))
        t2 = as_number(row.get("c2"))
        t3 = as_number(row.get("c3"))
        s_cm = as_number(row.get("c0"))

        if t1 is not None and t2 is not None and t3 is not None:
            t_avg = (t1 + t2 + t3) / 3.0
            row["c4"] = formatted(t_avg, 4)
            if t_avg > 0:
                v = delta_s_m / (t_avg * 1e-3)
                row["c5"] = formatted(v, 4)
                row["c6"] = formatted(v * v, 6)
            else:
                row["c5"] = ""
                row["c6"] = ""
        else:
            row["c4"] = ""
            row["c5"] = ""
            row["c6"] = ""

        if s_cm is not None:
            row["c7"] = formatted(s_cm * 1e-2 * 2, 4)
        else:
            row["c7"] = ""

    # ── 表 2：m_hang(kg)、a ──
    for row in tables.get("table2", []):
        m_hang_g = as_number(row.get("c0"))
        t1 = as_number(row.get("c2"))
        t2 = as_number(row.get("c3"))
        t3 = as_number(row.get("c4"))

        if m_hang_g is not None:
            row["c5"] = formatted(m_hang_g * 1e-3, 4)
        else:
            row["c5"] = ""

        if t1 is not None and t2 is not None and t3 is not None:
            t_avg = (t1 + t2 + t3) / 3.0
            if t_avg > 0 and s_fixed_m > 0:
                v = delta_s_m / (t_avg * 1e-3)
                a = v * v / (2.0 * s_fixed_m)
                row["c6"] = formatted(a, 4)
            else:
                row["c6"] = ""
        else:
            row["c6"] = ""

    # ── 表 3：v1、v1'、v2'、p_before、p_after ──
    for row in tables.get("table3", []):
        dt10 = as_number(row.get("c1"))
        dt1 = as_number(row.get("c2"))
        dt2 = as_number(row.get("c3"))

        v1 = v1p = v2p = 0.0
        if dt10 is not None and dt10 > 0:
            v1 = delta_s_m / (dt10 * 1e-3)
            row["c4"] = formatted(v1, 4)
        else:
            row["c4"] = ""
        if dt1 is not None and dt1 > 0:
            v1p = delta_s_m / (dt1 * 1e-3)
            row["c5"] = formatted(v1p, 4)
        else:
            row["c5"] = ""
        if dt2 is not None and dt2 > 0:
            v2p = delta_s2_m / (dt2 * 1e-3)
            row["c6"] = formatted(v2p, 4)
        else:
            row["c6"] = ""

        p_before = m1_kg * v1
        p_after = m1_kg * v1p + m2_kg * v2p
        row["c7"] = formatted(p_before, 6)
        row["c8"] = formatted(p_after, 6)

    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]

    _schema = schema()
    charts = []

    # 表 1 图表：v^2 vs 2s
    t1_schema = _schema["tables"][0]
    t1_rows = enriched["tables"].get("table1", [])
    c1_config = t1_schema.get("chart")
    if c1_config and t1_rows:
        charts.append(make_chart_from_table(
            t1_schema, t1_rows, c1_config,
            workpath, chart_filename="chart_v2_vs_2s.png",
        ))

    # 表 2 图表：a vs m_hang
    t2_schema = _schema["tables"][1]
    t2_rows = enriched["tables"].get("table2", [])
    c2_config = t2_schema.get("chart")
    if c2_config and t2_rows:
        charts.append(make_chart_from_table(
            t2_schema, t2_rows, c2_config,
            workpath, chart_filename="chart_a_vs_mhang.png",
        ))

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=[
            "匀加速运动实验数据已处理。",
            "表 1：v^2-2s 线性拟合求加速度 a，由 g = aL/h 计算重力加速度；",
            "表 2：a-m_hang 线性拟合验证牛顿第二定律；",
            "表 3：三种碰撞的动量守恒分析。",
        ],
        charts=charts,
    )
