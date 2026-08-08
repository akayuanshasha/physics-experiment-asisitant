"""
B同学实验模块的入口文件
======================
自动导入所有常用库，兼容B同学原来的 `from head import *` 写法。
"""
import os
import sys
import chardet
import traceback
import pandas as pd
import math
import numpy as np
import scipy.optimize
import scipy.stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.oxml.ns import qn

# 确保项目根目录在 sys.path 中，以便 api 包可以被找到
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 字体路径：B同学的模块中使用 fname="SourceHanSansSC-Regular.otf" 引用字体
# 将其设置为绝对路径，这样无论从哪里调用都能找到
_FONT_PATH = os.path.join(_project_root, 'SourceHanSansSC-Regular.otf')
if os.path.exists(_FONT_PATH):
    matplotlib.font_manager.fontManager.addfont(_FONT_PATH)
    # 同时把它注入到全局命名空间，这样 B 的模块中 fname="SourceHanSansSC-Regular.otf" 也能工作
    os.environ.setdefault('_B_FONT_PATH', _FONT_PATH)

from api.calc import *
from api.insert import *
