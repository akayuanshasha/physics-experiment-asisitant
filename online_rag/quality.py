"""面向正式知识库发布的确定性质量门禁。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any


_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_PAGE_RE = re.compile(r"<!--\s*页码\s*:\s*(\d+)\s*-->")
_SOURCE_RE = re.compile(r"<!--\s*源文件\s*:\s*(.+?)\s*-->")
_EXPERIMENT_RE = re.compile(r"<!--\s*实验名称\s*:\s*(.+?)\s*-->")
_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_OTHER_SCRIPT_RE = re.compile(r"[\u0c00-\u0c7f\u0740-\u077f]")
_UNRESOLVED_RE = re.compile(r"建议对照\s*PDF\s*人工核对|无法确定性还原|需人工核对")


@dataclass
class QualityGateResult:
    path: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_rag_markdown(
    text: str,
    *,
    path: str = "",
    minimum_body_chars: int = 200,
) -> QualityGateResult:
    """验证 selected Markdown 是否可发布；仅硬错误阻断。"""
    value = text or ""
    body = _COMMENT_RE.sub("", value).strip()
    pages = [int(number) for number in _PAGE_RE.findall(value)]
    source = _SOURCE_RE.search(value)
    experiment = _EXPERIMENT_RE.search(value)
    pua_count = len(_PUA_RE.findall(body))
    other_script_count = len(_OTHER_SCRIPT_RE.findall(body))
    replacement_count = body.count("�")
    unresolved_count = len(_UNRESOLVED_RE.findall(value))

    errors = []
    warnings = []
    if len(body) < minimum_body_chars:
        errors.append(f"正文过短：{len(body)} < {minimum_body_chars}")
    if not source or not source.group(1).strip():
        errors.append("缺少源文件元数据")
    if not experiment or not experiment.group(1).strip():
        errors.append("缺少实验名称元数据")
    if not pages:
        errors.append("缺少页码标记")
    elif pages != sorted(set(pages)):
        errors.append("页码标记重复或顺序异常")
    if pua_count:
        errors.append(f"正文残留 PUA 字符：{pua_count}")
    if other_script_count:
        errors.append(f"正文残留异常文字区字符：{other_script_count}")
    if replacement_count:
        errors.append(f"正文残留替换字符：{replacement_count}")
    if unresolved_count:
        errors.append(f"仍有未解决的人工核对标记：{unresolved_count}")

    scanned_markers = value.count("扫描页") + value.count("图片页")
    table_lines = sum(1 for line in body.splitlines() if line.count("|") >= 2)
    formula_lines = sum(
        1 for line in body.splitlines()
        if re.search(r"(?:\$[^$]+\$|\\frac|[=≈≠≤≥∑∫√])", line)
    )
    if scanned_markers:
        warnings.append(f"包含 {scanned_markers} 个扫描/图片页提示，请保留人工抽查记录")

    return QualityGateResult(
        path=path,
        passed=not errors,
        errors=errors,
        warnings=warnings,
        metrics={
            "body_chars": len(body),
            "page_markers": len(pages),
            "first_page": pages[0] if pages else None,
            "last_page": pages[-1] if pages else None,
            "pua_count": pua_count,
            "other_script_count": other_script_count,
            "replacement_count": replacement_count,
            "unresolved_review_markers": unresolved_count,
            "table_lines": table_lines,
            "formula_lines": formula_lines,
            "scan_markers": scanned_markers,
        },
    )
