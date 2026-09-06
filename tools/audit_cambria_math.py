#!/usr/bin/env python3
"""只读审计：逐个报告 exp11/exp12 中所有 Cambria Math 字体对象。
不修改任何 PDF、文本或仓库文件；仅输出到 stdout。

报告字段：字体对象编号(xref)、所在页码、BaseFont、字体子集前缀、Encoding、
ToUnicode 是否存在、ToUnicode 映射条目数、异常字符被映射到的目标值、
内嵌字体 cmap 是否存在；外加 PDF Creator/Producer，并给出 缺失/损坏/PUA 判定。
"""
import glob
import re
import io
import pymupdf as fitz
import fontTools.ttLib as ttLib

EXPS = {
    "exp11": "/root/107杯/main/b_static/experiment/exp11",
    "exp12": "/root/107杯/main/b_static/experiment/exp12",
}

# 异常目标区：Syriac / Arabic Ext / Thaana / Nko / Tamil / Telugu / Sinhala / PUA
ANOM = [
    (0x0700, 0x074F, "Syriac"),
    (0x0750, 0x077F, "ArabicExt-A"),
    (0x0780, 0x07BF, "Thaana"),
    (0x07C0, 0x07FF, "Nko"),
    (0x0B80, 0x0BFF, "Tamil"),
    (0x0C00, 0x0C7F, "Telugu"),
    (0x0D00, 0x0D7F, "Sinhala"),
    (0xE000, 0xF8FF, "PUA"),
]


def script_of(cp):
    for lo, hi, name in ANOM:
        if lo <= cp <= hi:
            return name
    return None


def gkey(doc, xref, key):
    try:
        t, v = doc.xref_get_key(xref, key)
        return t, v
    except Exception:
        return "null", ""


def parse_tounicode(stream_bytes):
    """解析 ToUnicode CMap 流，返回 {src_code: [target_codepoints]} 与总条目数。"""
    if not stream_bytes:
        return {}, 0
    try:
        text = stream_bytes.decode("latin-1", errors="replace")
    except Exception:
        text = stream_bytes.decode("utf-8", errors="replace")
    mapping = {}
    total = 0
    # bfchar 段
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            s = int(src, 16)
            # dst 可能是多码点（每 4 hex 一码点）
            targets = [int(dst[i:i + 4], 16) for i in range(0, len(dst), 4)]
            mapping.setdefault(s, []).extend(targets)
            total += 1
    # bfrange 段：<start> <end> <dst>  或  <start> <end> [<d1> <d2> ...]
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for m in re.finditer(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[([^\]]*)\])",
            block, re.S):
            start, end = int(m.group(1), 16), int(m.group(2), 16)
            if m.group(3):  # 单一目标，递增
                base = int(m.group(3), 16)
                for i, code in enumerate(range(start, end + 1)):
                    mapping.setdefault(code, []).append(base + i)
                    total += 1
            else:  # 列表
                vals = re.findall(r"<([0-9A-Fa-f]+)>", m.group(4))
                for i, code in enumerate(range(start, end + 1)):
                    if i < len(vals):
                        t = int(vals[i], 16)
                        mapping.setdefault(code, []).append(t)
                        total += 1
    return mapping, total


def audit_font(doc, xref, pages):
    print(f"\n--- 字体对象 xref={xref} ---")
    print(f"  所在页码: {sorted(pages)}")
    # basefont / subset 前缀
    t_bf, v_bf = gkey(doc, xref, "BaseFont")
    basefont = v_bf.strip().lstrip("/") if v_bf else "(无 /BaseFont)"
    # 去掉子集前缀里的括号
    subset = ""
    if "+" in basefont:
        subset = basefont.split("+")[0]
    print(f"  BaseFont: {basefont}")
    print(f"  字体子集前缀: {subset or '(无，可能非子集)'}")
    # Encoding
    t_enc, v_enc = gkey(doc, xref, "Encoding")
    enc = v_enc.strip() if v_enc else "(无)"
    print(f"  Encoding: {enc}  [type={t_enc}]")
    # 类型
    t_sub, v_sub = gkey(doc, xref, "Subtype")
    print(f"  Subtype: {v_sub.strip() if v_sub else '(无)'}")
    # ToUnicode
    t_tu, v_tu = gkey(doc, xref, "ToUnicode")
    tu_mapping, tu_total = {}, 0
    if t_tu == "xref":
        tu_xref = int(re.search(r"(\d+)", v_tu).group(1))
        try:
            stream = doc.xref_stream(tu_xref)
        except Exception as e:
            stream = None
            print(f"  ToUnicode: 存在(xref={tu_xref}) 但读取失败: {e}")
        if stream is not None:
            tu_mapping, tu_total = parse_tounicode(stream)
            print(f"  ToUnicode: 存在 (xref={tu_xref})，映射条目数 = {tu_total}")
        # else 已打印失败
    else:
        print(f"  ToUnicode: 不存在 [type={t_tu}, val={v_tu}]")
    # 异常目标值
    anom_targets = {}
    for src, targets in tu_mapping.items():
        for tp in targets:
            sc = script_of(tp)
            if sc:
                anom_targets.setdefault(sc, []).append((src, tp))
    if anom_targets:
        print(f"  异常目标值（按区聚合）:")
        for sc, pairs in anom_targets.items():
            shown = pairs[:12]
            detail = ", ".join(f"src<{s:02X}>→U+{tp:04X}" for s, tp in shown)
            more = f" …(+{len(pairs)-12})" if len(pairs) > 12 else ""
            print(f"    [{sc}] {len(pairs)} 条: {detail}{more}")
    elif tu_total > 0:
        # 全部目标均不在异常区
        all_tg = sorted({tp for tps in tu_mapping.values() for tp in tps})
        print(f"  异常目标值: 无（ToUnicode 全部目标落在正常区，例: "
              f"{', '.join('U+%04X' % t for t in all_tg[:8])}）")
    # 内嵌字体 cmap
    try:
        _, _, _, buf = doc.extract_font(xref)
        has_cmap = False
        cmap_n = 0
        glyph_n = 0
        outline = "(无)"
        if buf:
            font = ttLib.TTFont(io.BytesIO(buf))
            glyph_n = font["maxp"].numGlyphs
            has_cmap = "cmap" in font
            if has_cmap:
                cmap_n = len(font.getBestCmap() or {})
            if "glyf" in font:
                outline = "glyf(TrueType)"
            elif "CFF " in font:
                outline = "CFF"
            elif "CFF2" in font:
                outline = "CFF2"
        print(f"  内嵌字体 cmap: {'存在' if has_cmap else '不存在'}"
              f"（cmap 条目={cmap_n}，字形数={glyph_n}，轮廓表={outline}）")
    except Exception as e:
        print(f"  内嵌字体 cmap: 提取失败 ({type(e).__name__}: {e})")
    # CIDToGIDMap（Type0 才有，在 DescendantFonts 里）
    t_df, v_df = gkey(doc, xref, "DescendantFonts")
    if t_df == "xref":
        df_xref = int(re.search(r"(\d+)", v_df).group(1))
        t_g2u, v_g2u = gkey(doc, df_xref, "CIDToGIDMap")
        t_cid, v_cid = gkey(doc, df_xref, "CIDSystemInfo")
        print(f"  DescendantFont xref={df_xref}; CIDToGIDMap={v_g2u.strip() or '(无)'}"
              f" [type={t_g2u}]")
    # 判定
    if t_tu != "xref":
        verdict = "ToUnicode 缺失（抽取回退到内嵌字体 cmap）"
    elif anom_targets:
        # 区分 PUA 与 异区
        if list(anom_targets) == ["PUA"]:
            verdict = "映射到 PUA"
        else:
            verdict = "ToUnicode 损坏（映射到非数学文字区：" + "/".join(anom_targets) + "）"
    else:
        verdict = "ToUnicode 正常（无可疑目标）"
    print(f"  判定: {verdict}")
    return verdict


def main():
    for exp, dirp in EXPS.items():
        pdfs = glob.glob(dirp + "/*.pdf")
        if not pdfs:
            print(f"\n##### {exp}: 未找到 PDF"); continue
        pdf = pdfs[0]
        print(f"\n{'='*60}\n##### {exp}: {pdf}\n{'='*60}")
        doc = fitz.open(pdf)
        md = doc.metadata or {}
        print(f"  Creator : {md.get('creator') or '(无)'}")
        print(f"  Producer: {md.get('producer') or '(无)'}")
        print(f"  总页数  : {len(doc)}")
        # 收集所有 Cambria Math 字体对象
        font_pages = {}  # xref -> {'pages':set,'basefont':str}
        order = []
        for pno in range(len(doc)):
            for f in doc[pno].get_fonts(full=True):
                xref = f[0]
                basefont = f[3] or ""
                if "Cambria" in basefont or "CambriaMath" in basefont:
                    if xref not in font_pages:
                        font_pages[xref] = {"pages": set(), "basefont": basefont}
                        order.append(xref)
                    font_pages[xref]["pages"].add(pno + 1)
        print(f"  Cambria Math 字体对象数: {len(font_pages)}")
        verdicts = []
        for xref in order:
            v = audit_font(doc, xref, font_pages[xref]["pages"])
            verdicts.append(v)
        print(f"\n  >>> {exp} 汇总判定: " + " | ".join(f"#{x}={v}" for x, v in zip(order, verdicts)))


if __name__ == "__main__":
    main()
