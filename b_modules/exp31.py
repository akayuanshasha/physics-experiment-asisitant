from head import * # 导入万能头
from structured_support import (
    as_number, copied_tables, formatted, make_schema, make_table, structured_result,
)

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
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

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
        for j, h in enumerate(['U_std (V)', 'U_meas (V)', 'ΔU (V)', '相对误差(%)']):
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
    parameters = [
        {"id": "meter_resistance", "label": "表头内阻 Rg", "unit": "kΩ", "type": "number", "default": 1.0},
        {"id": "full_scale_current", "label": "满偏电流 Ig", "unit": "μA", "type": "number", "default": 100},
        {"id": "voltmeter_resistance", "label": "20V量程电压表内阻 RV", "unit": "kΩ", "type": "number", "default": 10000},
    ]
    return make_schema(
        "多量程直流数字电压表组装与测试（双数据表）",
        [
            make_table(
                "table1", "多量程直流数字电压表电路参数表",
                ["电压量程(mV/V)", "分压电阻阻值(kΩ/MΩ)", "组装表内阻Rg(kΩ/MΩ)"],
                sample=[[200, "", ""], [2000, "", ""], [20000, "", ""], [200000, "", ""], [2000000, "", ""]],
                readonly=(1, 2), initial_rows=5,
            ),
            make_table(
                "table2", "20V量程电压表内阻影响测试表",
                ["Rs(kΩ/MΩ)", "Us1(V)", "Uo1(V)", "相对误差(%)"],
                sample=[[1, 10.00, 9.98, ""], [10, 10.00, 9.90, ""], [100, 10.00, 9.10, ""]],
                readonly=(2, 3), initial_rows=3,
            ),
        ],
        parameters=parameters,
        analysis_hints="这些数据主要来自确定性电路计算，不宜机械使用3σ准则；应检查量程、单位、阻值正性和电压表内阻引起的系统误差。",
        preview_enabled=True,
    )


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
