"""磁力摆实验模块
===============
一级大物电磁学实验 —— 磁力摆

基础内容（对应实验指导书）：
  表1：亥姆霍兹线圈磁场标定（B-I 关系），用高灵敏特斯拉计测量不同电流下
      线圈中心的磁感应强度，拟合 B = k·I + b₀ 得到线圈常数 k，
      与理论值 k_理论 = (4/5)^(3/2)·μ₀N/R 对比。
  表2/表3：磁力摆振动周期测量（线圈磁场与地磁场同向 / 反向），
      每个电流下重复测量 3 次 n 个周期总时间，求平均周期 T̄ 与 1/T̄²。
  双直线拟合：同向 1/T₊² = A₊ + b₊·I，反向 1/T₋² = A₋ + b₋·I，
  取 A = (A₊+A₋)/2、b = (|b₊|+|b₋|)/2，
  由 B₀ = k × (A/b) 求局域地磁场水平分量（A/b = B₀/k）。

物理公式：
  B₁ = (4/5)^(3/2) · μ₀NI / R    （亥姆霍兹线圈中心磁场）
  1/T² = (m/(4π²J)) · (B₀ ± kI)  （磁力摆周期线性化，±对应同向/反向）
  B₀ = k · A / b                  （地磁场水平分量）
"""

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    make_chart_from_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data

# ── 物理常量 ─
_MU0 = 4e-7 * math.pi          # 真空磁导率 / T·m/A（用 math.pi 避免 sympy 符号污染数值计算）
_FIT_MIN_POINTS = 4             # 拟合所需最少数据点数


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
        style_doc_font(docu)
        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────
def _linear_fit_r2(xs, ys):
    """最小二乘线性拟合，返回 (斜率 k, 截距 b, 相关系数 R²)。"""
    n = len(xs)
    if n < 2:
        return None
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    sxy = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    syy = sum((y - y_mean) ** 2 for y in ys)
    if sxx == 0:
        return None
    k = sxy / sxx
    b = y_mean - k * x_mean
    r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else 1.0
    return k, b, r2


def _extract_points(rows, x_col, y_col):
    """从表格行提取 (x, y) 数据点，跳过空值。"""
    pts = []
    for row in rows:
        x_val = as_number(row.get(x_col))
        y_val = as_number(row.get(y_col))
        if x_val is not None and y_val is not None:
            pts.append((x_val, y_val))
    return pts


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def _period_sample(csv_name, time_column):
    """周期表示例：CSV 列为 I、T+、T-（可能还有 T+²），取指定列的时间值，
    三次重复测量暂填同一值（示例数据）。"""
    raw = load_sample_data("exp10", csv_name)
    rows = []
    for row in raw:
        if len(row) <= time_column or not row[0] or not row[time_column]:
            continue
        try:
            float(row[0])
            float(row[time_column])
        except (TypeError, ValueError):
            continue
        t = row[time_column]
        rows.append([row[0], t, t, t])
    return rows


def _table1_sample():
    """表 1 示例：按理论线圈常数 k = (4/5)^(3/2)·μ₀N/R 生成 B = k·I
    （与默认参数 N=30、R=1.0 m 一致），I = 0.0～1.0 A 共 6 点。"""
    k_mT = (0.8 ** 1.5) * _MU0 * 30.0 / 1.0 * 1000.0
    rows = []
    for i in range(6):
        current = 0.2 * i
        rows.append([f"{current:.1f}", f"{k_mT * current:.4f}"])
    return rows


def schema():
    sample1 = _table1_sample()
    sample2 = _period_sample("亥姆霍兹线圈磁场与振荡周期", 1)   # 同向：T+ 列
    sample3 = _period_sample("1T2与Btotal线性拟合", 2)          # 反向：T- 列

    # 表 1 图表：B-I 标定拟合
    chart_bi = {
        "x_column": "c0", "y_column": "c1",
        "x_label": "I (A)",
        "y_label": "B (mT)",
        "title": "亥姆霍兹线圈 B-I 标定拟合",
        "fit": "linear",
    }

    period_columns = [
        "I (A)",              # c0
        "t₁ (s)",             # c1
        "t₂ (s)",             # c2
        "t₃ (s)",             # c3
        "T̄ (s)",              # c4 只读（自动计算）
        "1/T̄² (s⁻²)",         # c5 只读（自动计算）
    ]

    return make_schema(
        (
            "本实验用小磁针在亥姆霍兹线圈磁场中的摆动测量局域地磁场的水平分量。"
            "请先完成 B–I 标定，再测量同向、反向振动周期随电流的变化，由 "
            r"$\frac{1}{T^2} = A \pm bI$" " 拟合得 " r"$B_0 = kA/b$" "。"
            "注意磁针置于线圈中心、电流不超过 1.0 A。"
        ),
        [
            make_table(
                "table1", "表1  亥姆霍兹线圈中心磁感应强度与电流关系",
                ["I (A)", "B (mT)"],
                sample=sample1,
                readonly=(),
                initial_rows=6,
                chart=chart_bi,
                description="用高灵敏特斯拉计测量线圈中心不同电流下的磁感应强度 B。"
                            "电流预设 0.0～1.0 A（可自行增删行）。"
                            "输入满 4 组数据后，表格下方自动显示拟合结果。",
            ),
            make_table(
                "table2", "表2  磁力摆振动周期测量（同向：线圈磁场与地磁场同向）",
                period_columns,
                sample=sample2,
                readonly=(4, 5),
                initial_rows=6,
                description="同向时 1/T₊² = A + b·I（斜率为正）。"
                            "每个电流下重复测量 3 次 n 个周期总时间 t₁、t₂、t₃。"
                            "提示：I = 0 行同向与反向物理条件相同，数据可共用，也可分别测量互相校验。",
            ),
            make_table(
                "table3", "表3  磁力摆振动周期测量（反向：线圈磁场与地磁场反向）",
                period_columns,
                sample=sample3,
                readonly=(4, 5),
                initial_rows=6,
                description="反向时 1/T₋² = A − b·I（斜率为负）。"
                            "每个电流下重复测量 3 次 n 个周期总时间 t₁、t₂、t₃。"
                            "提示：I = 0 行同向与反向物理条件相同，数据可共用，也可分别测量互相校验。",
            ),
        ],
        parameters=[
            {"id": "N", "label": "线圈匝数 N", "default": "30"},
            {"id": "R", "label": "线圈半径 R (m)", "default": "1.0"},
            {"id": "n", "label": "振动次数 n（测量的周期数）", "default": "10"},
            {"id": "B0_ref", "label": "参考地磁场水平分量 B₀_ref (μT)", "default": "30"},
        ],
        analysis_hints="表 1：B-I 标定拟合求线圈常数 k，并与理论值 k_理论 = (4/5)^(3/2)·μ₀N/R 对比。"
                       "表 2/表 3：同向、反向各测一组振动周期，分别拟合 1/T² - I 直线。"
                       "取平均截距 A、平均斜率绝对值 b，由 B₀ = k·(A/b) 求局域地磁场水平分量。",
        preview_enabled=True,
        table_theory=get_table_theory("exp10"),
    )


def preview(payload):
    """实时计算：只读列补全 + 拟合结果标注（fit_notes 渲染在表格下方）。"""
    tables = copied_tables(payload)
    params = payload.get("parameters", {})
    fit_notes = {}
    enriched_params = dict(params)

    # ── 参数 ──
    N = as_number(params.get("N")) or 30
    R = as_number(params.get("R")) or 1.0
    n_osc = as_number(params.get("n")) or 10
    B0_ref = as_number(params.get("B0_ref"))

    # 理论线圈常数：k_理论 = (4/5)^(3/2)·μ₀N/R（T/A → mT/A）
    k_theory_mT = (0.8 ** 1.5) * _MU0 * N / R * 1000.0
    enriched_params["_k_theory_mT"] = k_theory_mT

    # ── 表 1：B-I 标定拟合 ──
    bi_pts = _extract_points(tables.get("table1", []), "c0", "c1")
    k_calib = None
    if len(bi_pts) >= _FIT_MIN_POINTS:
        fit = _linear_fit_r2([p[0] for p in bi_pts], [p[1] for p in bi_pts])
        if fit is not None:
            k_calib, b0_calib, r2_calib = fit
            calib_err = abs(k_calib - k_theory_mT) / k_theory_mT * 100 if k_theory_mT else None
            enriched_params.update({"_k_calib": k_calib, "_b0_calib": b0_calib,
                                    "_r2_calib": r2_calib, "_calib_err": calib_err})
            fit_notes["table1"] = [
                f"拟合直线：B = {k_calib:.4f}·I + {b0_calib:.4f}（mT）",
                f"斜率 k = {k_calib:.4f} mT/A",
                f"截距 b₀ = {b0_calib:.4f} mT",
                f"相关系数 R² = {r2_calib:.4f}",
                f"理论值 k_理论 = (4/5)^(3/2)·μ₀N/R = {k_theory_mT:.4f} mT/A",
                f"标定相对误差 = |k − k_理论| / k_理论 × 100% = {calib_err:.2f}%",
            ]
    elif bi_pts:
        fit_notes["table1"] = [f"已输入 {len(bi_pts)} 组数据，满 {_FIT_MIN_POINTS} 组后自动开始拟合。"]

    # ── 表 2 / 表 3：周期测量 → T̄、1/T̄² ──
    period_pts = {}
    for table_id in ("table2", "table3"):
        pts = []
        for row in tables.get(table_id, []):
            I_val = as_number(row.get("c0"))
            t1 = as_number(row.get("c1"))
            t2 = as_number(row.get("c2"))
            t3 = as_number(row.get("c3"))
            if t1 is not None and t2 is not None and t3 is not None and n_osc > 0:
                T_bar = (t1 + t2 + t3) / (3.0 * n_osc)
                row["c4"] = formatted(T_bar, 4)
                row["c5"] = formatted(1.0 / (T_bar * T_bar), 4)
                if I_val is not None and T_bar > 0:
                    pts.append((I_val, 1.0 / (T_bar * T_bar)))
            else:
                row["c4"] = ""
                row["c5"] = ""
        period_pts[table_id] = pts

    # ── 双直线拟合 ──
    fit_p = _linear_fit_r2([p[0] for p in period_pts["table2"]],
                           [p[1] for p in period_pts["table2"]]) \
        if len(period_pts["table2"]) >= 2 else None
    fit_m = _linear_fit_r2([p[0] for p in period_pts["table3"]],
                           [p[1] for p in period_pts["table3"]]) \
        if len(period_pts["table3"]) >= 2 else None

    warnings = []
    A_avg, b_avg, B0 = None, None, None
    if fit_p is not None:
        enriched_params.update({"_A_p": fit_p[1], "_b_p": fit_p[0], "_r2_p": fit_p[2]})
        fit_notes["table2"] = [
            f"同向拟合：1/T₊² = {fit_p[1]:.4f} + {fit_p[0]:.4f}·I",
            f"截距 A₊ = {fit_p[1]:.4f} s⁻²，斜率 b₊ = {fit_p[0]:.4f} s⁻²/A，R² = {fit_p[2]:.4f}",
        ]
        if fit_p[0] < 0:
            warnings.append("同向斜率 b₊ 为负：斜率符号异常，请检查同向/反向接线是否正确")
    if fit_m is not None:
        enriched_params.update({"_A_m": fit_m[1], "_b_m": fit_m[0], "_r2_m": fit_m[2]})
        fit_notes["table3"] = [
            f"反向拟合：1/T₋² = {fit_m[1]:.4f} + {fit_m[0]:.4f}·I",
            f"截距 A₋ = {fit_m[1]:.4f} s⁻²，斜率 b₋ = {fit_m[0]:.4f} s⁻²/A，R² = {fit_m[2]:.4f}",
        ]
        if fit_m[0] > 0:
            warnings.append("反向斜率 b₋ 为正：斜率符号异常，请检查同向/反向接线是否正确")

    # ── 最终结果：B₀ = k × A / b ──
    if fit_p is not None and fit_m is not None:
        A_avg = (fit_p[1] + fit_m[1]) / 2.0
        b_avg = (abs(fit_p[0]) + abs(fit_m[0])) / 2.0
        if abs(fit_p[1] - fit_m[1]) > 0.2 * max(abs(fit_p[1]), abs(fit_m[1]), 1e-12):
            warnings.append("两组截距 A₊ 与 A₋ 偏差超过 20%，建议检查 I = 0 附近数据")
        if b_avg > 0 and k_calib is not None:
            k_uT = k_calib * 1000.0  # mT/A → μT/A
            B0 = k_uT * (A_avg / b_avg)
            enriched_params.update({"_A_avg": A_avg, "_b_avg": b_avg, "_B0": B0})
            final_lines = [
                "【最终结果】",
                f"平均截距 A = (A₊ + A₋)/2 = {A_avg:.4f} s⁻²",
                f"平均斜率绝对值 b = (|b₊| + |b₋|)/2 = {b_avg:.4f} s⁻²/A",
                f"局域地磁场水平分量 B₀ = k·(A/b) = {B0:.1f} μT",
            ]
            if B0_ref:
                err = abs(B0 - B0_ref) / B0_ref * 100
                enriched_params["_B0_err"] = err
                final_lines.append(f"参考值 B₀_ref = {B0_ref:.1f} μT，相对误差 = {err:.1f}%")
            fit_notes.setdefault("table3", []).extend(final_lines)
        elif k_calib is None:
            fit_notes.setdefault("table3", []).append(
                f"【提示】表 1 需满 {_FIT_MIN_POINTS} 组数据完成标定后，才能计算 B₀。")

    for warning in warnings:
        fit_notes.setdefault("table3", []).append(f"⚠ {warning}")
    enriched_params["_warnings"] = warnings
    enriched_params["_bi_pts"] = bi_pts
    enriched_params["_pts_p"] = period_pts["table2"]
    enriched_params["_pts_m"] = period_pts["table3"]

    return {"tables": tables, "parameters": enriched_params, "fit_notes": fit_notes}


def _generate_dual_line_chart(params, workpath):
    """图2：1/T² - I 双直线拟合图（同向蓝、反向红，含延长线与交点标注）。"""
    pts_p = params.get("_pts_p", [])
    pts_m = params.get("_pts_m", [])
    fit_p = (params.get("_b_p"), params.get("_A_p"))
    fit_m = (params.get("_b_m"), params.get("_A_m"))
    B0 = params.get("_B0")
    k_calib = params.get("_k_calib")
    if len(pts_p) + len(pts_m) < 4:
        return None

    try:
        zhfont = matplotlib.font_manager.FontProperties(
            fname=os.path.join(os.path.dirname(__file__), "SourceHanSansSC-Regular.otf")
        )
    except Exception:
        zhfont = matplotlib.font_manager.FontProperties()

    fig, ax = plt.subplots(figsize=(10, 6.5))

    # ── 数据点 ──
    if pts_p:
        ax.plot([p[0] for p in pts_p], [p[1] for p in pts_p], 'o',
                color='tab:blue', markersize=6, label='同向（B = B0 + kI）', zorder=4)
    if pts_m:
        ax.plot([p[0] for p in pts_m], [p[1] for p in pts_m], 'o',
                color='tab:red', markersize=6, label='反向（B = B0 - kI）', zorder=4)

    # ── 拟合直线与延长线 ──
    all_I = [p[0] for p in pts_p + pts_m]
    I_lo = min(min(all_I), -0.6) if all_I else -0.6
    I_hi = max(all_I) if all_I else 1.0

    def _draw_fit(slope, intercept, color, label_prefix):
        if slope is None or intercept is None:
            return
        ax.plot([I_lo, I_hi], [slope * I_lo + intercept, slope * I_hi + intercept],
                '-', color=color, linewidth=1.6,
                label=f'{label_prefix}：y = {intercept:.3f} + ({slope:.3f})·I', zorder=3)
        # I 轴交点 I = -A/b（延长线）
        if slope != 0:
            I_cross = -intercept / slope
            ax.plot(I_cross, 0.0, 'v', color=color, markersize=9, zorder=5)
            ax.annotate(f'I = {I_cross:.3f} A',
                        xy=(I_cross, 0.0), xytext=(I_cross, -0.06),
                        fontsize=9, color=color, ha='center', fontproperties=zhfont)

    _draw_fit(fit_p[0], fit_p[1], 'tab:blue', '同向拟合')
    _draw_fit(fit_m[0], fit_m[1], 'tab:red', '反向拟合')

    # ── 坐标轴（延长部分需要留出 1/T² < 0 的空间）──
    y_max = max([p[1] for p in pts_p + pts_m] + [0.1])
    ax.set_xlim(I_lo - 0.15, I_hi + 0.35)
    ax.set_ylim(-0.12 * y_max, y_max * 1.15)

    # ── I=0 竖直辅助线与两线交点 (0, A) ──
    ax.axvline(x=0.0, color='gray', linestyle='-.', linewidth=1, zorder=1)
    if fit_p[1] is not None and fit_m[1] is not None:
        A_avg = (fit_p[1] + fit_m[1]) / 2.0
        ax.plot(0.0, A_avg, 'ks', markersize=8, zorder=5)
        ax.annotate(f'(0, A)，A = {A_avg:.3f}',
                    xy=(0.0, A_avg), xytext=(0.08, A_avg * 1.05),
                    fontsize=9, fontproperties=zhfont,
                    arrowprops=dict(arrowstyle='->', color='gray'))

    # ── B₀ 标注 ──
    if B0 is not None:
        title_extra = f'　　B0 = {B0:.1f} μT'
        if k_calib is not None:
            title_extra += f'（k = {k_calib:.4f} mT/A）'
    else:
        title_extra = ''

    ax.set_xlabel('I (A)', fontsize=12, fontproperties=zhfont)
    ax.set_ylabel('1/T² (1/s²)', fontsize=12, fontproperties=zhfont)
    ax.set_title('磁力摆 1/T² - I 双直线拟合（求地磁场水平分量）' + title_extra,
                 fontsize=13, fontproperties=zhfont)
    ax.legend(loc='upper right', fontsize=9, prop=zhfont)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    imgpath = os.path.join(workpath, "chart_dual_line_fit.png")
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


def handle_structured(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    enriched["parameters"] = preview_result["parameters"]

    _schema = schema()
    charts = []
    params = enriched.get("parameters", {})

    # ── 图 1：B-I 标定拟合图 ──
    t1_schema = _schema["tables"][0]
    c1_config = t1_schema.get("chart")
    t1_rows = enriched["tables"].get("table1", [])
    if c1_config and t1_rows:
        charts.append(make_chart_from_table(
            t1_schema, t1_rows, c1_config,
            workpath, chart_filename="chart_BI_calibration.png",
        ))

    # ── 图 2：1/T² - I 双直线拟合图 ──
    chart_path = _generate_dual_line_chart(params, workpath)
    if chart_path:
        charts.append({
            "filename": "chart_dual_line_fit.png",
            "title": "1/T̄² − I 双直线拟合（同向/反向）",
            "url": chart_path,
        })

    # ── 卡片式结果汇总 ──
    summary_lines = ["磁力摆实验数据处理结果："]

    if params.get("_k_calib") is not None:
        summary_lines.extend([
            "【线圈标定结果】",
            f"k = {params['_k_calib']:.4f} mT/A = {params['_k_calib'] * 1000:.2f} μT/A，"
            f"截距 b₀ = {params.get('_b0_calib', 0):.4f} mT，R² = {params.get('_r2_calib', 0):.4f}",
            f"k_理论 = {params['_k_theory_mT']:.4f} mT/A，"
            f"标定相对误差 = {params.get('_calib_err', 0):.2f}%",
        ])
    if params.get("_A_p") is not None:
        summary_lines.extend([
            "【同向拟合】",
            f"1/T₊² = {params['_A_p']:.4f} + {params['_b_p']:.4f}·I，R² = {params['_r2_p']:.4f}",
        ])
    if params.get("_A_m") is not None:
        summary_lines.extend([
            "【反向拟合】",
            f"1/T₋² = {params['_A_m']:.4f} + {params['_b_m']:.4f}·I，R² = {params['_r2_m']:.4f}",
        ])
    if params.get("_B0") is not None:
        final_lines = [
            "【最终结果】",
            f"平均截距 A = {params['_A_avg']:.4f} s⁻²",
            f"平均斜率绝对值 b = {params['_b_avg']:.4f} s⁻²/A",
            f"★ 局域地磁场水平分量 B₀ = {params['_B0']:.1f} μT",
        ]
        B0_ref = as_number(enriched.get("parameters", {}).get("B0_ref")) or as_number(payload.get("parameters", {}).get("B0_ref"))
        if B0_ref:
            final_lines.append(f"参考值 B₀_ref = {B0_ref:.1f} μT，相对误差 = {params.get('_B0_err', 0):.1f}%")
        summary_lines.extend(final_lines)

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        warnings=params.get("_warnings", []),
        charts=charts,
    )
