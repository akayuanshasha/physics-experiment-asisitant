from head import * # 导入万能头
from scipy.signal import savgol_filter # 数据平滑去噪

def name(): # 返回实验名称
    return "光电效应测伏安特性曲线"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["U_365","I_365","U_405","I_405","U_436","I_436","U_546","I_546","U_577","I_577"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["U_365","I_365","U_405","I_405","U_436","I_436","U_546","I_546","U_577","I_577"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        fig, ax = plt.subplots()  # 新建绘图对象
        ax.plot(data["U_365"], data["I_365"], "o", color='b', markersize=3)
        data["I_365"] = savgol_filter(data["I_365"], 7, 4)
        ax.plot(data["U_365"], data["I_365"], color='b', markersize=1.5, label="λ=365.0nm")
        ax.plot(data["U_405"], data["I_405"], "s", color='r', markersize=3)
        data["I_405"] = savgol_filter(data["I_405"], 7, 4)
        ax.plot(data["U_405"], data["I_405"], color='r', markersize=1.5, label="λ=404.7nm")
        ax.plot(data["U_436"], data["I_436"], "^", color='g', markersize=3)
        data["I_436"] = savgol_filter(data["I_436"], 7, 4)
        ax.plot(data["U_436"], data["I_436"], color='g', markersize=1.5, label="λ=435.8nm")
        ax.plot(data["U_546"], data["I_546"], "D", color='m', markersize=3)
        data["I_546"] = savgol_filter(data["I_546"], 7, 4)
        ax.plot(data["U_546"], data["I_546"], color='m', markersize=1.5, label="λ=546.1nm")
        ax.plot(data["U_577"], data["I_577"], "v", color='orange', markersize=3)
        data["I_577"] = savgol_filter(data["I_577"], 7, 4)
        ax.plot(data["U_577"], data["I_577"], color='orange', markersize=1.5, label="λ=577.0nm")
        ax.legend()
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(5))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(5))

        ax.set_title("光电管的伏安特性曲线", fontproperties=zhfont)
        ax.set_xlabel("Collector Voltage (V)")
        ax.set_ylabel("Current in Phototube (nA)")

        imgpath=workpath+"1.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

        docu.add_paragraph("光电管的伏安特性曲线：")
        docu.add_picture(imgpath)
        docu.add_paragraph("从上图中观察出5条曲线的拐点，记录其对应的电压与电流，再利用“近代：光电效应测普朗克常量”实验工具即可获得用“拐点法”测得的普朗克常数。")

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        os.remove(imgpath)

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1

from structured_support import handle_legacy_single_table, make_schema, make_table


def schema():
    """本实验唯一的前端输入结构与示例数据来源。"""
    return make_schema(
        "光电效应测伏安特性曲线的数据输入与处理。",
        [make_table("table1", "光电效应测伏安特性曲线数据", ["U_365/V","I_365/nA","U_405/V","I_405/nA","U_436/V","I_436/nA","U_546/V","I_546/nA","U_577/V","I_577/nA"],
                    sample=[["-1.9","-0.0025","-1.9","-0.0016","-1.9","-0.0031","-1.9","-0.0003","-1.9","-0.0002"],["-1.8","-0.0016","-1.8","-0.0014","-1.8","-0.003","-1.8","-0.0003","-1.8","-0.0002"],["-1.7","-0.0002","-1.7","-0.0012","-1.7","-0.0029","-1.7","-0.0003","-1.7","-0.0002"],["-1.6","0.0041","-1.6","-0.0007","-1.6","-0.0028","-1.6","-0.0003","-1.6","-0.0002"],["-1.5","0.0101","-1.5","0","-1.5","-0.0026","-1.5","-0.0003","-1.5","-0.0002"],["-1.4","0.019","-1.4","0.0013","-1.4","-0.0023","-1.4","-0.0003","-1.4","-0.0002"],["-1.3","0.0302","-1.3","0.0038","-1.3","-0.0017","-1.3","-0.0003","-1.3","-0.0002"],["-1.2","0.0412","-1.2","0.0085","-1.2","0.0001","-1.2","-0.0003","-1.2","-0.0002"],["-1.1","0.0518","-1.1","0.0149","-1.1","0.0049","-1.1","-0.0003","-1.1","-0.0002"],["-1","0.0628","-1","0.0219","-1","0.016","-1","-0.0003","-1","-0.0002"],["-0.9","0.0722","-0.9","0.029","-0.9","0.0303","-0.9","-0.0002","-0.9","-0.0002"],["-0.8","0.0817","-0.8","0.0362","-0.8","0.0476","-0.8","-0.0002","-0.8","-0.0001"],["-0.7","0.0917","-0.7","0.0438","-0.7","0.063","-0.7","-0.0001","-0.7","-0.0001"],["-0.6","0.1022","-0.6","0.0511","-0.6","0.0778","-0.6","0.0006","-0.6","0"],["-0.5","0.1123","-0.5","0.059","-0.5","0.0912","-0.5","0.0024","-0.5","0.0003"],["-0.4","0.122","-0.4","0.0672","-0.4","0.1047","-0.4","0.0049","-0.4","0.0015"],["-0.3","0.1336","-0.3","0.0749","-0.3","0.1197","-0.3","0.0076","-0.3","0.0033"],["-0.2","0.147","-0.2","0.0832","-0.2","0.1343","-0.2","0.01","-0.2","0.0052"],["-0.1","0.1592","-0.1","0.092","-0.1","0.1466","-0.1","0.0124","-0.1","0.0066"],["0","0.17","0","0.1","0","0.16","0","0.02","0","0.009"]])],
        analysis_hints="按实验指导检查数据完整性，并调用本模块原有计算流程生成结果。",
    )


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
