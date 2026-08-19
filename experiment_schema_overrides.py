"""旧插件 schema 的通用兼容默认值。

具体实验的表格、示例数据、只读列和绘图关系均应由对应 ``expXX.py``
声明；本文件不得再保存实验编号分支。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any



def apply_schema_overrides(experiment_id: str, raw_schema: dict[str, Any]) -> dict[str, Any]:
    """返回经实验级配置增强后的 schema，不修改插件类上的原对象。"""

    schema = deepcopy(raw_schema)
    schema.setdefault("schema_revision", 2)
    schema.setdefault("draft_enabled", True)
    schema.setdefault("report_enabled", True)

    return schema
