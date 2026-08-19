"""
AI二级物理实验助教系统 —— 主入口
================================
整合了实验数据处理 + AI智能助教问答功能。

运行方式: python main.py
启动后打开浏览器访问 http://localhost:5002 即可使用。
"""

import os
import sys
import json
import random
import re
import threading
import time
import shutil
import tempfile

# 确保当前目录在模块搜索路径中
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, render_template, send_from_directory, jsonify

# ──────────────────────────────────────────────
# Flask 应用初始化
# ──────────────────────────────────────────────
app = Flask(__name__, static_folder='b_static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 摄谱仪一次最多上传9张、合计60 MB
basepath = os.path.dirname(__file__)

# AI 报告使用系统临时目录，避免长期污染项目目录。生成后的文件在30分钟后清理。
_report_temp_paths = {}
_REPORT_CLEANUP_DELAY = 1800


def _schedule_report_cleanup(report_id):
    def _cleanup():
        temp_dir = _report_temp_paths.pop(report_id, None)
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    timer = threading.Timer(_REPORT_CLEANUP_DELAY, _cleanup)
    timer.daemon = True
    timer.start()

import matplotlib
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'

# ──────────────────────────────────────────────
# 自动注册所有实验模块
# ──────────────────────────────────────────────
def register_all_plugins():
    """通过统一适配器扫描并注册所有 ``b_modules/expXX.py``。"""
    from plugins import PluginRegistry
    try:
        from b_adapter import register_all_b_modules
        print("\n[B模块适配] 开始加载全部实验模块...")
        b_count = register_all_b_modules()
        print(f"[B模块适配] 成功加载 {b_count} 个实验模块\n")
    except Exception as e:
        print(f"[警告] B模块适配器加载失败: {e}\n")

    print(f"  共发现 {len(PluginRegistry.list_all())} 个实验插件：")


# ──────────────────────────────────────────────
# 临时文件清理
# ──────────────────────────────────────────────
def removedir(dirpath, delay=320):
    """延迟删除用户产生的临时文件。"""
    time.sleep(delay)
    shutil.rmtree(dirpath, ignore_errors=True)


# ==============================================
# 页面路由
# ==============================================

@app.route('/')
def index():
    """首页 - 功能选择"""
    from plugins import PluginRegistry
    experiments = PluginRegistry.list_all()

    # 名称规范化后再统计重名。只有确实重名时才保留“实验指导”等后缀。
    def _base_name(value):
        return (value.replace('B（实验指导）', '')
                .replace('B(实验指导)', '')
                .replace('（实验指导）', '')
                .replace('(实验指导)', ''))

    name_count = {}
    for name in experiments:
        normalized = _base_name(name)
        name_count[normalized] = name_count.get(normalized, 0) + 1

    # 两级导航：基础工具 / 一级大物 / 二级大物 → 学科。
    nested = {}
    subject_order = ['光学', '力学', '声学', '热学', '电磁学', '综合', '近代物理']
    for name in experiments:
        plugin = PluginRegistry.get(name)
        cat = getattr(plugin, 'category', '其他')
        if cat == '基础工具':
            level, subject = '基础工具', ''
        elif cat.startswith('一级-'):
            level, subject = '一级大物', cat.replace('一级-', '', 1)
        elif cat.startswith('二级-'):
            level, subject = '二级大物', cat.replace('二级-', '', 1)
        else:
            level, subject = '其他', cat

        nested.setdefault(level, {}).setdefault(subject, []).append({
            'name': name if name_count[_base_name(name)] > 1 else _base_name(name),
            'mod_name': getattr(plugin, '_mod_name', ''),
            'description': getattr(plugin, 'description', name)
        })

    def _subject_key(item):
        subject = item[0]
        return subject_order.index(subject) if subject in subject_order else 99

    for level in nested:
        nested[level] = dict(sorted(nested[level].items(), key=_subject_key))
    level_order = {'基础工具': 0, '一级大物': 1, '二级大物': 2, '其他': 3}
    nested = dict(sorted(nested.items(), key=lambda item: level_order.get(item[0], 99)))
    return render_template("index.html", nested=nested)


@app.route('/experiment/<string:num>')
def experiment_page(num):
    """实验数据处理页面"""
    from plugins import PluginRegistry
    # 在已注册插件中查找对应的模块
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return render_template("404.html"), 404
    exp_name = plugin.name if hasattr(plugin, 'name') else num
    exp_name = (exp_name.replace('B（实验指导）', '')
                .replace('B(实验指导)', '')
                .replace('（实验指导）', '')
                .replace('(实验指导)', ''))
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
    """返回实验模块自己声明的表格结构和示例数据。"""

    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"error": "实验不存在"}), 404

    # 所有输入结构和示例数据都必须由对应的 b_modules/expXX.py 声明。
    mod = getattr(plugin, '_mod', None)
    schema_factory = getattr(mod, 'schema', None) if mod is not None else None
    if callable(schema_factory):
        try:
            schema = schema_factory()
            schema.setdefault("schema_version", 2)
            return jsonify(schema)
        except Exception as e:
            return jsonify({"error": f"实验表格结构加载失败：{e}"}), 500
    return jsonify({"error": f"{num} 未在对应 expXX.py 中声明 schema()"}), 500


@app.route('/api/<string:num>/preview', methods=['POST'])
def preview_table(num):
    """调用实验后端的只读预计算接口，为通用前端补全计算列。"""
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"code": 1, "message": "实验不存在"}), 404

    payload = request.get_json() or {}
    module = getattr(plugin, '_mod', None)
    handler = getattr(module, 'preview', None) if module is not None else None
    if handler is None:
        plugin_object = plugin() if isinstance(plugin, type) else plugin
        handler = getattr(plugin_object, 'preview', None)
    if not callable(handler):
        return jsonify({"code": 0, "tables": payload.get("tables") or {}})

    try:
        result = handler(payload)
    except Exception as exc:
        return jsonify({"code": 1, "message": f"自动计算失败：{exc}"}), 400
    if not isinstance(result, dict) or not isinstance(result.get("tables"), dict):
        return jsonify({"code": 1, "message": "实验模块返回了无效的预计算结果"}), 500
    return jsonify({"code": 0, **result})


@app.route('/api/<string:num>/handle-table', methods=['POST'])
def handle_table(num):
    """接收表格JSON数据并处理"""
    import pandas as pd

    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"code": 1, "data": "实验不存在"})

    data = request.get_json() or {}

    # 新版多表协议。模块直接接收结构化数据并生成专用计算结果、报告和图表。
    if data.get('schema_version') == 2 or 'tables' in data:
        mod = getattr(plugin, '_mod', None)

        fileid = str(random.randrange(1000000))
        workpath = os.path.join(basepath, "output", num, fileid) + os.sep
        os.makedirs(workpath, exist_ok=True)

        old_cwd = os.getcwd()
        b_modules_dir = os.path.join(basepath, 'b_modules')
        try:
            if mod is not None and hasattr(mod, 'handle_structured'):
                os.chdir(b_modules_dir)
                result = mod.handle_structured(workpath, data)
            else:
                from unified_schema import handle_plugin_structured
                result = handle_plugin_structured(plugin, num, workpath, data)
        except Exception as e:
            result = {"code": 1, "message": f"处理出错：{e}"}
            print(f"结构化实验处理出错: {e}")
        finally:
            os.chdir(old_cwd)

        if isinstance(result, dict) and result.get("code") == 0:
            exp_name = plugin.name if hasattr(plugin, 'name') else num
            charts = []
            for chart in result.get("charts", []):
                item = dict(chart)
                filename = os.path.basename(item.get("filename", ""))
                if filename:
                    item["filename"] = filename
                    item["url"] = f"/api/result-file/{num}/{fileid}/{filename}"
                    charts.append(item)
            threading.Thread(target=removedir, args=(workpath,), daemon=True).start()
            return jsonify({
                "code": 0,
                "data": fileid,
                "exp_name": exp_name,
                "summary": result.get("summary", []),
                "warnings": result.get("warnings", []),
                "charts": charts,
            })

        shutil.rmtree(workpath, ignore_errors=True)
        message = result.get("message", "文档生成失败，请检查数据格式！") \
            if isinstance(result, dict) else "文档生成失败，请检查数据格式！"
        return jsonify({"code": 1, "data": message})

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


@app.route('/api/<string:num>/process-images', methods=['POST'])
def process_experiment_images(num):
    """处理实验模块声明的图像输入；当前用于摄谱仪九幅谱图。"""
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"code": 1, "data": "实验不存在"})
    mod = getattr(plugin, '_mod', None)
    if mod is None or not hasattr(mod, 'process_images'):
        return jsonify({"code": 1, "data": "该实验没有图像处理流程"})

    fileid = str(random.randrange(1000000))
    workpath = os.path.join(basepath, "output", num, fileid) + os.sep
    os.makedirs(workpath, exist_ok=True)
    old_cwd = os.getcwd()
    b_modules_dir = os.path.join(basepath, 'b_modules')
    try:
        os.chdir(b_modules_dir)
        result = mod.process_images(workpath, request.files, request.form.to_dict())
    except Exception as e:
        result = {"code": 1, "message": f"图像处理出错：{e}"}
        print(f"实验图像处理出错: {e}")
    finally:
        os.chdir(old_cwd)

    if isinstance(result, dict) and result.get("code") == 0:
        charts = []
        for chart in result.get("charts", []):
            item = dict(chart)
            filename = os.path.basename(item.get("filename", ""))
            if filename:
                item["filename"] = filename
                item["url"] = f"/api/result-file/{num}/{fileid}/{filename}"
                charts.append(item)
        # 图像复核通常比普通下载耗时更长，保留30分钟后再清理。
        threading.Thread(target=removedir, args=(workpath, 1800), daemon=True).start()
        return jsonify({
            "code": 0,
            "data": fileid,
            "summary": result.get("summary", []),
            "warnings": result.get("warnings", []),
            "charts": charts,
        })

    shutil.rmtree(workpath, ignore_errors=True)
    message = result.get("message", "图像处理失败，请检查文件格式和数量") \
        if isinstance(result, dict) else "图像处理失败，请检查文件格式和数量"
    return jsonify({"code": 1, "data": message})


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


@app.route('/api/result-file/<string:num>/<string:fileid>/<string:filename>')
def result_file(num, fileid, filename):
    """提供结构化实验生成的图表等结果文件。"""
    if not re.fullmatch(r'exp\d+[a-z]?', num) or not fileid.isdigit():
        return jsonify({"error": "结果路径不合法"}), 400
    safe_name = os.path.basename(filename)
    if safe_name != filename or not safe_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        return jsonify({"error": "文件名不合法"}), 400
    directory = os.path.join(basepath, 'output', num, fileid)
    if os.path.exists(os.path.join(directory, safe_name)):
        return send_from_directory(directory, safe_name)
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
    mod_name = data.get('mod_name', '')
    pdf_text = data.get('pdf_text', '')
    columns = data.get('columns', [])
    data_rows = data.get('data', [])
    analysis_hints = data.get('analysis_hints')

    # 多表实验在异常检测时合并成一张带“数据表”来源列的宽表，
    # 既保留各表身份，又复用现有的统计和 AI 分析模块。
    structured_tables = data.get('tables') or {}
    if structured_tables and not (columns and data_rows):
        all_keys = []
        for rows in structured_tables.values():
            for row in rows or []:
                for key in row.keys():
                    if key not in all_keys:
                        all_keys.append(key)
        columns = ['数据表'] + all_keys
        data_rows = []
        for table_id, rows in structured_tables.items():
            for row in rows or []:
                data_rows.append([table_id] + [row.get(key, '') for key in all_keys])

    if not columns or not data_rows:
        return jsonify({"error": "请提供实验数据"}), 400

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
            data_rows=data_rows,
            analysis_hints=analysis_hints,
        )
        return jsonify({
            "report": result["report"],
            "stats": result["stats_preview"],
            "pdf_loaded": bool(pdf_text),
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
    chart_config = data.get('config', None)
    experiment_name = data.get('experiment_name', '')
    save_name = data.get('save_name', 'chart.png')

    if not columns or not data_rows:
        return jsonify({"error": "请提供实验数据"}), 400

    try:
        ai_reason = ""
        if chart_config is None:
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

def _safe_report_chart_path(candidate):
    """只允许报告读取项目生成目录中的图表，拒绝客户端传入任意本地路径。"""
    if not candidate:
        return None
    real_candidate = os.path.realpath(candidate)
    allowed_roots = [
        os.path.realpath(os.path.join(basepath, 'output')),
        os.path.realpath(os.path.join(basepath, 'outputs', 'charts')),
    ]
    for root in allowed_roots:
        try:
            if os.path.commonpath([root, real_candidate]) == root and os.path.isfile(real_candidate):
                return real_candidate
        except ValueError:
            continue
    return None


def _collect_report_charts(chart_info, mod_name, calc_results):
    """把旧单图、新多图和结构化结果统一为图表列表。"""
    if not isinstance(chart_info, dict):
        return []

    raw_items = []
    if chart_info.get('chart_path'):
        raw_items.append(chart_info)
    for item in chart_info.get('charts', []) or []:
        if isinstance(item, dict):
            raw_items.append(item)
    for key in sorted(k for k in chart_info if re.fullmatch(r'chart\d+', k)):
        item = chart_info.get(key)
        if isinstance(item, dict):
            raw_items.append(item)

    fileid = str((calc_results or {}).get('fileid') or (calc_results or {}).get('data') or '')
    result = []
    for index, item in enumerate(raw_items, 1):
        candidate = item.get('chart_path')
        filename = os.path.basename(item.get('filename', ''))
        if not candidate and filename and mod_name and fileid.isdigit():
            candidate = os.path.join(basepath, 'output', mod_name, fileid, filename)
        safe_path = _safe_report_chart_path(candidate)
        if safe_path:
            result.append({
                'name': f'chart_{index}',
                'path': safe_path,
                'title': item.get('title', f'实验图表{index}'),
                'x_label': item.get('x_label', ''),
                'y_label': item.get('y_label', ''),
                'fit_result': item.get('fit_result'),
            })
    return result


@app.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """AI生成实验报告，并在本机可用时编译为PDF。"""
    from report_generator import LATEX_REPORT_SYSTEM_PROMPT, build_latex_document, compile_latex_to_pdf

    data = request.get_json() or {}
    experiment_name = data.get('experiment_name', '物理实验')
    mod_name = data.get('mod_name', '')
    calc_results = data.get('calc_results', {})
    user_data = data.get('user_data', {})
    abnormal_report = data.get('abnormal_report', '')
    chart_info = data.get('chart_info')
    pdf_text = _load_experiment_pdf_text(mod_name) if mod_name else ''

    if _assistant_instance is None:
        _create_assistant()
    if _assistant_instance is None or _assistant_instance.client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    prompt = _build_report_prompt(
        experiment_name, calc_results, user_data, abnormal_report,
        chart_info, pdf_text=pdf_text,
    )

    try:
        response = _assistant_instance.client.chat.completions.create(
            model=_assistant_instance.model,
            messages=[
                {"role": "system", "content": LATEX_REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=8192,
        )
        latex_body = response.choices[0].message.content
        if not latex_body:
            return jsonify({"error": "模型未生成有效报告内容，请重试"}), 502

        tex_content = build_latex_document(experiment_name, latex_body)
        report_id = str(random.randrange(1000000))
        temp_dir = tempfile.mkdtemp(prefix=f"report_{report_id}_")
        _report_temp_paths[report_id] = temp_dir

        with open(os.path.join(temp_dir, 'report.tex'), 'w', encoding='utf-8') as file:
            file.write(tex_content)

        charts = _collect_report_charts(chart_info, mod_name, calc_results)
        for chart in charts:
            shutil.copy2(chart['path'], os.path.join(temp_dir, chart['name'] + '.png'))

        compile_result = compile_latex_to_pdf(tex_content, temp_dir)
        pdf_url = f"/api/report-pdf/{report_id}" if compile_result.get('success') else None
        pdf_error = None if pdf_url else compile_result.get('error', 'PDF编译失败')
        _schedule_report_cleanup(report_id)

        return jsonify({
            "report": tex_content,
            "report_id": report_id,
            "tex_url": f"/api/report-tex/{report_id}",
            "pdf_url": pdf_url,
            "pdf_error": pdf_error,
            "has_chart": bool(charts),
            "chart_count": len(charts),
        })
    except Exception as e:
        return jsonify({"error": f"报告生成失败: {str(e)}"}), 500


@app.route('/api/report-tex/<string:report_id>')
def download_report_tex(report_id):
    """下载临时目录中的 LaTeX 源文件。"""
    temp_dir = _report_temp_paths.get(report_id)
    if not temp_dir:
        return jsonify({"error": "报告已过期或不存在，请重新生成"}), 404
    tex_path = os.path.join(temp_dir, 'report.tex')
    if os.path.exists(tex_path):
        return send_from_directory(
            temp_dir,
            "report.tex",
            as_attachment=True,
            download_name="experiment_report.tex"
        )
    return jsonify({"error": "TEX 文件不存在"}), 404


@app.route('/api/report-pdf/<string:report_id>')
def report_pdf(report_id):
    """在线预览或下载生成的PDF；download=1时作为附件下载。"""
    temp_dir = _report_temp_paths.get(report_id)
    if not temp_dir:
        return jsonify({"error": "报告已过期或不存在，请重新生成"}), 404
    pdf_path = os.path.join(temp_dir, 'report.pdf')
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF不存在，请下载TEX源码后本地编译"}), 404
    return send_from_directory(
        temp_dir,
        'report.pdf',
        as_attachment=request.args.get('download') == '1',
        download_name='experiment_report.pdf',
    )


@app.route('/api/report-chart/<string:report_id>')
def download_report_chart(report_id):
    """旧接口保留为明确提示，多图表请使用各自图表地址。"""
    return jsonify({"error": "报告现已支持多图表，请从图表结果区下载原图"}), 410


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

KNOWLEDGE_SYSTEM_PROMPT = """你是一个物理实验知识库问答助手。根据提供的参考资料回答用户问题。
要求：
1. 优先使用参考资料中的内容回答
2. 如果参考资料中没有相关信息，请明确告知用户
3. 不要编造资料中不存在的内容
4. 回答要准确、简洁
5. 使用中文回答"""

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
    """根据模块名（如exp26）查找对应的插件"""
    from plugins import PluginRegistry
    for name in PluginRegistry.list_all():
        plugin = PluginRegistry.get(name)
        if hasattr(plugin, '_mod_name') and plugin._mod_name == mod_name:
            return plugin
    return None


# ──────────────────────────────────────────────
# 实验指导 PDF 文本提取（异常检测知识库）
# ──────────────────────────────────────────────
_pdf_text_cache = {}


def _load_experiment_pdf_text(mod_name):
    """根据模块名加载对应实验指导 PDF 的全文文本"""
    if mod_name in _pdf_text_cache:
        return _pdf_text_cache[mod_name]

    # 优先读取已提取的文本文件
    txt_path = os.path.join(basepath, "b_static", "experiment", mod_name, "实验指导_提取文本.txt")
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
            # 跳过头部元信息
            idx = text.find('=' * 60)
            if idx > 0:
                text = text[idx + 60:].strip()
            _pdf_text_cache[mod_name] = text
            print(f"  [PDF知识库] 从缓存加载: {mod_name} ({len(text)} 字符)")
            return text
        except Exception as e:
            print(f"  [PDF知识库] 文本读取失败: {e}")

    # 回退：从 PDF 直接提取
    pdf_dir = os.path.join(basepath, "b_static", "experiment", mod_name)
    if not os.path.isdir(pdf_dir):
        return ""

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
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
        return full_text
    except Exception as e:
        print(f"  [PDF知识库] 读取失败 {pdf_path}: {e}")
        return ""


def _build_report_prompt(
    experiment_name, calc_results, user_data, abnormal_report="",
    chart_info=None, pdf_text="",
):
    """构建报告生成提示词，兼容单表、多表和多图表。"""
    data_str = json.dumps(user_data, ensure_ascii=False, indent=2) if user_data else "无"
    results_str = json.dumps(calc_results, ensure_ascii=False, indent=2) if calc_results else "无"

    guide_section = ""
    if pdf_text and pdf_text.strip():
        guide_section = f"""
实验指导书摘录（仅用于核对实验原理、仪器和步骤，不得从中虚构测量数据）：
{pdf_text[:4000]}
"""

    abnormal_section = ""
    if abnormal_report and abnormal_report.strip():
        abnormal_section = f"""
数据异常检测报告（由异常检测模块得出，请在“数据异常检测分析”章节中引用）：
{abnormal_report}
"""

    chart_section = ""
    if isinstance(chart_info, dict):
        chart_items = []
        if chart_info.get('chart_path'):
            chart_items.append(chart_info)
        chart_items.extend(
            item for item in chart_info.get('charts', []) or [] if isinstance(item, dict)
        )
        chart_items.extend(
            chart_info[key]
            for key in sorted(k for k in chart_info if re.fullmatch(r'chart\d+', k))
            if isinstance(chart_info.get(key), dict)
        )
        if chart_items:
            chart_section = '\n实验数据图表已经生成，请在“数据处理与计算”章节中插入：\n'
            for index, item in enumerate(chart_items, 1):
                chart_section += (
                    f"\\includegraphics[width=0.82\\textwidth]{{chart_{index}.png}} "
                    f"（{item.get('title', f'图表{index}')}）\n"
                )
                fit_result = item.get('fit_result')
                if isinstance(fit_result, dict):
                    chart_section += (
                        f"拟合结果：{fit_result.get('equation', '')}，"
                        f"R²={fit_result.get('R2', '')}\n"
                    )

    return f"""请为以下实验生成完整的实验报告：

实验名称：{experiment_name}

用户输入的原始数据：
{data_str}

数据计算结果（由数学计算模块得出，请严格使用这些数据）：
{results_str}
{guide_section}{abnormal_section}{chart_section}
请生成完整的实验报告，包含：一、实验目的；二、实验原理；三、实验器材；四、实验步骤；五、实验数据记录；六、数据处理与计算；七、数据异常检测分析（如有）；八、误差分析；九、实验结论。
注意：所有测量数据必须来自上面提供的内容，不要编造任何数据。"""


def _search_knowledge_base(query):
    """简单的知识库检索（基于关键词匹配）"""
    kb_dir = os.path.join(basepath, "knowledge_base")
    if not os.path.isdir(kb_dir):
        # 回退：搜索实验指导提取文本
        exp_base = os.path.join(basepath, "b_static", "experiment")
        results = []
        query_keywords = set(query.lower().split())
        if os.path.isdir(exp_base):
            for dname in os.listdir(exp_base):
                txt_path = os.path.join(exp_base, dname, "实验指导_提取文本.txt")
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        content_lower = content.lower()
                        score = sum(1 for kw in query_keywords if kw in content_lower)
                        if score > 0:
                            idx = content.find('=' * 60)
                            body = content[idx + 60:].strip() if idx > 0 else content
                            results.append((score, body[:2000]))
                    except Exception:
                        continue
        if results:
            results.sort(key=lambda x: x[0], reverse=True)
            return "\n\n---\n\n".join(r[1] for r in results[:3])
        return "知识库为空，请上传实验资料文件或确保实验指导文本已提取。"

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
            content_lower = content.lower()
            score = sum(1 for kw in query_keywords if kw in content_lower)
            if score > 0:
                results.append((score, content[:2000]))
        except Exception:
            continue

    if not results:
        return ""

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

    # 预加载所有实验指导文本到缓存（异常检测知识库）
    print("\n[PDF知识库] 开始预加载实验指导文本…")
    _exp_base = os.path.join(basepath, "b_static", "experiment")
    if os.path.isdir(_exp_base):
        _loaded = 0
        for _dir_name in sorted(os.listdir(_exp_base)):
            _dir_path = os.path.join(_exp_base, _dir_name)
            if os.path.isdir(_dir_path):
                # 检查是否有提取文本或PDF
                _has_txt = os.path.exists(os.path.join(_dir_path, "实验指导_提取文本.txt"))
                _pdfs = [f for f in os.listdir(_dir_path) if f.lower().endswith('.pdf')]
                if _has_txt or _pdfs:
                    _load_experiment_pdf_text(_dir_name)
                    _loaded += 1
        print(f"[PDF知识库] 预加载完成，共 {_loaded} 个实验指导文本")
    else:
        print(f"[PDF知识库] 目录不存在: {_exp_base}")

    print("\n" + "=" * 50)
    print("  AI二级物理实验助教系统 即将启动…")
    print("=" * 50 + "\n")

    port = 5002
    import socket
    for p in range(5002, 5020):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", p))
                port = p
                break
        except OSError:
            continue

    print(f"\n{'=' * 50}")
    print(f"  AI二级物理实验助教系统 已启动")
    print(f"  打开浏览器访问: http://localhost:{port}")
    print(f"{'=' * 50}\n")

    app.run(host='0.0.0.0', port=port, debug=False)
