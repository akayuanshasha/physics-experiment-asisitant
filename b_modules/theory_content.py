"""生成 per-table 结构的 theory_content.py"""

# 每个实验的每个表格对应的公式和物理量说明
# 结构: {exp_id: {table_id: {"formulas": [...], "variables": [...]}}}
TABLE_THEORY = {
    # ── exp0: 基础工具（不确定度计算） ──
    # exp0 没有表格，使用全局公式
    "exp0": {
        "_global": {
            "formulas": [
                {"title": "算术平均值与不确定度", "steps": [
                    {"note": "对 n 次等精度测量取平均：", "formula": r"\bar{x} = \frac{1}{n}\sum_{i=1}^{n}x_i"},
                    {"note": "样本标准差（贝塞尔公式）：", "formula": r"s = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2}"},
                    {"note": "<strong>A 类不确定度</strong>：", "formula": r"u_A = \frac{s}{\sqrt{n}}"},
                    {"note": "<strong>合成不确定度</strong>（含 B 类仪器误差 Δ<sub>inst</sub>）：", "formula": r"u = \sqrt{u_A^2 + u_B^2}, \quad u_B = \frac{\Delta_{\text{inst}}}{\sqrt{3}}"},
                ]},
                {"title": "最小二乘法线性拟合", "steps": [
                    {"note": "对 y = a + bx 做最小二乘拟合：", "formula": r"b = \frac{n\sum x_i y_i - \sum x_i \sum y_i}{n\sum x_i^2 - (\sum x_i)^2}"},
                    {"note": "相关系数（衡量线性度）：", "formula": r"r = \frac{n\sum x_i y_i - \sum x_i \sum y_i}{\sqrt{[n\sum x_i^2-(\sum x_i)^2][n\sum y_i^2-(\sum y_i)^2]}"},
                ]},
            ],
            "variables": [
                {"symbol": r"\bar{x}", "description": "<strong>算术平均值</strong>，n 次测量的最佳估计值", "unit": "与测量值相同"},
                {"symbol": "s", "description": "<strong>样本标准差</strong>，由贝塞尔公式计算", "unit": "与测量值相同"},
                {"symbol": r"u_A", "description": "<strong>A 类不确定度</strong>，由统计方法评定", "unit": "与测量值相同"},
                {"symbol": r"u_B", "description": "<strong>B 类不确定度</strong>，由仪器误差评定", "unit": "与测量值相同"},
                {"symbol": "r", "description": "<strong>相关系数</strong>，|r| 越接近 1 线性越好", "unit": "无单位"},
            ],
        }
    },

    # ── exp1: 单摆法测重力加速度 ──
    "exp1": {
        "table1": {
            "formulas": [
                {"title": "单摆周期公式", "steps": [
                    {"note": "单摆在小角度（θ < 5°）下的周期公式：", "formula": r"T = 2\pi\sqrt{\frac{L}{g}}"},
                    {"note": "由此解出<strong>待求量 g</strong>：", "formula": r"g = \frac{4\pi^2 L}{T^2}"},
                ]},
            ],
            "variables": [
                {"symbol": "L", "description": "<strong>摆长</strong>，悬点到球心的距离，L = l + d/2", "unit": "cm"},
                {"symbol": "T", "description": "<strong>单摆周期</strong>，由累积时间 t 除以摆动次数 n 得到", "unit": "s"},
                {"symbol": "l", "description": "摆线长度，由钢卷尺测量", "unit": "cm"},
                {"symbol": "d", "description": "摆球直径，由游标卡尺测量", "unit": "mm"},
                {"symbol": "g", "description": "<strong>重力加速度</strong>（待求量），由 g = 4π²L/T² 计算", "unit": "m/s²"},
            ],
        },
        "table2": {
            "formulas": [
                {"title": "多摆长拟合求 g", "steps": [
                    {"note": "由 T = 2π√(L/g) 两边平方得：", "formula": r"T^2 = \frac{4\pi^2}{g} L"},
                    {"note": "作 L-T² 图，斜率 k = 4π²/g，故：", "formula": r"g = \frac{4\pi^2}{k}"},
                ]},
            ],
            "variables": [
                {"symbol": "L", "description": "<strong>摆长</strong>，不同摆长条件下的值", "unit": "cm"},
                {"symbol": "T", "description": "<strong>单摆周期</strong>，由累积时间除以摆动次数得到", "unit": "s"},
                {"symbol": r"T^2", "description": "<strong>周期平方</strong>，由 T² 计算（中间量）", "unit": "s²"},
                {"symbol": "k", "description": "L-T² 图<strong>拟合斜率</strong>，k = ΔL/ΔT²", "unit": "cm/s²"},
            ],
        },
    },

    # ── exp2: 表面张力 ──
    "exp2": {
        "table1": {
            "formulas": [
                {"title": "拉脱法测表面张力系数", "steps": [
                    {"note": "金属环被拉脱液面时，表面张力：", "formula": r"F = \alpha \cdot \pi(D_1 + D_2)"},
                    {"note": "<strong>表面张力系数</strong>：", "formula": r"\alpha = \frac{mg}{\pi(D_1 + D_2)}"},
                ]},
            ],
            "variables": [
                {"symbol": r"\alpha", "description": "<strong>表面张力系数</strong>（待求量）", "unit": "N/m"},
                {"symbol": "m", "description": "拉脱前后质量差，由天平测量", "unit": "kg"},
                {"symbol": r"D_1, D_2", "description": "金属环的内外直径，由游标卡尺测量", "unit": "m"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": "k", "description": "弹簧劲度系数，由胡克定律 F = kΔx 拟合求出", "unit": "N/m"},
                {"symbol": "F", "description": "施加的力，由砝码质量乘以 g 得到", "unit": "N"},
                {"symbol": r"\Delta x", "description": "弹簧伸长量", "unit": "m"},
            ],
        },
        "table3": {
            "formulas": [],
            "variables": [
                {"symbol": r"\alpha", "description": "<strong>表面张力系数</strong>（待求量）", "unit": "N/m"},
                {"symbol": "m", "description": "拉脱质量", "unit": "kg"},
            ],
        },
    },

    # ── exp3: 粘滞系数 ──
    "exp3": {
        "_global": {
            "formulas": [
                {"title": "落球法测粘滞系数", "steps": [
                    {"note": "小球在粘滞液体中匀速下落时，由<strong>斯托克斯公式</strong>：", "formula": r"\eta = \frac{2r^2(\rho - \rho_0)g}{9v}"},
                ]},
            ],
            "variables": [
                {"symbol": r"\eta", "description": "<strong>粘滞系数</strong>（待求量）", "unit": "Pa·s"},
                {"symbol": "r", "description": "小球半径，由螺旋测微器测量", "unit": "m"},
                {"symbol": "v", "description": "小球匀速下落速度，由距离/时间计算", "unit": "m/s"},
                {"symbol": r"\rho", "description": "小球密度", "unit": "kg/m³"},
                {"symbol": r"\rho_0", "description": "液体密度", "unit": "kg/m³"},
            ],
        }
    },

    # ── exp4: 密度测量 ──
    "exp4": {
        "table1": {
            "formulas": [
                {"title": "流体静力称衡法测密度", "steps": [
                    {"note": "固体密度：", "formula": r"\rho = \frac{m}{m - m'}\rho_0"},
                ]},
            ],
            "variables": [
                {"symbol": r"\rho", "description": "<strong>固体密度</strong>（待求量）", "unit": "kg/m³"},
                {"symbol": "m", "description": "物体在空气中的质量", "unit": "kg"},
                {"symbol": "m'", "description": "物体在液体中的视质量", "unit": "kg"},
                {"symbol": r"\rho_0", "description": "液体（水）的密度（常数）", "unit": "kg/m³"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": r"\rho", "description": "<strong>固体密度</strong>（待求量）", "unit": "kg/m³"},
            ],
        },
        "table3": {
            "formulas": [],
            "variables": [
                {"symbol": r"\rho", "description": "<strong>液体密度</strong>（待求量）", "unit": "kg/m³"},
            ],
        },
        "table4": {
            "formulas": [
                {"title": "转动定律测质量", "steps": [
                    {"note": "由转动定律 Iβ = M，通过测量转动惯量和角加速度求质量。", "formula": None},
                ]},
            ],
            "variables": [
                {"symbol": "m", "description": "物体质量（待求量）", "unit": "kg"},
            ],
        },
    },

    # ── exp5: 杨氏模量 ──
    "exp5": {
        "table1": {
            "formulas": [
                {"title": "拉伸法测杨氏模量", "steps": [
                    {"note": "<strong>杨氏模量</strong>定义（应力/应变）：", "formula": r"E = \frac{F/A}{\Delta L / L} = \frac{FL}{A\,\Delta L}"},
                    {"note": "用光杠杆放大微小伸长量：", "formula": r"\Delta L = \frac{b\,\Delta n}{2D}"},
                    {"note": "代入得最终公式：", "formula": r"E = \frac{8FLD}{\pi d^2 b\,\Delta n}"},
                ]},
            ],
            "variables": [
                {"symbol": "E", "description": "<strong>杨氏模量</strong>（待求量）", "unit": "Pa"},
                {"symbol": "F", "description": "施加的拉力，由砝码质量乘以 g 得到", "unit": "N"},
                {"symbol": "L", "description": "钢丝原长，由米尺测量", "unit": "m"},
                {"symbol": "d", "description": "钢丝直径，由螺旋测微器测量", "unit": "m"},
                {"symbol": "b", "description": "光杠杆前后足间距", "unit": "m"},
                {"symbol": "D", "description": "光杠杆镜面到标尺的距离", "unit": "m"},
                {"symbol": r"\Delta n", "description": "光杠杆标尺读数变化量（中间量）", "unit": "mm"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": r"\Delta n", "description": "光杠杆标尺读数变化量", "unit": "mm"},
                {"symbol": "F", "description": "施加的拉力", "unit": "N"},
            ],
        },
    },

    # ── exp6: 切变模量 ──
    "exp6": {
        "_global": {
            "formulas": [
                {"title": "扭转法测切变模量", "steps": [
                    {"note": "圆棒受扭时，<strong>切变模量</strong>：", "formula": r"G = \frac{32FLR}{\pi d^4 \theta}"},
                ]},
            ],
            "variables": [
                {"symbol": "G", "description": "<strong>切变模量</strong>（待求量）", "unit": "Pa"},
                {"symbol": "F", "description": "施加的外力", "unit": "N"},
                {"symbol": "L", "description": "圆棒长度", "unit": "m"},
                {"symbol": "R", "description": "力臂长度", "unit": "m"},
                {"symbol": "d", "description": "圆棒直径", "unit": "m"},
                {"symbol": r"\theta", "description": "扭转角", "unit": "rad"},
            ],
        }
    },

    # ── exp7: 固体比热 ──
    "exp7": {
        "_global": {
            "formulas": [
                {"title": "混合法测固体比热容", "steps": [
                    {"note": "热平衡方程：", "formula": r"c_x = \frac{(m_w c_w + C)(T_f - T_0)}{m_x(T_x - T_f)}"},
                ]},
            ],
            "variables": [
                {"symbol": "c_x", "description": "<strong>固体比热容</strong>（待求量）", "unit": "J/(kg·°C)"},
                {"symbol": "m_w", "description": "水的质量", "unit": "kg"},
                {"symbol": "c_w", "description": "水的比热容（常数）", "unit": "J/(kg·°C)"},
                {"symbol": "C", "description": "量热器水当量", "unit": "J/°C"},
                {"symbol": "T_f", "description": "热平衡后的末温", "unit": "°C"},
                {"symbol": "T_0", "description": "水的初温", "unit": "°C"},
                {"symbol": "T_x", "description": "待测固体的初温", "unit": "°C"},
                {"symbol": "m_x", "description": "待测固体质量", "unit": "kg"},
            ],
        }
    },

    # ── exp8: 匀加速运动 ──
    "exp8": {
        "table1": {
            "formulas": [
                {"title": "光电门测瞬时速度", "steps": [
                    {"note": "挡光宽度 Δs 很小，瞬时速度：", "formula": r"v = \frac{\Delta s}{\Delta t}"},
                ]},
            ],
            "variables": [
                {"symbol": "v", "description": "<strong>瞬时速度</strong>（中间量）", "unit": "m/s"},
                {"symbol": r"\Delta s", "description": "挡光片宽度（参数）", "unit": "m"},
                {"symbol": r"\Delta t", "description": "挡光时间，由光电门测量", "unit": "s"},
            ],
        },
        "table2": {
            "formulas": [
                {"title": "匀加速运动中速度与位移的关系", "steps": [
                    {"note": "速度平方与位移的关系：", "formula": r"v^2 = 2as"},
                    {"note": "作 v²-2s 图，斜率即为加速度 a。", "formula": r"g = \frac{aL}{h}"},
                ]},
            ],
            "variables": [
                {"symbol": "v", "description": "<strong>瞬时速度</strong>（中间量）", "unit": "m/s"},
                {"symbol": "a", "description": "<strong>加速度</strong>，由 v²-2s 图斜率求出（待求量）", "unit": "m/s²"},
                {"symbol": "s", "description": "滑块位移", "unit": "m"},
            ],
        },
        "table3": {
            "formulas": [
                {"title": "验证牛顿第二定律", "steps": [
                    {"note": "系统总质量 M 不变，改变悬挂质量 m：", "formula": r"a = \frac{m_{\text{hang}}}{M}g"},
                ]},
                {"title": "碰撞中的动量守恒", "steps": [
                    {"note": "两物体碰撞前后动量守恒：", "formula": r"m_1 v_1 = m_1 v_1' + m_2 v_2'"},
                ]},
            ],
            "variables": [
                {"symbol": "a", "description": "<strong>加速度</strong>（待求量）", "unit": "m/s²"},
                {"symbol": "m_{\text{hang}}", "description": "悬挂质量", "unit": "kg"},
                {"symbol": "M", "description": "系统总质量", "unit": "kg"},
            ],
        },
    },

    # ── exp9: 声速测量 ──
    "exp9": {
        "_global": {
            "formulas": [
                {"title": "驻波法测声速", "steps": [
                    {"note": "声速与频率、波长的关系：", "formula": r"v = f\lambda"},
                    {"note": "相邻共振间距 Δx = λ/2，故：", "formula": r"v = 2f\,\Delta x"},
                ]},
            ],
            "variables": [
                {"symbol": "v", "description": "<strong>声速</strong>（待求量）", "unit": "m/s"},
                {"symbol": "f", "description": "信号源频率", "unit": "Hz"},
                {"symbol": r"\Delta x", "description": "相邻共振位置间距，等于 λ/2（中间量）", "unit": "m"},
            ],
        }
    },

    # ── exp10: 磁力摆 ──
    "exp10": {
        "table1": {
            "formulas": [
                {"title": "亥姆霍兹线圈磁场", "steps": [
                    {"note": "亥姆霍兹线圈轴线中心处的磁场：", "formula": r"B_1 = kI"},
                    {"note": "磁针在合磁场中的振荡周期：", "formula": r"T = 2\pi\sqrt{\frac{J}{mB}}"},
                ]},
            ],
            "variables": [
                {"symbol": "I", "description": "励磁电流", "unit": "A"},
                {"symbol": "T", "description": "磁针振荡周期", "unit": "s"},
                {"symbol": "B_1", "description": "线圈产生的磁场（中间量）", "unit": "T"},
                {"symbol": "k", "description": "线圈常数（参数）", "unit": "T/A"},
            ],
        },
        "table2": {
            "formulas": [
                {"title": "线性化求地磁场", "steps": [
                    {"note": "1/T² 与 B<sub>total</sub> 成线性关系：", "formula": r"\frac{1}{T^2} = \frac{mB}{4\pi^2 J}"},
                    {"note": "由截距/斜率 = -B₀ 求得地磁场水平分量。", "formula": None},
                ]},
            ],
            "variables": [
                {"symbol": "B_0", "description": "<strong>地磁场水平分量</strong>（待求量）", "unit": "T"},
                {"symbol": r"1/T^2", "description": "周期平方的倒数（中间量）", "unit": "1/s²"},
            ],
        },
    },

    # ── exp11-exp25: 无表格实验，使用全局 ──
    "exp11": {"_global": {"formulas": [{"title": "半导体温度计原理", "steps": [{"note": "热敏电阻温度-电阻关系：", "formula": r"R_T = R_0 \exp\left[B\left(\frac{1}{T} - \frac{1}{T_0}\right)\right]"}]}], "variables": [{"symbol": "R_T", "description": "温度 T 时的阻值", "unit": "Ω"}, {"symbol": "B", "description": "<strong>材料常数</strong>（待求量）", "unit": "K"}]}},
    "exp12": {"_global": {"formulas": [{"title": "示波器使用", "steps": [{"note": "李萨如图形频率比：", "formula": r"\frac{f_y}{f_x} = \frac{n_x}{n_y}"}]}], "variables": [{"symbol": "f_x", "description": "x 方向信号频率", "unit": "Hz"}, {"symbol": "f_y", "description": "<strong>y 方向信号频率</strong>（待求量）", "unit": "Hz"}]}},
    "exp13": {"_global": {"formulas": [{"title": "整流滤波", "steps": [{"note": "全波整流输出：", "formula": r"V_{dc} = \frac{2V_m}{\pi}"}, {"note": "纹波电压：", "formula": r"V_{ripple} \approx \frac{I}{fC}"}]}], "variables": [{"symbol": "V_{dc}", "description": "整流输出平均值", "unit": "V"}, {"symbol": "V_m", "description": "输入交流峰值", "unit": "V"}]}},
    "exp14": {"_global": {"formulas": [{"title": "直流电源特性", "steps": [{"note": "端电压与电流关系：", "formula": r"V = \varepsilon - Ir"}]}], "variables": [{"symbol": r"\varepsilon", "description": "<strong>电动势</strong>（待求量）", "unit": "V"}, {"symbol": "r", "description": "<strong>内阻</strong>（待求量）", "unit": "Ω"}]}},
    "exp15": {"_global": {"formulas": [{"title": "硅光电池特性", "steps": [{"note": "伏安特性：", "formula": r"I = I_L - I_0\left(e^{\frac{qV}{nkT}} - 1\right)"}]}], "variables": [{"symbol": "I", "description": "输出电流", "unit": "A"}, {"symbol": "V", "description": "端电压", "unit": "V"}]}},
    "exp16": {"_global": {"formulas": [{"title": "配色实验", "steps": [{"note": "颜色混合的格拉斯曼定律（三原色原理）。", "formula": None}]}], "variables": [{"symbol": "—", "description": "配色实验基于三原色原理，无特定计算公式", "unit": "—"}]}},
    "exp17": {"_global": {"formulas": [{"title": "数字体温计", "steps": [{"note": "PN 结正向压降与温度：", "formula": r"V_F(T) = V_{F0} - kT"}]}], "variables": [{"symbol": "V_F", "description": "PN 结正向压降", "unit": "V"}, {"symbol": "k", "description": "<strong>温度灵敏度</strong>（待求量）", "unit": "V/°C"}]}},
    "exp18_a": {"_global": {"formulas": [{"title": "分光计的调节与使用", "steps": [{"note": "最小偏向角法测折射率：", "formula": r"n = \frac{\sin\frac{A + \delta_{\min}}{2}}{\sin\frac{A}{2}}"}]}], "variables": [{"symbol": "n", "description": "<strong>折射率</strong>（待求量）", "unit": "无单位"}, {"symbol": "A", "description": "三棱镜顶角", "unit": "°"}, {"symbol": r"\delta_{\min}", "description": "<strong>最小偏向角</strong>", "unit": "°"}]}},
    "exp18_b": {"_global": {"formulas": [{"title": "用分光计测三棱镜折射率", "steps": [{"note": "最小偏向角法：", "formula": r"n = \frac{\sin\frac{A + \delta_{\min}}{2}}{\sin\frac{A}{2}}"}]}], "variables": [{"symbol": "n", "description": "<strong>折射率</strong>（待求量）", "unit": "无单位"}, {"symbol": "A", "description": "三棱镜顶角", "unit": "°"}, {"symbol": r"\delta_{\min}", "description": "<strong>最小偏向角</strong>", "unit": "°"}]}},
    "exp19": {"_global": {"formulas": [{"title": "干涉法测微小量", "steps": [{"note": "劈尖干涉：", "formula": r"d = \frac{\lambda}{2\theta} \approx \frac{\lambda L}{2D}"}]}], "variables": [{"symbol": "d", "description": "<strong>待测微小量</strong>（待求量）", "unit": "m"}, {"symbol": r"\lambda", "description": "光波长", "unit": "m"}]}},
    "exp20": {"_global": {"formulas": [{"title": "透镜参数测量", "steps": [{"note": "薄透镜成像公式：", "formula": r"\frac{1}{u} + \frac{1}{v} = \frac{1}{f}"}]}], "variables": [{"symbol": "u", "description": "物距", "unit": "m"}, {"symbol": "v", "description": "像距", "unit": "m"}, {"symbol": "f", "description": "<strong>焦距</strong>（待求量）", "unit": "m"}]}},
    "exp21": {"_global": {"formulas": [{"title": "显微镜原理", "steps": [{"note": "总放大倍率：", "formula": r"M = \frac{\Delta}{f_o} \times \frac{250}{f_e}"}]}], "variables": [{"symbol": "M", "description": "<strong>总放大倍率</strong>（待求量）", "unit": "无单位"}, {"symbol": r"\Delta", "description": "光学筒长", "unit": "mm"}]}},
    "exp22": {"_global": {"formulas": [{"title": "衍射实验", "steps": [{"note": "单缝衍射暗纹条件：", "formula": r"a\sin\theta = k\lambda"}, {"note": "小角度近似条纹间距：", "formula": r"\Delta x = \frac{f\lambda}{a}"}]}], "variables": [{"symbol": "a", "description": "单缝宽度", "unit": "m"}, {"symbol": r"\lambda", "description": "光波长", "unit": "m"}]}},
    "exp23": {"_global": {"formulas": [{"title": "光电效应", "steps": [{"note": "<strong>爱因斯坦光电方程</strong>：", "formula": r"h\nu = \frac{1}{2}mv_{\max}^2 + W"}, {"note": "截止电压与频率：", "formula": r"U_s = \frac{h}{e}\nu - \frac{W}{e}"}]}], "variables": [{"symbol": "h", "description": "<strong>普朗克常量</strong>（待求量）", "unit": "J·s"}, {"symbol": r"\nu", "description": "入射光频率", "unit": "Hz"}, {"symbol": "U_s", "description": "截止电压", "unit": "V"}]}},
    "exp24": {"_global": {"formulas": [{"title": "密立根油滴", "steps": [{"note": "油滴电荷量（平衡法）：", "formula": r"q = \frac{mgd}{V}\left(1 + \frac{b}{pa}\right)^{3/2}"}, {"note": "验证电荷量子化：q = ne", "formula": None}]}], "variables": [{"symbol": "q", "description": "<strong>油滴电荷量</strong>（待求量）", "unit": "C"}, {"symbol": "V", "description": "极板电压", "unit": "V"}, {"symbol": "d", "description": "极板间距", "unit": "m"}]}},
    "exp25": {"_global": {"formulas": [{"title": "生活中的物理", "steps": [{"note": "本实验涵盖多个生活场景中的物理原理。", "formula": None}]}], "variables": [{"symbol": "—", "description": "具体物理量视实验项目而定", "unit": "—"}]}},

    # ── exp26-exp50: 二级实验，有表格 ──
    "exp26": {
        "table1": {
            "formulas": [{"title": "磁阻效应", "steps": [{"note": "磁阻相对变化率：", "formula": r"\frac{\Delta R}{R_0} = \frac{R(B) - R(0)}{R(0)}"}]}],
            "variables": [
                {"symbol": "R(B)", "description": "磁场 B 下的电阻值", "unit": "Ω"},
                {"symbol": "R(0)", "description": "零磁场下的电阻值", "unit": "Ω"},
                {"symbol": r"\Delta R/R_0", "description": "<strong>磁阻相对变化</strong>（待求量）", "unit": "无单位"},
                {"symbol": "B", "description": "磁感应强度", "unit": "T"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": "R", "description": "电阻值", "unit": "Ω"},
                {"symbol": "B", "description": "磁感应强度", "unit": "T"},
            ],
        },
    },
    "exp27": {
        "table1": {
            "formulas": [{"title": "非平衡电桥", "steps": [{"note": "电桥输出电压：", "formula": r"U_{out} = V_s \left(\frac{R_2}{R_1+R_2} - \frac{R_4}{R_3+R_4}\right)"}]}],
            "variables": [
                {"symbol": "U_{out}", "description": "<strong>电桥输出电压</strong>", "unit": "V"},
                {"symbol": "V_s", "description": "电源电压", "unit": "V"},
                {"symbol": "R_1 \\ldots R_4", "description": "电桥四个臂的电阻", "unit": "Ω"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": "U_{out}", "description": "输出电压", "unit": "V"},
                {"symbol": "T", "description": "温度", "unit": "°C"},
            ],
        },
    },
    "exp28": {
        "table1": {
            "formulas": [{"title": "霍尔电压测量", "steps": [{"note": "<strong>霍尔电压</strong>：", "formula": r"V_H = K_H I_H B"}]}],
            "variables": [
                {"symbol": "V_H", "description": "<strong>霍尔电压</strong>，由数字电压表测量", "unit": "V"},
                {"symbol": "I_H", "description": "霍尔元件工作电流", "unit": "A"},
                {"symbol": "B", "description": "外加磁场", "unit": "T"},
            ],
        },
        "table2": {
            "formulas": [{"title": "霍尔灵敏度测定", "steps": [{"note": "由 V<sub>H</sub>-I<sub>H</sub> 图斜率求 K<sub>H</sub>：", "formula": r"K_H = \frac{\Delta V_H}{\Delta I_H \cdot B}"}]}],
            "variables": [
                {"symbol": "K_H", "description": "<strong>霍尔灵敏度</strong>（待求量）", "unit": "V/(A·T)"},
                {"symbol": "V_H", "description": "霍尔电压", "unit": "V"},
                {"symbol": "I_H", "description": "工作电流", "unit": "A"},
            ],
        },
        "table3": {
            "formulas": [{"title": "电导率测量", "steps": [{"note": "电导率与载流子浓度、迁移率的关系：", "formula": r"\sigma = ne\mu"}]}],
            "variables": [
                {"symbol": r"\sigma", "description": "<strong>电导率</strong>（待求量）", "unit": "S/m"},
                {"symbol": "n", "description": "载流子浓度", "unit": "1/m³"},
                {"symbol": r"\mu", "description": "载流子迁移率", "unit": "m²/(V·s)"},
            ],
        },
    },
    "exp29": {
        "table1": {
            "formulas": [{"title": "RLC 串联谐振", "steps": [{"note": "谐振条件：", "formula": r"f_0 = \frac{1}{2\pi\sqrt{LC}}"}, {"note": "品质因数：", "formula": r"Q = \frac{1}{R}\sqrt{\frac{L}{C}}"}]}],
            "variables": [
                {"symbol": "f_0", "description": "<strong>谐振频率</strong>（待求量）", "unit": "Hz"},
                {"symbol": "L", "description": "电感", "unit": "H"},
                {"symbol": "C", "description": "电容", "unit": "F"},
                {"symbol": "R", "description": "电阻", "unit": "Ω"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": "f", "description": "信号频率", "unit": "Hz"},
                {"symbol": "V_R", "description": "电阻两端电压", "unit": "V"},
            ],
        },
        "table3": {
            "formulas": [],
            "variables": [
                {"symbol": "Q", "description": "<strong>品质因数</strong>（待求量）", "unit": "无单位"},
                {"symbol": r"\Delta f", "description": "通频带宽度", "unit": "Hz"},
            ],
        },
    },
    "exp30": {
        "table1": {
            "formulas": [{"title": "电容与介电常数", "steps": [{"note": "平行板电容：", "formula": r"C = \frac{\varepsilon_r \varepsilon_0 A}{d}"}]}],
            "variables": [
                {"symbol": "C", "description": "电容", "unit": "F"},
                {"symbol": r"\varepsilon_r", "description": "<strong>相对介电常数</strong>（待求量）", "unit": "无单位"},
                {"symbol": "A", "description": "极板有效面积", "unit": "m²"},
                {"symbol": "d", "description": "极板间距", "unit": "m"},
            ],
        },
        "table2": {
            "formulas": [],
            "variables": [
                {"symbol": "C", "description": "电容", "unit": "F"},
                {"symbol": "d", "description": "介质厚度", "unit": "m"},
            ],
        },
        "table3": {
            "formulas": [],
            "variables": [
                {"symbol": r"\varepsilon_r", "description": "<strong>相对介电常数</strong>（待求量）", "unit": "无单位"},
            ],
        },
    },
    "exp31": {
        "table1": {
            "formulas": [{"title": "电流表改装", "steps": [{"note": "分流电阻：", "formula": r"R_s = \frac{I_g r_g}{I - I_g}"}]}],
            "variables": [
                {"symbol": "R_s", "description": "分流电阻", "unit": "Ω"},
                {"symbol": "I_g", "description": "表头满偏电流", "unit": "A"},
                {"symbol": "r_g", "description": "表头内阻", "unit": "Ω"},
                {"symbol": "I", "description": "改装后量程电流", "unit": "A"},
            ],
        },
        "table2": {
            "formulas": [{"title": "电压表改装", "steps": [{"note": "分压电阻：", "formula": r"R_H = \frac{V - I_g r_g}{I_g}"}]}],
            "variables": [
                {"symbol": "R_H", "description": "分压电阻", "unit": "Ω"},
                {"symbol": "V", "description": "改装后量程电压", "unit": "V"},
            ],
        },
    },
    "exp32": {
        "table1": {
            "formulas": [{"title": "双臂电桥", "steps": [{"note": "消除接触电阻影响：", "formula": r"R_x = R_s \frac{R_2}{R_1}"}]}],
            "variables": [
                {"symbol": "R_x", "description": "<strong>待测低电阻</strong>（待求量）", "unit": "Ω"},
                {"symbol": "R_s", "description": "标准电阻", "unit": "Ω"},
                {"symbol": "R_1, R_2", "description": "比例臂电阻", "unit": "Ω"},
            ],
        },
        "table2": {"formulas": [], "variables": [{"symbol": "R_x", "description": "待测电阻", "unit": "Ω"}]},
        "table3": {"formulas": [], "variables": [{"symbol": "R_x", "description": "待测电阻", "unit": "Ω"}]},
        "table4": {"formulas": [], "variables": [{"symbol": "R_x", "description": "待测电阻", "unit": "Ω"}]},
    },

    # ── exp33-exp38: 复杂表格实验 ──
    "exp33": {"_global": {"formulas": [{"title": "对切透镜实验", "steps": [{"note": "干涉条纹间距：", "formula": r"\Delta x = \frac{D\lambda}{d}"}]}], "variables": [{"symbol": r"\Delta x", "description": "<strong>干涉条纹间距</strong>", "unit": "m"}, {"symbol": r"\lambda", "description": "光波长", "unit": "m"}, {"symbol": "d", "description": "双缝间距", "unit": "m"}]}},
    "exp34": {"_global": {"formulas": [{"title": "光纤传感器", "steps": [{"note": "全反射临界角：", "formula": r"\sin\theta_c = \frac{n_2}{n_1}"}]}], "variables": [{"symbol": r"\theta_c", "description": "<strong>全反射临界角</strong>", "unit": "rad"}, {"symbol": "n_1", "description": "纤芯折射率", "unit": "无单位"}, {"symbol": "n_2", "description": "包层折射率", "unit": "无单位"}]}},
    "exp35": {"_global": {"formulas": [{"title": "迈克尔逊干涉仪", "steps": [{"note": "移动反射镜 Δd，条纹变化数 N：", "formula": r"\Delta d = N \cdot \frac{\lambda}{2}"}]}], "variables": [{"symbol": r"\Delta d", "description": "反射镜移动距离", "unit": "m"}, {"symbol": "N", "description": "条纹变化数", "unit": "无单位"}, {"symbol": r"\lambda", "description": "<strong>光波长</strong>（待求量）", "unit": "m"}]}},
    "exp36": {"_global": {"formulas": [{"title": "马吕斯定律", "steps": [{"note": "<strong>马吕斯定律</strong>：", "formula": r"I = I_0 \cos^2\theta"}]}], "variables": [{"symbol": "I", "description": "透过检偏器后的光强", "unit": "W/m²"}, {"symbol": "I_0", "description": "入射偏振光光强", "unit": "W/m²"}, {"symbol": r"\theta", "description": "偏振方向与检偏器透光轴夹角", "unit": "rad"}]}},
    "exp37": {"_global": {"formulas": [{"title": "光栅方程", "steps": [{"note": "光栅衍射条件：", "formula": r"d(\sin\alpha + \sin\beta) = k\lambda"}]}], "variables": [{"symbol": "d", "description": "光栅常数", "unit": "m"}, {"symbol": r"\lambda", "description": "<strong>光波长</strong>（待求量）", "unit": "m"}, {"symbol": "k", "description": "衍射级次", "unit": "无单位"}]}},
    "exp38": {"_global": {"formulas": [{"title": "双光栅实验", "steps": [{"note": "莫尔条纹间距：", "formula": r"D = \frac{d}{\theta}"}]}], "variables": [{"symbol": "D", "description": "<strong>莫尔条纹间距</strong>", "unit": "m"}, {"symbol": "d", "description": "光栅常数", "unit": "m"}, {"symbol": r"\theta", "description": "两光栅夹角", "unit": "rad"}]}},

    # ── exp39-exp50: 二级实验 ──
    "exp39": {"table1": {"formulas": [{"title": "弗兰克-赫兹实验", "steps": [{"note": "电子与原子碰撞，能量量子化：", "formula": r"E = eV_s = n \cdot \Delta E"}]}], "variables": [{"symbol": "V_s", "description": "<strong>激发电位</strong>（待求量）", "unit": "V"}, {"symbol": "e", "description": "电子电荷量（常数）", "unit": "C"}]}},
    "exp40": {"table1": {"formulas": [{"title": "杨氏模量及泊松比", "steps": [{"note": "杨氏模量：", "formula": r"E = \frac{\sigma}{\varepsilon} = \frac{F/A}{\Delta L/L}"}, {"note": "泊松比：", "formula": r"\nu = -\frac{\varepsilon_{\text{横向}}}{\varepsilon_{\text{纵向}}}"}]}], "variables": [{"symbol": "E", "description": "<strong>杨氏模量</strong>（待求量）", "unit": "Pa"}, {"symbol": r"\nu", "description": "<strong>泊松比</strong>（待求量）", "unit": "无单位"}, {"symbol": "F", "description": "拉力", "unit": "N"}, {"symbol": r"\Delta L", "description": "伸长量", "unit": "m"}]}},
    "exp41": {"table1": {"formulas": [{"title": "超声光栅", "steps": [{"note": "超声波形成相位光栅：", "formula": r"\Lambda \sin\theta = k\lambda"}]}], "variables": [{"symbol": r"\Lambda", "description": "超声波长", "unit": "m"}, {"symbol": r"\lambda", "description": "光波长", "unit": "m"}]}},
    "exp42": {"table1": {"formulas": [{"title": "超声定位", "steps": [{"note": "回波测距：", "formula": r"d = \frac{v \cdot t}{2}"}]}], "variables": [{"symbol": "d", "description": "<strong>目标距离</strong>（待求量）", "unit": "m"}, {"symbol": "v", "description": "超声波速", "unit": "m/s"}, {"symbol": "t", "description": "回波时间", "unit": "s"}]}},
    "exp43": {"table1": {"formulas": [{"title": "刚体转动惯量", "steps": [{"note": "转动定律：", "formula": r"M = I\beta"}, {"note": "扭摆法测转动惯量：", "formula": r"I = \frac{mg r T^2}{4\pi^2}"}]}], "variables": [{"symbol": "I", "description": "<strong>转动惯量</strong>（待求量）", "unit": "kg·m²"}, {"symbol": "T", "description": "摆动周期", "unit": "s"}]}},
    "exp44": {"table1": {"formulas": [{"title": "凯特摆", "steps": [{"note": "复摆周期：", "formula": r"T = 2\pi\sqrt{\frac{I}{mgh}}"}, {"note": "凯特摆可逆条件：", "formula": r"g = \frac{4\pi^2 L_{\text{eff}}}{T^2}"}]}], "variables": [{"symbol": "g", "description": "<strong>重力加速度</strong>（待求量）", "unit": "m/s²"}, {"symbol": "L_{\text{eff}}", "description": "等效摆长", "unit": "m"}]}},
    "exp45": {"table1": {"formulas": [{"title": "空气阻尼振动", "steps": [{"note": "阻尼振动方程：", "formula": r"x(t) = A_0 e^{-\beta t}\cos(\omega t + \varphi)"}, {"note": "阻尼系数：", "formula": r"\beta = \frac{1}{T}\ln\frac{A_n}{A_{n+1}}"}]}], "variables": [{"symbol": r"\beta", "description": "<strong>阻尼系数</strong>（待求量）", "unit": "1/s"}, {"symbol": "A_n", "description": "第 n 个周期的振幅", "unit": "m"}]}},
    "exp46": {"table1": {"formulas": [{"title": "稳态法测导热系数", "steps": [{"note": "傅里叶热传导定律：", "formula": r"\frac{dQ}{dt} = -\kappa A \frac{dT}{dx}"}, {"note": "稳态时导热系数：", "formula": r"\kappa = \frac{Q \cdot d}{A \cdot \Delta T \cdot t}"}]}], "variables": [{"symbol": r"\kappa", "description": "<strong>导热系数</strong>（待求量）", "unit": "W/(m·K)"}, {"symbol": "A", "description": "传热面积", "unit": "m²"}, {"symbol": r"\Delta T", "description": "温差", "unit": "K"}]}},
    "exp47": {"table1": {"formulas": [{"title": "接触角测量", "steps": [{"note": "Young 方程：", "formula": r"\cos\theta = \frac{\gamma_{sv} - \gamma_{sl}}{\gamma_{lv}}"}]}], "variables": [{"symbol": r"\theta", "description": "<strong>接触角</strong>（待求量）", "unit": "°"}, {"symbol": r"\gamma_{sv}", "description": "固-气界面张力", "unit": "N/m"}, {"symbol": r"\gamma_{lv}", "description": "液-气界面张力", "unit": "N/m"}]}},
    "exp48": {"table1": {"formulas": [{"title": "传感器实验", "steps": [{"note": "传感器灵敏度：", "formula": r"S = \frac{\Delta V}{\Delta x}"}]}], "variables": [{"symbol": "S", "description": "<strong>传感器灵敏度</strong>（待求量）", "unit": "V/单位量"}]}},
    "exp49": {"table1": {"formulas": [{"title": "电子小制作", "steps": [{"note": "具体公式视电路设计而定。", "formula": None}]}], "variables": [{"symbol": "—", "description": "具体物理量视电路设计而定", "unit": "—"}]}},
    "exp50": {"table1": {"formulas": [{"title": "医学物理实验", "steps": [{"note": "具体公式视实验项目而定。", "formula": None}]}], "variables": [{"symbol": "—", "description": "具体物理量视实验项目而定", "unit": "—"}]}},

    # ── exp51-exp52: 外壳实验 ──
    "exp51": {"_global": {"formulas": [{"title": "用分光计测三棱镜折射率", "steps": [{"note": "最小偏向角法：", "formula": r"n = \frac{\sin\frac{A + \delta_{\min}}{2}}{\sin\frac{A}{2}}"}]}], "variables": [{"symbol": "n", "description": "<strong>折射率</strong>（待求量）", "unit": "无单位"}, {"symbol": "A", "description": "三棱镜顶角", "unit": "°"}, {"symbol": r"\delta_{\min}", "description": "<strong>最小偏向角</strong>", "unit": "°"}]}},
    "exp52": {"_global": {"formulas": [{"title": "配色实验", "steps": [{"note": "颜色混合的格拉斯曼定律（三原色原理）。", "formula": None}]}], "variables": [{"symbol": "—", "description": "配色实验基于三原色原理，无特定计算公式", "unit": "—"}]}},
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
