"""生成 per-table 结构的 theory_content.py"""

# 每个实验的每个表格对应的公式和物理量说明
# 结构: {exp_id: {table_id: {"formulas": [...], "variables": [...]}}}
TABLE_THEORY = {
    # ── exp0: 基础工具（不确定度计算） ──
    # exp0 没有表格，使用全局公式
    "exp0": {
    "_global": {
        "formulas": [
            {
                "title": "算术平均值与不确定度",
                "steps": [
                    {
                        "note": "对 n 次等精度测量取平均：",
                        "formula": "\\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n}x_i"
                    },
                    {
                        "note": "样本标准差（贝塞尔公式）：",
                        "formula": "s = \\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}(x_i - \\bar{x})^2}"
                    },
                    {
                        "note": "<strong>A 类不确定度</strong>：",
                        "formula": "u_A = \\frac{s}{\\sqrt{n}}"
                    },
                    {
                        "note": "<strong>合成不确定度</strong>（含 B 类仪器误差 Δ<sub>inst</sub>）：",
                        "formula": "u = \\sqrt{u_A^2 + u_B^2}, \\quad u_B = \\frac{\\Delta_{\\text{inst}}}{\\sqrt{3}}"
                    }
                ]
            },
            {
                "title": "最小二乘法线性拟合",
                "steps": [
                    {
                        "note": "对 y = a + bx 做最小二乘拟合：",
                        "formula": "b = \\frac{n\\sum x_i y_i - \\sum x_i \\sum y_i}{n\\sum x_i^2 - (\\sum x_i)^2}"
                    },
                    {
                        "note": "相关系数（衡量线性度）：",
                        "formula": "r = \\frac{n\\sum x_i y_i - \\sum x_i \\sum y_i}{\\sqrt{[n\\sum x_i^2-(\\sum x_i)^2][n\\sum y_i^2-(\\sum y_i)^2]}}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\bar{x}",
                "description": "<strong>算术平均值</strong>，n 次测量的最佳估计值",
                "unit": "与测量值相同"
            },
            {
                "symbol": "s",
                "description": "<strong>样本标准差</strong>，由贝塞尔公式计算",
                "unit": "与测量值相同"
            },
            {
                "symbol": "u_A",
                "description": "<strong>A 类不确定度</strong>，由统计方法评定",
                "unit": "与测量值相同"
            },
            {
                "symbol": "u_B",
                "description": "<strong>B 类不确定度</strong>，由仪器误差评定",
                "unit": "与测量值相同"
            },
            {
                "symbol": "r",
                "description": "<strong>相关系数</strong>，|r| 越接近 1 线性越好",
                "unit": "无单位"
            }
        ]
    },
    "table1": {
        "variables": [
            {
                "symbol": "x",
                "description": "单次测量值：直接读取的原始测量数据",
                "unit": ""
            },
            {
                "symbol": "x-\\bar{x}",
                "description": "偏差：各次测量值 x 与平均值 x̄ 之差，反映单次测量对平均值的偏离（自动计算）",
                "unit": ""
            },
            {
                "symbol": "(x-\\bar{x})^2",
                "description": "偏差平方：(x − x̄)²，其求和用于按贝塞尔公式计算标准差（自动计算）",
                "unit": ""
            }
        ]
    },
    "table2": {
        "variables": [
            {
                "symbol": "x",
                "description": "自变量：拟合数据点的横坐标（测量值）",
                "unit": ""
            },
            {
                "symbol": "y",
                "description": "因变量：拟合数据点的纵坐标（测量值）",
                "unit": ""
            },
            {
                "symbol": "y-\\hat{y}",
                "description": "残差：观测值 y 与最小二乘拟合值 ŷ 之差（自动计算）",
                "unit": ""
            }
        ]
    },
    "table3": {
        "variables": [
            {
                "symbol": "u",
                "description": "标准不确定度：A 类与 B 类不确定度的方和根合成结果",
                "unit": ""
            }
        ]
    }
},

    # ── exp1: 单摆法测重力加速度 ──
    "exp1": {
    "table1": {
        "formulas": [
            {
                "title": "单摆周期公式",
                "steps": [
                    {
                        "note": "单摆在小角度（θ < 5°）下的周期公式：",
                        "formula": "T = 2\\pi\\sqrt{\\frac{L}{g}}"
                    },
                    {
                        "note": "由此解出<strong>待求量 g</strong>：",
                        "formula": "g = \\frac{4\\pi^2 L}{T^2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "x",
                "description": "摆线长度：悬点到摆球上端细线的长度，用钢卷尺测量",
                "unit": "cm"
            },
            {
                "symbol": "d",
                "description": "摆球直径，由游标卡尺测量",
                "unit": "mm"
            },
            {
                "symbol": "l",
                "description": "实际摆长：摆线长 x 加摆球半径 d/2，即 l = x + d/20，后端自动计算",
                "unit": "cm"
            },
            {
                "symbol": "t",
                "description": "累积时间：连续 n 次全振动的总时间，用秒表测量",
                "unit": "s"
            },
            {
                "symbol": "n",
                "description": "周期数：单次测量累积的全振动次数",
                "unit": ""
            },
            {
                "symbol": "T",
                "description": "单摆周期：由累积时间 t 除以周期数 n 得到",
                "unit": "s"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "多摆长拟合求 g",
                "steps": [
                    {
                        "note": "由 T = 2π√(L/g) 两边平方得：",
                        "formula": "T^2 = \\frac{4\\pi^2}{g} L"
                    },
                    {
                        "note": "作 L-T² 图，斜率 k = 4π²/g，故：",
                        "formula": "g = \\frac{4\\pi^2}{k}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "l",
                "description": "摆长：各次实验设定的摆长（不同摆长拟合条件）",
                "unit": "cm"
            },
            {
                "symbol": "t",
                "description": "累积时间：n 次全振动的总时间，用秒表测量",
                "unit": "s"
            },
            {
                "symbol": "n",
                "description": "周期数：单次测量累积的全振动次数",
                "unit": ""
            },
            {
                "symbol": "T",
                "description": "单摆周期：由累积时间除以周期数得到",
                "unit": "s"
            },
            {
                "symbol": "T^2",
                "description": "周期平方：T² = (t/n)²，l–T² 线性拟合的自变量",
                "unit": "s²"
            }
        ]
    }
},

    # ── exp2: 表面张力 ──
    "exp2": {
    "table1": {
        "formulas": [
            {
                "title": "拉脱法测表面张力系数",
                "steps": [
                    {
                        "note": "金属环被拉脱液面时，表面张力：",
                        "formula": "F = \\alpha \\cdot \\pi(D_1 + D_2)"
                    },
                    {
                        "note": "<strong>表面张力系数</strong>：",
                        "formula": "\\alpha = \\frac{mg}{\\pi(D_1 + D_2)}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "m",
                "description": "砝码质量：挂在弹簧上的砝码质量，用于产生拉力",
                "unit": "g"
            },
            {
                "symbol": "x",
                "description": "升降杆读数：刻度尺（升降杆）上的读数，用于计算弹簧伸长量",
                "unit": "cm"
            },
            {
                "symbol": "\\Delta x",
                "description": "弹簧伸长量：Δx = x − x₀（升降杆读数与初始读数之差，自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "F",
                "description": "拉力：砝码重力产生的拉力 F = m·g（g = 9.8 m/s²）",
                "unit": "mN"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "l",
                "description": "初始读数：金属圈与液面刚接触瞬间的升降杆读数",
                "unit": "cm"
            },
            {
                "symbol": "\\bar{l}",
                "description": "破裂均值：五次破裂读数 l₁~l₅ 的平均值（自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "\\Delta F",
                "description": "拉力差：ΔF = k·(l̄−l₀)×10，k 为弹簧劲度系数（N/m），10 为 cm 折 m 的换算（自动计算）",
                "unit": "mN"
            },
            {
                "symbol": "\\sigma",
                "description": "表面张力系数：由拉力差与金属圈两脚间距计算 σ = ΔF/(2d)（自动计算）",
                "unit": "mN/m"
            }
        ]
    },
    "table3": {
        "formulas": [],
        "variables": [
            {
                "symbol": "C",
                "description": "浓度：肥皂水的百分比浓度",
                "unit": "%"
            },
            {
                "symbol": "l",
                "description": "初始读数：金属圈与液面刚接触瞬间的升降杆读数",
                "unit": "cm"
            },
            {
                "symbol": "\\bar{l}",
                "description": "破裂均值：破裂读数的平均值（自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "\\sigma",
                "description": "表面张力系数：σ = k(l̄−l₀)/(2d)，k 为劲度系数、d 为两脚间距（自动计算）",
                "unit": "mN/m"
            }
        ]
    }
},

    # ── exp3: 粘滞系数 ──
    "exp3": {
    "_global": {
        "formulas": [
            {
                "title": "落球法测粘滞系数",
                "steps": [
                    {
                        "note": "小球在粘滞液体中匀速下落时，由<strong>斯托克斯公式</strong>：",
                        "formula": "\\eta = \\frac{2r^2(\\rho - \\rho_0)g}{9v}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\eta",
                "description": "<strong>粘滞系数</strong>（待求量）",
                "unit": "Pa·s"
            },
            {
                "symbol": "r",
                "description": "小球半径，由螺旋测微器测量",
                "unit": "m"
            },
            {
                "symbol": "v",
                "description": "小球匀速下落速度，由距离/时间计算",
                "unit": "m/s"
            },
            {
                "symbol": "\\rho",
                "description": "小球密度",
                "unit": "kg/m³"
            },
            {
                "symbol": "\\rho_0",
                "description": "液体密度",
                "unit": "kg/m³"
            }
        ]
    },
    "table1": {
        "variables": [
            {
                "symbol": "h",
                "description": "液面高度：量筒内液面的起始高度位置",
                "unit": "cm"
            },
            {
                "symbol": "l",
                "description": "匀速下降区：小球匀速下落区间的长度（量筒刻度差）",
                "unit": "cm"
            },
            {
                "symbol": "D",
                "description": "量筒直径：量筒内径，用于计算量筒截面积",
                "unit": "mm"
            },
            {
                "symbol": "d",
                "description": "小球直径：实验小球的直径，用螺旋测微器测量",
                "unit": "mm"
            },
            {
                "symbol": "t",
                "description": "下落时间：小球通过匀速下降区间的用时（秒表或光电计时）",
                "unit": "s"
            },
            {
                "symbol": "v",
                "description": "速度：小球匀速下降的速度 v = l/t（自动计算）",
                "unit": "m/s"
            }
        ]
    }
},

    # ── exp4: 密度测量 ──
    "exp4": {
    "table1": {
        "formulas": [
            {
                "title": "流体静力称衡法测密度",
                "steps": [
                    {
                        "note": "固体密度：",
                        "formula": "\\rho = \\frac{m}{m - m'}\\rho_0"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "D",
                "description": "直径：圆柱体直径，用游标卡尺测量",
                "unit": "cm"
            },
            {
                "symbol": "H",
                "description": "高度：圆柱体高度，用游标卡尺测量",
                "unit": "cm"
            },
            {
                "symbol": "\\bar{D}",
                "description": "平均直径：多次测量的直径平均值（自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "\\bar{H}",
                "description": "平均高度：多次测量的高度平均值（自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "V",
                "description": "体积：圆柱体体积 V = πD̄²H̄/4（自动计算）",
                "unit": "cm³"
            },
            {
                "symbol": "m",
                "description": "质量：圆柱体的质量，用天平测量",
                "unit": "g"
            },
            {
                "symbol": "\\rho",
                "description": "几何密度：ρ₁ = m/V，由质量与体积计算（自动计算）",
                "unit": "g/cm³"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "m",
                "description": "空气中质量：圆柱体在空气中的质量，用天平测量",
                "unit": "g"
            },
            {
                "symbol": "\\Delta m",
                "description": "视质量损失：圆柱体在空气中与水中称衡的质量差（直接测量）",
                "unit": "g"
            },
            {
                "symbol": "\\rho",
                "description": "密度：水密度 ρ₀ 为标准值约 0.997 g/cm³，ρ₂ = m/Δm′·ρ₀ 为称衡法密度（自动计算）",
                "unit": "g/cm³"
            }
        ]
    },
    "table3": {
        "formulas": [],
        "variables": [
            {
                "symbol": "r",
                "description": "质心距：双小铜块质心到转轴的距离（直接测量）",
                "unit": "cm"
            },
            {
                "symbol": "t",
                "description": "30周期时间：30 次全振动的累积时间（直接测量）",
                "unit": "s"
            },
            {
                "symbol": "T",
                "description": "周期：T = t₃₀/30，一次全振动的时间（自动计算）",
                "unit": "s"
            },
            {
                "symbol": "X=r^2",
                "description": "X = r²：质心距的平方（换算为 m²），Y–X 线性拟合的自变量（自动计算）",
                "unit": "m²"
            },
            {
                "symbol": "Y_{grT^2}",
                "description": "Y = grT²/(4π²)：转动定律拟合参量（g = 9.8 m/s²），Y–X 线性拟合的因变量（自动计算）",
                "unit": "m²"
            }
        ]
    },
    "table4": {
        "formulas": [
            {
                "title": "转动定律测质量",
                "steps": [
                    {
                        "note": "由转动定律 Iβ = M，通过测量转动惯量和角加速度求质量。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "m",
                "description": "标准质量：已知质量的标准砝码（校准基准）",
                "unit": "g"
            },
            {
                "symbol": "T",
                "description": "周期：标准质量与待测物体分别对应的弹簧振子周期（直接测量）",
                "unit": "s"
            }
        ]
    }
},

    # ── exp5: 杨氏模量 ──
    "exp5": {
    "table1": {
        "formulas": [
            {
                "title": "拉伸法测杨氏模量",
                "steps": [
                    {
                        "note": "<strong>杨氏模量</strong>定义（应力/应变）：",
                        "formula": "E = \\frac{F/A}{\\Delta L / L} = \\frac{FL}{A\\,\\Delta L}"
                    },
                    {
                        "note": "用光杠杆放大微小伸长量：",
                        "formula": "\\Delta L = \\frac{b\\,\\Delta n}{2D}"
                    },
                    {
                        "note": "代入得最终公式：",
                        "formula": "E = \\frac{8FLD}{\\pi d^2 b\\,\\Delta n}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "d_i",
                "description": "钢丝直径：螺旋测微器第 i 次测量读数",
                "unit": "mm"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "b",
                "description": "标尺读数：加砝码（b₊）与减砝码（b₋）时光杠杆标尺读数",
                "unit": "cm"
            },
            {
                "symbol": "\\bar{b}",
                "description": "平均读数：同一载荷下 b₊ 与 b₋ 的平均值 b̄ = (b₊+b₋)/2（自动计算）",
                "unit": "cm"
            },
            {
                "symbol": "\\Delta b",
                "description": "读数变化量：Δb = b̄ − b̄₀，当前载荷与初始载荷的标尺读数差（自动计算）",
                "unit": "cm"
            }
        ]
    }
},

    # ── exp6: 切变模量 ──
    "exp6": {
        "_global": {
            "formulas": [
                {"title": "扭摆法测切变模量", "steps": [
                    {"note": "由空盘周期 T_0 和加环周期 T_1 消去难测的转动惯量：", "formula": r"G=\frac{16\pi Lm(D_1^2+D_2^2)}{d^4(T_1^2-T_0^2)}"},
                    {"note": "按微分法估算最大相对误差（各项取绝对值）：", "formula": r"\frac{\Delta G}{G}=\frac{\Delta L}{L}+\frac{\Delta m}{m}+\frac{2D_1\Delta D_1+2D_2\Delta D_2}{D_1^2+D_2^2}+4\frac{\Delta d}{d}+\frac{2T_1\Delta T_1+2T_0\Delta T_0}{T_1^2-T_0^2}"},
                    {"note": "累积测量 n 个周期时，计时误差被缩小为：", "formula": r"\Delta T=\frac{\Delta t}{n}"},
                    {"note": "与材料参考值比较的相对误差：", "formula": r"E_r=\frac{|G-G_{\mathrm{ref}}|}{G_{\mathrm{ref}}}\times100\%"},
                    {"note": "提升实验对不同初始扭转角求 G，并检验线性关系：", "formula": r"G(\theta)=a+b\theta\quad(b\approx0\text{ in the elastic range})"},
                ]},
            ],
            "variables": [
                {"symbol": "G", "description": "<strong>切变模量</strong>（待求量）", "unit": "Pa"},
                {"symbol": "L", "description": "圆棒长度", "unit": "m"},
                {"symbol": "d", "description": "圆棒直径", "unit": "m"},
                {"symbol": r"\theta", "description": "扭转角", "unit": "rad"},
                {"symbol": "D_1,D_2", "description": "圆环内、外直径", "unit": "m"},
                {"symbol": "m", "description": "圆环质量", "unit": "kg"},
                {"symbol": "T_0,T_1", "description": "空盘和加环后的扭摆周期", "unit": "s"},
                {"symbol": "G_{\\mathrm{ref}}", "description": "材料切变模量参考值", "unit": "Pa"},
            ],
        },
        "table1": {"description": "多次测量钢丝直径；由于 G∝d⁻⁴，直径误差会被放大，应在不同方向和位置重复测量。"},
        "table2": {"description": "保持装置参数不变，改变初始扭转角，由每组 T₀、T₁ 计算 G；拟合斜率接近 0 表明弹性限度内 G 与扭转角无关。"},
    },

    # ── exp7: 固体比热 ──
    "exp7": {
    "table1": {
        "formulas": [
            {
                "title": "混合法测固体比热容（雷诺校正）",
                "steps": [
                    {
                        "note": "热平衡方程（含温度计热容量修正）：",
                        "formula": "m_x c_x (T' - T_2) = (m c + m_1 c_1 + 1.9 V)(T_2 - T_1)"
                    },
                    {
                        "note": "锌的比热容（雷诺校正法）：",
                        "formula": "c_x = \\frac{(m c + m_1 c_1 + 1.9 V)(T_2 - T_1)}{m_x (T' - T_2)}"
                    },
                    {
                        "note": "雷诺校正（外推法）求 T₁、T₂：",
                        "formula": "T_1 = k_1 t_G + b_1, \\quad T_2 = k_2 t_G + b_2"
                    },
                    {
                        "note": "线性拟合（阶段一、三）：",
                        "formula": "k = \\frac{\\sum (t_i - \\bar{t})(T_i - \\bar{T})}{\\sum (t_i - \\bar{t})^2}, \\quad b = \\bar{T} - k\\bar{t}"
                    },
                    {
                        "note": "相对误差：",
                        "formula": "\\delta = \\frac{|c_x - c_{x,\\text{std}}|}{c_{x,\\text{std}}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "时间：冷却过程中记录的时刻（分钟）",
                "unit": "min"
            },
            {
                "symbol": "T",
                "description": "温度：冷却过程中温度计的读数",
                "unit": "°C"
            }
        ]
    },
    "table2": {
        "variables": [
            {
                "symbol": "t",
                "description": "时间：冷却过程中记录的时刻（分钟）",
                "unit": "min"
            },
            {
                "symbol": "T",
                "description": "温度：冷却过程中温度计的读数",
                "unit": "°C"
            }
        ]
    },
    "table3": {
        "variables": [
            {
                "symbol": "t",
                "description": "时间：冷却过程中记录的时刻（分钟）",
                "unit": "min"
            },
            {
                "symbol": "T",
                "description": "温度：冷却过程中温度计的读数",
                "unit": "°C"
            }
        ]
    },
    "cooling_time": {
        "variables": [
            {
                "symbol": "\\Delta t",
                "description": "冷却时间差：金属样品温度从 102 ℃ 自然冷却到 98 ℃ 所需的时间",
                "unit": "s"
            }
        ]
    }
},

    # ── exp7_b: 冷却法测金属比热容 ──
    "exp7_b": {
        "_global": {
            "formulas": [
                {"title": "冷却法测比热容", "steps": [
                    {"note": "单位时间的热量损失与温度下降速率成正比：", "formula": r"\frac{\Delta Q}{\Delta t} = C_1 M_1 \frac{\Delta\theta_1}{\Delta t}"},
                    {"note": "两样品形状、尺寸、表面状况相同，介质相同时：", "formula": r"\frac{C_2}{C_1} = \frac{M_1 (\Delta\theta/\Delta t)_2}{M_2 (\Delta\theta/\Delta t)_1}"},
                    {"note": "两样品在相同温度区间 Δθ 冷却（102 ℃→98 ℃），以时间之比表示：", "formula": r"C_2 = C_1 \frac{M_1 \Delta t_2}{M_2 \Delta t_1}"},
                    {"note": "以铜为标准样品，铁、铝的比热容：", "formula": r"C_{\text{Fe}} = C_{\text{Cu}}\frac{M_{\text{Cu}}\Delta t_{\text{Fe}}}{M_{\text{Fe}}\Delta t_{\text{Cu}}}, \quad C_{\text{Al}} = C_{\text{Cu}}\frac{M_{\text{Cu}}\Delta t_{\text{Al}}}{M_{\text{Al}}\Delta t_{\text{Cu}}}"},
                    {"note": "平均冷却时间（重复2次）：", "formula": r"\overline{\Delta t} = \frac{\Delta t_1 + \Delta t_2}{2}"},
                    {"note": "相对误差：", "formula": r"\delta = \frac{|C - C_{\text{std}}|}{C_{\text{std}}} \times 100\%"},
                ]},
            ],
            "variables": [
                {"symbol": r"C_{\text{Fe}}, C_{\text{Al}}", "description": "<strong>待测金属的比热容</strong>（待求量）", "unit": "cal/(g·℃)"},
                {"symbol": r"C_{\text{Cu}}", "description": "铜在100 ℃的标准比热容 0.0940", "unit": "cal/(g·℃)"},
                {"symbol": "M", "description": "样品质量，由天平称得", "unit": "g"},
                {"symbol": r"\Delta t", "description": "样品从102 ℃冷却到98 ℃所用时间，重复测2次", "unit": "s"},
                {"symbol": r"\overline{\Delta t}", "description": "两次测量的平均冷却时间", "unit": "s"},
                {"symbol": r"C_{\text{std}}", "description": "标准比热容（铁 0.110，铝 0.230）", "unit": "cal/(g·℃)"},
                {"symbol": r"\delta", "description": "<strong>相对误差</strong>", "unit": "%"},
            ],
        }
    },

    # ── exp8: 匀加速运动 ──
    "exp8": {
    "table1": {
        "formulas": [
            {
                "title": "光电门测瞬时速度",
                "steps": [
                    {
                        "note": "挡光宽度 Δs 很小，瞬时速度：",
                        "formula": "v = \\frac{\\Delta s}{\\Delta t}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "s",
                "description": "滑块位置：滑块在斜面上的起始位置（距光电门的位移）",
                "unit": "cm"
            },
            {
                "symbol": "t_{avg}",
                "description": "平均挡光时间：t1、t2、t3 三次挡光时间读数的平均值（自动计算）",
                "unit": "ms"
            },
            {
                "symbol": "v^2",
                "description": "速度平方：v² = (Δs/t_avg)²，v²–2s 线性拟合的纵坐标（自动计算）",
                "unit": "m²/s²"
            },
            {
                "symbol": "2s",
                "description": "两倍位移：2s（cm 换算为 m），v²–2s 线性拟合的横坐标（自动计算）",
                "unit": "m"
            },
            {
                "symbol": "t",
                "description": "挡光时间：单次测量的光电门挡光时间（t1/t2/t3 三次重复读数）",
                "unit": "ms"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "匀加速运动中速度与位移的关系",
                "steps": [
                    {
                        "note": "速度平方与位移的关系：",
                        "formula": "v^2 = 2as"
                    },
                    {
                        "note": "作 v²-2s 图，斜率即为加速度 a。",
                        "formula": "g = \\frac{aL}{h}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "m",
                "description": "悬挂质量：悬挂在细绳上的钩码质量",
                "unit": "g"
            },
            {
                "symbol": "t",
                "description": "挡光时间：第 i 次（t1/t2/t3 三次重复）光电门挡光时间读数",
                "unit": "ms"
            },
            {
                "symbol": "a",
                "description": "加速度：a = v²/(2s)，由固定位移与速度平方计算（自动计算）",
                "unit": "m/s²"
            },
            {
                "symbol": "m_{\\text{hang}}",
                "description": "悬挂质量：悬挂在细绳上的钩码质量（g 与 kg 两列分别为直接读数与换算值）",
                "unit": "g/kg"
            },
            {
                "symbol": "s",
                "description": "位移：滑块在斜面上的起始位置（距光电门的位移）",
                "unit": "cm"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "验证牛顿第二定律",
                "steps": [
                    {
                        "note": "系统总质量 M 不变，改变悬挂质量 m：",
                        "formula": "a = \\frac{m_{\\text{hang}}}{M}g"
                    }
                ]
            },
            {
                "title": "碰撞中的动量守恒",
                "steps": [
                    {
                        "note": "两物体碰撞前后动量守恒：",
                        "formula": "m_1 v_1 = m_1 v_1' + m_2 v_2'"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\Delta t",
                "description": "挡光时间：滑块通过挡光片的遮光时间（Δt10 为碰前、Δt1/Δt2 为碰后读数）",
                "unit": "ms"
            },
            {
                "symbol": "v",
                "description": "速度：碰撞前后滑块速度（v1 为碰前、v1′/v2′ 为碰后，由 Δs/Δt 自动计算）",
                "unit": "m/s"
            },
            {
                "symbol": "p_{before}",
                "description": "碰前总动量：p = m1·v1（自动计算）",
                "unit": "kg·m/s"
            },
            {
                "symbol": "p_{after}",
                "description": "碰后总动量：p = m1·v1′ + m2·v2′（自动计算）",
                "unit": "kg·m/s"
            }
        ]
    }
},

    # ── exp9: 声速测量 ──
    "exp9": {
    "table1": {
        "formulas": [
            {
                "title": "驻波法测声速",
                "steps": [
                    {
                        "note": "声速与频率、波长的关系：",
                        "formula": "v = f\\lambda"
                    },
                    {
                        "note": "由 n-L 线性拟合斜率 m 得波长：",
                        "formula": "\\lambda = 2|m|"
                    },
                    {
                        "note": "声速理论值：",
                        "formula": "v_t = 331.45\\sqrt{1 + \\frac{t}{273.15}}"
                    },
                    {
                        "note": "相对误差：",
                        "formula": "\\delta = \\frac{|v - v_t|}{v_t} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "n",
                "description": "波节序号：驻波波节的编号（n = 1,2,3,…），相邻波节间距为半波长",
                "unit": ""
            },
            {
                "symbol": "L",
                "description": "位置：第 n 个波节处接收换能器的位置读数",
                "unit": "mm"
            }
        ]
    },
    "phase_position": {
        "formulas": [
            {
                "title": "相位比较法测水中声速",
                "steps": [
                    {
                        "note": "李萨如图形斜率正、负变化的直线每移动 λ/2 重复出现：",
                        "formula": "\\lambda = 2|b_1|"
                    },
                    {
                        "note": "j-L 线性拟合：",
                        "formula": "L_j = b_0 + b_1 j"
                    },
                    {
                        "note": "水中声速：",
                        "formula": "v = f\\lambda"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "v",
                "description": "<strong>水中声速</strong>（待求量）",
                "unit": "m/s"
            },
            {
                "symbol": "f",
                "description": "谐振频率（直接测量）",
                "unit": "Hz"
            },
            {
                "symbol": "\\lambda",
                "description": "<strong>水中波长</strong>（由拟合斜率计算）",
                "unit": "cm"
            },
            {
                "symbol": "j",
                "description": "位置序号",
                "unit": "无单位"
            },
            {
                "symbol": "L",
                "description": "直线出现时 S2 的位置",
                "unit": "cm"
            },
            {
                "symbol": "b_1",
                "description": "j-L 线性拟合斜率（相邻直线间距）",
                "unit": "cm/序号"
            }
        ]
    }
},

    # ── exp10: 磁力摆 ──
    "exp10": {
    "table1": {
        "formulas": [
            {
                "title": "亥姆霍兹线圈磁场标定",
                "steps": [
                    {
                        "note": "亥姆霍兹线圈轴线中心处的磁场：",
                        "formula": "B_1 = \\left(\\frac{4}{5}\\right)^{3/2} \\frac{\\mu_0 N I}{R}"
                    },
                    {
                        "note": "实验上对 (I, B) 作线性拟合得到线圈常数：",
                        "formula": "B = kI + b_0"
                    },
                    {
                        "note": "理论线圈常数（可对比验证）：",
                        "formula": "k_{\\text{理论}} = \\left(\\frac{4}{5}\\right)^{3/2} \\frac{\\mu_0 N}{R}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "励磁电流（直接测量）",
                "unit": "A"
            },
            {
                "symbol": "B",
                "description": "线圈中心磁感应强度（特斯拉计测量）",
                "unit": "mT"
            },
            {
                "symbol": "k",
                "description": "<strong>线圈常数</strong>（拟合斜率，待求量）",
                "unit": "mT/A"
            },
            {
                "symbol": "b_0",
                "description": "拟合截距（零点偏移）",
                "unit": "mT"
            },
            {
                "symbol": "N",
                "description": "线圈匝数（参数）",
                "unit": "无单位"
            },
            {
                "symbol": "R",
                "description": "线圈半径（参数）",
                "unit": "m"
            },
            {
                "symbol": "\\mu_0",
                "description": "真空磁导率（常数 4π×10⁻⁷）",
                "unit": "T·m/A"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "磁力摆测地磁场（同向）",
                "steps": [
                    {
                        "note": "总磁场（线圈磁场与地磁场同向）：",
                        "formula": "B_{\\text{total}} = B_0 + kI"
                    },
                    {
                        "note": "磁针在合磁场中的振荡周期：",
                        "formula": "T = 2\\pi\\sqrt{\\frac{J}{mB_{\\text{total}}}}"
                    },
                    {
                        "note": "线性化（斜率为正）：",
                        "formula": "\\frac{1}{T^2} = \\frac{m}{4\\pi^2 J} (B_0 + kI) = A + bI"
                    },
                    {
                        "note": "平均周期由三次重复测量求得：",
                        "formula": "\\bar{T} = \\frac{t_1 + t_2 + t_3}{3n}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "励磁电流：本次测量设定的电流值",
                "unit": "A"
            },
            {
                "symbol": "t",
                "description": "累积时间：三次重复测量 n 个周期的总时间（t₁、t₂、t₃）",
                "unit": "s"
            },
            {
                "symbol": "T",
                "description": "平均周期：三次 n 周期总时间的平均周期（自动计算）",
                "unit": "s"
            },
            {
                "symbol": "1/T^2",
                "description": "平均周期的倒数平方：1/T̄²，用于 1/T̄²–I² 线性拟合（自动计算）",
                "unit": "s⁻²"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "磁力摆测地磁场（反向）与最终结果",
                "steps": [
                    {
                        "note": "总磁场（线圈磁场与地磁场反向）：",
                        "formula": "B_{\\text{total}} = B_0 - kI"
                    },
                    {
                        "note": "线性化（斜率为负）：",
                        "formula": "\\frac{1}{T^2} = \\frac{m}{4\\pi^2 J} (B_0 - kI) = A - bI"
                    },
                    {
                        "note": "取平均截距与平均斜率绝对值：",
                        "formula": "A = \\frac{A_+ + A_-}{2}, \\quad b = \\frac{|b_+| + |b_-|}{2}"
                    },
                    {
                        "note": "由 A/b = B₀/k 得地磁场水平分量：",
                        "formula": "B_0 = k \\cdot \\frac{A}{b}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "励磁电流：本次测量设定的电流值",
                "unit": "A"
            },
            {
                "symbol": "t",
                "description": "累积时间：三次重复测量 n 个周期的总时间（t₁、t₂、t₃）",
                "unit": "s"
            },
            {
                "symbol": "\\bar{T}",
                "description": "平均周期：三次 n 周期总时间的平均周期（自动计算）",
                "unit": "s"
            },
            {
                "symbol": "1/T^2",
                "description": "平均周期的倒数平方：1/T̄²，用于线性拟合（自动计算）",
                "unit": "s⁻²"
            }
        ]
    }
},

    # ── exp11-exp25: 无表格实验，使用全局 ──
    "exp11": {
    "table1": {
        "formulas": [
            {
                "title": "NTC 特性与非平衡电桥设计",
                "steps": [
                    {
                        "note": "NTC 热敏电阻温度-电阻关系：",
                        "formula": "R_T = R_0 \\exp\\left[B\\left(\\frac{1}{T} - \\frac{1}{T_0}\\right)\\right]"
                    },
                    {
                        "note": "桥臂电阻设计（式 3，测温下限 T1、上限 T2）：",
                        "formula": "R_1 = R_2 = \\frac{2V_{CD}}{I_G}\\left(\\frac{1}{2} - \\frac{R_{T2}}{R_{T1}+R_{T2}}\\right) - 2\\left(R_G + \\frac{R_{T1}R_{T2}}{R_{T1}+R_{T2}}\\right)"
                    },
                    {
                        "note": "第三桥臂取下限温度阻值：",
                        "formula": "R_3 = R_{T1}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "温度：恒温水浴的标准温度",
                "unit": "°C"
            },
            {
                "symbol": "R_T",
                "description": "热敏电阻阻值：温度 T 时的阻值（万用表直接测量）",
                "unit": "Ω"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "温度计标定（I-T 拟合）",
                "steps": [
                    {
                        "note": "非平衡电桥输出电流随温度变化：",
                        "formula": "I = f(R_T)"
                    },
                    {
                        "note": "用三次多项式拟合标定曲线：",
                        "formula": "I = a_0 + a_1 T + a_2 T^2 + a_3 T^3"
                    },
                    {
                        "note": "相关系数：",
                        "formula": "R^2 = 1 - \\frac{\\sum (I_i - \\hat{I}_i)^2}{\\sum (I_i - \\bar{I})^2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R_T",
                "description": "热敏电阻阻值：温度 T 时的阻值（万用表直接测量）",
                "unit": "Ω"
            },
            {
                "symbol": "I",
                "description": "微安表电流：标定时的电流读数（直接测量）",
                "unit": "μA"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "测温反算与误差分析",
                "steps": [
                    {
                        "note": "局部线性插值反算温度（I_测 落在相邻标定点 I_k、I_{k+1} 之间）：",
                        "formula": "T_{\\text{测}} = T_k + (T_{k+1} - T_k) \\frac{I_{\\text{测}} - I_k}{I_{k+1} - I_k}"
                    },
                    {
                        "note": "绝对误差：",
                        "formula": "\\Delta T = |T_{\\text{测}} - T_{\\text{标}}|"
                    },
                    {
                        "note": "相对误差：",
                        "formula": "\\delta = \\frac{\\Delta T}{T_{\\text{标}}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "温度：标准温度（恒温水浴设定 32 °C / 58 °C）与由标定曲线反算的实测温度",
                "unit": "°C"
            },
            {
                "symbol": "I",
                "description": "实测微安表电流：测量时的电流读数",
                "unit": "μA"
            },
            {
                "symbol": "\\Delta T",
                "description": "测温偏差：ΔT = |T_测 − T_标|（自动计算）",
                "unit": "°C"
            },
            {
                "symbol": "\\delta",
                "description": "测温相对误差：δ = ΔT/T_标 × 100%（自动计算）",
                "unit": "%"
            }
        ]
    }
},
    "exp12": {
    "table1": {
        "formulas": [
            {
                "title": "自备方波周期测量",
                "steps": [
                    {
                        "note": "直接读数法：周期 = 波形厘米数 × 时基（μs ÷ 1000 换算为 ms）：",
                        "formula": "T = n \\cdot t_{div} / 1000"
                    },
                    {
                        "note": "以测量功能读数为基准的相对偏差：",
                        "formula": "\\delta = \\frac{T_{测} - T_{基准}}{T_{基准}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "周期：直接读数法、光标法、测量功能法三种方法测得的信号周期",
                "unit": "ms"
            },
            {
                "symbol": "t_{div}",
                "description": "时基：示波器水平扫描时间因数，周期 T = n × 时基",
                "unit": "μs/cm"
            },
            {
                "symbol": "n",
                "description": "波形厘米数：屏幕上单个周期的横向格数（cm）",
                "unit": "cm"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "频率测量与线性拟合",
                "steps": [
                    {
                        "note": "由周期换算频率（T 单位 ms）：",
                        "formula": "f = \\frac{1000}{T}"
                    },
                    {
                        "note": "f_meas-f_set 最小二乘线性拟合，理想斜率 k ≈ 1：",
                        "formula": "f_{meas} = k \\cdot f_{set} + b"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "f",
                "description": "实测频率：f = 1000/T_测（自动计算）",
                "unit": "Hz"
            },
            {
                "symbol": "f_{set}",
                "description": "设定频率：信号发生器输出的频率",
                "unit": "Hz"
            },
            {
                "symbol": "T",
                "description": "测量周期：示波器实测信号周期",
                "unit": "ms"
            },
            {
                "symbol": "f_{meas}",
                "description": "实测频率：f = 1000/T_测（自动计算）",
                "unit": "Hz"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "Vpp 双对数拟合",
                "steps": [
                    {
                        "note": "对设定值与测量值取对数后线性回归：",
                        "formula": "\\lg y = k \\cdot \\lg x + b"
                    },
                    {
                        "note": "等价幂函数形式，理想 k ≈ 1：",
                        "formula": "y = 10^{b} \\cdot x^{k}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "V_{pp}",
                "description": "峰峰值电压：信号发生器设定值与示波器实测值（Vpp）",
                "unit": "V"
            }
        ]
    },
    "table4": {
        "formulas": [
            {
                "title": "李萨如图形测未知频率",
                "steps": [
                    {
                        "note": "频率比等于切点数反比（水平切点对应 fy，垂直切点对应 fx）：",
                        "formula": "\\frac{f_y}{f_x} = \\frac{n_x}{n_y}"
                    },
                    {
                        "note": "未知频率：",
                        "formula": "f_x = f_y \\cdot \\frac{n_y}{n_x}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "f_y",
                "description": "本地信号源频率（已知）",
                "unit": "Hz"
            },
            {
                "symbol": "n_x",
                "description": "水平切线切点数（最左/最右端）",
                "unit": "—"
            },
            {
                "symbol": "n_y",
                "description": "垂直切线切点数（最上/最下端）",
                "unit": "—"
            },
            {
                "symbol": "f_x",
                "description": "待测未知频率",
                "unit": "Hz"
            }
        ]
    }
},
    "exp13": {
    "table1": {
        "formulas": [
            {
                "title": "整流滤波与纹波系数",
                "steps": [
                    {
                        "note": "峰值与全波整流平均值：",
                        "formula": "U_p = \\frac{V_{pp}}{2},\\quad U_{DC,\\mathrm{全波}} = \\frac{2U_p}{\\pi}"
                    },
                    {
                        "note": "单电容滤波：二极管截止时电容经负载指数放电（放电时间常数 τ = R_L·C）：",
                        "formula": "u_c(t) = u_{c0}\\, e^{-\\frac{t}{R_L C}}"
                    },
                    {
                        "note": "π 型第二级 R_1-C_2 低通递推（等效电阻 R_{eq} = R_1‖R_L）：",
                        "formula": "u_{c2} = u_{\\infty} + (u_{c2,0} - u_{\\infty})\\, e^{-\\frac{t}{\\tau}},\\quad \\tau = \\frac{R_1 R_L}{R_1 + R_L}\\, C_2"
                    },
                    {
                        "note": "纹波系数：",
                        "formula": "K_u = \\frac{U_{AC}}{U_{DC}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_{DC}",
                "description": "负载上直流电压（平均值）",
                "unit": "V"
            },
            {
                "symbol": "U_{AC}",
                "description": "纹波电压有效值（RMS）",
                "unit": "V"
            },
            {
                "symbol": "K_u",
                "description": "<strong>纹波系数</strong>（待求量）",
                "unit": "%"
            },
            {
                "symbol": "f",
                "description": "信号源频率",
                "unit": "Hz"
            },
            {
                "symbol": "C",
                "description": "滤波电容（μF，计算时 ×10⁻⁶ 转 F）",
                "unit": "μF"
            },
            {
                "symbol": "R_1",
                "description": "π 型滤波电阻",
                "unit": "Ω"
            },
            {
                "symbol": "R_L",
                "description": "负载电阻",
                "unit": "Ω"
            }
        ]
    }
},
    "exp14": {
    "_global": {
        "formulas": [
            {
                "title": "直流电源特性",
                "steps": [
                    {
                        "note": "纹波系数（交流分量有效值与直流分量之比，衡量直流电源品质的重要参数）：",
                        "formula": "K_u = \\frac{U_{AC}}{U_{DC}}"
                    },
                    {
                        "note": "负载输出功率：",
                        "formula": "P = \\frac{U_{DC}^2}{R_L}"
                    },
                    {
                        "note": "开路电压、短路电流与电源内阻：",
                        "formula": "r = \\frac{E}{I_{sc}}"
                    },
                    {
                        "note": "最大功率传输定理：",
                        "formula": "P = \\frac{E^2 R_L}{(R_L + r)^2},\\quad P_{max} \\ \\Leftrightarrow \\ R_L = r"
                    },
                    {
                        "note": "半偏法测电流表内阻：",
                        "formula": "R_g = R_2 - 2R_1"
                    },
                    {
                        "note": "改装电压表的串联电阻：",
                        "formula": "R_{ser} = \\frac{U}{I_g} - R_g"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "K_u",
                "description": "<strong>纹波系数</strong>（表征直流电源品质的重要参数）",
                "unit": "%"
            },
            {
                "symbol": "P",
                "description": "负载输出功率",
                "unit": "mW"
            },
            {
                "symbol": "E",
                "description": "<strong>电源电动势</strong>（开路电压，补偿法测得）",
                "unit": "V"
            },
            {
                "symbol": "I_{sc}",
                "description": "短路电流（取样电阻法间接测得）",
                "unit": "mA"
            },
            {
                "symbol": "r",
                "description": "<strong>电源内阻</strong>（待求量）",
                "unit": "Ω"
            },
            {
                "symbol": "R_g",
                "description": "<strong>电流表内阻</strong>（半偏法测得）",
                "unit": "Ω"
            },
            {
                "symbol": "R_{ser}",
                "description": "<strong>改装串联电阻</strong>",
                "unit": "Ω"
            },
            {
                "symbol": "U",
                "description": "改装电压表目标量程",
                "unit": "V"
            },
            {
                "symbol": "I_g",
                "description": "电流表满偏电流",
                "unit": "μA"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "负载功率曲线",
                "steps": [
                    {
                        "note": "负载输出功率：",
                        "formula": "P = \\frac{U_{DC}^2}{R_L}"
                    },
                    {
                        "note": "最大功率传输条件（P-R 曲线峰值处）：",
                        "formula": "R_L = r"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "负载电阻：电阻箱读数（20~2000 Ω）",
                "unit": "Ω"
            },
            {
                "symbol": "U_{AC}",
                "description": "输出端交流电压：纹波电压的有效值（直接测量）",
                "unit": "V"
            },
            {
                "symbol": "K_u",
                "description": "纹波系数：Ku = U_AC/U_DC × 100%（自动计算）",
                "unit": "%"
            },
            {
                "symbol": "U_{DC}",
                "description": "输出端直流电压（直接测量）",
                "unit": "V"
            },
            {
                "symbol": "P",
                "description": "负载输出功率：P = U_DC²/R（自动计算）",
                "unit": "mW"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "纹波系数与电容滤波",
                "steps": [
                    {
                        "note": "纹波系数：",
                        "formula": "K_u = \\frac{U_{AC}}{U_{DC}} \\times 100\\%"
                    },
                    {
                        "note": "小纹波近似下纹波系数反比于滤波电容与负载电阻：",
                        "formula": "K_u \\propto \\frac{1}{C R_L}"
                    },
                    {
                        "note": "滤波电容放电时间常数：",
                        "formula": "\\tau = R_L C"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "负载电阻：电阻箱读数（20~2000 Ω）",
                "unit": "Ω"
            },
            {
                "symbol": "U_{DC}",
                "description": "输出端直流电压（直接测量）",
                "unit": "V"
            },
            {
                "symbol": "P",
                "description": "负载输出功率：P = U_DC²/R（自动计算）",
                "unit": "mW"
            },
            {
                "symbol": "U_{AC}",
                "description": "输出端交流电压：纹波电压的有效值（直接测量）",
                "unit": "V"
            },
            {
                "symbol": "Ku",
                "description": "纹波系数：Ku = U_AC/U_DC × 100%（自动计算）",
                "unit": "%"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "开路电压与短路电流的测定",
                "steps": [
                    {
                        "note": "电压表内阻有限、直接短路会损坏电源，故用等效电路（补偿法）测开路电压：",
                        "formula": "E = U_{oc}"
                    },
                    {
                        "note": "短路电流由取样电阻间接测量：",
                        "formula": "I_{sc} = \\frac{U_s}{R_s}"
                    },
                    {
                        "note": "电源内阻：",
                        "formula": "r = \\frac{E}{I_{sc}}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_{oc}",
                "description": "补偿法测得的开路电压",
                "unit": "V"
            },
            {
                "symbol": "U_s",
                "description": "取样电阻两端电压",
                "unit": "mV"
            },
            {
                "symbol": "R_s",
                "description": "取样电阻（实验参数）",
                "unit": "Ω"
            },
            {
                "symbol": "I_{sc}",
                "description": "<strong>短路电流</strong>（计算列）",
                "unit": "mA"
            },
            {
                "symbol": "r",
                "description": "<strong>电源内阻</strong>（待求量）",
                "unit": "Ω"
            }
        ]
    },
    "table4": {
        "formulas": [
            {
                "title": "半偏法测电流表内阻与改装",
                "steps": [
                    {
                        "note": "满偏时 R_g + R1 = E/I_g，半偏时 R_g + R2 = 2(R_g + R1)，故：",
                        "formula": "R_g = R_2 - 2R_1"
                    },
                    {
                        "note": "改装成量程 U 的电压表需串联分压电阻：",
                        "formula": "R_{ser} = \\frac{U}{I_g} - R_g"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "电阻箱阻值：表头满偏时电阻箱阻值 R1 与半偏时阻值 R2",
                "unit": "Ω"
            },
            {
                "symbol": "R_g",
                "description": "电流表内阻（由满偏/半偏法测得）",
                "unit": "Ω"
            }
        ]
    },
    "table5": {
        "formulas": [
            {
                "title": "改装电表的定标",
                "steps": [
                    {
                        "note": "绝对误差与相对误差：",
                        "formula": "\\Delta U = U_m - U_{std},\\quad \\delta = \\frac{\\Delta U}{U_{std}}"
                    },
                    {
                        "note": "引用误差（满量程）定级：",
                        "formula": "\\gamma = \\frac{|\\Delta U|_{max}}{U_{FS}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\delta",
                "description": "相对误差：δ = (U_m − U_std)/U_std × 100%（自动计算）",
                "unit": "%"
            },
            {
                "symbol": "U_{std}",
                "description": "标准电压表读数（被测电压的真实值）",
                "unit": "V"
            },
            {
                "symbol": "U_m",
                "description": "改装表读数（改装电压表的示值）",
                "unit": "V"
            },
            {
                "symbol": "\\Delta U",
                "description": "绝对误差：ΔU = U_m − U_std（自动计算）",
                "unit": "V"
            }
        ]
    }
},
    "exp15": {
    "_global": {
        "formulas": [
            {
                "title": "硅光电池光电特性",
                "steps": [
                    {
                        "note": "无光照时等效为 PN 结二极管（暗特性）；有光照时叠加光生电流 Iph：",
                        "formula": "I = I_0\\left(e^{\\frac{qV}{kT}} - 1\\right) - I_{ph}"
                    },
                    {
                        "note": "短路时（V=0）电流即短路电流，等于光生电流：",
                        "formula": "I_{sc} = I_{ph} \\propto L"
                    },
                    {
                        "note": "开路时（I=0）电压即开路电压：",
                        "formula": "V_{oc} = \\frac{kT}{q}\\ln\\left(1 + \\frac{I_{sc}}{I_0}\\right) \\propto \\ln L"
                    },
                    {
                        "note": "输出功率与填充因子（衡量光电转换品质）：",
                        "formula": "P = VI,\\quad FF = \\frac{P_m}{V_{oc} I_{sc}}"
                    },
                    {
                        "note": "光照强度与灯距换算（d=50cm 标定为 40 lx）：",
                        "formula": "L = 40\\left(\\frac{50}{d}\\right)^2 \\ \\mathrm{lx}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "输出电流",
                "unit": "mA"
            },
            {
                "symbol": "V",
                "description": "工作电压（端电压）",
                "unit": "V"
            },
            {
                "symbol": "I_0",
                "description": "<strong>反向饱和电流</strong>，由暗伏安特性拟合得到",
                "unit": "mA"
            },
            {
                "symbol": "I_{ph}",
                "description": "光生电流，与光照强度 L 成正比",
                "unit": "mA"
            },
            {
                "symbol": "I_{sc}",
                "description": "<strong>短路电流</strong>，等于光生电流 Iph",
                "unit": "mA"
            },
            {
                "symbol": "V_{oc}",
                "description": "<strong>开路电压</strong>，与 ln L 成正比",
                "unit": "V"
            },
            {
                "symbol": "P_m",
                "description": "<strong>最大输出功率</strong>，对应最佳负载 Rm",
                "unit": "mW"
            },
            {
                "symbol": "R_m",
                "description": "<strong>最佳负载电阻</strong>（最大功率点对应负载）",
                "unit": "Ω"
            },
            {
                "symbol": "FF",
                "description": "<strong>填充因子</strong>，Pm/(Voc·Isc)，越大转换品质越好",
                "unit": "—"
            },
            {
                "symbol": "L",
                "description": "光照强度，由灯距 d 换算",
                "unit": "lx"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "暗伏安特性（二极管模型）",
                "steps": [
                    {
                        "note": "无光照时硅光电池等效为 PN 结二极管，正向偏压下电流随电压指数增长：",
                        "formula": "I = I_0\\left(e^{\\frac{qU}{kT}} - 1\\right)"
                    },
                    {
                        "note": "线性化：取 I>0 的点作 ln I-U 图，斜率为 b = q/kT：",
                        "formula": "\\ln I = \\ln I_0 + \\frac{q}{kT}\\, U"
                    },
                    {
                        "note": "由斜率反推热电压与结温：",
                        "formula": "\\frac{kT}{q} = \\frac{1}{b},\\quad T = \\frac{11604.5}{b}\\ \\mathrm{K}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "暗电流：无光照时硅光电池的反向电流（直接测量）",
                "unit": "mA"
            },
            {
                "symbol": "U",
                "description": "电压：硅光电池反向偏置电压（暗电流测量）",
                "unit": "V"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "输出特性与最大功率点",
                "steps": [
                    {
                        "note": "负载电阻 R 上的工作电流与输出功率：",
                        "formula": "I = \\frac{U}{R},\\quad P = U I = \\frac{U^2}{R}"
                    },
                    {
                        "note": "最大输出功率 Pm 对应最佳负载 Rm，据此求填充因子：",
                        "formula": "FF = \\frac{P_m}{V_{oc} I_{sc}}"
                    },
                    {
                        "note": "表中 Uoc、Isc 由最大/最小负载近似（R→∞ 时 U→Uoc，R→0 时 I→Isc），应与表 3 实测值对照。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_{cm}",
                "description": "输出电压：不同灯距 d（20/30/40/50 cm）下硅光电池的输出电压",
                "unit": "V"
            },
            {
                "symbol": "R",
                "description": "负载电阻：不同灯距下连接的负载电阻",
                "unit": "Ω"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "开路电压、短路电流与光照",
                "steps": [
                    {
                        "note": "短路电流由取样电阻电压换算：",
                        "formula": "I_{sc} = \\frac{U_r}{R_0}"
                    },
                    {
                        "note": "短路电流与光照成正比，作 Isc-L 线性拟合：",
                        "formula": "I_{sc} = k L"
                    },
                    {
                        "note": "开路电压与光照的对数近似成正比：",
                        "formula": "V_{oc} = A \\ln L + B"
                    },
                    {
                        "note": "光照强度与灯距换算：",
                        "formula": "L = 40\\left(\\frac{50}{d}\\right)^2 \\ \\mathrm{lx}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_{oc}",
                "description": "开路电压：光照下硅光电池两端的开路电压（直接测量）",
                "unit": "V"
            },
            {
                "symbol": "I_{sc}",
                "description": "短路电流：I_sc = U_r/R₀（自动计算）",
                "unit": "mA"
            },
            {
                "symbol": "d",
                "description": "光源到硅光电池的距离（灯距）",
                "unit": "cm"
            },
            {
                "symbol": "U_r",
                "description": "采样电阻两端电压，用于计算短路电流 I_sc = U_r/R₀",
                "unit": "mV"
            }
        ]
    },
    "table4": {
        "formulas": [
            {
                "title": "输出电压与光照特性",
                "steps": [
                    {
                        "note": "接负载 RL 时，输出电压随光照增强而升高并趋于饱和，近似对数规律：",
                        "formula": "U = A \\ln L + B"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "d",
                "description": "光源到硅光电池的距离（灯距）",
                "unit": "cm"
            },
            {
                "symbol": "U",
                "description": "输出电压：硅光电池在对应灯距与负载下的输出电压",
                "unit": "V"
            }
        ]
    },
    "table5": {
        "formulas": [
            {
                "title": "反向偏压下输出电压与光照特性",
                "steps": [
                    {
                        "note": "反向偏压下硅光电池处于光电流线性区，光电流与光照成正比：",
                        "formula": "I_{ph} \\propto L"
                    },
                    {
                        "note": "负载电压随光照线性增长：",
                        "formula": "U = I_{ph} R_L = k L + b"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "d",
                "description": "光源到硅光电池的距离（灯距）",
                "unit": "cm"
            },
            {
                "symbol": "U",
                "description": "输出电压：硅光电池在对应灯距与负载下的输出电压",
                "unit": "V"
            }
        ]
    }
},
    "exp16": {
    "_global": {
        "formulas": [
            {
                "title": "LED 发光波长与禁带宽度",
                "steps": [
                    {
                        "note": "LED 发光峰值波长由半导体材料<strong>禁带宽度</strong>决定：",
                        "formula": "\\lambda = \\frac{1240}{E_g} \\ (\\mathrm{nm})"
                    },
                    {
                        "note": "可见光 380~780 nm 对应 E_g 在 1.63~3.26 eV 之间；不同颜色 LED 的典型波长：红 620~750 nm、绿 500~565 nm、蓝 450~495 nm。",
                        "formula": None
                    }
                ]
            },
            {
                "title": "相加混色（格拉斯曼定律）",
                "steps": [
                    {
                        "note": "三基色按比例相加合成混色：红+绿=黄、绿+蓝=青、蓝+红=紫、红+绿+蓝=白。",
                        "formula": None
                    },
                    {
                        "note": "CIE 标准三基色波长：红 700 nm、绿 546.1 nm、蓝 435.8 nm，相对视敏函数分别为 0.0041、0.975、0.0173。",
                        "formula": None
                    },
                    {
                        "note": "扣除背景光强后混色光强满足<strong>可加性</strong>：",
                        "formula": "L_{混}' \\approx L_1' + L_2' (+ L_3'), \\quad L' = L - L_0"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\lambda",
                "description": "<strong>发光峰值波长</strong>，由 λ = 1240/E_g 计算",
                "unit": "nm"
            },
            {
                "symbol": "E_g",
                "description": "<strong>半导体禁带宽度</strong>，数值上取 I-U 曲线阈值电压 U_th 的 eV 值",
                "unit": "eV"
            },
            {
                "symbol": "U",
                "description": "<strong>LED 正向电压</strong>，数字万用表测量",
                "unit": "V"
            },
            {
                "symbol": "I",
                "description": "<strong>工作电流</strong>（I ≤ 100 mA），毫安表测量",
                "unit": "mA"
            },
            {
                "symbol": "L",
                "description": "<strong>相对光强</strong>，硅光电池输出电压",
                "unit": "mV"
            },
            {
                "symbol": "L_0",
                "description": "<strong>背景光强</strong>，全部 LED 熄灭时光电池读数",
                "unit": "mV"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "LED 正向伏安特性",
                "steps": [
                    {
                        "note": "LED 的 I-U 特性非线性，超过阈值电压后近似按指数规律增长：",
                        "formula": "I = I_0\\left(e^{bU} - 1\\right)"
                    },
                    {
                        "note": "线性化：对 I>0 的点做 ln I 对 U 的线性拟合：",
                        "formula": "\\ln I = \\ln I_0 + b\\,U"
                    },
                    {
                        "note": "阈值电压 U_th（曲线膝点）用于计算发光峰值波长。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "LED 正向电压，由数字万用表测量",
                "unit": "V"
            },
            {
                "symbol": "I",
                "description": "LED 工作电流（I ≤ 100 mA），由毫安表测量",
                "unit": "mA"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "峰值波长与标准不确定度",
                "steps": [
                    {
                        "note": "<strong>峰值波长</strong>：",
                        "formula": "\\lambda = \\frac{1240}{U_{th}}\\ (\\mathrm{nm})"
                    },
                    {
                        "note": "<strong>B 类</strong>不确定度（万用表电压档分辨率 ΔU，均匀分布）：",
                        "formula": "u_B(U_{th}) = \\frac{\\Delta U}{\\sqrt{3}}"
                    },
                    {
                        "note": "同一 LED 多次读数的<strong>A 类</strong>不确定度（P=0.95）：",
                        "formula": "u_A(U_{th}) = t(n-1)\\cdot\\frac{\\sigma}{\\sqrt{n}}"
                    },
                    {
                        "note": "<strong>合成</strong>标准不确定度与波长的传递：",
                        "formula": "u(U_{th}) = \\sqrt{u_A^2 + u_B^2}, \\quad u(\\lambda) = \\frac{\\lambda}{U_{th}}\\,u(U_{th})"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_th",
                "description": "阈值电压（曲线膝点对应的正向电压）",
                "unit": "V"
            },
            {
                "symbol": "\\lambda",
                "description": "LED 发光峰值波长，由 λ = 1240/U_th（U_th 以 V 计）计算",
                "unit": "nm"
            },
            {
                "symbol": "u",
                "description": "峰值波长的标准不确定度（A 类与 B 类合成）",
                "unit": "nm"
            },
            {
                "symbol": "u(\\lambda)",
                "description": "峰值波长的标准不确定度（A 类与 B 类合成）",
                "unit": "nm"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "发光强度特性",
                "steps": [
                    {
                        "note": "低中电流区相对光强与工作电流近似线性：",
                        "formula": "L = k\\,I + b"
                    },
                    {
                        "note": "线性度用相关系数衡量，|r| 越接近 1 线性越好。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "绿色 LED 的工作电流",
                "unit": "mA"
            },
            {
                "symbol": "L",
                "description": "绿色 LED 的相对光强，取硅光电池输出电压",
                "unit": "mV"
            }
        ]
    },
    "table4": {
        "formulas": [
            {
                "title": "两色相加混色",
                "steps": [
                    {
                        "note": "<strong>扣除背景光强</strong>：",
                        "formula": "L_1' = L_1 - L_0, \\quad L_2' = L_2 - L_0"
                    },
                    {
                        "note": "<strong>两基色光强比</strong>：",
                        "formula": "L_1' : L_2'"
                    },
                    {
                        "note": "<strong>可加性校核</strong>（混色实测与基色之和比较）：",
                        "formula": "L_{混}' = L_{混} - L_0 \\approx L_1' + L_2'"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "L",
                "description": "某基色 LED 单独点亮时的相对光强（LED1、LED2 分别为两基色）",
                "unit": "mV"
            },
            {
                "symbol": "L_0",
                "description": "背景光强，全部 LED 熄灭时硅光电池的读数",
                "unit": "mV"
            },
            {
                "symbol": "L'",
                "description": "扣除背景光强后的相对光强，L′ = L − L₀",
                "unit": "mV"
            },
            {
                "symbol": "L_L",
                "description": "两基色扣除背景光强后的光强比 L₁′:L₂′",
                "unit": ""
            }
        ]
    },
    "table5": {
        "formulas": [
            {
                "title": "三色相加混色配白",
                "steps": [
                    {
                        "note": "<strong>扣除背景光强</strong>：",
                        "formula": "L_R' = L_R - L_0, \\quad L_G' = L_G - L_0, \\quad L_B' = L_B - L_0"
                    },
                    {
                        "note": "<strong>三基色光强比</strong>：",
                        "formula": "L_R' : L_G' : L_B'"
                    },
                    {
                        "note": "<strong>可加性校核</strong>：",
                        "formula": "L_{白}' = L_{白} - L_0 \\approx L_R' + L_G' + L_B'"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "L",
                "description": "红、绿、蓝 LED 各自单独点亮时的相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_0",
                "description": "背景光强，全部 LED 熄灭时硅光电池的读数",
                "unit": "mV"
            },
            {
                "symbol": "L_R'",
                "description": "扣除背景光强后的红色 LED 相对光强，L_R′ = L_R − L₀",
                "unit": "mV"
            },
            {
                "symbol": "L_G'",
                "description": "扣除背景光强后的绿色 LED 相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_B'",
                "description": "扣除背景光强后的蓝色 LED 相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_L",
                "description": "三基色扣除背景光强后的光强比 L_R′:L_G′:L_B′",
                "unit": ""
            }
        ]
    },
    "table6": {
        "formulas": [
            {
                "title": "颜料色彩配出",
                "steps": [
                    {
                        "note": "<strong>扣除背景光强</strong>：",
                        "formula": "L_R' = L_R - L_0, \\quad L_G' = L_G - L_0, \\quad L_B' = L_B - L_0"
                    },
                    {
                        "note": "<strong>三基色光强比</strong>：",
                        "formula": "L_R' : L_G' : L_B'"
                    },
                    {
                        "note": "<strong>可加性校核</strong>：",
                        "formula": "L_{混}' = L_{混} - L_0 \\approx L_R' + L_G' + L_B'"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "L",
                "description": "红、绿、蓝基色各自单独点亮时的相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_0",
                "description": "背景光强，全部 LED 熄灭时硅光电池的读数",
                "unit": "mV"
            },
            {
                "symbol": "L_R'",
                "description": "扣除背景光强后的红色相对光强，L_R′ = L_R − L₀",
                "unit": "mV"
            },
            {
                "symbol": "L_G'",
                "description": "扣除背景光强后的绿色相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_B'",
                "description": "扣除背景光强后的蓝色相对光强",
                "unit": "mV"
            },
            {
                "symbol": "L_L",
                "description": "三基色扣除背景光强后的光强比 L_R′:L_G′:L_B′",
                "unit": ""
            }
        ]
    }
},
    "exp17": {
    "_global": {
        "formulas": [
            {
                "title": "直流非平衡电桥",
                "steps": [
                    {
                        "note": "分压原理，电桥输出（Rg 为负载电阻）：",
                        "formula": "U=\\frac{R_2R_x-R_1R_3}{(R_1+R_x)(R_2+R_3)}E"
                    },
                    {
                        "note": "电桥平衡条件（起始点预调平衡，U=0）：",
                        "formula": "R_1R_3=R_2R_x"
                    },
                    {
                        "note": "设电桥比率 K = R2/R3、待测桥臂相对变化 δ = ΔRx/R0：",
                        "formula": "U=\\frac{E K\\delta}{(1+K+\\delta)(1+K)}"
                    },
                    {
                        "note": "δ ≪ 1 时线性近似（K=1 时 U=Eδ/4）：",
                        "formula": "U\\approx\\frac{E K\\delta}{(1+K)^2}"
                    }
                ]
            },
            {
                "title": "Pt1000 铂热电阻与温度系数",
                "steps": [
                    {
                        "note": "铂热电阻阻值随温度线性变化：",
                        "formula": "R_t=R_0[1+\\alpha(t-t_0)]"
                    },
                    {
                        "note": "由 U–t 拟合斜率 m 求电阻温度系数：",
                        "formula": "\\alpha=\\frac{m(1+K)^2}{KE}"
                    },
                    {
                        "note": "0 ℃ 阻值外推：",
                        "formula": "R(0℃)=\\frac{R_x(t_0)}{1+\\alpha t_0},\\quad R_x(t_0)=\\frac{R_1R_3}{R_2}"
                    }
                ]
            },
            {
                "title": "温标与电桥灵敏度",
                "steps": [
                    {
                        "note": "国际温标（ITS-90）摄氏与热力学温度的关系：",
                        "formula": "T=t+273.15\\ (\\mathrm{K})"
                    },
                    {
                        "note": "平衡电桥灵敏度（δ=0 处）：",
                        "formula": "S_0=\\frac{\\Delta U}{\\Delta R}\\Big|_{\\delta=0}=\\frac{E K}{(1+K)^2 R_0}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "<strong>电桥非平衡输出电压</strong>（200 mV 档测量）",
                "unit": "mV"
            },
            {
                "symbol": "E",
                "description": "<strong>激励电压</strong>（直流信号源输出）",
                "unit": "V"
            },
            {
                "symbol": "K",
                "description": "<strong>电桥比率</strong> K = R2/R3",
                "unit": "1"
            },
            {
                "symbol": "\\delta",
                "description": "<strong>待测桥臂相对变化</strong> δ = ΔRx/R0 = α(t−t0)",
                "unit": "1"
            },
            {
                "symbol": "R_t",
                "description": "Pt1000 在 t ℃ 时的阻值",
                "unit": "Ω"
            },
            {
                "symbol": "R_0",
                "description": "Pt1000 在 0 ℃ 时的阻值（待求量）",
                "unit": "Ω"
            },
            {
                "symbol": "\\alpha",
                "description": "<strong>电阻温度系数</strong>（待求量）",
                "unit": "℃⁻¹"
            },
            {
                "symbol": "m",
                "description": "U–t 拟合直线<strong>斜率</strong>（灵敏度）",
                "unit": "mV/℃"
            },
            {
                "symbol": "S_0",
                "description": "平衡电桥<strong>理论灵敏度</strong>",
                "unit": "mV/Ω"
            }
        ]
    },
    "bridge": {
        "formulas": [
            {
                "title": "U–t 线性拟合与温度系数",
                "steps": [
                    {
                        "note": "预调平衡后 U 与 (t−t0) 成正比，拟合斜率：",
                        "formula": "m=\\frac{E K\\alpha}{(1+K)^2}"
                    },
                    {
                        "note": "<strong>电阻温度系数</strong>：",
                        "formula": "\\alpha=\\frac{m(1+K)^2}{KE}"
                    },
                    {
                        "note": "由平衡条件得 t0 时传感器阻值，外推 0 ℃ 阻值：",
                        "formula": "R_x(t_0)=\\frac{R_1R_3}{R_2},\\quad R(0℃)=\\frac{R_x(t_0)}{1+\\alpha t_0}"
                    },
                    {
                        "note": "逐点相对偏差量化线性特性：",
                        "formula": "\\frac{U-U_{理论}}{U_{理论}}\\times100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "温度（Pt1000 热电阻所处水温，30~45 ℃ 范围测量）",
                "unit": "℃"
            },
            {
                "symbol": "U",
                "description": "桥路输出电压（实测值，数字万用表 200 mV 档测量）",
                "unit": "mV"
            },
            {
                "symbol": "δ=ΔR/R₀",
                "description": "待测桥臂（Pt1000）相对电阻变化 δ = ΔR/R₀，由实测输出电压按线性近似反算",
                "unit": ""
            }
        ]
    },
    "sensitivity": {
        "formulas": [
            {
                "title": "平衡电桥灵敏度",
                "steps": [
                    {
                        "note": "平衡点附近改变 ΔR，逐点灵敏度：",
                        "formula": "S=\\frac{\\Delta U}{\\Delta R}"
                    },
                    {
                        "note": "<strong>理论灵敏度</strong>：",
                        "formula": "S_0=\\frac{E K}{(1+K)^2 R_0},\\quad R_0=R_x(t_0)=\\frac{R_1R_3}{R_2}"
                    },
                    {
                        "note": "K=1 时 S0 = E/4R0：增大 E 或减小 R0 可提高灵敏度。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\Delta R",
                "description": "平衡点附近被测桥臂的电阻改变量（电阻箱调节，δ ≪ 1）",
                "unit": "Ω"
            },
            {
                "symbol": "U",
                "description": "对应 ΔR 的电桥输出电压（实测值，200 mV 档测量）",
                "unit": "mV"
            },
            {
                "symbol": "S_U",
                "description": "电桥灵敏度 S = U/ΔR，输出电压随电阻的变化率",
                "unit": "mV/Ω"
            }
        ]
    },
    "calib": {
        "formulas": [
            {
                "title": "数字体温计校准",
                "steps": [
                    {
                        "note": "以水银温度计为标准逐点比对，<strong>修正量</strong>：",
                        "formula": "\\Delta t=t_{标准}-t_{读数}"
                    },
                    {
                        "note": "取平均得<strong>修正公式</strong>：",
                        "formula": "t=t_{读数}+\\overline{\\Delta t}"
                    },
                    {
                        "note": "线性修正（斜率接近 1 说明系统误差小）：",
                        "formula": "t_{标准}=a+b\\,t_{读数}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "温度读数（标准表 t_标准、数字表 t_读数 与修正后 t_修正 三列）",
                "unit": "℃"
            },
            {
                "symbol": "\\Delta t",
                "description": "修正量 Δt = t_标准 − t_读数（Δt̄ < 0 表示读数偏高）",
                "unit": "℃"
            }
        ]
    },
    "nonlinear": {
        "formulas": [
            {
                "title": "非平衡电桥线性与非线性",
                "steps": [
                    {
                        "note": "<strong>精确输出</strong>与<strong>线性近似</strong>：",
                        "formula": "U=\\frac{E K\\delta}{(1+K+\\delta)(1+K)},\\quad U_0=\\frac{E K\\delta}{(1+K)^2}"
                    },
                    {
                        "note": "线性近似相对精确输出的<strong>理论偏差</strong>（K=1 时 δ/2）：",
                        "formula": "\\frac{U_0-U}{U}=\\frac{\\delta}{1+K}"
                    },
                    {
                        "note": "δ ≲ 0.01 时偏差 < 1%，可视作线性；δ 增大后非线性逐渐显现。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "温度（扩大到 30~60 ℃ 大范围，δ 不再远小于 1）",
                "unit": "℃"
            },
            {
                "symbol": "U",
                "description": "桥路输出电压（实测值）",
                "unit": "mV"
            },
            {
                "symbol": "δ=ΔR/R₀",
                "description": "待测桥臂（Pt1000）相对电阻变化 δ = ΔR/R₀（大温度范围下由输出电压按精确关系反算）",
                "unit": ""
            }
        ]
    }
},
    "exp18_a": {
    "_global": {
        "formulas": [
            {
                "title": "分光计的调节与使用（光栅衍射）",
                "steps": [
                    {
                        "note": "光栅方程（平行光垂直入射）：",
                        "formula": "d\\sin\\varphi = k\\lambda,\\quad k = 0,\\ \\pm 1,\\ \\pm 2,\\cdots"
                    },
                    {
                        "note": "衍射角：各谱线位置与 0 级位置的夹角，左右游标分别取差再平均（消除刻度盘偏心误差）：",
                        "formula": "\\varphi = \\frac{|\\theta_1 - \\theta_{10}| + |\\theta_2 - \\theta_{20}|}{2}"
                    },
                    {
                        "note": "两侧（+1、-1 级）衍射角应一致（相差 ≤3′），否则光栅刻痕未与转轴平行或入射未垂直：",
                        "formula": "\\varphi \\approx \\frac{\\varphi_{+1} + \\varphi_{-1}}{2}"
                    },
                    {
                        "note": "由绿光（546.07 nm）的衍射角求光栅常数：",
                        "formula": "d = \\frac{\\lambda_g}{\\sin\\varphi_g}\\ \\ (\\lambda_g = 546.07\\ \\mathrm{nm})"
                    },
                    {
                        "note": "同法测其他谱线波长：",
                        "formula": "\\lambda = d\\sin\\varphi"
                    },
                    {
                        "note": "光栅常数与空间频率（每毫米刻痕数）：",
                        "formula": "f = \\frac{1}{d}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "d",
                "description": "<strong>光栅常数</strong>（相邻刻痕间距），教学光栅常见 100~300 线/mm（d 约 3.3~10 μm）",
                "unit": "nm"
            },
            {
                "symbol": "\\varphi",
                "description": "<strong>衍射角</strong>，谱线位置与 0 级位置的夹角",
                "unit": "°"
            },
            {
                "symbol": "k",
                "description": "衍射级次（本实验取 ±1）",
                "unit": "—"
            },
            {
                "symbol": "\\lambda",
                "description": "光波长（绿光 546.07 nm；蓝紫 435.83、黄内 576.96、黄外 579.07 nm）",
                "unit": "nm"
            },
            {
                "symbol": "\\theta_1, \\theta_2",
                "description": "左、右游标读数（θ2 = θ1 + 180°），双游标平均消除偏心误差",
                "unit": "°"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "衍射角与光栅常数的计算",
                "steps": [
                    {
                        "note": "读数规则：刻度盘分 720 等份，游标最小分度 30″（格值 30′），估读到 0.5′。θ1、θ2 两游标相差 180°，两游标读数差与 180° 之差应不超 3′。",
                        "formula": None
                    },
                    {
                        "note": "每次测量的衍射角：",
                        "formula": "\\varphi_i = \\frac{|\\theta_{1k} - \\theta_{10}| + |\\theta_{2k} - \\theta_{20}|}{2}"
                    },
                    {
                        "note": "平均衍射角与光栅常数：",
                        "formula": "\\bar\\varphi = \\frac{1}{n}\\sum \\varphi_i,\\quad d = \\frac{\\lambda_g}{\\sin\\bar\\varphi}"
                    },
                    {
                        "note": "两侧一致性检验：|φ+1 − φ−1| ≤ 3′ 表明光栅已调节好；否则需重新调节光栅。",
                        "formula": None
                    },
                    {
                        "note": "各谱线波长 λ = d·sinφ，与标准值（蓝紫 435.83、黄内 576.96、黄外 579.07 nm）比较相对偏差。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\theta",
                "description": "左、右游标读数（θ1、θ2 各测 3 次；同一位置两游标读数相差 180°）",
                "unit": "°"
            },
            {
                "symbol": "\\varphi",
                "description": "衍射角 φ = |θ_k − θ_0|，左右游标平均以消除偏心误差（末列为三次平均）",
                "unit": "°"
            }
        ]
    }
},
    "exp18_b": {
    "_global": {
        "formulas": [
            {
                "title": "用分光计测三棱镜折射率（最小偏向角法）",
                "steps": [
                    {
                        "note": "入射光与出射光的夹角为偏向角 δ；当入射角等于出射角时 δ 最小，称为最小偏向角 δ_min：",
                        "formula": "\\delta = (i - r) + (i' - r')"
                    },
                    {
                        "note": "最小偏向角条件下，光在棱镜内对称传播：",
                        "formula": "r = r' = \\frac{A}{2},\\quad \\delta_{\\min} = 2i - A"
                    },
                    {
                        "note": "由折射定律得折射率（最小偏向角法核心公式）：",
                        "formula": "n = \\frac{\\sin\\frac{A + \\delta_{\\min}}{2}}{\\sin\\frac{A}{2}}"
                    },
                    {
                        "note": "材料的色散可用柯西经验公式描述（进阶内容，测 3 条谱线定 a、b、c）：",
                        "formula": "n(\\lambda) = a + \\frac{b}{\\lambda^2} + \\frac{c}{\\lambda^4}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "n",
                "description": "<strong>折射率</strong>（待求量），玻璃典型值约 1.5~1.6（K9 冕牌玻璃 546.1 nm 处约 1.518）",
                "unit": "无单位"
            },
            {
                "symbol": "A",
                "description": "<strong>三棱镜顶角</strong>（一般 50°~70°，常见 60°）",
                "unit": "°"
            },
            {
                "symbol": "\\delta_{\\min}",
                "description": "<strong>最小偏向角</strong>（一般 30°~45°）",
                "unit": "°"
            },
            {
                "symbol": "\\theta_1, \\theta_2",
                "description": "左、右游标读数（θ2 = θ1 + 180°），双游标平均消除偏心误差",
                "unit": "°"
            },
            {
                "symbol": "\\lambda",
                "description": "谱线波长（绿谱线 546.1 nm）",
                "unit": "nm"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "三棱镜顶角 A 的测量",
                "steps": [
                    {
                        "note": "AC 面、AB 面依次正对望远镜，两次读数之差即顶角的补角：",
                        "formula": "\\varphi = \\frac{(\\theta_1 - \\theta_1') + (\\theta_2 - \\theta_2')}{2},\\quad A = 180° - \\varphi"
                    },
                    {
                        "note": "左、右游标分别取圆周差再平均，消除刻度盘偏心误差（处理 0°/360° 跨界）。",
                        "formula": None
                    },
                    {
                        "note": "读数规则：同一位置两游标读数差与 180° 之差应不超 3′。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "AC\\theta",
                "description": "AC 面正对望远镜时的左、右游标读数（θ1 左、θ2 右，相差 180°）",
                "unit": "°"
            },
            {
                "symbol": "AB\\theta",
                "description": "AB 面正对望远镜时的左、右游标读数（θ1′ 左、θ2′ 右，相差 180°）",
                "unit": "°"
            },
            {
                "symbol": "A",
                "description": "三棱镜顶角，由 A = 180° − φ 计算（φ 为两次读数差的平均）",
                "unit": "°"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "最小偏向角与折射率的计算",
                "steps": [
                    {
                        "note": "绿谱线处于最小偏向位置与入射光方向（取下棱镜、望远镜对准平行光管）的读数之差：",
                        "formula": "\\delta_{\\min} = \\frac{(\\theta_1 - \\theta_1') + (\\theta_2 - \\theta_2')}{2}"
                    },
                    {
                        "note": "将平均顶角 Ā 与平均最小偏向角 δ̄_min 代入最小偏向角公式：",
                        "formula": "n = \\frac{\\sin\\frac{\\bar A + \\bar\\delta_{\\min}}{2}}{\\sin\\frac{\\bar A}{2}}"
                    },
                    {
                        "note": "折射率的标准不确定度由 Ā 与 δ̄_min 的不确定度按误差传递公式求得。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\theta",
                "description": "游标读数（最小偏向位置与入射光方向各读左、右游标，相差 180°）",
                "unit": "°"
            },
            {
                "symbol": "\\delta_min",
                "description": "最小偏向角（单次测量值），由最小偏向位置与入射光方向读数差平均计算",
                "unit": "°"
            }
        ]
    }
},
    "exp19": {
    "_global": {
        "formulas": [
            {
                "title": "干涉法测微小量",
                "steps": [
                    {
                        "note": "光程差（含半波损失）：",
                        "formula": "\\Delta = 2\\delta + \\frac{\\lambda}{2}"
                    },
                    {
                        "note": "牛顿环暗环（m = 0,1,2,…）：",
                        "formula": "\\delta_m = \\frac{m\\lambda}{2}, \\quad r_m^2 = mR\\lambda \\;\\Rightarrow\\; D_m^2 = 4mR\\lambda"
                    },
                    {
                        "note": "劈尖第 m 级暗纹处空气层厚度：",
                        "formula": "d_m = \\frac{m\\lambda}{2}"
                    },
                    {
                        "note": "细丝直径（N 为细丝处条纹级数）：",
                        "formula": "d = \\frac{N\\lambda}{2} = \\frac{10\\lambda L}{\\Delta l}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\lambda",
                "description": "钠灯光源波长",
                "unit": "589.3 nm"
            },
            {
                "symbol": "m",
                "description": "干涉级次（暗环/暗纹序号）",
                "unit": "无单位"
            },
            {
                "symbol": "D_m",
                "description": "第 m 级暗环直径",
                "unit": "mm"
            },
            {
                "symbol": "R",
                "description": "<strong>平凸透镜曲率半径</strong>（待求量）",
                "unit": "mm"
            },
            {
                "symbol": "\\Delta l",
                "description": "20 条暗纹的总长度",
                "unit": "mm"
            },
            {
                "symbol": "L",
                "description": "劈尖交线到细丝的总长度",
                "unit": "mm"
            },
            {
                "symbol": "n",
                "description": "单位长度的干涉条纹数",
                "unit": "条/mm"
            },
            {
                "symbol": "d",
                "description": "<strong>细丝直径</strong>（待求量）",
                "unit": "μm"
            }
        ]
    },
    "table1": {
        "formulas": [
            {
                "title": "牛顿环测平凸透镜曲率半径",
                "steps": [
                    {
                        "note": "同一暗环两侧读数之差：",
                        "formula": "D_m = |d'_m - d_m|"
                    },
                    {
                        "note": "差值法（n = 15，环对 (5,20)、(10,25)、(15,30)）：",
                        "formula": "R = \\frac{D_{m+n}^2 - D_m^2}{4n\\lambda}"
                    },
                    {
                        "note": "最小二乘交叉验证：",
                        "formula": "\\bar{D}_m^2 = 4R\\lambda \\cdot m"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "m",
                "description": "牛顿环暗环序号（干涉级次），本表取 30、25、20、15、10、5",
                "unit": ""
            },
            {
                "symbol": "d",
                "description": "第 m 暗环一侧的读数显微镜位置读数（左右两列各为一侧相切位置）",
                "unit": "mm"
            },
            {
                "symbol": "U(\\bar{D}_m)",
                "description": "平均直径 D̄_m 的标准不确定度（A 类）",
                "unit": "mm"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "劈尖等厚干涉测细丝直径",
                "steps": [
                    {
                        "note": "两次读数之差：",
                        "formula": "\\Delta l = l_2 - l_1, \\quad L = L_2 - L_1"
                    },
                    {
                        "note": "单位长度条纹数：",
                        "formula": "n = \\frac{20}{\\Delta l}"
                    },
                    {
                        "note": "细丝直径（N = 20）：",
                        "formula": "d = \\frac{N\\lambda}{2} = \\frac{10\\lambda L}{\\Delta l}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "l",
                "description": "端点位置读数（右、左两列；Δl 行与 L 行的端点位置）",
                "unit": "mm"
            },
            {
                "symbol": "\\Delta",
                "description": "端点读数之差 Δ = |右 − 左|（Δl 行为 20 条暗纹总长度、L 行为交线到细丝长度）；平均列为三次平均",
                "unit": "mm"
            },
            {
                "symbol": "U",
                "description": "三次测量平均值的标准不确定度（A 类）",
                "unit": "mm"
            }
        ]
    }
},
    "exp20": {"_global": {"formulas": [{"title": "透镜参数测量", "steps": [{"note": "薄透镜成像公式：", "formula": r"\frac{1}{u} + \frac{1}{v} = \frac{1}{f}"}]}], "variables": [{"symbol": "u", "description": "物距", "unit": "m"}, {"symbol": "v", "description": "像距", "unit": "m"}, {"symbol": "f", "description": "<strong>焦距</strong>（待求量）", "unit": "m"}]}},
    "exp21": {"_global": {"formulas": [{"title": "显微镜原理", "steps": [{"note": "总放大倍率：", "formula": r"M = \frac{\Delta}{f_o} \times \frac{250}{f_e}"}]}], "variables": [{"symbol": "M", "description": "<strong>总放大倍率</strong>（待求量）", "unit": "无单位"}, {"symbol": r"\Delta", "description": "光学筒长", "unit": "mm"}]}},
    "exp22": {"_global": {"formulas": [{"title": "衍射实验", "steps": [{"note": "单缝衍射暗纹条件：", "formula": r"a\sin\theta = k\lambda"}, {"note": "小角度近似条纹间距：", "formula": r"\Delta x = \frac{f\lambda}{a}"}]}], "variables": [{"symbol": "a", "description": "单缝宽度", "unit": "m"}, {"symbol": r"\lambda", "description": "光波长", "unit": "m"}]}},
    "exp23": {"_global": {"formulas": [{"title": "光电效应", "steps": [{"note": "<strong>爱因斯坦光电方程</strong>：", "formula": r"h\nu = \frac{1}{2}mv_{\max}^2 + W"}, {"note": "截止电压与频率：", "formula": r"U_s = \frac{h}{e}\nu - \frac{W}{e}"}]}], "variables": [{"symbol": "h", "description": "<strong>普朗克常量</strong>（待求量）", "unit": "J·s"}, {"symbol": r"\nu", "description": "入射光频率", "unit": "Hz"}, {"symbol": "U_s", "description": "截止电压", "unit": "V"}]}},
    "exp24": {"_global": {"formulas": [{"title": "密立根油滴", "steps": [{"note": "油滴电荷量（平衡法）：", "formula": r"q = \frac{mgd}{V}\left(1 + \frac{b}{pa}\right)^{3/2}"}, {"note": "验证电荷量子化：q = ne", "formula": None}]}], "variables": [{"symbol": "q", "description": "<strong>油滴电荷量</strong>（待求量）", "unit": "C"}, {"symbol": "V", "description": "极板电压", "unit": "V"}, {"symbol": "d", "description": "极板间距", "unit": "m"}]}},
    "exp25": {"_global": {"formulas": [{"title": "生活中的物理", "steps": [{"note": "本实验涵盖多个生活场景中的物理原理。", "formula": None}]}], "variables": [{"symbol": "—", "description": "具体物理量视实验项目而定", "unit": "—"}]}},

    # ── exp26-exp50: 二级实验，有表格 ──
    "exp26": {
    "table1": {
        "formulas": [
            {
                "title": "磁阻效应",
                "steps": [
                    {
                        "note": "磁阻相对变化率：",
                        "formula": "\\frac{\\Delta R}{R_0} = \\frac{R(B) - R(0)}{R(0)}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I_M",
                "description": "励磁电流（产生磁场的电磁铁线圈电流），与磁感应强度 B 成正比",
                "unit": "A"
            },
            {
                "symbol": "R",
                "description": "磁场 B 下的磁阻元件电阻实测值",
                "unit": "Ω"
            },
            {
                "symbol": "\\Delta R",
                "description": "磁阻相对变化率 ΔR/R(0)，即电阻相对零磁场电阻 R(0) 的变化率",
                "unit": ""
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "I_M",
                "description": "励磁电流（产生磁场的电磁铁线圈电流），与磁感应强度 B 成正比",
                "unit": "A"
            },
            {
                "symbol": "R",
                "description": "电阻值",
                "unit": "Ω"
            },
            {
                "symbol": "\\Delta R",
                "description": "磁阻相对变化率 ΔR/R(0)，即电阻相对零磁场电阻 R(0) 的变化率",
                "unit": ""
            }
        ]
    }
},
    "exp27": {
    "table1": {
        "formulas": [
            {
                "title": "非平衡电桥",
                "steps": [
                    {
                        "note": "电桥输出电压：",
                        "formula": "U_{out} = V_s \\left(\\frac{R_2}{R_1+R_2} - \\frac{R_4}{R_3+R_4}\\right)"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "桥臂可调电阻 R4（电阻箱读数），偏离平衡电阻 R₀ 时电桥输出非零电压",
                "unit": "Ω"
            },
            {
                "symbol": "U_g",
                "description": "电桥输出电压（实测值），平衡时约为零",
                "unit": "mV"
            },
            {
                "symbol": "δ=ΔR/R₀",
                "description": "桥臂电阻相对平衡电阻 R₀ 的相对变化 δ=ΔR/R₀",
                "unit": ""
            },
            {
                "symbol": "U_{g,lin}",
                "description": "线性近似输出电压（=Us/4·δ），与实测值比较确定线性范围",
                "unit": "mV"
            },
            {
                "symbol": "\\delta_lin",
                "description": "线性近似电压相对实测输出电压的偏差百分比",
                "unit": "%"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "R",
                "description": "桥臂可调电阻 R4（电阻箱读数），偏离平衡电阻 R₀ 时电桥输出非零电压",
                "unit": "Ω"
            },
            {
                "symbol": "U_g",
                "description": "电桥输出电压（实测值），平衡时约为零",
                "unit": "mV"
            },
            {
                "symbol": "δ=ΔR/R₀",
                "description": "桥臂电阻相对平衡电阻 R₀ 的相对变化 δ=ΔR/R₀",
                "unit": ""
            },
            {
                "symbol": "U_{g,lin}",
                "description": "线性近似输出电压（=Us/4·δ），与实测值比较确定线性范围",
                "unit": "mV"
            },
            {
                "symbol": "\\delta_lin",
                "description": "线性近似电压相对实测输出电压的偏差百分比",
                "unit": "%"
            }
        ]
    }
},
    "exp28": {
    "table1": {
        "formulas": [
            {
                "title": "霍尔电压测量",
                "steps": [
                    {
                        "note": "<strong>霍尔电压</strong>：",
                        "formula": "V_H = K_H I_H B"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I_S",
                "description": "霍尔元件控制电流（工作电流）",
                "unit": "mA"
            },
            {
                "symbol": "V",
                "description": "换向法（对称测量）四组霍尔电压读数之一 V1~V4，取绝对值平均得霍尔电压",
                "unit": "mV"
            },
            {
                "symbol": "V_H",
                "description": "霍尔电压（由四组对称测量读数计算，待求量）",
                "unit": "mV"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "霍尔灵敏度测定",
                "steps": [
                    {
                        "note": "由 V<sub>H</sub>-I<sub>H</sub> 图斜率求 K<sub>H</sub>：",
                        "formula": "K_H = \\frac{\\Delta V_H}{\\Delta I_H \\cdot B}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I_M",
                "description": "励磁电流（产生磁感应强度 B 的电磁铁电流）",
                "unit": "A"
            },
            {
                "symbol": "V_H",
                "description": "霍尔电压（控制电流固定时随励磁电流变化）",
                "unit": "mV"
            }
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "电导率测量",
                "steps": [
                    {
                        "note": "电导率与载流子浓度、迁移率的关系：",
                        "formula": "\\sigma = ne\\mu"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "霍尔样品温度（变温霍尔测量）",
                "unit": "℃"
            },
            {
                "symbol": "R_H",
                "description": "霍尔系数（反映载流子浓度，随温度升高而下降）",
                "unit": "m³/C"
            }
        ]
    }
},
    "exp29": {
    "table1": {
        "formulas": [
            {
                "title": "RLC 串联谐振",
                "steps": [
                    {
                        "note": "谐振条件：",
                        "formula": "f_0 = \\frac{1}{2\\pi\\sqrt{LC}}"
                    },
                    {
                        "note": "品质因数：",
                        "formula": "Q = \\frac{1}{R}\\sqrt{\\frac{L}{C}}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "f",
                "description": "信号频率（正弦信号源扫频，用于幅频特性测量）",
                "unit": "kHz"
            },
            {
                "symbol": "V_{i,pp}",
                "description": "输入信号电压峰峰值（本实验固定约 2.0 V）",
                "unit": "V"
            },
            {
                "symbol": "V_{R,pp}",
                "description": "电阻 R 两端电压峰峰值（正比于回路电流）",
                "unit": "V"
            },
            {
                "symbol": "I_{pp}",
                "description": "回路电流峰峰值（由 Ipp=VR,pp/R 计算）",
                "unit": "mA"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "f",
                "description": "信号频率（正弦信号源扫频，用于幅频特性测量）",
                "unit": "kHz"
            },
            {
                "symbol": "V_R",
                "description": "电阻两端电压",
                "unit": "V"
            },
            {
                "symbol": "V_{i,pp}",
                "description": "输入信号电压峰峰值（本实验固定约 2.0 V）",
                "unit": "V"
            },
            {
                "symbol": "I_{pp}",
                "description": "回路电流峰峰值（由 Ipp=VR,pp/R 计算）",
                "unit": "mA"
            }
        ]
    },
    "table3": {
        "formulas": [],
        "variables": [
            {
                "symbol": "Q",
                "description": "品质因数（三点法、电压法、理论值三种方法计算结果的对比）",
                "unit": ""
            }
        ]
    }
},
    "exp30": {
    "table1": {
        "formulas": [
            {
                "title": "电容与介电常数",
                "steps": [
                    {
                        "note": "平行板电容：",
                        "formula": "C = \\frac{\\varepsilon_r \\varepsilon_0 A}{d}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "C",
                "description": "样品电容（电容表直接读数）",
                "unit": "pF"
            },
            {
                "symbol": "d",
                "description": "固体样品厚度",
                "unit": "mm"
            },
            {
                "symbol": "S",
                "description": "极板有效面积",
                "unit": "cm²"
            },
            {
                "symbol": "\\varepsilon_r",
                "description": "固体样品的相对介电常数（待求量）",
                "unit": ""
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "d",
                "description": "固体样品厚度",
                "unit": "mm"
            },
            {
                "symbol": "S",
                "description": "极板有效面积",
                "unit": "cm²"
            },
            {
                "symbol": "C",
                "description": "电容读数（C1 为无样品空气间隙、C2 为插入样品后的电容）",
                "unit": "pF"
            },
            {
                "symbol": "\\varepsilon_r",
                "description": "固体样品的相对介电常数（固定极板间距法，待求量）",
                "unit": ""
            }
        ]
    },
    "table3": {
        "formulas": [],
        "variables": [
            {
                "symbol": "C",
                "description": "电容表读数（C11/C12 为空气状态初终态，C21/C22 为液体状态初终态）",
                "unit": "pF"
            },
            {
                "symbol": "\\varepsilon_r",
                "description": "液体相对介电常数（由两次电容变化之比计算）",
                "unit": ""
            }
        ]
    }
},
    "exp31": {
    "table1": {
        "formulas": [
            {
                "title": "电流表改装",
                "steps": [
                    {
                        "note": "分流电阻：",
                        "formula": "R_s = \\frac{I_g r_g}{I - I_g}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "电压表各档的满量程电压（量程）",
                "unit": "mV/V"
            },
            {
                "symbol": "R_s",
                "description": "串联分压电阻阻值（由量程、表头内阻与满偏电流计算）",
                "unit": "kΩ/MΩ"
            },
            {
                "symbol": "R_g",
                "description": "表头内阻（组装电压表的内阻）",
                "unit": "kΩ/MΩ"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "电压表改装",
                "steps": [
                    {
                        "note": "分压电阻：",
                        "formula": "R_H = \\frac{V - I_g r_g}{I_g}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R_s",
                "description": "测量回路中串联的电源内阻（使电压表读数偏低）",
                "unit": "kΩ/MΩ"
            },
            {
                "symbol": "U_s",
                "description": "标准电压表读数（被测电压的真实值）",
                "unit": "V"
            },
            {
                "symbol": "U_o",
                "description": "改装电压表读数（受电压表内阻分压影响）",
                "unit": "V"
            },
            {
                "symbol": "\\delta",
                "description": "电压表内阻引起的相对测量误差",
                "unit": "%"
            }
        ]
    }
},
    "exp32": {
    "table1": {
        "formulas": [
            {
                "title": "双臂电桥",
                "steps": [
                    {
                        "note": "消除接触电阻影响：",
                        "formula": "R_x = R_s \\frac{R_2}{R_1}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "D_{Cu}",
                "description": "铜棒直径（多次测量取平均）",
                "unit": "mm"
            },
            {
                "symbol": "D_{Al}",
                "description": "铝棒直径（多次测量取平均）",
                "unit": "mm"
            }
        ]
    },
    "table2": {
        "formulas": [],
        "variables": [
            {
                "symbol": "R_{Cu}",
                "description": "铜棒的电阻读数（正向 R_Cu+ 与反向 R_Cu−，取平均消除热电势）",
                "unit": "Ω"
            },
            {
                "symbol": "R_{Al}",
                "description": "铝棒的电阻读数（正向 R_Al+ 与反向 R_Al−，取平均消除热电势）",
                "unit": "Ω"
            }
        ]
    },
    "table3": {
        "formulas": [],
        "variables": [
            {
                "symbol": "L",
                "description": "电压头间距（被测长度）",
                "unit": "cm"
            },
            {
                "symbol": "R",
                "description": "电桥读数电阻（正向 R₊ 与反向 R₋，取平均）",
                "unit": "Ω"
            },
            {
                "symbol": "R_x",
                "description": "待测低电阻（正反向读数平均后换算，Rx=R×10⁻⁶Ω）",
                "unit": "mΩ"
            },
            {
                "symbol": "\\rho",
                "description": "该长度处的电阻率（ρ=Rx·πD²/(4L)）",
                "unit": "10⁻⁸Ω·m"
            }
        ]
    },
    "table4": {
        "formulas": [],
        "variables": [
            {
                "symbol": "L",
                "description": "电压头间距（被测长度）",
                "unit": "cm"
            },
            {
                "symbol": "R",
                "description": "电桥读数电阻（正向 R₊ 与反向 R₋，取平均）",
                "unit": "Ω"
            },
            {
                "symbol": "R_x",
                "description": "待测低电阻（正反向读数平均后换算，Rx=R×10⁻⁶Ω）",
                "unit": "mΩ"
            },
            {
                "symbol": "\\rho",
                "description": "该长度处的电阻率（ρ=Rx·πD²/(4L)）",
                "unit": "10⁻⁸Ω·m"
            }
        ]
    }
},

    # ── exp33-exp38: 复杂表格实验 ──
    "exp34": {
    "_global": {
        "formulas": [
            {
                "title": "光纤传感器",
                "steps": [
                    {
                        "note": "全反射临界角：",
                        "formula": "\\sin\\theta_c = \\frac{n_2}{n_1}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\theta_c",
                "description": "<strong>全反射临界角</strong>",
                "unit": "rad"
            },
            {
                "symbol": "n_1",
                "description": "纤芯折射率",
                "unit": "无单位"
            },
            {
                "symbol": "n_2",
                "description": "包层折射率",
                "unit": "无单位"
            }
        ]
    },
    "transmission_longitudinal": {
        "variables": [
            {
                "symbol": "x",
                "description": "光纤探头纵向位置读数（透射式纵向位移传感）",
                "unit": "mm"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随被测位移变化）",
                "unit": ""
            }
        ]
    },
    "transmission_left": {
        "variables": [
            {
                "symbol": "y",
                "description": "光纤探头横向位置读数（相对最大功率位置 y₀ 向左的位移）",
                "unit": "mm"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随被测位移变化）",
                "unit": ""
            }
        ]
    },
    "transmission_right": {
        "variables": [
            {
                "symbol": "y",
                "description": "光纤探头横向位置读数（相对最大功率位置 y₀ 向右的位移）",
                "unit": "mm"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随被测位移变化）",
                "unit": ""
            }
        ]
    },
    "reflection": {
        "variables": [
            {
                "symbol": "x",
                "description": "光纤探头到反射镜的纵向距离（反射式位移传感）",
                "unit": "mm"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随探头到反射镜距离变化）",
                "unit": ""
            }
        ]
    },
    "microbend": {
        "variables": [
            {
                "symbol": "x",
                "description": "微弯器位移量（弯曲深度，微弯位移传感）",
                "unit": "mm"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随弯曲深度变化）",
                "unit": ""
            }
        ]
    },
    "voltage": {
        "variables": [
            {
                "symbol": "U",
                "description": "施加在电光晶体上的外加电压（电压传感），相邻极值电压差估算半波电压",
                "unit": "V"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随外加电压变化）",
                "unit": ""
            }
        ]
    },
    "current": {
        "variables": [
            {
                "symbol": "I",
                "description": "导线中电流（电流传感，光功率随电流平方变化）",
                "unit": "A"
            },
            {
                "symbol": "P",
                "description": "光纤接收端的光功率读数（随导线电流变化）",
                "unit": ""
            }
        ]
    }
},
    "exp35": {
    "_global": {
        "formulas": [
            {
                "title": "迈克尔逊干涉仪",
                "steps": [
                    {
                        "note": "移动反射镜 Δd，条纹变化数 N：",
                        "formula": "\\Delta d = N \\cdot \\frac{\\lambda}{2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\Delta d",
                "description": "反射镜移动距离",
                "unit": "m"
            },
            {
                "symbol": "N",
                "description": "条纹变化数",
                "unit": "无单位"
            },
            {
                "symbol": "\\lambda",
                "description": "<strong>光波长</strong>（待求量）",
                "unit": "m"
            }
        ]
    },
    "wavelength": {
        "variables": [
            {
                "symbol": "S",
                "description": "M₁镜的测微螺旋位置读数（第 n 次），相邻两次读数差对应固定条纹数",
                "unit": "mm"
            },
            {
                "symbol": "\\Delta S",
                "description": "相邻两次测量的 M₁ 镜位置差（对应一次条纹计数的镜移动量）",
                "unit": "μm"
            }
        ]
    },
    "film": {
        "variables": [
            {
                "symbol": "S",
                "description": "M₁镜的测微螺旋位置读数（S₀ 为无样品、S₁ 为加样品时的位置）",
                "unit": "mm"
            },
            {
                "symbol": "\\Delta d",
                "description": "无样品与加样品时 M₁ 镜的位置之差（用于计算薄片折射率）",
                "unit": "mm"
            },
            {
                "symbol": "t",
                "description": "螺旋测微计薄片厚度原始读数",
                "unit": "mm"
            },
            {
                "symbol": "l",
                "description": "零点修正后的薄片厚度（l=读数−零点）",
                "unit": "mm"
            }
        ]
    }
},
    "exp36": {
    "_global": {
        "formulas": [
            {
                "title": "马吕斯定律",
                "steps": [
                    {
                        "note": "<strong>马吕斯定律</strong>：",
                        "formula": "I = I_0 \\cos^2\\theta"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "I",
                "description": "透过检偏器后的光强",
                "unit": "W/m²"
            },
            {
                "symbol": "I_0",
                "description": "入射偏振光光强",
                "unit": "W/m²"
            },
            {
                "symbol": "\\theta",
                "description": "偏振方向与检偏器透光轴夹角",
                "unit": "rad"
            }
        ]
    },
    "malus": {
        "variables": [
            {
                "symbol": "\\theta",
                "description": "起偏器与检偏器透振方向的夹角（马吕斯定律验证）",
                "unit": "°"
            },
            {
                "symbol": "I",
                "description": "透过检偏器后的透射光强读数（相对值）",
                "unit": ""
            }
        ]
    },
    "brewster": {
        "variables": [
            {
                "symbol": "\\theta_B",
                "description": "布儒斯特角（反射光完全偏振时的入射角，重复测量取平均）",
                "unit": "°"
            }
        ]
    }
},
    "exp37": {
    "_global": {
        "formulas": [
            {
                "title": "光栅方程",
                "steps": [
                    {
                        "note": "光栅衍射条件：",
                        "formula": "d(\\sin\\alpha + \\sin\\beta) = k\\lambda"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "d",
                "description": "光栅常数",
                "unit": "m"
            },
            {
                "symbol": "\\lambda",
                "description": "<strong>光波长</strong>（待求量）",
                "unit": "m"
            },
            {
                "symbol": "k",
                "description": "衍射级次",
                "unit": "无单位"
            }
        ]
    },
    "spectrograph_standard": {
        "variables": [
            {
                "symbol": "x",
                "description": "标准谱线峰中心在拼接谱图中的像素坐标（用于像素—波长定标）",
                "unit": "px"
            },
            {
                "symbol": "\\lambda",
                "description": "标准谱线的已知波长（查阅谱线表）",
                "unit": "nm"
            }
        ]
    },
    "spectrograph_unknown": {
        "variables": [
            {
                "symbol": "x",
                "description": "待测谱线峰中心在拼接谱图中的像素坐标",
                "unit": "px"
            },
            {
                "symbol": "\\lambda",
                "description": "待测谱线的参考波长（已知近似值，可留空）",
                "unit": "nm"
            }
        ]
    },
    "monochromator_calibration": {
        "variables": [
            {
                "symbol": "\\lambda_m",
                "description": "单色仪的未校准波长读数（校准拟合的自变量）",
                "unit": "nm"
            },
            {
                "symbol": "\\lambda_s",
                "description": "校准用已知谱线的标准波长（拟合的目标值）",
                "unit": "nm"
            }
        ]
    },
    "monochromator_scan": {
        "variables": [
            {
                "symbol": "\\lambda_m",
                "description": "扫描点的单色仪波长读数（未校准，需经校准曲线修正）",
                "unit": "nm"
            },
            {
                "symbol": "I",
                "description": "探测器信号光强（发射或透射光强）",
                "unit": ""
            },
            {
                "symbol": "I_r",
                "description": "吸收测量时的入射参考光强（透射率=信号/参考光强）",
                "unit": ""
            }
        ]
    }
},
    "exp38": {
    "_global": {
        "formulas": [
            {
                "title": "双光栅实验",
                "steps": [
                    {
                        "note": "莫尔条纹间距：",
                        "formula": "D = \\frac{d}{\\theta}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "D",
                "description": "<strong>莫尔条纹间距</strong>",
                "unit": "m"
            },
            {
                "symbol": "d",
                "description": "光栅常数",
                "unit": "m"
            },
            {
                "symbol": "\\theta",
                "description": "两光栅夹角",
                "unit": "rad"
            }
        ]
    },
    "grating": {
        "variables": [
            {
                "symbol": "\\theta",
                "description": "分光计游标角度读数（±1级亮纹位置，左右游标读数平均可消除偏心差）",
                "unit": "°"
            }
        ]
    },
    "lau": {
        "variables": [
            {
                "symbol": "\\theta_s",
                "description": "标准样品转角测量的游标角度读数（初始与末态读数之差为转角）",
                "unit": "°"
            },
            {
                "symbol": "\\theta_u",
                "description": "待测样品转角测量的游标角度读数（初始与末态读数之差为转角）",
                "unit": "°"
            }
        ]
    }
},

    # ── exp39-exp50: 二级实验 ──
    "exp39": {
    "table1": {
        "formulas": [
            {
                "title": "弗兰克-赫兹实验（氩管）",
                "steps": [
                    {
                        "note": "电子被加速电压 U<sub>G2K</sub> 加速，能量达到氩原子第一激发能时发生非弹性碰撞，板极电流 I<sub>p</sub> 随 U<sub>G2K</sub> 变化出现等间隔的峰值。相邻峰位电压差即第一激发电位：",
                        "formula": "\\Delta U = U_{n+1} - U_n"
                    },
                    {
                        "note": "第一激发电位取相邻峰位间隔的平均值（或峰位-序数最小二乘拟合的斜率）：",
                        "formula": "\\overline{\\Delta U} = \\frac{1}{N-1}\\sum_{n=1}^{N-1}(U_{n+1} - U_n)"
                    },
                    {
                        "note": "氩原子第一激发态与基态能级差（第一激发能）：",
                        "formula": "E = e \\cdot \\overline{\\Delta U}"
                    },
                    {
                        "note": "受激原子退激辐射的波长：",
                        "formula": "\\lambda = \\frac{hc}{E}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_GK",
                "description": "第二栅极电压（加速电压）U_G2K，电子在阴极 K 与第二栅极 G2 之间被加速",
                "unit": "V"
            },
            {
                "symbol": "I_p",
                "description": "板极电流（微电流仪测得，随加速电压出现等间隔峰值）",
                "unit": "nA"
            }
        ]
    }
},
    "exp40": {
    "table1": {
        "formulas": [
            {
                "title": "杨氏模量及泊松比",
                "steps": [
                    {
                        "note": "杨氏模量：",
                        "formula": "E = \\frac{\\sigma}{\\varepsilon} = \\frac{F/A}{\\Delta L/L}"
                    },
                    {
                        "note": "泊松比：",
                        "formula": "\\nu = -\\frac{\\varepsilon_{\\text{横向}}}{\\varepsilon_{\\text{纵向}}}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "F",
                "description": "拉力（加载的砝码重力）",
                "unit": "N"
            },
            {
                "symbol": "\\Delta L",
                "description": "轴向伸长量（纵向形变，加载后金属丝长度的改变量）",
                "unit": "mm"
            },
            {
                "symbol": "\\Delta D",
                "description": "横向形变量（直径方向的改变，拉伸时收缩为负值）",
                "unit": "mm"
            }
        ]
    }
},
    "exp41": {
    "table1": {
        "formulas": [
            {
                "title": "超声光栅",
                "steps": [
                    {
                        "note": "超声波形成相位光栅：",
                        "formula": "\\Lambda \\sin\\theta = k\\lambda"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "f",
                "description": "超声频率（信号发生器驱动换能器的频率）",
                "unit": "MHz"
            },
            {
                "symbol": "\\Delta x",
                "description": "衍射条纹间距（0 级到 k 级条纹的间距）",
                "unit": "mm"
            },
            {
                "symbol": "k",
                "description": "衍射级次",
                "unit": ""
            }
        ]
    }
},
    "exp42": {
    "table1": {
        "formulas": [
            {
                "title": "超声定位",
                "steps": [
                    {
                        "note": "回波测距：",
                        "formula": "d = \\frac{v \\cdot t}{2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "f",
                "description": "超声频率（信号发生器驱动换能器的频率）",
                "unit": "MHz"
            },
            {
                "symbol": "\\Delta x",
                "description": "衍射条纹间距（0 级到 k 级条纹的间距）",
                "unit": "mm"
            },
            {
                "symbol": "k",
                "description": "衍射级次",
                "unit": ""
            }
        ]
    }
},
    "exp43": {
        "table1": {
            "formulas": [
                {
                    "title": "圆盘转动惯量",
                    "steps": [
                        {
                            "note": "由三线悬点等边三角形的边长求悬点圆半径：",
                            "formula": "r=\\frac{a}{\\sqrt{3}},\\qquad R=\\frac{b}{\\sqrt{3}}"
                        },
                        {
                            "note": "三线摆测圆盘转动惯量：",
                            "formula": "I_0=\\frac{m_0gRrT_0^2}{4\\pi^2H},\\qquad T_0=\\frac{50T_0}{50}"
                        }
                    ]
                }
            ],
        "variables": [
            {
                "symbol": "m_0",
                "description": "下圆盘质量",
                "unit": "g"
            },
            {
                "symbol": "a,b",
                "description": "上、下圆盘悬点间距",
                "unit": "cm"
            },
            {
                "symbol": "H",
                "description": "上下两圆盘间的垂直距离",
                "unit": "cm"
            },
            {
                "symbol": "R",
                "description": "下圆盘上悬点所在圆的半径",
                "unit": "cm"
            },
            {
                "symbol": "T",
                "description": "摆动周期：下圆盘（三线摆）扭摆运动的周期",
                "unit": "s"
            }
        ]
    },
    "table2": {
        "formulas": [
            {
                "title": "圆环转动惯量",
                "steps": [
                    {
                        "note": "由加环系统与空盘的转动惯量之差求圆环转动惯量：",
                        "formula": "I_{环}=\\frac{(m_0+m_1)gRr(T_1^2-T_0^2)}{4\\pi^2H}"
                    },
                    {
                        "note": "均匀圆环的理论值：",
                        "formula": "I_{理论}=\\frac{m_1(D_{内}^2+D_{外}^2)}{8}"
                    }
                ]
            }
        ],
        "variables": [
            {"symbol": "m_1", "description": "圆环质量", "unit": "g"},
            {"symbol": "D_{内},D_{外}", "description": "圆环内、外直径", "unit": "cm"},
            {"symbol": "T_1", "description": "加圆环后的摆动周期", "unit": "s"}
        ]
    },
    "table3": {
        "formulas": [
            {
                "title": "平行轴定理与线性拟合",
                "steps": [
                    {
                        "note": "偏离质心轴 d 后的转动惯量：",
                        "formula": "I_d=I_c+md^2"
                    },
                    {
                        "note": "对 I_d-d^2 作最小二乘直线拟合：",
                        "formula": "I_d=kd^2+b，\\qquad k\\approx m"
                    }
                ]
            }
        ],
        "variables": [
            {"symbol": "d", "description": "圆柱质心到中心转轴的距离", "unit": "cm"},
            {"symbol": "I_d", "description": "距中心转轴 d 时两圆柱的转动惯量", "unit": "g·cm²"},
            {"symbol": "k", "description": "I_d-d² 拟合斜率，用于求质量", "unit": "g"}
        ]
    }
},
    "exp44": {
    "table1": {
        "formulas": [
            {
                "title": "凯特摆",
                "steps": [
                    {
                        "note": "复摆周期：",
                        "formula": "T = 2\\pi\\sqrt{\\frac{I}{mgh}}"
                    },
                    {
                        "note": "凯特摆可逆条件：",
                        "formula": "g = \\frac{4\\pi^2 L_{\\text{eff}}}{T^2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "摆动周期（正挂与倒挂时的周期应调节至基本相等）",
                "unit": "s"
            },
            {
                "symbol": "h",
                "description": "刀口到摆重心的距离（h1 为正挂刀口、h2 为倒挂刀口，等效摆长 L_eff = h1 + h2）",
                "unit": "cm"
            }
        ]
    }
},
    "exp45": {
    "table1": {
        "formulas": [
            {
                "title": "空气阻尼振动",
                "steps": [
                    {
                        "note": "阻尼振动方程：",
                        "formula": "x(t) = A_0 e^{-\\beta t}\\cos(\\omega t + \\varphi)"
                    },
                    {
                        "note": "阻尼系数：",
                        "formula": "\\beta = \\frac{1}{T}\\ln\\frac{A_n}{A_{n+1}}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "时刻（振幅衰减过程中的时间读数）",
                "unit": "s"
            },
            {
                "symbol": "A",
                "description": "振幅（振动物体偏离平衡位置的最大位移，随时间按指数规律衰减）",
                "unit": ""
            }
        ]
    }
},
    "exp46": {
    "steady": {
        "formulas": [
            {
                "title": "傅里叶热传导定律",
                "steps": [
                    {
                        "note": "物体内存在温度梯度时，传热速率正比于温度梯度与截面积：",
                        "formula": "\\frac{dQ}{dt} = -\\lambda S \\frac{dT}{dx}"
                    }
                ]
            },
            {
                "title": "稳态法（李氏法）",
                "steps": [
                    {
                        "note": "厚度 h<sub>B</sub>、截面积 S 的平板样品，两盘温度恒定 T<sub>1</sub>、T<sub>2</sub> 时：",
                        "formula": "\\frac{dQ}{dt} = \\lambda \\frac{S(T_1 - T_2)}{h_B}"
                    },
                    {
                        "note": "稳定导热条件下，经样品盘传入的热流等于散热盘 A 向环境的散热率，因此测散热率即可得到传热率",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "稳态温度（上盘 T1 为发热盘、下盘 T2 为散热盘，10 分钟内变化不超过 0.5 °C 判稳）",
                "unit": "°C"
            }
        ]
    },
    "cooling": {
        "formulas": [
            {
                "title": "散热率的面积修正",
                "steps": [
                    {
                        "note": "散热速率与散热面积成正比；稳态时 A 盘经下表面与侧面散热，自由冷却时经上下表面与侧面散热：",
                        "formula": "\\frac{dQ}{dt} = m_{\\text{铜}} c_{\\text{铜}} \\frac{dT}{dt} \\cdot \\frac{R_B + 2h_A}{2R_B + 2h_A}"
                    }
                ]
            },
            {
                "title": "导热系数计算公式（指导书公式 6）",
                "steps": [
                    {
                        "note": "冷却速率 dT/dt 由 T(t) 在 T₂ 附近的最小二乘拟合斜率得到",
                        "formula": None
                    },
                    {
                        "note": "结合稳态热流方程得：",
                        "formula": "\\lambda = \\frac{m_{\\text{铜}} c_{\\text{铜}} h_B}{(T_1 - T_2) \\pi R_B^2} \\cdot \\frac{R_B + 2h_A}{2R_B + 2h_A} \\cdot \\frac{dT}{dt}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "冷却时间（移去样品盘后自然冷却，每 30 s 记录一次）",
                "unit": "s"
            },
            {
                "symbol": "T",
                "description": "冷却过程中黄铜盘 A 的温度",
                "unit": "°C"
            }
        ]
    },
    "calib": {
        "formulas": [
            {
                "title": "热电偶定标",
                "steps": [
                    {
                        "note": "温差电动势与两接点温差近似成正比：",
                        "formula": "E_x \\approx a(t - t_0)"
                    },
                    {
                        "note": "铜-康铜热电偶温差电系数约 0.04 mV/K，定标拟合斜率即 a",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "T",
                "description": "水浴温度（热电偶热端温度，冷端为冰水混合物 0 °C）",
                "unit": "°C"
            },
            {
                "symbol": "E",
                "description": "温差电动势（由电压表测得）",
                "unit": "mV"
            }
        ]
    },
    "metal": {
        "formulas": [
            {
                "title": "金属棒热导率",
                "steps": [
                    {
                        "note": "恒功率加热，热流量等于加热功率：",
                        "formula": "P = UI"
                    },
                    {
                        "note": "由傅里叶定律得热导率：",
                        "formula": "\\lambda = \\frac{P h}{S \\Delta T}"
                    },
                    {
                        "note": "金属棒截面积：",
                        "formula": "S = \\frac{\\pi d^2}{4}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "h",
                "description": "两温度传感器间距（10 cm 或 5 cm）",
                "unit": "cm"
            },
            {
                "symbol": "U",
                "description": "加热电压（恒功率加热金属棒）",
                "unit": "V"
            },
            {
                "symbol": "I",
                "description": "加热电流",
                "unit": "A"
            },
            {
                "symbol": "T",
                "description": "金属棒两端温度（T1 为热端、T2 为冷端）",
                "unit": "°C"
            }
        ]
    }
},
    "exp47": {
    "_global": {
        "formulas": [
            {
                "title": "静态接触角与 Young 方程",
                "steps": [
                    {
                        "note": "气-液-固三相交界处，界面张力在水平方向平衡（Young 方程）：",
                        "formula": "\\gamma_{sv} = \\gamma_{sl} + \\gamma_{lv}\\cos\\theta"
                    },
                    {
                        "note": "粘附功（润湿功）：",
                        "formula": "W_a = \\gamma_{lv}(1+\\cos\\theta)"
                    },
                    {
                        "note": "浸润性判据：",
                        "formula": "\\theta<90^\\circ \\text{ 亲水};\\quad \\theta>90^\\circ \\text{ 疏水};\\quad \\theta>150^\\circ \\text{ 超疏水}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\theta",
                "description": "<strong>接触角</strong>（待求量）",
                "unit": "°"
            },
            {
                "symbol": "\\gamma_{sv}",
                "description": "固-气界面张力（固体表面自由能）",
                "unit": "mN/m"
            },
            {
                "symbol": "\\gamma_{sl}",
                "description": "固-液界面张力",
                "unit": "mN/m"
            },
            {
                "symbol": "\\gamma_{lv}",
                "description": "液-气界面张力（水的表面张力，20 °C 时 72.8 mN/m）",
                "unit": "mN/m"
            },
            {
                "symbol": "W_a",
                "description": "粘附功（润湿功）",
                "unit": "mN/m"
            }
        ]
    },
    "geometry": {
        "formulas": [
            {
                "title": "θ/2 法（影像分析法）",
                "steps": [
                    {
                        "note": "小液滴近似球冠，由几何关系得接触角：",
                        "formula": "\\theta = 2\\arctan\\frac{2h}{d}"
                    },
                    {
                        "note": "h 为液滴高度，d 为固-液接触直径（停滴法 θ/2）。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "h",
                "description": "液滴高度",
                "unit": "mm"
            },
            {
                "symbol": "d",
                "description": "固-液接触直径",
                "unit": "mm"
            },
            {
                "symbol": "\\theta",
                "description": "<strong>接触角</strong>（几何法待求量）",
                "unit": "°"
            }
        ]
    },
    "dynamic": {
        "formulas": [
            {
                "title": "动态接触角与滞后",
                "steps": [
                    {
                        "note": "前进角与后退角之差为接触角滞后：",
                        "formula": "\\Delta\\theta = \\theta_A - \\theta_R"
                    },
                    {
                        "note": "滞后越大，三相接触线越难移动，液滴越不易从表面滚落。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "\\theta_A",
                "description": "<strong>前进接触角</strong>",
                "unit": "°"
            },
            {
                "symbol": "\\theta_R",
                "description": "<strong>后退接触角</strong>",
                "unit": "°"
            },
            {
                "symbol": "\\Delta\\theta",
                "description": "<strong>接触角滞后</strong>（待求量）",
                "unit": "°"
            },
            {
                "symbol": "\\alpha",
                "description": "起始滑动（滚动）角",
                "unit": "°"
            }
        ]
    },
    "static": {
        "variables": [
            {
                "symbol": "\\theta_L",
                "description": "左接触角（液滴左侧三相接触线的接触角）",
                "unit": "°"
            },
            {
                "symbol": "\\theta_R",
                "description": "右接触角（液滴右侧三相接触线的接触角）",
                "unit": "°"
            },
            {
                "symbol": "\\bar{\\theta}",
                "description": "仪器平均接触角（θ̄_仪，可留空时自动取左右角平均）",
                "unit": "°"
            }
        ]
    }
},
    "exp48": {
    "_global": {
        "formulas": [
            {
                "title": "电阻应变效应",
                "steps": [
                    {
                        "note": "金属导体电阻：",
                        "formula": "R = \\rho\\frac{l}{A}"
                    },
                    {
                        "note": "受力形变时电阻相对变化（K 为应变片灵敏系数，ε 为轴向应变）：",
                        "formula": "\\frac{\\Delta R}{R} = K\\varepsilon"
                    },
                    {
                        "note": "直流电桥输出电压（单臂 / 半桥 / 全桥，U₀ 为电源电压）：",
                        "formula": "U_o = U_0\\frac{\\Delta R}{4R},\\; U_0\\frac{\\Delta R}{2R},\\; U_0\\frac{\\Delta R}{R}"
                    },
                    {
                        "note": "电桥灵敏度（每单位 ΔR/R 的输出电压）：",
                        "formula": "S = \\frac{U_0}{4},\\; \\frac{U_0}{2},\\; U_0"
                    },
                    {
                        "note": "压阻效应（K_ρ 为压阻系数，σ 为应力）：",
                        "formula": "\\frac{\\Delta R}{R} \\approx \\frac{\\Delta\\rho}{\\rho} = K_\\rho\\sigma"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "应变片电阻",
                "unit": "Ω"
            },
            {
                "symbol": "\\Delta R",
                "description": "受力引起的电阻变化",
                "unit": "Ω"
            },
            {
                "symbol": "K",
                "description": "应变片灵敏系数",
                "unit": "—"
            },
            {
                "symbol": "\\varepsilon",
                "description": "轴向应变（常用单位 με = 10⁻⁶）",
                "unit": "με"
            },
            {
                "symbol": "U_0",
                "description": "电桥电源电压",
                "unit": "V"
            },
            {
                "symbol": "U_o",
                "description": "电桥输出电压",
                "unit": "mV"
            },
            {
                "symbol": "K_\\rho",
                "description": "压阻系数（表征材料压阻效应）",
                "unit": "—"
            },
            {
                "symbol": "\\sigma",
                "description": "材料所受应力",
                "unit": "Pa"
            }
        ]
    },
    "quarter": {
        "formulas": [
            {
                "title": "单臂电桥灵敏度",
                "steps": [
                    {
                        "note": "由标定数据最小二乘拟合求灵敏度：",
                        "formula": "S_1 = \\frac{\\Delta U_1}{\\Delta m}"
                    },
                    {
                        "note": "理论电桥灵敏度（每单位 ΔR/R）：",
                        "formula": "S_{th} = \\frac{U_0}{4}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "单臂电桥输出电压（万用表读数）",
                "unit": "mV"
            },
            {
                "symbol": "m",
                "description": "砝码质量（施加在应变梁自由端的载荷）",
                "unit": "g"
            }
        ]
    },
    "half": {
        "formulas": [
            {
                "title": "半桥灵敏度",
                "steps": [
                    {
                        "note": "由标定数据最小二乘拟合求灵敏度：",
                        "formula": "S_2 = \\frac{\\Delta U_2}{\\Delta m}"
                    },
                    {
                        "note": "理论电桥灵敏度（每单位 ΔR/R）：",
                        "formula": "S_{th} = \\frac{U_0}{2}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "半桥输出电压（万用表读数）",
                "unit": "mV"
            },
            {
                "symbol": "m",
                "description": "砝码质量（施加在应变梁自由端的载荷）",
                "unit": "g"
            }
        ]
    },
    "full": {
        "formulas": [
            {
                "title": "全桥灵敏度",
                "steps": [
                    {
                        "note": "由标定数据最小二乘拟合求灵敏度：",
                        "formula": "S_3 = \\frac{\\Delta U_3}{\\Delta m}"
                    },
                    {
                        "note": "理论电桥灵敏度（每单位 ΔR/R）：",
                        "formula": "S_{th} = U_0"
                    },
                    {
                        "note": "三种电桥灵敏度之比应满足：",
                        "formula": "S_1 : S_2 : S_3 = 1 : 2 : 4"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "全桥输出电压（万用表读数）",
                "unit": "mV"
            },
            {
                "symbol": "m",
                "description": "砝码质量（施加在应变梁自由端的载荷）",
                "unit": "g"
            }
        ]
    },
    "unknown": {
        "formulas": [
            {
                "title": "待测物质量",
                "steps": [
                    {
                        "note": "由全桥标定曲线反推待测物质量：",
                        "formula": "m_x = \\frac{U' - b}{S_3}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U'",
                "description": "放置待测物时全桥输出电压",
                "unit": "mV"
            },
            {
                "symbol": "b",
                "description": "全桥标定拟合截距",
                "unit": "mV"
            },
            {
                "symbol": "m_x",
                "description": "<strong>待测物质量</strong>（待求量）",
                "unit": "g"
            }
        ]
    },
    "pressure_pos": {
        "formulas": [
            {
                "title": "正压输出特性",
                "steps": [
                    {
                        "note": "由 U-P 数据拟合求正压灵敏度：",
                        "formula": "S_+ = \\frac{\\Delta U}{\\Delta P}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "P",
                "description": "正压力（真空压力表读数）",
                "unit": "kPa"
            },
            {
                "symbol": "U",
                "description": "传感器输出电压",
                "unit": "mV"
            },
            {
                "symbol": "S_+",
                "description": "<strong>正压灵敏度</strong>（待求量）",
                "unit": "mV/kPa"
            }
        ]
    },
    "pressure_neg": {
        "formulas": [
            {
                "title": "负压输出特性",
                "steps": [
                    {
                        "note": "由 U-P 数据拟合求负压灵敏度（P 按负值记录）：",
                        "formula": "S_- = \\frac{\\Delta U}{\\Delta P}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "P",
                "description": "负压力（真空泵抽气，取负值）",
                "unit": "kPa"
            },
            {
                "symbol": "U",
                "description": "传感器输出电压",
                "unit": "mV"
            },
            {
                "symbol": "S_-",
                "description": "<strong>负压灵敏度</strong>（待求量）",
                "unit": "mV/kPa"
            }
        ]
    },
    "components": {
        "formulas": [
            {
                "title": "元器件检测",
                "steps": [
                    {
                        "note": "硅二极管正向导通电压约 0.6~0.7 V。",
                        "formula": None
                    },
                    {
                        "note": "硅三极管发射结（B-E）、集电结（B-C）导通电压约 0.6~0.7 V。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_D",
                "description": "二极管导通电压",
                "unit": "V"
            },
            {
                "symbol": "U_{BE}",
                "description": "三极管基极-发射极导通电压",
                "unit": "V"
            },
            {
                "symbol": "U_{BC}",
                "description": "三极管基极-集电极导通电压",
                "unit": "V"
            }
        ]
    },
    "strain_record": {
        "formulas": [
            {
                "title": "应变片受力与电阻变化",
                "steps": [
                    {
                        "note": "应变片受拉伸时电阻增大，受压缩时电阻减小：",
                        "formula": "\\Delta R \\propto \\varepsilon"
                    },
                    {
                        "note": "双弯曲悬梁上、下表面应变片分别受拉、受压，构成差动工作方式。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R_1",
                "description": "应变片 1（梁上表面，受拉）",
                "unit": "Ω"
            },
            {
                "symbol": "R_2",
                "description": "应变片 2（梁下表面，受压）",
                "unit": "Ω"
            }
        ]
    }
},
    "exp49": {
    "_global": {
        "formulas": [
            {
                "title": "无级调压原理（RC 触发电路）",
                "steps": [
                    {
                        "note": "电容 C 经 R1、Rp 充电，充电时间常数：",
                        "formula": "\\tau = (R_1 + R_p) C"
                    },
                    {
                        "note": "电容电压升到晶闸管门极触发阈值（约 0.7 V）所需时间即断路时间 t1；Rp 增大 → 充电变慢 → t1 变长 → 导通时间变短 → 灯泡变暗：",
                        "formula": "t_1 \\approx \\tau \\ln\\frac{U_s}{U_s - 0.7}"
                    },
                    {
                        "note": "灯泡平均电流随导通时间占空比变化，从而实现无级调压。",
                        "formula": None
                    }
                ]
            },
            {
                "title": "测量相对误差",
                "steps": [
                    {
                        "note": "多次测量取平均：",
                        "formula": "\\bar{R} = \\frac{1}{n}\\sum_{i=1}^{n} R_i"
                    },
                    {
                        "note": "相对误差（与标称值比较）：",
                        "formula": "E = \\frac{|\\bar{R} - R_0|}{R_0} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R_p",
                "description": "<strong>电位器阻值</strong>，调节触发延时与灯泡亮度",
                "unit": "kΩ"
            },
            {
                "symbol": "\\tau",
                "description": "RC 充电时间常数，决定晶闸管触发时刻",
                "unit": "s"
            },
            {
                "symbol": "C",
                "description": "电解电容容量（本实验标称 6.3 μF）",
                "unit": "μF"
            },
            {
                "symbol": "t_1",
                "description": "<strong>断路时间</strong>（电容充电至门极触发阈值的时间）",
                "unit": "s"
            },
            {
                "symbol": "E",
                "description": "<strong>相对误差</strong>，测量值与标称值偏差的百分比",
                "unit": "%"
            }
        ]
    },
    "diode": {
        "formulas": [
            {
                "title": "二极管单向导电性",
                "steps": [
                    {
                        "note": "二极管核心是 PN 结，正向导通、反向截止；正向管压降与材料有关：",
                        "formula": None
                    },
                    {
                        "note": "硅二极管正向压降约 0.6~0.7 V；锗二极管约 0.2~0.3 V。",
                        "formula": None
                    },
                    {
                        "note": "本实验 1N4007 为硅整流二极管，万用表二极管档显示“626”即正向压降 626 mV。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U_F",
                "description": "正向导通压降（硅二极管约 0.6~0.7 V，用于判定材料与好坏）",
                "unit": "mV"
            }
        ]
    },
    "resistor": {
        "formulas": [
            {
                "title": "色环电阻读数与误差",
                "steps": [
                    {
                        "note": "四环电阻：前二环为有效数字，第三环为倍乘数，末环为误差（金 ±5%、银 ±10%、棕 ±1%）：",
                        "formula": "R_0 = (a \\times 10 + b) \\times 10^{m}"
                    },
                    {
                        "note": "三次测量取平均并与色环标称值比较：",
                        "formula": "\\bar{R} = \\frac{R_1 + R_2 + R_3}{3}, \\quad E = \\frac{|\\bar{R} - R_0|}{R_0} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R",
                "description": "电阻读数（R0 为色环标称值，R1~R3 为三次万用表测量值）",
                "unit": "Ω"
            }
        ]
    },
    "component": {
        "formulas": [
            {
                "title": "元件参数相对误差",
                "steps": [
                    {
                        "note": "实测值与标称值比较：",
                        "formula": "E = \\frac{|C_{测} - C_{标}|}{C_{标}} \\times 100\\%"
                    },
                    {
                        "note": "电解电容容量误差大（可达 ±20%），存放时间长易失效，测量前需短接放电。",
                        "formula": None
                    },
                    {
                        "note": "电位器旋转旋钮阻值连续变化，记录其最大阻值与标称值比较。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "C/R_p",
                "description": "元件标称值与实测值（电解电容 C 单位 μF，电位器 R_p 单位 kΩ）",
                "unit": ""
            }
        ]
    },
    "scr": {
        "formulas": [
            {
                "title": "单向晶闸管（SCR）工作原理",
                "steps": [
                    {
                        "note": "晶闸管为 P-N-P-N 四层三结结构，有阳极 A、阴极 K、控制极（门极）G 三个电极。",
                        "formula": None
                    },
                    {
                        "note": "导通条件：A-K 间加正向电压，同时 G-K 间加正向触发电压。",
                        "formula": None
                    },
                    {
                        "note": "一旦导通，门极失去控制作用（保持导通）。",
                        "formula": None
                    },
                    {
                        "note": "关断条件：阳极电流降到维持电流以下，或 A-K 电压反向。",
                        "formula": None
                    },
                    {
                        "note": "导通后 A-K 管压降约 1 V，几乎不耗电，调压效率高。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "正向导通电压（G-K 约 0.6~0.8 V，A-K 触发后约 1 V）",
                "unit": "V"
            }
        ]
    },
    "lamp": {
        "formulas": [
            {
                "title": "无级调压台灯电路分析",
                "steps": [
                    {
                        "note": "桥式整流将 24 V 交流电变为脉动直流；灯泡、整流桥与晶闸管（脉冲开关）串联。",
                        "formula": None
                    },
                    {
                        "note": "半周期内电容充电至门极阈值（约 0.7 V）触发导通，导通时间：",
                        "formula": "t_{通} = \\frac{T}{2} - t_1"
                    },
                    {
                        "note": "改变 Rp 即改变 t通/t断 比值，从而调节灯泡平均电流与亮度：",
                        "formula": "\\bar{I} \\propto \\frac{t_{通}}{T/2}"
                    },
                    {
                        "note": "断路期间电路几乎无电流（仅 ~0.1 mA 充电电流），导通期间晶闸管压降约 1 V，故调光效率高。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "R_p",
                "description": "电位器阻值（旋转位置对应的阻值，调节触发延时与灯泡亮度）",
                "unit": "kΩ"
            },
            {
                "symbol": "U",
                "description": "灯泡两端电压（不同触发状态下记录）",
                "unit": "V"
            }
        ]
    },
    "thyristor_test": {
        "formulas": [
            {
                "title": "晶闸管导通、保持与关断判据",
                "steps": [
                    {
                        "note": "闭合 s1、s2（门极正向触发）后主回路导通，灯泡发光。",
                        "formula": None
                    },
                    {
                        "note": "断开 s2（撤销门极电压）灯泡仍亮——触发导通后门极失去控制。",
                        "formula": None
                    },
                    {
                        "note": "断开主回路或 A-K 加反向电压，晶闸管关断，灯泡熄灭。",
                        "formula": None
                    },
                    {
                        "note": "交流主回路中每半周期末电压过零，晶闸管自然关断，下一半周期重新触发。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "U",
                "description": "灯泡两端电压（导通/保持/关断各状态下的记录）",
                "unit": "V"
            }
        ]
    }
},
    "exp50": {
    "_global": {
        "formulas": [
            {
                "title": "温度传感器特性",
                "steps": [
                    {
                        "note": "NTC 热敏电阻阻值随温度指数变化（恒压源电流法 R_t = R_1·U_Rt/U_R1）：",
                        "formula": "R_t = R_0 e^{B(1/T - 1/T_0)}, \\quad \\ln R_t = B(1/T - 1/T_0) + \\ln R_0"
                    },
                    {
                        "note": "PN 结正向电压与温度近似线性，温度系数约 -2.3 mV/°C：",
                        "formula": "U = BT + U_{go}"
                    },
                    {
                        "note": "LM35 输出电压与摄氏温度成正比：",
                        "formula": "U_0 = (10\\,\\mathrm{mV/°C})\\cdot t"
                    },
                    {
                        "note": "电压型传感器<strong>灵敏度</strong>与<strong>相关系数</strong>（最小二乘拟合）：",
                        "formula": "K = \\frac{\\Delta U}{\\Delta t}, \\quad r = \\frac{\\sum(t_i - \\bar{t})(U_i - \\bar{U})}{\\sqrt{\\sum(t_i - \\bar{t})^2\\sum(U_i - \\bar{U})^2}}"
                    }
                ]
            },
            {
                "title": "线性度",
                "steps": [
                    {
                        "note": "<strong>线性度</strong>（非线性误差）：最大偏差与满量程输出之比：",
                        "formula": "\\delta = \\frac{\\Delta Y_{max}}{Y} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "<strong>摄氏温度</strong>，由控温仪设定并稳定",
                "unit": "°C"
            },
            {
                "symbol": "T",
                "description": "<strong>热力学温度</strong>，T = t + 273.15",
                "unit": "K"
            },
            {
                "symbol": "R_t",
                "description": "<strong>热敏电阻阻值</strong>，恒压源电流法由分压换算",
                "unit": "kΩ"
            },
            {
                "symbol": "B",
                "description": "<strong>热敏电阻材料常数</strong>，典型值 2000~6000 K",
                "unit": "K"
            },
            {
                "symbol": "K",
                "description": "<strong>传感器灵敏度</strong>，ΔU/Δt",
                "unit": "mV/°C"
            },
            {
                "symbol": "\\delta",
                "description": "<strong>线性度</strong>，最大偏差与满量程之比",
                "unit": "%"
            }
        ]
    },
    "sensor": {
        "formulas": [
            {
                "title": "恒压源电流法测 NTC 阻值",
                "steps": [
                    {
                        "note": "NTC 与固定电阻 R1 串联接恒压源，两电阻电流相等：",
                        "formula": "R_t = R_1\\frac{U_{Rt}}{U_{R1}}"
                    },
                    {
                        "note": "取对数后 ln R_t 与 1/T 成线性，斜率即材料常数 B：",
                        "formula": "\\ln R_t = B\\cdot\\frac{1}{T} + \\left(\\ln R_0 - \\frac{B}{T_0}\\right)"
                    },
                    {
                        "note": "电阻温度系数（%/K）：",
                        "formula": "\\alpha = -\\frac{B}{T_0^2} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "控温仪设定并稳定的摄氏温度",
                "unit": "°C"
            },
            {
                "symbol": "U",
                "description": "传感器输出电压（NTC 为热敏电阻电压 U_Rt，PN 结为 U_be，LM35 为 U0）",
                "unit": "mV"
            },
            {
                "symbol": "U_R",
                "description": "固定电阻 R1 两端参考电压（恒压源电流法换算 NTC 阻值用）",
                "unit": "mV"
            }
        ]
    },
    "calib": {
        "formulas": [
            {
                "title": "温度表定标与线性度",
                "steps": [
                    {
                        "note": "组装表与标准表的<strong>示值差</strong>：",
                        "formula": "\\Delta t = t_{组装} - t_{标准}"
                    },
                    {
                        "note": "<strong>线性度</strong>（最大差值对测量范围 Y）：",
                        "formula": "\\delta = \\frac{|\\Delta t|_{max}}{Y} \\times 100\\%"
                    },
                    {
                        "note": "组装表对标准表拟合应接近恒等：",
                        "formula": "t_{组装} = k\\,t_{标准} + b, \\quad k \\approx 1, \\; b \\approx 0"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "温度示数（t_设定 为设定温度，t_标准 为标准表读数，t_组装 为组装表读数）",
                "unit": "°C"
            }
        ]
    },
    "body_temp": {
        "formulas": [
            {
                "title": "人体各部位温度分布",
                "steps": [
                    {
                        "note": "每部位多次测量的平均值与样本标准差：",
                        "formula": "\\bar{t} = \\frac{1}{n}\\sum_{i=1}^{n}t_i, \\quad \\sigma = \\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}(t_i - \\bar{t})^2}"
                    },
                    {
                        "note": "部位间温差反映血液循环与散热：",
                        "formula": "\\Delta t = \\bar{t}_{max} - \\bar{t}_{min}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "人体该部位实测温度（每部位测 2~3 次）",
                "unit": "°C"
            }
        ]
    },
    "pressure": {
        "formulas": [
            {
                "title": "MPS3100 压力传感器特性",
                "steps": [
                    {
                        "note": "输出电压与压强近似线性，最小二乘拟合求灵敏度：",
                        "formula": "U = K P + U_0, \\quad K = \\frac{\\Delta U}{\\Delta P}"
                    },
                    {
                        "note": "<strong>非线性度</strong>（最大偏差对满量程输出）：",
                        "formula": "\\delta = \\frac{|\\Delta U|_{max}}{U_{max} - U_{min}} \\times 100\\%"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "P",
                "description": "<strong>气体压强</strong>，指针式压力表读取（可靠量程 4~32 kPa）",
                "unit": "kPa"
            },
            {
                "symbol": "U",
                "description": "<strong>传感器输出电压</strong>",
                "unit": "mV"
            },
            {
                "symbol": "K",
                "description": "<strong>压力灵敏度</strong>，ΔU/ΔP",
                "unit": "mV/kPa"
            }
        ]
    },
    "blood": {
        "formulas": [
            {
                "title": "柯氏音法测血压",
                "steps": [
                    {
                        "note": "袖套放气过程中<strong>第一声</strong>柯氏音对应<strong>收缩压</strong>，<strong>最后一声</strong>对应<strong>舒张压</strong>：",
                        "formula": "\\text{血压} = \\text{收缩压}/\\text{舒张压}"
                    },
                    {
                        "note": "脉压差：",
                        "formula": "\\Delta P = P_{收缩} - P_{舒张}"
                    },
                    {
                        "note": "单位换算（毫米汞柱 ↔ 千帕）：",
                        "formula": "1\\,\\mathrm{mmHg} \\approx 0.1333\\,\\mathrm{kPa}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "P_s",
                "description": "收缩压（袖带缓慢放气中听到的第一声柯氏音对应的压力）",
                "unit": "kPa"
            },
            {
                "symbol": "P_d",
                "description": "舒张压（柯氏音消失时的压力）",
                "unit": "kPa"
            },
            {
                "symbol": "n",
                "description": "心率（每分钟心跳次数，由脉搏计数器测得）",
                "unit": "次/分"
            }
        ]
    },
    "boyle": {
        "formulas": [
            {
                "title": "波意耳定律",
                "steps": [
                    {
                        "note": "一定质量气体在<strong>等温过程</strong>中压强与体积成反比：",
                        "formula": "P V = \\text{常数}"
                    },
                    {
                        "note": "P 与 1/V 应成过原点直线：",
                        "formula": "P = C\\cdot\\frac{1}{V}, \\quad C = PV"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "P",
                "description": "<strong>气体压强</strong>",
                "unit": "kPa"
            },
            {
                "symbol": "V",
                "description": "<strong>气体体积</strong>，由注射器刻度读取",
                "unit": "ml"
            },
            {
                "symbol": "C",
                "description": "<strong>PV 常数</strong>，等温条件下不变",
                "unit": "kPa·ml"
            }
        ]
    },
    "hearing": {
        "formulas": [
            {
                "title": "听阈测量与零位修正",
                "steps": [
                    {
                        "note": "<strong>渐增法</strong>与<strong>渐减法</strong>的平均值作为该频率听阈：",
                        "formula": "L = \\frac{L_1 + L_2}{2}"
                    },
                    {
                        "note": "<strong>零位修正</strong>：以 1000 Hz 的听阈为基准（L0），求相对声强级：",
                        "formula": "L_{测} = L - L_0"
                    },
                    {
                        "note": "作听阈曲线用<strong>半对数坐标</strong>（横轴 lg f），正常听阈在 2~4 kHz 最低。",
                        "formula": None
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "L",
                "description": "听阈声强级（L1 为渐增法、L2 为渐减法测得）",
                "unit": "dB"
            },
            {
                "symbol": "f",
                "description": "测试信号频率（不同频率下的听阈测量）",
                "unit": "Hz"
            }
        ]
    },
    "reaction": {
        "formulas": [
            {
                "title": "人体反应时间统计",
                "steps": [
                    {
                        "note": "各测试项目 6 次测量的平均值与标准差：",
                        "formula": "\\bar{t} = \\frac{1}{n}\\sum_{i=1}^{n}t_i, \\quad \\sigma = \\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}(t_i - \\bar{t})^2}"
                    },
                    {
                        "note": "比较不同刺激通路的反应时间：",
                        "formula": "\\Delta \\bar{t} = \\bar{t}_{视觉} - \\bar{t}_{听觉}"
                    }
                ]
            }
        ],
        "variables": [
            {
                "symbol": "t",
                "description": "<strong>反应时间</strong>，刺激出现到做出反应的时间",
                "unit": "ms"
            },
            {
                "symbol": "\\bar{t}",
                "description": "某项目 6 次测量的<strong>平均反应时间</strong>",
                "unit": "ms"
            }
        ]
    }
},

}


def get_table_formulas(exp_id: str, table_id: str) -> list:
    """获取指定实验指定表格的公式列表。"""
    exp_data = TABLE_THEORY.get(exp_id, {})
    table_data = exp_data.get(table_id, exp_data.get("_global", {}))
    return table_data.get("formulas", [])


def get_table_variables(exp_id: str, table_id: str) -> list:
    """获取指定实验指定表格的物理量列表。"""
    exp_data = TABLE_THEORY.get(exp_id, {})
    table_data = exp_data.get(table_id, exp_data.get("_global", {}))
    return table_data.get("variables", [])


def get_table_theory(exp_id: str) -> dict:
    """获取指定实验的全部 per-table 理论数据。

    返回格式: {table_id: {"formulas": [...], "variables": [...]}, "_global": {...}}
    前端可用 _global 作为没有单独配置的表格的回退数据。
    """
    exp_data = TABLE_THEORY.get(exp_id, {})
    result = {}
    for table_id, data in exp_data.items():
        if table_id == "_global":
            result["_global"] = {
                "formulas": data.get("formulas", []),
                "variables": data.get("variables", []),
            }
        else:
            result[table_id] = {
                "formulas": data.get("formulas", []),
                "variables": data.get("variables", []),
            }
    return result


# 向后兼容：旧的全局函数
def get_formulas(exp_id: str) -> list:
    """获取指定实验的全局公式列表（向后兼容）。"""
    exp_data = TABLE_THEORY.get(exp_id, {})
    return exp_data.get("_global", {}).get("formulas", [])


def get_variables(exp_id: str) -> list:
    """获取指定实验的全局物理量列表（向后兼容）。"""
    exp_data = TABLE_THEORY.get(exp_id, {})
    return exp_data.get("_global", {}).get("variables", [])
