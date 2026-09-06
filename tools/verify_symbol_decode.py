#!/usr/bin/env python3
"""验证 symbol_font_map 对全库 PUA 的覆盖率与分级。只读，不写项目文件。
输出：每个出现的 F0xx 码点 -> confidence -> 出现次数 -> 还原字符。"""
import glob
import collections
import pymupdf as fitz
import sys
sys.path.insert(0, '/root/107杯/main/tools')
from symbol_font_map import decode_pua_char, SYMBOL_CODE_TO_UNICODE

hist = collections.Counter()
for pdf in sorted(glob.glob('/root/107杯/main/b_static/experiment/*/*.pdf')):
    d = fitz.open(pdf)
    for p in d:
        for ch in p.get_text():
            o = ord(ch)
            if 0xF000 <= o <= 0xF0FF:
                hist[o] += 1

by_conf = collections.Counter()
total = sum(hist.values())
unmapped = []
print(f"corpus PUA chars total: {total}, distinct codes: {len(hist)}\n")
print(f"{'PUA':9} {'conf':6} {'restored':>4}  name            count")
for cp in sorted(hist):
    ch = chr(cp)
    restored, conf, name = decode_pua_char(ch)
    by_conf[conf] += hist[cp]
    mark = '' if conf in ('ok', 'ascii') else '  <-- 需人工' if conf in ('ext', 'manual', 'unknown') else ''
    if conf in ('ext', 'manual', 'unknown'):
        unmapped.append((cp, conf, name, hist[cp]))
    print(f"  U+{cp:04X} {conf:6} {restored!r:>4}  {name:14s} x{hist[cp]}{mark}")

print(f"\n=== 按置信度汇总 ===")
for c, n in by_conf.most_common():
    print(f"  {c}: {n} 字符")
auto = sum(by_conf[c] for c in ('ok', 'ascii'))
manual = sum(by_conf[c] for c in ('ext', 'manual', 'unknown'))
print(f"\n可自动还原 (ok+ascii): {auto} / {total} = {auto/total*100:.1f}%")
print(f"需人工/抽查 (ext+manual+unknown): {manual} / {total} = {manual/total*100:.1f}%")
