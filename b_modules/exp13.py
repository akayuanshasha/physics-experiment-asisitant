"""整流滤波电路实验模块
===================
一级大物电磁学实验 —— 整流滤波

基础内容（对应实验指导书）：
  输入信号：f = 400 Hz，Vpp(in) = 10 V。
  1. 全波整流 + 1μF 电容滤波 → 测 U_DC, U_AC → 算纹波系数 Ku
  2. 全波整流 + π 型 RC 滤波 → 测 U_DC, U_AC → 算纹波系数 Ku
  比较两种滤波电路的纹波系数。

提升内容：
  改变滤波电容（1μF → 10μF），探究电容大小对纹波系数的影响。

物理公式：
  Ku = U_AC / U_DC × 100%               （纹波系数）
  半波整流平均值 Udc = Up/π，全波整流平均值 Udc = 2Up/π（Up = Vpp/2）
  单电容滤波：导通时 u_c = u_in，截止时 u_c *= exp(-dt/(RL·C))
  π型第二级：R_eq = R1·RL/(R1+RL)，τ = R_eq·C2，u_inf = u_c1·RL/(R1+RL)
             u_c2 = u_inf + (u_c2_prev − u_inf)·exp(-dt/τ)
  τ = RC：电容越大 → 纹波越小 → 滤波效果越好
"""

import math

from head import *
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table,
    structured_result,
)
from theory_content import get_table_theory
from sample_data_loader import load_sample_data

# 仿真参数（与前端自定义页面保持一致）：3 个周期共 3000 个采样点，
# 纹波统计只取最后一个完整周期（第 2→第 3 周期末），避免初始充电瞬态。
_SIM_N = 3000


def name():
    return "整流滤波"


def handle(workpath, extension):
    """旧版 CSV 接口：保留原始逻辑。"""
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf")
        excelpath = workpath + name() + '.' + extension
        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0,
                               names=["f.Hz", "pi.DC", "pi.AC", "whole.DC", "whole.AC"],
                               encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0,
                                 names=["f.Hz", "pi.DC", "pi.AC", "whole.DC", "whole.AC"])
        os.remove(excelpath)

        fig, ax = plt.subplots()
        ax.plot(data["f.Hz"], data["pi.AC"] / data["pi.DC"] * 100, 'o-',
                color='r', markersize=3, label="π型RC电路")
        ax.plot(data["f.Hz"], data["whole.AC"] / data["whole.DC"] * 100, 'o-',
                color='b', markersize=3, label="全波整流电路")
        ax.set_title("纹波系数随频率的变化曲线", fontproperties=zhfont)
        ax.set_xlabel("频率 $f/Hz$", fontproperties=zhfont)
        ax.set_ylabel("纹波系数$\\gamma(\\%)$", fontproperties=zhfont)
        ax.legend(prop=zhfont)
        imgpath = workpath + "img.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu = Document()
        style_doc_font(docu)
        docu.add_paragraph("请使用新版结构化界面获取完整分析。")
        docu.save(workpath + name() + ".docx")
        os.remove(imgpath)
        return 0
    except:
        traceback.print_exc()
        return 1


# ─────────────────────────────────────────────
# 电容滤波数值仿真（供统一前端 preview 接口使用）
# ─────────────────────────────────────────────
def _simulate(Up, freq, RL, c_single, c1, c2, r1):
    """全波整流后接滤波电路的逐时间步数值仿真。

    参数（电容单位均为 F，已换算）：
      Up        峰值 = Vpp/2
      freq      信号频率 (Hz)
      RL        负载电阻 (Ω)
      c_single  单电容滤波电容 (F)
      c1/c2/r1  π 型滤波参数 (F, F, Ω)

    返回 (uin, u_single, u_pi) 三个长度为 _SIM_N 的数组（3 个周期）。
    """
    total = 3.0 / freq                       # 总时长 = 3 个周期
    dt = total / _SIM_N                      # 时间步长
    r_eq = r1 * RL / (r1 + RL)               # π型第二级等效放电电阻 R1‖RL
    tau2 = r_eq * c2                         # 第二级时间常数
    uin = np.empty(_SIM_N)
    u_single = np.empty(_SIM_N)
    u_pi = np.empty(_SIM_N)
    uc = uc1 = uc2 = 0.0                     # 初始电容电压均为 0
    for n in range(_SIM_N):
        t = n * dt
        # 全波整流输出作为滤波电路输入：|Up·sin(2πft)|
        ui = abs(Up * math.sin(2 * math.pi * freq * t))
        uin[n] = ui
        # 单电容：ui > u_c 时二极管导通（近似立即跟随充电），
        #         否则二极管截止，电容经 RL 指数放电
        uc = ui if ui > uc else uc * math.exp(-dt / (RL * c_single))
        u_single[n] = uc
        # π型第一级 C1：与单电容相同的导通/截止递推
        uc1 = ui if ui > uc1 else uc1 * math.exp(-dt / (RL * c1))
        # π型第二级 R1-C2 低通（无二极管，始终导通），指数法精确递推：
        #   稳态值 u_inf = u_c1·RL/(R1+RL)，u_c2 按 exp(-dt/τ) 趋近稳态
        u_inf = uc1 * RL / (r1 + RL)
        uc2 = u_inf + (uc2 - u_inf) * math.exp(-dt / tau2)
        u_pi[n] = uc2
    return uin, u_single, u_pi


def _ripple(u):
    """取最后一个完整周期计算直流分量、交流有效值与纹波系数。"""
    seg = u[2 * len(u) // 3:]
    udc = float(seg.mean())
    uac = math.sqrt(float(((seg - udc) ** 2).mean()))
    ku = uac / udc * 100 if udc else None
    return udc, uac, ku


def _theory_ku(kind, c_uf, params):
    """按电路类型与电容值（μF）仿真出理论纹波系数。"""
    up = (params["vpp"] / 2.0)
    c_f = c_uf * 1e-6                        # μF → F
    _, u_single, u_pi = _simulate(
        up, params["freq"], params["rl"],
        c_f, c_f, c_f, params["r1"],
    )
    _, _, ku = _ripple(u_single if kind == "single" else u_pi)
    return ku


def _zhfont():
    try:
        return matplotlib.font_manager.FontProperties(
            fname="SourceHanSansSC-Regular.otf")
    except Exception:
        return matplotlib.font_manager.FontProperties()


# ─────────────────────────────────────────────
# 新版结构化接口
# ─────────────────────────────────────────────
def schema():
    sample = load_sample_data("exp13", "纹波系数汇总对比")
    return make_schema(
        (
            "本实验学习整流滤波电路的基本工作原理并制作直流电源。请记录不同电路"
            "（半波/全波/π 型滤波）与不同电容下的 " r"$U_{DC}$" "、" r"$U_{AC}$" "，"
            "计算纹波系数 " r"$K_u = U_{AC}/U_{DC}$" " 并与理论值比较。"
        ),
        [
            make_table(
                "table1", "纹波系数汇总对比",
                [
                    "电路类型",          # c0 文字：单电容滤波 / π型RC滤波
                    "电容值 C(μF)",        # c1 该配置的滤波电容值
                    "实测U_DC(V)",       # c2 万用表直流电压档
                    "实测U_AC(V)",       # c3 万用表交流电压档
                    "实测Ku(%)",         # c4 只读：U_AC/U_DC×100
                    "理论Ku(%)",         # c5 只读：数值仿真理论值
                ],
                sample=sample,
                readonly=(4, 5),
                text_columns=(0,),
                initial_rows=4,
                description="四种电路配置：{单电容, π型RC} × {1 μF, 10 μF}。"
                            "填入万用表实测的 U_DC 与 U_AC，"
                            "实测纹波系数 Ku = U_AC/U_DC×100% 与理论值（数值仿真，"
                            "3 周期 3000 点、取最后一个完整周期）均自动计算。",
            ),
        ],
        parameters=[
            {"id": "freq", "label": "信号源频率 f (Hz)", "default": "400"},
            {"id": "vpp", "label": "信号源峰峰值 Vpp (V)", "default": "10"},
            {"id": "rl", "label": "负载电阻 RL (Ω)", "default": "1000"},
            {"id": "r1", "label": "π 型滤波电阻 R1 (Ω)", "default": "100"},
        ],
        analysis_hints="比较单电容与 π 型滤波的纹波系数，π 型滤波效果更优；"
                       "对比 1 μF 与 10 μF：电容越大，放电时间常数 τ=RC 越大，纹波越小。",
        preview_enabled=True,
        table_theory=get_table_theory("exp13"),
    )


def _read_params(payload):
    params = payload.get("parameters", {})
    return {
        "freq": as_number(params.get("freq")) or 400.0,
        "vpp": as_number(params.get("vpp")) or 10.0,
        "rl": as_number(params.get("rl")) or 1000.0,
        "r1": as_number(params.get("r1")) or 100.0,
    }


def preview(payload):
    """实时计算实测/理论纹波系数。"""
    tables = copied_tables(payload)
    params = _read_params(payload)

    for row in tables.get("table1", []):
        kind = str(row.get("c0", ""))
        c_uf = as_number(row.get("c1"))
        udc = as_number(row.get("c2"))
        uac = as_number(row.get("c3"))

        # 实测 Ku = U_AC / U_DC × 100
        if udc is not None and uac is not None and udc != 0:
            row["c4"] = formatted(uac / udc * 100, 4)
        else:
            row["c4"] = ""

        # 理论 Ku：按行内电路类型与电容值数值仿真
        if c_uf is not None and c_uf > 0:
            is_pi = ("π" in kind) or ("pi" in kind.lower())
            ku = _theory_ku("pi" if is_pi else "single", c_uf, params)
            row["c5"] = formatted(ku, 4) if ku is not None else ""
        else:
            row["c5"] = ""

    return {"tables": tables, "parameters": params}


# ─────────────────────────────────────────────
# 图表生成
# ─────────────────────────────────────────────
def _waveform_chart(params, workpath):
    """图 1：滤波波形对比（C = 1 μF，C1 = C2 = 1 μF）。"""
    up = params["vpp"] / 2.0
    c_f = 1e-6                               # 1 μF → F（标准对比基准）
    uin, u_single, u_pi = _simulate(
        up, params["freq"], params["rl"], c_f, c_f, c_f, params["r1"])
    t_ms = np.arange(_SIM_N) * (3.0 / params["freq"] / _SIM_N) * 1000

    zhfont = _zhfont()
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.plot(t_ms, uin, '--', color='#a0aec0', linewidth=1, label="全波整流（未滤波）")
    ax.plot(t_ms, u_single, color='#3182ce', linewidth=1.8, label="单电容滤波（1 μF）")
    ax.plot(t_ms, u_pi, color='#e53e3e', linewidth=1.8, label="π型RC滤波（1 μF）")
    ax.set_title("滤波电路输出波形对比（3 个周期数值仿真）", fontproperties=zhfont)
    ax.set_xlabel("t (ms)", fontproperties=zhfont)
    ax.set_ylabel("u (V)", fontproperties=zhfont)
    ax.grid(True, alpha=0.3)
    ax.legend(prop=zhfont, loc='upper right')
    imgpath = workpath + "chart_waveforms.png"
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


def _gamma_bar_chart(rows, workpath):
    """图 2：四种配置纹波系数对比（实测 vs 理论，分组柱状图）。"""
    labels, measured, theory = [], [], []
    for row in rows:
        kind = row.get("c0", "")
        c_val = row.get("c1", "")
        if not kind:
            continue
        labels.append(f"{kind}\n{c_val} μF")
        measured.append(as_number(row.get("c4")))
        theory.append(as_number(row.get("c5")))
    if not labels:
        return None

    zhfont = _zhfont()
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    width = 0.38
    m_vals = [v if v is not None else 0 for v in measured]
    t_vals = [v if v is not None else 0 for v in theory]
    bars1 = ax.bar(x - width / 2, t_vals, width, color='#dd6b20',
                   alpha=0.85, label="理论 Ku（数值仿真）")
    bars2 = ax.bar(x + width / 2, m_vals, width, color='#3182ce',
                   alpha=0.85, label="实测 Ku")
    for bars, vals in ((bars1, t_vals), (bars2, m_vals)):
        for rect, v in zip(bars, vals):
            if v:
                ax.annotate(f"{v:.1f}", (rect.get_x() + rect.get_width() / 2, v),
                            ha='center', va='bottom', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontproperties=zhfont)
    ax.set_title("纹波系数对比（实测与理论）", fontproperties=zhfont)
    ax.set_ylabel("Ku (%)", fontproperties=zhfont)
    ax.grid(True, axis='y', alpha=0.3)
    ax.legend(prop=zhfont)
    imgpath = workpath + "chart_ku_compare.png"
    fig.savefig(imgpath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return imgpath


def handle_structured(workpath, payload):
    enriched = dict(payload)
    preview_result = preview(payload)
    enriched["tables"] = preview_result["tables"]
    enriched["parameters"] = preview_result["parameters"]

    _schema = schema()
    params = enriched.get("parameters", {})
    rows = enriched["tables"].get("table1", [])
    charts = []

    # ── 图 1：滤波波形对比 ──
    img1 = _waveform_chart(params, workpath)
    if img1:
        charts.append({
            "filename": "chart_waveforms.png",
            "title": "滤波电路输出波形对比（C = 1 μF）",
            "url": img1,
        })

    # ── 图 2：纹波系数对比柱状图 ──
    img2 = _gamma_bar_chart(rows, workpath)
    if img2:
        charts.append({
            "filename": "chart_ku_compare.png",
            "title": "四种电路配置纹波系数对比（实测与理论）",
            "url": img2,
        })

    # ── 汇总 ──
    summary_lines = [
        f"整流滤波实验数据已处理（f = {params['freq']:g} Hz，"
        f"Vpp = {params['vpp']:g} V，RL = {params['rl']:g} Ω，"
        f"R1 = {params['r1']:g} Ω）：",
    ]
    by_key = {}
    for row in rows:
        kind = row.get("c0", "")
        c_val = row.get("c1", "")
        udc, uac = row.get("c2", ""), row.get("c3", "")
        kum, kut = row.get("c4", ""), row.get("c5", "")
        if not kind:
            continue
        by_key[(kind, str(c_val))] = (kum, kut)
        line = f"  {kind}（{c_val} μF）："
        line += f"U_DC={udc} V, U_AC={uac} V" if udc else "（未填实测值）"
        if kum:
            line += f"，实测 Ku = {kum}%"
        if kut:
            line += f"，理论 Ku = {kut}%"
        summary_lines.append(line)

    # 电容影响分析：单电容与 π 型的 1 μF → 10 μF 降幅
    def _drop(key_lo, key_hi):
        lo = by_key.get(key_lo)
        hi = by_key.get(key_hi)
        if not lo or not hi:
            return None
        lo_ku = as_number(lo[1] or lo[0])
        hi_ku = as_number(hi[1] or hi[0])
        if lo_ku and hi_ku and lo_ku > 0:
            return lo_ku, hi_ku, (lo_ku - hi_ku) / lo_ku * 100
        return None

    summary_lines.append("【电容对滤波效果的影响】")
    for label, keys in (("单电容滤波", (("单电容滤波", "1"), ("单电容滤波", "10"))),
                        ("π型滤波", (("π型RC滤波", "1"), ("π型RC滤波", "10")))):
        res = _drop(*keys)
        if res:
            lo_ku, hi_ku, drop_pct = res
            summary_lines.append(
                f"  {label}：电容从 1 μF 增大到 10 μF，纹波系数从 "
                f"{lo_ku:.1f}% 降至 {hi_ku:.1f}%，降低了 {drop_pct:.1f}%。")
    summary_lines.append(
        "原因：电容放电时间常数 τ = RL·C，C 增大则 τ 增大，"
        "电容放电更慢，纹波电压更小，输出更平滑。")

    return structured_result(
        workpath, name(), _schema, enriched,
        summary=summary_lines,
        charts=charts,
    )
