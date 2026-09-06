"""Load and chunk formal experiment guides without using the legacy retriever."""

from __future__ import annotations

import hashlib
import csv
import json
import logging
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from query_aliases import detect_canonical_terms

from .models import Chunk


logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (_PROJECT_ROOT / path).resolve()


def _fingerprint_paths(
    paths: Iterable[tuple[Path, str]],
    *,
    options: dict[str, Any] | None = None,
) -> str:
    """Return a cheap, deterministic signature for a set of source files.

    Runtime refresh checks should not read every PDF on every request.  File
    identity, byte size and nanosecond mtime catch normal edits while keeping
    the check bounded by directory metadata.  The parsed chunk fingerprint in
    the benchmark remains the content-level verification for release reports.
    """
    records: list[tuple[str, int, int]] = []
    seen: set[Path] = set()
    for path, label in paths:
        try:
            resolved = path.resolve()
            if resolved in seen or not resolved.is_file():
                continue
            stat = resolved.stat()
        except OSError:
            # A file being replaced during a refresh must still change the
            # signature on the next check; retain a stable missing marker.
            records.append((f"{label}:{path}", -1, -1))
            continue
        seen.add(resolved)
        records.append((f"{label}:{resolved}", int(stat.st_size), int(stat.st_mtime_ns)))
    payload = {
        "version": 1,
        "files": sorted(records),
        "options": {
            str(key): options[key]
            for key in sorted(options or {})
        },
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def source_fingerprint(
    root: str | Path,
    *,
    reference_root: str | Path | None = None,
    include_example_data: bool = True,
    include_reference_materials: bool = True,
    options: dict[str, Any] | None = None,
) -> str:
    """Return a fast source-tree fingerprint used for runtime index refresh.

    The discovery set intentionally follows the supported RAG formats, so
    unrelated generated charts or reports do not rebuild the retrieval index.
    ``options`` should contain chunking/filter settings that change parsed
    output; callers can therefore use the same source tree with independent
    index generations safely.
    """
    root_path = _project_path(root)
    paths: list[tuple[Path, str]] = []
    authority_manifest = root_path.parent / KNOWLEDGE_SOURCE_MANIFEST_FILENAME
    if authority_manifest.is_file():
        paths.append((authority_manifest, "authority-manifest"))
    if root_path.is_dir():
        try:
            candidates = sorted(root_path.rglob("*"), key=lambda item: str(item))
        except OSError:
            candidates = []
        for path in candidates:
            if not path.is_file():
                continue
            if path.name == EXPERIMENT_MANIFEST_FILENAME or path.suffix.lower() in SUPPORTED_SUFFIXES:
                paths.append((path, "corpus"))

    if include_reference_materials:
        if reference_root is not None:
            reference_path = _project_path(reference_root)
        else:
            reference_path = _resolve_reference_root(root_path, None)
        if reference_path is not None and reference_path.is_dir():
            try:
                candidates = sorted(reference_path.rglob("*"), key=lambda item: str(item))
            except OSError:
                candidates = []
            for path in candidates:
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                    paths.append((path, "reference"))

    effective_options = {
        "include_example_data": bool(include_example_data),
        "include_reference_materials": bool(include_reference_materials),
        **(options or {}),
    }
    # Example data is discovered only when enabled.  The broad source scan
    # above includes it, so filter it here without duplicating discovery code.
    if not include_example_data:
        paths = [
            (path, label) for path, label in paths
            if not (label == "corpus" and path.suffix.lower() in TABLE_SUFFIXES)
        ]
    return _fingerprint_paths(paths, options=effective_options)


def chunk_fingerprint(chunks: Iterable[Chunk]) -> str:
    """Hash parsed chunk identity and content for reports and diagnostics."""
    records = []
    for chunk in sorted(chunks, key=lambda item: item.chunk_id):
        records.append({
            "chunk_id": chunk.chunk_id,
            "experiment_id": chunk.experiment_id,
            "experiment_name": chunk.experiment_name,
            "source": chunk.source,
            "section": chunk.section,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "source_tier": chunk.source_tier,
            "source_kind": chunk.source_kind,
            "authority": chunk.authority,
            "is_example_data": chunk.is_example_data,
            "text": chunk.text,
        })
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()

RAG_FILENAME = "实验指导_RAG文本.md"
LEGACY_FILENAME = "实验指导_提取文本.txt"
SUPPLEMENT_DIRECTORY = "RAG补充资料"
REFERENCE_DIRECTORY = "实验参考文档"
REVIEWED_REFERENCE_SUFFIX = "_RAG文本.md"
EXPERIMENT_MANIFEST_FILENAME = "_experiments_summary.json"
KNOWLEDGE_SOURCE_MANIFEST_FILENAME = "knowledge_sources.json"
TEXT_SUFFIXES = {".md", ".txt"}
RAW_DOCUMENT_SUFFIXES = {".pdf", ".docx"}
TABLE_SUFFIXES = {".csv"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | RAW_DOCUMENT_SUFFIXES | TABLE_SUFFIXES
_COMMENT_RE = re.compile(r"^\s*<!--.*?-->\s*$")
_PAGE_RE = re.compile(r"^\s*<!--\s*页码\s*:\s*(\d+)\s*-->")
_META_RE = re.compile(r"^\s*<!--\s*(实验名称|源文件)\s*:\s*(.*?)\s*-->")
_LEGACY_META_RE = re.compile(r"^(实验名称|源文件)\s*:\s*(.*?)\s*$")
_SECTION_NAMES = (
    "实验目的", "实验要求", "实验原理", "实验装置", "实验仪器",
    "实验内容", "实验步骤", "数据记录", "数据处理", "注意事项",
    "思考题", "实验报告", "参考资料", "能力培养", "实验任务",
    "预习测试", "入门测试", "出门测试", "出入门测", "考试说明",
    "题目", "答案", "评分标准", "实验目录",
)
_SECTION_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:第?[一二三四五六七八九十百0-9]+[、.．章节部分]\s*)?"
    + "(" + "|".join(map(re.escape, _SECTION_NAMES)) + r")[：:]?$"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；])")
_FORMULA_RE = re.compile(
    r"(?:\$\$?|\\\(|\\\)|\\\[|\\\]|\\begin\{|\\end\{|"
    r"[A-Za-zΑ-Ωα-ω][A-Za-zΑ-Ωα-ω0-9_{}^]*\s*[=≈≤≥≠]|"
    r"[=≈≤≥≠±×÷√∑∫])"
)
_FORMULA_INTRO_RE = re.compile(r"(?:公式|关系|表达式)?(?:为|如下|可得|则有|满足)[：:]?$" )
_FORMULA_TAIL_RE = re.compile(r"^(?:式中|其中|这里|由式|公式中|上式中)")
_MARKDOWN_TABLE_RULE_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")

_REMOTE_EMBEDDING_OVERSIZE_CHUNK_IDS = frozenset({
    "d1dd142e29a6355646b4",
    "124e79de60edfd20c010",
    "0ecb669106c25b763416",
    "315ddf76b4527d0f78f8",
    "6a4ef78527e409371ddd",
    "c003d855635ec1808c5f",
    "cca6b78eed00943e2ca9",
    "22ab192ff18ff51f31ea",
    "c801b1d3714372693aa9",
    "861252eb8cd04034348e",
    "7ce3d3800366d0e5bc83",
    "4d5132ccba49a28238fe",
    "6fed39500bfedf79a9f7",
    "f536a44bd948aeeb3ed7",
    "a8c3cfe2840c635f07d8",
    "107d63e7cd70a8a4a20b",
    "525dfefb1f93dca5eb5c",
    "65458b98320a13696bd1",
    "9db88ca8166d59584a01",
    "d7bd0606073a54161e82",
    "0eeacc6f2bbe01010de3",
    "2adffd10897ebac96e97",
    "a0d467456a23c8bb80ea",
    "049a5e51316c77807349",
    "2385df6a1d2a54a7ab74",
    "47897aff69c7eadfd667",
    "ee9e5618170c0f3c7369",
    "2d953e457812b8409016",
    "324991d1d1f90c5a6764",
    "b3aea8746e6e08d84bdc",
    "126c6f2f755b759eb62c",
    "f5cd24a6ecc956533d43",
    "44d70be042223894a078",
    "3e13602793000876d984",
    "0d01e13054f795cbf087",
    "2f8139c72e0b9cc0afe7",
    "6fe20fdf77e317a97a7a",
    "e09dad1369eb0e4cd78e",
    "dac03a99fe9714093de6",
    "7dd36955dde559cb07a2",
    "2881951a28012bbd3dcf",
    "f9c6ac82d7201246d7d3",
    "8c7d90366cb5dd672933",
    "b9625c7893ae499401ec",
    "d67c2b8aae81f877b20e",
    "adc812506de044a5f9ae",
    "62d62dbbc2616542c82b",
    "d0fcc0c3e64caa3ee3d7",
    "b9c6e17eac4d48ba9eec",
    "4c5ec5faa40387177bfd",
    "fd792ce38dfce7d407ff",
    "63b3227269da9e6385d8",
    "2b39da5657ca251fa032",
    "d74f66057dcc08b6435e",
    "7939407c2946033048ff",
    "9693ccbcec912ac782c6",
    "55a9802e49326cf336a6",
    "6a6bc5ce6254b4fd5115",
    "171e889c1f86840a448c",
    "f81c25d74494bcdc889d",
    "11617927d84a05c58208",
    "6973f3395997dc52f58c",
    "3439fd30a1c0c740052b",
    "921675b732db3a313ef2",
    "e18b5f47e3155e1db11f",
    "469f5c22afc79b5e52b4",
    "05998a993db3a4aa7ed6",
    "39a1ebbeca686e8203a9",
    "df6965b842d90b0bbbdc",
    "09ff9b54b52c9b8f9273",
    "6716af3320096913a0f1",
    "30547da0426f21bb4767",
    "99d011e8c89ad3a5d3a0",
    "00295cfb34dab32e81b4",
    "b85c17f9f7061b404eb6",
    "95d323964df0bd473065",
    "2f16f99de5775e34bbfb",
    "0dee028c74f641570722",
    "4b4e8055266d92443b20",
    "7eb57ae5d50c1ba38fa3",
    "a7cc9ff5d3870d4b8be3",
    "340f0884e82f67b04aab",
    "8be8742c48c9920bde44",
    "327e90d4d0888a4bd97d",
    "73198357095b6fae867a",
    "2709f2f4a9881892eb1c",
    "985986dd9b5142749fcd",
    "eb0d3436964be9389b1d",
    "189f28ce21906d56be8e",
    "0be4c447b2a77ae584ea",
    "7946ba5e1f86c3310f45",
    "f6a9b0f5376907ac3d8c",
    "4528a8e5bcd3cc423457",
    "b05611a9535573991a33",
    "c077c6d3294c3e68ddbd",
    "6bc6bd322b3826ea289b",
    "58870aab685794254ccd",
    "60034fd5496d04442c47",
    "939e2ee9caed859d15af",
    "8a7390faa590104e8489",
    "581bb5a6d406b8080279",
    "8d604a4bdc131fbb5d02",
    "9f0e9677f78baf7fd615",
    "cf9d4d1a73ca25da5eb3",
    "2d6db0dc92bcf4f606a2",
    "640669958bbdf1b98285",
    "92cd316b491fae39235b",
    "14c87cd973ed938d3b1c",
    "7e283cc5f1e961dc1f04",
    "b7d0229443e17bdca052",
    "ac1695ef758ff968a178",
    "8c13aacf75093f339847",
    "af2b6e74cde8ccb571af",
    "63c6821a99644241b9ea",
    "3654a105ff267e1a0c0b",
    "14d93b59c079813047de",
    "3dc8127785713f9f54c5",
    "8d348f54daecc3bc0cbe",
    "2fad1781b8edf7f77ef7",
    "7f8a0935f0e1f686f8cd",
    "0fa6ae4df2a1c136cece",
    "dc60815cda51fc529308",
    "e5c770f2e55ef75f1076",
    "0f1ccdc845be80ad9d6e",
    "2db3be441ba550ec1bed",
    "5f4836669163f355bb9b",
    "96ef33f8dcdaf706652d",
    "d3c4c864c29753370bf5",
    "51fc6f1c0e22fd2d1993",
    "5827975c999fda6ebbf5",
    "6272be9b824c06e7029c",
    "46b83c3bba7963ff7cd3",
    "7e765fa047ab29076331",
    "2d9907184642625fcd9c",
    "4ce3d918b0bac844a780",
    "d183013746a0b0c0cb61",
    "090e89fcf344dbb4f52d",
    "b66566f469fe370d1ff9",
    "1c9a07cb5b680bfadfeb",
    "75b6ba294e7763d16d00",
    "039e983ed8754afeb5b9",
    "dc2a9bf4328d2ff66c14",
    "4dba8129cfd59520693d",
    "ded0064059b49a005130",
    "019e4aee61c8884528e1",
    "19897ed661f87d4e4f31",
    "fc432da27652c8535763",
    "43407315410f20dff9df",
    "81753d59c9f6b5abdd7c",
    "1befc4ff3e9be58858c6",
    "465095530bfff16d2bce",
    "f36392f4891175197636",
    "e47fb6599474fc75f387",
    "bc93f5c453e572b76769",
    "bdebc52b33b83e0fe050",
    "38dbebd7f4260772b5ec",
    "c6a9ba87ada437a43e3d",
    "8c664f653dc032d2c57b",
    "e94f6909d69e1af63c95",
    "b6ca04a8671be8190bbc",
    "6a0e29ea52062dba811e",
    "6d80313fa9234f5fbc4c",
    "591a3b8b38f830e87fce",
    "d073a9c870d60c9f8711",
    "90aca7f9da973324169e",
    "26264b5b160817fc4118",
    "a0bf370bd9de809d8b92",
    "da7458a77638c152c2ef",
    "a7e6602ede7dd8cb79ad",
    "fc2097627bc181fde9a2",
    "41b4020a83134c1df3a8",
    "d481585ac248e8f0f2d1",
    "ebb3e51683ed30c1b0b0",
    "a5c24b0b958d9da1347b",
    "18999a597408730e60e7",
    "359538731dbb04a55e2f",
    "e1b74e027042987976da",
    "7e0d1b8667b39ce3bf3b",
    "4af027c2f53fe4c2d4d1",
    "d00d5528a2fc92754128",
    "93933d800bc1aa6d0245",
    "c50d83ea912c7819e17a",
    "4c5cd10c0ad325c70768",
    "4aef557e0a266f4fdcbf",
    "064bd3a424d0f788397b",
    "7d4aec4e217d05f7fdac",
    "83e6b77c07dfb3bb8a51",
    "6154deae9bae3ebe2f89",
    "e0db03b6062af650bd16",
    "59b2996a9e2b6333b9ec",
    "ca5656631a49b2d25f3d",
    "cf0a973f8e75bba7ae5a",
    "79640187524cd02b3e78",
    "ff146c9b9b1e023f4389",
    "7f8420a79b9f3cebf64e",
    "cda01e6ab94527d218c3",
    "de62d2bbf26485989375",
    "e0f410cec1c3a2049e39",
    "9c3a3d61f6420a5b7075",
    "8686b2284b226f501c6a",
    "d4591e000603f72c5250",
    "b3f7ca4efa395a47d1ae",
    "2da93acd446be7b67453",
    "92785f8f12b5b5c8f8fe",
    "57e2ffafe7d406866e8b",
    "7f8724da42726824ad52",
    "603814fb196dd4b5dfd6",
    "409d7f03e97e4ee5ee34",
    "087c43b2ad5c06848b91",
    "b5ec0bd1e4453bbeb3f4",
    "706d7239f1e541f1a20a",
    "ba0de09ce3a97974032b",
    "c9571f599365b23e6b0d",
    "9f82c4aa1955c279e04b",
    "783f7a16a80c7f2e4565",
    "c2ef3bafc17fa378c28c",
    "934a644f510a987bf2b0",
    "00586a06843163a70f7a",
    "f01b1380015f211d235f",
    "493089c075f2f8ddd728",
    "795e120def168880b9c6",
    "a748585b99ac86232368",
    "34bf319d53d12875b521",
    "b742702e08b598df2481",
    "33da42e2b7056b48db69",
    "81872aad1e3df3d41049",
    "34a405240d548bd2bef7",
    "1023841f7e5116768806",
    "f762b1759aa55628bdca",
    "6c9715d977186416ce10",
    "23805d4c5c51f06699d0",
    "a774bd0c5a6825cfb320",
    "318c73e49d6596b3f477",
    "4a6c30910d57bb285ad3",
    "2a2ff4252b9ef119bf77",
    "b6a183cee1cea642ac8c",
    "0a1c3a053fd127041e0f",
    "db8abcc7a6e9d83ca95e",
    "72981d7ff0ecb2bac1c1",
})
_REMOTE_EMBEDDING_RECHUNK_CHARS = 450
_REMOTE_EMBEDDING_RECHUNK_OVERLAP_CHARS = 50


@dataclass
class _Unit:
    text: str
    page: int | None
    section: str
    kind: str = "plain"


def _is_formula_line(text: str) -> bool:
    return bool(_FORMULA_RE.search(text or ""))


def _is_table_row(text: str) -> bool:
    value = str(text or "").strip()
    if _MARKDOWN_TABLE_RULE_RE.match(value):
        return True
    if value.count("|") >= 2 or value.count("\t") >= 2:
        return True
    return value.count(",") >= 2 and bool(re.search(r"\d", value))


def _smart_join(left: str, right: str) -> str:
    if not left or not right:
        return ""
    if left[-1].isascii() and right[0].isascii() and left[-1].isalnum() and right[0].isalnum():
        return " "
    return ""


def _source_name(filename: str) -> str:
    name = re.sub(r"[（(]?实验指导[）)]?", "", filename)
    name = re.sub(r"B$", "", Path(name).stem)
    return name.strip("-_（）() ")


def _canonical_experiment_name(raw_name: str | None, source: str, experiment_id: str) -> str:
    name = (raw_name or "").strip()
    if not name or re.fullmatch(r"exp\d+(?:_[a-z])?", name, re.I):
        name = _source_name(source)
    detected = detect_canonical_terms(f"{name} {_source_name(source)}")
    return detected["experiments"][0] if detected["experiments"] else name


class CorpusDocumentError(RuntimeError):
    """Raised when a supported source document cannot be parsed."""


def _read_records(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    records: list[tuple[int | None, str]] = []
    meta: dict[str, str] = {}
    page: int | None = None
    is_rag = path.suffix.lower() == ".md"
    before_separator = True
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if is_rag:
            page_match = _PAGE_RE.match(line)
            if page_match:
                page = int(page_match.group(1))
                continue
            meta_match = _META_RE.match(line)
            if meta_match:
                meta[meta_match.group(1)] = meta_match.group(2).strip()
                continue
            if _COMMENT_RE.match(line):
                continue
        elif before_separator:
            meta_match = _LEGACY_META_RE.match(line)
            if meta_match:
                meta[meta_match.group(1)] = meta_match.group(2).strip()
                continue
            if re.fullmatch(r"={20,}", line):
                before_separator = False
                continue
        records.append((page, line))
    return records, meta


def _extract_pdf_pages_pypdf(path: Path) -> list[str]:
    """Extract one text string per page using the lightweight PDF reader."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("未安装 PyPDF2 或 pypdf") from exc
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def _extract_pdf_pages_pdfplumber(path: Path) -> list[str]:
    import pdfplumber

    with pdfplumber.open(str(path)) as document:
        return [page.extract_text() or "" for page in document.pages]


def _extract_pdf_pages_fitz(path: Path) -> list[str]:
    import fitz

    with fitz.open(str(path)) as document:
        return [page.get_text() or "" for page in document]


def _read_pdf_records(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    """Read a PDF page by page, using optional extractors as fallbacks.

    PyPDF2 is the required baseline. pdfplumber and PyMuPDF are tried when the
    baseline is unavailable or returns an empty document, which lets the same
    corpus loader handle more PDF variants without making those heavier packages
    mandatory.
    """
    extractors = (
        ("pypdf2", _extract_pdf_pages_pypdf),
        ("pdfplumber", _extract_pdf_pages_pdfplumber),
        ("pymupdf", _extract_pdf_pages_fitz),
    )
    errors: list[str] = []
    empty_pages: list[str] | None = None
    for name, extractor in extractors:
        try:
            pages = extractor(path)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        if any(text.strip() for text in pages):
            records = [
                (page_number, line)
                for page_number, text in enumerate(pages, start=1)
                for line in text.splitlines()
            ]
            return records, {"解析器": name}
        empty_pages = pages
    if empty_pages is not None:
        return [], {"解析器": "empty"}
    detail = "; ".join(errors) or "没有可用的 PDF 解析器"
    raise CorpusDocumentError(f"PDF 解析失败: {path.name}; {detail}")


def _table_row_text(values: list[object]) -> str:
    cells = [
        ("" if value is None else str(value)).strip().replace("\n", " ")
        for value in values
    ]
    cells = [cell for cell in cells if cell]
    return " | ".join(cells)


def _read_docx_records(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    """Read paragraphs and tables from a DOCX while retaining body order."""
    try:
        from docx import Document
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as exc:
        raise CorpusDocumentError("DOCX 解析需要安装 python-docx") from exc

    document = Document(str(path))
    records: list[tuple[int | None, str]] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            value = Paragraph(child, document).text.strip()
            if value:
                records.append((None, value))
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            for row in table.rows:
                value = _table_row_text([cell.text for cell in row.cells])
                if value:
                    records.append((None, value))
    return records, {"解析器": "python-docx"}


def _read_csv_records(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    errors: list[str] = []
    rows: list[list[str]] | None = None
    for encoding in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                rows = list(csv.reader(handle))
            break
        except (OSError, UnicodeError, csv.Error) as exc:
            errors.append(f"{encoding}: {type(exc).__name__}: {exc}")
    if rows is None:
        raise CorpusDocumentError(
            f"CSV 解析失败: {path.name}; {'; '.join(errors)}"
        )
    records = []
    for row_number, row in enumerate(rows, start=1):
        value = _table_row_text(row)
        if value:
            records.append((None, value))
    return records, {"解析器": "csv", "行数": str(len(records))}


def _read_manifest_records(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CorpusDocumentError(f"实验目录清单解析失败: {path.name}: {exc}") from exc
    records: list[tuple[int | None, str]] = []
    if isinstance(data, dict):
        for experiment_id, item in sorted(data.items()):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            category = str(item.get("category") or "").strip()
            source = str(item.get("source_file") or "").strip()
            fields = [str(value) for value in (experiment_id, name, category, source) if value]
            if fields:
                records.append((None, " | ".join(fields)))
    return records, {"解析器": "json-manifest"}


def _read_document(path: Path) -> tuple[list[tuple[int | None, str]], dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return _read_records(path)
    if suffix == ".pdf":
        return _read_pdf_records(path)
    if suffix == ".docx":
        return _read_docx_records(path)
    if suffix == ".csv":
        return _read_csv_records(path)
    if path.name == EXPERIMENT_MANIFEST_FILENAME and suffix == ".json":
        return _read_manifest_records(path)
    raise CorpusDocumentError(f"不支持的资料格式: {path.name}")


def _records_to_units(
    records: list[tuple[int | None, str]], *, default_section: str = "实验指导"
) -> list[_Unit]:
    nonempty = [line.strip() for _, line in records if line.strip()]
    fragmentary = bool(nonempty) and sum(len(x) <= 2 for x in nonempty) / len(nonempty) >= 0.25
    units: list[_Unit] = []
    section = default_section
    buffer = ""
    buffer_page: int | None = None

    def flush() -> None:
        nonlocal buffer, buffer_page
        if buffer.strip():
            protected = _is_formula_line(buffer) or _is_table_row(buffer)
            parts = [buffer.strip()] if protected else _SENTENCE_SPLIT_RE.split(buffer.strip())
            for sentence in parts:
                if sentence.strip():
                    units.append(_Unit(
                        sentence.strip(), buffer_page, section,
                        "formula" if _is_formula_line(sentence) else (
                            "table" if _is_table_row(sentence) else "plain"
                        ),
                    ))
        buffer = ""
        buffer_page = None

    for page, raw_line in records:
        line = raw_line.strip()
        if not line:
            if not fragmentary:
                flush()
            continue
        match = _SECTION_RE.match(line)
        if match:
            flush()
            section = match.group(1)
            continue
        if _is_table_row(line):
            flush()
            if (
                units and units[-1].kind == "table"
                and units[-1].page == page and units[-1].section == section
            ):
                units[-1].text += "\n" + line
            else:
                units.append(_Unit(line, page, section, "table"))
            continue
        if _is_formula_line(line):
            flush()
            prefix = ""
            if (
                units and units[-1].kind == "plain"
                and units[-1].section == section
                and _FORMULA_INTRO_RE.search(units[-1].text)
            ):
                prefix = units.pop().text + "\n"
            units.append(_Unit(prefix + line, page, section, "formula"))
            continue
        if (
            units and units[-1].kind == "formula"
            and units[-1].section == section and _FORMULA_TAIL_RE.match(line)
        ):
            units[-1].text += "\n" + line
            continue
        if buffer and page != buffer_page and page is not None:
            flush()
        if not buffer:
            buffer, buffer_page = line, page
        else:
            buffer += _smart_join(buffer, line) + line
        if not fragmentary and (line.endswith(("。", "！", "？")) or len(buffer) >= 350):
            flush()
    flush()
    return units


def _split_long(text: str, maximum: int, overlap: int) -> list[str]:
    if len(text) <= maximum:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + maximum, len(text))
        if end < len(text):
            boundary = max(text.rfind(mark, start + maximum // 2, end) for mark in "。；，\n")
            if boundary >= start + maximum // 2:
                end = boundary + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [piece for piece in pieces if piece]


def _chunk_units(
    units: list[_Unit], *, experiment_id: str, experiment_name: str,
    source: str, target: int, maximum: int, overlap: int,
    source_tier: str = "primary", source_kind: str = "formal_guide",
    authority: str = "course_official", is_example_data: bool = False,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[_Unit] = []
    current_len = 0
    current_has_new_content = False

    def emit() -> None:
        nonlocal current, current_len, current_has_new_content
        if not current:
            return
        # After a flush, ``current`` contains only the overlap suffix. Do not
        # emit that suffix again when the source ends or before a new section;
        # it becomes part of the next real chunk only when new content arrives.
        if not current_has_new_content:
            current, current_len = [], 0
            return
        text = "\n".join(unit.text for unit in current).strip()
        pages = [unit.page for unit in current if unit.page is not None]
        section = current[0].section
        digest_input = f"{experiment_id}\0{source}\0{section}\0{min(pages) if pages else ''}\0{text}"
        chunk_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:20]
        chunks.append(Chunk(
            chunk_id=chunk_id, text=text, experiment_id=experiment_id,
            experiment_name=experiment_name, source=source, section=section,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            source_tier=source_tier,
            source_kind=source_kind,
            authority=authority,
            is_example_data=is_example_data,
        ))
        if overlap > 0:
            kept: list[_Unit] = []
            kept_len = 0
            for unit in reversed(current):
                # A formula/table can be larger than the overlap window. Do
                # not retain that whole unit, or the final flush would emit
                # the same oversized chunk a second time.
                if kept_len + len(unit.text) > overlap:
                    break
                kept.insert(0, unit)
                kept_len += len(unit.text)
            current, current_len = kept, kept_len
        else:
            current, current_len = [], 0
        current_has_new_content = False

    for unit in units:
        pieces = (
            [unit.text] if unit.kind in {"formula", "table"}
            else _split_long(unit.text, maximum, overlap)
        )
        for text in pieces:
            part = _Unit(text, unit.page, unit.section, unit.kind)
            section_changed = current and current[0].section != part.section
            would_overflow = current and current_len + len(text) + 1 > maximum
            if section_changed or would_overflow:
                emit()
                if section_changed:
                    current, current_len = [], 0
            current.append(part)
            current_len += len(text) + 1
            current_has_new_content = True
            if current_len >= target:
                emit()
    emit()
    linked: list[Chunk] = []
    for index, chunk in enumerate(chunks):
        parent_input = f"{experiment_id}\0{source}\0{chunk.section}"
        parent_id = hashlib.sha256(parent_input.encode("utf-8")).hexdigest()[:20]
        linked.append(replace(
            chunk,
            parent_id=parent_id,
            previous_chunk_id=(chunks[index - 1].chunk_id if index > 0 else None),
            next_chunk_id=(chunks[index + 1].chunk_id if index + 1 < len(chunks) else None),
        ))
    return linked


def _embedding_subchunk_id(parent_chunk_id: str, index: int, text: str) -> str:
    digest_input = f"{parent_chunk_id}\0remote-embedding-subchunk\0{index}\0{text}"
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:20]


def _rechunk_embedding_oversize_chunks(
    chunks: list[Chunk],
    *,
    chunk_ids: frozenset[str] = _REMOTE_EMBEDDING_OVERSIZE_CHUNK_IDS,
    maximum: int = _REMOTE_EMBEDDING_RECHUNK_CHARS,
    overlap: int = _REMOTE_EMBEDDING_RECHUNK_OVERLAP_CHARS,
) -> list[Chunk]:
    """Replace only remotely confirmed oversized chunks with deterministic children."""
    if not chunks or not chunk_ids:
        return chunks

    replacements: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        if chunk.chunk_id not in chunk_ids:
            continue
        pieces = _split_long(chunk.text, maximum, overlap)
        if len(pieces) <= 1:
            continue
        replacements[chunk.chunk_id] = [
            replace(
                chunk,
                chunk_id=_embedding_subchunk_id(chunk.chunk_id, index, text),
                text=text,
            )
            for index, text in enumerate(pieces)
        ]

    if not replacements:
        return chunks

    first_child = {
        chunk_id: children[0].chunk_id
        for chunk_id, children in replacements.items()
    }
    last_child = {
        chunk_id: children[-1].chunk_id
        for chunk_id, children in replacements.items()
    }

    def previous_id(chunk: Chunk) -> str | None:
        return last_child.get(chunk.previous_chunk_id or "", chunk.previous_chunk_id)

    def next_id(chunk: Chunk) -> str | None:
        return first_child.get(chunk.next_chunk_id or "", chunk.next_chunk_id)

    rechunked: list[Chunk] = []
    for chunk in chunks:
        children = replacements.get(chunk.chunk_id)
        if children is None:
            previous = previous_id(chunk)
            next_chunk = next_id(chunk)
            rechunked.append(
                replace(chunk, previous_chunk_id=previous, next_chunk_id=next_chunk)
                if (
                    previous != chunk.previous_chunk_id
                    or next_chunk != chunk.next_chunk_id
                )
                else chunk
            )
            continue

        for index, child in enumerate(children):
            previous = (
                children[index - 1].chunk_id if index > 0 else previous_id(chunk)
            )
            next_chunk = (
                children[index + 1].chunk_id
                if index + 1 < len(children)
                else next_id(chunk)
            )
            rechunked.append(replace(
                child,
                previous_chunk_id=previous,
                next_chunk_id=next_chunk,
            ))
    return rechunked


def _relative_source(path: Path, base: Path) -> str:
    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = Path(path.name)
    return str(relative).replace("\\", "/")


def _stable_reference_id(path: Path, root: Path) -> str:
    relative = _relative_source(path, root)
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", Path(relative).with_suffix("").as_posix())
    slug = slug.strip("_") or "document"
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:8]
    return f"reference:{slug[:80]}-{digest}"


def _reference_document_paths(root: Path) -> list[Path]:
    """Return reference sources, preferring reviewed sidecar Markdown.

    A file named ``资料_RAG文本.md`` is the reviewed representation of
    ``资料.pdf`` (or ``资料.docx``).  The raw document stays on disk for visual
    auditing but is not indexed a second time.
    """
    paths = [
        path for path in sorted(root.rglob("*"), key=lambda item: str(item))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    reviewed_raw_paths = {
        path.resolve()
        for path in paths
        if path.suffix.lower() in RAW_DOCUMENT_SUFFIXES
        and path.with_name(f"{path.stem}{REVIEWED_REFERENCE_SUFFIX}").is_file()
    }
    return [path for path in paths if path.resolve() not in reviewed_raw_paths]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_policy_map(root_path: Path) -> dict[Path, dict[str, Any]]:
    """Load the reviewed source classification for paths used by the index."""
    manifest_path = root_path.parent / KNOWLEDGE_SOURCE_MANIFEST_FILENAME
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CorpusDocumentError(f"知识资料清单解析失败: {manifest_path}: {exc}") from exc
    sources = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(sources, list):
        raise CorpusDocumentError("知识资料清单缺少 sources 数组")
    policies: dict[Path, dict[str, Any]] = {}
    for item in sources:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        index_path = str(item.get("index_path") or "").strip()
        if not index_path:
            continue
        policies[_project_path(index_path).resolve()] = item
    return policies


def _resolved_source_policy(
    path: Path, *, default_section: str, experiment_id: str,
    policies: dict[Path, dict[str, Any]],
) -> dict[str, Any]:
    item = policies.get(path.resolve(), {})
    if item:
        priority = str(item.get("priority") or "primary")
        kind = str(item.get("source_kind") or "formal_guide")
        official = bool(item.get("authoritative_for_course_requirements", False))
        return {
            "source_tier": priority,
            "source_kind": kind,
            "authority": "course_official" if official else (
                "example_only" if priority == "example" else "supplementary"
            ),
            "is_example_data": priority == "example" or kind == "example_data",
        }
    if default_section == "示例数据":
        return {
            "source_tier": "example", "source_kind": "example_data",
            "authority": "example_only", "is_example_data": True,
        }
    if experiment_id.startswith("reference:"):
        return {
            "source_tier": "secondary", "source_kind": "reference",
            "authority": "supplementary", "is_example_data": False,
        }
    return {
        "source_tier": "primary", "source_kind": "formal_guide",
        "authority": "course_official", "is_example_data": False,
    }


def corpus_source_hashes(
    root: str | Path = "b_static/experiment", *,
    reference_root: str | Path | None = None,
) -> set[str]:
    """Hash physical system-corpus files for cross-corpus deduplication.

    Raw PDFs covered by reviewed Markdown are intentionally included.  This
    means a browser upload identical to such a PDF is not indexed again even
    though the system index itself reads the reviewed Markdown sidecar.
    """
    root_path = _project_path(root)
    roots = [root_path]
    resolved_reference_root = _resolve_reference_root(root_path, reference_root)
    if resolved_reference_root is not None:
        roots.append(resolved_reference_root)

    hashes: set[str] = set()
    seen: set[Path] = set()
    for source_root in roots:
        if not source_root.is_dir():
            continue
        for path in source_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                hashes.add(_file_sha256(path))
            except OSError as exc:
                logger.warning("计算 RAG 资料哈希失败 %s：%s", path, exc)
    return hashes


def _document_paths_for_experiment(
    directory: Path, *, include_example_data: bool,
) -> list[tuple[Path, str]]:
    """Return canonical and supplementary files for one experiment.

    A reviewed RAG Markdown file wins over its legacy text and raw guide. If
    keeps one guide from being indexed three times while still covering every
    source for which no reviewed extraction has been published.
    """
    documents: list[tuple[Path, str]] = []
    primary: Path | None = None
    reviewed = directory / RAG_FILENAME
    legacy = directory / LEGACY_FILENAME
    if reviewed.is_file():
        primary = reviewed
        documents.append((reviewed, "实验指导"))
    elif legacy.is_file():
        primary = legacy
        documents.append((legacy, "实验指导"))
    else:
        raw_guides = sorted(
            path for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in RAW_DOCUMENT_SUFFIXES
        )
        documents.extend((path, "实验指导") for path in raw_guides)

    # Include custom text files placed directly in an experiment directory.
    known_names = {RAG_FILENAME, LEGACY_FILENAME}
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if (
            path.is_file()
            and path.name not in known_names
            and path.suffix.lower() in TEXT_SUFFIXES
        ):
            documents.append((path, "参考资料"))

    if include_example_data:
        documents.extend(
            (path, "示例数据")
            for path in sorted(directory.iterdir(), key=lambda item: item.name)
            if path.is_file() and path.suffix.lower() in TABLE_SUFFIXES
        )

    supplement_root = directory / SUPPLEMENT_DIRECTORY
    if supplement_root.is_dir():
        documents.extend(
            (path, "参考资料")
            for path in sorted(supplement_root.rglob("*"), key=lambda item: str(item))
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )

    # A path should be read at most once even if it matches two discovery rules.
    unique: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for path, section in documents:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append((path, section))
    return unique


def _append_document_chunks(
    chunks: list[Chunk], path: Path, *, experiment_id: str,
    experiment_name_hint: str | None, default_section: str,
    source_base: Path, target_chars: int, max_chars: int, overlap_chars: int,
    source_override: str | None = None,
    source_policies: dict[Path, dict[str, Any]] | None = None,
) -> str | None:
    """Parse one source and append its chunks; return its resolved name."""
    try:
        records, meta = _read_document(path)
    except Exception as exc:
        logger.warning("RAG 资料跳过 %s：%s", path, exc)
        return experiment_name_hint
    if not records:
        logger.warning("RAG 资料没有可检索文本：%s", path)
        return experiment_name_hint
    source = (
        meta.get("源文件")
        or source_override
        or _relative_source(path, source_base)
    )
    experiment_name = _canonical_experiment_name(
        meta.get("实验名称") or experiment_name_hint,
        source,
        experiment_id,
    )
    units = _records_to_units(records, default_section=default_section)
    policy = _resolved_source_policy(
        path,
        default_section=default_section,
        experiment_id=experiment_id,
        policies=source_policies or {},
    )
    chunks.extend(_chunk_units(
        units,
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        source=source,
        target=target_chars,
        maximum=max_chars,
        overlap=overlap_chars,
        **policy,
    ))
    return experiment_name


def _resolve_reference_root(root_path: Path, reference_root: str | Path | None) -> Path | None:
    if reference_root is not None:
        candidate = _project_path(reference_root)
        return candidate if candidate.is_dir() else None
    for candidate in (root_path / REFERENCE_DIRECTORY, root_path.parent / REFERENCE_DIRECTORY):
        if candidate.is_dir():
            return candidate
    return None


def load_corpus(
    root: str | Path = "b_static/experiment", *, target_chars: int = 700,
    max_chars: int = 1000, overlap_chars: int = 100,
    reference_root: str | Path | None = None,
    include_example_data: bool = True,
    include_reference_materials: bool = True,
) -> list[Chunk]:
    """Load all local knowledge materials into stable, page-aware chunks.

    Reviewed RAG Markdown remains the canonical representation of a formal
    guide. Raw PDF/DOCX guides are used when a reviewed/legacy text file is
    absent. CSV examples, nested supplementary files and the sibling
    ``实验参考文档`` directory are included as independent sources.
    """
    root_path = _project_path(root)
    source_policies = _source_policy_map(root_path)
    chunks: list[Chunk] = []
    for directory in sorted(root_path.glob("exp*"), key=lambda p: p.name):
        if not directory.is_dir():
            continue
        documents = _document_paths_for_experiment(
            directory, include_example_data=include_example_data,
        )
        experiment_name: str | None = None
        for path, section in documents:
            experiment_name = _append_document_chunks(
                chunks,
                path,
                experiment_id=directory.name,
                experiment_name_hint=experiment_name,
                default_section=section,
                source_base=directory,
                target_chars=target_chars,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
                source_policies=source_policies,
            ) or experiment_name

    # The manifest is useful searchable context for experiment names/categories.
    manifest = root_path / EXPERIMENT_MANIFEST_FILENAME
    if manifest.is_file():
        _append_document_chunks(
            chunks,
            manifest,
            experiment_id="reference:experiment-summary",
            experiment_name_hint="实验目录",
            default_section="实验目录",
            source_base=root_path,
            target_chars=target_chars,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            source_override=manifest.name,
            source_policies=source_policies,
        )

    if include_reference_materials:
        reference_path = _resolve_reference_root(root_path, reference_root)
        if reference_path is not None:
            for path in _reference_document_paths(reference_path):
                _append_document_chunks(
                    chunks,
                    path,
                    experiment_id=_stable_reference_id(path, reference_path),
                    experiment_name_hint=path.stem,
                    default_section="参考资料",
                    source_base=reference_path.parent,
                    target_chars=target_chars,
                    max_chars=max_chars,
                    overlap_chars=overlap_chars,
                    source_override=_relative_source(path, reference_path.parent),
                    source_policies=source_policies,
                )
    return _rechunk_embedding_oversize_chunks(chunks)
