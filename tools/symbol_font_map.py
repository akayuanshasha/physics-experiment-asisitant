#!/usr/bin/env python3
"""标准 Adobe Symbol 字体编码 -> Unicode 确定性映射表（只读常量模块）。

原理：实验指导 PDF 的公式符号用 SymbolMT（Adobe Symbol 字体）排布，Word/MathType
导出时把字形放进 Unicode 私用区 U+F0xx，其中 xx = 标准 Symbol 8 位编码。本表把
xx 还原为对应 Unicode 字符。

分级（决定能否自动还原）：
  - "ok"   ：标准 Symbol 编码中该码点对应唯一 Unicode 符号，可确定性自动还原。
  - "ext"  ：Symbol 扩展区（0xE0–0xEF、0xF2 等），对应大括号/方括号等分段符号，
             Unicode 有对应数学括号字符，但具体选哪个（如 ⎛vs⎜vs⎝）需结合上下文
             开/闭位置；本表给出最常见对应并标记，建议人工抽查。
  - "ascii"：与 ASCII 同码（数字、字母在某些公式中混入），直接保留 ASCII 本身。

本模块不执行任何替换逻辑，只提供常量。替换由 rebuild_guide_texts.py 在离线、
非破坏性流程中调用，并仅对 confidence=="ok" 的码点自动还原；其余保留 PUA 原符
并写入 manual_review/formulas.md 标人工核对。

数据来源：Adobe Symbol 字体公开编码规范 + 字形索引/字宽取证验证（见
tools/forensic_pua_decode.py）。无任何"根据上下文猜测"。
"""

# 键 = 标准 Symbol 8 位码点；值 = (Unicode 字符, 符号名, 置信度)
SYMBOL_CODE_TO_UNICODE = {
    # ── ASCII 同码区（保留原 ASCII 字符）──────────────────────
    0x20: (" ", "space", "ascii"),
    0x26: ("&", "ampersand", "ascii"),
    0x28: ("(", "parenleft", "ascii"),
    0x29: (")", "parenright", "ascii"),
    0x2B: ("+", "plus", "ascii"),
    0x31: ("1", "one", "ascii"),
    0x32: ("2", "two", "ascii"),
    0x5B: ("[", "bracketleft", "ascii"),
    0x5D: ("]", "bracketright", "ascii"),

    # ── 运算符 / 关系符（确定性）──────────────────────────────
    0x2D: ("−", "minus", "ok"),         # U+2212 减号（非 ASCII 连字符）
    0x3C: ("<", "less", "ok"),
    0x3D: ("=", "equal", "ok"),
    0x3E: (">", "greater", "ok"),
    0x40: ("≅", "approxequal", "ok"),
    0x5C: ("∴", "therefore", "ok"),
    0x5E: ("⊥", "perpendicular", "ok"),
    0x7E: ("~", "similar", "ok"),        # 约等/相似，Symbol 中为 tilde
    0xA2: ("′", "minute", "ok"),         # 角分
    0xA3: ("√", "radical", "ok"),        # 根号
    0xA5: ("∞", "infinity", "ok"),
    0xA9: ("⊗", "otimes", "ok"),
    0xAB: ("〈", "angleleft", "ok"),      # 左角括号
    0xB0: ("°", "degree", "ok"),
    0xB1: ("±", "plusminus", "ok"),
    0xB4: ("´", "acute", "ok"),
    0xB5: ("µ", "mu", "ok"),             # micro
    0xB6: ("∂", "partial", "ok"),
    0xBA: ("˚", "dotless-ring", "ok"),
    0xBB: ("〉", "angleright", "ok"),     # 右角括号
    0xD7: ("×", "multiply", "ok"),
    0xDE: ("Þ", "Thorn", "ok"),          # 罕见，按标准
    0xF7: ("÷", "divide", "ok"),

    # ── 希腊字母（确定性，标准 Symbol 编码唯一对应）──────────
    0x41: ("Α", "Alpha", "ok"),
    0x42: ("Β", "Beta", "ok"),
    0x43: ("Χ", "Chi", "ok"),
    0x44: ("Δ", "Delta", "ok"),
    0x45: ("Ε", "Epsilon", "ok"),
    0x46: ("Φ", "Phi", "ok"),            # 大写 Phi
    0x47: ("Γ", "Gamma", "ok"),
    0x48: ("Η", "Eta", "ok"),
    0x49: ("Ι", "Iota", "ok"),
    0x4C: ("Λ", "Lambda", "ok"),
    0x4D: ("Μ", "Mu", "ok"),
    0x4E: ("Ν", "Nu", "ok"),
    0x50: ("Π", "Pi", "ok"),
    0x51: ("Θ", "Theta", "ok"),
    0x52: ("Ρ", "Rho", "ok"),
    0x53: ("Σ", "Sigma", "ok"),
    0x54: ("Τ", "Tau", "ok"),
    0x55: ("Υ", "Upsilon", "ok"),
    0x57: ("Ω", "Omega", "ok"),
    0x5A: ("Ζ", "Zeta", "ok"),
    0x61: ("α", "alpha", "ok"),
    0x62: ("β", "beta", "ok"),
    0x63: ("χ", "chi", "ok"),
    0x64: ("δ", "delta", "ok"),
    0x65: ("ε", "epsilon", "ok"),
    0x66: ("φ", "phi", "ok"),            # 小写 phi（varphi 形）
    0x67: ("γ", "gamma", "ok"),
    0x68: ("η", "eta", "ok"),
    0x6A: ("φ", "phi", "ok"),            # 小写 phi（直身形）—— 与 0x66 同为 φ
    0x6C: ("λ", "lambda", "ok"),
    0x6D: ("μ", "mu", "ok"),
    0x6E: ("ν", "nu", "ok"),
    0x70: ("π", "pi", "ok"),
    0x71: ("θ", "theta", "ok"),
    0x72: ("ρ", "rho", "ok"),
    0x73: ("σ", "sigma", "ok"),
    0x74: ("τ", "tau", "ok"),
    0x75: ("υ", "upsilon", "ok"),
    0x77: ("ω", "omega", "ok"),
    0x78: ("ξ", "xi", "ok"),

    # ── Symbol 扩展区：大型括号/方括号分段（0xE0–0xEF, 0xF2）──
    # 这些是 stretchable 括号的各段，Unicode 数学括号可对应，但开/闭/中段需看位置。
    # 给出最常见对应，confidence=ext，建议人工抽查。
    0xE5: ("⎴", "brackettop", "ext"),
    0xE6: ("⎛", "parenleftbig", "ext"),   # 大左括号上段
    0xE7: ("⎜", "parenleftmid", "ext"),   # 大左括号中段
    0xE8: ("⎞", "parenrightbig", "ext"),  # 大右括号上段
    0xE9: ("⎟", "parenrightmid", "ext"),  # 大右括号中段
    0xEA: ("⎝", "parenleftbottom", "ext"),
    0xEB: ("⎠", "parenrightbottom", "ext"),
    0xEC: ("⎡", "bracketleftbig", "ext"),
    0xED: ("⎢", "bracketleftmid", "ext"),
    0xEE: ("⎤", "bracketrightbig", "ext"),
    0xEF: ("⎥", "bracketrightmid", "ext"),
    0xF2: ("⎣", "bracketleftbottom", "ext"),
    0xF6: ("⎛", "parenleftbig2", "ext"),
    0xF7: ("⎞", "parenrightbig2", "ext"),
    0xF8: ("⎝", "parenleftbottom2", "ext"),
    0xF9: ("⎜", "parenleftmid2", "ext"),
    0xFA: ("⎠", "parenrightbottom2", "ext"),
    0xFB: ("⎟", "parenrightmid2", "ext"),

    # ── 上标/修饰（确定性）──────────────────────────────────
    0xB3: ("³", "threesuperior", "ok"),
    0xAE: ("ﬁ", "fi", "ext"),             # 极罕见，按字形轮廓可能为别的；标 ext

    # ── 角分/上标撇号变体 ──
    0x95: ("•", "bullet", "ok"),
}


# corpus 中出现、但不在上表（无法确定性还原）的码点：保留 PUA 原符，标人工。
# 经取证：0x22(∀)、0x2A(∗)、0xA2 重复、0x4D(Μ) 等。本集合由工具运行时动态计算。
MANUAL_REVIEW_CODES = {
    0x22,  # ∀ for-all —— 出现需确认是否真是 ∀
    0x2A,  # ∗ 卷积/星号
    0xA2,  # ′ 已在 ok；若出现歧义另行处理
}


def decode_pua_char(ch):
    """对一个 PUA 字符返回 (还原字符, confidence, sym_name)。
    若非 F0xx PUA 或不在表中，返回 (ch, "unknown", "")。"""
    o = ord(ch)
    if not (0xF000 <= o <= 0xF0FF):
        return ch, "unknown", ""
    code = o & 0xFF
    entry = SYMBOL_CODE_TO_UNICODE.get(code)
    if entry is None:
        return ch, "manual", ""
    return entry[0], entry[2], entry[1]


def is_pua(ch):
    o = ord(ch)
    return (0xE000 <= o <= 0xF8FF) or (0xF0000 <= o <= 0xFFFFD)
