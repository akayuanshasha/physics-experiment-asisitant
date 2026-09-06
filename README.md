# AI物理实验助教系统

一个基于 Flask 的物理实验智能助教系统，整合了 **实验数据处理** 与 **AI 智能问答** 两大能力，面向大学二级物理实验教学场景。

系统通过可插拔的实验插件机制，对 50+ 个物理实验（力学、电磁学等）提供统一的数据计算、图表绘制、Word 报告生成能力；同时内置 RAG（检索增强生成）问答引擎，可基于实验指导书 PDF 和用户上传资料进行智能答疑。

---

## 功能特性

- **实验数据处理**：对原始测量数据做拟合、不确定度传递、异常检测，输出计算结果。
- **图表生成**：基于 matplotlib 生成科学图表，嵌入报告与页面。
- **报告生成**：自动生成带公式（MathML/OMML）的 Word 实验报告。
- **AI 智能问答**：调用大模型（默认 GLM，兼容 OpenAI SDK），支持多轮对话。
- **RAG 检索**：支持 BM25 / 本地 embedding / 远程 embedding / 混合（RRF）多种检索模式，基于指导书与用户上传资料回答问题。
- **插件化架构**：新增一个实验只需按规范编写一个插件，无需改动框架。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | Flask |
| AI/LLM | OpenAI 兼容 SDK（`openai`）、`python-dotenv` |
| 科学计算 | NumPy、SciPy、SymPy、uncertainties、pandas |
| 图表 | matplotlib |
| 报告 | python-docx、lxml、latex2mathml |
| PDF 解析 | PyPDF2、pdfplumber、PyMuPDF（fitz） |
| 前端 | 原生 HTML/JS + MathJax 3（公式渲染）+ pdf.js（PDF 预览） |

---

## 目录结构

```
main/
├── main.py                 # 主入口（Flask 应用 + 路由）
├── b_adapter.py            # 将 b_modules 中的实验包装为插件
├── plugins/                # 插件基类与注册中心（核心）
│   └── __init__.py         # ExperimentPlugin + PluginRegistry
├── b_modules/              # 各实验模块（exp*.py，53 个实验）
├── b_static/               # 静态资源：知识库、实验数据、前端依赖
├── online_rag/             # RAG 检索增强问答引擎
├── api/                    # 计算 / 报告插入 / 转换等接口
├── templates/              # HTML 模板（index / chat / experiment）
├── prompts/                # 提示词模板
├── tests/                  # 测试
├── tools/                  # 离线构建 / 审计脚本
├── .env.example            # 环境变量模板（提交）
└── .env                    # 真实密钥（已 gitignore，不提交）
```

---

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
# 复制模板，填入真实 API 信息
cp .env.example .env
```

编辑 `.env`，至少填写 `LLM_API_KEY`。`.env` 已被 `.gitignore` 排除，**切勿提交真实密钥**。

### 3. 启动

```bash
python main.py
```

启动后会自动在 `5002～5019` 端口中选择可用端口，浏览器访问 `http://localhost:<端口>` 即可使用。

---

## 配置说明（`.env`）

| 变量 | 说明 | 默认 |
|------|------|------|
| `LLM_API_KEY` | 大模型 API 密钥（必填） | 无 |
| `LLM_BASE_URL` | OpenAI 兼容 API 地址 | `https://api.llm.ustc.edu.cn/v1` |
| `LLM_MODEL` | 对话模型名 | `glm-5.2-107` |
| `RAG_EMBEDDING_BACKEND` | 检索模式：`auto` / `remote` / `local` / `bm25` | `bm25` |
| `RAG_MIN_RRF_SCORE` | 最低相关性门槛（RRF） | `0.03` |
| `RAG_MIN_BM25_SCORE` | 最低相关性门槛（BM25） | `50.0` |
| `RAG_SESSION_DB` | 会话持久化路径 | `.cache/online_rag/sessions.sqlite3` |
| `REDIS_URL` | 填写后切换 Redis 会话存储 | 空（用 SQLite） |

更多可选项（embedding 服务、代理、重排模型等）见 `.env.example` 内注释。

> 学校未开放 embedding 服务时，建议保持 `RAG_EMBEDDING_BACKEND=bm25`（无需额外服务即可检索）。

---

## 插件化架构

每个物理实验都是一个继承 `ExperimentPlugin` 的插件，需实现三个方法：

- `calculate(data, constants)` — 处理原始数据 → 返回计算结果
- `generate_chart(data, results)` — 生成图表
- `get_report_content(data, results)` — 返回报告内容

插件通过 `@PluginRegistry.register` 装饰器注册。`b_adapter.py` 会扫描 `b_modules/` 下的 `exp*.py`，将 B 同学编写的 Flask 式模块（`name()` + `handle()`）自动包装为插件，使 AI 助教可调用全部实验。

---

## RAG 问答

`online_rag/` 实现完整的检索增强问答链路：

- **语料来源**：`b_static/knowledge_sources.json` 清单 + 用户上传资料（`user_corpus.py`）
- **检索**：BM25 / dense embedding / 混合（RRF），支持最低相关性门槛与上传资料加权
- **会话**：默认 SQLite 持久化，可切换 Redis（`RAG_SESSION_TTL_SECONDS`）
- **重排**：可选 cross-encoder 重排模型

---

## 测试

```bash
pytest
```

---

## 安全须知

- `.env` 中的 API 密钥**严禁提交**到仓库；已通过 `.gitignore` 保护。
- 仅需提交 `.env.example`（占位符模板）。
- 大体积产物（如 `evaluation_reports/`、字体文件）建议按需加入 `.gitignore` 或使用 Git LFS。

---

## License

项目仅供教学与研究使用。上传至 GitHub 前请确认不含任何敏感信息或受版权保护的数据。
