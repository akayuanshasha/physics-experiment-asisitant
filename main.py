"""
AI二级物理实验助教系统 —— 主入口
================================
整合了实验数据处理 + AI智能助教问答功能。

运行方式: python main.py
启动后打开浏览器访问 对应网址 即可使用。
"""

import os
import atexit
import sys
import json
import hashlib
import math
import random
import re
import threading
import time
import shutil
import tempfile
import secrets

# 加载 .env 文件中的环境变量（使用脚本所在目录）
from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)

# 确保当前目录在模块搜索路径中
sys.path.insert(0, os.path.dirname(__file__))

from flask import (
    Flask, Response, jsonify, make_response, render_template, request,
    send_from_directory, stream_with_context,
)
from flask.json.provider import DefaultJSONProvider

# ──────────────────────────────────────────────
# Flask 应用初始化
# ──────────────────────────────────────────────
app = Flask(__name__, static_folder='b_static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 摄谱仪一次最多上传9张、合计60 MB
basepath = os.path.dirname(__file__)


def _json_safe(value):
    """递归把非有限浮点数（NaN/±Infinity）替换为 None。

    Python 的 json.dumps 默认会把 NaN/±Infinity 序列化成裸的
    ``NaN``/``-Infinity`` 字面量，这不是合法 JSON，浏览器 JSON.parse
    会报 “No number after minus sign in JSON” 之类的错误。
    通过自定义 JSON Provider 统一拦截，保证所有接口响应都是合法 JSON。
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class _SafeJSONProvider(DefaultJSONProvider):
    """全局 JSON 序列化兜底：非有限浮点数一律输出为 null。"""

    def dumps(self, obj, **kwargs):
        return super().dumps(_json_safe(obj), **kwargs)


app.json = _SafeJSONProvider(app)

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
    # 学科顺序与《一级大物实验指导》文件夹顺序一致。
    nested = {}
    subject_order = ['光学', '力学', '热学', '电磁学', '综合', '近代物理']
    
    def _mod_sort_key(mod_name):
        """按实验编号稳定排序；拆分模块紧跟同编号的基础模块。"""
        match = re.fullmatch(r"exp(\d+)(?:_([a-z]))?", mod_name)
        if not match:
            return (9999, 0)
        suffix = match.group(2)
        suffix_order = ord(suffix) - ord('a') + 1 if suffix else 0
        return (int(match.group(1)), suffix_order)

    # 一级实验的指导书顺序：按《一级大物实验指导》各文件夹内的文件顺序排列，
    # 指导书未收录的实验（干涉法、透镜、切变模量、固体比热与冷却法测量金属比热）
    # 接在对应学科末尾。
    _first_level_guide_order = [
        # 光学（含外壳实验）
        '分光计的调节和使用', '显微镜', '用分光计测三棱镜折射率', '衍射实验', '配色实验',
        '干涉法测微小量', '透镜参数测量',
        # 力学
        '匀加速运动', '单摆法测重力加速度', '声速测量', '密度的测量',
        '杨氏模量', '粘滞系数', '表面张力', '切变模量',
        # 热学
        '半导体温度计', '数字体温计', '固体比热与冷却法测量金属比热',
        # 电磁学
        '整流滤波', '直流电源特性', '硅光电池', '磁力摆', '示波器的使用',
        # 综合
        '生活中的物理实验',
        # 近代物理
        '光电效应', '密立根油滴实验',
    ]

    def _sort_key(level, display_name, mod_name):
        """一级实验按指导书文件顺序，其余按 b_static 目录顺序。"""
        if level == '一级大物' and display_name in _first_level_guide_order:
            return (0, _first_level_guide_order.index(display_name))
        return (1, _mod_sort_key(mod_name))

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

        display_name = name if name_count[_base_name(name)] > 1 else _base_name(name)
        nested.setdefault(level, {}).setdefault(subject, []).append({
            'name': display_name,
            'mod_name': getattr(plugin, '_mod_name', ''),
            'description': getattr(plugin, 'description', name),
            '_sort_key': _sort_key(level, display_name, getattr(plugin, '_mod_name', ''))
        })

    def _subject_key(item):
        subject = item[0]
        return subject_order.index(subject) if subject in subject_order else 99

    for level in nested:
        nested[level] = dict(sorted(nested[level].items(), key=_subject_key))
        # 在每个学科内，按照稳定的实验编号顺序排序。
        for subject in nested[level]:
            nested[level][subject].sort(key=lambda x: x.get('_sort_key', 9999))
    
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
    user_id, created = _request_user_identity()
    response = make_response(render_template("chat.html"))
    return _attach_user_cookie(response, user_id, created)


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


@app.route('/api/<string:num>/calc-table', methods=['POST'])
def calc_table(num):
    """单表即时计算接口：按某一张表的数据计算并返回结果摘要。

    请求体：{"table_id": "table1", "tables": {"table1": [...]}}
    模块需实现 calc_table(table_id, tables)；未实现或返回 None 表示该表不支持。
    """
    plugin = _find_plugin_by_mod_name(num)
    if plugin is None:
        return jsonify({"code": 1, "message": "实验不存在"}), 404

    payload = request.get_json() or {}
    table_id = payload.get("table_id")
    tables = payload.get("tables") or {}
    if not table_id:
        return jsonify({"code": 1, "message": "缺少 table_id"}), 400

    module = getattr(plugin, '_mod', None)
    handler = getattr(module, 'calc_table', None) if module is not None else None
    if not callable(handler):
        return jsonify({"code": 1, "message": "该实验不支持单表计算"}), 400

    old_cwd = os.getcwd()
    b_modules_dir = os.path.join(basepath, 'b_modules')
    try:
        os.chdir(b_modules_dir)
        result = handler(table_id, tables)
    except Exception as exc:
        return jsonify({"code": 1, "message": f"计算失败：{exc}"}), 400
    finally:
        os.chdir(old_cwd)

    if not isinstance(result, dict):
        return jsonify({"code": 1, "message": "该表不支持即时计算"}), 400
    return jsonify({
        "code": 0,
        "summary": result.get("summary", []),
        "warnings": result.get("warnings", []),
    })


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
    if not re.fullmatch(r'exp\d+(?:_?[a-z])?', num) or not fileid.isdigit():
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
    """AI助教问答接口（RAG 知识库问答，不涉及实验数据处理）"""
    request_started = time.perf_counter()
    request_id = secrets.token_hex(12)
    data = request.get_json() or {}
    user_message = (data.get('message') or '').strip()
    session_id = str(data.get('session_id', 'default'))[:128]
    user_id, created_user = _request_user_identity()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 读取本轮之前的对话历史（session 维度）
    history = _get_session_store().get(user_id, session_id)

    result = _answer_chat_question(
        user_message, history=list(history), user_id=user_id,
    )

    # 只有成功回答才进入历史，避免后续追问携带网络错误文本。
    if not result.get("error"):
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": result["answer"]})
        _get_session_store().set(user_id, session_id, history[-20:])

    total_ms = (time.perf_counter() - request_started) * 1000
    diagnostics = {
        "request_id": request_id,
        "timings_ms": result.get("timings_ms", {"total": total_ms}),
        "retrieved_count": result.get("retrieved_count", 0),
        "evidence_count": result.get("evidence_count", len(result.get("sources", []))),
        "eligible_count": result.get("eligible_count", 0),
        "filtered_count": result.get("filtered_count", 0),
        "query_variant_count": result.get("query_variant_count", 0),
        "maximum_lexical_score": result.get("maximum_lexical_score", 0.0),
    }
    diagnostics["timings_ms"]["http_total"] = total_ms
    _get_rag_diagnostics().record({
        "request_id": request_id,
        "user": _anonymous_log_id(user_id),
        "session": _anonymous_log_id(session_id),
        "backend": result.get("backend", "online_rag"),
        "retrieval_mode": result.get("retrieval_mode"),
        "evidence_available": bool(result.get("evidence_available")),
        "retrieved_count": diagnostics["retrieved_count"],
        "evidence_count": diagnostics["evidence_count"],
        "eligible_count": diagnostics["eligible_count"],
        "filtered_count": diagnostics["filtered_count"],
        "query_variant_count": diagnostics["query_variant_count"],
        "maximum_lexical_score": diagnostics["maximum_lexical_score"],
        "history_rewrite_used": bool(result.get("history_rewrite_used", False)),
        "dense_fallback_reason": result.get("dense_fallback_reason"),
        "upload_intent_injection": result.get("upload_intent_injection", False),
        "upload_fallback_injection": result.get("upload_fallback_injection", False),
        "history_messages": len(history),
        "warning_count": len(result.get("warnings", [])),
        "error_type": result.get("error_type"),
        "error_stage": result.get("error_stage"),
        "error_message": result.get("error"),
        "proxy_mode": result.get("proxy_mode"),
        "generation_mode": result.get("generation_mode"),
        "fallback_used": bool(result.get("fallback_used")),
        "timings_ms": diagnostics["timings_ms"],
    })

    response = jsonify({
        "request_id": request_id,
        "reply": result["answer"],
        "sources": result.get("sources", []),
        "backend": result.get("backend", "online_rag"),
        "evidence_available": bool(result.get("evidence_available")),
        "warnings": result.get("warnings", []),
        "retrieval_mode": result.get("retrieval_mode"),
        "history_rewrite_used": result.get("history_rewrite_used", False),
        "diagnostics": diagnostics,
    })
    return _attach_user_cookie(response, user_id, created_user)


@app.route('/api/chat/reset', methods=['POST'])
def api_chat_reset():
    """重置对话会话"""
    data = request.get_json() or {}
    session_id = str(data.get('session_id', 'default'))[:128]
    user_id, created_user = _request_user_identity()
    _get_session_store().delete(user_id, session_id)
    return _attach_user_cookie(
        jsonify({"status": "ok"}), user_id, created_user,
    )


def _sse_event(name, payload):
    return (
        f"event: {name}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


@app.route('/api/chat/stream', methods=['POST'])
def api_chat_stream():
    """SSE 问答：先返回检索状态，再透传模型 token，最后返回引用与诊断。"""
    data = request.get_json() or {}
    user_message = (data.get('message') or '').strip()
    session_id = str(data.get('session_id', 'default'))[:128]
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    user_id, created_user = _request_user_identity()
    history = _get_session_store().get(user_id, session_id)
    request_id = secrets.token_hex(12)

    @stream_with_context
    def generate():
        request_started = time.perf_counter()
        assistant = None
        token_emitted = False
        yield _sse_event("status", {
            "request_id": request_id,
            "stage": "accepted",
        })
        try:
            assistant = _get_online_rag_assistant(user_id)
            result = None
            for event in assistant.ask_stream(
                user_message, conversation_history=list(history),
            ):
                if event["type"] == "done":
                    result = _online_result_to_web(event["result"])
                else:
                    if event["type"] == "token" and event.get("text"):
                        token_emitted = True
                    yield _sse_event(event["type"], {
                        key: value for key, value in event.items() if key != "type"
                    })
            if result is None:
                raise RuntimeError("流式问答未返回 done 结果")

            updated_history = list(history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": result["answer"]})
            _get_session_store().set(user_id, session_id, updated_history[-20:])
            total_ms = (time.perf_counter() - request_started) * 1000
            timings = dict(result.get("timings_ms", {}))
            timings["http_total"] = total_ms
            diagnostics = {
                "request_id": request_id,
                "timings_ms": timings,
                "retrieved_count": result.get("retrieved_count", 0),
                "evidence_count": result.get("evidence_count", len(result.get("sources", []))),
                "eligible_count": result.get("eligible_count", 0),
                "filtered_count": result.get("filtered_count", 0),
                "query_variant_count": result.get("query_variant_count", 0),
                "maximum_lexical_score": result.get("maximum_lexical_score", 0.0),
            }
            _get_rag_diagnostics().record({
                "request_id": request_id,
                "user": _anonymous_log_id(user_id),
                "session": _anonymous_log_id(session_id),
                "backend": result.get("backend", "online_rag"),
                "retrieval_mode": result.get("retrieval_mode"),
                "evidence_available": bool(result.get("evidence_available")),
                "retrieved_count": diagnostics["retrieved_count"],
                "evidence_count": diagnostics["evidence_count"],
                "eligible_count": diagnostics["eligible_count"],
                "filtered_count": diagnostics["filtered_count"],
                "query_variant_count": diagnostics["query_variant_count"],
                "maximum_lexical_score": diagnostics["maximum_lexical_score"],
                "history_rewrite_used": bool(result.get("history_rewrite_used", False)),
                "dense_fallback_reason": result.get("dense_fallback_reason"),
                "upload_intent_injection": result.get(
                    "upload_intent_injection", False
                ),
                "upload_fallback_injection": result.get(
                    "upload_fallback_injection", False
                ),
                "history_messages": len(updated_history),
                "warning_count": len(result.get("warnings", [])),
                "error_type": result.get("error_type"),
                "error_stage": result.get("error_stage"),
                "proxy_mode": result.get("proxy_mode"),
                "generation_mode": result.get("generation_mode"),
                "fallback_used": bool(result.get("fallback_used")),
                "token_emitted": token_emitted,
                "timings_ms": timings,
                "transport": "sse",
            })
            yield _sse_event("done", {
                "request_id": request_id,
                "reply": result["answer"],
                "sources": result.get("sources", []),
                "backend": result.get("backend", "online_rag"),
                "evidence_available": bool(result.get("evidence_available")),
                "warnings": result.get("warnings", []),
                "retrieval_mode": result.get("retrieval_mode"),
                "history_rewrite_used": result.get("history_rewrite_used", False),
                "diagnostics": diagnostics,
            })
        except Exception as exc:
            total_ms = (time.perf_counter() - request_started) * 1000
            chat_config = getattr(
                getattr(assistant, "chat_backend", None), "config", None,
            )
            _get_rag_diagnostics().record({
                "request_id": request_id,
                "user": _anonymous_log_id(user_id),
                "session": _anonymous_log_id(session_id),
                "backend": "online_rag",
                "evidence_available": False,
                "error_type": type(exc).__name__,
                "error_stage": getattr(exc, "stage", "generation"),
                "error_message": str(exc),
                "proxy_mode": getattr(chat_config, "proxy_mode", None),
                "generation_mode": "stream",
                "fallback_used": False,
                "token_emitted": token_emitted,
                "timings_ms": {"http_total": total_ms},
                "transport": "sse",
            })
            yield _sse_event("error", {
                "request_id": request_id,
                "message": (
                    "AI 回答传输中断，请稍后重试。"
                    if token_emitted else "AI 服务连接失败，请稍后重试。"
                ),
                "partial": token_emitted,
            })

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return _attach_user_cookie(response, user_id, created_user)


# ==============================================
# 数据异常检测 API
# ==============================================

# 异常检测结果缓存（TTL）：同一份数据+指导书短时间内重复提交直接复用，避免重复调用 LLM
_abnormal_cache = {}
_ABNORMAL_CACHE_TTL = 600   # 缓存有效期（秒）
_ABNORMAL_CACHE_MAX = 32    # 最大条目数，超出时淘汰最旧


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

    # 结果缓存：请求体 + 指导书文本共同决定分析结果
    body_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    pdf_hash = hashlib.sha256((pdf_text or "").encode("utf-8")).hexdigest()
    cache_key = (body_hash, pdf_hash)
    cached = _abnormal_cache.get(cache_key)
    if cached and time.time() - cached["ts"] < _ABNORMAL_CACHE_TTL:
        return jsonify({**cached["result"], "cached": True})

    if _llm_client is None:
        _create_llm_client()

    if _llm_client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    try:
        detector = AbnormalDetector(
            llm_client=_llm_client,
            model_name=_llm_model,
        )
        result = detector.detect_with_stats(
            experiment_name=experiment_name,
            pdf_text=pdf_text,
            columns=columns,
            data_rows=data_rows,
            analysis_hints=analysis_hints,
        )
        payload = {
            "report": result["report"],
            "stats": result["stats_preview"],
            "structured": result.get("structured"),
            "pdf_loaded": bool(pdf_text),
            "mod_name": mod_name
        }
        _abnormal_cache[cache_key] = {"ts": time.time(), "result": payload}
        if len(_abnormal_cache) > _ABNORMAL_CACHE_MAX:
            _abnormal_cache.pop(
                min(_abnormal_cache, key=lambda k: _abnormal_cache[k]["ts"]), None)
        return jsonify(payload)
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
            if _llm_client is None:
                _create_llm_client()
            llm_client = _llm_client
            model_name = _llm_model

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
        print(f"[报告] chart_info 不是 dict: {type(chart_info)}")
        return []

    print(f"[报告] chart_info 内容: {json.dumps(chart_info, ensure_ascii=False)[:500]}")

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

    print(f"[报告] 收集到 {len(raw_items)} 个原始图表项")

    fileid = str((calc_results or {}).get('fileid') or (calc_results or {}).get('data') or '')
    result = []
    for index, item in enumerate(raw_items, 1):
        candidate = item.get('chart_path')
        filename = os.path.basename(item.get('filename', ''))
        if not candidate and filename and mod_name and fileid.isdigit():
            candidate = os.path.join(basepath, 'output', mod_name, fileid, filename)
        print(f"[报告] 图表{index}: candidate={candidate}")
        safe_path = _safe_report_chart_path(candidate)
        print(f"[报告] 图表{index}: safe_path={safe_path}")
        if safe_path:
            result.append({
                'name': f'chart_{index}',
                'path': safe_path,
                'title': item.get('title', f'实验图表{index}'),
                'x_label': item.get('x_label', ''),
                'y_label': item.get('y_label', ''),
                'fit_result': item.get('fit_result'),
            })
    print(f"[报告] 最终收集到 {len(result)} 张有效图表")
    return result


@app.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """AI生成实验报告，并在本机可用时编译为PDF。"""
    from report_generator import LATEX_REPORT_SYSTEM_PROMPT, build_latex_document, compile_latex_to_pdf
    import time as _time
    _t0 = _time.time()

    data = request.get_json() or {}
    experiment_name = data.get('experiment_name', '物理实验')
    mod_name = data.get('mod_name', '')
    calc_results = data.get('calc_results', {})
    user_data = data.get('user_data', {})
    abnormal_report = data.get('abnormal_report', '')
    chart_info = data.get('chart_info')
    print(f"[报告] 后端收到的 chart_info 类型: {type(chart_info)}, 值: {chart_info}")
    print(f"[报告] 后端收到的 data keys: {list(data.keys())}")
    pdf_text = _load_experiment_pdf_text(mod_name) if mod_name else ''
    print(f"[报告] PDF文本加载完成 ({_time.time()-_t0:.1f}s), 长度={len(pdf_text)}字符")

    if _llm_client is None:
        _create_llm_client()
    if _llm_client is None:
        return jsonify({"error": "LLM API 未配置"}), 500

    prompt = _build_report_prompt(
        experiment_name, calc_results, user_data, abnormal_report,
        chart_info, pdf_text=pdf_text,
    )
    print(f"[报告] 开始调用LLM API生成报告... prompt长度={len(prompt)}字符")

    try:
        _t1 = _time.time()
        response = _llm_client.chat.completions.create(
            model=_llm_model,
            messages=[
                {"role": "system", "content": LATEX_REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=16384,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        print(f"[报告] LLM API 返回 ({_time.time()-_t1:.1f}s)")
        latex_body = response.choices[0].message.content
        print(f"[报告] LLM 返回内容长度: {len(latex_body) if latex_body else 0} 字符")
        if latex_body:
            # 检查是否包含 includegraphics
            import re as _re
            img_count = len(_re.findall(r'includegraphics', latex_body))
            print(f"[报告] LLM 返回中包含 {img_count} 个 \\includegraphics 命令")
        if not latex_body:
            return jsonify({"error": "模型未生成有效报告内容，请重试"}), 502

        tex_content = build_latex_document(experiment_name, latex_body)
        report_id = str(random.randrange(1000000))
        temp_dir = tempfile.mkdtemp(prefix=f"report_{report_id}_")
        _report_temp_paths[report_id] = temp_dir

        with open(os.path.join(temp_dir, 'report.tex'), 'w', encoding='utf-8') as file:
            file.write(tex_content)

        charts = _collect_report_charts(chart_info, mod_name, calc_results)
        print(f"[报告] 收集到 {len(charts)} 张图表")
        for chart in charts:
            shutil.copy2(chart['path'], os.path.join(temp_dir, chart['name'] + '.png'))

        _t2 = _time.time()
        print(f"[报告] 开始编译PDF...")
        compile_result = compile_latex_to_pdf(tex_content, temp_dir)
        print(f"[报告] PDF编译完成 ({_time.time()-_t2:.1f}s), success={compile_result.get('success')}")
        if compile_result.get('error'):
            print(f"[报告] PDF编译错误: {compile_result['error']}")
        pdf_url = f"/api/report-pdf/{report_id}" if compile_result.get('success') else None
        pdf_error = None if pdf_url else compile_result.get('error', 'PDF编译失败')
        _schedule_report_cleanup(report_id)

        print(f"[报告] 总耗时 {_time.time()-_t0:.1f}s")
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
        print(f"[报告] 异常: {e}")
        err_msg = str(e)
        if 'timed out' in err_msg.lower() or 'timeout' in err_msg.lower():
            return jsonify({"error": "LLM API 请求超时（180秒），API 服务响应缓慢，请稍后重试或检查网络连接。"}), 504
        return jsonify({"error": f"报告生成失败: {err_msg}"}), 500


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
    """基于 online_rag 的无会话状态兼容接口。"""
    data = request.get_json() or {}
    question = (data.get('question') or '').strip()

    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    user_id, created_user = _request_user_identity()
    result = _answer_online_rag_question(question, user_id=user_id)
    if result.get("error"):
        response = jsonify({"error": "AI 服务连接失败，请稍后重试。"})
        return _attach_user_cookie(response, user_id, created_user), 500
    response = jsonify({
        "answer": result["answer"],
        "sources": result.get("sources", []),
    })
    return _attach_user_cookie(response, user_id, created_user)


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

    user_id, created_user = _request_user_identity()
    kb_dir = os.path.join(basepath, "knowledge_base", "users", user_id)
    os.makedirs(kb_dir, exist_ok=True)

    original_name = os.path.basename(file.filename.replace('\\', '/'))
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', original_name).replace(' ', '_')
    if not filename or os.path.splitext(filename)[1].lower() not in {'.txt', '.md', '.csv', '.pdf'}:
        return jsonify({"error": "仅支持 txt、md、csv、pdf 文件"}), 400
    from online_rag import UserCorpusValidationError, validate_user_corpus_file

    extension = os.path.splitext(filename)[1].lower()
    filepath = os.path.join(kb_dir, filename)
    incoming_dir = os.path.join(kb_dir, ".incoming")
    os.makedirs(incoming_dir, exist_ok=True)
    handle, temporary_path = tempfile.mkstemp(suffix=extension, dir=incoming_dir)
    os.close(handle)
    try:
        file.save(temporary_path)
        validate_user_corpus_file(temporary_path)
        os.replace(temporary_path, filepath)
    except UserCorpusValidationError as exc:
        response = _attach_user_cookie(
            jsonify({"error": str(exc)}), user_id, created_user,
        )
        return response, 400
    except OSError:
        response = _attach_user_cookie(
            jsonify({"error": "文件保存失败，请稍后重试"}), user_id, created_user,
        )
        return response, 500
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    _discard_online_rag_assistant(user_id)

    return _attach_user_cookie(
        jsonify({"status": "ok", "filename": filename}), user_id, created_user,
    )


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

# 会话管理
_llm_client = None
_llm_model = None
_online_rag_instances = {}
_online_rag_lock = threading.Lock()
_session_store = None
_session_store_lock = threading.Lock()
_USER_COOKIE = "physics_rag_user"
_USER_ID_RE = re.compile(r"^u_[A-Za-z0-9_-]{20,80}$")
_rag_diagnostics = None
_rag_diagnostics_lock = threading.Lock()


def _request_user_identity():
    value = (request.cookies.get(_USER_COOKIE) or "").strip()
    if _USER_ID_RE.fullmatch(value):
        return value, False
    return "u_" + secrets.token_urlsafe(24), True


def _attach_user_cookie(response, user_id, created):
    if created:
        response.set_cookie(
            _USER_COOKIE,
            user_id,
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            samesite="Lax",
        )
    return response


def _get_session_store():
    global _session_store
    if _session_store is not None:
        return _session_store
    with _session_store_lock:
        if _session_store is None:
            from online_rag import create_session_store_from_env
            _session_store = create_session_store_from_env()
    return _session_store


def _anonymous_log_id(value):
    from online_rag import anonymous_id
    return anonymous_id(value)


def _get_rag_diagnostics():
    global _rag_diagnostics
    if _rag_diagnostics is not None:
        return _rag_diagnostics
    with _rag_diagnostics_lock:
        if _rag_diagnostics is None:
            from online_rag import RagDiagnostics
            _rag_diagnostics = RagDiagnostics(os.getenv(
                "RAG_DIAGNOSTICS_PATH", ".cache/online_rag/rag_events.jsonl"
            ))
    return _rag_diagnostics


def _create_llm_client():
    """创建异常检测、图表建议和报告生成共用的LLM客户端。"""
    global _llm_client, _llm_model
    try:
        from llm_client import create_llm_client_from_env
        _llm_client, _llm_model = create_llm_client_from_env()
    except Exception as e:
        print(f"[警告] 通用LLM客户端创建失败: {e}")
        _llm_client = None
        _llm_model = None


def _get_online_rag_assistant(user_id):
    """Lazily build an isolated online_rag assistant per browser user."""
    instance = _online_rag_instances.get(user_id)
    if instance is not None:
        return instance
    with _online_rag_lock:
        instance = _online_rag_instances.get(user_id)
        if instance is None:
            from online_rag import create_assistant_from_env
            instance = create_assistant_from_env(
                user_corpus_root=os.path.join(basepath, "knowledge_base", "users"),
                user_id=user_id,
            )
            _online_rag_instances[user_id] = instance
    return instance


def _close_online_rag_assistant(instance):
    close = getattr(instance, "close", None)
    if callable(close):
        try:
            close()
        except Exception as exc:
            print(f"[警告] online_rag 资源释放失败: {type(exc).__name__}")


def _discard_online_rag_assistant(user_id):
    with _online_rag_lock:
        instance = _online_rag_instances.pop(user_id, None)
    if instance is not None:
        _close_online_rag_assistant(instance)


def _close_all_online_rag_assistants():
    with _online_rag_lock:
        instances = list(_online_rag_instances.values())
        _online_rag_instances.clear()
    for instance in instances:
        _close_online_rag_assistant(instance)


atexit.register(_close_all_online_rag_assistants)


def _answer_online_rag_question(
    question, history=None, experiment_ids=None, user_id="anonymous",
):
    """Adapt online_rag's related sources to the existing web response shape."""
    assistant = None
    try:
        assistant = _get_online_rag_assistant(user_id)
        result = assistant.ask(
            question,
            conversation_history=history,
            experiment_ids=experiment_ids,
        )
    except Exception as exc:
        chat_config = getattr(
            getattr(assistant, "chat_backend", None), "config", None,
        )
        return {
            "answer": "AI 服务连接失败，请稍后重试。",
            "sources": [],
            "error": str(exc),
            "backend": "online_rag",
            "evidence_available": False,
            "warnings": [f"online_rag 调用失败：{type(exc).__name__}"],
            "retrieval_mode": None,
            "history_rewrite_used": False,
            "timings_ms": {},
            "retrieved_count": 0,
            "evidence_count": 0,
            "eligible_count": 0,
            "filtered_count": 0,
            "query_variant_count": 0,
            "maximum_lexical_score": 0.0,
            "dense_fallback_reason": None,
            "upload_intent_injection": False,
            "upload_fallback_injection": False,
            "error_type": type(exc).__name__,
            "error_stage": getattr(exc, "stage", "generation"),
            "proxy_mode": getattr(chat_config, "proxy_mode", None),
            "generation_mode": "nonstream",
            "fallback_used": False,
        }

    return _online_result_to_web(result)


def _online_result_to_web(result):
    sources = [item.to_dict() for item in result.citations]
    retrieval_diagnostics = dict(
        getattr(result, "retrieval_diagnostics", {}) or {}
    )
    return {
        "answer": result.answer,
        "sources": sources,
        "error": None,
        "backend": "online_rag",
        "evidence_available": bool(sources),
        "warnings": list(result.warnings),
        "retrieval_mode": result.retrieval.retrieval_mode,
        "history_rewrite_used": result.history_rewrite_used,
        "timings_ms": dict(result.timings_ms),
        "retrieved_count": len(result.retrieval.hits),
        "evidence_count": len(result.evidence),
        "eligible_count": retrieval_diagnostics.get("eligible_count", 0),
        "filtered_count": retrieval_diagnostics.get("filtered_count", 0),
        "query_variant_count": retrieval_diagnostics.get("query_variant_count", 0),
        "maximum_lexical_score": retrieval_diagnostics.get(
            "maximum_lexical_score", 0.0,
        ),
        "dense_fallback_reason": retrieval_diagnostics.get("dense_fallback_reason"),
        "upload_intent_injection": retrieval_diagnostics.get(
            "upload_intent_injection", False,
        ),
        "upload_fallback_injection": retrieval_diagnostics.get(
            "upload_fallback_injection", False,
        ),
        "error_type": None,
        "error_stage": None,
        "proxy_mode": getattr(result, "proxy_mode", None),
        "generation_mode": getattr(result, "generation_mode", ""),
        "fallback_used": bool(getattr(result, "fallback_used", False)),
    }


def _answer_chat_question(
    question, history=None, experiment_ids=None, user_id="anonymous",
):
    return _answer_online_rag_question(
        question, history=history, experiment_ids=experiment_ids, user_id=user_id,
    )


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

    # exp33_a / exp33_b 等拆分实验优先使用自己的资料目录；目录不存在时
    # 复用基础编号 exp33 的同一份实验指导，避免复制和维护重复文档。
    guide_mod_name = mod_name
    guide_dir = os.path.join(basepath, "b_static", "experiment", guide_mod_name)
    if not os.path.isdir(guide_dir):
        split_match = re.fullmatch(r"(exp\d+)_([a-z])", mod_name)
        if split_match:
            base_dir = os.path.join(basepath, "b_static", "experiment", split_match.group(1))
            if os.path.isdir(base_dir):
                guide_mod_name = split_match.group(1)
                guide_dir = base_dir

    # 优先读取已提取的文本文件
    txt_path = os.path.join(guide_dir, "实验指导_提取文本.txt")
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
    pdf_dir = guide_dir
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


def _escape_report_prompt_boundaries(value):
    """Prevent supplied text from opening or closing trusted prompt sections."""
    text = str(value or "")
    return re.sub(
        r"<\s*/?\s*(?:source|data)\s*>",
        lambda match: (
            match.group(0).replace("<", "&lt;").replace(">", "&gt;")
        ),
        text,
        flags=re.IGNORECASE,
    )


def _build_report_prompt(
    experiment_name, calc_results, user_data, abnormal_report="",
    chart_info=None, pdf_text="",
):
    """Build an isolated report prompt whose user message contains data only."""
    chart_items = []
    if isinstance(chart_info, dict):
        if chart_info.get("chart_path"):
            chart_items.append(chart_info)
        chart_items.extend(
            item for item in chart_info.get("charts", []) or []
            if isinstance(item, dict)
        )
        chart_items.extend(
            chart_info[key]
            for key in sorted(key for key in chart_info if re.fullmatch(r"chart\d+", key))
            if isinstance(chart_info.get(key), dict)
        )

    charts = []
    for index, item in enumerate(chart_items, 1):
        chart = {
            "asset_name": f"chart_{index}.png",
            "title": item.get("title", f"图表{index}"),
            "x_label": item.get("x_label", ""),
            "y_label": item.get("y_label", ""),
        }
        if isinstance(item.get("fit_result"), dict):
            chart["fit_result"] = item["fit_result"]
        charts.append(chart)

    report_data = {
        "experiment_name": experiment_name,
        "user_input": user_data or None,
        "calculation_results": calc_results or None,
        "abnormal_detection_report": abnormal_report or None,
        "charts": charts,
    }
    source_text = (pdf_text or "").strip()[:3000] or "未提供实验指导书内容"
    source_text = _escape_report_prompt_boundaries(source_text)
    data_text = json.dumps(report_data, ensure_ascii=False, indent=2, default=str)
    data_text = _escape_report_prompt_boundaries(data_text)
    return (
        "<source>\n"
        f"{source_text}\n"
        "</source>\n\n"
        "<data>\n"
        f"{data_text}\n"
        "</data>"
    )


# AI助教问答统一由 online_rag 提供。


# ==============================================
# 错误处理
# ==============================================

@app.errorhandler(404)
def error_404(e):
    return render_template("404.html"), 404


# ==============================================
# 启动
# ==============================================

# 在模块导入时即注册所有实验插件。
# 生产环境使用 `gunicorn main:app` 直接 import main，不会执行下面的 __main__ 分支；
# 若只在 __main__ 里注册，PluginRegistry 始终为空，首页会显示“暂无可用实验模块”。
register_all_plugins()

if __name__ == '__main__':
    # 预创建非RAG功能共用的LLM客户端
    _create_llm_client()

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

    port = None
    import socket
    for p in range(5002, 5020):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", p))
                port = p
                break
        except OSError:
            continue

    if port is None:
        print("错误: 5002～5019 端口均已被占用")
        raise SystemExit(1)

    print(f"\n{'=' * 50}")
    print(f"  AI二级物理实验助教系统 已启动")
    print(f"  打开浏览器访问: http://localhost:{port}")
    print(f"{'=' * 50}\n")

    app.run(host='0.0.0.0', port=port, debug=False)
