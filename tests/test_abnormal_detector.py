"""abnormal_detector 单元测试（不依赖真实 LLM，用 mock client）"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abnormal_detector import AbnormalDetector, _parse_number


# ── 数值解析 ──────────────────────────────────────────────
def test_parse_number():
    cases = [
        ("15.0", 15.0, False),
        ("15.0 cm", 15.0, True),
        ("15.0cm", 15.0, True),
        ("15.0±0.1", 15.0, False),
        ("15.0±0.1 cm", 15.0, True),
        ("1.5e-3", 1.5e-3, False),
        ("1.5×10³", 1500.0, False),
        ("1.5×10^-3", 1.5e-3, False),
        ("1,500", 1500.0, False),
        ("12,345.67", 12345.67, False),
        ("－１２．５", -12.5, False),  # 全角数字与符号可解析（\d 匹配 Unicode 数字）
        ("-3.2", -3.2, False),
        ("15.0 / 16.0", None, False),
        ("abc", None, False),
        ("", None, False),
        ("50%", 50.0, True),
        ("1,5", None, False),  # 逗号后不足3位，不做千分位
        ("t1", None, False),   # 数字不在开头（身份列文本），不应解析
        ("(15.0)", 15.0, False),  # 括号包裹
    ]
    for raw, expect_val, expect_unit in cases:
        p = _parse_number(raw)
        if expect_val is None:
            assert p is None, f"{raw!r} 应解析失败，实际 {p}"
        else:
            assert p is not None, f"{raw!r} 应能解析"
            assert abs(p["value"] - expect_val) < 1e-9 * max(1, abs(expect_val)), f"{raw!r} 值错误: {p}"
            assert p["has_unit"] == expect_unit, f"{raw!r} has_unit 应为 {expect_unit}: {p}"
    print("✓ test_parse_number 通过")


# ── 统计预分析 ────────────────────────────────────────────
def test_statistical_analysis():
    columns = ["次数", "直径d", "电压U"]
    data_rows = [
        ["1", "15.0", "1.5"],
        ["2", "15.2", "1.6"],
        ["3", "15.1 cm", "1.5"],   # 单位混入 → unit_mixed
        ["4", "15.3", "abc"],      # 无法解析 → parse_fail
        ["5", "15.1", "1.5"],
        ["6", "99.0", "1.7"],      # 大离群点
        ["7", "15.0", ""],         # 缺失
        ["8", "15.2", "1.5"],
    ]
    stats = AbnormalDetector._statistical_analysis(columns, data_rows)
    assert "直径d" in stats and "电压U" in stats, "数值列应出现在统计中"
    d = stats["直径d"]
    assert d["n"] == 8
    assert len(d["unit_mixed"]) == 1 and d["unit_mixed"][0]["row"] == 3
    u = stats["电压U"]
    assert u["n"] == 6
    assert len(u["parse_fails"]) == 1 and u["parse_fails"][0]["row"] == 4
    assert u["missing"] == [7]
    assert any(o["row"] == 6 for o in d["outliers_mad"]), "99.0 应被 MAD 判为离群点"
    # 序号列有数值但统计意义不大——允许存在，只验证不崩溃
    assert "次数" in stats
    # 统计表渲染
    md = AbnormalDetector._format_stats_md(stats)
    assert "样本量过小" in md
    print("✓ test_statistical_analysis 通过")


# ── 趋势预分析 ──────────────────────────────────────────
def test_trend_analysis():
    columns = ["U", "I"]
    data_rows = [
        ["1.0", "0.10"],
        ["2.0", "0.21"],
        ["3.0", "0.29"],
        ["4.0", "0.41"],
        ["5.0", "0.52"],
        ["6.0", "1.50"],   # 趋势断点
    ]
    trends = AbnormalDetector._trend_analysis(columns, data_rows)
    assert "I" in trends
    t = trends["I"]
    assert t["单调性"] == "单调递增"
    assert "与参考列线性拟合" in t and "最大残差点：第6行" in t["与参考列线性拟合"]
    md = AbnormalDetector._format_trend_md(trends)
    assert "R²" in md
    print("✓ test_trend_analysis 通过")


# ── 结构化输出解析 / 渲染 ────────────────────────────────
def test_structured_parsing():
    raw_llm = '''
```json
{
  "综合结论": "发现 2 处异常",
  "维度判定": {
    "统计异常": {"判定": "异常", "分析": "第6行99.0超出3σ"},
    "物理合理性": {"判定": "正常", "分析": "符合欧姆定律"},
    "录入错误": {"判定": "可疑", "分析": "有单位混入"},
    "趋势异常": {"判定": "正常", "分析": "线性良好"}
  },
  "异常项": [
    {"行号": 6, "列名": "直径d", "数值": "99.0", "维度": "统计异常", "严重度": "高", "问题": "离群", "建议": "复测"},
    {"行号": 3, "列名": "直径d", "数值": "15.1 cm", "维度": "录入错误", "严重度": "低", "问题": "带单位", "建议": "去掉单位"}
  ]
}
```
'''
    st = AbnormalDetector._extract_json(raw_llm)
    assert st is not None
    assert st["conclusion"] == "发现 2 处异常"
    assert st["verdicts"]["统计异常"]["判定"] == "异常"
    # 「录入错误」维度已废弃：维度判定只保留三个维度，异常项中该维度被过滤
    assert set(st["verdicts"]) == {"统计异常", "物理合理性", "趋势异常"}
    assert len(st["anomalies"]) == 1
    assert st["anomalies"][0]["row"] == 6 and st["anomalies"][0]["severity"] == "高"
    md = AbnormalDetector._render_report_md(st)
    assert "## 综合结论" in md and "异常明细（共 1 处）" in md
    assert "录入错误" not in md
    # 缺字段容错
    st2 = AbnormalDetector._extract_json('{"维度判定": {"统计异常": {"判定": "正常", "分析": ""}}}')
    assert st2 is not None and st2["anomalies"] == []
    assert st2["verdicts"]["趋势异常"]["判定"] == "正常"
    # 非法输出
    assert AbnormalDetector._extract_json("这是一段没有JSON的回答") is None
    assert AbnormalDetector._extract_json("") is None
    print("✓ test_structured_parsing 通过")


# ── 端到端（mock LLM） ──────────────────────────────────
class FakeChoice:
    def __init__(self, content, finish_reason="stop"):
        self.message = type("M", (), {"content": content})()
        self.finish_reason = finish_reason


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("R", (), {"choices": [FakeChoice(self._content)]})()


class FakeClient:
    def __init__(self, content):
        self.chat = type("C", (), {"completions": FakeCompletions(content)})()


def test_detect_end_to_end():
    llm_json = json.dumps({
        "综合结论": "未发现明显异常",
        "维度判定": {d: {"判定": "正常", "分析": "无异常"} for d in ("统计异常", "物理合理性", "趋势异常")},
        "异常项": [],
    }, ensure_ascii=False)
    client = FakeClient(llm_json)
    detector = AbnormalDetector(client, "test-model")
    result = detector.detect_with_stats(
        "测试实验", "指导书文本", ["U", "I"],
        [["1.0", "0.10"], ["2.0", "0.21"], ["3.0", "0.29"], ["4.0", "0.41"]])
    assert "未发现明显异常" in result["report"]
    assert result["structured"]["anomalies"] == []
    assert "U" in result["stats_preview"]
    # 校验注入 prompt 的内容
    user_prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "统计预分析" in user_prompt and "趋势预分析" in user_prompt
    assert "录入格式线索" not in user_prompt and "重复数据线索" not in user_prompt
    assert "<data>" in user_prompt
    # 校验 response_format 传参
    assert client.chat.completions.calls[0].get("response_format") == {"type": "json_object"}

    # LLM 输出非 JSON 时兜底
    client2 = FakeClient("模型输出了普通文本")
    r2 = AbnormalDetector(client2, "test-model").detect("t", "", ["a"], [["1"], ["2"]])
    assert r2["structured"] is None and "普通文本" in r2["report"]
    print("✓ test_detect_end_to_end 通过")


# ── LLM 调用健壮性：重试 / 降级 / 截断救援 ──────────────────
def _make_client(completions_obj):
    return type("C", (), {"chat": type("Ch", (), {"completions": completions_obj})()})()


def test_retry_on_transient_error():
    calls = []
    good = json.dumps({"综合结论": "未发现明显异常",
                       "维度判定": {d: {"判定": "正常", "分析": ""} for d in
                                    ("统计异常", "物理合理性", "趋势异常")},
                       "异常项": []}, ensure_ascii=False)

    class TransientThenOK:
        def create(self, **kwargs):
            calls.append(dict(kwargs))
            if len(calls) == 1:
                raise RuntimeError("connection reset by peer")
            return type("R", (), {"choices": [FakeChoice(good)]})()

    r = AbnormalDetector(_make_client(TransientThenOK()), "test-model").detect(
        "t", "", ["a"], [["1"], ["2"]])
    assert len(calls) == 2, "瞬时错误应重试一次"
    assert r["structured"] is not None
    assert calls[0]["timeout"] == 150 and calls[0]["temperature"] == 0.1
    print("✓ test_retry_on_transient_error 通过")


def test_response_format_degrade():
    calls = []

    class Reject400:
        def create(self, **kwargs):
            calls.append(dict(kwargs))
            if "response_format" in kwargs:
                e = RuntimeError("bad request")
                e.status_code = 400
                raise e
            return type("R", (), {"choices": [FakeChoice(
                '{"维度判定": {}, "异常项": []}')]})()

    r = AbnormalDetector(_make_client(Reject400()), "test-model").detect(
        "t", "", ["a"], [["1"], ["2"]])
    assert len(calls) == 2, "response_format 被拒后应降级重试"
    assert calls[0].get("response_format") == {"type": "json_object"}
    assert "response_format" not in calls[1]
    assert r["structured"] is not None and r["structured"]["anomalies"] == []
    print("✓ test_response_format_degrade 通过")


def test_parameter_error_fails_fast():
    calls = []

    class Always400:
        def create(self, **kwargs):
            calls.append(dict(kwargs))
            e = RuntimeError("invalid param")
            e.status_code = 422
            raise e

    r = AbnormalDetector(_make_client(Always400()), "test-model").detect(
        "t", "", ["a"], [["1"], ["2"]])
    # 首个 JSON 请求遇 4xx 会降级重试一次（无法区分是 response_format 还是其他参数问题），
    # 降级后仍 4xx 则直接失败，不再重试
    assert len(calls) == 2 and "response_format" not in calls[1]
    assert r["structured"] is None and "异常检测调用失败" in r["report"]
    print("✓ test_parameter_error_fails_fast 通过")


def test_truncation_rescue():
    calls = []
    good = json.dumps({"综合结论": "未发现明显异常",
                       "维度判定": {d: {"判定": "正常", "分析": ""} for d in
                                    ("统计异常", "物理合理性", "趋势异常")},
                       "异常项": []}, ensure_ascii=False)

    class TruncatedThenOK:
        def create(self, **kwargs):
            calls.append(dict(kwargs))
            if len(calls) == 1:
                return type("R", (), {"choices": [FakeChoice(good[:40], "length")]})()
            return type("R", (), {"choices": [FakeChoice(good, "stop")]})()

    r = AbnormalDetector(_make_client(TruncatedThenOK()), "test-model").detect(
        "t", "", ["a"], [["1"], ["2"]])
    assert len(calls) == 2, "截断后应追加压缩指令重试一次"
    assert "压缩" in calls[1]["messages"][-1]["content"]
    assert "未发现明显异常" in r["report"] and "截断" not in r["report"]
    assert r["structured"] is not None
    print("✓ test_truncation_rescue 通过")


if __name__ == "__main__":
    test_parse_number()
    test_statistical_analysis()
    test_trend_analysis()
    test_structured_parsing()
    test_detect_end_to_end()
    test_retry_on_transient_error()
    test_response_format_degrade()
    test_parameter_error_fails_fast()
    test_truncation_rescue()
    print("\n全部测试通过 ✅")
