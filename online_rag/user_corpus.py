"""Load one browser user's uploaded documents into isolated RAG chunks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Collection

from .corpus import _Unit, _chunk_units
from .models import Chunk


SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".pdf"}
MAX_USER_CORPUS_FILE_BYTES = 50 * 1024 * 1024
MAX_USER_CORPUS_PDF_PAGES = 1000


class UserCorpusValidationError(ValueError):
    """Raised when an uploaded knowledge file cannot be safely indexed."""


def validate_user_corpus_file(
    path: str | Path,
    *,
    max_bytes: int = MAX_USER_CORPUS_FILE_BYTES,
    max_pdf_pages: int = MAX_USER_CORPUS_PDF_PAGES,
) -> None:
    """Validate size and readability before publishing an uploaded file."""
    resolved = Path(path)
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UserCorpusValidationError("不支持该文件格式")
    size = resolved.stat().st_size
    if size <= 0:
        raise UserCorpusValidationError("文件内容为空")
    if size > max_bytes:
        raise UserCorpusValidationError("单个知识资料不能超过 50 MiB")
    try:
        if resolved.suffix.lower() == ".pdf":
            from PyPDF2 import PdfReader

            reader = PdfReader(str(resolved))
            if reader.is_encrypted:
                raise UserCorpusValidationError("暂不支持加密 PDF")
            if len(reader.pages) > max_pdf_pages:
                raise UserCorpusValidationError("PDF 不能超过 1000 页")
            for page in reader.pages:
                page.extract_text()
        else:
            resolved.read_text(encoding="utf-8-sig", errors="replace")
    except UserCorpusValidationError:
        raise
    except Exception as exc:
        raise UserCorpusValidationError(
            f"文件无法解析（{type(exc).__name__}）"
        ) from exc


def _pages(path: Path) -> list[str]:
    if path.suffix.lower() == ".pdf":
        from PyPDF2 import PdfReader
        return [(page.extract_text() or "") for page in PdfReader(str(path)).pages]
    return [path.read_text(encoding="utf-8-sig", errors="replace")]


def load_user_corpus(
    root: str | Path,
    user_id: str,
    *,
    target_chars: int = 700,
    max_chars: int = 1000,
    overlap_chars: int = 100,
    warnings: list[str] | None = None,
    excluded_content_hashes: Collection[str] = (),
    duplicate_chunks: list[Chunk] | None = None,
) -> list[Chunk]:
    """Load one user's uploads into retrieval chunks.

    与系统语料或已有上传内容重复的文件不进入返回值（避免重复索引，
    且系统语料可能对应已审核的 Markdown 版本），但仍会切块写入
    `duplicate_chunks`，供“问题指向上传资料”时按上传原文直接引用。
    """
    directory = Path(root) / user_id
    if not directory.is_dir():
        return []
    chunks: list[Chunk] = []
    seen_hashes = set(excluded_content_hashes)
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        units = []
        try:
            validate_user_corpus_file(path)
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            duplicated = content_hash in seen_hashes
            seen_hashes.add(content_hash)
            pages = _pages(path)
        except Exception as exc:
            if warnings is not None:
                warnings.append(
                    f"已跳过无法读取的上传资料“{path.name}”（{type(exc).__name__}）"
                )
            continue
        for page_number, text in enumerate(pages, start=1):
            for paragraph in text.splitlines():
                value = paragraph.strip()
                if value:
                    units.append(_Unit(value, page_number, "用户知识库"))
        file_chunks = _chunk_units(
            units,
            experiment_id=f"user:{user_id}",
            experiment_name=path.stem,
            source=path.name,
            target=target_chars,
            maximum=max_chars,
            overlap=overlap_chars,
            source_tier="primary",
            source_kind="user_upload",
            authority="user_provided",
            is_example_data=False,
        )
        if duplicated:
            if duplicate_chunks is not None:
                duplicate_chunks.extend(file_chunks)
            if warnings is not None:
                warnings.append(
                    f"上传资料“{path.name}”与已有资料内容相同，未重复索引，"
                    "提问该资料时按上传原文引用"
                )
            continue
        chunks.extend(file_chunks)
    return chunks
