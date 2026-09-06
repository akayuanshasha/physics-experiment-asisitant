"""统一前端框架的离线冒烟测试。

不调用外部 AI API，不生成正式报告，只验证插件注册、页面路由、表格 schema
和本地前端依赖是否可以被 Flask 正常提供。
"""

from __future__ import annotations

import os
import re
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main  # noqa: E402
from plugins import PluginRegistry  # noqa: E402


class UnifiedFrontendSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PluginRegistry.list_all():
            main.register_all_plugins()
        cls.client = main.app.test_client()

    def test_registry_contains_unique_experiment_ids(self):
        plugins = [PluginRegistry.get(name) for name in PluginRegistry.list_all()]
        module_ids = [getattr(plugin, "_mod_name", "") for plugin in plugins]
        self.assertEqual(53, len(plugins))
        self.assertTrue(all(module_ids))
        self.assertEqual(len(module_ids), len(set(module_ids)))

    def test_all_registered_experiments_are_b_modules(self):
        modules_root = os.path.realpath(os.path.join(PROJECT_ROOT, "b_modules"))
        for name in PluginRegistry.list_all():
            plugin = PluginRegistry.get(name)
            with self.subTest(module_id=plugin._mod_name):
                self.assertEqual("b_adapter", type(plugin).__module__)
                module = getattr(plugin, "_mod", None)
                self.assertIsNotNone(module)
                self.assertTrue(os.path.realpath(module.__file__).startswith(modules_root + os.sep))

    def test_every_experiment_page_and_table_info_loads(self):
        for name in PluginRegistry.list_all():
            plugin = PluginRegistry.get(name)
            module_id = plugin._mod_name
            with self.subTest(module_id=module_id):
                self.assertEqual(200, self.client.get(f"/experiment/{module_id}").status_code)
                response = self.client.get(f"/api/{module_id}/table-info")
                self.assertEqual(200, response.status_code)
                self.assertIsInstance(response.get_json(), dict)

    def test_representative_multitable_schemas(self):
        expected_tables = {
            "exp1": 2, "exp2": 3, "exp4": 4, "exp5": 2,
            "exp7": 4, "exp10": 3, "exp12": 4, "exp20": 4,
            "exp30": 3, "exp37": 4,
        }
        for module_id, minimum_count in expected_tables.items():
            with self.subTest(module_id=module_id):
                schema = self.client.get(f"/api/{module_id}/table-info").get_json()
                self.assertEqual(2, schema.get("schema_version"))
                self.assertGreaterEqual(len(schema.get("tables", [])), minimum_count)

    def test_every_experiment_owns_schema_handler_and_examples(self):
        for name in PluginRegistry.list_all():
            plugin = PluginRegistry.get(name)
            module_id = plugin._mod_name
            module = plugin._mod
            with self.subTest(module_id=module_id):
                self.assertTrue(callable(getattr(module, "schema", None)))
                self.assertTrue(callable(getattr(module, "handle_structured", None)))
                schema = module.schema()
                self.assertEqual(2, schema.get("schema_version"))
                # 外壳实验（指导书已收录但功能待开发）没有数据表，跳过表格断言
                if schema.get("shell"):
                    self.assertFalse(schema.get("tables"))
                    continue
                self.assertTrue(schema.get("tables"))
                for table in schema["tables"]:
                    self.assertTrue(table.get("columns"), table.get("id"))
                    self.assertTrue(table.get("sample"), table.get("id"))

    def test_table_info_has_no_external_csv_schema_fallback(self):
        import inspect

        with open(os.path.join(PROJECT_ROOT, "b_adapter.py"), encoding="utf-8") as handle:
            adapter_source = handle.read()
        endpoint_source = inspect.getsource(main.table_info)
        self.assertNotIn("_get_example_data", adapter_source)
        self.assertNotIn("schema_from_plugin", endpoint_source)
        self.assertNotIn("exampleData", endpoint_source)

    def test_guide_required_repetition_counts_are_encoded(self):
        lens = main._find_plugin_by_mod_name("exp20")._mod.schema()
        tables = {table["id"]: table for table in lens["tables"]}
        expected_shapes = {
            "convex_object_image": (7, 2),
            "convex_displacement": (7, 2),
            "convex_autocollimation": (6, 1),
            "concave_object_image": (4, 2),
        }
        for table_id, (input_count, readonly_count) in expected_shapes.items():
            with self.subTest(table_id=table_id):
                table = tables[table_id]
                self.assertEqual(1, table["min_rows"])
                columns = table["columns"]
                self.assertEqual(input_count, sum(not column.get("readonly") for column in columns))
                self.assertEqual(readonly_count, sum(bool(column.get("readonly")) for column in columns))

        activities = main._find_plugin_by_mod_name("exp25")._mod.schema()
        self.assertTrue(activities["shell"])
        self.assertEqual([], activities["tables"])
        self.assertFalse(activities["report_enabled"])
        self.assertFalse(activities["draft_enabled"])

    def test_secondary_experiments_are_owned_by_b_modules(self):
        modules_root = os.path.realpath(os.path.join(PROJECT_ROOT, "b_modules"))
        module_ids = [f"exp{number}" for number in range(26, 51) if number != 33]
        module_ids.extend(("exp33_a", "exp33_b"))
        for module_id in module_ids:
            with self.subTest(module_id=module_id):
                plugin = main._find_plugin_by_mod_name(module_id)
                module = getattr(plugin, "_mod", None)
                self.assertIsNotNone(module)
                self.assertEqual("b_adapter", type(plugin).__module__)
                self.assertTrue(os.path.realpath(module.__file__).startswith(modules_root + os.sep))
                self.assertTrue(callable(getattr(module, "schema", None)))
                self.assertTrue(callable(getattr(module, "handle_structured", None)))
                schema = self.client.get(f"/api/{module_id}/table-info").get_json()
                self.assertEqual(2, schema.get("schema_version"))
                if schema.get("shell"):
                    self.assertFalse(schema.get("tables"))
                else:
                    self.assertGreater(len(schema.get("tables", [])), 0)

    def test_exp33_is_split_by_guide_requirements(self):
        # exp33 按指导书要求拆分为 exp33_a / exp33_b（基础 exp33 目录保留共用指导文本）
        experiment_one = main._find_plugin_by_mod_name("exp33_a")
        experiment_two = main._find_plugin_by_mod_name("exp33_b")
        self.assertIsNotNone(experiment_one)
        self.assertIsNotNone(experiment_two)

        schema_one = experiment_one._mod.schema()
        self.assertTrue(schema_one.get("report_enabled"))
        self.assertEqual(
            ["billet_basic", "billet_enhanced"],
            [table["id"] for table in schema_one.get("tables", [])],
        )
        self.assertTrue(all(table.get("min_rows") == 3 for table in schema_one["tables"]))

        schema_two = experiment_two._mod.schema()
        self.assertFalse(schema_two.get("report_enabled"))
        self.assertTrue(schema_two.get("shell"))
        self.assertFalse(schema_two.get("tables"))

        # 拆分模块无独立资料目录时复用基础 exp33 的同一份指导文本
        guide_one = main._load_experiment_pdf_text("exp33_a")
        guide_two = main._load_experiment_pdf_text("exp33_b")
        self.assertTrue(guide_one)
        self.assertEqual(guide_one, guide_two)

        # 拆分模块应紧挨基础编号排列：exp33_a < exp33_b < exp34
        index_html = self.client.get("/").get_data(as_text=True)
        self.assertLess(index_html.index("/experiment/exp33_a"), index_html.index("/experiment/exp33_b"))
        self.assertLess(index_html.index("/experiment/exp33_b"), index_html.index("/experiment/exp34"))

        # 下划线实验编号应通过路径校验；文件不存在时应是404，而不是编号非法的400。
        self.assertEqual(
            404,
            self.client.get("/api/result-file/exp33_a/123/nonexistent.png").status_code,
        )

    def test_shared_frontend_contains_no_experiment_formulas(self):
        path = os.path.join(PROJECT_ROOT, "b_static", "js", "unified-experiment.js")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(re.search(r"\bexp\d+[a-z]?\b", source))
        for old_name in (
            "calculatePendulum", "calculateSurfaceTension", "calculateDensity", "calculateYoung",
            "calculateAC", "calculateDielectric", "calculateDigitalMeter", "calculateKelvin",
        ):
            self.assertNotIn(old_name, source)
        self.assertIn("/preview", source)

    def test_every_structured_schema_has_consistent_ids(self):
        for name in PluginRegistry.list_all():
            plugin = PluginRegistry.get(name)
            module_id = plugin._mod_name
            schema = self.client.get(f"/api/{module_id}/table-info").get_json()
            with self.subTest(module_id=module_id):
                self.assertEqual(2, schema.get("schema_version"))
                table_ids = [table.get("id") for table in schema.get("tables", [])]
                self.assertTrue(all(table_ids))
                self.assertEqual(len(table_ids), len(set(table_ids)))
                for table in schema.get("tables", []):
                    column_ids = [column.get("id") for column in table.get("columns", [])]
                    self.assertTrue(all(column_ids))
                    self.assertEqual(len(column_ids), len(set(column_ids)))
                    for sample in table.get("sample", []):
                        self.assertTrue(set(sample).issubset(set(column_ids)))
                    chart = table.get("chart")
                    if chart:
                        self.assertIn(chart.get("x_column"), column_ids)
                        # 多系列图表用 y_columns（列 ID 列表），单系列用 y_column
                        if chart.get("y_columns"):
                            for y_column in chart["y_columns"]:
                                self.assertIn(y_column, column_ids)
                        else:
                            self.assertIn(chart.get("y_column"), column_ids)

    def test_index_and_local_frontend_dependencies(self):
        index = self.client.get("/")
        self.assertEqual(200, index.status_code)
        self.assertEqual(53, index.data.count(b'class="experiment-card" href="/experiment/'))

        for url in (
            "/static/js/unified-experiment.js",
            "/static/js/rich-text-renderer.js",
            "/static/js/primary-navigation.js",
            "/static/css/rich-text.css",
            "/static/css/primary-navigation.css",
            "/static/vendor/markdown-it/markdown-it.min.js",
            "/static/vendor/dompurify/purify.min.js",
            "/static/vendor/mathjax/tex-mml-chtml-mathjax-newcm.js",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                try:
                    self.assertEqual(200, response.status_code)
                finally:
                    response.close()

    def test_primary_navigation_marks_the_current_page(self):
        index_html = self.client.get("/").get_data(as_text=True)
        chat_html = self.client.get("/chat").get_data(as_text=True)
        experiment_html = self.client.get("/experiment/exp20").get_data(as_text=True)

        self.assertIn('class="home-nav__link is-active" href="/" aria-current="page"', index_html)
        self.assertIn('class="home-nav__link is-active" href="/chat" aria-current="page"', chat_html)
        self.assertNotIn('class="home-nav"', experiment_html)

    def test_main_templates_do_not_require_external_cdn(self):
        for url in ("/chat", "/experiment/exp1", "/experiment/exp37"):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
            html = response.get_data(as_text=True)
            self.assertNotIn("cdn.jsdelivr.net", html)
            self.assertNotIn("cdnjs.cloudflare.com", html)
            self.assertNotIn("polyfill.io", html)
            if url.startswith("/experiment/"):
                self.assertIn('id="reportPdfFrame"', html)
                self.assertIn('/static/js/unified-experiment.js', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
