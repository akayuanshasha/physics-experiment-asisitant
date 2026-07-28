"""
AI助教核心引擎 —— 对话+工具调度主循环
======================================
AI助教就是"老师" —— 它理解学生说的话，判断要做什么，
然后调用 tool_executor.py 里的工具完成实际计算。

流程：
1. 用户说一句话 → AI 判断意图
2. AI 决定调用哪个工具 → 工具返回结果
3. AI 把结果组织成自然语言回答用户
"""

import json
import os
from plugins import PluginRegistry
from experiment_state import ExperimentState
from tool_executor import (
    compute_statistics, fit_linear, create_chart, generate_report,
    compute_young_modulus, compute_hall_effect
)

# ──────────────────────────────────────────────
# 工具注册（把函数和它们的描述注册给 AI）
# ──────────────────────────────────────────────
# 这里我们模拟 GLM API 的 tools 参数格式。
# AI 看到这些描述就知道"有哪些工具可用，各自做什么用"。

TOOL_DESCRIPTIONS = [
    {
        "type": "function",
        "function": {
            "name": "compute_statistics",
            "description": "计算一组数据的平均值、标准差和A类不确定度",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "数据列表"
                    },
                    "label": {
                        "type": "string",
                        "description": "数据名称（如「钢丝直径」）"
                    }
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fit_linear",
            "description": "对两组数据进行线性拟合 y = a*x + b，返回斜率和截距",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {"type": "array", "items": {"type": "number"}},
                    "y_data": {"type": "array", "items": {"type": "number"}},
                    "x_label": {"type": "string"},
                    "y_label": {"type": "string"}
                },
                "required": ["x_data", "y_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "生成图表（散点+拟合线），保存为PNG文件，返回文件路径",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {"type": "array", "items": {"type": "number"}},
                    "y_data": {"type": "array", "items": {"type": "number"}},
                    "x_label": {"type": "string"},
                    "y_label": {"type": "string"},
                    "title": {"type": "string"},
                    "fit_type": {"type": "string", "enum": ["linear", None]},
                    "save_name": {"type": "string"}
                },
                "required": ["x_data", "y_data", "title", "save_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "生成实验报告HTML文件，包含数据、结果、图表和分析",
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_name": {"type": "string"},
                    "data_summary": {"type": "string"},
                    "results_summary": {"type": "string"},
                    "analysis_text": {"type": "string"},
                    "chart_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选的图表路径列表"
                    },
                    "output_name": {"type": "string"}
                },
                "required": ["experiment_name", "data_summary", "results_summary", "analysis_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_young_modulus",
            "description": "计算杨氏模量（拉伸法）E = F*L/(A*ΔL)，返回E值",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "拉力值列表 (N)"
                    },
                    "diameter": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "钢丝直径列表 (mm)"
                    },
                    "length": {
                        "type": "number",
                        "description": "钢丝原长 (mm)"
                    },
                    "elongation": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "伸长量列表 (mm)"
                    }
                },
                "required": ["force", "diameter", "length", "elongation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_hall_effect",
            "description": "计算霍尔效应，返回霍尔灵敏度K_H或K_H*B",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_currents": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "工作电流列表 (mA)"
                    },
                    "hall_voltages": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "霍尔电压列表 (mV)"
                    },
                    "excitation_currents": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "励磁电流列表 (A)，可选，用于改变磁场"
                    }
                },
                "required": ["work_currents", "hall_voltages"]
            }
        }
    }
]

# ──────────────────────────────────────────────
# 工具函数映射（名字 → 对应的Python函数）
# ──────────────────────────────────────────────
TOOL_MAP = {
    "compute_statistics": compute_statistics,
    "fit_linear": fit_linear,
    "create_chart": create_chart,
    "generate_report": generate_report,
    "compute_young_modulus": compute_young_modulus,
    "compute_hall_effect": compute_hall_effect,
}


class Assistant:
    """AI助教 —— 对话+工具调度主循环"""

    def __init__(self):
        # 首次运行时打印可用的实验列表
        experiments = PluginRegistry.list_all()
        if experiments:
            print(f"[AI助教] 已加载 {len(experiments)} 个实验插件：{', '.join(experiments)}")
        else:
            print("[AI助教] 注意：未注册任何实验插件，请先加载插件模块")

    def build_system_prompt(self, state):
        """构建系统提示词 —— 告诉AI它的身份和在做什么"""
        plugin_info = PluginRegistry.list_all()
        plugin_str = "\n".join([f"  · {name}: {PluginRegistry.get(name).description}" for name in plugin_info])

        return f"""
你是一个物理实验AI助教，擅长处理大学物理实验的数据处理和报告生成。
你的工作是与学生对话，帮助他们完成实验的数据处理和分析。

当前可以支持的实验类型：
{plugin_str if plugin_str else "  (暂无已注册的实验插件，请先注册)"}

你拥有以下工具可以使用（通过 function calling 调用）：
{json.dumps(TOOL_DESCRIPTIONS, ensure_ascii=False, indent=2)}

请遵循以下规则：
1. 当学生说"帮我做XX实验"时，更新状态为"recording"并引导学生依次提供数据
2. 当学生提供数据时，记录到状态中，检查是否所有必需数据已收集齐
3. 当所有数据收集完成后，调用合适的工具进行计算
4. 用自然语言把计算结果反馈给学生，展示中间步骤
5. 如果学生要求生成图表或报告，调用对应的工具
6. 保持对话友好、耐心，适合本科生的理解水平

{state.to_system_prompt() if state else ""}
"""

    def execute_tool(self, tool_name, arguments):
        """执行工具调用 —— 从TOOL_MAP中找到函数并调用"""
        if tool_name not in TOOL_MAP:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
        try:
            func = TOOL_MAP[tool_name]
            result = func(**arguments)
            return result
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def handle_tool_calls(self, tool_calls, state):
        """处理AI返回的工具调用请求"""
        results = []
        for call in tool_calls:
            name = call.get("function", {}).get("name", "")
            args_raw = call.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            print(f"  [工具调用] {name}({json.dumps(args, ensure_ascii=False)})")
            result = self.execute_tool(name, args)
            results.append({
                "tool_call_id": call.get("id", ""),
                "output": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            })
            # 如果工具返回了计算结果，保存到实验状态中
            if name == "compute_young_modulus" or \
               name == "compute_hall_effect" or \
               name == "fit_linear" or \
               name == "compute_statistics":
                state.results[name] = result
        return results

    def chat(self, user_input, state):
        """处理用户输入 —— 模拟AI对话流程

        实际项目中这里会调用 GLM API。这里我们用伪代码展示接口。
        当前实现是一个模拟版本，演示数据流走向。
        """
        print(f"\n[用户] {user_input}")
        print(f"[AI助教] ", end="")

        # ===== 模拟AI的意图理解和工具调用 =====
        # 实际项目里，这里会是 GLM API 的调用

        # 判断用户意图（模拟）：
        # 如果用户说"做XX实验"，设置实验名称
        # 这里只是一个模拟框架，实际由GLM API完成

        response = f"收到！我是物理实验AI助教，很高兴为您服务。请问您需要处理什么实验数据？\n" \
                   f"目前系统支持以下实验：{PluginRegistry.list_all()}"
        return response

    def print_tools(self):
        """打印可用工具列表"""
        print("\n=== 可用工具 ===")
        for t in TOOL_DESCRIPTIONS:
            name = t["function"]["name"]
            desc = t["function"]["description"]
            print(f"  · {name}: {desc}")