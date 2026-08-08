"""
B同学实验模块适配器
===================
将B同学的 Flask 式实验模块（name() + handle()）包装为新插件系统的格式，
让 AI 助教可以调用所有 B 同学已完成的实验。

工作原理：
1. 扫描 b_modules/ 目录，导入所有 exp*.py 模块
2. 为每个模块创建一个 ExperimentPlugin 适配器
3. AI 说"做XX实验"时，适配器接收 dict 数据 → 写入临时 CSV → 调用 B 的 handle()
4. 读取生成的 Word 文档和图表，返回给 AI
"""

import os
import sys
import importlib
import tempfile
import shutil
import traceback
import pandas as pd
from pathlib import Path

from plugins import ExperimentPlugin, PluginRegistry

# B 模块所在目录
_B_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b_modules")
_B_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b_static")
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 确保 b_modules 在 sys.path 中（这样 from head import * 才能工作）
if _B_MODULES_DIR not in sys.path:
    sys.path.insert(0, _B_MODULES_DIR)


def _discover_b_modules():
    """扫描 b_modules/ 目录，发现所有 exp*.py 模块并导入
    
    返回: dict, {模块名: 模块对象}
    """
    modules = {}
    for fname in os.listdir(_B_MODULES_DIR):
        if fname.startswith("exp") and fname.endswith(".py"):
            modname = fname[:-3]  # 去掉 .py
            try:
                # 临时切换到 b_modules 目录，以便模块内的相对路径能正常工作
                old_cwd = os.getcwd()
                os.chdir(_B_MODULES_DIR)
                mod = importlib.import_module(modname)
                os.chdir(old_cwd)
                modules[modname] = mod
            except Exception as e:
                print(f"  [警告] 无法导入 b_modules/{fname}: {e}")
    return modules


def _get_example_data(mod_name):
    """读取B模块的示例数据CSV，返回列名和示例数据"""
    csv_path = os.path.join(_B_STATIC_DIR, "experiment", mod_name)
    if not os.path.isdir(csv_path):
        return None, None
    
    # 查找示例数据文件
    for f in os.listdir(csv_path):
        if "示例数据" in f and f.endswith(".csv"):
            full_path = os.path.join(csv_path, f)
            try:
                import chardet
                with open(full_path, 'rb') as fh:
                    encode = chardet.detect(fh.read())['encoding']
                df = pd.read_csv(full_path, header=0, encoding=encode, dtype=str, keep_default_na=False)
                return list(df.columns), df.values.tolist()
            except Exception:
                return None, None
    return None, None


class BModuleAdapter(ExperimentPlugin):
    """B同学实验模块的适配器
    
    将 B 的 handle(workpath, extension) 接口适配到新的插件系统。
    """
    
    def __init__(self, mod_name, mod):
        self._mod_name = mod_name
        self._mod = mod
        self.name = mod.name()
        self.category = self._infer_category(mod_name)
        self.description = f"{self.name}（B同学模块适配）"
        self.required_fields = self._infer_fields(mod_name)
    
    @staticmethod
    def _infer_category(mod_name):
        """根据模块编号推断实验分类"""
        num = mod_name.replace("exp", "")
        # 去掉后缀字母
        base = ''.join(c for c in num if c.isdigit())
        base = int(base) if base else 0
        
        # 特殊分类映射
        _CATEGORY_MAP = {
            0: "基础工具",      # exp0a/b/c: 不确定度、最小二乘法
            1: "力学",          # 自由落体、单摆
            2: "力学",          # 表面张力
            3: "力学",          # 落球法测粘度
            4: "力学",          # 密度测量
            5: "力学",          # 杨氏模量
            6: "力学",          # 切变模量
            7: "热学",          # 固体比热
            8: "力学",          # 匀变速运动、碰撞、牛顿第二定律
            9: "声学",          # 声速测量
            10: "电磁学",       # 磁力摆
            11: "电磁学",       # 半导体温度计
            12: "电磁学",       # 示波器
            13: "电磁学",       # 整流滤波
            14: "电磁学",       # 直流电源特性
            15: "电磁学",       # 硅光电池
            16: "电磁学",       # LED
            17: "电磁学",       # 数字体温计
            18: "光学",         # 分光计
            19: "光学",         # 干涉法
            20: "光学",         # 透镜
            21: "光学",         # 显微镜
            22: "光学",         # 衍射、弹簧
            23: "近代物理",     # 光电效应
            24: "近代物理",     # 密立根油滴
            25: "综合",         # 生活中的物理
        }
        return _CATEGORY_MAP.get(base, "综合")
    
    def _infer_fields(self, mod_name):
        """从示例数据CSV推断需要的数据字段"""
        cols, _ = _get_example_data(mod_name)
        if cols:
            return cols
        return []
    
    def calculate(self, data, constants=None):
        """调用B模块的handle()处理数据
        
        data: dict, 键为列名，值为数据列表
        """
        # 创建临时工作目录
        work_dir = tempfile.mkdtemp(prefix="bmod_")
        
        try:
            # 将 dict 数据写入 CSV
            df = pd.DataFrame(data)
            csv_name = f"{self.name}.csv"
            csv_path = os.path.join(work_dir, csv_name)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # 切换到B模块目录（因为字体路径等依赖相对路径）
            old_cwd = os.getcwd()
            os.chdir(_B_MODULES_DIR)
            
            # 调用B模块的handle
            result = self._mod.handle(work_dir + os.sep, "csv")
            
            os.chdir(old_cwd)
            
            if result == 0:
                # 成功：读取生成的 Word 文档路径
                docx_path = os.path.join(work_dir, f"{self.name}.docx")
                chart_files = []
                for f in os.listdir(work_dir):
                    if f.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        chart_files.append(os.path.join(work_dir, f))
                
                return {
                    "status": "success",
                    "docx_path": docx_path if os.path.exists(docx_path) else None,
                    "chart_paths": chart_files,
                    "work_dir": work_dir,  # 保留工作目录，后续可以下载
                    "message": f"实验「{self.name}」数据处理完成，已生成报告文档。"
                }
            else:
                return {
                    "status": "error",
                    "message": f"实验「{self.name}」数据处理失败，请检查数据格式是否正确。"
                }
        except Exception as e:
            traceback.print_exc()
            os.chdir(old_cwd)
            return {
                "status": "error",
                "message": f"实验「{self.name}」处理出错：{str(e)}"
            }
    
    def generate_chart(self, data, results, save_dir):
        """从B模块的处理结果中提取图表"""
        chart_paths = results.get("chart_paths", [])
        return chart_paths
    
    def get_report_content(self, data, results):
        """从B模块的处理结果中提取报告内容"""
        status = results.get("status", "unknown")
        message = results.get("message", "")
        
        return {
            "purpose": f"本实验为「{self.name}」的数据处理。",
            "principle": "详细实验原理请参考实验指导书。",
            "steps": message,
            "final": results.get("message", "处理完成"),
            "analysis": f"数据处理状态：{status}。请查看生成的Word文档获取完整的计算过程和结果。"
        }


# ──────────────────────────────────────────────
# 自动注册所有B同学的实验模块
# ──────────────────────────────────────────────
def register_all_b_modules():
    """扫描并注册所有B同学的实验模块为插件"""
    b_modules = _discover_b_modules()
    count = 0
    
    for mod_name, mod in sorted(b_modules.items()):
        try:
            # 跳过没有实现handle的模块（如磁力摆）
            exp_name = mod.name()
            
            # 创建适配器并注册
            adapter = BModuleAdapter(mod_name, mod)
            
            # 手动注册到 PluginRegistry
            PluginRegistry._plugins[adapter.name] = adapter
            print(f"  [B模块适配] {mod_name} → 「{exp_name}」({adapter.category})")
            count += 1
        except Exception as e:
            print(f"  [警告] 无法注册 b_modules/{mod_name}: {e}")
    
    print(f"  共注册 {count} 个B同学实验模块")
    return count
