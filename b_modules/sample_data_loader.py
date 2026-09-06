
"""
示例数据加载工具
从 b_static/experiment/expN/ 文件夹中读取CSV文件作为示例数据
"""

import os
import pandas as pd
import chardet


def _detect_encoding(file_path):
    """检测文件编码"""
    with open(file_path, 'rb') as f:
        raw = f.read(10000)  # 读取前10KB
    result = chardet.detect(raw)
    enc = result.get('encoding', 'utf-8')
    # 常见编码修正
    if enc and enc.lower() in ('big5', 'cp949'):
        enc = 'gb18030'  # 中文Windows常用编码
    return enc or 'utf-8'


def _find_csv(experiment_dir, csv_file_pattern):
    """在实验文件夹中查找匹配的CSV文件"""
    csv_filename = f"{csv_file_pattern}（示例数据）.csv"
    csv_path = os.path.join(experiment_dir, csv_filename)
    if os.path.exists(csv_path):
        return csv_path
    return None


def load_sample_data(exp_folder_name, csv_file_pattern):
    """
    从实验文件夹加载示例数据
    
    参数:
        exp_folder_name: 实验文件夹名称，如 "exp2", "exp9"
        csv_file_pattern: CSV文件名（不含"（示例数据）.csv"后缀）
    
    返回:
        list of lists: 示例数据，每行是一个列表
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    experiment_dir = os.path.join(base_dir, "b_static", "experiment", exp_folder_name)
    
    if not os.path.exists(experiment_dir):
        print(f"警告: 实验文件夹不存在: {experiment_dir}")
        return []
    
    csv_path = _find_csv(experiment_dir, csv_file_pattern)
    if csv_path is None:
        print(f"警告: 示例数据文件不存在: {exp_folder_name}/{csv_file_pattern}（示例数据）.csv")
        return []
    
    try:
        enc = _detect_encoding(csv_path)
        df = pd.read_csv(csv_path, encoding=enc)
        
        sample_data = []
        for _, row in df.iterrows():
            row_data = [str(val) if pd.notna(val) else "" for val in row]
            # 跳过全空行
            if any(cell.strip() for cell in row_data):
                sample_data.append(row_data)
        
        return sample_data
    
    except Exception as e:
        print(f"错误: 读取示例数据失败 {csv_path}: {e}")
        return []


def load_sample_data_numeric(exp_folder_name, csv_file_pattern):
    """
    加载示例数据并尝试转换为数值类型（适用于二级实验）
    
    返回:
        list of lists: 数值型示例数据
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    experiment_dir = os.path.join(base_dir, "b_static", "experiment", exp_folder_name)
    
    if not os.path.exists(experiment_dir):
        return []
    
    csv_filename = f"{csv_file_pattern}.csv"
    csv_path = os.path.join(experiment_dir, csv_filename)
    
    if not os.path.exists(csv_path):
        return []
    
    try:
        enc = _detect_encoding(csv_path)
        df = pd.read_csv(csv_path, encoding=enc)
        
        sample_data = []
        for _, row in df.iterrows():
            row_data = []
            for val in row:
                if pd.isna(val):
                    row_data.append("")
                else:
                    try:
                        num = float(val)
                        row_data.append(int(num) if num == int(num) else num)
                    except (ValueError, TypeError, OverflowError):
                        row_data.append(str(val))
            if any(cell != "" for cell in row_data):
                sample_data.append(row_data)
        
        return sample_data
    
    except Exception as e:
        print(f"错误: 读取示例数据失败 {csv_path}: {e}")
        return []


def load_all_csvs(exp_folder_name):
    """
    加载实验文件夹中所有CSV文件，返回 {csv_basename: data} 字典
    
    用于多表格模块，按CSV文件名字母顺序分配给各表格
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    experiment_dir = os.path.join(base_dir, "b_static", "experiment", exp_folder_name)
    
    if not os.path.exists(experiment_dir):
        return {}
    
    csvs = sorted([f for f in os.listdir(experiment_dir) if f.endswith('.csv')])
    result = {}
    for csv_file in csvs:
        csv_path = os.path.join(experiment_dir, csv_file)
        try:
            enc = _detect_encoding(csv_path)
            df = pd.read_csv(csv_path, encoding=enc)
            data = []
            for _, row in df.iterrows():
                row_data = [str(val) if pd.notna(val) else "" for val in row]
                if any(cell.strip() for cell in row_data):
                    data.append(row_data)
            # 去掉后缀获取基础名
            basename = csv_file.replace('（示例数据）.csv', '').replace('_example.csv', '')
            result[basename] = data
        except Exception as e:
            print(f"错误: 读取 {csv_path}: {e}")
    
    return result
