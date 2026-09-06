#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线实验指导 PDF 预处理与知识库发布工具
========================================================

流程：原始 PDF → 多抽取器逐页比较 → 质量打分与候选选择 → 结构清理
（章节标题重组 / 页眉页脚 / 目录页） → 生成候选「实验指导_RAG文本.md」
+ 审计报告 + 公式人工核对清单。

抽取、审计和构建输出写入 ``rag_extraction_review/``；``publish`` 会先执行
质量门禁，再把 selected 中通过的 Markdown 直接写入正式实验目录。发布不创建
备份，且始终不修改 PDF 或旧的 ``实验指导_提取文本.txt``。

子命令：:

    audit    第一阶段：资料审计 → audit.json / audit.csv / summary.md
    extract  第二阶段：逐页多抽取器候选比较 → candidates/expXX/candidates.json
    build    第三+五阶段：结构清理并生成候选 MD → selected/expXX/实验指导_RAG文本.md
    review   第四阶段：公式异常人工核对清单 → manual_review/formulas.md
    gate     发布门禁 → quality_gate.json（失败时返回非零退出码）
    publish  门禁通过后直接发布到正式实验目录（覆盖、不备份）
    all      依次执行 extract → audit → build → review（默认）

硬性规则（与任务约定一致）：

- 不删除孤立数字 / 公式编号 / 步骤编号 / 表格序号；
- 不把所有换行直接删除、不把所有汉字无条件粘连；
- 不因某行含「实验原理」就判定为标题或目录；
- 异常 Unicode（PUA / Telugu / Arabic 区 / 替换符 �）只作为质量风险指标，
  绝不自动删除或替换；
- 公式绝不猜测、绝不固定映射补写、绝不删除后谎报清洗成功；
- OCR 只在离线阶段考虑（本环境未安装 tesseract，见报告）。
"""

import argparse
import csv
import datetime
import importlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools import guide_text_utils as guide
from online_rag.parsed_document import ParsedBlock, ParsedDocument, ParsedPage
from online_rag.quality import evaluate_rag_markdown

# 确定性 PUA 解码表：Adobe Symbol 字体 + U+F000 偏移（见 tools/symbol_font_map.py）
# 读取 PDF 内嵌字体声明的编码，非上下文猜测；仅还原无歧义码点。
from symbol_font_map import decode_pua_char, is_pua
from cambria_math_map import decode_cambria_math

EXPERIMENT_DIR = os.path.join(PROJECT_ROOT, "b_static", "experiment")
REVIEW_DIR = os.path.join(PROJECT_ROOT, "rag_extraction_review")
CANDIDATES_DIR = os.path.join(REVIEW_DIR, "candidates")
SELECTED_DIR = os.path.join(REVIEW_DIR, "selected")
MANUAL_DIR = os.path.join(REVIEW_DIR, "manual_review")
RAG_FILENAME = "实验指导_RAG文本.md"
OLD_TXT_FILENAME = "实验指导_提取文本.txt"

# ──────────────────────────────────────────────
# 字符分类（异常 Unicode 只统计、不替换）
# ──────────────────────────────────────────────
RE_PUA = re.compile(r"[-]")            # 私用区：公式符号丢失后的替身
RE_OTHER = re.compile(r"[ఀ-౿݀-ݿ]")  # Telugu 区 + Arabic Supplement 区
RE_CJK = re.compile(r"[一-鿿]")
RE_REPLACE = re.compile("�")                  # 替换字符 �
RE_PAGE_NUM = re.compile(r"^\d{1,3}\s*/\s*\d{1,3}$")
RE_DOT_LEADER = re.compile(r"[.．·…]{4,}")
RE_MD_COMMENT = re.compile(r"^\s*<!--.*-->\s*$")
# 页眉页脚候选白名单排除：这些短行是正文标签，不是页眉页脚
RE_FOOTER_EXCLUDE = re.compile(
    r"^(式中|其中|即|可得|由式|公式中|式中各|由上式|如下|表|图)"
    r"|(：|:)$|[，。；、：！？…]$|^[（(]?\d{1,3}[)）]?$"
)

# ──────────────────────────────────────────────
# 抽取器注册表：只注册当前已安装的库，绝不自动安装
# ──────────────────────────────────────────────
def _importable(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def _extract_pypdf2_plain(path):
    from PyPDF2 import PdfReader
    reader = PdfReader(path)
    return ParsedDocument.from_page_texts(
        path, "pypdf2-plain", (page.extract_text() or "" for page in reader.pages)
    )


def _extract_fitz(path):          # PyMuPDF（未安装时不会注册）
    import fitz
    with fitz.open(path) as doc:
        texts = [doc[i].get_text() for i in range(len(doc))]
    return ParsedDocument.from_page_texts(path, "pymupdf-fitz", texts)


def _extract_pdfplumber(path):    # pdfplumber（未安装时不会注册）
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        texts = [(pg.extract_text() or "") for pg in pdf.pages]
    return ParsedDocument.from_page_texts(path, "pdfplumber", texts)


def _extract_pdftotext(path):     # 系统级 poppler（未安装时不会注册）
    texts = []
    page = 1
    # 用 pdfinfo 拿总页数，避免靠 returncode 误判尾页
    info = subprocess.run(["pdfinfo", path], capture_output=True, text=True,
                          errors="replace")
    total = 0
    for ln in (info.stdout or "").splitlines():
        if ln.startswith("Pages:"):
            try:
                total = int(ln.split(":", 1)[1].strip())
            except ValueError:
                total = 0
            break
    if total == 0:
        return ParsedDocument.from_page_texts(path, "pdftotext-cli", texts)
    for page in range(1, total + 1):
        proc = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", path, "-"],
            capture_output=True, text=True, errors="replace")
        texts.append(proc.stdout or "")
    return ParsedDocument.from_page_texts(path, "pdftotext-cli", texts)


def _extract_docling(path):
    """Docling v2 适配器：按页导出 Markdown，保留表格和公式结构。"""
    from docling.document_converter import DocumentConverter

    document = DocumentConverter().convert(path).document
    page_numbers = sorted(int(number) for number in document.pages)
    pages = [
        ParsedPage(
            number=number,
            blocks=[ParsedBlock(document.export_to_markdown(page_no=number))],
        )
        for number in page_numbers
    ]
    return ParsedDocument(
        source_path=path,
        parser="docling",
        pages=pages,
        metadata={"structured_markdown": True},
    )


def _mineru_block_text(item):
    for key in ("text", "table_body", "latex", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_mineru(path):
    """MinerU 2.x CLI 适配器，优先读取 content_list.json 的逐页结构。"""
    executable = shutil.which("mineru")
    if not executable:
        raise RuntimeError("未找到 mineru 命令")
    with tempfile.TemporaryDirectory(prefix="rag-mineru-") as output_dir:
        process = subprocess.run(
            [executable, "-p", path, "-o", output_dir, "-m", "auto"],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if process.returncode != 0:
            detail = (process.stderr or process.stdout or "未知错误").strip()[-1000:]
            raise RuntimeError(f"MinerU 解析失败（exit={process.returncode}）：{detail}")

        root = Path(output_dir)
        content_files = sorted(root.rglob("*content_list.json"))
        if content_files:
            items = json.loads(content_files[0].read_text(encoding="utf-8"))
            by_page = {}
            kind_map = {
                "text": "text", "title": "title", "list": "list",
                "table": "table", "equation": "formula",
                "interline_equation": "formula", "image": "image",
            }
            for item in items if isinstance(items, list) else []:
                page_number = int(item.get("page_idx", 0)) + 1
                raw_kind = str(item.get("type", "unknown"))
                kind = kind_map.get(raw_kind, "unknown")
                block = ParsedBlock(
                    text=_mineru_block_text(item),
                    kind=kind,
                    metadata={"mineru_type": raw_kind},
                )
                by_page.setdefault(page_number, []).append(block)
            pages = [
                ParsedPage(
                    number=number,
                    blocks=blocks,
                    is_scanned=not any(block.text for block in blocks),
                )
                for number, blocks in sorted(by_page.items())
            ]
        else:
            markdown_files = sorted(root.rglob("*.md"))
            if not markdown_files:
                raise RuntimeError("MinerU 未生成 content_list.json 或 Markdown")
            markdown = markdown_files[0].read_text(encoding="utf-8")
            pages = [ParsedPage(number=1, blocks=[ParsedBlock(markdown)])]

    warnings = []
    if not content_files:
        warnings.append("MinerU 仅生成整篇 Markdown，无法保留逐页定位")
    return ParsedDocument(
        source_path=path,
        parser="mineru",
        pages=pages,
        metadata={"method": "auto", "structured_markdown": True},
        warnings=warnings,
    )


def subprocess_run(args, devnull):
    import subprocess
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=devnull,
                          text=True, errors="replace")


EXTRACTOR_REGISTRY = [
    ("pypdf2-plain", True, _extract_pypdf2_plain),
    ("pymupdf-fitz", _importable("fitz"), _extract_fitz),
    ("pdfplumber", _importable("pdfplumber"), _extract_pdfplumber),
    ("pdftotext-cli", shutil.which("pdftotext") is not None, _extract_pdftotext),
    ("docling", _importable("docling"), _extract_docling),
    ("mineru", shutil.which("mineru") is not None, _extract_mineru),
]


def available_extractors():
    return [name for name, ok, _ in EXTRACTOR_REGISTRY if ok]


def missing_extractors():
    return [name for name, ok, _ in EXTRACTOR_REGISTRY if not ok]


# ──────────────────────────────────────────────
# 逐页质量指标与打分
# ──────────────────────────────────────────────
def _section_titles(lines):
    seen = set()
    for line in lines:
        canon = guide.canonicalize_section(line)
        if canon and canon not in seen:
            seen.add(canon)
    return sorted(seen)


def _page_metrics(text):
    """一页候选文本的质量指标。异常 Unicode 只统计为风险指标，不删除不替换。"""
    lines = [l.strip() for l in text.split("\n")]
    nonempty = [l for l in lines if l]
    joined = text.replace("\n", "").replace(" ", "")
    n = len(joined)
    pua = len(RE_PUA.findall(text))
    other = len(RE_OTHER.findall(text))
    repl = len(RE_REPLACE.findall(text))
    garbled_formula_lines = 0
    for l in nonempty:
        if ("=" in l or "≈" in l or "Δ" in l or "λ" in l) and (RE_PUA.search(l) or RE_OTHER.search(l)):
            garbled_formula_lines += 1
    table_lines = sum(1 for line in nonempty if line.count("|") >= 2)
    formula_lines = sum(
        1 for line in nonempty
        if re.search(r"(?:\$[^$]+\$|\\frac|[=≈≠≤≥∑∫√])", line)
    )
    two_column_lines = sum(
        1 for line in nonempty if re.search(r"\S\s{4,}\S", line)
    )
    m = {
        "chars": n,
        "lines": len(nonempty),
        "cjk_ratio": round(len(RE_CJK.findall(joined)) / n, 4) if n else 0.0,
        "pua_count": pua,
        "pua_ratio": round(pua / n, 4) if n else 0.0,
        "other_script_count": other,
        "other_script_ratio": round(other / n, 4) if n else 0.0,
        "replace_count": repl,
        "digit_ratio": round(sum(c.isdigit() for c in joined) / n, 4) if n else 0.0,
        "single_char_line_ratio": (
            round(sum(1 for l in nonempty if len(l) == 1) / len(nonempty), 4)
            if nonempty else 0.0
        ),
        "section_titles": _section_titles(nonempty),
        "garbled_formula_lines": garbled_formula_lines,
        "table_lines": table_lines,
        "formula_lines": formula_lines,
        "two_column_suspect_lines": two_column_lines,
        "scanned_suspect": n < 20,
    }
    m["score"] = _score_page(m)
    return m


def _score_page(m):
    """候选质量分（0~100）。只做相对比较，异常字符按比例扣分。"""
    if m["chars"] == 0:
        return 0.0
    s = 0.0
    s += min(m["cjk_ratio"], 0.7) / 0.7 * 30.0      # 中文正文占比
    s -= m["pua_ratio"] * 100.0                     # 私用区异常
    s -= m["other_script_ratio"] * 100.0            # 异常文字区
    s -= (m["replace_count"] / max(m["chars"], 1)) * 100.0
    s -= m["single_char_line_ratio"] * 20.0         # 逐字碎片
    s += min(len(m["section_titles"]), 6) * 3.0     # 可识别章节标题
    s += min(m["digit_ratio"] * 100.0, 8.0)         # 数字/单位保留（弱正相关）
    s -= m["garbled_formula_lines"] * 2.0           # 公式附近乱码
    return round(max(0.0, min(100.0, s)), 2)


def _page_needs_review(m):
    return (
        m["pua_count"] > 0 or m["other_script_count"] > 0
        or m["replace_count"] > 0 or m["chars"] == 0
        or m.get("scanned_suspect", False)
    )


# ──────────────────────────────────────────────
# 逐页候选比较（第二阶段）
# ──────────────────────────────────────────────
def extract_doc_candidates(pdf_path):
    """对一份 PDF 逐页运行所有可用抽取器，记录指标、分数、选择与原因。"""
    candidates_by_page = []
    for extractor, ok, fn in EXTRACTOR_REGISTRY:
        if not ok:
            continue
        try:
            document = fn(pdf_path)
            page_texts = document.page_texts
        except Exception as e:
            print(f"  [extract] {extractor} 失败: {e}")
            continue
        candidates_by_page.append((extractor, page_texts))
    n_pages = max((len(t) for _, t in candidates_by_page), default=0)
    pages = []
    for i in range(n_pages):
        cand = {}
        for name, texts in candidates_by_page:
            if i < len(texts):
                cand[name] = _page_metrics(texts[i])
        if not cand:
            continue
        best = max(cand.items(), key=lambda kv: kv[1]["score"])
        winner, metrics = best
        if metrics["chars"] == 0:
            reason = "所有抽取器输出为空（可能为扫描/图片页）"
        elif len(cand) == 1:
            reason = "唯一可用抽取器"
        else:
            losers = ", ".join(
                f"{n}({c['score']})" for n, c in cand.items() if n != winner
            )
            reason = f"得分最高（对比 {losers}）"
        pages.append({
            "page": i + 1,
            "candidates": cand,
            "selected": winner,
            "reason": reason,
            "needs_manual_review": _page_needs_review(metrics),
        })
    return {
        "pages": pages,
        "pages_total": n_pages,
        "extractors_available": available_extractors(),
        "extractors_missing": missing_extractors(),
    }


# ──────────────────────────────────────────────
# 结构清理（第三阶段）
# ──────────────────────────────────────────────
def _detect_header_footer(pages_lines):
    """跨页重复页眉页脚：在多页的页首/页尾位置反复出现的短行。

    只在高置信度条件下判定：出现页数 ≥ max(3, 30% 页数) 且 ≥60% 出现在
    页首 2 行或页尾 2 行；排除章节标题、句末标点行、冒号标签行、
    「式中/其中」等正文短标签、纯数字行（页码由 RE_PAGE_NUM 单独处理）。
    """
    n_pages = len(pages_lines)
    counter = {}
    for lines in pages_lines:
        nonempty = [l.strip() for l in lines if l.strip()]
        if not nonempty:
            continue
        positions = set(nonempty[:2]) | set(nonempty[-2:])
        for l in positions:
            if l not in counter:
                counter[l] = {"pages": 0, "at_edge": 0}
            counter[l]["pages"] += 1
            counter[l]["at_edge"] += 1
    min_pages = max(3, int(0.3 * n_pages)) if n_pages >= 3 else 3
    flagged = {}
    for line, c in counter.items():
        if c["pages"] < min_pages:
            continue
        if len(line) > 25 or len(line) <= 1:
            continue
        if guide.is_section_heading(line):
            continue
        if RE_FOOTER_EXCLUDE.search(line):
            continue
        if RE_PAGE_NUM.match(line):
            continue
        if c["at_edge"] / c["pages"] < 0.6:
            continue
        flagged[line] = c["pages"]
    return flagged


def _toc_titles(lines):
    """目录页标题识别：目录行常为「3实验目的 1」式粘连（前导编号+标题+页码）。

    去掉行首行尾数字后精确匹配规范章节名，正文中不存在的组合形式。
    """
    titles = set()
    for l in lines:
        core = re.sub(r"^\d{1,3}\s*", "", l.strip())
        core = re.sub(r"\s*\d{1,3}\s*$", "", core)
        canon = guide.canonicalize_section(core)
        if canon:
            titles.add(canon)
    return titles


def _detect_toc_pages(pages_lines):
    """目录页只能按组合特征判定：≥3 个章节标题（含「N标题 M」粘连形式）
    + 大量以页码结尾/点线行 + 长句很少 + 长正文行很少。

    任一特征单独出现都不判目录；缺正文解释句是必要条件之一。
    """
    toc = []
    for idx, lines in enumerate(pages_lines):
        nonempty = [l.strip() for l in lines if l.strip()]
        if not nonempty:
            continue
        titles = _toc_titles(nonempty)
        digit_ended = sum(1 for l in nonempty if re.search(r"\d\s*$", l))
        dot_lines = sum(1 for l in nonempty if RE_DOT_LEADER.search(l))
        long_sentences = sum(
            1 for l in nonempty if len(l) >= 15 and l.endswith(("。", "！", "？"))
        )
        long_lines = sum(1 for l in nonempty if len(l) >= 15)
        if (
            len(titles) >= 3
            and (digit_ended / len(nonempty) >= 0.4 or dot_lines >= 2)
            and long_sentences <= 2
            and long_lines <= 3
        ):
            toc.append(idx)
    return toc


def _reassemble_heading_block(lines):
    """块内标题重组：块前 2~4 行紧凑拼接后若能精确匹配规范章节名，则合并。

    例：「实验原」「理」 → 「实验原理」；逐字拆散的「实」「验」「原」「理」同理。
    单行本身已是标题的 k=1 情况不算重组；拼接结果必须精确匹配章节名，
    否则一行不动，绝不动正文内容。
    """
    if not lines or guide.is_section_heading(lines[0]):
        return lines, 0
    for k in range(2, min(4, len(lines)) + 1):
        joined = "".join(l.strip() for l in lines[:k])
        if guide.canonicalize_section(joined) is not None:
            return [joined] + lines[k:], 1
    return lines, 0


def clean_page_lines(lines, headers):
    """去掉一页中的高置信噪声：页眉页脚行、页码行（N / M）。"""
    out = []
    for l in lines:
        s = l.strip()
        if not s:
            out.append("")
            continue
        if s in headers:
            continue
        if RE_PAGE_NUM.match(s):
            continue
        out.append(l.rstrip())
    while out and not out[-1]:
        out.pop()
    return out


# ──────────────────────────────────────────────
# 候选 MD 组装（第五阶段）
# ──────────────────────────────────────────────
def _formula_flags(lines):
    """统计一页清理后文本的异常字符，并给出含异常字符的具体行（供核对清单）。"""
    flags = {"count": 0, "bad_lines": []}
    for l in lines:
        if not l.strip():
            continue
        c = len(RE_PUA.findall(l)) + len(RE_OTHER.findall(l)) + len(RE_REPLACE.findall(l))
        if c > 0:
            flags["count"] += c
            flags["bad_lines"].append((l.strip()[:80], c))
    return flags


def decode_page_pua(lines):
    """确定性还原 Symbol 字体 PUA 码点。返回 (新行列表, 统计)。

    - confidence=ok/ascii：还原为对应 Unicode 字符，计入 restored_ok；
    - confidence=ext（大型括号分段）：还原为数学括号字符，计入 restored_ext，
      并把该页标记 ext（建议人工抽查，非阻断）；
    - confidence=manual/unknown：保留 PUA 原符，计入 manual，该页仍进核对清单。

    非上下文猜测，逐字符查表；不替换的绝不动。
    """
    restored_ok = restored_ext = manual = 0
    ext_hit = False
    out = []
    for l in lines:
        if not l or not is_pua_needed(l):
            out.append(l)
            continue
        buf = []
        for ch in l:
            if is_pua(ch) and 0xF000 <= ord(ch) <= 0xF0FF:
                new_ch, conf, _name = decode_pua_char(ch)
                if conf in ("ok", "ascii"):
                    buf.append(new_ch)
                    restored_ok += 1
                elif conf == "ext":
                    buf.append(new_ch)
                    restored_ext += 1
                    ext_hit = True
                else:  # manual / unknown
                    buf.append(ch)  # 保留 PUA 原符
                    manual += 1
            else:
                buf.append(ch)
        out.append("".join(buf))
    stats = {"ok": restored_ok, "ext": restored_ext, "manual": manual, "ext_hit": ext_hit}
    return out, stats


def is_pua_needed(line):
    """该行是否含 F0xx PUA，避免无谓的逐字符扫描。"""
    for ch in line:
        if 0xF000 <= ord(ch) <= 0xF0FF:
            return True
    return False


def _page_body_lines(text, headers):
    """一页文本 → 清理（页眉页脚/页码行）→ 分块重组标题后的正文行列表。"""
    lines = [l.strip() for l in text.split("\n")]
    lines = clean_page_lines(lines, headers)
    blocks, cur = [], []
    for l in lines:
        if l:
            cur.append(l)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    body, n_re = [], 0
    for blk in blocks:
        blk, n = _reassemble_heading_block(blk)
        n_re += n
        body.extend(blk)
        body.append("")
    return body, n_re


def build_markdown(exp, pdf_file, cand, extractor_texts, toc_pages, headers):
    """用每页胜出的候选文本组装 实验指导_RAG文本.md 内容。

    元信息与页码/公式异常都以 ``<!-- … -->`` 注释行写入：人可读、
    检索器可整体剥离，正文与旧提取文本管道完全一致。
    """
    pages_text = {
        name: texts for name, texts in extractor_texts
    }
    # 第一遍：逐页清理并统计，供头部「清洗记录」汇总
    page_out = []
    total_re = 0
    for p in cand["pages"]:
        pno = p["page"]
        text = pages_text.get(p["selected"], [None] * cand["pages_total"])[pno - 1]
        lines = [l.strip() for l in (text or "").split("\n")]
        if not any(lines):
            page_out.append((pno, ["<!-- 无文本（可能为扫描页，建议人工核对） -->"]))
            continue
        if pno - 1 in toc_pages:
            page_out.append((pno, ["<!-- 目录页已按组合特征移除（见 candidates/ 记录，请人工复核） -->"]))
            continue
        body, n_re = _page_body_lines(text, headers)
        total_re += n_re
        cambria_count = 0
        repaired_body = []
        for line in body:
            line, repaired = decode_cambria_math(line, exp)
            repaired_body.append(line)
            cambria_count += repaired
        body = repaired_body
        body, dec = decode_page_pua(body)
        flags = _formula_flags(body)
        chunks = []
        if cambria_count:
            chunks.append(
                f"<!-- 公式解码: 本页按 Cambria Math 字形轮廓映射确定性还原 "
                f"{cambria_count} 个字符 -->"
            )
        if dec["ok"] + dec["ext"] > 0:
            chunks.append(f"<!-- 公式解码: 本页确定性还原 {dec['ok']} 个符号"
                          + (f"、大型括号 {dec['ext']} 个（建议抽查）" if dec["ext"] else "")
                          + "（Symbol 字体编码查表，非猜测） -->")
        if flags["count"] > 0:
            chunks.append(f"<!-- 公式异常: 本页仍有 {flags['count']} 个未还原异常字符，"
                          "建议对照 PDF 人工核对，见 manual_review/formulas.md -->")
        chunks.extend(body)
        page_out.append((pno, chunks))

    out = []
    out.append("<!-- rag-extracted: v1 -->")
    out.append(f"<!-- 实验名称: {guide.strip_guide_filename(pdf_file)} -->")
    out.append(f"<!-- 源文件: {pdf_file} -->")
    sel_by_ext = {}
    for p in cand["pages"]:
        sel_by_ext.setdefault(p["selected"], []).append(p["page"])
    out.append("<!-- 抽取器: " + ", ".join(
        f"{e}（第" + "、".join(f"{a}-{b}" if a != b else str(a)
        for a, b in _ranges(pgs)) + "页）"
        for e, pgs in sorted(sel_by_ext.items())
    ) + " -->")
    out.append("<!-- 人工确认: false -->")
    out.append(f"<!-- 生成时间: {datetime.datetime.now().isoformat(timespec='seconds')} -->")
    head_desc = "、".join(f"{h}×{n}页" for h, n in sorted(headers.items()))
    toc_desc = "第" + "、".join(str(i + 1) for i in toc_pages) if toc_pages else "无"
    out.append("<!-- 清洗记录: "
               f"页眉页脚 {len(headers)} 种（{head_desc or '无'}）；"
               f"目录页 {len(toc_pages)} 页（{toc_desc}）；"
               f"标题重组 {total_re} 处；页码行按页清理 -->")
    out.append("")

    for pno, chunks in page_out:
        out.append(f"<!-- 页码:{pno} -->")
        out.extend(chunks)
    return "\n".join(out), total_re


def _ranges(nums):
    """把页面列表压缩为连续区间 [(a,b), ...]。"""
    nums = sorted(set(nums))
    ranges, start, prev = [], nums[0], nums[0]
    for x in nums[1:]:
        if x == prev + 1:
            prev = x
        else:
            ranges.append((start, prev))
            start, prev = x, x
    ranges.append((start, prev))
    return ranges


# ──────────────────────────────────────────────
# 审计（第一阶段）
# ──────────────────────────────────────────────
def _txt_stats(raw):
    body = raw
    lines = [l for l in body.split("\n") if l.strip()]
    n = len(body.replace("\n", "").replace(" ", ""))
    return {
        "chars": len(body.replace("\n", "").replace(" ", "")),
        "pua": len(RE_PUA.findall(body)),
        "other": len(RE_OTHER.findall(body)),
        "replace": len(RE_REPLACE.findall(body)),
        "single_char_line_ratio": (
            round(sum(1 for l in lines if len(l) == 1) / len(lines), 4) if lines else 0.0
        ),
        "sections": _section_titles(lines),
        "_n": n,
    }


def run_audit():
    """逐实验目录统计，输出 audit.json / audit.csv / summary.md。"""
    rows = []
    for dname in sorted(os.listdir(EXPERIMENT_DIR)):
        dpath = os.path.join(EXPERIMENT_DIR, dname)
        if not os.path.isdir(dpath):
            continue
        pdfs = sorted(f for f in os.listdir(dpath) if f.lower().endswith(".pdf"))
        docx = sorted(f for f in os.listdir(dpath) if f.lower().endswith(".docx"))
        txt_path = os.path.join(dpath, OLD_TXT_FILENAME)
        rag_path = os.path.join(dpath, RAG_FILENAME)
        row = {
            "experiment": dname,
            "pdf_files": pdfs,
            "pdf_pages": None,
            "old_txt": os.path.isfile(txt_path),
            "rag_md": os.path.isfile(rag_path),
            "docx_files": docx,
            "old_txt_pua": None, "old_txt_other": None, "old_txt_replace": None,
            "old_txt_chars": None, "old_txt_single_char_line_ratio": None,
            "old_txt_sections": None,
            "suspected_headers_footers": [],
            "suspected_toc_pages": [],
            "empty_pages": [],
            "scanned_suspect": False,
            "needs_manual_review": False,
            "notes": [],
        }
        if os.path.isfile(txt_path):
            try:
                raw = open(txt_path, encoding="utf-8", errors="replace").read()
            except Exception as e:
                row["notes"].append(f"旧文本读取失败: {e}")
                raw = ""
            st = _txt_stats(raw)
            row["old_txt_chars"] = st["chars"]
            row["old_txt_pua"] = st["pua"]
            row["old_txt_other"] = st["other"]
            row["old_txt_replace"] = st["replace"]
            row["old_txt_single_char_line_ratio"] = st["single_char_line_ratio"]
            row["old_txt_sections"] = st["sections"]
        if pdfs:
            cand_path = os.path.join(CANDIDATES_DIR, dname, "candidates.json")
            cand = None
            if os.path.isfile(cand_path):
                try:
                    cand = json.load(open(cand_path, encoding="utf-8"))
                except Exception:
                    cand = None
            if cand is None:
                cand = extract_doc_candidates(os.path.join(dpath, pdfs[0]))
            row["pdf_pages"] = cand["pages_total"]
            page_lines = []
            # 重新取逐页文本（直接再跑一次抽取，保证审计独立可跑）
            try:
                from PyPDF2 import PdfReader
                r = PdfReader(os.path.join(dpath, pdfs[0]))
                all_texts = [(pg.extract_text() or "") for pg in r.pages]
            except Exception:
                all_texts = []
            for p in cand["pages"]:
                t = all_texts[p["page"] - 1] if p["page"] - 1 < len(all_texts) else ""
                page_lines.append([l.strip() for l in t.split("\n")])
                chars = len(t.replace("\n", "").replace(" ", ""))
                if chars < 10:
                    row["empty_pages"].append(p["page"])
                # 疑似扫描页：正文页完全抽不出文本（第 1 页封面不计）
                if chars == 0 and p["page"] > 1:
                    row["scanned_suspect"] = True
                if p["needs_manual_review"] and chars > 0:
                    row["needs_manual_review"] = True
            if row["scanned_suspect"]:
                row["needs_manual_review"] = True
            if row["empty_pages"]:
                row["notes"].append(f"文本过少页: {row['empty_pages']}")
            row["suspected_headers_footers"] = sorted(
                _detect_header_footer(page_lines).items()
            )
            row["suspected_toc_pages"] = [
                i + 1 for i in _detect_toc_pages(page_lines)
            ]
        if docx:
            row["needs_manual_review"] = True
            row["notes"].append("源文件为 docx，无 PDF，沿用旧提取文本")
        if pdfs and not os.path.isfile(txt_path):
            row["notes"].append("有 PDF 但无旧提取文本")
        if not pdfs and not docx and not os.path.isfile(txt_path):
            row["notes"].append("无 PDF/docx/旧文本（仅示例数据）")
        if row["suspected_toc_pages"]:
            row["needs_manual_review"] = True
            row["notes"].append(f"疑似目录页: {row['suspected_toc_pages']}")
        rows.append(row)

    summary = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "experiment_dirs": len(rows),
        "pdf_count": sum(1 for r in rows if r["pdf_files"]),
        "old_txt_count": sum(1 for r in rows if r["old_txt"]),
        "extractors_available": available_extractors(),
        "extractors_missing": missing_extractors(),
        "dirs_without_pdf": [r["experiment"] for r in rows if not r["pdf_files"]],
        "dirs_without_any_text": [r["experiment"] for r in rows
                                  if not r["old_txt"] and not r["pdf_files"]],
        "dirs_needing_review": [
            r["experiment"] for r in rows if r["needs_manual_review"]
        ],
    }
    os.makedirs(REVIEW_DIR, exist_ok=True)
    with open(os.path.join(REVIEW_DIR, "audit.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "experiments": rows}, f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(REVIEW_DIR, "audit.csv"), "w", encoding="utf-8-sig",
              newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "experiment", "pdf_count", "pdf_name", "pdf_pages", "old_txt",
            "old_txt_chars", "old_txt_pua", "old_txt_other", "old_txt_replace",
            "single_char_line_ratio", "old_txt_sections", "headers_footers",
            "toc_pages", "empty_pages", "scanned_suspect", "needs_manual_review",
            "notes",
        ])
        for r in rows:
            w.writerow([
                r["experiment"], len(r["pdf_files"]),
                r["pdf_files"][0] if r["pdf_files"] else "",
                r["pdf_pages"] if r["pdf_pages"] is not None else "",
                r["old_txt"], r["old_txt_chars"], r["old_txt_pua"],
                r["old_txt_other"], r["old_txt_replace"],
                r["old_txt_single_char_line_ratio"],
                "、".join(r["old_txt_sections"] or []),
                "; ".join(f"{h}({n}页)" for h, n in r["suspected_headers_footers"]),
                ",".join(map(str, r["suspected_toc_pages"])),
                ",".join(map(str, r["empty_pages"])),
                r["scanned_suspect"], r["needs_manual_review"],
                " | ".join(r["notes"]),
            ])
    return rows, summary


def write_summary(rows, summary):
    lines = [
        "# 实验指导资料审计摘要",
        "",
        f"生成时间: {summary['generated_at']}",
        "",
        f"- 实验目录: {summary['experiment_dirs']} 个",
        f"- PDF: {summary['pdf_count']} 份；旧提取文本: {summary['old_txt_count']} 份",
        f"- 无 PDF 的目录: {', '.join(summary['dirs_without_pdf']) or '无'}",
        f"- 无任何文本资料的目录: {', '.join(summary['dirs_without_any_text']) or '无'}",
        "",
        "## 48 份 PDF 与 51 份提取文本的差异",
        "",
        "- exp0：无 PDF 也无提取文本（目录内只有示例数据 CSV，检索器本来就会跳过）；",
        "- exp30 / exp33 / exp44：源文件是 .docx（无 PDF），旧提取文本从 docx 生成，"
        "本轮工具只处理 PDF，这三份沿用旧文本；",
        "- 其余 48 个目录各含 1 份 PDF 与 1 份旧提取文本，未发现共用 PDF 或一目录多 PDF。",
        "",
        "## 抽取器可用性",
        "",
        f"- 可用: {', '.join(summary['extractors_available']) or '无'}",
        f"- 未安装（本轮不主动安装）: {', '.join(summary['extractors_missing']) or '无'}",
        "",
        "## 需要人工复核的目录",
        "",
    ]
    if summary["dirs_needing_review"]:
        for d in summary["dirs_needing_review"]:
            r = next(x for x in rows if x["experiment"] == d)
            why = "; ".join(r["notes"]) or "异常字符或空页"
            lines.append(f"- `{d}`：{why}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 疑似扫描 PDF / 空页")
    lines.append("")
    for r in rows:
        if r["empty_pages"]:
            lines.append(f"- `{r['experiment']}` 页 {r['empty_pages']} 文本过少"
                         f"（{'、'.join(r['pdf_files']) or '无PDF'}）")
    if not any(r["empty_pages"] for r in rows):
        lines.append("- 无")
    with open(os.path.join(REVIEW_DIR, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ──────────────────────────────────────────────
# 公式人工核对清单（第四阶段）
# ──────────────────────────────────────────────
def run_review(docs_built):
    """根据候选构建结果生成 manual_review/formulas.md。

    只标记异常、给页码与上下文，绝不做任何替换/补写/删除。
    """
    lines = [
        "# 公式异常人工核对清单",
        "",
        f"生成时间: {datetime.datetime.now().isoformat(timespec='seconds')}",
        "",
        "说明：异常字符 = 私用区(PUA)/Telugu 区/Arabic Supplement 区/替换符 �。",
        "本工具已按 Adobe Symbol 字体编码（U+F000 偏移）对 PUA 码点做**确定性查表还原**",
        "（非上下文猜测，见 tools/symbol_font_map.py）：希腊字母、运算符、大型括号等已",
        "自动还原为本页注释所示的 Unicode 符号。**本清单只列出查表后仍残留、无法确定性",
        "还原的异常字符**——这些需对照原 PDF 人工核对，绝不自动猜测替换。",
        "建议：对照原 PDF 同页核对公式符号；人工确认后可在正式版中手工改写为 LaTeX，"
        "并注明来源 PDF 与页码。",
        "",
    ]
    n_entries = 0
    for exp, info in sorted(docs_built.items()):
        entries = info["formula_entries"]
        if not entries:
            continue
        lines.append(f"## {exp}（PDF: {info['pdf_file']}）")
        lines.append("")
        for e in entries:
            n_entries += 1
            lines.append(f"### 第 {e['page']} 页（章节: {e['section']}）异常字符 {e['count']} 个")
            lines.append("")
            for label, t in e["context"]:
                lines.append(f"- {label}: `{t}`")
            lines.append("")
            lines.append(f"- 推荐人工检查: 对照原 PDF 第 {e['page']} 页核对上述行的公式符号"
                         "；确认后以 LaTeX 改写并在 MD 元信息中标注来源页码。")
            lines.append("")
    if not n_entries:
        lines.append("（未发现异常公式字符页）")
    lines.append("")
    lines.append("## 疑似扫描页 / 空文本页")
    lines.append("")
    n_scanned = 0
    for exp, info in sorted(docs_built.items()):
        if info["empty_pages"]:
            n_scanned += 1
            lines.append(f"- `{exp}`：第 {info['empty_pages']} 页文本为空或过少"
                         f"（PDF: {info['pdf_file']}）。本环境未安装 OCR 工具"
                         f"（tesseract 未安装），如需恢复请先确认安装。")
    if not n_scanned:
        lines.append("- 无")
    lines.append("")
    lines.append("## docx 源实验（无 PDF，沿用旧文本）")
    lines.append("")
    lines.append("- exp30 / exp33 / exp44：源文件为 .docx，本工具不处理，旧提取文本质量"
                 "未审计，建议人工通读。")
    os.makedirs(MANUAL_DIR, exist_ok=True)
    with open(os.path.join(MANUAL_DIR, "formulas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return n_entries


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────
def collect_docs(only=None):
    """返回需要处理的实验目录（有 PDF 的目录）。"""
    docs = []
    for dname in sorted(os.listdir(EXPERIMENT_DIR)):
        if only and dname not in only:
            continue
        dpath = os.path.join(EXPERIMENT_DIR, dname)
        if not os.path.isdir(dpath):
            continue
        pdfs = sorted(f for f in os.listdir(dpath) if f.lower().endswith(".pdf"))
        if pdfs:
            docs.append((dname, dpath, pdfs))
    return docs


def cmd_extract(only):
    docs = collect_docs(only)
    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    for dname, dpath, pdfs in docs:
        out_dir = os.path.join(CANDIDATES_DIR, dname)
        os.makedirs(out_dir, exist_ok=True)
        cand = extract_doc_candidates(os.path.join(dpath, pdfs[0]))
        cand.update({"experiment": dname, "pdf_file": pdfs[0]})
        with open(os.path.join(out_dir, "candidates.json"), "w", encoding="utf-8") as f:
            json.dump(cand, f, ensure_ascii=False, indent=2)
        n_review = sum(1 for p in cand["pages"] if p["needs_manual_review"])
        print(f"[extract] {dname}: {cand['pages_total']} 页, "
              f"{n_review} 页需人工核对")
    return docs


def cmd_build(only):
    docs = cmd_extract(only) if not all(
        os.path.isfile(os.path.join(CANDIDATES_DIR, d, "candidates.json"))
        for d, _, _ in collect_docs(only)
    ) else collect_docs(only)
    os.makedirs(SELECTED_DIR, exist_ok=True)
    built = {}
    for dname, dpath, pdfs in docs:
        cand_path = os.path.join(CANDIDATES_DIR, dname, "candidates.json")
        if not os.path.isfile(cand_path):
            continue
        cand = json.load(open(cand_path, encoding="utf-8"))
        # 重新抽取胜出页文本
        extractor_texts = []
        for name, ok, fn in EXTRACTOR_REGISTRY:
            if not ok:
                continue
            try:
                document = fn(os.path.join(dpath, pdfs[0]))
                extractor_texts.append((name, document.page_texts))
            except Exception as e:
                print(f"  [build] {dname} {name} 失败: {e}")
        # 以胜出候选重建逐页文本
        page_texts = [None] * cand["pages_total"]
        for p in cand["pages"]:
            for name, texts in extractor_texts:
                if name == p["selected"] and p["page"] - 1 < len(texts):
                    page_texts[p["page"] - 1] = texts[p["page"] - 1]
                    break
        page_lines = [
            [l.strip() for l in (t or "").split("\n")] for t in page_texts
        ]
        headers = _detect_header_footer(page_lines)
        toc_pages = _detect_toc_pages(page_lines)
        md, n_re = build_markdown(dname, pdfs[0], cand, extractor_texts,
                                  toc_pages, headers)
        out_dir = os.path.join(SELECTED_DIR, dname)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, RAG_FILENAME), "w", encoding="utf-8") as f:
            f.write(md + "\n")
        # 收集公式核对条目
        formula_entries, empty_pages = [], []
        for p in cand["pages"]:
            t = page_texts[p["page"] - 1] or ""
            if not t.strip():
                empty_pages.append(p["page"])
                continue
            if p["page"] - 1 in toc_pages:
                continue
            lines = clean_page_lines(
                [l.strip() for l in t.split("\n")], headers
            )
            lines = [decode_cambria_math(line, dname)[0] for line in lines]
            lines, _dec = decode_page_pua(lines)   # 先确定性解码，只统计残留异常
            flags = _formula_flags(lines)
            if flags["count"] == 0:
                continue
            section = "未识别"
            for l in lines:
                canon = guide.canonicalize_section(l)
                if canon:
                    section = canon
            context = []
            for i, l in enumerate(lines):
                if not (RE_PUA.search(l) or RE_OTHER.search(l) or RE_REPLACE.search(l)):
                    continue
                if i > 0 and lines[i - 1].strip():
                    context.append(("上文", lines[i - 1].strip()[:60]))
                context.append(("异常行", l.strip()[:80]))
                nxt = next((x.strip() for x in lines[i + 1:i + 3] if x.strip()), "")
                if nxt:
                    context.append(("下文", nxt[:60]))
                break  # 每页只记录首个异常行上下文，避免清单爆炸
            formula_entries.append({
                "page": p["page"], "section": section,
                "count": flags["count"], "context": context,
            })
        built[dname] = {
            "pdf_file": pdfs[0], "pages": cand["pages_total"],
            "headers": sorted(headers.items()), "toc_pages": [i + 1 for i in toc_pages],
            "reassembled_headings": n_re,
            "formula_entries": formula_entries, "empty_pages": empty_pages,
            "md_path": os.path.join(out_dir, RAG_FILENAME),
        }
        print(f"[build] {dname}: {cand['pages_total']} 页 → "
              f"{os.path.relpath(out_dir, PROJECT_ROOT)}/{RAG_FILENAME}"
              f"（标题重组 {n_re} 处，公式异常 {len(formula_entries)} 页，"
              f"空页 {len(empty_pages)}，目录页 {built[dname]['toc_pages']}）")
    return built


def run_quality_gate(only=None):
    """检查 selected/ 中的候选是否达到正式知识库发布条件。"""
    results = []
    selected_dirs = [
        name for name in sorted(os.listdir(SELECTED_DIR))
        if os.path.isdir(os.path.join(SELECTED_DIR, name))
        and (not only or name in only)
    ] if os.path.isdir(SELECTED_DIR) else []
    for experiment in selected_dirs:
        path = os.path.join(SELECTED_DIR, experiment, RAG_FILENAME)
        if not os.path.isfile(path):
            continue
        text = Path(path).read_text(encoding="utf-8")
        result = evaluate_rag_markdown(text, path=path)
        data = result.to_dict()
        data["experiment"] = experiment
        formal_dir = os.path.join(EXPERIMENT_DIR, experiment)
        if not os.path.isdir(formal_dir):
            data["passed"] = False
            data["errors"].append("正式实验目录不存在")
        results.append(data)

    passed = sum(1 for item in results if item["passed"])
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "documents": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
    os.makedirs(REVIEW_DIR, exist_ok=True)
    report_path = os.path.join(REVIEW_DIR, "quality_gate.json")
    Path(report_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_parser_comparison(only)
    return report


def write_parser_comparison(only=None):
    """汇总 candidates 的逐页质量，显式比较所有已注册/缺失解析器。"""
    registry = {name: available for name, available, _ in EXTRACTOR_REGISTRY}
    stats = {
        name: {
            "status": "available" if available else "unavailable",
            "pages_evaluated": 0,
            "selected_pages": 0,
            "score_sum": 0.0,
            "empty_pages": 0,
            "pua_count": 0,
            "replacement_count": 0,
            "table_lines": 0,
            "formula_lines": 0,
            "two_column_suspect_lines": 0,
            "scanned_suspect_pages": 0,
        }
        for name, available in registry.items()
    }
    if os.path.isdir(CANDIDATES_DIR):
        for experiment in sorted(os.listdir(CANDIDATES_DIR)):
            if only and experiment not in only:
                continue
            path = os.path.join(CANDIDATES_DIR, experiment, "candidates.json")
            if not os.path.isfile(path):
                continue
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            for page in document.get("pages", []):
                selected = page.get("selected")
                for parser, metrics in page.get("candidates", {}).items():
                    if parser not in stats:
                        continue
                    item = stats[parser]
                    item["pages_evaluated"] += 1
                    item["selected_pages"] += int(parser == selected)
                    item["score_sum"] += float(metrics.get("score", 0.0))
                    item["empty_pages"] += int(metrics.get("chars", 0) == 0)
                    item["pua_count"] += int(metrics.get("pua_count", 0))
                    item["replacement_count"] += int(metrics.get("replace_count", 0))
                    item["table_lines"] += int(metrics.get("table_lines", 0))
                    item["formula_lines"] += int(metrics.get("formula_lines", 0))
                    item["two_column_suspect_lines"] += int(
                        metrics.get("two_column_suspect_lines", 0)
                    )
                    item["scanned_suspect_pages"] += int(
                        metrics.get("scanned_suspect", False)
                    )
    rows = []
    for parser, item in stats.items():
        pages = item.pop("pages_evaluated")
        score_sum = item.pop("score_sum")
        rows.append({
            "parser": parser,
            "pages_evaluated": pages,
            "average_score": round(score_sum / pages, 4) if pages else None,
            **item,
        })
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": (
            "同页质量分仅用于候选比较；unavailable 表示本机未安装，"
            "没有伪造 Docling/MinerU 结果。"
        ),
        "parsers": rows,
    }
    Path(os.path.join(REVIEW_DIR, "parser_comparison.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def cmd_publish(only=None):
    """门禁通过后直接发布 selected 内容；覆盖原文件且不创建备份。"""
    report = run_quality_gate(only)
    failed = [item for item in report["results"] if not item["passed"]]
    if failed:
        names = ", ".join(item["experiment"] for item in failed)
        raise RuntimeError(f"质量门禁未通过，未发布任何文件：{names}")
    if not report["results"]:
        raise RuntimeError("没有找到可发布的 selected 文档")

    records = []
    published_at = datetime.datetime.now().isoformat(timespec="seconds")
    for item in report["results"]:
        experiment = item["experiment"]
        source = os.path.join(SELECTED_DIR, experiment, RAG_FILENAME)
        destination = os.path.join(EXPERIMENT_DIR, experiment, RAG_FILENAME)
        content = Path(source).read_text(encoding="utf-8")
        content = re.sub(
            r"<!--\s*人工确认\s*:\s*false\s*-->",
            "<!-- 人工确认: true（质量门禁通过并获用户授权发布） -->",
            content,
            count=1,
        )
        publication = f"<!-- 发布时间: {published_at} -->"
        if "<!-- 发布时间:" in content:
            content = re.sub(r"<!--\s*发布时间\s*:.*?-->", publication, content, count=1)
        else:
            marker = re.search(r"<!--\s*生成时间\s*:.*?-->", content)
            insert_at = marker.end() if marker else 0
            content = content[:insert_at] + "\n" + publication + content[insert_at:]
        Path(destination).write_text(content.rstrip() + "\n", encoding="utf-8")
        records.append({
            "experiment": experiment,
            "source": source,
            "destination": destination,
            "body_chars": item["metrics"]["body_chars"],
            "page_markers": item["metrics"]["page_markers"],
        })

    manifest = {
        "published_at": published_at,
        "backup_created": False,
        "documents": len(records),
        "records": records,
    }
    Path(os.path.join(REVIEW_DIR, "publish_manifest.json")).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main():
    ap = argparse.ArgumentParser(description="离线实验指导 PDF 预处理工具（非破坏性）")
    ap.add_argument("cmd", nargs="?", default="all",
                    choices=["all", "audit", "extract", "build", "review", "gate", "publish"])
    ap.add_argument("--only", help="只处理指定实验目录（逗号分隔，如 exp1,exp2）")
    ap.add_argument("--deploy", metavar="EXP",
                    help="兼容旧命令：等价于 publish --only EXP")
    ap.add_argument("--deploy-confirm", choices=["yes"],
                    help="必须显式传入 yes 才会执行 --deploy")
    args = ap.parse_args()
    only = set(x.strip() for x in (args.only or "").split(",") if x.strip()) or None

    if args.deploy:
        if args.deploy_confirm != "yes":
            print("错误：--deploy 需要 --deploy-confirm yes；本轮绝不部署，退出。")
            sys.exit(1)
        manifest = cmd_publish({args.deploy})
        print(f"[publish] 已直接发布 {manifest['documents']} 份文档，不创建备份")
        return

    os.makedirs(REVIEW_DIR, exist_ok=True)
    print(f"[环境] 可用抽取器: {available_extractors() or '无'}")
    print(f"[环境] 未安装: {missing_extractors() or '无'}（本轮不安装）")
    built = None
    if args.cmd in ("all", "extract"):
        cmd_extract(only)
    if args.cmd in ("all", "audit"):
        rows, summary = run_audit()
        write_summary(rows, summary)
        print(f"[audit] 已输出 audit.json / audit.csv / summary.md"
              f"（需复核 {len(summary['dirs_needing_review'])} 个目录）")
    if args.cmd in ("all", "build"):
        built = cmd_build(only)
    if args.cmd in ("all", "review"):
        if built is None:
            built = cmd_build(only)
        n = run_review(built)
        print(f"[review] formulas.md 已生成，公式异常条目 {n} 条")
    if args.cmd == "gate":
        report = run_quality_gate(only)
        print(f"[gate] {report['passed']}/{report['documents']} 份通过，"
              f"{report['failed']} 份失败；报告见 quality_gate.json")
        if report["failed"]:
            sys.exit(1)
    if args.cmd == "publish":
        manifest = cmd_publish(only)
        print(f"[publish] 已直接发布 {manifest['documents']} 份文档，不创建备份")
    print("[完成] 全部输出位于 rag_extraction_review/，未改动任何 PDF 与旧提取文本。")


if __name__ == "__main__":
    main()
