from head import * # 导入万能头

def name(): # 返回实验名称
    return "固体比热"

def schema():
    from theory_content import get_formulas, get_variables, get_table_theory
    return {
        "schema_version": 2,
        "report_enabled": False,
        "description": "混合法测定固体比热容",
        "parameters": [],
        "tables": [],
        "formulas": get_formulas("exp7"),
        "variables": get_variables("exp7"),
        "table_theory": get_table_theory("exp7"),
    }


def handle(workpath,extension):
    # 处理数据并生成文档，workpath为工作文件夹路径（本程序涉及到的所有文件只能保存在此文件夹内），extension为扩展名（csv/xls/xlsx）
    return 1 # 若失败，返回1