"""电子小制作实验模块
===================
二级大物综合实验 —— 电学综合设计实验：无级调压台灯电路设计

实验内容（对应《电子小制作（实验指导）》）：
1. 元件性能测试（附录2 基本特性测量，下课之前提交数据处理）：
   整流二极管 1N4007 正反向测试；色环电阻（1k、2k）测量与色环辨别；
   电解电容（6.3μF）与电位器（500k）测量；单向晶闸管 PCR606 电极判别与触发测试；
2. 设计并制作由晶闸管、桥式整流电路与 RC 触发电路组成的无级调压台灯，
   记录不同电位器阻值下的灯泡电压与亮度现象；
3. 提升/进阶内容：主回路与控制回路在直流/交流组合下的晶闸管
   导通、保持、关断测试（记录灯泡亮暗与电压并解释现象）；
4. 高阶内容：示波器测灯泡工作电压波形、晶闸管导通时间、电扇无级调速
   （观察记录，无数据处理表）。

实验指导说明"不需要写报告，下课之前提交数据处理"，故 report_enabled = False。

网页流程（新版结构化接口）：
1. schema() 声明二极管、色环电阻、电容与电位器、晶闸管、台灯性能、
   导通关断测试六张表与实验参数；
2. preview() 实时判定元件好坏、计算相对误差、分析调压特性；
3. handle_structured() 生成台灯 U-Rp 曲线、二极管压降图、电阻对比图与 Word 文档。

旧版 CSV 流程 handle() 保留（通用列名识别），供旧接口与 AI 助教调用。
"""

from __future__ import annotations

import math
import os
import traceback
from typing import Any

import numpy as np

from head import *  # 导入万能头（analyse、insert_data、pandas 等）
from structured_support import as_number, copied_tables, make_schema, make_table, structured_result
from theory_content import get_table_theory

# ── 常数与判据 ──
_SI_VF_RANGE = (500.0, 900.0)   # 硅二极管正向压降典型范围（mV）
_GE_VF_RANGE = (200.0, 400.0)   # 锗二极管正向压降典型范围（mV）
_SCR_GK_RANGE = (0.4, 1.0)      # 晶闸管 G-K 硅 PN 结正向压降范围（V）
_SCR_AK_ON_RANGE = (0.5, 2.5)   # 晶闸管触发导通后 A-K 管压降范围（V，约 1 V）
_ERR_LIMIT = 20.0               # 电解电容/电位器常用标称误差上限（%）
_RESISTOR_GOLD = 5.0            # 四环电阻金环误差（%）
_RESISTOR_SILVER = 10.0         # 四环电阻银环误差（%）
_U_MONO_TOL = 0.3               # 台灯电压单调性检查容差（V）
_U_SUPPLY_DEFAULT = 24.0        # 实验装置交流电源电压（V）


def name():
    return "电子小制作"


# ──────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────

def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _param_number(parameters: dict[str, Any], key: str, label: str,
                  default: float | None) -> float | None:
    """读取实验参数；未填写返回 default，非数字报错。"""
    value = parameters.get(key)
    if not _has_value(value):
        return default
    number = as_number(value)
    if number is None:
        raise ValueError("{}必须是数字".format(label))
    return number


def _font_properties():
    from matplotlib.font_manager import FontProperties

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceHanSansSC-Regular.otf"))
    return FontProperties(fname=font_path) if os.path.isfile(font_path) else None


# ──────────────────────────────────────────────
# 各表计算
# ──────────────────────────────────────────────

def _calc_diode(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """整流二极管：正向压降判材料、反向显示判好坏。"""
    labels: list[str] = []
    vf_values: list[float] = []
    lines: list[str] = []
    good = True
    for index, row in enumerate(rows or [], start=1):
        label = str(row.get("c0") or "").strip() or "二极管{}".format(index)
        raw_vf = row.get("c1")
        reverse = str(row.get("c2") or "").strip()
        if not _has_value(raw_vf):
            raise ValueError("整流二极管测试表第 {} 行未填写正向压降".format(index))
        vf = as_number(raw_vf)
        if vf is None or vf < 0:
            raise ValueError("整流二极管测试表第 {} 行正向压降不是有效数字".format(index))
        if vf == 0:
            kind = "正向压降 0 mV：二极管可能开路/损坏或表笔接反，请核对"
            good = False
        elif _SI_VF_RANGE[0] <= vf <= _SI_VF_RANGE[1]:
            kind = "硅二极管（{:.0f} mV）".format(vf)
        elif _GE_VF_RANGE[0] <= vf < _GE_VF_RANGE[1]:
            kind = "锗二极管（{:.0f} mV）".format(vf)
        else:
            kind = "正向压降 {:.0f} mV 不在常见硅管（500~900 mV）或锗管（200~400 mV）范围，请核对档位与表笔极性".format(vf)
            good = False
        rev_norm = reverse.upper()
        if rev_norm in ("1", "OL"):
            rev_verdict = "反向显示 1/OL，正常"
        elif rev_norm in ("0", "000"):
            rev_verdict = "反向显示 0，二极管可能已击穿短路"
            good = False
        elif rev_norm == "":
            rev_verdict = "未填写反向显示"
        else:
            rev_verdict = "反向显示异常（{}），请核对".format(reverse)
            good = False
        lines.append("{}：{}；{}。".format(label, kind, rev_verdict))
        labels.append(label)
        vf_values.append(vf)
    if len(rows) >= 4:
        lines.append("共检测 {} 只二极管：桥式整流电路需 4 只性能相近的二极管，请确认均为正常硅管。".format(len(rows)))
    return {"lines": lines, "labels": labels, "vf_values": vf_values, "good": good}


def _calc_resistor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """色环电阻：三次测量取平均，与色环标称值比较相对误差。"""
    labels: list[str] = []
    nominals: list[float] = []
    means: list[float] = []
    errors: list[float] = []
    lines: list[str] = []
    for index, row in enumerate(rows or [], start=1):
        label = str(row.get("c0") or "").strip() or "R{}".format(index)
        raw_nominal = row.get("c1")
        if not _has_value(raw_nominal):
            raise ValueError("色环电阻测量表第 {} 行未填写色环标称值".format(index))
        nominal = as_number(raw_nominal)
        if nominal is None or nominal <= 0:
            raise ValueError("色环电阻测量表第 {} 行标称值不是有效正数".format(index))
        measurements = [as_number(row.get(col)) for col in ("c2", "c3", "c4")]
        measurements = [value for value in measurements if value is not None]
        if not measurements:
            raise ValueError("色环电阻测量表第 {} 行未填写任何测量值".format(index))
        mean = sum(measurements) / len(measurements)
        sigma = 0.0
        if len(measurements) > 1:
            sigma = math.sqrt(sum((value - mean) ** 2 for value in measurements) / (len(measurements) - 1))
        error = abs(mean - nominal) / nominal * 100.0
        if error <= 1.0:
            verdict = "误差极小"
        elif error <= _RESISTOR_GOLD:
            verdict = "在四环金环 ±5% 允差内"
        elif error <= _RESISTOR_SILVER:
            verdict = "在四环银环 ±10% 允差内"
        else:
            verdict = "超出常见色环误差（±5%/±10%），请核读色环或检查电阻是否损坏"
        lines.append("{}：R̄ = {:.1f} Ω，σ = {:.1f} Ω，相对误差 E = {:.2f}% → {}。".format(
            label, mean, sigma, error, verdict))
        labels.append(label)
        nominals.append(nominal)
        means.append(mean)
        errors.append(error)
    return {"lines": lines, "labels": labels, "nominals": nominals,
            "means": means, "errors": errors}


def _calc_component(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """电解电容与电位器：实测值与标称值比较。"""
    lines: list[str] = []
    for index, row in enumerate(rows or [], start=1):
        label = str(row.get("c0") or "").strip() or "元件{}".format(index)
        unit = str(row.get("c3") or "").strip()
        raw_nominal = row.get("c1")
        raw_measured = row.get("c2")
        if not _has_value(raw_nominal) or not _has_value(raw_measured):
            raise ValueError("电容与电位器参数表第 {} 行需填写标称值与实测值".format(index))
        nominal = as_number(raw_nominal)
        measured = as_number(raw_measured)
        if nominal is None or measured is None or nominal <= 0:
            raise ValueError("电容与电位器参数表第 {} 行数值无效".format(index))
        error = abs(measured - nominal) / nominal * 100.0
        if error <= _ERR_LIMIT:
            verdict = "在标称误差 ±20% 范围内"
        else:
            verdict = "偏差较大（电解电容容量误差大、存放久易失效，或电位器老化，请复查）"
        lines.append("{}：标称 {:.2f} {}，实测 {:.2f} {}，相对误差 E = {:.2f}% → {}。".format(
            label, nominal, unit, measured, unit, error, verdict))
    return {"lines": lines}


def _calc_scr(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """晶闸管：G-K、A-K（未触发/触发后）判定。"""
    gk = None
    ak_off_rev = ""
    ak_on = None
    extra_lines: list[str] = []
    for row in rows or []:
        item = str(row.get("c0") or "").strip()
        if not item:
            continue
        raw_val = row.get("c1")
        reverse = str(row.get("c2") or "").strip()
        val = as_number(raw_val) if _has_value(raw_val) else None
        item_key = item.upper().replace(" ", "")
        if "G-K" in item_key or "GK" in item_key or ("控制极" in item and "阴极" in item):
            gk = val
        elif "未触发" in item:
            ak_off_rev = reverse
        elif "触发" in item:
            ak_on = val
        elif val is not None:
            extra_lines.append("{}：实测 {} V".format(item, val))

    lines: list[str] = []
    if gk is not None:
        if _SCR_GK_RANGE[0] <= gk <= _SCR_GK_RANGE[1]:
            lines.append("G-K 正向导通电压 {:.3f} V：控制极-阴极间为硅 PN 结，正常；"
                         "红表笔所接为控制极 G，黑表笔所接为阴极 K。".format(gk))
        else:
            lines.append("注意：G-K 正向导通电压 {:.3f} V 不在硅 PN 结常见范围（0.4~1.0 V），"
                         "请核对电极判别与表笔接法。".format(gk))
    else:
        lines.append("未填写 G-K 极间正向导通电压。")
    if ak_off_rev:
        rev_norm = ak_off_rev.upper()
        if rev_norm in ("1", "OL"):
            lines.append("A-K 未触发时不导通（显示 1/OL），正常。")
        elif rev_norm in ("0", "000"):
            lines.append("警告：A-K 未触发即导通（显示 0），晶闸管可能已击穿短路。")
        else:
            lines.append("A-K 未触发反向显示异常（{}），请核对。".format(ak_off_rev))
    if ak_on is not None:
        if _SCR_AK_ON_RANGE[0] <= ak_on <= _SCR_AK_ON_RANGE[1]:
            lines.append("A-K 触发后导通电压 {:.3f} V（晶闸管导通管压降约 1 V），触发导通成功。".format(ak_on))
        else:
            lines.append("注意：A-K 触发后电压 {:.3f} V 不在导通管压降常见范围（0.5~2.5 V），"
                         "请核对触发方式（导线短接 A 与 G）。".format(ak_on))
    lines.extend(extra_lines)
    return {"lines": lines}


def _calc_lamp(rows: list[dict[str, Any]], u_supply: float | None,
               u_fan_start: float | None) -> dict[str, Any]:
    """无级调压台灯：U 随 R_p 变化范围、单调性、与电源比较。"""
    rp_values: list[float] = []
    u_values: list[float] = []
    for index, row in enumerate(rows or [], start=1):
        raw_rp = row.get("c0")
        raw_u = row.get("c1")
        if not _has_value(raw_rp) and not _has_value(raw_u):
            continue
        rp = as_number(raw_rp)
        u = as_number(raw_u)
        if rp is None or u is None:
            raise ValueError("台灯性能检测表第 {} 行电位器阻值与灯泡电压需为数字".format(index))
        if rp < 0 or u < 0:
            raise ValueError("台灯性能检测表第 {} 行数值不能为负".format(index))
        rp_values.append(rp)
        u_values.append(u)
    if len(rp_values) < 2:
        raise ValueError("台灯性能检测表至少需要 2 组有效数据")

    order = sorted(range(len(rp_values)), key=lambda i: rp_values[i])
    rp_sorted = [rp_values[i] for i in order]
    u_sorted = [u_values[i] for i in order]

    u_max = max(u_values)
    u_min = min(u_values)
    i_max = u_values.index(u_max)
    i_min = u_values.index(u_min)

    lines = [
        "共 {} 组数据：灯泡电压范围 {:.1f} ~ {:.1f} V（R_p = {:.1f} kΩ 时最高，"
        "R_p = {:.1f} kΩ 时最低）。".format(
            len(u_values), u_min, u_max, rp_values[i_max], rp_values[i_min]),
    ]
    rises = [i for i in range(len(u_sorted) - 1) if u_sorted[i + 1] > u_sorted[i] + _U_MONO_TOL]
    if rises:
        lines.append("注意：R_p 增大时灯泡电压在第 {} 个数据点附近出现上升，理论上应单调下降，"
                     "请检查测量或接线。".format(rises[0] + 1))
    else:
        lines.append("灯泡电压随 R_p 增大而单调下降，符合 RC 触发调压原理"
                     "（R_p 增大 → 充电变慢 → 导通时间变短 → 灯变暗）。")
    if u_supply is not None:
        if u_max > u_supply * 1.1:
            lines.append("注意：最高电压 {:.1f} V 高于电源电压 {:.1f} V，"
                         "请核对万用表档位（应使用交流电压档）与电源。".format(u_max, u_supply))
        elif u_max < u_supply * 0.7:
            lines.append("提示：最高电压 {:.1f} V 明显低于电源电压 {:.1f} V，"
                         "可检查灯泡接触与整流桥焊接质量。".format(u_max, u_supply))
    if u_fan_start is not None:
        ratio = u_fan_start / u_max * 100.0 if u_max > 0 else 0.0
        lines.append("风扇起始电压 {:.1f} V，约为最高电压的 {:.0f}%；"
                     "调节调压开关即可实现电扇转速由大到小的无级调节。".format(u_fan_start, ratio))
    return {"lines": lines, "rp_values": rp_values, "u_values": u_values}


def _calc_thyristor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """导通关断测试：逐项复述并检查现象与电压一致性。"""
    lines: list[str] = []
    count = 0
    for index, row in enumerate(rows or [], start=1):
        item = str(row.get("c0") or "").strip()
        phenomenon = str(row.get("c3") or "").strip()
        raw_u = row.get("c4")
        u = as_number(raw_u) if _has_value(raw_u) else None
        if not item and not phenomenon and u is None:
            continue
        count += 1
        note = ""
        if phenomenon and u is not None:
            off_words = ("灭", "不亮")
            if any(word in phenomenon for word in off_words) and u > 1.0:
                note = "（注意：现象记录为灭/不亮但电压 {:.1f} V，请核对）".format(u)
            elif ("亮" in phenomenon) and not any(word in phenomenon for word in off_words) and u < 1.0:
                note = "（注意：现象记录为亮但电压约 0 V，请核对）"
        lines.append("{}：主回路 {}，控制回路 {}，灯泡 {}，电压 {}{}".format(
            item or "第{}项".format(index),
            str(row.get("c1") or "").strip() or "—",
            str(row.get("c2") or "").strip() or "—",
            phenomenon or "—",
            "{:.1f} V".format(u) if u is not None else "—",
            note))
    if count:
        lines.append("晶闸管特点：触发导通后门极失去控制（保持导通）；"
                     "主回路断开或 A-K 反向即关断；交流主回路每半周期末电压过零自然关断。")
    return {"lines": lines}


# ──────────────────────────────────────────────
# 结构化接口
# ──────────────────────────────────────────────

def preview(payload: dict[str, Any]) -> dict[str, Any]:
    """网页输入时的实时预计算：元件判定、相对误差与调压特性分析。"""
    tables = copied_tables(payload)
    parameters = payload.get("parameters") or {}
    calc_results: dict[str, Any] = {}
    calc_messages: list[str] = []
    fit_notes: dict[str, list[str]] = {}

    try:
        u_supply = _param_number(parameters, "u_supply", "交流电源电压", _U_SUPPLY_DEFAULT)
    except ValueError:
        u_supply = _U_SUPPLY_DEFAULT
    try:
        u_fan_start = _param_number(parameters, "u_fan_start", "风扇开始旋转时电压", None)
    except ValueError:
        u_fan_start = None

    spec = (
        ("diode", ("c0", "c1", "c2"),
         ["硅二极管正向压降约 500~900 mV，锗管约 200~400 mV。",
          "反向显示 1/OL 为正常，0/000 说明二极管已击穿。"]),
        ("resistor", ("c0", "c1", "c2", "c3", "c4"),
         ["相对误差 E = |R̄ − R₀|/R₀ × 100%。",
          "四环电阻末环：金 ±5%、银 ±10%、棕 ±1%。"]),
        ("component", ("c0", "c1", "c2", "c3"),
         ["电解电容容量误差大（可达 ±20%），测量前需短接放电。",
          "电位器旋转旋钮阻值连续变化，记录最大阻值。"]),
        ("scr", ("c0", "c1", "c2"),
         ["晶闸管导通条件：A-K 正向电压 + G-K 正向触发；导通后门极失去控制。",
          "A-K 触发导通后管压降约 1 V，几乎不耗电。"]),
        ("lamp", ("c0", "c1", "c2"),
         ["R_p 增大 → 充电电流减小 → 导通时刻 t1 后移 → 灯泡变暗。",
          "U 应随 R_p 单调下降；R_p 最大时灯泡熄灭。"]),
        ("thyristor_test", ("c0", "c1", "c2", "c3", "c4"),
         ["触发导通后撤销门极电压仍保持导通（门极失去控制）。",
          "主回路断开或 A-K 反向即关断，灯泡熄灭。"]),
    )

    handlers = {
        "diode": _calc_diode,
        "resistor": _calc_resistor,
        "component": _calc_component,
        "scr": _calc_scr,
        "lamp": lambda rows: _calc_lamp(rows, u_supply, u_fan_start),
        "thyristor_test": _calc_thyristor,
    }

    for table_id, cols, notes in spec:
        rows = tables.get(table_id) or []
        if not any(_has_value(row.get(col)) for row in rows for col in cols):
            continue
        try:
            calc_results[table_id] = handlers[table_id](rows)
            fit_notes[table_id] = notes
        except ValueError as exc:
            calc_messages.append(str(exc))

    return {"tables": tables, "calc_results": calc_results,
            "calc_messages": calc_messages, "fit_notes": fit_notes}


# ──────────────────────────────────────────────
# 图表
# ──────────────────────────────────────────────

def _make_lamp_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """灯泡电压-电位器阻值散点 + 线性趋势线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    rp = np.asarray(info["rp_values"], dtype=float)
    u = np.asarray(info["u_values"], dtype=float)

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.scatter(rp, u, s=46, color="#2f7fc1", zorder=4, label="测量点")
    if len(rp) >= 2:
        coeffs = np.polyfit(rp, u, 1)
        x_fit = np.linspace(rp.min(), rp.max(), 100)
        axis.plot(x_fit, np.poly1d(coeffs)(x_fit), "--", color="#d94b40",
                  linewidth=1.2, zorder=3, label="线性趋势 k = {:.3f} V/kΩ".format(coeffs[0]))
    axis.set_xlabel("电位器阻值 R_p (kΩ)", fontproperties=font)
    axis.set_ylabel("灯泡电压 U (V)", fontproperties=font)
    axis.set_title("无级调压台灯：灯泡电压随电位器阻值变化", fontproperties=font)
    axis.grid(alpha=0.25)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "lamp_voltage.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "lamp_voltage.png", "title": "灯泡电压-电位器阻值关系",
            "x_label": "电位器阻值 R_p (kΩ)", "y_label": "灯泡电压 U (V)"}


def _make_diode_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """各二极管正向压降柱状图 + 硅管典型区。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    labels = info["labels"]
    vf_values = info["vf_values"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.axhspan(_SI_VF_RANGE[0], _SI_VF_RANGE[1], color="#3a9d5d", alpha=0.10, zorder=1)
    axis.text(0.995, 0.96, "硅管典型区 500~900 mV", transform=axis.transAxes, ha="right",
              va="top", fontsize=8, color="#666666", fontproperties=font)
    x = np.arange(len(labels))
    axis.bar(x, vf_values, width=0.55, color="#2f7fc1", alpha=0.85, zorder=3)
    for xi, value in enumerate(vf_values):
        axis.annotate("{:.0f}".format(value), (xi, value + 12), ha="center",
                      fontsize=9, fontproperties=font)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, fontproperties=font, fontsize=9)
    axis.set_xlabel("二极管", fontproperties=font)
    axis.set_ylabel("正向压降 (mV)", fontproperties=font)
    axis.set_title("整流二极管正向压降", fontproperties=font)
    axis.set_ylim(0, max(vf_values) * 1.25)
    axis.grid(alpha=0.25, axis="y", zorder=0)
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "diode_vf.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "diode_vf.png", "title": "整流二极管正向压降",
            "x_label": "二极管", "y_label": "正向压降 (mV)"}


def _make_resistor_chart(workpath: str, info: dict[str, Any]) -> dict[str, Any]:
    """色环标称值与测量平均值对比柱状图 + 相对误差标注。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font = _font_properties()
    labels = info["labels"]
    nominals = info["nominals"]
    means = info["means"]
    errors = info["errors"]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    x = np.arange(len(labels))
    width = 0.34
    axis.bar(x - width / 2, nominals, width, color="#8f9aa8", alpha=0.9, zorder=3, label="色环标称值")
    axis.bar(x + width / 2, means, width, color="#2f7fc1", alpha=0.9, zorder=3, label="测量平均值")
    for xi, (mean, error) in enumerate(zip(means, errors)):
        axis.annotate("E = {:.2f}%".format(error), (xi + width / 2, mean),
                      xytext=(0, 6), textcoords="offset points", ha="center",
                      fontsize=8.5, color="#3a9d5d", fontproperties=font)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, fontproperties=font, fontsize=9)
    axis.set_xlabel("电阻", fontproperties=font)
    axis.set_ylabel("阻值 (Ω)", fontproperties=font)
    axis.set_title("色环电阻标称值与测量平均值对比", fontproperties=font)
    axis.grid(alpha=0.25, axis="y", zorder=0)
    if font is not None:
        axis.legend(prop=font)
    else:
        axis.legend()
    figure.tight_layout()
    figure.savefig(os.path.join(workpath, "resistor_compare.png"), dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {"filename": "resistor_compare.png", "title": "色环电阻标称值与测量值对比",
            "x_label": "电阻", "y_label": "阻值 (Ω)"}


# ──────────────────────────────────────────────
# 新版结构化处理
# ──────────────────────────────────────────────

def handle_structured(workpath: str, payload: dict[str, Any]) -> dict[str, Any]:
    """新版结构化接口：判定元件、计算误差、分析调压特性，输出摘要、图表与 Word 文档。"""
    parameters = payload.get("parameters") or {}
    for parameter_id, label in (("u_supply", "交流电源电压"), ("u_fan_start", "风扇开始旋转时电压")):
        if _has_value(parameters.get(parameter_id)) and as_number(parameters.get(parameter_id)) is None:
            return {"code": 1, "message": "{}必须是数字".format(label)}

    result = preview(payload)
    calc = result["calc_results"]

    if not calc:
        return {"code": 1, "message": "；".join(result["calc_messages"]) or "请先填写至少一张测量表。"}

    os.makedirs(workpath, exist_ok=True)
    charts: list[dict[str, Any]] = []
    if "lamp" in calc:
        charts.append(_make_lamp_chart(workpath, calc["lamp"]))
    if "diode" in calc:
        charts.append(_make_diode_chart(workpath, calc["diode"]))
    if "resistor" in calc:
        charts.append(_make_resistor_chart(workpath, calc["resistor"]))

    summary: list[str] = []
    for table_id, label in (("diode", "整流二极管测试"),
                            ("resistor", "色环电阻测量"),
                            ("component", "电容与电位器参数"),
                            ("scr", "晶闸管电极与触发测试")):
        if table_id in calc:
            summary.append("【{}】".format(label))
            summary.extend(calc[table_id]["lines"])
    if "lamp" in calc:
        summary.append("【无级调压台灯性能检测】")
        summary.extend(calc["lamp"]["lines"])
    if "thyristor_test" in calc:
        summary.append("【晶闸管导通关断测试】")
        summary.extend(calc["thyristor_test"]["lines"])

    warnings = list(result["calc_messages"])
    for table_id, label in (("diode", "整流二极管测试"),
                            ("resistor", "色环电阻测量"),
                            ("component", "电容与电位器参数"),
                            ("scr", "晶闸管电极与触发测试"),
                            ("lamp", "无级调压台灯性能检测"),
                            ("thyristor_test", "晶闸管导通关断测试（选做）")):
        if table_id == "thyristor_test":
            continue
        if table_id not in calc:
            warnings.append("未填写「{}」表，数据处理结果不完整（见附录 2 基本特性测量）。".format(label))

    enriched = dict(payload)
    enriched["tables"] = result["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=summary,
        warnings=warnings,
        charts=charts,
    )


# ──────────────────────────────────────────────
# 表结构与示例数据
# ──────────────────────────────────────────────

def _set_units(table: dict[str, Any], units: tuple[str, ...]) -> dict[str, Any]:
    """给 make_table 生成的列补充单位。"""
    for column, unit in zip(table["columns"], units):
        if unit:
            column["unit"] = unit
    return table


def schema() -> dict[str, Any]:
    diode = _set_units(
        make_table(
            "diode", "整流二极管测试表（基础内容，附录2-1）",
            ["二极管编号", "正向压降", "反向显示"],
            sample=[
                ["二极管1", 626, "1"],
                ["二极管2", 630, "1"],
                ["二极管3", 618, "1"],
                ["二极管4", 640, "1"],
            ],
            text_columns=(0, 2), min_rows=4, initial_rows=4,
            description=(
                "数字万用表二极管档：红表笔接二极管正极、黑表笔接负极，显示“626”即正向导通管压降 626 mV；"
                "表笔反接显示“1”或“OL”为反向正常，显示“0”或“000”说明二极管已击穿。"
                "桥式整流需 4 只性能一致的二极管（1N4007）。"
            ),
        ),
        ("", "mV", ""),
    )
    diode["calc"] = {"label": "判定二极管"}

    resistor = _set_units(
        make_table(
            "resistor", "色环电阻测量表（基础内容，附录2-2）",
            ["电阻编号", "色环标称值 R0(Ω)", "测量值1 R1(Ω)", "测量值2 R2(Ω)", "测量值3 R3(Ω)"],
            sample=[
                ["R1", 1000, 998, 1001, 997],
                ["R2", 2000, 2005, 1998, 2001],
            ],
            text_columns=(0,), min_rows=2, initial_rows=2,
            description=(
                "先读色环记录标称值（四环电阻：前二环为有效数字，第三环为倍乘数，"
                "末环为误差——金 ±5%、银 ±10%、棕 ±1%），再用万用表电阻档测量 3 次。"
            ),
        ),
        ("", "Ω", "Ω", "Ω", "Ω"),
    )
    resistor["calc"] = {"label": "计算平均值与相对误差"}

    component = _set_units(
        make_table(
            "component", "电容与电位器参数表（基础内容，附录2-3/2-4）",
            ["元件名称", "标称值", "实测值", "单位"],
            sample=[
                ["电解电容 C", 6.3, 6.1, "μF"],
                ["电位器最大阻值 R_p", 500, 495, "kΩ"],
            ],
            text_columns=(0, 3), min_rows=2, initial_rows=2,
            description=(
                "电容表测量电解电容（测量待测电容前需短接放电，然后直接测量）；"
                "万用表测电位器两固定端电阻，旋转旋钮记录其最大阻值。"
            ),
        ),
        ("", "", "", ""),
    )
    component["calc"] = {"label": "计算元件相对误差"}

    scr = _set_units(
        make_table(
            "scr", "晶闸管电极与触发测试表（基础内容，附录2-5）",
            ["测试项目", "正向导通电压", "反向显示"],
            sample=[
                ["G-K 极间正向导通电压", 0.676, "1"],
                ["A-K 极间（未触发）", "", "1"],
                ["A-K 极间（短接触发后）", 0.779, ""],
            ],
            text_columns=(0, 2), min_rows=3, initial_rows=3,
            description=(
                "二极管档两两测量晶闸管三电极：红表笔接控制极 G、黑表笔接阴极 K 时显示 0.6~0.8 V，"
                "剩下的是阳极；A-K 未触发显示“1”（不导通），用导线短接 A 与 G 触发后，"
                "A-K 显示导通电压（约 1 V）。"
            ),
        ),
        ("", "V", ""),
    )
    scr["calc"] = {"label": "判定晶闸管"}

    lamp = _set_units(
        make_table(
            "lamp", "无级调压台灯性能检测表（基础内容，附录2-6）",
            ["电位器阻值 R_p", "灯泡电压 U", "现象记录"],
            sample=[
                [0, 23.6, "最亮"],
                [100, 18.4, "亮"],
                [250, 11.3, "较暗"],
                [400, 5.2, "暗"],
                [500, 2.1, "微亮/熄灭"],
            ],
            text_columns=(2,), min_rows=3, initial_rows=5,
            chart={"x_column": "c0", "y_column": "c1",
                   "x_label": "电位器阻值 R_p (kΩ)", "y_label": "灯泡电压 U (V)",
                   "title": "灯泡电压随电位器阻值变化曲线", "fit": "auto"},
            description=(
                "旋转电位器旋钮，用万用表交流电压档记录不同阻值位置下的灯泡电压与亮度现象；"
                "电扇调速时记录风扇开始旋转时的电压（见实验参数）。"
            ),
        ),
        ("kΩ", "V", ""),
    )
    lamp["calc"] = {"label": "分析调压特性"}

    thyristor_test = _set_units(
        make_table(
            "thyristor_test", "晶闸管导通关断测试表（提升/进阶内容，选做）",
            ["测试项目", "主回路状态", "控制回路状态", "灯泡现象", "灯泡电压"],
            sample=[
                ["导通测试（闭合 s2）", "直流", "直流（正向触发）", "亮", 11.5],
                ["保持导通（断开 s2）", "直流", "断开", "仍亮", 11.4],
                ["关断（断开主回路）", "断开", "断开", "灭", 0],
                ["主回路加反向电压", "直流（反向）", "正向/断开", "不亮", 0],
                ["控制极加反向电压", "直流（正向）", "反向", "不亮", 0],
            ],
            text_columns=(0, 1, 2, 3), min_rows=1, initial_rows=5, required=False,
            description=(
                "提升内容：主、控回路均为直流时的导通、保持、关断测试；"
                "进阶内容：主/控回路交流与直流三种组合（主交控直、主直控交、主交控交）下"
                "记录灯泡亮暗与电压，并解释实验现象。"
            ),
        ),
        ("", "", "", "", "V"),
    )
    thyristor_test["calc"] = {"label": "检查导通测试记录"}
    thyristor_test["enabled_by_default"] = False

    parameters = [
        {"id": "u_supply", "label": "交流电源电压", "unit": "V", "type": "number",
         "default": _U_SUPPLY_DEFAULT, "min": 0, "step": "any", "required": False,
         "help": "实验装置为 24 V 交流电源（安全电压），高阶内容可在 12 V 与 24 V 下测试"},
        {"id": "u_fan_start", "label": "风扇开始旋转时电压", "unit": "V", "type": "number",
         "default": "", "min": 0, "step": "any", "required": False,
         "help": "高阶内容：打开无级调压开关，记录电扇开始旋转时的电压"},
    ]

    theory = get_table_theory("exp49")
    return make_schema(
        (
            "电学综合设计实验——无级调压台灯电路：① 用万用表/电容表测整流二极管（1N4007）、"
            "色环电阻、电解电容（6.3μF）、电位器（500k）、单向晶闸管（PCR606）的基本参数；"
            "② 设计并制作晶闸管、桥式整流电路与 RC 触发电路组成的无级调压台灯，"
            "记录不同电位器阻值下灯泡电压与现象；③ 提升/进阶内容记录晶闸管在主、控回路"
            "直流/交流组合下的导通、保持与关断；④ 高阶内容用示波器观测灯泡电压波形"
            "与导通时间（记录结果，无数据处理表）。"
        ),
        [diode, resistor, component, scr, lamp, thyristor_test],
        parameters=parameters,
        parameters_sample={"u_supply": _U_SUPPLY_DEFAULT, "u_fan_start": ""},
        analysis_hints=(
            "硅二极管正向压降约 500~900 mV，锗管约 200~400 mV，反向显示 1/OL 为正常、0 为击穿；"
            "色环电阻相对误差 E = |R̄−R₀|/R₀ 一般应小于 5%（金环）或 10%（银环）；"
            "电解电容容量误差可达 ±20%，测量前需短接放电；"
            "晶闸管 G-K 正向压降 0.4~1.0 V（硅 PN 结），A-K 未触发应不导通（显示 1），"
            "触发后导通管压降约 1 V；灯泡电压应随电位器阻值单调下降，"
            "最高电压应接近 24 V 交流电源电压；导通测试中触发后断开控制回路灯泡仍亮（保持导通），"
            "主回路反向或断开即关断。"
        ),
        preview_enabled=True,
        formulas=theory.get("_global", {}).get("formulas", []),
        variables=theory.get("_global", {}).get("variables", []),
        table_theory=theory,
        report_enabled=False,
    )


# ──────────────────────────────────────────────
# 旧版 CSV 流程（供旧接口与 AI 助教调用）
# ──────────────────────────────────────────────

def _find_column(cols: list[str], keywords: tuple[str, ...]) -> str | None:
    """按关键词从列名中查找目标列。

    单字符关键词（如 U、V、I、A）要求列名完全相等，避免误匹配
    CURRENT 等单词；多字符关键词允许子串匹配（如 电压、标称）。
    """
    for col in cols:
        upper = str(col).strip().upper()
        for keyword in keywords:
            if len(keyword) == 1:
                if upper == keyword:
                    return col
            elif keyword in upper:
                return col
    return None


def _legacy_voltage_current(docu, data: pd.DataFrame, cols: list[str]) -> None:
    """U、I 两列 → 等效电阻 R = U/I。"""
    u_col = _find_column(cols, ("U", "V", "电压"))
    i_col = _find_column(cols, ("I", "A", "电流"))
    if u_col is None or i_col is None or u_col == i_col:
        return
    u = pd.to_numeric(data[u_col], errors='coerce')
    i = pd.to_numeric(data[i_col], errors='coerce')
    valid = u.notna() & i.notna() & (i.abs() > 1e-10)
    if valid.sum() == 0:
        return
    r_calc = u[valid] / i[valid]
    docu.add_paragraph("由 U/I 计算等效电阻（欧姆定律）：")
    insert_data(docu, "等效电阻 R", analyse(r_calc, 0, 0, 'R', r'\Omega'), "word")
    docu.add_paragraph()


def _legacy_resistor(docu, data: pd.DataFrame, cols: list[str]) -> None:
    """色环标称值 + 测量值列 → 平均值与相对误差。"""
    nominal_col = _find_column(cols, ('标称', '色环', '阻值'))
    measure_cols = [col for col in cols if '测量' in str(col)]
    if nominal_col is None or not measure_cols:
        return
    nominal = pd.to_numeric(data[nominal_col], errors='coerce')
    docu.add_paragraph("色环电阻测量（平均值与相对误差）：")
    for index in range(len(data)):
        if pd.isna(nominal.iloc[index]):
            continue
        values = []
        for col in measure_cols:
            value = pd.to_numeric(data[col], errors='coerce').iloc[index]
            if pd.notna(value):
                values.append(value)
        if not values:
            continue
        mean = float(np.mean(values))
        error = abs(mean - float(nominal.iloc[index])) / float(nominal.iloc[index]) * 100.0
        docu.add_paragraph("第 {} 行：R̄ = {:.1f} Ω，相对误差 E = {:.2f}%".format(index + 1, mean, error))
    docu.add_paragraph()


def _legacy_lamp(docu, data: pd.DataFrame, cols: list[str]) -> None:
    """电位器阻值 + 电压列 → 调压范围描述。"""
    rp_col = _find_column(cols, ('电位器', 'RP', 'R_P'))
    u_col = _find_column(cols, ("U", "V", "电压"))
    if rp_col is None or u_col is None or rp_col == u_col:
        return
    rp = pd.to_numeric(data[rp_col], errors='coerce')
    u = pd.to_numeric(data[u_col], errors='coerce')
    valid = rp.notna() & u.notna()
    if valid.sum() < 2:
        return
    docu.add_paragraph("无级调压特性：R_p 从 {:.1f} 调至 {:.1f} 时，灯泡电压由 {:.1f} 变为 {:.1f}。".format(
        rp[valid].min(), rp[valid].max(), u[valid].max(), u[valid].min()))
    docu.add_paragraph()


def handle(workpath: str, extension: str) -> int:
    """旧版 CSV 流程：通用列名识别（U/I、电阻、台灯），生成 Word 文档。"""
    try:
        excelpath = workpath + name() + '.' + extension

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]
            data = pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data = pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        docu = Document()
        style_doc_font(docu)

        docu.add_heading(name(), level=0)
        docu.add_paragraph("电学综合设计实验：无级调压台灯电路设计（旧版 CSV 流程）")
        docu.add_paragraph()

        table = docu.add_table(rows=len(data) + 1, cols=len(cols), style='Table Grid')
        for j, header in enumerate(cols):
            table.rows[0].cells[j].text = str(header)
        for i in range(len(data)):
            for j in range(len(cols)):
                try:
                    value = pd.to_numeric(data[cols[j]], errors='coerce').iloc[i]
                    table.rows[i + 1].cells[j].text = '{:.4g}'.format(value) if pd.notna(value) else str(data[cols[j]].iloc[i])
                except Exception:
                    table.rows[i + 1].cells[j].text = str(data[cols[j]].iloc[i])
        docu.add_paragraph()

        _legacy_voltage_current(docu, data, cols)
        _legacy_resistor(docu, data, cols)
        _legacy_lamp(docu, data, cols)

        docu.save(workpath + name() + ".docx")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
