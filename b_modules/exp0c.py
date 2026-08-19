from head import *  # 导入万能头


def name():  # 返回实验名称
    return "表达式及合成不确定度计算"


def handle(workpath, extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        excelpath = workpath+name()+'.'+extension  # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension == 'csv':
            with open(excelpath, 'rb') as f:
                encode = chardet.detect(f.read())["encoding"]  # 判断编码格式
            data = pd.read_csv(excelpath, header=0, names=["exp", "varr", "varr_val", "varr_unc", "constt", "constt_val", "unit", "confidence_P"], encoding=encode)  # 读取csv文件
        else:
            data = pd.read_excel(excelpath, header=0, names=["exp", "varr", "varr_val", "varr_unc", "constt", "constt_val", "unit", "confidence_P"])  # 读取xls/xlsx文件

        os.remove(excelpath)  # 读取Excel数据后删除文件

        data["exp"][0] = data["exp"][0].replace("^", "**")
        symbol = data["exp"][0][:data["exp"][0].find('=')]
        varr = tuple((data["varr"][i], float(data["varr_val"][i]), float(data["varr_unc"][i])) for i in range(len(data["varr"].dropna())))
        constt = tuple((data["constt"][i], float(data["constt_val"][i])) for i in range(len(data["constt"].dropna())))
        res = analyse_com(data["exp"][0], varr, constt, data["unit"][0], float(data["confidence_P"][0]))

        docu = Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')  # 设置Word文档字体

        docu.add_paragraph(name())  # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        insert_data_com(docu, symbol, res, "word")

        docu.add_paragraph("【Latex代码】")
        insert_data_com(docu, symbol, res, "latex")

        docu.save(workpath+name()+".docx")  # 保存Word文档，注意文件名必须与name()函数返回值一致

        return 0  # 若成功，返回0
    except:
        traceback.print_exc()  # 打印错误
        return 1  # 若失败，返回1

from structured_support import handle_legacy_single_table, make_schema, make_table


def schema():
    """本实验唯一的前端输入结构与示例数据来源。"""
    return make_schema(
        "表达式及合成不确定度计算的数据输入与处理。",
        [make_table(
            "table1",
            "表达式及合成不确定度计算数据",
            ["表达式","变量符号","变量对应值","变量对应不确定度","常量符号","常量对应值","运算结果的单位","置信概率P"],
            sample=[["k=a*(b^2+c)","a","0.6976","0.0021","c","1.567","m/s^2","0.95"],["","b","1.677","0.0064","","","",""]],
            text_columns=[0,1,4,6],
        )],
        analysis_hints="按实验指导检查数据完整性，并调用本模块原有计算流程生成结果。",
    )


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
