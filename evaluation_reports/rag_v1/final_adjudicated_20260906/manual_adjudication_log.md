# RAG v1 最终人工复核日志

日期：2026-09-06（UTC）

## 封账约束

仅读取冻结预测、自动评分、三组离线分析和人工结论；没有重跑题目、调用模型或改动冻结系统。原始 automatic 报告保持原样，人工结果写入独立目录。

## R066 / LLM Only 唯一裁定

最终 Human Answer Quality Score：**43.75**。

冻结题目共有四个 required term groups，人工按语义而非字符串偶遇逐组映射：

1. `短接/放电`：PASS。回答明确要求先短接或用放电电阻充分放电。
2. `12V/24V/安全电压`：FAIL。主规则是“36V 以下”，只顺带列举 12V，遗漏 24V，不能算正确表达课程指定安全电压。
3. `不需要/报告`：FAIL。回答称“需要提交完整实验报告”，与冻结答案方向相反。
4. `下课之前/数据处理`：FAIL。仅把“数据处理”列为错误的完整报告内容，没有表达下课前提交数据处理。

因此人工 term coverage = 1/4 = 0.25。严格套用既有共同分公式：Factual 30×0.25=7.5，Completeness 15×0.25=3.75，Boundary=10，Clarity=5；合计 26.25/60，归一化为 **43.75/100**。没有新增 forbidden 或评分规则。

## 复核映射与结论

| 项 | 系统 | 映射字段 | 人工结论 |
|---|---|---|---|
| R061 | Hybrid | forbidden_suspicions / term coverage | 带系数 2 的正确公式，不构成 forbidden；维持 100。 |
| R061 | BM25 | forbidden_hits | 无 2 公式硬命中 forbidden；维持 33.33。 |
| R061 | LLM Only | term coverage | x1/x2 与 S1/S2 物理等价；0.75→1.0，81.25→100。 |
| B007 | LLM Only | refusal_detected / boundary | 语义明确拒答；Boundary FAIL→PASS，83.33→100。 |
| B007 | Hybrid + BM25 | boundary | 均维持 PASS/100。 |
| R058 | Hybrid | term coverage | 按人工决定不下调，维持 81.25。 |
| R062 | Hybrid + BM25 | term coverage | 缺 I0/I1 与理论值比较，维持 0.5/62.5。 |
| R066 | Hybrid + BM25 | term coverage | 按人工决定不额外下调，维持 0.75/81.25。 |
| R066 | LLM Only | term coverage | 人工语义覆盖 0.25，100→43.75。 |

映射完成：9/9 复核项、12/12 系统×题号单元，无未映射项。

## Automatic 与 Human 不一致

- R061 / LLM Only：Answer 81.25→100；E2E 48.75→60。x1/x2 与 S1/S2 表示同一组目标距离，带系数 2 的公式和往返解释完整。
- R066 / LLM Only：Answer 100→43.75；E2E 60→26.25。四个冻结要点仅“短接放电”正确；36V 主规则不等于 12V/24V，完整报告结论反向，且未说明下课前提交数据处理。
- B007 / LLM Only：Answer 83.33→100；E2E 50→60。明确拒绝把示例数据当作实测数据，并要求上传图像或提供测量值；自动 refusal 词表漏检。

## 争议状态

未解决人工争议项：**无（0）**。
