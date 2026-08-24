"""磁力摆实验模块
===============
一级大物电磁学实验 —— 磁力摆 B

基础内容（对应实验指导书）：
  1. 掌握亥姆霍兹线圈磁场的分布规律
     → 测量磁场大小与线圈电流的关系（验证 B₁ = kI，线性拟合）
  2. 掌握局域地磁场水平分量的测量方法
     → 测量不同电流下磁针的振动周期，通过作图给出 B₀

物理公式：
  T = 2π√(J / mB)   →   T² = 4π²J / (mB)
  B = B₀ ± B₁（同向取 +，反向取 −）
  B₁ = (4/5)^(3/2) · μ₀NI / R  = k · I

线性化作图原理：
  由 T² = 4π²J / (m·B_total) 得  1/T² = m·B_total / (4π²J)
  故 1/T² 与 B_total 成线性关系：
    斜率 s = m / (4π²J)
    截距 i = m·B₀ / (4π²J)
    → B₀ = i / s
"""

from head import *  # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data

# ── 物理常量（典型教学仪器参数）──
_N = 500                        # 线圈匝数
_R = 0.10                       # 线圈半径 / m
_MU0 = 4e-7 * pi                # 真空磁导率 / T·m/A
_K_COIL = (4 / 5) ** 1.5 * _MU0 * _N / _R   # ≈ 4.423e-4 T/A
_B0_REF = 2.0e-5                # 参考地磁场水平分量 / T（约 20 μT）
_J_OVER_M = 1.13e-7             # 转动惯量 / 磁矩


# ─────────────────────────────────────────────
# 旧版接口（向后兼容）
# ─────────────────────────────────────────────
def name():
    return "磁力摆"


def handle(workpath, extension):
    """旧版 CSV 单表接口：读取数据 → 生成 Word 文档。"""
    try:
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)
        os.remove(excelpath)

        docu = Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("实验数据已接收，请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    # 从 CSV 文件加载示例数据
    sample1 = load_sample_data("exp10", "亥姆霍兹线圈磁场与振荡周期")
    sample2 = load_sample_data("exp10", "1T2与Btotal线性拟合")

    # 表 1 图表：T² 与 I 的关系（验证磁场与电流线性关系）
    chart1 = {
        "x_column": "c0", "y_column": "c3",
        "x_label": "I (A)",
        "y_label": "T_plus^2 (s^2)",
        "title": "振荡周期平方与励磁电流关系",
        "fit": "auto",
    }

    # 表 2 图表：1/T² 与 B_total 线性拟合 → 求 B₀
    chart2 = {
        "x_column": "c2", "y_column": "c4",
        "x_label": "B_total (1e-5 T)",
        "y_label": "1/T_plus^2 (1/s^2)",
        "title": "1/T^2 - B_total 线性拟合（求地磁场水平分量）",
        "fit": "linear",
    }

    return make_schema(
        "磁力摆实验：测量亥姆霍兹线圈磁场分布及局域地磁场水平分量",
        [
            make_table(
                "table1",
                "亥姆霍兹线圈磁场与振荡周期测量",
                [
                    "励磁电流 I(A)",
                    "同向周期 T+(s)",
                    "反向周期 T-(s)",
                    "T+^2 (s^2)",
                ],
                sample=sample1,
                readonly=(3,),
                initial_rows=6,
                chart=chart1,
                description="测量不同励磁电流下磁针的振动周期。T+ 为线圈磁场与地磁场同向，T- 为反向。",
            ),
            make_table(
                "table2",
                "1/T^2 与 B_total 线性拟合求地磁场水平分量",
                [
                    "励磁电流 I(A)",
                    "T+(s)",
                    "B_total (1e-5 T)",
                    "1/B_total (1e5/T)",
                    "1/T+^2 (1/s^2)",
                ],
                sample=sample2,
                readonly=(2, 3, 4),
                initial_rows=6,
                chart=chart2,
                description="由 B_total = B0 + kI 计算总磁场。作 1/T^2 - B_total 图，"
                            "线性拟合的截距与斜率之比即为局域地磁场水平分量 B0 = 截距/斜率。",
            ),
        ],
        parameters=[
            {
                "id": "k_coil",
                "label": "线圈常数 k (1e-4 T/A)",
                "default": "4.423",
                "unit": "1e-4 T/A",
                "backend_key": "k_coil_raw",
            },
        ],
        analysis_hints="检查 B-I 关系的线性度，以及 1/T^2-B_total 拟合的线性度；"
                       "由截距/斜率求 B0，与当地地磁场参考值比较。",
        preview_enabled=True,
        table_theory=get_table_theory("exp10"),)


def preview(payload):
    """实时计算派生量：T+^2、B_total、1/B_total、1/T+^2。"""
    tables = copied_tables(payload)

    # 表 1：计算 T+^2
    for row in tables.get("table1", []):
        tp = as_number(row.get("c1"))
        row["c3"] = formatted(tp * tp if tp is not None else None, 6)

    # 表 2：计算 B_total、1/B_total、1/T+^2
    k_raw = as_number(payload.get("parameters", {}).get("k_coil", "4.423"))
    k_coil = (k_raw if k_raw is not None else 4.423) * 1e-4

    for row in tables.get("table2", []):
        I_val = as_number(row.get("c0"))
        tp = as_number(row.get("c1"))

        # B_total = B0 + k*I，以 ×10⁻⁵ T 为单位显示
        if I_val is not None:
            B_total = _B0_REF + k_coil * I_val
            B_display = B_total * 1e5
            row["c2"] = formatted(B_display, 4)
            row["c3"] = formatted(1.0 / B_display if B_display != 0 else None, 6)
        else:
            row["c2"] = ""
            row["c3"] = ""

        # 1/T+^2
        if tp is not None and tp > 0:
            row["c4"] = formatted(1.0 / (tp * tp), 6)
        else:
            row["c4"] = ""

    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]

    _schema = schema()
    charts = []

    # 从表 2 生成图表：1/T² vs B_total 线性拟合
    table2_schema = _schema["tables"][1]
    table2_rows = enriched["tables"].get("table2", [])
    chart2_config = table2_schema.get("chart")
    if chart2_config and table2_rows:
        chart_item = make_chart_from_table(
            table2_schema, table2_rows, chart2_config,
            workpath, chart_filename="chart_1overT2_vs_B.png",
        )
        charts.append(chart_item)

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=[
            "磁力摆实验数据已处理。",
            "表 1 验证了亥姆霍兹线圈磁场与电流的线性关系；",
            "表 2 通过 1/T^2 - B_total 线性拟合可求局域地磁场水平分量 B0 = 截距/斜率。",
        ],
        charts=charts,
    )
