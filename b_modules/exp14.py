from head import * # 导入万能头

def name(): # 返回实验名称
    return "直流电源特性"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["R", "U_DC", "U_AC"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["R", "U_DC", "U_AC"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        data["P"] = data["U_DC"]*data["U_DC"]/data["R"]*1000
        data["K"] = data["U_AC"]/data["U_DC"]

        fig, ax = plt.subplots()  # 新建绘图对象
        fig_P, ax_P = fig, ax
        ax_P.plot(data["R"], data["P"], "o", color='r', markersize=3)
        ax_P.plot(data["R"], data["P"], color='b', linewidth=1.5)
        ax_P.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax_P.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax_P.set_title("输出功率和负载 $P$–$R$ 曲线", fontproperties=zhfont)
        ax_P.set_xlabel("Load Resistance ($\Omega$)")
        ax_P.set_ylabel("Output Power (mW)")

        imgpath_P=workpath+"Power.jpg"
        fig_P.savefig(imgpath_P, dpi=300, bbox_inches='tight')
        plt.close()

        fig, ax = plt.subplots()  # 新建绘图对象
        fig_K, ax_K = fig, ax
        ax_K.plot(data["R"], data["K"], "o", color='r', markersize=3)
        ax_K.plot(data["R"], data["K"], color='b', linewidth=1.5)
        ax_K.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax_K.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax_K.set_title("纹波系数和负载 $K$–$R$ 曲线", fontproperties=zhfont)
        ax_K.set_xlabel("Load Resistance ($\Omega$)")
        ax_K.set_ylabel("Ripple Factor")

        imgpath_K=workpath+"ripple.jpg"
        fig_K.savefig(imgpath_K, dpi=300, bbox_inches='tight')
        plt.close()

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        docu.add_paragraph("【本文档不只有一页，请向下翻阅】")
        docu.add_paragraph()
        docu.add_paragraph("输出功率：")
        docu.add_picture(imgpath_P)
        docu.add_paragraph()
        docu.add_paragraph("纹波系数：")
        docu.add_picture(imgpath_K)

        docu.save(workpath+name()+".docx")

        os.remove(imgpath_P)
        os.remove(imgpath_K)

        return 0
    except:
        traceback.print_exc() # 打印错误
        return 1

from structured_support import handle_legacy_single_table, make_schema, make_table


def schema():
    """本实验唯一的前端输入结构与示例数据来源。"""
    return make_schema(
        "直流电源特性的数据输入与处理。",
        [make_table(
            "table1",
            "直流电源特性数据",
            ["R/Ω","U_DC/V","U_AC/V"],
            sample=[["20","0.0376","0.01629"],["100","0.17918","0.06724"],["300","0.4889","0.123"],["500","0.7453","0.1356"],["700","0.9609","0.1354"],["900","1.1445","0.1317"],["1000","1.2269","0.1284"],["1100","1.3034","0.1255"],["1300","1.4421","0.1197"],["1500","1.5641","0.1142"],["1700","1.6729","0.1089"],["2000","1.8159","0.1018"]],
            text_columns=[],
        )],
        analysis_hints="按实验指导检查数据完整性，并调用本模块原有计算流程生成结果。",
    )


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
