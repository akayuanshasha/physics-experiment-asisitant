"""
数据异常检测模块
================
对学生提交的物理实验数据进行全面异常分析。

四个检测维度：
1. 统计异常（3σ准则识别离群值）
2. 物理合理性（结合实验指导判断）
3. 录入错误（小数点、单位、抄写错误等）
4. 趋势异常（数据变化趋势是否符合物理规律）
"""

import json
import os
import numpy as np


# ──────────────────────────────────────────────
# System Prompt（异常检测专用）
# ──────────────────────────────────────────────
ABNORMAL_SYSTEM_PROMPT = (
    "你是一位大学物理实验数据分析专家，同时也是一位严格的数据质量审核者。"
    "你的任务是对学生提交的物理实验数据进行全面、严谨的异常检测分析。\n\n"

    "用户会在消息中提供：\n"
    "1. 该实验的《实验指导》全文（从PDF提取）\n"
    "2. 学生提交的实验数据\n\n"

    "请仔细阅读实验指导，了解：实验目的、原理、公式、仪器（含量程和允差）、"
    "测量步骤、数据处理方法，以及各项物理量的预期范围。"
    "然后结合这些信息对学生数据进行以下四个维度的异常检测：\n\n"

    "1. **统计异常**："
    "使用3σ准则识别离群值；"
    "计算各列均值、标准差，判断是否存在偏离均值超过3倍标准差的数据点；"
    "评估数据离散程度是否合理。\n"

    "2. **物理合理性**："
    "结合实验指导中的公式和预期范围，"
    "判断数据是否符合物理规律；"
    "估算最终物理量是否符合理论预期。\n"

    "3. **录入错误**："
    "检查是否存在："
    "小数点错误、单位混淆、数字抄写错误、"
    "异常重复数据、缺失值等问题。\n"

    "4. **趋势异常**："
    "如果实验数据存在变量关系，"
    "检查数据是否符合物理变化趋势，"
    "是否存在明显异常突变。\n\n"

    "输出格式要求：\n"

    "- 使用中文撰写\n"
    "- 风格严谨、学术化\n"

    "- 必须按照以下四个标题输出：\n"
    "## 统计异常\n"
    "## 物理合理性\n"
    "## 录入错误\n"
    "## 趋势异常\n\n"

    "- 每个部分必须包含："
    "判断结论（正常/可疑/异常）"
    "以及详细分析过程\n"

    "- 如果没有异常，综合结论必须明确写："
    "未发现明显异常\n"

    "- 如果发现异常，必须指出："
    "具体数据行号和异常数值\n"

    "- 涉及具体数值时保留合理精度"
)


class AbnormalDetector:
    """数据异常检测器

    用法:
        detector = AbnormalDetector(llm_client, model_name)
        report = detector.detect(experiment_name, pdf_text, columns, data_rows)
    """

    def __init__(self, llm_client, model_name="glm-5.2-107"):
        """
        参数:
            llm_client: OpenAI 兼容的 LLM 客户端
            model_name: 模型名称
        """
        self.client = llm_client
        self.model = model_name

    def detect(self, experiment_name, pdf_text, columns, data_rows, analysis_hints=None, stats=None):
        """执行异常检测

        参数:
            experiment_name: str, 实验名称
            pdf_text: str, 实验指导书文本（可为空字符串）
            columns: list[str], 表格列名
            data_rows: list[list[str]], 表格数据行
            analysis_hints: str|None, 实验特定的分析提示（覆盖默认四维度）
            stats: dict|None, 统计预分析结果（提供时注入 prompt 供模型核对）

        返回:
            str, 异常检测报告文本
        """
        # 1. 将数据转换为 Markdown 表格
        table_md = self._build_markdown_table(columns, data_rows)

        # 2. 构造 System Prompt（如有自定义提示则追加）
        system_prompt = ABNORMAL_SYSTEM_PROMPT
        if analysis_hints and analysis_hints.strip():
            system_prompt += "\n\n" + analysis_hints.strip()

        # 3. 构造用户 Prompt
        user_prompt = self._build_user_prompt(experiment_name, pdf_text, columns, data_rows, table_md, stats)

        # 4. 调用 LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4096,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            report_text = response.choices[0].message.content
            if not report_text:
                return "❌ 模型未生成有效内容（可能 token 不足），请重试。"
            return report_text
        except Exception as e:
            return f"❌ 异常检测调用失败: {str(e)}"

    def detect_with_stats(self, experiment_name, pdf_text, columns, data_rows, analysis_hints=None):
        """执行异常检测，同时返回统计预分析结果

        返回:
            dict: {
                "report": str,        # AI 检测报告
                "stats_preview": dict  # 统计预分析（均值、标准差、离群值等）
            }
        """
        # 先做统计预分析
        stats = self._statistical_analysis(columns, data_rows)

        # 再调用 AI 检测（统计预分析结果注入 prompt，供模型直接核对引用）
        report = self.detect(experiment_name, pdf_text, columns, data_rows,
                             analysis_hints=analysis_hints, stats=stats)

        return {
            "report": report,
            "stats_preview": stats
        }

    @staticmethod
    def _build_markdown_table(columns, data_rows):
        """将列名和数据行转换为 Markdown 表格"""
        if not columns or not data_rows:
            return "（无数据）"

        # 表头
        header = "| " + " | ".join(str(c) for c in columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"

        # 数据行
        rows = []
        for row in data_rows:
            cells = []
            for val in row:
                cells.append(str(val) if val != '' and val is not None else "-")
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join([header, separator] + rows)

    @staticmethod
    def _format_stats_md(stats):
        """将统计预分析结果渲染为 Markdown 表格"""
        lines = [
            "| 列名 | 有效数据个数 | 均值 | 标准差σ | 最小值 | 最大值 | 3σ离群点(行号:数值) |",
            "|---|---|---|---|---|---|---|"
        ]
        for col, s in stats.items():
            outliers = ", ".join(
                f"第{o['row']}行: {o['value']}" for o in s["outliers_3sigma"]
            ) or "无"
            lines.append(
                f"| {col} | {s['n']} | {s['mean']} | {s['std']} | "
                f"{s['min']} | {s['max']} | {outliers} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _build_user_prompt(experiment_name, pdf_text, columns, data_rows, table_md, stats=None):
        """构造用户 Prompt"""
        pdf_section = ""
        if pdf_text and pdf_text.strip():
            pdf_section = (
                f"## 实验指导（原文）\n"
                f"以下为该实验官方实验指导书全文：\n\n"
                f"{pdf_text}\n\n"
            )
        else:
            pdf_section = (
                "## 实验指导\n"
                "（未提供实验指导书文本，请仅基于数据本身和物理常识进行分析）\n\n"
            )

        stats_section = ""
        if stats:
            stats_section = (
                "## 统计预分析结果（程序预计算）\n"
                "以下统计量由程序预先计算（3σ准则，仅列出有效数据不少于2个的数值列），"
                "在“统计异常”部分可直接引用核对，无需重新推算；"
                "判定时请结合样本量与实验指导中的仪器允差，"
                "不要仅凭是否存在3σ离群点下结论。\n\n"
                f"{AbnormalDetector._format_stats_md(stats)}\n\n"
            )

        return (
            f"## 实验名称\n"
            f"{experiment_name}\n\n"

            f"{pdf_section}"

            f"## 学生提交的实验数据\n"
            f"共 {len(data_rows)} 行，{len(columns)} 列：\n\n"
            f"{table_md}\n\n"

            f"{stats_section}"

            f"请严格按照系统指令中的四个维度和输出格式要求，"
            f"对以上数据进行全面异常检测分析。"
            f"注意结合实验指导中给出的：仪器允差、公式、物理常数、理论范围进行严格判断。"
        )

    @staticmethod
    def _statistical_analysis(columns, data_rows):
        """对每列数值数据做统计预分析

        返回:
            dict: {列名: {mean, std, min, max, outliers_3sigma}}
        """
        if not data_rows or not columns:
            return {}

        stats = {}
        n_cols = len(columns)

        for col_idx in range(n_cols):
            col_name = columns[col_idx]
            # 提取该列的数值
            values = []
            for row in data_rows:
                if col_idx < len(row):
                    try:
                        values.append(float(row[col_idx]))
                    except (ValueError, TypeError):
                        pass

            if len(values) < 2:
                continue

            arr = np.array(values)
            mean = float(np.mean(arr))
            std = float(np.std(arr, ddof=1))

            # 3σ 离群值检测
            outliers = []
            if std > 0:
                for i, v in enumerate(values):
                    if abs(v - mean) > 3 * std:
                        outliers.append({"row": i + 1, "value": v})

            stats[col_name] = {
                "mean": round(mean, 6),
                "std": round(std, 6),
                "min": round(float(np.min(arr)), 6),
                "max": round(float(np.max(arr)), 6),
                "n": len(values),
                "outliers_3sigma": outliers
            }

        return stats
