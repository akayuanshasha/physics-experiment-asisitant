"""
实验状态管理 —— AI助教的"短期记忆"
==============================
用户每说一句话，AI 就检查一下这个状态管理器，
知道"用户当前在做什么实验"、"做到哪一步了"、"已经有哪些数据了"。

状态流转:
idle → "我要做杨氏模量实验" → recording → 用户提供数据 → calculating → 自动计算 → reporting → 生成报告 → idle
"""

class ExperimentState:
    """实验状态管理 —— 让 AI 记住实验进行到哪一步了"""

    def __init__(self):
        self.clear()

    def clear(self):
        """重置所有状态 —— 开始一个新实验时调用"""
        self.experiment_name = None   # 实验名称，如 "杨氏模量（拉伸法）"
        self.step = "idle"           # 当前阶段: idle/recording/calculating/reporting
        self.data = {}                # 收集到的用户数据
        self.constants = {}           # 物理常数
        self.results = {}             # 计算结果
        self.chart_paths = []         # 图表文件路径列表
        self.report_path = None       # 报告文件路径
        self.dialog_history = []      # 对话历史
        self.required_fields_queue = []  # 待收集的数据项队列

    def to_system_prompt(self):
        """生成当前状态的摘要 —— 给 AI 看的

        AI 看到这段文字就知道"目前做到哪一步了"
        """
        data_summary_lines = []
        for k, v in self.data.items():
            data_summary_lines.append(f"  {k}: {v}")
        data_summary = "\n".join(data_summary_lines) if data_summary_lines else "  暂无"

        result_summary_lines = []
        for k, v in self.results.items():
            if isinstance(v, dict):
                sub = "; ".join(f"{sk}: {sv}" for sk, sv in v.items())
                result_summary_lines.append(f"  {k}: {sub}")
            else:
                result_summary_lines.append(f"  {k}: {v}")
        result_summary = "\n".join(result_summary_lines) if result_summary_lines else "  暂无"

        next_fields = ""
        if self.required_fields_queue:
            next_fields = f"\n- 待收集数据项：{', '.join(self.required_fields_queue)}"

        return f"""
当前实验状态：
- 实验名称：{self.experiment_name or '未设置'}
- 当前阶段：{self.step} (idle=空闲, recording=记录数据, calculating=计算中, reporting=生成报告)
- 测量数据：
{data_summary}
- 已计算结果：
{result_summary}
- 图表路径：{self.chart_paths or '暂无'}
- 报告路径：{self.report_path or '暂无'}{next_fields}

请根据当前状态引导用户完成实验。如果是在 recording 阶段，询问用户提供下一个待收集的数据项。
"""

    def add_data(self, name, values):
        """添加一组测量数据"""
        if name in self.data:
            self.data[name].extend(values)
        else:
            self.data[name] = values

        # 如果该数据项在待收集队列中，移除它
        if name in self.required_fields_queue:
            self.required_fields_queue.remove(name)

    def set_experiment(self, name, required_fields=None):
        """设置实验名称，进入 recording 阶段"""
        self.experiment_name = name
        self.step = "recording"
        if required_fields:
            self.required_fields_queue = list(required_fields)

    def to_dict(self):
        """把状态转为普通字典，方便序列化"""
        return {
            "experiment_name": self.experiment_name,
            "step": self.step,
            "data": self.data,
            "constants": self.constants,
            "results": self.results,
            "chart_paths": self.chart_paths,
            "report_path": self.report_path,
            "dialog_history": self.dialog_history[-20:],  # 只保留最近20条
            "required_fields_queue": self.required_fields_queue,
        }

    @classmethod
    def from_dict(cls, d):
        """从字典恢复状态"""
        state = cls()
        state.experiment_name = d.get("experiment_name")
        state.step = d.get("step", "idle")
        state.data = d.get("data", {})
        state.constants = d.get("constants", {})
        state.results = d.get("results", {})
        state.chart_paths = d.get("chart_paths", [])
        state.report_path = d.get("report_path")
        state.dialog_history = d.get("dialog_history", [])
        state.required_fields_queue = d.get("required_fields_queue", [])
        return state