"""
智能图表生成模块
================
根据实验数据自动生成合适的图表。

核心流程：
1. AI 分析实验数据关系，判断应该画什么图（如 h-t²、U-I 等）
2. 根据 AI 建议的配置生成图表
3. 支持线性拟合、二次函数拟合等

支持：
- 散点图 + 线性拟合线
- 数据变换（x²、√x、1/x 等）
- 跨列运算（如 nT÷n 得到 T，再平方得 T²）
- 自定义坐标轴标签和标题
- 中文标签支持
"""

import os
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


def _setup_chinese():
    """配置 matplotlib 中文支持"""
    plt.rcParams["font.family"] = _CN_FONT
    plt.rcParams["axes.unicode_minus"] = False


def _linear_fit(x, y):
    """线性拟合 y = ax + b，返回 (a, b, r2, x_line, y_line)"""
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    A = np.vstack([x_arr, np.ones_like(x_arr)]).T
    a, b = np.linalg.lstsq(A, y_arr, rcond=None)[0]
    y_pred = a * x_arr + b
    ss_res = np.sum((y_arr - y_pred) ** 2)
    ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    y_line = a * x_line + b
    return a, b, r2, x_line, y_line


# ──────────────────────────────────────────────
# AI 智能图表配置建议
# ──────────────────────────────────────────────
CHART_AI_PROMPT = """你是一位大学物理实验数据分析专家。

用户会提供一个实验的名称和数据表格的列名及示例数据。
你需要判断：
1. 哪两列数据之间存在物理关系，应该作为图表的 X 和 Y 轴
2. 这两个变量之间是什么关系（线性、二次函数、反比等）
3. 为了验证这个关系，应该对数据做什么变换使其变成线性关系
4. 变换后的坐标轴标签应该怎么写

例如：
- 自由落体测重力加速度：h 与 t 是二次关系 h=½gt²，应该画 h 与 t² 的图，变换后是线性关系
- 单摆测重力加速度：T² 与 L 是线性关系 T²=4π²L/g，应该画 L 与 T² 的图
- 光电效应：遏止电压 U₀ 与频率 ν 是线性关系
- 伏安特性：电流 I 与电压 U 是线性关系

请严格按照以下 JSON 格式输出，不要输出其他内容：
{
    "x_col": "X轴列名（必须与提供的列名完全一致）",
    "y_col": "Y轴列名（必须与提供的列名完全一致）",
    "x_transform": "none 或 square 或 sqrt 或 reciprocal",
    "y_transform": "none 或 square 或 sqrt 或 reciprocal",
    "x_divide_by": "可选，如果需要先除以另一列再变换，填该列名（如 nT 列需要除以 n 列得到 T）",
    "y_divide_by": "可选，同上",
    "x_label": "变换后X轴的物理标签（含单位）",
    "y_label": "变换后Y轴的物理标签（含单位）",
    "title": "图表标题",
    "fit": "linear",
    "reason": "简要说明为什么这样选择（一句话）"
}

注意：
- x_transform/y_transform 的含义：square 表示对原数据取平方，sqrt 表示取平方根，reciprocal 表示取倒数，none 表示不变换
- x_divide_by/y_divide_by：当某列数据需要先除以另一列才有物理意义时使用。例如单摆实验中 nT/s 列是50个周期总时间，需要先除以 n 列得到周期 T，再对 T 取平方得 T²
- 变换的目的是使两个变量之间的关系变成线性，从而通过线性拟合验证
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
    title = chart_config.get("title", f"{y_label} vs {x_label}")
    fit_type = chart_config.get("fit")

    # 绘图
    fig, ax = plt.subplots(figsize=(8, 5.5))

    ax.scatter(x_arr, y_arr, color=COLORS[0], marker="o", s=50,
               label="测量数据", zorder=5, edgecolors="white", linewidth=0.5)

    fit_result = None
    if fit_type == "linear" and len(x_arr) >= 2:
        a, b, r2, x_line, y_line = _linear_fit(x_arr, y_arr)
        ax.plot(x_line, y_line, color=COLORS[1], linewidth=2,
                label=f"拟合线: y = {a:.4f}x + {b:.4f}\n$R^2$ = {r2:.4f}")
        fit_result = {
            "slope": round(float(a), 6),
            "intercept": round(float(b), 6),
            "R2": round(float(r2), 6),
            "equation": f"y = {a:.4f}x + {b:.4f}"
        }

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    file_path = os.path.join(OUTPUT_DIR, save_name)
    fig.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {
        "path": file_path,
        "fit_result": fit_result,
        "x_data": x_arr.tolist(),
        "y_data": y_arr.tolist(),
        "x_label": x_label,
        "y_label": y_label,
    }


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
        "fit": "linear",
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
