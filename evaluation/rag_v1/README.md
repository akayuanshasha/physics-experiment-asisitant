# RAG 71 题评测（v1.2）

题库共 71 题：已在先前开发中查看或使用过的 56 题全部归入 `dev`；新建的 15 题归入 `test`，覆盖先前缺失的实验、第一/第二优先级冲突、示例数据禁用与显式启用。

资料规则：

- 第一优先级证据达到相关性门槛时，第二优先级不得进入模型上下文。
- 只有第一优先级不足时，才允许第二优先级降级补充。
- 示例 CSV 只在问题明确要求示例、格式或计算演示时启用，不得冒充用户实测数据。

## 执行顺序

```bash
python -m rag_eval validate
python -m rag_eval audit --split dev --output evaluation_reports/rag_v1/dev_corpus_audit.json
python -m rag_eval run --split dev --mode blind --retrieval-only --lexical-only
python -m rag_eval run --split dev --mode blind --retrieval-only
python -m rag_eval run --split dev --mode blind
```

只有 dev 调整结束、文件哈希写入 `manifest.json` 后，才能对新 test 执行唯一一次验收：

```bash
python -m rag_eval run --split test --mode blind
```

`blind` 只发送学生问题；`page-context` 模拟学生已进入实验页面。自动分只用于定位检索、引用、拒答、资料等级和示例误用问题；物理事实与 P0/P1 结论仍需按 `manual_review_template.csv` 人工复核。

每次完整运行会输出 `run_metadata.json`、`corpus_audit.json`、`raw.jsonl`、`predictions.jsonl`、`auto_report.json`、`failure_cases.md` 和 `regression_gate.json`。
