from head import * # 导入万能头

def name(): # 返回实验名称
    return "LED的发光强度特性"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["RI","RU","GI","GU","BI","BU"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["RI","RU","GI","GU","BI","BU"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        fig, ax = plt.subplots()  # 新建绘图对象

        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        # 设置副刻度为主刻度的一半

        ax.plot(data["RI"], data["RU"], color='r', linewidth=1.5, marker="o", markersize=3, label = "R")
        ax.plot(data["GI"], data["GU"], color='g', linewidth=1.5, marker="o", markersize=3, label = "G")
        ax.plot(data["BI"], data["BU"], color='b', linewidth=1.5, marker="o", markersize=3, label = "B")
        ax.legend()
        # 作图，详见 https://www.runoob.com/matplotlib/matplotlib-marker.html 和 https://www.runoob.com/matplotlib/matplotlib-line.html
        ax.set_title("LED发光强度曲线", fontproperties=zhfont) # 若有中文，需加fontproperties=zhfont
        ax.set_xlabel("电流I/mA", fontproperties=zhfont)
        ax.set_ylabel("相对光强L（光电池电压U/mV）", fontproperties=zhfont)
        # 添加标题和轴标签，详见 https://www.runoob.com/matplotlib/matplotlib-label.html

        imgpath=workpath+"img.jpg"
        fig.savefig(imgpath, dpi=300, bbox_inches='tight')
        plt.close()

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_picture(imgpath)

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致

        os.remove(imgpath) # 删除刚才保存的图像

        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1

from structured_support import handle_legacy_single_table, make_schema, make_table


def schema():
    """本实验唯一的前端输入结构与示例数据来源。"""
    return make_schema(
        "LED的发光强度特性的数据输入与处理。",
        [make_table(
            "table1",
            "LED的发光强度特性数据",
            ["R: I/mA","U/mV","G: I/mA","U/mV","B: I/mA","U/mV"],
            sample=[["0.9","0.94","1.1","1.14","1.3","1.69"],["1.9","1.18","3.2","1.8","2.7","2.17"],["3.3","1.6","5.7","2.62","4.8","4.74"],["5.1","3","9.3","4.13","7.6","7.62"],["9.5","4.18","14.7","5.97","14","13.15"],["13","5.26","21.4","7.61","21.7","20.1"],["19.7","8.51","27.3","9.28","30.1","28.93"],["30","13.2","34.5","11.46","40.1","39.1"],["39.1","17.69","44.5","14.17","51.3","49.3"],["49.6","22.1","54.8","16.74","63.7","60.98"],["61.2","28.02","65.9","19.47","79.5","78.4"],["78.4","35.04","74.2","21.28","86.9","85.84"],["89.9","40.7","92.1","26.12","95.2","94.34"]],
            text_columns=[],
        )],
        analysis_hints="按实验指导检查数据完整性，并调用本模块原有计算流程生成结果。",
    )


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
