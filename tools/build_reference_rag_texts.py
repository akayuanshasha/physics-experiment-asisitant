"""Build the three visually reviewed reference Markdown files.

This is an offline maintenance tool, not a runtime OCR/VLM integration.  It
extracts ordinary text with pdfplumber and adds formula/figure notes that were
verified against rendered PDF pages.  Browser uploads continue to use PyPDF2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = PROJECT_ROOT / "b_static" / "实验参考文档"


DOCUMENTS = (
    ("大雾实验不完全指北.pdf", "大雾实验不完全指北_RAG文本.md", "大雾实验不完全指北"),
    ("一级大雾出入门测.pdf", "一级大雾出入门测_RAG文本.md", "一级大雾出入门测"),
    ("二级大雾出入门测11.7.pdf", "二级大雾出入门测11.7_RAG文本.md", "二级大雾出入门测11.7"),
)


GUIDE_NOTES = {
    26: [
        "本页含费曼图示例。图中的典型顶点因子为 $-iZe\\gamma^\\mu$，光子传播子写作 $-ig_{\\mu\\nu}/(q^2+i\\varepsilon)$。",
    ],
    27: ["本页为球面折射示意图，主要角度标记为 $\\theta_i$、$\\theta_f$、$\\phi$、$\\psi$。"],
    31: [
        "(2.1) $Y=f(X_1,X_2,\\ldots,X_N)$。",
        "(2.2) $y=f(x_1,x_2,\\ldots,x_N)$。",
        "(2.3) $u_A=\\sigma_{\\bar{x}}/\\sqrt{n}=\\sqrt{\\frac{\\sum_{i=1}^{n}(x_i-\\bar{x})^2}{n(n-1)}}$。",
    ],
    32: [
        "(2.4) $u_x=a/k_p$。",
        "(2.5) $u_x=U_x/k$。",
        "(2.6) $u_x=a/\\sqrt{3}$。",
        "(2.7) $u_c^2(y)=\\sum_{i=1}^{N}\\left(\\frac{\\partial f}{\\partial x_i}\\right)^2u^2(x_i)=\\sum_{i=1}^{N}c_i^2u^2(x_i)$。",
        "(2.8) $\\left(\\frac{u_c(y)}{y}\\right)^2=\\sum_{i=1}^{N}\\left(\\frac{\\partial\\ln f}{\\partial x_i}\\right)^2u^2(x_i)$。",
    ],
    33: [
        "(2.9) $u_c^4(y)/\\nu_{\\mathrm{eff}}=\\sum_{i=1}^{N}u_i^4(y)/\\nu_i$。",
        "(2.10) $\\nu_{\\mathrm{eff}}=u_c^4(y)\\left/\\sum_{i=1}^{N}\\frac{u_i^4(y)}{\\nu_i}\\right.$。",
        "$u_c^2(y)=\\sum_i u_i^2(y)$；$U_p(y)=k_pu_c(y)=t_p(\\nu_{\\mathrm{eff}})u_c(y)$；结果写作 $Y=y\\pm U_p$。",
        "(2.11) $Y=y\\pm U=(100.02147\\pm0.00079)\\,\\mathrm{g},\\ P=0.95$。",
    ],
    34: [
        "(2.12) $y=b+kx+e$；(2.13) $\\hat y=\\hat b+\\hat kx$。",
        "(2.14) $\\hat k=\\frac{\\sum_i(x_i-\\bar x)(y_i-\\bar y)}{\\sum_i(x_i-\\bar x)^2}$；(2.15) $\\hat b=\\bar y-\\hat k\\bar x$。",
        "(2.16) $r=\\frac{\\overline{xy}-\\bar x\\bar y}{\\sqrt{(\\overline{x^2}-\\bar x^2)(\\overline{y^2}-\\bar y^2)}}$。",
        "(2.17) $u_k=k\\sqrt{\\frac{1/r^2-1}{n-2}}$；(2.18) $u_b=\\sqrt{\\overline{x^2}}u_k$；(2.19) $U_k=t_pu_k,\\ U_b=t_pu_b$。",
    ],
    35: [
        "(2.20) $V=\\pi D^2h/4=806.8\\,\\mathrm{mm^3}$。",
        "(2.21) $\\sigma_D=\\sqrt{\\frac{\\sum_{i=1}^{6}(D_i-\\bar D)^2}{6(6-1)}}=0.0048\\,\\mathrm{mm}$。",
        "(2.22) $\\sigma_h=\\sqrt{\\frac{\\sum_{i=1}^{6}(h_i-\\bar h)^2}{6(6-1)}}=0.0018\\,\\mathrm{mm}$。",
        "$u_3=0.01/\\sqrt{3}=0.0058\\,\\mathrm{mm}$。",
        "(2.23) $u_c=\\sqrt{(\\partial V/\\partial D)^2u_D^2+(\\partial V/\\partial h)^2u_h^2+[(\\partial V/\\partial D)^2+(\\partial V/\\partial h)^2]u_3^2}=1.3\\,\\mathrm{mm^3}$。",
        "(2.24) $\\nu=\\frac{u_c^4}{(\\partial V/\\partial D)^4u_D^4/\\nu_D+(\\partial V/\\partial h)^4u_h^4/\\nu_h+[(\\partial V/\\partial D)^2+(\\partial V/\\partial h)^2]^2u_3^4/\\nu_3}=40.92$。",
    ],
    36: [
        "(2.25) $U=ku_c=2.02\\times1.3\\,\\mathrm{mm^3}=2.6\\,\\mathrm{mm^3}$。",
        "(2.26) $V=(806.8\\pm2.6)\\,\\mathrm{mm^3},\\ P=0.95$。",
    ],
    37: [
        "(2.27) $U_p=\\sqrt{U_A^2+U_B^2}=\\sqrt{(t_pu_A)^2+(k_pu_B)^2}$。",
        "本页还列出分量合成形式 $u_c^2(y)=\\sum_i u_i^2(y)$、$U_p=t_p(\\nu_{\\mathrm{eff}})u_c$，以及 $\\nu_{\\mathrm{eff}}\\leq\\sum_i\\nu_i$。",
    ],
    39: [
        "$g=4\\pi^2l/T^2$。",
        "最大相对误差表达式为 $\\Delta g/g=2\\Delta T/T+\\Delta l/l$。",
    ],
    40: ["参考量：$g=9.7947\\,\\mathrm{m/s^2}$，$E\\approx2\\times10^{11}\\,\\mathrm{Pa}$。"],
    41: [
        "光栅关系写作 $k\\lambda l=ax_k$，也写作 $k\\lambda l=dx_k$。",
        "缺级条件为 $n/k=d/a$。",
    ],
    42: [
        "$U=E\\alpha\\Delta t$。",
        "数字温度计关系式为 $U=E_0\\Delta t/4$。",
        "扭摆关系式：$D=4\\pi^2I_0/T_0^2$，$G=2DL/(\\pi R^4)$。",
    ],
    43: [
        "$D=\\frac{2\\pi^2m(r_{\\mathrm{in}}^2+r_{\\mathrm{out}}^2)}{T_1^2-T_0^2}$。",
        "$G=\\frac{4\\pi Lm(r_{\\mathrm{in}}^2+r_{\\mathrm{out}}^2)}{R^4(T_1^2-T_0^2)}$。",
        "$\\Delta G/G=\\Delta L/L+\\Delta m/m+4\\Delta R/R+\\frac{2r_{\\mathrm{in}}\\Delta r_{\\mathrm{in}}+2r_{\\mathrm{out}}\\Delta r_{\\mathrm{out}}}{r_{\\mathrm{in}}^2+r_{\\mathrm{out}}^2}+\\frac{2T_0\\Delta T_0+2T_1\\Delta T_1}{T_1^2-T_0^2}$。",
        "判据分别为 $\\frac{2T_0\\Delta T_0}{T_1^2-T_0^2}<\\frac15\\frac{4\\Delta R}{R}$ 和 $\\frac{2T_1\\Delta T_1}{T_1^2-T_0^2}<\\frac15\\frac{4\\Delta R}{R}$。",
        "资料校正说明（优先于 PDF 原文单位）：PDF 将 $D=(5.39\\pm0.09)\\times10^{-3}$ 的单位印为 $\\mathrm{Pa}$；由 $D=4\\pi^2I_0/T_0^2$ 的量纲可知，$D$ 的正确单位应为 $\\mathrm{N\\cdot m}$。$G=(6.69\\pm0.16)\\times10^{10}\\,\\mathrm{Pa}$ 的单位 $\\mathrm{Pa}$ 正确，$P=0.95$。",
    ],
    47: ["参考量：$k=1.1580\\,\\mathrm{N/m}$，$\\sigma=(0.066\\pm0.004)\\,\\mathrm{N/m}$，洗涤剂表面张力为 $0.02938\\,\\mathrm{N/m}$。"],
    53: [
        "杨氏模量关系式：$m=\\frac{\\pi d^2E}{4gL}\\Delta l$。",
        "本页给出的参考量为 $E=1.720\\times10^{11}\\,\\mathrm{Pa}$、$\\mu=0.279$。",
    ],
    55: ["本页主要是一张板书照片（图 3.10）；其内容仅作实验分析示例，正文没有给出可独立引用的完整公式。"],
    56: ["三线摆关系式：$I_0=\\frac{m_0gRr}{4\\pi^2H}T_0^2$。"],
    57: ["参考量：$R_H=-5\\times10^{-3}\\,\\mathrm{m^3/C}$，$\\mu=7.8\\,\\mathrm{m^2/(V\\cdot s)}$；临界条件 $\\mu B=1$。"],
    58: ["马吕斯定律曲线：$I/I_0\\sim\\cos^2\\theta$。"],
    59: ["光密度定义：$O.D.=\\lg(I_0/I)$。"],
    60: ["参考量：$T_e\\approx5\\times10^4\\,\\mathrm{K}$，$S\\approx7\\times10^{-5}\\,\\mathrm{m^3/s}$。"],
    61: ["表面等离激元条件：$n_p\\sin\\theta_{sp}=\\sqrt{\\frac{\\operatorname{Re}(\\varepsilon_m)n_s^2}{\\operatorname{Re}(\\varepsilon_m)+n_s^2}}$。"],
    63: ["朗德因子参考值：$g\\approx2$。"],
}


LEVEL1_NOTES = {
    7: ["本页量值包括 $0.123\\,\\mathrm{V}$、摆长 $85.32\\,\\mathrm{cm}$、周期 $1.854\\,\\mathrm{s}$，以及 $(1.794\\pm0.054)\\,\\mathrm{s}$。"],
    8: ["流体静力称衡法密度关系：$\\rho=\\frac{m}{V}=\\frac{m}{m-m_1}\\rho_0$。"],
    9: ["题干原式使用小写 $v$ 写作 $\\rho=m/v$，并将该陈述判为错误；此处按题面保留，不自动改成大写 $V$。"],
    13: ["匀加速运动关系：$2as=v^2-v_0^2$。"],
    15: ["耦合振动中两线圈中点磁场相等的几何条件为 $R=d$。"],
    23: ["整流滤波题中的输入量为 $U_p=5.00\\,\\mathrm{V}$、$U_{p-p}=10.00\\,\\mathrm{V}$。"],
    26: ["非平衡电桥条件写作 $\\Delta R_c/R_c\\ll1$。"],
    27: ["李萨如图形中频率记为 $f_x$、$f_y$，切线斜率绝对值之比为 $f_y/f_x$；示例为 $f_x=1200\\,\\mathrm{Hz}$、$f_y=800\\,\\mathrm{Hz}$。"],
    29: [
        "光子能量写作 $Nh\\nu$。",
        "硅光电池填充因子：$FF=\\frac{U_mI_m}{U_{oc}I_{sc}}$。",
    ],
    34: ["高斯成像公式中的 $p$、$p'$ 均按正值处理。"],
    41: [
        "艾里斑半径：$r=1.22\\lambda f/D$。",
        "单缝衍射第 $k$ 级暗纹角：$\\phi_k=x_k/L$；双缝条件写作 $d\\cos\\phi=n\\lambda$ 与 $a\\cos\\phi=k\\lambda$。",
    ],
    44: [
        "爱因斯坦光电方程对应的图示关系为 $E_k=h\\nu-W_0$，截止频率满足 $\\nu_0=W_0/h$。",
        "遏止电压关系可写为 $eU_c=h\\nu-W_0$。",
    ],
    45: ["本页比较波长 $\\lambda$ 与 $3\\lambda/4$ 的光电子最大初动能，并给出比值 $1:2$。"],
    46: [
        "题目量值：$\\lambda_0=500\\,\\mathrm{nm}$、$\\lambda=300\\,\\mathrm{nm}$、$U=2.1\\,\\mathrm{V}$、$I=0.56\\,\\mathrm{mA}$。",
        "答案校正说明（优先于 PDF 答案行）：第一问为 $I/e=3.5\\times10^{15}$ 个/秒；第二问最大动能为 $6.01\\times10^{-19}\\,\\mathrm{J}$；第三问光强增至三倍时最大动能不变，仍为 $6.01\\times10^{-19}\\,\\mathrm{J}$。PDF 已用橙色注记更正第一问；PDF 答案行把第二问的单位写成 $\\mathrm{C}$，属于单位笔误。",
    ],
    48: ["密立根油滴实验选择 $q\\leq6e_0$ 的油滴，静止平衡电压范围为 $100\\sim300\\,\\mathrm{V}$。"],
    50: ["量值示例：$10^{-5}\\sim10^{-3}\\,\\mathrm{cm}$，$\\rho=(8.095\\pm0.014)\\,\\mathrm{g/cm^3}$。"],
    53: ["本页再次给出密度结果 $\\rho=(8.095\\pm0.014)\\,\\mathrm{g/cm^3}$。"],
}


LEVEL2_NOTES = {
    2: ["显微实验尺度量级为 $10\\,\\mu\\mathrm{m}$。"],
    4: ["磁阻效应：弱磁场下 $\\Delta R/R(0)\\propto B^2$，强磁场下近似呈线性。"],
    5: ["电阻量值为 $(390000\\pm3900)\\,\\Omega$；迈克耳孙干涉仪中反射镜移动距离是光程差的一半。"],
    9: ["电桥平衡时 $I_G=0$，$R_x=(R/R_1)R_n$；本页另写有 $R_x=V/I$。"],
    14: ["马吕斯定律：$I=I_0\\cos^2\\theta$。原 PDF 此处使用了 LaTeX 风格的普通文本。"],
    28: ["线性关系写作 $U=BT+U_{g0}$；热敏电阻作图变量为 $\\ln R_T$ 对 $1/T$。"],
    29: ["线性度：$\\delta=\\Delta Y_{\\max}/Y\\times100\\%$。"],
    30: ["RLC 题给定 $U=20\\,\\mathrm{V}$、$\\omega=100\\,\\mathrm{rad/s}$、$R=10\\,\\Omega$、$L=2\\,\\mathrm{H}$；答案为 $C=50\\,\\mu\\mathrm{F}$、电压 $400\\,\\mathrm{V}$。"],
    31: ["串联谐振条件：$\\omega L=1/(\\omega C)$。"],
    32: ["导热系数单位：$\\mathrm{W/(m\\cdot K)}$。"],
}


NOTE_MAPS = {
    "大雾实验不完全指北.pdf": GUIDE_NOTES,
    "一级大雾出入门测.pdf": LEVEL1_NOTES,
    "二级大雾出入门测11.7.pdf": LEVEL2_NOTES,
}


def _clean_page_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\(cid:\d+\)", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            if cleaned and cleaned[-1]:
                cleaned.append("")
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def build_document(pdf_name: str, markdown_name: str, title: str) -> tuple[Path, int]:
    pdf_path = REFERENCE_ROOT / pdf_name
    output_path = REFERENCE_ROOT / markdown_name
    notes = NOTE_MAPS[pdf_name]
    with pdfplumber.open(pdf_path) as document:
        pages = [_clean_page_text(page.extract_text() or "") for page in document.pages]

    output = [
        "<!-- rag-extracted: v1 -->",
        f"<!-- 实验名称: {title} -->",
        f"<!-- 源文件: {pdf_name} -->",
        "<!-- 抽取器: pdfplumber + 页面图像视觉校验 -->",
        "<!-- 人工确认: true（逐页正文已收录，公式候选页已完成视觉校验） -->",
        "<!-- 生成时间: 2026-09-05 -->",
        "<!-- 清洗记录: 删除 PDF 内部 cid 占位符；保留原文判断与答案；规范公式另列于对应页面。 -->",
        "",
        f"# {title}",
        "",
    ]
    for page_number, page_text in enumerate(pages, start=1):
        output.extend((f"<!-- 页码:{page_number} -->", ""))
        if page_text:
            output.extend((page_text, ""))
        else:
            output.extend(("[本页没有可提取的正文文本。]", ""))
        page_notes = notes.get(page_number)
        if page_notes:
            output.extend(("### 视觉校验公式与图示", ""))
            output.extend(f"- {note}" for note in page_notes)
            output.append("")

    output_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    return output_path, len(pages)


def main() -> None:
    for pdf_name, markdown_name, title in DOCUMENTS:
        path, page_count = build_document(pdf_name, markdown_name, title)
        print(f"{path.name}: {page_count} pages")


if __name__ == "__main__":
    main()
