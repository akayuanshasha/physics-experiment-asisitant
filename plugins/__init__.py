"""
插件基类与注册中心 —— 整个项目的心脏
==============================

这个文件定义了"一个实验插件长什么样"（ExperimentPlugin），
以及"所有插件的花名册在哪里"（PluginRegistry）。

B同学写的每个实验插件都继承 ExperimentPlugin，
然后在定义类时用 @PluginRegistry.register 注册。
"""

class ExperimentPlugin:
    """实验插件的基类 —— 所有物理实验的"模板"

    任何一个物理实验都可以拆成三个步骤：
    1. calculate  — 处理原始数据 → 返回计算结果
    2. generate_chart — 根据数据+结果 → 生成图表
    3. get_report_content — 根据数据+结果 → 返回报告内容

    B同学写插件时只需要覆盖这三个方法，其他事情由框架处理。
    """
    name = ""               # 实验名称，如 "杨氏模量（拉伸法）"
    category = ""           # 分类，如 "力学"、"电磁学"
    description = ""        # 简短描述
    required_fields = []    # 这个实验需要用户提供哪些数据项的名称列表

    def calculate(self, data, constants=None):
        """处理数据 → 返回计算结果

        参数:
            data: dict, 用户输入的原始数据
                  e.g. {"钢丝直径(mm)": [0.495, 0.497, ...]}
            constants: dict, 物理常数（可选）
                       e.g. {"标距(cm)": 50.0}
        返回:
            dict, 包含计算结果，格式如下：
            {
                "final": {"杨氏模量 E": "(2.01e11 ± 4.3e9) Pa", ...},
                "steps": {"直径平均值": "0.4964 mm", ...}
            }
        """
        raise NotImplementedError("子类必须实现 calculate 方法")

    def generate_chart(self, data, results, save_dir):
        """生成图表 → 返回图表文件路径列表

        参数:
            data: dict, 原始数据
            results: dict, calculate 返回的结果
            save_dir: str, 图表保存目录
        返回:
            list, 生成的图片路径列表 e.g. ["outputs/charts/young_modulus.png"]
        """
        raise NotImplementedError("子类必须实现 generate_chart 方法")

    def get_report_content(self, data, results):
        """生成报告各章节内容 → 返回字典

        返回:
            dict, 包含 "purpose"/"principle"/"steps"/"final"/"analysis" 等键
        """
        raise NotImplementedError("子类必须实现 get_report_content 方法")


class PluginRegistry:
    """插件注册中心 —— 所有实验插件的"花名册"

    工作原理：
    - B同学写完插件用 @PluginRegistry.register 装饰器注册
    - 注册中心把它记在 _plugins 字典里
    - 系统启动时，AI 问"有哪些实验可用？"注册中心告诉 AI
    - 用户说"我要做杨氏模量"，注册中心把杨氏模量插件交给 AI
    """
    _plugins = {}  # "花名册"，格式: {插件名字(str): 插件对象(ExperimentPlugin子类)}

    @classmethod
    def register(cls, plugin):
        """装饰器：把插件写进花名册

        用法: @PluginRegistry.register 放在类定义前面
        等价于 PluginRegistry.register(YoungModulus)
        """
        cls._plugins[plugin.name] = plugin
        print(f"[注册中心] 插件已注册: {plugin.name} ({plugin.category})")
        return plugin

    @classmethod
    def get(cls, name):
        """获取插件 —— 从花名册里按名字查找"""
        return cls._plugins.get(name)

    @classmethod
    def list_all(cls):
        """列出所有已注册的插件名字"""
        return list(cls._plugins.keys())

    @classmethod
    def get_by_category(cls, category):
        """按分类查找插件"""
        return [p for p in cls._plugins.values() if p.category == category]