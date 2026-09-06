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


def style_doc_font(docu):
    """统一设置 Word 文档字体为微软雅黑、加粗。

    覆盖 Normal 正文样式以及 Title / Heading 1~3 标题样式，使标题、正文、
    表格表头与单元格全部使用微软雅黑加粗。Title / Heading 默认走主题字体
    （中文宋体、西文 Calibri），不显式覆盖就会和正文不一致，故在此一并处理。
    """
    font_name = '微软雅黑'
    # Normal 正文样式：西文 + 中文（eastAsia）都设为微软雅黑
    normal = docu.styles['Normal']
    normal.font.name = font_name
    normal.font.bold = True
    rpr = normal._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = rpr.makeelement(qn('w:rFonts'), {})
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), font_name)
    # Title 与 Heading 1~3：同样统一为微软雅黑加粗（覆盖主题字体）
    for style_name in ('Title', 'Heading 1', 'Heading 2', 'Heading 3'):
        try:
            style = docu.styles[style_name]
        except KeyError:
            continue
        style.font.name = font_name
        style.font.bold = True
        s_rpr = style._element.get_or_add_rPr()
        s_rfonts = s_rpr.find(qn('w:rFonts'))
        if s_rfonts is None:
            s_rfonts = s_rpr.makeelement(qn('w:rFonts'), {})
            s_rpr.append(s_rfonts)
        s_rfonts.set(qn('w:eastAsia'), font_name)

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
