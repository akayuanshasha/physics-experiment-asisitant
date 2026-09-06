"""数字表改装实验模块
=================
二级大物电磁学实验 —— 数字表改装

实验内容：
本实验包含两组数据表：
1. 多量程直流数字电压表电路参数表（5个量程）
2. 20V量程电压表内阻影响测试表（3组测试）

每组数据独立进行异常检验。

物理背景：
数字电压表由表头与分压电阻串联组成。
量程扩展公式：R_s = U/Ig - Rg
其中 Ig 为满偏电流，Rg 为表头内阻，U 为量程电压。
电压表内阻会引起测量误差，内阻越大误差越小。
"""

from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)
from theory_content import get_formulas, get_variables, get_table_theory
from sample_data_loader import load_sample_data_numeric

def name():
    return "数字表改装"

def handle(workpath,extension):
    try:
        excelpath=workpath+name()+'.'+extension

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"]
            data=pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data=pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        # 识别列：U_S1(标准表读数V), U_O1(改装表读数V)
        us_col = [c for c in cols if 'U_S' in c or '标准' in c or 'standard' in c.lower()][0] if any('U_S' in c or '标准' in c or 'standard' in c.lower() for c in cols) else cols[0]
        uo_col = [c for c in cols if 'U_O' in c or '改装' in c or '实测' in c][0] if any('U_O' in c or '改装' in c or '实测' in c for c in cols) else cols[1]

        U_std = pd.to_numeric(data[us_col], errors='coerce')
        U_meas = pd.to_numeric(data[uo_col], errors='coerce')

        # 相对误差
        rel_err = abs(U_meas - U_std) / U_std.where(abs(U_std) > 1e-10, 1e-10) * 100

        # 线性拟合（校准曲线）
        res_lsm = analyse_lsm(U_std, U_meas, 'U_{std}', 'U_{meas}', 'V', 'V')

        docu=Document()
        style_doc_font(docu)

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("校准曲线线性拟合")
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.mx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.bx2))
        docu.add_paragraph()._element.append(latex_to_word(res_lsm.rx2))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=len(U_std)+1, cols=4, style='Table Grid')
        for j, h in enumerate(['U_std (V)', 'U_meas (V)', 'ΔU (V)', '相对误差 δ(%)']):
            table.rows[0].cells[j].text = h
        for i in range(len(U_std)):
            table.rows[i+1].cells[0].text = '{:.4f}'.format(U_std.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(U_meas.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(U_meas.iloc[i] - U_std.iloc[i])
            table.rows[i+1].cells[3].text = '{:.3f}'.format(rel_err.iloc[i])
        docu.add_paragraph()

        docu.add_paragraph("最大相对误差：{:.3f}%".format(rel_err.max()))
        docu.add_paragraph("平均相对误差：{:.3f}%".format(rel_err.mean()))
        docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("校准曲线 U_{meas} vs U_{std}：")
        docu.add_paragraph(res_lsm.mx)
        docu.add_paragraph(res_lsm.bx)
        docu.add_paragraph(res_lsm.rx)
        docu.add_paragraph()
        docu.add_paragraph("改装表等级评定：若最大相对误差 < 0.5% 则为 0.5 级表")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    _all = load_sample_data_numeric("exp31", "exp31_example")
    _s0 = _all
    _s1 = _all
    parameters = [
        {"id": "meter_resistance", "label": "表头内阻 Rg", "unit": "kΩ", "type": "number", "default": 1.0},
        {"id": "full_scale_current", "label": "满偏电流 Ig", "unit": "μA", "type": "number", "default": 100},
        {"id": "voltmeter_resistance", "label": "20V量程电压表内阻 RV", "unit": "kΩ", "type": "number", "default": 10000},
    ]
    return make_schema(
        (
            "本实验研究数字万用表的组成并完成多量程数字电压表的改装：① 计算各量程分压电阻"
            "并组装测试；② 测量组装表内阻；③ 测试 20 V 量程内阻对测量结果的影响并计算相对误差。"
        ),
        [
            make_table(
                "table1", "多量程直流数字电压表电路参数表",
                ["电压量程 U(mV/V)", "分压电阻 Rs(kΩ/MΩ)", "组装表内阻Rg(kΩ/MΩ)"],
                sample=_s0,
                readonly=(1, 2), initial_rows=5,
            ),
            make_table(
                "table2", "20V量程电压表内阻影响测试表",
                ["Rs(kΩ/MΩ)", "Us1(V)", "Uo1(V)", "相对误差 δ(%)"],
                sample=_s1,
                readonly=(2, 3), initial_rows=3,
            ),
        ],
        parameters=parameters,
        analysis_hints="这些数据主要来自确定性电路计算，不宜机械使用3σ准则；应检查量程、单位、阻值正性和电压表内阻引起的系统误差。",
        preview_enabled=True,
        table_theory=get_table_theory("exp31"), report_enabled=False,)


def preview(payload):
    parameters = payload.get("parameters") or {}
    rg = as_number(parameters.get("meter_resistance"))
    ig = as_number(parameters.get("full_scale_current"))
    rv = as_number(parameters.get("voltmeter_resistance"))
    rg = 1.0 if rg is None else rg
    ig = 100.0 if ig is None else ig
    rv = 10000.0 if rv is None else rv
    tables = copied_tables(payload)
    for row in tables.get("table1", []):
        voltage_range = as_number(row.get("c0"))
        resistance = voltage_range / ig - rg if voltage_range is not None and ig != 0 else None
        row["c1"] = formatted(resistance, 4)
        row["c2"] = formatted(rg, 4)
    for row in tables.get("table2", []):
        rs, source = as_number(row.get("c0")), as_number(row.get("c1"))
        denominator = rs + rv if rs is not None else None
        row["c2"] = formatted(source * rv / denominator if source is not None and denominator not in (None, 0) else None, 5)
        row["c3"] = formatted(rs / denominator * 100 if rs is not None and denominator not in (None, 0) else None, 4)
    return {"tables": tables}


def handle_structured(workpath, payload):
    enriched = dict(payload)
    enriched["tables"] = preview(payload)["tables"]
    return structured_result(
        workpath, name(), schema(), enriched,
        summary=["分压电阻、组装表内阻及电压表内阻影响已由模块后端计算。"],
    )
