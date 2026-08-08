"""
工具执行器 —— 物理实验数据处理核心
==============================
这个模块由 AI 调用，完成"计算平均值""拟合曲线""画图""生成报告"等任务。

每个函数就是一个"工具"，AI 通过 tool calling 来调用它们。
函数名即工具名，docstring 即工具描述，参数由 AI 自动解析。
"""

import numpy as np
from scipy import optimize
import matplotlib
matplotlib.use("Agg")  # 无头模式（服务器无 GUI）
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import json

# ──────────────────────────────────────────────
# 全局配置
# ──────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 尝试加载中文字体（用于图表标题）
_CN_FONTS = [f.name for f in fm.fontManager.ttflist if any(kw in f.name for kw in ["SimHei", "Microsoft YaHei", "WenQuanYi", "Noto Sans CJK", "Source Han Sans"])]
_CN_FONT = _CN_FONTS[0] if _CN_FONTS else "sans-serif"


# ==============================================
# 工具1：计算统计量（平均值、标准差、不确定度）
# ==============================================
def compute_statistics(data, label="data"):
    """
    计算平均值、标准差、不确定度。

    Parameters
    ----------
    data : list of float
        测量数据列表。
    label : str
        数据名称（仅用于输出显示）。

    Returns
    -------
    dict
        包含 mean, std, n, uncertainty 等信息的字典。
    """
    arr = np.array(data, dtype=float)
    n = len(arr)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    uncertainty = std / np.sqrt(n)  # A类不确定度
    return {
        "data_label": label,
        "n": n,
        "mean": round(mean, 6),
        "std": round(std, 6),
        "uncertainty": round(uncertainty, 6),
        "summary": f"{label}：平均值={mean:.4f}，标准差={std:.4f}，A类不确定度={uncertainty:.4f}",
    }


# ==============================================
# 工具2：线性拟合（y = a*x + b）
# ==============================================
def fit_linear(x_data, y_data, x_label="x", y_label="y"):
    """
    对数据进行线性拟合 y = a*x + b，返回拟合参数和拟合优度 R²。

    Parameters
    ----------
    x_data : list of float
    y_data : list of float
    x_label, y_label : str
        轴标签。

    Returns
    -------
    dict
        包含 a(斜率)，b(截距)，R²，拟合曲线数据点等。
    """
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)
    A = np.vstack([x, np.ones_like(x)]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]
    # 计算 R²
    y_pred = a * x + b
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
    return {
        "slope": round(a, 6),
        "intercept": round(b, 6),
        "R²": round(r2, 6),
        "x_label": x_label,
        "y_label": y_label,
        "summary": f"线性拟合 {y_label} = {a:.4f} * {x_label} + {b:.4f}，R²={r2:.4f}",
    }


# ==============================================
# 工具3：绘制数据图表（折线图 + 散点图 + 拟合线）
# ==============================================
def create_chart(x_data, y_data, x_label="x", y_label="y", title="Chart",
                 fit_type=None, extra_lines=None, save_name="chart.png"):
    """
    生成图表，保存为 PNG 文件。

    Parameters
    ----------
    x_data, y_data : list of float
    x_label, y_label : str
    title : str
    fit_type : str or None
        可选的拟合线类型："linear"（线性）或 None（不画拟合线）。
    extra_lines : list of dict, optional
        额外的线，例如 [{"x": [...], "y": [...], "label": "理论曲线", "style": "--"}]
    save_name : str
        保存的文件名。

    Returns
    -------
    str
        保存的文件路径。
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    # 设置中文字体
    plt.rcParams["font.family"] = _CN_FONT
    plt.rcParams["axes.unicode_minus"] = False

    ax.scatter(x_data, y_data, color="#4472C4", label="测量数据", zorder=5)

    x = np.linspace(min(x_data), max(x_data), 200)
    if fit_type == "linear":
        # 对本数据做线性拟合
        x_arr = np.array(x_data, dtype=float)
        y_arr = np.array(y_data, dtype=float)
        a, b = np.linalg.lstsq(np.vstack([x_arr, np.ones_like(x_arr)]).T, y_arr, rcond=None)[0]
        ax.plot(x, a * x + b, color="#E74C3C", label=f"拟合线: y={a:.3f}x+{b:.3f}")
    if extra_lines:
        for line in extra_lines:
            ax.plot(line["x"], line["y"], line.get("style", "-"), label=line.get("label", ""))

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    file_path = os.path.join(OUTPUT_DIR, save_name)
    fig.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return file_path


# ==============================================
# 工具4：生成实验报告（Word 格式）
# ==============================================
def generate_report(experiment_name, data_summary, results_summary, analysis_text,
                    chart_paths=None, output_name="report.docx"):
    """
    生成一个简易的实验报告 HTML 文件（可转换为 Word）。

    Parameters
    ----------
    experiment_name : str
        实验名称。
    data_summary : str
        数据摘要。
    results_summary : str
        计算结果摘要。
    analysis_text : str
        分析结论。
    chart_paths : list of str
        图表路径列表。
    output_name : str
        输出文件名（.html 或 .docx）。

    Returns
    -------
    str
        保存的文件路径。
    """
    # 由于环境限制，使用 HTML 输出，方便浏览器查看
    chart_html = ""
    if chart_paths:
        for path in chart_paths:
            if os.path.exists(path):
                # 转为相对路径
                rel = os.path.relpath(path, OUTPUT_DIR)
                chart_html += f'<img src="{rel}" style="max-width:100%;margin:12px 0;" />\n'

    # 将结果摘要从 dict 格式转为多行文本
    if isinstance(results_summary, dict):
        lines = []
        for k, v in results_summary.items():
            if isinstance(v, dict):
                lines.append(f"<b>{k}：</b><br>")
                for sk, sv in v.items():
                    lines.append(f"&nbsp;&nbsp;{sk}: {sv}<br>")
            else:
                lines.append(f"<b>{k}：</b>{v}<br>")
        results_html = "".join(lines)
    else:
        results_html = str(results_summary).replace("\n", "<br>")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>{experiment_name} — 实验报告</title></head>
<body style="font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
<h1 style="text-align:center;">{experiment_name} — 实验报告</h1>
<hr>
<h2>一、实验目的</h2>
<p>本实验旨在通过霍尔效应测量霍尔元件的灵敏度，验证霍尔电压与工作电流和励磁电流的线性关系。</p>
<h2>二、实验原理</h2>
<p>当通有电流的半导体置于磁场中时，载流子受到洛伦兹力作用，在垂直于电流和磁场的方向上产生电势差，称为霍尔电压。</p>
<h2>三、实验数据</h2>
<pre>{data_summary}</pre>
<h2>四、数据处理与结果</h2>
<div>{results_html}</div>
<h2>五、实验图表</h2>
<div>{chart_html}</div>
<h2>六、误差分析</h2>
<p>{analysis_text}</p>
</body>
</html>"""
    file_path = os.path.join(OUTPUT_DIR, output_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return file_path


# ==============================================
# 工具5：杨氏模量专用计算
# ==============================================
def compute_young_modulus(force, diameter, length, elongation, width=None):
    """
    计算杨氏模量（拉伸法）。

    E = (F * L) / (A * ΔL)

    Parameters
    ----------
    force : float or list
        拉力 (N)。
    diameter : float or list
        钢丝直径 (mm)。
    length : float
        钢丝原长 (mm)。
    elongation : float or list
        伸长量 (mm)。
    width : float or list, optional
        宽度 (mm)，梁弯曲法时需要。

    Returns
    -------
    dict
    """
    F = np.mean(np.array(force, dtype=float)) if isinstance(force, list) else float(force)
    d = np.mean(np.array(diameter, dtype=float)) if isinstance(diameter, list) else float(diameter)
    ΔL = np.mean(np.array(elongation, dtype=float)) if isinstance(elongation, list) else float(elongation)
    A = np.pi * (d / 2000) ** 2  # 截面积 (m²)
    L = float(length) / 1000  # 原长 (m)
    E = (F * L) / (A * ΔL) / 1e9  # 转为 GPa
    return {
        "E_GPa": round(E, 4),
        "F_N": round(F, 4),
        "d_mm": round(d, 4),
        "ΔL_mm": round(ΔL, 4),
        "A_m2": round(A, 10),
        "summary": f"杨氏模量 E = {E:.4f} GPa (F={F:.2f}N, d={d:.4f}mm, ΔL={ΔL:.4f}mm)",
    }


# ==============================================
# 工具6：霍尔效应专用计算
# ==============================================
def compute_hall_effect(work_currents, hall_voltages, excitation_currents=None):
    """
    计算霍尔元件灵敏度 K_H。

    U_H = K_H * I * B

    如果提供了励磁电流，用 I*B 乘积做线性拟合得到 K_H。
    否则用 I 做线性拟合得到 K_H * B（假设磁场恒定）。

    Parameters
    ----------
    work_currents : list of float
        工作电流 I (mA)，单位 mA。
    hall_voltages : list of float
        霍尔电压 U_H (mV)，单位 mV。
    excitation_currents : list of float or None
        励磁电流 I_m (A)，用于改变磁场。

    Returns
    -------
    dict
    """
    I = np.array(work_currents, dtype=float)
    U = np.array(hall_voltages, dtype=float)
    if excitation_currents is not None:
        Im = np.array(excitation_currents, dtype=float)
        X = I * Im
        x_label = "I * I_m (mA·A)"
        y_label = "U_H (mV)"
        a, b = np.linalg.lstsq(np.vstack([X, np.ones_like(X)]).T, U, rcond=None)[0]
        R2 = 1 - np.sum((U - (a * X + b))**2) / np.sum((U - np.mean(U))**2)
        return {
            "K_H": round(a, 6),
            "intercept": round(b, 6),
            "R²": round(R2, 6),
            "summary": f"霍尔灵敏度 K_H = {a:.4f} mV/(mA·A) (R²={R2:.4f})",
            "x_label": x_label,
            "y_label": y_label,
        }
    else:
        # 恒磁场，直接用 I 拟合
        a, b = np.linalg.lstsq(np.vstack([I, np.ones_like(I)]).T, U, rcond=None)[0]
        R2 = 1 - np.sum((U - (a * I + b))**2) / np.sum((U - np.mean(U))**2)
        return {
            "K_H_B": round(a, 6),
            "intercept": round(b, 6),
            "R²": round(R2, 6),
            "summary": f"K_H * B = {a:.4f} mV/mA (R²={R2:.4f})",
            "x_label": "I (mA)",
            "y_label": "U_H (mV)",
        }


# ==============================================
# 工具7：通用实验插件运行器
# ==============================================
def run_experiment_plugin(experiment_name, data):
    """
    运行任意已注册的实验插件，自动完成数据处理、图表生成和报告生成。

    Parameters
    ----------
    experiment_name : str
        实验名称（必须与已注册插件名完全一致）。
    data : dict
        实验数据，键为数据项名称，值为数值列表。
        e.g. {"钢丝直径(mm)": [0.495, 0.497, ...], "砝码质量(kg)": [0, 1, 2, ...]}

    Returns
    -------
    dict
        包含处理结果、图表路径、报告内容等。
    """
    from plugins import PluginRegistry

    plugin_cls = PluginRegistry.get(experiment_name)
    if plugin_cls is None:
        available = PluginRegistry.list_all()
        return {
            "status": "error",
            "message": f"未找到实验插件「{experiment_name}」。可用的实验：{', '.join(available)}"
        }

    plugin = plugin_cls() if isinstance(plugin_cls, type) else plugin_cls

    try:
        # 1. 计算
        results = plugin.calculate(data)

        # 2. 生成图表
        chart_dir = os.path.join(OUTPUT_DIR, "charts")
        os.makedirs(chart_dir, exist_ok=True)
        chart_paths = []
        try:
            chart_paths = plugin.generate_chart(data, results, chart_dir)
        except Exception as e:
            print(f"  [警告] 图表生成失败: {e}")

        # 3. 获取报告内容
        report_content = {}
        try:
            report_content = plugin.get_report_content(data, results)
        except Exception as e:
            print(f"  [警告] 报告内容生成失败: {e}")

        return {
            "status": "success",
            "experiment_name": experiment_name,
            "results": results,
            "chart_paths": chart_paths,
            "report_content": report_content,
            "message": f"实验「{experiment_name}」处理完成。"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"实验「{experiment_name}」处理失败：{str(e)}"
        }