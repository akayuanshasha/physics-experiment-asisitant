"""Section-name helpers shared by the offline guide extraction tool."""

from __future__ import annotations

import re


SECTION_ALIASES = {
    "实验目的": ("实验目的", "实验目标", "教学目的"),
    "实验任务": ("实验任务",),
    "能力培养": ("能力培养",),
    "实验要求": ("实验要求", "实验须知", "基本要求"),
    "实验原理": ("实验原理", "理论原理", "基本原理"),
    "实验装置": ("实验装置", "装置简介"),
    "实验仪器": (
        "实验仪器", "实验器材", "仪器设备", "实验设备",
        "仪器与器材", "实验仪器与器材",
    ),
    "实验内容": ("实验内容", "实验步骤", "实验方法", "实验过程", "实验内容与步骤"),
    "数据记录": ("数据记录", "数据记录与处理", "数据记录和处理"),
    "数据处理": ("数据处理", "数据处理与分析", "数据处理和分析"),
    "结果分析": ("结果分析", "结果与分析"),
    "不确定度计算": ("不确定度计算", "不确定度分析", "误差分析与不确定度"),
    "注意事项": ("注意事项", "安全事项", "实验注意事项", "注意"),
    "思考题": ("思考题", "思考与讨论"),
    "实验报告": ("实验报告", "报告要求", "实验报告要求"),
    "参考资料": ("参考资料", "参考文献"),
}

_SECTION_NAME_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}
_CN_NUM = "一二三四五六七八九十百"
_NUM_PREFIX_RE = re.compile(
    rf"^(?:\d{{1,3}}\s*[.．、]\s*|[{_CN_NUM}]{{1,3}}\s*[、.．]\s*|"
    rf"第\s*[{_CN_NUM}0-9]{{1,3}}\s*[章节部分篇]\s*)+"
)


def strip_heading_decoration(line: str) -> str | None:
    text = line.strip()
    if not text:
        return None
    text = re.sub(r"^#{1,6}\s*", "", text)
    match = re.match(r"^【(.+)】\s*$", text)
    if match:
        text = match.group(1)
    text = _NUM_PREFIX_RE.sub("", text)
    text = text.strip().rstrip("：:")
    return text or None


def canonicalize_section(line: str) -> str | None:
    core = strip_heading_decoration(line)
    return _SECTION_NAME_TO_CANONICAL.get(core) if core is not None else None


def is_section_heading(line: str) -> bool:
    return canonicalize_section(line) is not None


def strip_guide_filename(filename: str) -> str:
    name = filename
    for extension in (".pdf", ".PDF"):
        if name.endswith(extension):
            name = name[:-len(extension)]
    name = re.sub(r"[（(]实验指导[)）]", "", name)
    name = re.sub(r"[ABC]$", "", name).strip()
    return name or filename
