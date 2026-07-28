"""
主入口 —— 启动AI物理实验助教
================================
运行方式: python main.py

启动后打开浏览器访问 http://localhost:7860 即可使用。
"""

import importlib
import pkgutil
import os
import sys

# 确保当前目录在模块搜索路径中
sys.path.insert(0, os.path.dirname(__file__))

# ──────────────────────────────────────────────
# 自动注册所有插件
# ──────────────────────────────────────────────
def register_all_plugins():
    """扫描 plugins 目录，加载所有实验插件模块"""
    plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.isdir(plugins_dir):
        print("[WARNING] plugins/ 目录不存在，跳过插件加载")
        return
    for importer, modname, ispkg in pkgutil.iter_modules([plugins_dir]):
        if modname == "__init__":
            continue
        importlib.import_module(f"plugins.{modname}")
        print(f"  [加载] plugins/{modname}.py")
    print(f"  共发现 {len(PluginRegistry.list_all())} 个实验插件：")


# ──────────────────────────────────────────────
# 交互模式（控制台演示 / Gradio Web）
# ──────────────────────────────────────────────
def start_console():
    """控制台交互模式（调试用）"""
    from assistant import Assistant
    from experiment_state import ExperimentState

    register_all_plugins()
    print()

    assistant = Assistant()
    state = ExperimentState()

    print("=== 物理实验AI助教（控制台模式）===")
    print("输入 'exit' 退出，输入 'tools' 查看可用工具\n")

    while True:
        try:
            user_input = input("[你] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "tools":
            assistant.print_tools()
            continue

        response = assistant.chat(user_input, state)
        print(f"[AI助教] {response}")


def start_web():
    """启动Gradio Web界面（生产模式）"""
    try:
        import gradio as gr
        from assistant import Assistant
        from experiment_state import ExperimentState

        register_all_plugins()
        print()

        assistant = Assistant()
        state = ExperimentState()

        def respond(message, history):
            if not message.strip():
                return ""
            return assistant.chat(message, state)

        demo = gr.ChatInterface(
            respond,
            title="🧪 物理实验AI助教",
            description="支持语音输入或文字输入，自动完成数据处理与报告生成。"
                        "输入 '做xx实验' 开始一个实验。",
            theme="soft",
        )
        demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
    except ImportError:
        print("Gradio 未安装，启动控制台模式。")
        print("安装命令: pip install gradio")
        print()
        start_console()


if __name__ == "__main__":
    from plugins import PluginRegistry

    # 默认启动 Web 界面
    # 可以通过命令行参数切换：python main.py --console
    if len(sys.argv) > 1 and sys.argv[1] == "--console":
        start_console()
    else:
        start_web()