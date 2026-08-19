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
            old_cwd = os.getcwd()
            try:
                # 临时切换到 b_modules 目录，以便模块内的相对路径能正常工作
                os.chdir(_B_MODULES_DIR)
                mod = importlib.import_module(modname)
                modules[modname] = mod
            except Exception as e:
                print(f"  [警告] 无法导入 b_modules/{fname}: {e}")
            finally:
                os.chdir(old_cwd)
    return modules


class BModuleAdapter(ExperimentPlugin):
    """B同学实验模块的适配器
    
    将 B 的 handle(workpath, extension) 接口适配到新的插件系统。
    """
    
    def __init__(self, mod_name, mod):
        self._mod_name = mod_name
        self._mod = mod
        display_name = getattr(mod, "display_name", None)
        self.name = display_name() if callable(display_name) else mod.name()
        self.category = self._infer_category(mod_name)
        self.description = f"{self.name}（B同学模块适配）"
        self.required_fields = self._infer_fields()
    
    @staticmethod
    def _infer_category(mod_name):
        """根据模块编号推断实验分类"""
        num = mod_name.replace("exp", "")
        # 去掉后缀字母
        base = ''.join(c for c in num if c.isdigit())
        base = int(base) if base else 0
        
        # 分类映射（一级实验 + 二级实验）
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
            # ── 二级大物实验 ──
            26: "电磁学",       # 磁阻效应
            27: "电磁学",       # 非平衡电桥
            28: "电磁学",       # 霍尔效应
            29: "电磁学",       # 交流谐振电路
            30: "电磁学",       # 介电常数
            31: "电磁学",       # 数字表改装
            32: "电磁学",       # 双臂电桥
            33: "光学",         # 对切透镜的光学实验
            34: "光学",         # 光纤传感器
            35: "光学",         # 迈氏干涉仪
            36: "光学",         # 偏振光
            37: "光学",         # 摄谱/单色仪
            38: "光学",         # 双光栅实验
            39: "近代物理",     # F-H实验
            40: "力学",         # 杨氏模量及泊松比
            41: "力学",         # 超声光栅
            42: "力学",         # 超声定位与形貌成像
            43: "力学",         # 刚体转动惯量
            44: "力学",         # 凯特摆
            45: "力学",         # 空气阻尼测定实验
            46: "热学",         # 导热系数
            47: "热学",         # 接触角仪
            48: "综合",         # 传感器
            49: "综合",         # 电子小制作
            50: "综合",         # 医学物理实验
        }
        subject = _CATEGORY_MAP.get(base, "综合")
        if base == 0:
            return "基础工具"
        level = "一级" if base <= 25 else "二级"
        return f"{level}-{subject}"
    
    def _infer_fields(self):
        """从模块自己的 schema 汇总字段，不再读取静态示例 CSV。"""
        schema_factory = getattr(self._mod, "schema", None)
        if not callable(schema_factory):
            return []
        schema = schema_factory()
        return [
            column.get("label", column.get("id", ""))
            for table in schema.get("tables", [])
            for column in table.get("columns", [])
        ]
    
    def calculate(self, data, constants=None):
        """调用B模块的handle()处理数据
        
        data: dict, 键为列名，值为数据列表
        """
        # 创建临时工作目录
        work_dir = tempfile.mkdtemp(prefix="bmod_")
        old_cwd = os.getcwd()
        
        try:
            # 将 dict 数据写入 CSV
            df = pd.DataFrame(data)
            csv_name = f"{self.name}.csv"
            csv_path = os.path.join(work_dir, csv_name)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # 切换到B模块目录（因为字体路径等依赖相对路径）
            os.chdir(_B_MODULES_DIR)
            
            # 调用B模块的handle
            result = self._mod.handle(work_dir + os.sep, "csv")
            
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
            return {
                "status": "error",
                "message": f"实验「{self.name}」处理出错：{str(e)}"
            }
        finally:
            os.chdir(old_cwd)
    
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
# 自动注册所有实验模块
# ──────────────────────────────────────────────
def register_all_b_modules():
    """扫描并注册所有 ``b_modules/expXX.py`` 实验模块。"""
    b_modules = _discover_b_modules()
    count = 0
    
    for mod_name, mod in sorted(b_modules.items()):
        try:
            # 创建适配器并注册
            adapter = BModuleAdapter(mod_name, mod)
            
            # 手动注册到 PluginRegistry
            PluginRegistry._plugins[adapter.name] = adapter
            print(f"  [B模块适配] {mod_name} → 「{adapter.name}」({adapter.category})")
            count += 1
        except Exception as e:
            print(f"  [警告] 无法注册 b_modules/{mod_name}: {e}")
    
    print(f"  共注册 {count} 个实验模块")
    return count
