"""
AI物理实验助教系统 —— 主入口
================================
整合了实验数据处理 + AI智能助教问答功能。

运行方式: python main.py
启动后打开浏览器访问 http://localhost:5000 即可使用。
"""

import importlib
import pkgutil
import os
import sys
import json
import random
import threading
import time
import shutil

# 确保当前目录在模块搜索路径中
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, render_template, send_from_directory, jsonify

# ──────────────────────────────────────────────
# Flask 应用初始化
# ──────────────────────────────────────────────
app = Flask(__name__, static_folder='b_static', static_url_path='/static')
basepath = os.path.dirname(__file__)

import matplotlib
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'

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

    # 注册B同学的实验模块（通过适配器）
    try:
        from b_adapter import register_all_b_modules
        print("\n[B模块适配] 开始加载B同学的实验模块...")
        b_count = register_all_b_modules()
        print(f"[B模块适配] 成功加载 {b_count} 个实验模块\n")
    except Exception as e:
        print(f"[警告] B模块适配器加载失败: {e}\n")

    print(f"  共发现 {len(PluginRegistry.list_all())} 个实验插件：")


# ──────────────────────────────────────────────
# 临时文件清理
# ──────────────────────────────────────────────
def removedir(dirpath):
    """约5分钟后删除用户数据"""
    time.sleep(320)
    shutil.rmtree(dirpath, ignore_errors=True)


# ==============================================
# 页面路由
# ==============================================

@app.route('/')
def index():
    """首页 - 功能选择"""
    from plugins import PluginRegistry
    experiments = PluginRegistry.list_all()
    # 按分类分组
    categories = {}
    for name in experiments:
        plugin = PluginRegistry.get(name)
        cat = getattr(plugin, 'category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            'name': name,
            'mod_name': getattr(plugin, '_mod_name', ''),
            'description': getattr(plugin, 'description', name)
        })
    return render_template("index.html", categories=categories)


@app.route('/experiment/<string:num>')
def experiment_page(num):
    """实验数据处理页面"""
    from plugins import PluginRegistry
    # 在已注册插件中查找对应的模块
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return render_template("404.html"), 404
    exp_name = plugin.name if hasattr(plugin, 'name') else num
    return render_template("experiment.html", num=num, name=exp_name)


@app.route('/chat')
def chat_page():
    """AI智能助教问答页面"""
    return render_template("chat.html")


# ==============================================
# 实验数据处理 API
# ==============================================

@app.route('/api/<string:num>/table-info', methods=['GET'])
def table_info(num):
    """返回表格列名和示例数据"""
    import pandas as pd
    import chardet

    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"error": "实验不存在"}), 404

    csv_path = os.path.join(basepath, 'b_static', 'experiment', num)
    if not os.path.isdir(csv_path):
        return jsonify({"columns": [], "exampleData": [], "rowCount": 0})

    # 查找示例数据文件
    for f in os.listdir(csv_path):
        if "示例数据" in f and f.endswith(".csv"):
            full_path = os.path.join(csv_path, f)
            try:
                with open(full_path, 'rb') as fh:
                    encode = chardet.detect(fh.read())['encoding']
                raw_df = pd.read_csv(full_path, header=0, encoding=encode, dtype=str, keep_default_na=False)
                columns = list(raw_df.columns)
                example_data = raw_df.values.tolist()
                return jsonify({
                    "columns": columns,
                    "exampleData": example_data,
                    "rowCount": len(raw_df)
                })
            except Exception as e:
                return jsonify({"columns": [], "exampleData": [], "rowCount": 0, "error": str(e)})

    return jsonify({"columns": [], "exampleData": [], "rowCount": 0})


@app.route('/api/<string:num>/handle-table', methods=['POST'])
def handle_table(num):
    """接收表格JSON数据并处理"""
    import pandas as pd

    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"code": 1, "data": "实验不存在"})

    data = request.get_json()
    if data and 'columns' in data and 'data' in data:
        fileid = str(random.randrange(1000000))
        workpath = os.path.join(basepath, "output", num, fileid) + os.sep
        os.makedirs(workpath, exist_ok=True)

        df = pd.DataFrame(data['data'], columns=data['columns'])
        exp_name = plugin.name if hasattr(plugin, 'name') else num
        df.to_csv(workpath + exp_name + '.csv', index=False, encoding='utf-8-sig')

        # 启动清理线程
        threading.Thread(target=removedir, args=(workpath,), daemon=True).start()

        # 调用B模块的handle
        mod = getattr(plugin, '_mod', None)
        if mod is None:
            return jsonify({"code": 1, "data": "该实验不支持直接数据处理"})

        old_cwd = os.getcwd()
        b_modules_dir = os.path.join(basepath, 'b_modules')
        try:
            os.chdir(b_modules_dir)
            result = mod.handle(workpath, "csv")
        except Exception as e:
            result = 1
            print(f"处理出错: {e}")
        finally:
            os.chdir(old_cwd)

        if result == 0:
            return jsonify({"code": 0, "data": fileid, "exp_name": exp_name})
        else:
            return jsonify({"code": 1, "data": "文档生成失败，请检查数据格式！"})

    return jsonify({"code": 1, "data": "数据格式错误！"})


@app.route('/api/download/<string:num>/<string:fileid>.docx')
def download_docx(num, fileid):
    """Word文档下载"""
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return render_template("404.html"), 404

    directory = os.path.join(basepath, 'output', num, fileid)
    exp_name = plugin.name if hasattr(plugin, 'name') else num
    filename = exp_name + '.docx'
    if os.path.exists(os.path.join(directory, filename)):
        return send_from_directory(directory, filename, as_attachment=True)
    return jsonify({"error": "文件不存在"}), 404


# ==============================================
# AI 对话 API
# ==============================================

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI助教对话接口"""
    from assistant import Assistant
    from experiment_state import ExperimentState

    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 获取或创建会话状态
    if session_id not in _sessions:
        _sessions[session_id] = ExperimentState()

    state = _sessions[session_id]

    # 获取或创建助手实例
    if _assistant_instance is None:
        _create_assistant()

    if _assistant_instance is None:
        return jsonify({"reply": "⚠️ LLM API 未配置，请设置 .env 文件中的 LLM_API_KEY 和 LLM_BASE_URL。"})

    response = _assistant_instance.chat(user_message, state)
    return jsonify({
        "reply": response,
        "session_id": session_id,
        "state": state.to_dict()
    })


@app.route('/api/chat/reset', methods=['POST'])
def api_chat_reset():
    """重置对话会话"""
    data = request.get_json() or {}
    session_id = data.get('session_id', 'default')
    if session_id in _sessions:
        del _sessions[session_id]
    return jsonify({"status": "ok"})


# ==============================================
# 数据异常检测 API
# ==============================================

@app.route('/api/abnormal-detect', methods=['POST'])
def api_abnormal_detect():
    """数据异常检测接口"""
    from abnormal_detector import AbnormalDetector

    data = request.get_json()
    experiment_name = data.get('experiment_name', '物理实验')
    mod_name = data.get('mod_name', '')  # 模块名（如 exp1b）
    pdf_text = data.get('pdf_text', '')  # 前端可传空字符串，后端自动从 PDF 加载
    columns = data.get('columns', [])
    data_rows = data.get('data', [])

    if not columns or not data_rows:
        return jsonify({"error": "请提供实验数据"}), 400

    # 如果前端未提供 pdf_text，则根据 mod_name 自动加载实验指导 PDF
    if not pdf_text and mod_name:
        pdf_text = _load_experiment_pdf_text(mod_name)

    if _assistant_instance is None:
        _create_assistant()

    if _assistant_instance is None or _assistant_instance.client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    try:
        detector = AbnormalDetector(
            llm_client=_assistant_instance.client,
            model_name=_assistant_instance.model
        )
        result = detector.detect_with_stats(
            experiment_name=experiment_name,
            pdf_text=pdf_text,
            columns=columns,
            data_rows=data_rows
        )
        return jsonify({
            "report": result["report"],
            "stats": result["stats_preview"],
            "pdf_loaded": bool(pdf_text),  # 告知前端是否成功加载了 PDF 知识库
            "mod_name": mod_name
        })
    except Exception as e:
        return jsonify({"error": f"异常检测失败: {str(e)}"}), 500


# ==============================================
# 图表生成 API
# ==============================================

@app.route('/api/generate-chart', methods=['POST'])
def api_generate_chart():
    """生成实验数据图表（AI 智能判断图表类型）"""
    from chart_generator import generate_chart, ai_suggest_chart_config

    data = request.get_json()
    columns = data.get('columns', [])
    data_rows = data.get('data', [])
    chart_config = data.get('config', None)  # 可选：用户自定义配置
    experiment_name = data.get('experiment_name', '')
    save_name = data.get('save_name', 'chart.png')

    if not columns or not data_rows:
        return jsonify({"error": "请提供实验数据"}), 400

    try:
        # 如果没有指定配置，用 AI 智能判断
        ai_reason = ""
        if chart_config is None:
            # 获取 LLM 客户端
            if _assistant_instance is None:
                _create_assistant()
            llm_client = _assistant_instance.client if _assistant_instance else None
            model_name = _assistant_instance.model if _assistant_instance else None

            chart_config = ai_suggest_chart_config(
                experiment_name=experiment_name,
                columns=columns,
                data_rows=data_rows,
                llm_client=llm_client,
                model_name=model_name
            )
            if chart_config:
                ai_reason = chart_config.get("ai_reason", "")

        result = generate_chart(columns, data_rows, chart_config, save_name)

        if result.get("path") and os.path.exists(result["path"]):
            chart_filename = os.path.basename(result["path"])
            return jsonify({
                "success": True,
                "chart_url": f"/api/chart-image/{chart_filename}",
                "chart_path": result["path"],
                "fit_result": result.get("fit_result"),
                "x_label": result.get("x_label", ""),
                "y_label": result.get("y_label", ""),
                "ai_reason": ai_reason,
                "chart_config": chart_config,
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "图表生成失败")
            })
    except Exception as e:
        return jsonify({"error": f"图表生成失败: {str(e)}"}), 500


@app.route('/api/chart-image/<string:filename>')
def serve_chart_image(filename):
    """提供图表图片访问"""
    chart_dir = os.path.join(basepath, "outputs", "charts")
    filepath = os.path.join(chart_dir, filename)
    if os.path.exists(filepath):
        return send_from_directory(chart_dir, filename)
    return jsonify({"error": "图片不存在"}), 404


# ==============================================
# AI 报告生成 API（LaTeX 代码）
# ==============================================

@app.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """AI生成实验报告（LaTeX格式），返回完整 .tex 代码"""
    from report_generator import LATEX_REPORT_SYSTEM_PROMPT, build_latex_document

    data = request.get_json()
    experiment_name = data.get('experiment_name', '物理实验')
    calc_results = data.get('calc_results', {})
    user_data = data.get('user_data', {})
    abnormal_report = data.get('abnormal_report', '')
    chart_info = data.get('chart_info', None)  # 图表信息

    if _assistant_instance is None:
        _create_assistant()

    if _assistant_instance is None or _assistant_instance.client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    prompt = _build_report_prompt(experiment_name, calc_results, user_data, abnormal_report, chart_info)

    try:
        # 1. AI 生成 LaTeX 正文
        response = _assistant_instance.client.chat.completions.create(
            model=_assistant_instance.model,
            messages=[
                {"role": "system", "content": LATEX_REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        latex_body = response.choices[0].message.content

        # 2. 包装为完整 LaTeX 文档
        tex_content = build_latex_document(experiment_name, latex_body)

        # 3. 保存 .tex 文件供下载
        report_id = str(random.randrange(1000000))
        output_dir = os.path.join(basepath, "outputs", "reports", report_id)
        os.makedirs(output_dir, exist_ok=True)
        tex_path = os.path.join(output_dir, "report.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        # 4. 如果有图表，复制到报告目录
        has_chart = False
        if chart_info and chart_info.get('chart_path'):
            src = chart_info['chart_path']
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, os.path.join(output_dir, "chart.png"))
                has_chart = True

        return jsonify({
            "report": tex_content,
            "report_id": report_id,
            "tex_url": f"/api/report-tex/{report_id}",
            "has_chart": has_chart
        })

    except Exception as e:
        return jsonify({"error": f"报告生成失败: {str(e)}"}), 500


@app.route('/api/report-tex/<string:report_id>')
def download_report_tex(report_id):
    """下载 LaTeX 源文件"""
    tex_path = os.path.join(basepath, "outputs", "reports", report_id, "report.tex")
    if os.path.exists(tex_path):
        return send_from_directory(
            os.path.join(basepath, "outputs", "reports", report_id),
            "report.tex",
            as_attachment=True,
            download_name="experiment_report.tex"
        )
    return jsonify({"error": "TEX 文件不存在"}), 404


@app.route('/api/report-chart/<string:report_id>')
def download_report_chart(report_id):
    """下载报告中的图表图片"""
    chart_path = os.path.join(basepath, "outputs", "reports", report_id, "chart.png")
    if os.path.exists(chart_path):
        return send_from_directory(
            os.path.join(basepath, "outputs", "reports", report_id),
            "chart.png",
            as_attachment=True,
            download_name="chart.png"
        )
    return jsonify({"error": "图表文件不存在"}), 404


# ==============================================
# 知识库问答 API
# ==============================================

@app.route('/api/knowledge-chat', methods=['POST'])
def api_knowledge_chat():
    """基于知识库的RAG问答"""
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    # 检索知识库
    context = _search_knowledge_base(question)

    if _assistant_instance is None:
        _create_assistant()

    if _assistant_instance is None or _assistant_instance.client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    try:
        response = _assistant_instance.client.chat.completions.create(
            model=_assistant_instance.model,
            messages=[
                {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
                {"role": "user", "content": f"参考资料：\n{context}\n\n用户问题：{question}"}
            ],
            temperature=0.3,
        )
        answer = response.choices[0].message.content
        return jsonify({"answer": answer, "sources": context[:200] if context else "无相关资料"})
    except Exception as e:
        return jsonify({"error": f"问答失败: {str(e)}"}), 500


# ==============================================
# 知识库上传 API
# ==============================================

@app.route('/api/knowledge-upload', methods=['POST'])
def api_knowledge_upload():
    """上传知识库文件"""
    if 'file' not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400

    kb_dir = os.path.join(basepath, "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)

    # 安全保存文件
    filename = file.filename.replace(' ', '_')
    filepath = os.path.join(kb_dir, filename)
    file.save(filepath)

    return jsonify({"status": "ok", "filename": filename})


# ==============================================
# 实验列表 API
# ==============================================

@app.route('/api/experiments')
def api_experiments():
    """获取所有可用实验列表"""
    from plugins import PluginRegistry
    experiments = []
    for name in PluginRegistry.list_all():
        plugin = PluginRegistry.get(name)
        experiments.append({
            "name": name,
            "mod_name": getattr(plugin, '_mod_name', ''),
            "category": getattr(plugin, 'category', '其他'),
            "description": getattr(plugin, 'description', name),
            "required_fields": getattr(plugin, 'required_fields', [])
        })
    return jsonify({"experiments": experiments})


# ==============================================
# 辅助函数
# ==============================================

REPORT_SYSTEM_PROMPT = """（已弃用，使用 report_generator.py 中的 LATEX_REPORT_SYSTEM_PROMPT）"""

KNOWLEDGE_SYSTEM_PROMPT = """你是一个物理实验知识库问答助手。根据提供的参考资料回答用户问题。
要求：
1. 优先使用参考资料中的内容回答
2. 如果参考资料中没有相关信息，请明确告知用户
3. 不要编造资料中不存在的内容
4. 回答要准确、简洁
5. 使用中文回答
6. 整体回答使用 Markdown，不要输出 HTML 标签
7. 行内数学公式使用 \\( ... \\)，独立数学公式使用 \\[ ... \\]
8. 不要输出没有分隔符包裹的 LaTeX 命令，不要把公式放进 Markdown 代码块
9. 除非用户明确要求 LaTeX 源码，否则不要输出完整 LaTeX 文档结构"""

# 会话管理
_sessions = {}
_assistant_instance = None


def _create_assistant():
    """创建AI助手实例"""
    global _assistant_instance
    try:
        from assistant import Assistant
        _assistant_instance = Assistant()
    except Exception as e:
        print(f"[警告] AI助手创建失败: {e}")
        _assistant_instance = None


def _find_plugin_by_mod_name(mod_name):
    """根据模块名（如exp0a）查找对应的插件"""
    from plugins import PluginRegistry
    for name in PluginRegistry.list_all():
        plugin = PluginRegistry.get(name)
        if hasattr(plugin, '_mod_name') and plugin._mod_name == mod_name:
            return plugin
    return None


# ──────────────────────────────────────────────
# 实验指导 PDF 文本提取（异常检测知识库）
# ──────────────────────────────────────────────
_pdf_text_cache = {}  # {mod_name: pdf_text} 缓存，避免重复读取


def _load_experiment_pdf_text(mod_name):
    """根据模块名加载对应实验指导 PDF 的全文文本

    PDF 文件位于 b_static/experiment/<mod_name>/ 目录下。
    提取结果会被缓存，避免每次请求都重新读取。

    参数:
        mod_name: str, 模块名（如 'exp1b'）

    返回:
        str: PDF 全文文本，如找不到 PDF 则返回空字符串
    """
    if mod_name in _pdf_text_cache:
        return _pdf_text_cache[mod_name]

    pdf_dir = os.path.join(basepath, "b_static", "experiment", mod_name)
    if not os.path.isdir(pdf_dir):
        print(f"  [PDF知识库] 目录不存在: {pdf_dir}")
        return ""

    # 查找目录中的 PDF 文件
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"  [PDF知识库] 未找到 PDF 文件: {pdf_dir}")
        return ""

    pdf_path = os.path.join(pdf_dir, pdf_files[0])

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        full_text = "\n".join(text_parts).strip()

        if full_text:
            _pdf_text_cache[mod_name] = full_text
            print(f"  [PDF知识库] 已加载: {mod_name} → {pdf_files[0]} ({len(full_text)} 字符)")
        else:
            print(f"  [PDF知识库] PDF 文本提取为空: {pdf_path}")
            return ""

        return full_text
    except Exception as e:
        print(f"  [PDF知识库] 读取失败 {pdf_path}: {e}")
        return ""


def _build_report_prompt(experiment_name, calc_results, user_data, abnormal_report="", chart_info=None):
    """构建报告生成提示词（支持异常检测报告和图表）"""
    data_str = json.dumps(user_data, ensure_ascii=False, indent=2) if user_data else "无"
    results_str = json.dumps(calc_results, ensure_ascii=False, indent=2) if calc_results else "无"

    abnormal_section = ""
    if abnormal_report and abnormal_report.strip():
        abnormal_section = f"""
数据异常检测报告（由异常检测模块得出，请在“数据异常检测分析”章节中完整引用）：
{abnormal_report}
"""

    chart_section = ""
    if chart_info:
        chart_section = f"""
实验数据图表已生成，请在“数据处理与计算”章节中用 \\includegraphics[width=0.8\\textwidth]{{chart.png}} 插入此图表。
图表信息：X轴={chart_info.get('x_label', '')}，Y轴={chart_info.get('y_label', '')}"""
        if chart_info.get('fit_result'):
            f = chart_info['fit_result']
            chart_section += f"\n拟合结果：{f.get('equation', '')}，R²={f.get('R2', '')}"

    return f"""请为以下实验生成完整的实验报告：

实验名称：{experiment_name}

用户输入的原始数据：
{data_str}

数据计算结果（由数学计算模块得出，请严格使用这些数据）：
{results_str}
{abnormal_section}{chart_section}
请生成完整的实验报告，包含：一、实验目的；二、实验原理；三、实验器材；四、实验步骤；五、实验数据记录；六、数据处理与计算；七、数据异常检测分析（如有）；八、误差分析；九、实验结论。
注意：所有数据必须使用上面提供的计算结果，不要编造任何数据。"""


def _search_knowledge_base(query):
    """简单的知识库检索（基于关键词匹配）"""
    kb_dir = os.path.join(basepath, "knowledge_base")
    if not os.path.isdir(kb_dir):
        return "知识库目录不存在，请上传实验资料文件。"

    results = []
    query_keywords = set(query.lower().split())

    for fname in os.listdir(kb_dir):
        fpath = os.path.join(kb_dir, fname)
        if not os.path.isfile(fpath):
            continue

        try:
            if fname.endswith('.txt') or fname.endswith('.md'):
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif fname.endswith('.csv'):
                import pandas as pd
                df = pd.read_csv(fpath)
                content = df.to_string()
            else:
                continue

            # 简单的关键词匹配评分
            content_lower = content.lower()
            score = sum(1 for kw in query_keywords if kw in content_lower)
            if score > 0:
                # 取前2000字符作为上下文
                results.append((score, content[:2000]))
        except Exception:
            continue

    if not results:
        return ""

    # 按匹配分数排序，取最相关的
    results.sort(key=lambda x: x[0], reverse=True)
    return "\n\n---\n\n".join(r[1] for r in results[:3])


# ==============================================
# 错误处理
# ==============================================

@app.errorhandler(404)
def error_404(e):
    return render_template("404.html"), 404


# ==============================================
# 启动
# ==============================================

if __name__ == '__main__':
    from plugins import PluginRegistry

    # 注册所有实验插件
    register_all_plugins()

    # 预创建AI助手实例
    _create_assistant()

    # 预加载所有实验指导 PDF 到缓存（异常检测知识库）
    print("\n[PDF知识库] 开始预加载实验指导 PDF…")
    _exp_base = os.path.join(basepath, "b_static", "experiment")
    if os.path.isdir(_exp_base):
        _loaded = 0
        for _dir_name in sorted(os.listdir(_exp_base)):
            _dir_path = os.path.join(_exp_base, _dir_name)
            if os.path.isdir(_dir_path):
                _pdfs = [f for f in os.listdir(_dir_path) if f.lower().endswith('.pdf')]
                if _pdfs:
                    _load_experiment_pdf_text(_dir_name)
                    _loaded += 1
        print(f"[PDF知识库] 预加载完成，共 {_loaded} 个实验指导 PDF")
    else:
        print(f"[PDF知识库] 目录不存在: {_exp_base}")

    print("\n" + "=" * 50)
    print("  AI物理实验助教系统 即将启动…")
    print("=" * 50 + "\n")

    port = 5001
    # 如果5001被占用，自动找可用端口
    import socket
    for p in range(5001, 5020):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", p))
                port = p
                break
        except OSError:
            continue

    print(f"\n{'=' * 50}")
    print(f"  AI物理实验助教系统 已启动")
    print(f"  打开浏览器访问: http://localhost:{port}")
    print(f"{'=' * 50}\n")

    app.run(host='0.0.0.0', port=port, debug=False)
