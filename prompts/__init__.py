"""Prompt 集中管理包。

按用途拆分，避免 main.py / abnormal_detector.py / report_generator.py
各自保存一份互相独立的提示词：

- ``abnormal_analysis`` —— 数据异常检测（/api/abnormal-detect）
- ``report_generation`` —— LaTeX 实验报告生成（/api/generate-report）
"""

from .abnormal_analysis import ABNORMAL_SYSTEM_PROMPT
from .report_generation import LATEX_REPORT_SYSTEM_PROMPT

__all__ = [
    "ABNORMAL_SYSTEM_PROMPT",
    "LATEX_REPORT_SYSTEM_PROMPT",
]
