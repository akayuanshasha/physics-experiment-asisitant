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
from dotenv import load_dotenv
from openai import OpenAI
from plugins import PluginRegistry
from experiment_state import ExperimentState
from tool_executor import (
    compute_statistics, fit_linear, create_chart, generate_report,
    compute_young_modulus, compute_hall_effect, run_experiment_plugin
)

# 加载项目根目录下的 .env 文件（如果存在），自动注入环境变量
load_dotenv()

# 防止无限工具调用循环的上限
MAX_TOOL_ROUNDS = 5

# ──────────────────────────────────────────────
# 工具注册（把函数和它们的描述注册给 AI）
# ──────────────────────────────────────────────
# 这里我们模拟 GLM API 的 tools 参数格式。
# AI 看到这些描述就知道"有哪些工具可用，各自做什么用"。

TOOL_DESCRIPTIONS = [
    {
        "type": "function",
        "function": {
            "name": "set_experiment",
            "description": "设置当前实验类型并进入数据记录阶段。当学生说'做XX实验'时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "实验名称，必须与已注册插件中的实验名一致"
                    },
                    "required_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要收集的数据项名称列表"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_data",
            "description": "记录学生提供的一组测量数据。每收集到一组数据就调用此工具保存。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "数据项名称（如'钢丝直径(mm)'）"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "测量值列表"
                    }
                },
                "required": ["name", "values"]
            }
        }
    },
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
            "name": "run_experiment_plugin",
            "description": "运行任意已注册的实验插件，自动完成数据处理、图表生成和报告生成。"
                           "当学生提供了实验数据并要求处理时，调用此工具。"
                           "experiment_name 必须与已注册的插件名称完全一致。",
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_name": {
                        "type": "string",
                        "description": "实验名称（必须与已注册插件名一致）"
                    },
                    "data": {
                        "type": "object",
                        "description": "实验数据，键为数据项名称，值为数值列表",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "number"}
                        }
                    }
                },
                "required": ["experiment_name", "data"]
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
def set_experiment(name, required_fields=None):
    """设置当前实验类型（实际状态由 handle_tool_calls 写入 state）"""
    return {"experiment": name, "required_fields": required_fields or []}


def add_data(name, values):
    """记录一组测量数据（实际状态由 handle_tool_calls 写入 state）"""
    return {"recorded": name, "count": len(values), "values": values}


TOOL_MAP = {
    "set_experiment": set_experiment,
    "add_data": add_data,
    "compute_statistics": compute_statistics,
    "fit_linear": fit_linear,
    "create_chart": create_chart,
    "generate_report": generate_report,
    "compute_young_modulus": compute_young_modulus,
    "compute_hall_effect": compute_hall_effect,
    "run_experiment_plugin": run_experiment_plugin,
}


class Assistant:
    """AI助教 —— 对话+工具调度主循环"""

    def __init__(self):
        # ── 初始化 LLM API 客户端（OpenAI 兼容） ──
        api_key = os.environ.get("LLM_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL")
        self.model = os.environ.get("LLM_MODEL", "glm-5.2")

        missing = []
        if not api_key:
            missing.append("LLM_API_KEY")
        if not base_url:
            missing.append("LLM_BASE_URL")

        if missing:
            print(f"[AI助教] ⚠️  警告：未检测到环境变量 {', '.join(missing)}")
            print("  设置方法：")
            print("    set LLM_API_KEY=your_api_key       (你的 API Key)")
            print("    set LLM_BASE_URL=https://xxx/v1    (你的 API 地址)")
            print("    set LLM_MODEL=模型名               (可选，默认 glm-5.2)")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            print(f"[AI助教] LLM API 客户端初始化成功 (model={self.model})")
            print(f"         base_url={base_url}")

        # 打印可用的实验列表
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

工具使用规则（通过 function calling 调用对应工具）：
1. 当学生说"帮我做XX实验"或类似意图时，调用 `set_experiment` 工具设置实验名称并进入记录阶段，
   `required_fields` 应填写该实验需要的所有数据项（参考插件描述）。
2. 学生每提供一组测量数据，调用 `add_data` 工具记录到状态中。
3. 所有必需数据收集完成后，调用对应的计算工具（如 `compute_young_modulus` / `compute_hall_effect`）。
4. 学生要求画图时调用 `create_chart`，要求生成报告时调用 `generate_report`。
5. 用自然语言把计算结果反馈给学生，展示中间步骤和物理意义。
6. 保持对话友好、耐心，适合本科生的理解水平，使用中文回复。

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
            # ── 把工具副作用落到 state 上 ──
            if name == "set_experiment":
                state.set_experiment(
                    args.get("name"),
                    required_fields=args.get("required_fields"),
                )
            elif name == "add_data":
                state.add_data(args.get("name"), args.get("values", []))
            elif name in ("compute_young_modulus", "compute_hall_effect",
                          "fit_linear", "compute_statistics",
                          "run_experiment_plugin"):
                state.results[name] = result
        return results

    def chat(self, user_input, state):
        """处理用户输入 —— 调用 GLM API 完成对话和工具调度

        流程：
        1. 构建 messages（系统提示词 + 历史对话 + 当前输入）
        2. 调用 GLM API
        3. 如果 AI 返回 tool_calls → 执行工具 → 结果送回 GLM → 循环
        4. 如果 AI 返回纯文本 → 保存历史 → 返回
        """
        print(f"\n[用户] {user_input}")

        # ── API Key/URL 未配置时的回退 ──
        if not self.client:
            fallback = (
                "⚠️ LLM API 未配置，请设置以下环境变量：\n"
                "  set LLM_API_KEY=your_api_key        (你的 API Key)\n"
                "  set LLM_BASE_URL=https://xxx/v1     (你的 API 地址)\n"
                "  set LLM_MODEL=模型名                (可选，默认 glm-5.2)"
            )
            state.dialog_history.append({"role": "user", "content": user_input})
            state.dialog_history.append({"role": "assistant", "content": fallback})
            print(f"[AI助教] {fallback}")
            return fallback

        # ── 构建消息列表 ──
        messages = [
            {"role": "system", "content": self.build_system_prompt(state)},
        ]
        # 添加最近对话历史（保留上下文）
        for entry in state.dialog_history[-20:]:
            messages.append({"role": entry["role"], "content": entry["content"]})
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        # ── 工具调用循环（最多 MAX_TOOL_ROUNDS 轮） ──
        for _round in range(MAX_TOOL_ROUNDS):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DESCRIPTIONS,
                    tool_choice="auto",
                )
            except Exception as e:
                print(f"[AI助教] API 调用失败：{e}")
                state.dialog_history.append({"role": "user", "content": user_input})
                error_msg = f"❌ 调用 GLM API 时出错：{e}\n请检查网络连接和 API Key 是否正确。"
                state.dialog_history.append({"role": "assistant", "content": error_msg})
                return error_msg

            msg = response.choices[0].message

            # ── 无 tool_calls：直接返回文本回复 ──
            if not msg.tool_calls:
                text = msg.content or ""
                state.dialog_history.append({"role": "user", "content": user_input})
                state.dialog_history.append({"role": "assistant", "content": text})
                print(f"[AI助教] {text[:200]}{'...' if len(text) > 200 else ''}")
                return text

            # ── 有 tool_calls：执行工具 ──
            print(f"  [工具调用] {[tc.function.name for tc in msg.tool_calls]}")

            # 把 AI 的 tool_calls 消息加入对话
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            messages.append(assistant_msg)

            # 执行工具
            tool_results = self.handle_tool_calls(
                [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
                state,
            )

            # 把工具结果加入对话
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["output"],
                })

        # ── 超过最大轮次，请求用户简化 ──
        fallback = "抱歉，处理步骤过多，请简化您的问题后重试。"
        state.dialog_history.append({"role": "user", "content": user_input})
        state.dialog_history.append({"role": "assistant", "content": fallback})
        print(f"[AI助教] {fallback}")
        return fallback

    def print_tools(self):
        """打印可用工具列表"""
        print("\n=== 可用工具 ===")
        for t in TOOL_DESCRIPTIONS:
            name = t["function"]["name"]
            desc = t["function"]["description"]
            print(f"  · {name}: {desc}")