from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import hashlib

from online_rag import (
    ParsedBlock,
    ParsedDocument,
    ParsedPage,
    SQLiteSessionStore,
    UserCorpusValidationError,
    evaluate_rag_markdown,
    load_user_corpus,
    validate_user_corpus_file,
)


class ParsedDocumentTest(unittest.TestCase):
    def test_page_texts_are_normalized_through_one_model(self):
        document = ParsedDocument.from_page_texts(
            "guide.pdf", "test-parser", ["第一页", "第二页"]
        )

        self.assertEqual(document.page_texts, ["第一页", "第二页"])
        self.assertEqual(document.pages[0].number, 1)
        self.assertEqual(document.parser, "test-parser")

    def test_structured_blocks_preserve_table_formula_and_scan_state(self):
        document = ParsedDocument(
            source_path="guide.pdf",
            parser="structured-parser",
            pages=[
                ParsedPage(1, [
                    ParsedBlock("|x|y|", kind="table"),
                    ParsedBlock("E=mc²", kind="formula"),
                ]),
                ParsedPage(2, [], is_scanned=True),
            ],
        )

        self.assertIn("E=mc²", document.text)
        self.assertEqual(document.scanned_pages, [2])
        self.assertEqual(document.to_dict()["pages"][0]["blocks"][0]["kind"], "table")


class QualityGateTest(unittest.TestCase):
    def _valid_text(self):
        return (
            "<!-- rag-extracted: v1 -->\n"
            "<!-- 实验名称: 单摆 -->\n"
            "<!-- 源文件: 单摆.pdf -->\n"
            "<!-- 页码:1 -->\n"
            "实验原理\n" + "单摆周期用于测量重力加速度。" * 20
        )

    def test_valid_reviewed_markdown_passes(self):
        result = evaluate_rag_markdown(self._valid_text(), path="exp1.md")

        self.assertTrue(result.passed)
        self.assertEqual(result.metrics["page_markers"], 1)

    def test_unresolved_pua_and_review_marker_block_publication(self):
        result = evaluate_rag_markdown(
            self._valid_text() + "\n\uf061\n建议对照 PDF 人工核对"
        )

        self.assertFalse(result.passed)
        self.assertTrue(any("PUA" in error for error in result.errors))
        self.assertTrue(any("人工核对" in error for error in result.errors))

    def test_missing_source_and_page_markers_block_publication(self):
        result = evaluate_rag_markdown("正文" * 200)

        self.assertFalse(result.passed)
        self.assertIn("缺少源文件元数据", result.errors)
        self.assertIn("缺少页码标记", result.errors)


class PersistenceAndIsolationTest(unittest.TestCase):
    def test_sqlite_sessions_persist_and_are_scoped_by_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.sqlite3"
            first = SQLiteSessionStore(path)
            first.set("user-a", "same-session", [{"role": "user", "content": "A"}])
            first.set("user-b", "same-session", [{"role": "user", "content": "B"}])
            reopened = SQLiteSessionStore(path)

            self.assertEqual(reopened.get("user-a", "same-session")[0]["content"], "A")
            self.assertEqual(reopened.get("user-b", "same-session")[0]["content"], "B")
            reopened.delete("user-a", "same-session")
            self.assertEqual(reopened.get("user-a", "same-session"), [])
            self.assertTrue(reopened.get("user-b", "same-session"))

    def test_sqlite_session_ttl_expires_old_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.sqlite3"
            store = SQLiteSessionStore(path, ttl_seconds=10)
            with patch("online_rag.session_store.time.time", return_value=100.0):
                store.set("user-a", "session", [{"role": "user", "content": "A"}])
            with patch("online_rag.session_store.time.time", return_value=111.0):
                self.assertEqual(store.get("user-a", "session"), [])

    def test_uploaded_corpus_only_loads_requested_user_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "user-a").mkdir()
            (root / "user-b").mkdir()
            (root / "user-a" / "a.txt").write_text("甲用户的独有资料。", encoding="utf-8")
            (root / "user-b" / "b.txt").write_text("乙用户的独有资料。", encoding="utf-8")

            chunks = load_user_corpus(root, "user-a")

            self.assertTrue(chunks)
            self.assertTrue(all(chunk.experiment_id == "user:user-a" for chunk in chunks))
            self.assertIn("甲用户", "".join(chunk.text for chunk in chunks))
            self.assertNotIn("乙用户", "".join(chunk.text for chunk in chunks))

    def test_invalid_uploaded_pdf_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "user-a"
            directory.mkdir()
            invalid = directory / "broken.pdf"
            invalid.write_bytes(b"not a pdf")
            warnings = []

            with self.assertRaises(UserCorpusValidationError):
                validate_user_corpus_file(invalid)
            chunks = load_user_corpus(root, "user-a", warnings=warnings)

            self.assertEqual(chunks, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("broken.pdf", warnings[0])

    def test_uploaded_file_size_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.txt"
            path.write_bytes(b"1234")
            with self.assertRaisesRegex(UserCorpusValidationError, "50 MiB"):
                validate_user_corpus_file(path, max_bytes=3)

    def test_user_corpus_skips_system_and_same_user_hash_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "user-a"
            directory.mkdir()
            duplicate_text = "与系统资料完全相同。"
            system_hash = hashlib.sha256(duplicate_text.encode("utf-8")).hexdigest()
            (directory / "a.txt").write_text(duplicate_text, encoding="utf-8")
            (directory / "b.txt").write_text(duplicate_text, encoding="utf-8")
            (directory / "unique.txt").write_text("用户独有资料。", encoding="utf-8")
            warnings = []

            chunks = load_user_corpus(
                root,
                "user-a",
                warnings=warnings,
                excluded_content_hashes={system_hash},
            )

            self.assertEqual({chunk.source for chunk in chunks}, {"unique.txt"})
            self.assertEqual(len(warnings), 2)
            self.assertTrue(all("重复" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
