"""统一前端框架的离线冒烟测试。

不调用外部 AI API，不生成正式报告，只验证插件注册、页面路由、表格 schema
和本地前端依赖是否可以被 Flask 正常提供。
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
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
        self.assertEqual(74, len(plugins))
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
            "exp1b": 2, "exp2a": 3, "exp4a": 4, "exp5": 3,
            "exp7": 4, "exp10": 4, "exp12": 6, "exp20": 5, "exp21": 3,
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
        minimums = {table["id"]: table["min_rows"] for table in lens["tables"]}
        self.assertEqual(6, minimums["convex_object_image"])
        self.assertEqual(6, minimums["convex_displacement"])
        self.assertEqual(6, minimums["convex_autocollimation"])
        self.assertEqual(3, minimums["concave_object_image"])

        activities = main._find_plugin_by_mod_name("exp25")._mod.schema()["tables"][0]
        self.assertEqual(7, activities["min_rows"])

    def test_secondary_experiments_are_owned_by_b_modules(self):
        modules_root = os.path.realpath(os.path.join(PROJECT_ROOT, "b_modules"))
        for number in range(26, 51):
            module_id = f"exp{number}"
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
                self.assertGreater(len(schema.get("tables", [])), 0)

    def test_migrated_big1_experiments_are_owned_by_b_modules(self):
        modules_root = os.path.realpath(os.path.join(PROJECT_ROOT, "b_modules"))
        for module_id in ("exp1b", "exp2a", "exp4a", "exp5"):
            with self.subTest(module_id=module_id):
                plugin = main._find_plugin_by_mod_name(module_id)
                module = getattr(plugin, "_mod", None)
                self.assertIsNotNone(module)
                self.assertEqual("b_adapter", type(plugin).__module__)
                self.assertTrue(os.path.realpath(module.__file__).startswith(modules_root + os.sep))
                self.assertTrue(callable(getattr(module, "schema", None)))
                self.assertTrue(callable(getattr(module, "preview", None)))
                self.assertTrue(callable(getattr(module, "handle_structured", None)))
                schema = self.client.get(f"/api/{module_id}/table-info").get_json()
                self.assertEqual(2, schema.get("schema_version"))
                self.assertGreater(len(schema.get("tables", [])), 1)

    def test_migrated_big1_sample_submissions_generate_documents(self):
        for module_id in ("exp1b", "exp2a", "exp4a", "exp5"):
            with self.subTest(module_id=module_id), tempfile.TemporaryDirectory() as workdir:
                plugin = main._find_plugin_by_mod_name(module_id)
                module = plugin._mod
                schema = module.schema()
                payload = {
                    "schema_version": 2,
                    "parameters": {item["id"]: item.get("default", "") for item in schema.get("parameters", [])},
                    "tables": {table["id"]: table.get("sample", []) for table in schema.get("tables", [])},
                }
                result = module.handle_structured(workdir + os.sep, payload)
                self.assertEqual(0, result.get("code"), result)
                self.assertTrue(os.path.isfile(os.path.join(workdir, result["document"])))

    def test_module_owned_schema_samples_generate_documents(self):
        module_ids = ("exp0a", "exp0b", "exp7", "exp10", "exp12", "exp16a", "exp20", "exp21", "exp24b", "exp25")
        for module_id in module_ids:
            with self.subTest(module_id=module_id), tempfile.TemporaryDirectory() as workdir:
                module = main._find_plugin_by_mod_name(module_id)._mod
                schema = module.schema()
                payload = {
                    "schema_version": 2,
                    "parameters": {item["id"]: item.get("default", "") for item in schema.get("parameters", [])},
                    "tables": {table["id"]: table.get("sample", []) for table in schema.get("tables", [])},
                }
                result = module.handle_structured(workdir + os.sep, payload)
                self.assertEqual(0, result.get("code"), result)
                self.assertTrue(os.path.isfile(os.path.join(workdir, result["document"])))

    def test_migrated_big1_has_no_active_legacy_registration(self):
        adapter_path = os.path.join(PROJECT_ROOT, "b_adapter.py")
        overrides_path = os.path.join(PROJECT_ROOT, "experiment_schema_overrides.py")
        with open(adapter_path, encoding="utf-8") as handle:
            self.assertNotIn("_CUSTOM_PLUGIN_MODULE_IDS", handle.read())
        with open(overrides_path, encoding="utf-8") as handle:
            override_source = handle.read()
        for module_id in ("exp1b", "exp2a", "exp4a", "exp5"):
            self.assertNotIn(f'"{module_id}"', override_source)
        plugins_dir = os.path.join(PROJECT_ROOT, "plugins")
        for filename in os.listdir(plugins_dir):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            with open(os.path.join(plugins_dir, filename), encoding="utf-8") as handle:
                self.assertNotIn("@PluginRegistry.register", handle.read())

    def test_backend_preview_preserves_computed_columns(self):
        expected = {
            "exp1b": ("table1", "c3", "81.1000"),
            "exp2a": ("table1", "c2", "0.0000"),
            "exp4a": ("table1", "c7", "2.0030"),
            "exp5": ("table2", "c3", "5.190"),
            "exp29": ("table1", "c4", "3.50000"),
            "exp30": ("table1", "c3", "3.99811"),
            "exp31": ("table2", "c2", "9.99900"),
            "exp32": ("table3", "c3", "0.000007"),
        }
        for module_id, (table_id, column_id, value) in expected.items():
            with self.subTest(module_id=module_id):
                schema = self.client.get(f"/api/{module_id}/table-info").get_json()
                payload = {
                    "schema_version": 2,
                    "parameters": {item["id"]: item.get("default", "") for item in schema.get("parameters", [])},
                    "tables": {table["id"]: table.get("sample", []) for table in schema.get("tables", [])},
                }
                response = self.client.post(f"/api/{module_id}/preview", json=payload)
                self.assertEqual(200, response.status_code)
                result = response.get_json()
                self.assertEqual(0, result.get("code"))
                self.assertEqual(value, str(result["tables"][table_id][0][column_id]))

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
                        self.assertIn(chart.get("y_column"), column_ids)

    def test_index_and_local_frontend_dependencies(self):
        index = self.client.get("/")
        self.assertEqual(200, index.status_code)
        self.assertEqual(74, index.data.count(b'class="experiment-card"'))

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

        self.assertIn('data-current="experiments"', index_html)
        self.assertIn('data-active="experiments"', index_html)
        self.assertIn('data-current="assistant"', chat_html)
        self.assertIn('data-active="assistant"', chat_html)
        self.assertIn('/static/js/primary-navigation.js', index_html)
        self.assertIn('/static/js/primary-navigation.js', chat_html)
        self.assertNotIn('data-primary-switcher', experiment_html)

    def test_main_templates_do_not_require_external_cdn(self):
        for url in ("/chat", "/experiment/exp1b", "/experiment/exp37"):
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
