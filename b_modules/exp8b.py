from head import * # 导入万能头

def name(): # 返回实验名称
    return "研究三种碰撞状态下的守恒定律"

def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    try:
        zhfont = matplotlib.font_manager.FontProperties(fname="SourceHanSansSC-Regular.otf") # 设置图像中的文字字体

        excelpath=workpath+name()+'.'+extension # Excel文件名（含路径），文件名与name()函数返回值一致

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"] # 判断编码格式
            data=pd.read_csv(excelpath, header=0, names=["b","t10","t1","t2"], encoding=encode) # 读取csv文件
        else:
            data=pd.read_excel(excelpath, header=0, names=["b","t10","t1","t2"]) # 读取xls/xlsx文件

        os.remove(excelpath) # 读取Excel数据后删除文件

        m1=float(data["b"][0])
        m2=float(data["b"][2])
        delta_s=float(data["b"][4])
        data.dropna(inplace = True)
        data["v10"]=delta_s/data["t10"]
        data["v1"]=delta_s/data["t1"]
        data["v2"]=delta_s/data["t2"]
        data["Δp/p"]=1-(m1*data["v1"]+m2*data["v2"])/(m1*data["v10"])
        data["ΔE/E"]=1-(m1*data["v1"]**2+m2*data["v2"]**2)/(m1*data["v10"]**2)
        data["e"]=(data["v2"]-data["v1"])/data["v10"]

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑') # 设置Word文档字体

        docu.add_paragraph(name()) # 在Word文档中添加文字
        docu.add_paragraph()
        table = docu.add_table(rows=len(data["v10"])+1, cols=7, style="Table Grid") # 在Word文档中插入表格
        table.cell(0,0).text = '序号'
        table.cell(0,1).text = 'v10(m/s)'
        table.cell(0,2).text = 'v1(m/s)'
        table.cell(0,3).text = 'v2(m/s)'
        table.cell(0,4).text = 'Δp/p'
        table.cell(0,5).text = 'ΔE/E'
        table.cell(0,6).text = 'e'
        for i in range(len(data["v10"])):
            table.cell(i+1,0).text = str(i)
            table.cell(i+1,1).text = ('%.4f' % data["v10"][i])
            table.cell(i+1,2).text = ('%.4f' % data["v1"][i])
            table.cell(i+1,3).text = ('%.4f' % data["v2"][i])
            table.cell(i+1,4).text = ('%.4f' % data["Δp/p"][i])
            table.cell(i+1,5).text = ('%.4f' % data["ΔE/E"][i])
            table.cell(i+1,6).text = ('%.4f' % data["e"][i])

        docu.save(workpath+name()+".docx") # 保存Word文档，注意文件名必须与name()函数返回值一致
    
        return 0 # 若成功，返回0
    except:
        traceback.print_exc() # 打印错误
        return 1 # 若失败，返回1

from structured_support import handle_legacy_single_table, make_schema, make_table


def schema():
    """本实验唯一的前端输入结构与示例数据来源。"""
    return make_schema(
        "研究三种碰撞状态下的守恒定律的数据输入与处理。",
        [make_table("table1", "研究三种碰撞状态下的守恒定律数据", ["m1/g","Δt10/ms","Δt1/ms","Δt2/ms"],
                    sample=[["329.8","158.51","385.99","152.23"],["m2/g","162.13","347.34","175.15"],["174","154.83","364.93","157.37"],["挡光宽度Δs/mm","162.09","419.08","154.63"],["4.993","155.93","385.49","149.66"]], text_columns=[0])],
        analysis_hints="按实验指导检查数据完整性，并调用本模块原有计算流程生成结果。",
    )


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
