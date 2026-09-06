from __future__ import annotations

import re
import unittest
from pathlib import Path

from online_rag import evaluate_rag_markdown


REFERENCE_ROOT = Path(__file__).resolve().parents[1] / "b_static" / "实验参考文档"


class ReviewedReferenceMaterialTest(unittest.TestCase):
    EXPECTED_PAGES = {
        "大雾实验不完全指北_RAG文本.md": 75,
        "一级大雾出入门测_RAG文本.md": 54,
        "二级大雾出入门测11.7_RAG文本.md": 36,
    }

    def test_reviewed_markdown_has_every_pdf_page(self):
        for filename, expected_pages in self.EXPECTED_PAGES.items():
            with self.subTest(filename=filename):
                text = (REFERENCE_ROOT / filename).read_text(encoding="utf-8")
                markers = [int(value) for value in re.findall(r"<!--\s*页码\s*:\s*(\d+)\s*-->", text)]
                self.assertEqual(markers, list(range(1, expected_pages + 1)))
                self.assertTrue(evaluate_rag_markdown(text, path=filename).passed)

    def test_visually_verified_formula_examples_are_present(self):
        guide = (REFERENCE_ROOT / "大雾实验不完全指北_RAG文本.md").read_text(encoding="utf-8")
        level1 = (REFERENCE_ROOT / "一级大雾出入门测_RAG文本.md").read_text(encoding="utf-8")
        level2 = (REFERENCE_ROOT / "二级大雾出入门测11.7_RAG文本.md").read_text(encoding="utf-8")

        self.assertIn(r"u_A=\sigma_{\bar{x}}/\sqrt{n}", guide)
        self.assertIn(r"n_p\sin\theta_{sp}", guide)
        self.assertIn(r"\rho=\frac{m}{V}", level1)
        self.assertIn(r"FF=\frac{U_mI_m}{U_{oc}I_{sc}}", level1)
        self.assertIn(r"I=I_0\cos^2\theta", level2)
        self.assertIn(r"\omega L=1/(\omega C)", level2)

    def test_verified_corrections_override_recognizer_and_source_typos(self):
        guide = (REFERENCE_ROOT / "大雾实验不完全指北_RAG文本.md").read_text(encoding="utf-8")
        level1 = (REFERENCE_ROOT / "一级大雾出入门测_RAG文本.md").read_text(encoding="utf-8")
        level2 = (REFERENCE_ROOT / "二级大雾出入门测11.7_RAG文本.md").read_text(encoding="utf-8")

        self.assertIn(r"100.02147\pm0.00079", guide)
        self.assertNotIn("0.000079", guide)
        self.assertIn(r"正确单位应为 $\mathrm{N\cdot m}$", guide)
        self.assertIn(r"I/e=3.5\times10^{15}", level1)
        self.assertIn(r"第二问最大动能为 $6.01\times10^{-19}\,\mathrm{J}$", level1)
        self.assertIn("不自动改成大写", level1)
        self.assertNotIn("原文字符按电流", level2)


if __name__ == "__main__":
    unittest.main()
