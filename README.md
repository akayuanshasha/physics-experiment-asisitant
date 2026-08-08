# 🧪 物理实验AI助教系统

> 一个以**大语言模型（OpenAI 兼容 API）**为"大脑"，自动完成物理实验数据处理、图表绘制和报告生成的智能体系统。

## 快速启动

```bash
# 1. 依赖安装
pip install -r requirements.txt

# 2. 设置LLM API 环境变量
#    (支持任何 OpenAI 兼容的 API，如学校提供的 LLM 服务)
export LLM_API_KEY=your_api_key_here
export LLM_BASE_URL=https://your-api-host/v1
export LLM_MODEL=your_model_name      # 可选，默认 glm-5.2

# 3. 运行调试脚本（不依赖API，建议先跑这个）
venv/Scripts/python.exe debug_tools.py

# 4. 启动控制台模式（调试用）
venv/Scripts/python.exe main.py --console

# 5. 启动Web界面
venv/Scripts/python.exe main.py
# 浏览器访问 http://localhost:7860
```

---

## 📁 项目文件总览

```
D:\vscode_code\code\
│
├── main.py                  # 🚀 启动入口 —— 负责加载插件、启动Web/控制台
├── assistant.py             # 🧠 AI助教核心 —— 对话管理、工具调度、提示词构建
├── tool_executor.py         # 🔧 工具函数库 —— 统计/拟合/画图/报告/杨氏模量/霍尔计算
├── experiment_state.py      # 📋 实验状态管理 —— 记录当前实验进度和数据收集情况
├── debug_tools.py           # 🐛 调试脚本 —— 分层验证所有功能（不依赖API Key）
├── requirements.txt         # 📦 依赖清单
├── DEMO_DATA.md             # 📊 演示数据
│
├── plugins/                 # 🧩 实验插件目录
│   ├── __init__.py          #   插件基类 + 注册中心（ExperimentPlugin + PluginRegistry）
│   ├── young_modulus.py     #   杨氏模量（拉伸法）实验插件
│   └── hall_effect.py       #   霍尔效应实验插件
│
├── templates/               # 📄 报告模板目录（当前为空，需C同学添加）
├── output/                  # 📸 生成文件目录（图表PNG、报告HTML）
├── outputs/                 # 📂 备用输出目录
│   ├── charts/
│   └── reports/
│
└── venv/                    # 🔒 Python虚拟环境（勿手动修改）
```

---

## 👥 成员详细分工与操作指南

### A同学 —— AI对话引擎（assistant.py）

**负责模块：** 对接 LLM API（OpenAI 兼容）、Function Calling、对话管理、Prompt工程

| 文件 | 职责 | 核心工作 |
|------|------|---------|
| `assistant.py` | AI助教核心引擎 | 构建系统提示词、解析用户意图、调度工具、组织回复 |

**需要添加/修改的内容：**

1. **接入 LLM API（核心工作）**
   - 在 `assistant.py` 的 `chat()` 方法中，替换当前的模拟代码，接入 `openai` SDK
   - 参考代码：`from openai import OpenAI`
   - 实现流程：用户输入 → 调用 LLM API → 解析返回的 tool_calls → 执行工具 → 返回结果给用户

2. **完善工具描述（Tool Definitions）**
   - 当前的 `TOOL_DESCRIPTIONS` 列表是模拟GLM API的tool格式
   - 如果GLM API的tool格式有变化，需要同步更新
   - 添加新工具的描述（比如未来B同学新增的实验）

3. **优化系统提示词（Prompt Engineering）**
   - 在 `Assistant.build_system_prompt()` 中优化提示词
   - 让AI更懂实验流程、更自然地和学生对话
   - 加入中文指令，让AI用中文思考

**操作流程：**
```python
# 在 assistant.py 的 chat() 方法中实现以下逻辑：
# 1. 初始化 OpenAI 兼容客户端
client = OpenAI(api_key="your-api-key", base_url="https://your-host/v1")
# 2. 调用 LLM API
response = client.chat.completions.create(
    model="your-model-name",
    messages=[
        {"role": "system", "content": self.build_system_prompt(state)},
        {"role": "user", "content": user_input}
    ],
    tools=TOOL_DESCRIPTIONS,   # 注册好的工具列表
    tool_choice="auto"
)
# 3. 处理 tool_calls
if response.choices[0].message.tool_calls:
    results = self.handle_tool_calls(response.choices[0].message.tool_calls, state)
# 4. 将工具结果送回 LLM，生成最终回复
```

**测试方式：**
```bash
venv/Scripts/python.exe main.py --console
# 然后在控制台输入 "做杨氏模量实验" 测试对话流程
```

---

### B同学 —— 实验插件开发（plugins/ 目录）

**负责模块：** 物理公式实现、NumPy/SciPy数值计算、不确定度分析

| 文件 | 职责 | 核心工作 |
|------|------|---------|
| `plugins/__init__.py` | 插件基类+注册中心 | **框架文件，B同学不需要修改**（但需理解接口） |
| `plugins/young_modulus.py` | 杨氏模量实验 | 已实现，可作为模板参考 |
| `plugins/hall_effect.py` | 霍尔效应实验 | 已实现，可作为模板参考 |
| `plugins/牛顿环.py`（待创建） | 新的实验 | 示例：需要新增的实验插件 |

**需要创建的内容（B同学的核心工作）：**

每个新实验插件需要继承 `ExperimentPlugin` 基类，实现以下三个方法：

```python
from . import ExperimentPlugin, PluginRegistry

@PluginRegistry.register  # 这行自动注册插件，不需要修改其他文件
class 新实验(ExperimentPlugin):
    name = "实验名称"          # 唯一标识
    category = "分类"          # 如 "力学"、"电磁学"、"光学"
    description = "简短描述"
    required_fields = ["数据项1", "数据项2"]  # 用户需要提供哪些数据

    # 方法1：数据处理与计算 —— 核心物理公式
    def calculate(self, data, constants=None):
        """输入原始数据 → 返回计算结果"""
        # data 格式: {"数据项1": [值1, 值2, ...], "数据项2": [...]}
        # 使用 numpy/scipy 做数值计算
        # 返回 {"steps": {...中间步骤...}, "final": {...最终结果...}}
        pass

    # 方法2：生成图表
    def generate_chart(self, data, results, save_dir):
        """生成PNG图表 → 返回文件路径列表"""
        # 使用 matplotlib 绘图
        # save_dir 是 output/ 目录
        pass

    # 方法3：生成报告内容
    def get_report_content(self, data, results):
        """返回报告各章节内容 → 用于生成HTML报告"""
        # 返回 {"purpose": "", "principle": "", "steps": "", "final": "", "analysis": ""}
        pass
```

**如何新增一个实验插件（以"牛顿环"为例）：**

1. 在 `plugins/` 目录下创建新文件 `newtons_rings.py`
2. 参考 `young_modulus.py` 的模板编写代码
3. 使用 `@PluginRegistry.register` 装饰器
4. 系统启动时会**自动加载**，无需修改任何其他文件

**测试方式：**
```bash
# 测试单个插件
venv/Scripts/python.exe debug_tools.py
# debug_tools.py 中已包含 Layer 2 插件测试部分

# 或单独测试
venv/Scripts/python.exe -c "
from plugins import PluginRegistry
import plugins.young_modulus  # 或你的新插件
p = PluginRegistry.get('杨氏模量（拉伸法）')
result = p.calculate({'钢丝直径(mm)': [0.495, 0.497], '砝码质量(kg)': [0,1], '标尺读数(mm)': [0,0.30]})
print(result)
"
```

---

### C同学 —— 工具函数与可视化（tool_executor.py + templates/）

**负责模块：** Matplotlib图表、报告模板、Gradio界面

| 文件 | 职责 | 核心工作 |
|------|------|---------|
| `tool_executor.py` | 工具函数库 | 统计/拟合/画图/报告生成 |
| `templates/` | 报告模板目录 | **当前为空，需要C同学添加** |
| `main.py` 中的 `start_web()` | Web启动 | Gradio界面配置 |

**需要添加/修改的内容：**

1. **优化图表（tool_executor.py 中的 create_chart）**
   - 改进图表样式、颜色方案、字体
   - 添加更多的图表类型（柱状图、误差棒图、双纵轴图等）
   - 支持中文字体自动检测

2. **改进报告生成（tool_executor.py 中的 generate_report）**
   - 在 `templates/` 目录下创建 HTML 报告模板文件
   - 例如：`templates/report_template.html`
   - 让报告有更好的排版和专业外观
   - 添加Word文档（.docx）输出支持

3. **改进 Web 界面（main.py 中的 start_web 函数）**
   - 优化 Gradio 布局（添加数据表格输入、文件上传等）
   - 支持语音输入（接Whisper）
   - 更好的用户体验

**templates/ 目录需要添加的文件：**

```html
<!-- templates/report_template.html -->
<!-- 一个专业的HTML报告模板，供 generate_report 使用 -->
```

```html
<!-- templates/experiment_card.html -->
<!-- 实验结果的预览卡片模板 -->
```

**测试方式：**
```bash
# 测试图表生成
venv/Scripts/python.exe -c "
from tool_executor import create_chart, generate_report
path = create_chart([1,2,3,4], [1.1,2.3,3.1,4.2], 'X', 'Y', '测试', fit_type='linear', save_name='test.png')
print('图表生成在:', path)
report_path = generate_report('测试实验', '数据摘要', '结果摘要', '分析文字', chart_paths=[path])
print('报告生成在:', report_path)
"
```

---

### D同学 —— 系统架构与集成（框架文件）

**负责模块：** 插件注册中心、工具调度器、状态管理、联调测试

| 文件 | 职责 | 核心工作 |
|------|------|---------|
| `plugins/__init__.py` | 插件基类+注册中心 | 框架核心，维护插件注册机制 |
| `experiment_state.py` | 实验状态管理 | 管理实验进度和数据 |
| `main.py` | 启动入口 | 加载插件、选择运行模式 |
| `debug_tools.py` | 调试脚本 | 分层验证，整合测试 |
| `requirements.txt` | 依赖管理 | 维护依赖清单 |

**需要添加/修改的内容：**

1. **完善实验状态管理（experiment_state.py）**
   - 确保状态流转正确：idle → recording → calculating → reporting → idle
   - 添加状态持久化（保存/加载历史实验记录）
   - 添加实验数据的校验逻辑

2. **维护调试脚本（debug_tools.py）**
   - 当B同学新增插件时，在debug_tools.py中添加对应的测试用例
   - 当C同学新增工具函数时，添加对应的测试

3. **维护依赖清单（requirements.txt）**
   - 跟踪所有新增的Python依赖包

---

## 📊 输出文件说明

运行后生成的文件在以下目录：

| 输出路径 | 类型 | 说明 |
|---------|------|------|
| `output/debug_test_chart.png` | 图表 | debug_tools.py生成的测试折线图 |
| `output/debug_test_report.html` | 报告 | debug_tools.py生成的测试HTML报告 |
| `output/young_modulus_fit.png` | 图表 | 杨氏模量实验的力-伸长量拟合图 |
| `output/YoungModulus_full_report.html` | 报告 | 杨氏模量实验完整报告 |
| `output/hall_effect_fit.png` | 图表 | 霍尔效应的电压-电流乘积拟合图 |
| `output/HallEffect_full_report.html` | 报告 | 霍尔效应实验完整报告 |

---

## 🔧 技术栈

| 组件 | 技术 | 负责人 |
|------|------|--------|
| AI引擎 | OpenAI 兼容 API（可配置） | A同学 |
| 科学计算 | NumPy, SciPy | B同学 |
| 图表生成 | Matplotlib | C同学 |
| 报告输出 | HTML / python-docx | C同学 |
| Web界面 | Gradio | C同学 |
| 实验插件 | 自定义插件系统 | B同学 |
| 状态管理 | Python类 | D同学 |
| 系统调度 | Python主循环 | D同学 |

---

## 🤝 协作流程

1. **各成员独立工作**：在自己的负责文件中修改，不互相影响
2. **新增实验插件**：B同学新建文件 → `@PluginRegistry.register` 自动注册 → D同学更新debug_tools.py添加测试
3. **新增工具函数**：C同学在tool_executor.py中添加 → A同学在assistant.py的TOOL_MAP中注册描述
4. **联调测试**：所有成员完成后，运行 `debug_tools.py` 做全流程测试
5. **代码提交**：确认所有功能正常后，提交到Git仓库