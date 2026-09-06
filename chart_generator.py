"""
智能图表生成模块
================
根据实验数据自动生成合适的图表。

核心流程：
1. AI 分析实验数据关系，判断应该画什么图（如 h-t²、U-I 等）
2. 根据 AI 建议的配置生成图表
3. 支持多种拟合模型：线性、二次、指数、幂函数、对数、反比
4. auto 模式自动尝试所有模型，选 R² 最高的

支持：
- 散点图 + 多种拟合线
- 数据变换（x²、√x、1/x 等）
- 跨列运算（如 nT÷n 得到 T，再平方得 T²）
- 自定义坐标轴标签和标题
- 中文标签支持
"""

import os
import re
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ──────────────────────────────────────────────
# 全局配置
# ──────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 尝试加载中文字体
_CN_FONTS = [f.name for f in fm.fontManager.ttflist
             if any(kw in f.name for kw in ["SimHei", "Microsoft YaHei",
                                            "WenQuanYi", "Noto Sans CJK",
                                            "Source Han Sans"])]
_CN_FONT = _CN_FONTS[0] if _CN_FONTS else "sans-serif"

# 图表样式
COLORS = ["#4472C4", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
          "#1ABC9C", "#E67E22", "#3498DB"]
STYLES = ["o", "s", "^", "D", "v", "p", "h", "*"]


def _html_to_plain(text):
    """将含 HTML 标签的物理量文本转为纯文本（用于 matplotlib 坐标轴标签）"""
    if not text:
        return text
    # 下标字符映射
    _sub_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
                'a': 'ₐ', 'e': 'ₑ', 'i': 'ᵢ', 'o': 'ₒ', 'u': 'ᵤ',
                'x': 'ₓ', '+': '₊', '-': '₋'}
    _sup_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                '+': '⁺', '-': '⁻'}

    def _to_sub(m):
        inner = m.group(1)
        return ''.join(_sub_map.get(c, c) for c in inner)

    def _to_sup(m):
        inner = m.group(1)
        return ''.join(_sup_map.get(c, c) for c in inner)

    text = re.sub(r'<sub>(.*?)</sub>', _to_sub, text)
    text = re.sub(r'<sup>(.*?)</sup>', _to_sup, text)
    text = re.sub(r'<[^>]+>', '', text)  # 移除剩余标签
    return text


def _setup_chinese():
    """配置 matplotlib 中文支持"""
    plt.rcParams["font.family"] = _CN_FONT
    plt.rcParams["axes.unicode_minus"] = False


def _calc_r2(y_arr, y_pred):
    """计算决定系数 R²"""
    ss_res = np.sum((y_arr - y_pred) ** 2)
    ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot != 0 else 0


def _finite_float(value):
    """递归把非有限浮点数（NaN/±Infinity）替换为 None。

    Python 的 json.dumps 会把 NaN/±Infinity 直接序列化成裸的
    ``NaN``/``-Infinity`` 字面量，这不是合法 JSON，浏览器
    JSON.parse 会报 “No number after minus sign in JSON” 之类错误。
    该函数作为最后一道防线，保证返回给前端的结构不含非有限数。
    """
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _finite_float(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite_float(item) for item in value]
    return value


def _fmt_coef(value):
    """拟合系数显示：常规量级保留 4 位小数；过小（<1e-3）或过大（≥1e5）时
    转科学计数法，避免有效系数被显示成 0.0000。"""
    value = _finite_float(value)
    if value is None or not np.isfinite(value):
        return "0.0000"
    magnitude = abs(value)
    if 0 < magnitude < 1e-3 or magnitude >= 1e5:
        return f"{value:.4e}"
    return f"{value:.4f}"


def _linear_fit(x, y):
    """线性拟合 y = ax + b，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    A = np.vstack([x_arr, np.ones_like(x_arr)]).T
    a, b = np.linalg.lstsq(A, y_arr, rcond=None)[0]
    y_pred = a * x_arr + b
    r2 = _calc_r2(y_arr, y_pred)
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    y_line = a * x_line + b
    return a, b, r2, x_line, y_line


def _quadratic_fit(x, y):
    """二次拟合 y = ax² + bx + c，返回 (a, b, c, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    A = np.vstack([x_arr**2, x_arr, np.ones_like(x_arr)]).T
    coeffs = np.linalg.lstsq(A, y_arr, rcond=None)[0]
    a, b, c = coeffs
    y_pred = a * x_arr**2 + b * x_arr + c
    r2 = _calc_r2(y_arr, y_pred)
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    y_line = a * x_line**2 + b * x_line + c
    return a, b, c, r2, x_line, y_line


def _exponential_fit(x, y):
    """指数拟合 y = a·e^(bx)，对 y 取 ln 后线性拟合，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    # 仅保留 y > 0 的点
    mask = y_arr > 0
    if np.sum(mask) < 2:
        return None
    x_m, y_m = x_arr[mask], y_arr[mask]
    ln_y = np.log(y_m)
    A = np.vstack([x_m, np.ones_like(x_m)]).T
    b, ln_a = np.linalg.lstsq(A, ln_y, rcond=None)[0]
    a = np.exp(ln_a)
    y_pred = a * np.exp(b * x_arr)
    r2 = _calc_r2(y_arr, y_pred)
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    y_line = a * np.exp(b * x_line)
    return a, b, r2, x_line, y_line


def _power_fit(x, y):
    """幂函数拟合 y = a·x^b，对两边取 ln 后线性拟合，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    mask = (x_arr > 0) & (y_arr > 0)
    if np.sum(mask) < 2:
        return None
    x_m, y_m = x_arr[mask], y_arr[mask]
    ln_x, ln_y = np.log(x_m), np.log(y_m)
    A = np.vstack([ln_x, np.ones_like(ln_x)]).T
    b, ln_a = np.linalg.lstsq(A, ln_y, rcond=None)[0]
    a = np.exp(ln_a)
    y_pred = a * np.power(x_arr, b)
    r2 = _calc_r2(y_arr, y_pred)
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    y_line = a * np.power(x_line, b)
    return a, b, r2, x_line, y_line


def _log_fit(x, y):
    """对数拟合 y = a·ln(x) + b，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    mask = x_arr > 0
    if np.sum(mask) < 2:
        return None
    x_m, y_m = x_arr[mask], y_arr[mask]
    ln_x = np.log(x_m)
    A = np.vstack([ln_x, np.ones_like(ln_x)]).T
    a, b = np.linalg.lstsq(A, y_m, rcond=None)[0]
    # R² 只在模型有定义的区间（x > 0）上计算；
    # 若对 x = 0 求 ln(0) = -inf，会把 R² 污染成 -Infinity
    y_pred = a * ln_x + b
    r2 = _calc_r2(y_m, y_pred)
    x_line = np.linspace(x_m.min(), x_m.max(), 200)
    y_line = a * np.log(x_line) + b
    return a, b, r2, x_line, y_line


def _inverse_fit(x, y):
    """反比拟合 y = a/x + b，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    mask = x_arr != 0
    if np.sum(mask) < 2:
        return None
    x_m, y_m = x_arr[mask], y_arr[mask]
    inv_x = 1.0 / x_m
    A = np.vstack([inv_x, np.ones_like(inv_x)]).T
    a, b = np.linalg.lstsq(A, y_m, rcond=None)[0]
    # R² 只在模型有定义的区间（x ≠ 0）上计算；
    # 若对 x = 0 做除法会产生 inf，把 R² 污染成 -Infinity
    y_pred = a * inv_x + b
    r2 = _calc_r2(y_m, y_pred)
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    # 避免除以 0
    x_line = x_line[x_line != 0]
    y_line = a / x_line + b
    return a, b, r2, x_line, y_line


def _auto_best_fit(x, y):
    """自动尝试所有拟合模型，返回 R² 最高的结果

    返回: dict {
        "type": str,          # 最优模型类型
        "label": str,         # 模型中文名
        "equation": str,      # 拟合方程
        "r2": float,          # R²
        "x_line": ndarray,    # 绘图用 x
        "y_line": ndarray,    # 绘图用 y
        "params": dict,       # 模型参数
    }
    """
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    n = len(x_arr)
    if n < 2:
        return None

    candidates = []

    # 1. 线性 y = ax + b  (k=2)
    try:
        a, b, r2, xl, yl = _linear_fit(x_arr, y_arr)
        candidates.append({
            "type": "linear", "label": "线性", "n_params": 2,
            "equation": f"y = {_fmt_coef(a)}x + {_fmt_coef(b)}",
            "r2": r2, "x_line": xl, "y_line": yl,
            "params": {"a": a, "b": b}
        })
    except Exception:
        pass

    # 2. 二次 y = ax² + bx + c  (k=3)
    if n >= 4:
        try:
            a, b, c, r2, xl, yl = _quadratic_fit(x_arr, y_arr)
            candidates.append({
                "type": "quadratic", "label": "二次", "n_params": 3,
                "equation": f"y = {_fmt_coef(a)}x² + {_fmt_coef(b)}x + {_fmt_coef(c)}",
                "r2": r2, "x_line": xl, "y_line": yl,
                "params": {"a": a, "b": b, "c": c}
            })
        except Exception:
            pass

    # 3. 指数 y = a·e^(bx)  (k=2)
    try:
        result = _exponential_fit(x_arr, y_arr)
        if result is not None:
            a, b, r2, xl, yl = result
            candidates.append({
                "type": "exponential", "label": "指数", "n_params": 2,
                "equation": f"y = {_fmt_coef(a)}·e^({_fmt_coef(b)}x)",
                "r2": r2, "x_line": xl, "y_line": yl,
                "params": {"a": a, "b": b}
            })
    except Exception:
        pass

    # 4. 幂函数 y = a·x^b  (k=2)
    try:
        result = _power_fit(x_arr, y_arr)
        if result is not None:
            a, b, r2, xl, yl = result
            candidates.append({
                "type": "power", "label": "幂函数", "n_params": 2,
                "equation": f"y = {_fmt_coef(a)}·x^{_fmt_coef(b)}",
                "r2": r2, "x_line": xl, "y_line": yl,
                "params": {"a": a, "b": b}
            })
    except Exception:
        pass

    # 5. 对数 y = a·ln(x) + b  (k=2)
    try:
        result = _log_fit(x_arr, y_arr)
        if result is not None:
            a, b, r2, xl, yl = result
            candidates.append({
                "type": "log", "label": "对数", "n_params": 2,
                "equation": f"y = {_fmt_coef(a)}·ln(x) + {_fmt_coef(b)}",
                "r2": r2, "x_line": xl, "y_line": yl,
                "params": {"a": a, "b": b}
            })
    except Exception:
        pass

    # 6. 反比 y = a/x + b  (k=2)
    try:
        result = _inverse_fit(x_arr, y_arr)
        if result is not None:
            a, b, r2, xl, yl = result
            candidates.append({
                "type": "inverse", "label": "反比", "n_params": 2,
                "equation": f"y = {_fmt_coef(a)}/x + {_fmt_coef(b)}",
                "r2": r2, "x_line": xl, "y_line": yl,
                "params": {"a": a, "b": b}
            })
    except Exception:
        pass

    if not candidates:
        return None

    # 用调整 R² 选择最优模型（惩罚参数更多的模型）
    # Adj_R² = 1 - (1-R²)*(n-1)/(n-k-1)
    for c in candidates:
        k = c["n_params"]
        if n > k + 1:
            c["adj_r2"] = 1 - (1 - c["r2"]) * (n - 1) / (n - k - 1)
        else:
            c["adj_r2"] = c["r2"]  # 数据点不足时退化为普通 R²

    best = max(candidates, key=lambda c: c["adj_r2"])
    best["all_candidates"] = [
        {"type": c["type"], "label": c["label"], "r2": round(c["r2"], 6),
         "adj_r2": round(c["adj_r2"], 6), "equation": c["equation"]}
        for c in sorted(candidates, key=lambda c: c["adj_r2"], reverse=True)
    ]
    return best


# ──────────────────────────────────────────────
# AI 智能图表配置建议
# ──────────────────────────────────────────────
CHART_AI_PROMPT = """你是一位大学物理实验数据分析专家。

用户会提供一个实验的名称和数据表格的列名及示例数据。
你需要判断：
1. 哪两列数据之间存在物理关系，应该作为图表的 X 和 Y 轴
2. 这两个变量之间是什么函数关系（线性、二次、指数、幂函数、对数、反比等）
3. 为了验证这个关系，应该对数据做什么变换使其变成线性关系（如果适用）
4. 变换后的坐标轴标签应该怎么写
5. 推荐哪种拟合模型

支持的拟合模型：
- linear: 线性 y = ax + b
- quadratic: 二次 y = ax² + bx + c
- exponential: 指数 y = a·e^(bx)
- power: 幂函数 y = a·x^b
- log: 对数 y = a·ln(x) + b
- inverse: 反比 y = a/x + b
- auto: 自动选择（系统会尝试所有模型，选 R² 最高的）

例如：
- 自由落体测重力加速度：h 与 t 是二次关系 h=½gt²，建议 fit="quadratic"，或画 h 与 t² 的图并 fit="linear"
- 单摆测重力加速度：T² 与 L 是线性关系，fit="linear"
- 光电效应：遏止电压 U₀ 与频率 ν 是线性关系，fit="linear"
- RC 放电曲线：电压随时间指数衰减，fit="exponential"
- 光强与距离：光强与距离平方成反比，fit="inverse"

请严格按照以下 JSON 格式输出，不要输出其他内容：
{
    "x_col": "X轴列名（必须与提供的列名完全一致）",
    "y_col": "Y轴列名（必须与提供的列名完全一致）",
    "x_transform": "none 或 square 或 sqrt 或 reciprocal",
    "y_transform": "none 或 square 或 sqrt 或 reciprocal",
    "x_divide_by": "可选，如果需要先除以另一列再变换，填该列名",
    "y_divide_by": "可选，同上",
    "x_label": "变换后X轴的物理标签（含单位）",
    "y_label": "变换后Y轴的物理标签（含单位）",
    "title": "图表标题",
    "fit": "linear 或 quadratic 或 exponential 或 power 或 log 或 inverse 或 auto",
    "reason": "简要说明为什么这样选择（一句话）"
}

注意：
- 如果原始数据是二次关系且你想直接拟合曲线，用 fit="quadratic"
- 如果你想通过变量变换使其线性化，设置对应的 transform 并用 fit="linear"
- 如果不确定哪种模型最合适，用 fit="auto"，系统会自动比较所有模型的 R² 并选最优
- x_transform/y_transform 的含义：square 表示对原数据取平方，sqrt 表示取平方根，reciprocal 表示取倒数，none 表示不变换
- x_divide_by/y_divide_by：当某列数据需要先除以另一列才有物理意义时使用
- x_label/y_label 必须反映变换后的物理量，例如如果 X 轴是 t²，标签应写't²/s²'而不是't/s'"""


def ai_suggest_chart_config(experiment_name, columns, data_rows, llm_client=None, model_name=None):
    """用 AI 分析实验数据，建议最佳图表配置

    参数:
        experiment_name: str, 实验名称
        columns: list[str], 列名
        data_rows: list[list[str]], 数据行
        llm_client: OpenAI 兼容客户端
        model_name: 模型名

    返回:
        dict: 图表配置，格式同 chart_config
    """
    if llm_client is None:
        return auto_detect_chart_config(columns, data_rows)

    # 构建用户消息
    sample_data = "\n".join(
        " | ".join(str(v) for v in row) for row in data_rows[:6]
    )
    user_msg = f"""实验名称：{experiment_name}

数据列名：{json.dumps(columns, ensure_ascii=False)}

前几行示例数据：
{sample_data}

请分析这些数据，给出最佳的图表配置。"""

    try:
        response = llm_client.chat.completions.create(
            model=model_name or "glm-5.2-107",
            messages=[
                {"role": "system", "content": CHART_AI_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.1,
            max_tokens=2048,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        content = response.choices[0].message.content.strip()

        # 提取 JSON（可能被包裹在 ```json ... ``` 中）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        config = json.loads(content)

        # 验证列名存在
        if config.get("x_col") not in columns:
            config["x_col"] = columns[0]
        if config.get("y_col") not in columns:
            config["y_col"] = columns[1] if len(columns) > 1 else columns[0]

        # 规范化 transform 值
        valid_transforms = {"none", "square", "sqrt", "reciprocal"}
        xt = config.get("x_transform", "none").lower()
        yt = config.get("y_transform", "none").lower()
        config["x_transform"] = xt if xt in valid_transforms else "none"
        config["y_transform"] = yt if yt in valid_transforms else "none"
        if config["x_transform"] == "none":
            config.pop("x_transform", None)
        if config["y_transform"] == "none":
            config.pop("y_transform", None)

        # 验证 divide_by 列名存在
        for key in ["x_divide_by", "y_divide_by"]:
            val = config.get(key)
            if val and val not in columns:
                config.pop(key, None)

        config["ai_reason"] = config.get("reason", "")
        return config

    except Exception as e:
        print(f"[图表AI] 分析失败，回退到规则引擎: {e}")
        return auto_detect_chart_config(columns, data_rows)


def _generate_multi_series_chart(columns, data_rows, chart_config, x_idx, save_name):
    """多 y 列绘图：同一 x 轴上绘制多条曲线（如红/绿/蓝三基色 LED 伏安特性）。

    chart_config 额外支持:
        y_cols:          list[str|int]，各曲线对应的 y 列名或索引
        series_labels:   list[str]，各曲线图例名（缺省用列名）
        series_colors:   list[str]，各曲线颜色（缺省按 COLORS 循环）
        connect_points:  bool，按 x 排序把每列测量点连成折线

    多列模式只画散点/折线，不做回归拟合（各曲线的拟合在实验报告图中进行）。
    """
    y_cols = chart_config.get("y_cols")
    series_labels = chart_config.get("series_labels") or []
    series_colors = chart_config.get("series_colors") or []

    series = []
    for order, yc in enumerate(y_cols):
        if isinstance(yc, str):
            y_idx = columns.index(yc) if yc in columns else None
        else:
            y_idx = yc
        if y_idx is None or y_idx < 0 or y_idx >= len(columns):
            continue
        label = series_labels[order] if order < len(series_labels) else columns[y_idx]
        color = series_colors[order] if order < len(series_colors) else COLORS[order % len(COLORS)]
        series.append((y_idx, _html_to_plain(label), color, order))
    if not series:
        return {"path": None, "error": "未找到有效的 y 列（y_cols 需为列名或索引列表）"}

    x_transform = chart_config.get("x_transform")
    y_transform = chart_config.get("y_transform")
    x_label = chart_config.get("x_label", columns[x_idx] if x_idx < len(columns) else "x")
    y_label = chart_config.get("y_label", "y")
    x_label_clean = _html_to_plain(x_label)
    y_label_clean = _html_to_plain(y_label)
    title = chart_config.get("title", f"{y_label_clean} vs {x_label_clean}")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    plotted = 0
    for y_idx, label, color, order in series:
        x_data, y_data = [], []
        for row in data_rows:
            try:
                if x_idx >= len(row) or y_idx >= len(row):
                    continue
                xv = str(row[x_idx]).strip()
                yv = str(row[y_idx]).strip()
                if not xv or not yv:
                    continue
                x_data.append(float(xv))
                y_data.append(float(yv))
            except (ValueError, IndexError):
                continue
        if len(x_data) < 2:
            continue
        x_arr = np.array(x_data, dtype=float)
        y_arr = np.array(y_data, dtype=float)
        # 与单列模式一致的数据变换
        if x_transform == "square":
            x_arr = x_arr ** 2
        elif x_transform == "sqrt":
            x_arr = np.sqrt(np.abs(x_arr))
        elif x_transform == "reciprocal":
            x_arr = 1.0 / x_arr
        if y_transform == "square":
            y_arr = y_arr ** 2
        elif y_transform == "sqrt":
            y_arr = np.sqrt(np.abs(y_arr))
        elif y_transform == "reciprocal":
            y_arr = 1.0 / y_arr
        marker = STYLES[order % len(STYLES)]
        ax.scatter(x_arr, y_arr, color=color, marker=marker, s=46, label=label,
                   zorder=5, edgecolors="white", linewidth=0.5)
        if chart_config.get("connect_points"):
            order_idx = np.argsort(x_arr)
            ax.plot(x_arr[order_idx], y_arr[order_idx], color=color,
                    linewidth=1.2, linestyle="-", alpha=0.65, zorder=4)
        plotted += 1

    if plotted == 0:
        plt.close(fig)
        return {"path": None, "error": "有效数据点不足（至少需要2个）"}

    ax.set_xlabel(x_label_clean, fontsize=12)
    ax.set_ylabel(y_label_clean, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    file_path = os.path.join(OUTPUT_DIR, save_name)
    fig.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return _finite_float({
        "path": file_path,
        "fit_result": None,
        "x_data": [],
        "y_data": [],
        "x_label": x_label,
        "y_label": y_label,
    })


def generate_chart(columns, data_rows, chart_config=None, save_name="chart.png"):
    """通用图表生成函数

    参数:
        columns: list[str], 列名列表
        data_rows: list[list[str]], 数据行
        chart_config: dict, 图表配置，格式:
            {
                "x_col": str or int,      # x 轴列名或索引
                "y_col": str or int,      # y 轴列名或索引
                "x_label": str,           # x 轴标签（可选，默认用列名）
                "y_label": str,           # y 轴标签（可选，默认用列名）
                "title": str,             # 图表标题
                "fit": "linear" | None,   # 是否做线性拟合
                "x_transform": str,       # x 轴数据变换，如 "square"（x→x²）
                "y_transform": str,       # y 轴数据变换
            }
        save_name: str, 保存文件名

    返回:
        dict: {
            "path": str,       # 图表文件路径
            "fit_result": dict, # 拟合结果（如有）
            "x_data": list,
            "y_data": list,
        }
    """
    _setup_chinese()

    if chart_config is None:
        chart_config = auto_detect_chart_config(columns, data_rows)

    # 解析列
    x_col = chart_config.get("x_col", 0)
    y_col = chart_config.get("y_col", 1)

    if isinstance(x_col, str):
        x_idx = columns.index(x_col) if x_col in columns else 0
    else:
        x_idx = x_col

    # 多 y 列模式：同一 x 轴绘制多条曲线（如三基色 LED 伏安特性）
    y_cols = chart_config.get("y_cols")
    if isinstance(y_cols, (list, tuple)) and len(y_cols) > 0:
        return _generate_multi_series_chart(columns, data_rows, chart_config, x_idx, save_name)

    if isinstance(y_col, str):
        y_idx = columns.index(y_col) if y_col in columns else 1
    else:
        y_idx = y_col

    # 提取数据（支持 divide_by 跨列运算）
    x_data = []
    y_data = []
    x_divide_col = chart_config.get("x_divide_by")
    y_divide_col = chart_config.get("y_divide_by")

    # 获取 divide_by 列的索引
    x_div_idx = None
    y_div_idx = None
    if x_divide_col:
        x_div_idx = columns.index(x_divide_col) if x_divide_col in columns else None
    if y_divide_col:
        y_div_idx = columns.index(y_divide_col) if y_divide_col in columns else None

    # 预计算 divide_by 列的默认值（取第一个非空值，用于填充空单元格）
    x_div_default = None
    y_div_default = None
    if x_div_idx is not None:
        for row in data_rows:
            if x_div_idx < len(row) and row[x_div_idx].strip():
                try:
                    x_div_default = float(row[x_div_idx].strip())
                    if x_div_default != 0:
                        break
                except (ValueError, ZeroDivisionError):
                    pass
    if y_div_idx is not None:
        for row in data_rows:
            if y_div_idx < len(row) and row[y_div_idx].strip():
                try:
                    y_div_default = float(row[y_div_idx].strip())
                    if y_div_default != 0:
                        break
                except (ValueError, ZeroDivisionError):
                    pass

    for row in data_rows:
        try:
            xv = row[x_idx].strip() if x_idx < len(row) else ""
            yv = row[y_idx].strip() if y_idx < len(row) else ""
            if xv and yv:
                x_val = float(xv)
                y_val = float(yv)
                # 跨列除法：先除以另一列（空值时使用默认值）
                if x_div_idx is not None and x_div_idx < len(row):
                    div_str = row[x_div_idx].strip() if x_div_idx < len(row) else ""
                    div_val = float(div_str) if div_str else x_div_default
                    if div_val and div_val != 0:
                        x_val = x_val / div_val
                if y_div_idx is not None and y_div_idx < len(row):
                    div_str = row[y_div_idx].strip() if y_div_idx < len(row) else ""
                    div_val = float(div_str) if div_str else y_div_default
                    if div_val and div_val != 0:
                        y_val = y_val / div_val
                x_data.append(x_val)
                y_data.append(y_val)
        except (ValueError, IndexError, ZeroDivisionError):
            continue

    if len(x_data) < 2:
        return {"path": None, "error": "有效数据点不足（至少需要2个）"}

    # 数据变换（在 divide_by 之后应用）
    x_transform = chart_config.get("x_transform")
    y_transform = chart_config.get("y_transform")
    x_arr = np.array(x_data)
    y_arr = np.array(y_data)

    if x_transform == "square":
        x_arr = x_arr ** 2
    elif x_transform == "sqrt":
        x_arr = np.sqrt(np.abs(x_arr))
    elif x_transform == "reciprocal":
        x_arr = 1.0 / x_arr

    if y_transform == "square":
        y_arr = y_arr ** 2
    elif y_transform == "sqrt":
        y_arr = np.sqrt(np.abs(y_arr))
    elif y_transform == "reciprocal":
        y_arr = 1.0 / y_arr

    x_label = chart_config.get("x_label", columns[x_idx] if x_idx < len(columns) else "x")
    y_label = chart_config.get("y_label", columns[y_idx] if y_idx < len(columns) else "y")
    # 清理 HTML 标签用于 matplotlib 显示
    x_label_clean = _html_to_plain(x_label)
    y_label_clean = _html_to_plain(y_label)
    title = chart_config.get("title", f"{y_label_clean} vs {x_label_clean}")
    fit_type = chart_config.get("fit")

    # 绘图
    fig, ax = plt.subplots(figsize=(8, 5.5))

    ax.scatter(x_arr, y_arr, color=COLORS[0], marker="o", s=50,
               label="测量数据", zorder=5, edgecolors="white", linewidth=0.5)

    fit_result = None
    if fit_type == "auto" and len(x_arr) >= 3:
        # 自动选择最优拟合模型
        best = _auto_best_fit(x_arr, y_arr)
        if best:
            ax.plot(best["x_line"], best["y_line"], color=COLORS[1], linewidth=2,
                    label=f"{best['label']}拟合: {best['equation']}\n$R^2$ = {best['r2']:.4f}")
            fit_result = {
                "type": best["type"],
                "label": best["label"],
                "equation": best["equation"],
                "R2": round(best["r2"], 6),
                "params": best["params"],
                "all_candidates": best.get("all_candidates", [])
            }
    elif fit_type == "quadratic" and len(x_arr) >= 3:
        a, b, c, r2, x_line, y_line = _quadratic_fit(x_arr, y_arr)
        ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                label=f"二次拟合: y = {_fmt_coef(a)}x² + {_fmt_coef(b)}x + {_fmt_coef(c)}\n$R^2$ = {r2:.4f}")
        fit_result = {
            "type": "quadratic", "label": "二次",
            "equation": f"y = {_fmt_coef(a)}x² + {_fmt_coef(b)}x + {_fmt_coef(c)}",
            "R2": round(float(r2), 6),
            "params": {"a": round(float(a), 6), "b": round(float(b), 6), "c": round(float(c), 6)}
        }
    elif fit_type == "exponential" and len(x_arr) >= 2:
        result = _exponential_fit(x_arr, y_arr)
        if result:
            a, b, r2, x_line, y_line = result
            ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                    label=f"指数拟合: y = {_fmt_coef(a)}·e^({_fmt_coef(b)}x)\n$R^2$ = {r2:.4f}")
            fit_result = {
                "type": "exponential", "label": "指数",
                "equation": f"y = {_fmt_coef(a)}·e^({_fmt_coef(b)}x)",
                "R2": round(float(r2), 6),
                "params": {"a": round(float(a), 6), "b": round(float(b), 6)}
            }
    elif fit_type == "power" and len(x_arr) >= 2:
        result = _power_fit(x_arr, y_arr)
        if result:
            a, b, r2, x_line, y_line = result
            ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                    label=f"幂函数拟合: y = {_fmt_coef(a)}·x^{_fmt_coef(b)}\n$R^2$ = {r2:.4f}")
            fit_result = {
                "type": "power", "label": "幂函数",
                "equation": f"y = {_fmt_coef(a)}·x^{_fmt_coef(b)}",
                "R2": round(float(r2), 6),
                "params": {"a": round(float(a), 6), "b": round(float(b), 6)}
            }
    elif fit_type == "log" and len(x_arr) >= 2:
        result = _log_fit(x_arr, y_arr)
        if result:
            a, b, r2, x_line, y_line = result
            ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                    label=f"对数拟合: y = {_fmt_coef(a)}·ln(x) + {_fmt_coef(b)}\n$R^2$ = {r2:.4f}")
            fit_result = {
                "type": "log", "label": "对数",
                "equation": f"y = {_fmt_coef(a)}·ln(x) + {_fmt_coef(b)}",
                "R2": round(float(r2), 6),
                "params": {"a": round(float(a), 6), "b": round(float(b), 6)}
            }
    elif fit_type == "inverse" and len(x_arr) >= 2:
        result = _inverse_fit(x_arr, y_arr)
        if result:
            a, b, r2, x_line, y_line = result
            ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                    label=f"反比拟合: y = {_fmt_coef(a)}/x + {_fmt_coef(b)}\n$R^2$ = {r2:.4f}")
            fit_result = {
                "type": "inverse", "label": "反比",
                "equation": f"y = {_fmt_coef(a)}/x + {_fmt_coef(b)}",
                "R2": round(float(r2), 6),
                "params": {"a": round(float(a), 6), "b": round(float(b), 6)}
            }
    elif fit_type == "linear" and len(x_arr) >= 2:
        a, b, r2, x_line, y_line = _linear_fit(x_arr, y_arr)
        ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                label=f"线性拟合: y = {_fmt_coef(a)}x + {_fmt_coef(b)}\n$R^2$ = {r2:.4f}")
        fit_result = {
            "type": "linear", "label": "线性",
            "equation": f"y = {_fmt_coef(a)}x + {_fmt_coef(b)}",
            "R2": round(float(r2), 6),
            "params": {"slope": round(float(a), 6), "intercept": round(float(b), 6)}
        }
    elif fit_type is None:
        # 不做回归拟合，只画散点；可选把测量点按 x 排序连成折线
        # （如伏安特性/激发曲线这类没有解析模型的物理曲线）
        if chart_config.get("connect_points"):
            order = np.argsort(x_arr)
            ax.plot(x_arr[order], y_arr[order], color=COLORS[0],
                    linewidth=1.2, linestyle="-", alpha=0.65, zorder=4)
    else:
        # 默认回退到线性拟合
        a, b, r2, x_line, y_line = _linear_fit(x_arr, y_arr)
        ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                label=f"线性拟合: y = {_fmt_coef(a)}x + {_fmt_coef(b)}\n$R^2$ = {r2:.4f}")
        fit_result = {
            "type": "linear", "label": "线性",
            "equation": f"y = {_fmt_coef(a)}x + {_fmt_coef(b)}",
            "R2": round(float(r2), 6),
            "params": {"slope": round(float(a), 6), "intercept": round(float(b), 6)}
        }

    ax.set_xlabel(x_label_clean, fontsize=12)
    ax.set_ylabel(y_label_clean, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    file_path = os.path.join(OUTPUT_DIR, save_name)
    fig.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 最后一道防线：拟合结果里不允许出现 NaN/±Infinity，
    # 否则 jsonify 会输出非法 JSON，浏览器端 JSON.parse 直接报错。
    result = {
        "path": file_path,
        "fit_result": fit_result,
        "x_data": x_arr.tolist(),
        "y_data": y_arr.tolist(),
        "x_label": x_label,
        "y_label": y_label,
    }
    return _finite_float(result)


def generate_multi_chart(columns, data_rows, chart_configs, save_prefix="chart"):
    """生成多张图表

    参数:
        chart_configs: list[dict], 每张图的配置

    返回:
        list[dict], 每张图的结果
    """
    results = []
    for i, config in enumerate(chart_configs):
        save_name = f"{save_prefix}_{i}.png"
        result = generate_chart(columns, data_rows, config, save_name)
        result["config"] = config
        results.append(result)
    return results


def auto_detect_chart_config(columns, data_rows):
    """回退方案：根据列名和数据自动推断图表配置（规则引擎）

    当 AI 不可用时使用。
    """
    cols_lower = [c.lower() for c in columns]
    n_cols = len(columns)

    # 检测哪些列是数值型且有变化
    numeric_cols = []
    for i, col in enumerate(columns):
        vals = []
        for row in data_rows:
            if i < len(row):
                try:
                    vals.append(float(row[i]))
                except (ValueError, TypeError):
                    pass
        if len(vals) >= 2:
            # 检查是否有变化（不全是同一个值）
            if max(vals) != min(vals):
                numeric_cols.append(i)

    if len(numeric_cols) < 2:
        return None

    # 默认取前两个有变化的数值列
    x_idx = numeric_cols[0]
    y_idx = numeric_cols[1]

    config = {
        "x_col": x_idx,
        "y_col": y_idx,
        "fit": "auto",  # 自动选择最优拟合模型
    }

    # 根据列名关键词做特殊处理
    col_text = " ".join(columns).lower()

    # 单摆实验：l vs T²
    if any("t" in c.lower() and ("t/s" in c.lower() or "周期" in c.lower()) for c in columns):
        for i, c in enumerate(columns):
            cl = c.lower()
            if "l/cm" in cl or "l/m" in cl or "摆长" in c:
                x_idx = i
            if ("t/s" in cl or "周期" in c) and "nt" not in cl:
                y_idx = i
        # 如果找到 nT 列，需要除以 n 得到 T
        for i, c in enumerate(columns):
            if "nt" in c.lower() or "nt/s" in c.lower():
                y_idx = i
                break
        config["x_col"] = x_idx
        config["y_col"] = y_idx

    # 伏安特性：U vs I
    elif any("u/v" in c.lower() or "电压" in c.lower() for c in columns) and \
         any("i/ma" in c.lower() or "电流" in c.lower() for c in columns):
        for i, c in enumerate(columns):
            cl = c.lower()
            if "i/ma" in cl or "电流" in c:
                x_idx = i
            if "u/v" in cl or "电压" in c:
                y_idx = i
        config["x_col"] = x_idx
        config["y_col"] = y_idx

    # 光电效应：ν vs U0
    elif any("ν" in c or "频率" in c for c in columns):
        for i, c in enumerate(columns):
            if "ν" in c or "频率" in c:
                x_idx = i
            if "u0" in c.lower() or "电压" in c.lower():
                y_idx = i
        config["x_col"] = x_idx
        config["y_col"] = y_idx

    # 声速：L vs 其他
    elif any("l/cm" in c.lower() and "声" in col_text for c in columns):
        config["fit"] = None  # 声速实验可能不是线性

    return config
