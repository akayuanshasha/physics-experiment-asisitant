"""统一的文档解析结果，隔离 Docling、MinerU 与传统 PDF 抽取器差异。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ParsedBlock:
    """页面中的最小结构单元。

    ``kind`` 使用少量稳定类型：text/title/list/table/formula/image/unknown。
    解析器特有字段放入 metadata，避免公共接口随第三方版本变化。
    """

    text: str
    kind: str = "text"
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        allowed = {"text", "title", "list", "table", "formula", "image", "unknown"}
        if self.kind not in allowed:
            raise ValueError(f"不支持的 ParsedBlock.kind: {self.kind}")


@dataclass
class ParsedPage:
    number: int
    blocks: list[ParsedBlock] = field(default_factory=list)
    width: float | None = None
    height: float | None = None
    is_scanned: bool = False
    column_count: int | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks if block.text).strip()

    @classmethod
    def from_text(
        cls,
        number: int,
        text: str,
        *,
        is_scanned: bool | None = None,
    ) -> "ParsedPage":
        value = text or ""
        scanned = not value.strip() if is_scanned is None else is_scanned
        blocks = [ParsedBlock(value)] if value else []
        warnings = ["页面无可检索文本，可能是扫描页或图片页"] if scanned else []
        return cls(number=number, blocks=blocks, is_scanned=scanned, warnings=warnings)


@dataclass
class ParsedDocument:
    source_path: str
    parser: str
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        numbers = [page.number for page in self.pages]
        if any(number < 1 for number in numbers):
            raise ValueError("页码必须从 1 开始")
        if len(numbers) != len(set(numbers)):
            raise ValueError("ParsedDocument 中存在重复页码")

    @property
    def page_texts(self) -> list[str]:
        return [page.text for page in sorted(self.pages, key=lambda page: page.number)]

    @property
    def text(self) -> str:
        return "\n\n".join(text for text in self.page_texts if text).strip()

    @property
    def scanned_pages(self) -> list[int]:
        return [page.number for page in self.pages if page.is_scanned]

    @classmethod
    def from_page_texts(
        cls,
        source_path: str | Path,
        parser: str,
        page_texts: Iterable[str],
        *,
        metadata: dict[str, Any] | None = None,
        warnings: Iterable[str] = (),
    ) -> "ParsedDocument":
        pages = [
            ParsedPage.from_text(index, text)
            for index, text in enumerate(page_texts, start=1)
        ]
        return cls(
            source_path=str(source_path),
            parser=parser,
            pages=pages,
            metadata=dict(metadata or {}),
            warnings=list(warnings),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
