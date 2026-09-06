"""
LaTeX 实验报告生成模块
======================
将 AI 生成的实验报告编译为精美的 LaTeX PDF 文档。

流程：
1. AI 生成 LaTeX 格式的报告内容
2. 包装为完整的 .tex 文件（含中文支持、公式、表格等）
3. 调用 xelatex 编译为 PDF（用 XeTeX 引擎以支持 ctex 的 OpenType 中文字体，
   pdflatex 在 PDF 输出模式下无法使用 fandol 等中文字体集）
"""

import os
import re
import subprocess
import tempfile
import shutil
import time


# LaTeX 报告 System Prompt —— 已迁移至 prompts 包，按用途集中管理。
from prompts import LATEX_REPORT_SYSTEM_PROMPT


# ──────────────────────────────────────────────
# LaTeX 文档模板
# ──────────────────────────────────────────────
LATEX_PREAMBLE = r"""\documentclass[12pt,a4paper]{ctexart}

% 页面设置
\usepackage[margin=2.5cm]{geometry}
\usepackage{setspace}
\onehalfspacing

% 数学公式
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}

% 单位/符号（AI 常用 \degree \ohm \textcelsius 等，需提供来源）
% 优先加载 gensymb（提供 \degree \ohm \celsius 等），缺失时用 \providecommand 兜底，避免
% “Undefined control sequence”导致整篇 PDF 编译失败。
\IfFileExists{gensymb.sty}{\usepackage{gensymb}}{}
\IfFileExists{siunitx.sty}{\usepackage{siunitx}}{}
\providecommand{\degree}{^{\circ}}
\providecommand{\ohm}{\Omega}
\providecommand{\celsius}{^{\circ}\mathrm{C}}
\providecommand{\micro}{\mu}

% 表格
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{tabularx}
\usepackage{longtable}

% 图形（如有需要）
\usepackage{graphicx}
\usepackage{float}

% 超链接
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    citecolor=blue,
    urlcolor=blue
}

% 页眉页脚
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small 物理实验报告}
\fancyhead[R]{\small \thetitle}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% 段落设置
\setlength{\parindent}{2em}
\setlength{\parskip}{0.5em}

% 标题设置
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries\centering}{第\,\chinese{section}\,节}{1em}{}

"""

LATEX_TITLE_TEMPLATE = r"""
\title{{\textbf{{{title}}}}}
\author{{物理实验助教系统}}
\date{{\today}}

\begin{{document}}
\maketitle
\thispagestyle{{fancy}}

"""

LATEX_END = r"""
\end{document}
"""


def escape_latex(text):
    """转义 LaTeX 特殊字符（但保留已有的 LaTeX 命令和数学模式）"""
    if not text:
        return ""
    # 如果文本已经包含大量 LaTeX 命令，认为它是 LaTeX 格式，不做转义
    latex_indicators = [r'\section', r'\begin{', r'\frac', r'\sum', r'\alpha',
                        r'\beta', r'\gamma', r'\delta', r'\theta', r'\lambda',
                        r'\mu', r'\sigma', r'\omega', r'\pi', r'\times',
                        r'\cdot', r'\pm', r'\leq', r'\geq', r'\neq',
                        r'\overline', r'\sqrt', r'\bar']
    if any(ind in text for ind in latex_indicators):
        return text

    # 纯文本模式：转义特殊字符
    special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    result = text
    for char, replacement in special_chars.items():
        result = result.replace(char, replacement)
    return result


def build_latex_document(title, body_content):
    """将正文内容包装为完整的 LaTeX 文档

    参数:
        title: str, 报告标题（实验名称）
        body_content: str, AI 生成的 LaTeX 正文

    返回:
        str, 完整的 .tex 文件内容
    """
    # 清理正文开头可能多余的空白
    body_content = body_content.strip()

    # 如果 AI 不小心包含了 preamble，去掉它
    body_content = re.sub(r'\\documentclass.*?\{.*?\}', '', body_content)
    body_content = re.sub(r'\\usepackage.*?\{.*?\}', '', body_content)
    body_content = re.sub(r'\\begin\{document\}', '', body_content)
    body_content = re.sub(r'\\end\{document\}', '', body_content)

    document = LATEX_PREAMBLE
    document += LATEX_TITLE_TEMPLATE.format(title=escape_latex(title))
    document += body_content + "\n\n"
    document += LATEX_END

    return document


def _extract_latex_error(log):
    r"""从 xelatex 日志中提取首条可读错误，便于定位 AI 生成的 LaTeX 问题。

    日志里错误形如：
        ! Undefined control sequence.
        l.127 $\theta\,(\degree
                                  )$ ...
    或：
        ! Misplaced \noalign.
        l.69 \midrule
    这里把“! 错误标题”与紧随其后的 l.<行号> 上下文拼成一句话返回。
    """
    if not log:
        return None
    lines = log.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("!"):
            title = line[1:].strip()
            # 向后找最近的 l.<n> 行号上下文
            ctx = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                m = re.match(r"l\.(\d+)\s?(.*)", lines[j])
                if m:
                    ctx = f"（第 {m.group(1)} 行：{m.group(2).strip()[:80]}）"
                    break
            return f"PDF 编译失败：{title} {ctx}".strip()
    return None


def compile_latex_to_pdf(tex_content, output_dir, extra_search_dirs=None):
    """编译 LaTeX 文档为 PDF

    参数:
        tex_content: str, 完整的 .tex 文件内容
        output_dir: str, 输出目录（.tex 和 .pdf 保存位置）
        extra_search_dirs: list[str], 额外的图片/资源搜索目录（加入 TEXINPUTS）

    返回:
        dict: {
            "success": bool,
            "pdf_path": str or None,
            "tex_path": str or None,
            "log": str,
            "error": str or None
        }
    """
    # 查找 xelatex（用 XeTeX 引擎编译，ctex 的中文字体集在 pdfTeX+PDF 模式下不可用）
    latex_path = shutil.which("xelatex")
    if latex_path is None:
        # 尝试常见路径
        common_paths = [
            r"C:\Users\{}\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe",
            r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
            r"C:\texlive\2024\bin\windows\xelatex.exe",
            r"C:\texlive\2025\bin\windows\xelatex.exe",
        ]
        import getpass
        username = getpass.getuser()
        for p in common_paths:
            try:
                test_path = p.format(username)
                if os.path.exists(test_path):
                    latex_path = test_path
                    break
            except Exception:
                continue

        if latex_path is None:
            return {
                "success": False,
                "pdf_path": None,
                "tex_path": None,
                "log": "",
                "error": "未找到 xelatex，请确认已安装 TeX Live 或 MiKTeX（需包含 xelatex）"
            }

    # 创建临时工作目录
    work_dir = tempfile.mkdtemp(prefix="latex_", dir=output_dir)
    tex_path = os.path.join(work_dir, "report.tex")

    try:
        # 写入 .tex 文件
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        # 编译两次（确保引用正确）
        logs = []
        for i in range(2):
            result = subprocess.run(
                [latex_path,
                 "-interaction=nonstopmode",
                 "-halt-on-error",
                 "-output-directory", work_dir,
                 tex_path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=work_dir,
                env={**os.environ, "TEXINPUTS": os.pathsep.join(
                    [work_dir, output_dir] + (extra_search_dirs or []) + [''])}
            )
            logs.append(result.stdout)

            # 如果第一次编译失败，检查是否需要自动安装包
            if i == 0 and result.returncode != 0:
                # MiKTeX 自动安装包
                if "miktex" in latex_path.lower():
                    subprocess.run(
                        [latex_path,
                         "--configure",
                         "--auto-install=yes"],
                        capture_output=True,
                        timeout=60,
                        cwd=work_dir
                    )

        # 检查 PDF 是否生成
        pdf_path = os.path.join(work_dir, "report.pdf")
        if os.path.exists(pdf_path):
            # 将 PDF 复制到输出目录
            final_pdf = os.path.join(output_dir, "report.pdf")
            shutil.copy2(pdf_path, final_pdf)

            # 同时保留 .tex 源文件
            final_tex = os.path.join(output_dir, "report.tex")
            shutil.copy2(tex_path, final_tex)

            return {
                "success": True,
                "pdf_path": final_pdf,
                "tex_path": final_tex,
                "log": "\n".join(logs)[-2000:],  # 保留最后2000字符日志
                "error": None
            }
        else:
            full_log = "\n".join(logs)
            return {
                "success": False,
                "pdf_path": None,
                "tex_path": tex_path,
                "log": full_log[-2000:],
                "error": _extract_latex_error(full_log) or "PDF 编译失败，请检查 LaTeX 内容格式"
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "pdf_path": None,
            "tex_path": tex_path,
            "log": "",
            "error": "LaTeX 编译超时（超过120秒）"
        }
    except Exception as e:
        return {
            "success": False,
            "pdf_path": None,
            "tex_path": tex_path,
            "log": "",
            "error": str(e)
        }
    finally:
        # 清理临时工作目录
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
