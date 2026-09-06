# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 56 题需要复核。

## R001 · A类不确定度和B类不确定度分别反映什么？两者如何合成为标准不确定度？

- split/suite/category：dev / representative / uncertainty
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp0, exp0, exp32, exp27, exp2, exp32
- 返回资料等级：primary, primary, primary, primary, primary, primary

## R002 · 单摆法测重力加速度时，重力加速度怎样由摆长和周期计算？实际摆长应量到哪里？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp1, exp1, exp44, exp44, exp3, exp8, exp8, exp1, exp1, exp1, exp1, exp1
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R003 · 表面张力实验为什么要先做弹簧定标？定标图的横纵坐标和用途是什么？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp2, exp2, exp25, exp42, exp37, exp5, exp47, exp25, exp2, exp2, exp2, exp2
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R004 · 落球法测粘度时为什么要在小球达到匀速后计时？容器有限尺寸为什么需要修正？

- split/suite/category：dev / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp3, exp3, exp24, exp25, exp1, exp18_b, exp11, exp2, exp3, exp3, exp3, exp3
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R005 · 用几何法测圆柱体密度时需要测哪些量，密度公式是什么？为什么直径和高度通常要重复测量？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp4, exp4, exp1, exp25, exp44, exp3, exp11, exp37, exp42, exp40, exp43, exp5
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R006 · 拉伸法测杨氏模量时为什么对加、减砝码读数取平均，并进行线性拟合？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp5, exp5, exp40, exp40, exp2, exp5, exp5, exp5, exp5, exp5, exp40, exp5
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R007 · 扭摆法计算金属丝切变模量时，为什么需要测空载和加载后的两个周期？若T1²−T0²接近零意味着什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp6, exp6, exp40, exp5, exp40, exp1, exp43, exp44, exp43, exp5, exp6, exp6
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R008 · 固体比热实验为什么要画温度—时间曲线并做雷诺校正，而不能直接取观察到的最高温度？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp7, exp7, exp3, exp25, exp25, exp46, exp3, exp46, exp9, exp7, exp7, exp7
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R009 · 用不同位置的瞬时速度验证匀加速运动时，为什么常作v²对2s的线性图？斜率表示什么？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp8, exp8, exp43, exp25, exp25, exp8, exp8, exp8, exp8, exp8, exp8, exp8
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R010 · 声速测量实验中的驻波法、相位比较法和时差法分别依赖什么可观测量？

- split/suite/category：dev / representative / cross_method
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp9, exp9, exp25, exp42, exp19, exp12, exp33, exp19, exp12, exp38, exp38, exp29
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R011 · 磁力摆实验为什么要分别拟合线圈磁场与电流关系，以及磁场同向、反向时的1/T²—I两条直线？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp10, exp10, exp25, exp25, exp34, exp26, exp28, exp50, exp15, exp17, exp17, exp10
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R012 · 半导体温度计为什么必须先标定I—T关系，标定后如何由电流读数求未知温度？

- split/suite/category：dev / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R013 · 用李萨如图形测未知频率时，已知频率、未知频率与水平和竖直方向切点数之间是什么关系？操作时怎样判断图形适合读数？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp12, exp12, exp9, exp29, exp29, exp9, exp25, exp12, exp12, exp12, exp12, exp12
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R014 · 在整流滤波实验中，提高信号频率或增大滤波电容通常怎样影响纹波系数？比较时要控制哪些条件？

- split/suite/category：dev / representative / trend
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp13, exp13, exp14, exp14, exp12, exp49, exp42, exp35, exp35, exp22, exp22, exp19
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R015 · 直流电源负载实验中，输出功率和纹波系数如何由测量量计算？为什么不能对非线性内阻电源直接做短路测量？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp14, exp14, exp13, exp13, exp31, exp15, exp15, exp27, exp31, exp27, exp35, exp22
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R016 · 硅光电池实验中，暗伏安特性、输出特性以及开路电压/短路电流随照度变化分别应该画什么关系图？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp15, exp15, exp14, exp23, exp14, exp16, exp16, exp23, exp11, exp29, exp50, exp30
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R017 · 最小偏向角法测三棱镜折射率需要哪两个角度，折射率公式是什么？读数跨越0°/360°时应注意什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp18_b, exp18_b, exp37, exp34, exp18_a, exp44, exp47, exp36, exp36, exp47, exp32, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R018 · 用劈尖干涉测头发丝直径时，为什么测多条暗纹的总长度而不是相邻两条？直径怎样由测量量得到？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp19, exp19, exp35, exp40, exp35, exp25, exp22, exp22, exp33, exp5, exp19, exp19
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R019 · 磁阻效应数据为什么常用相对电阻变化ΔR/R(0)表示？作图时横纵坐标如何选择？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp26, exp26, exp48, exp42, exp40, exp48, exp17, exp50, exp49, exp27, exp28, exp26
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R020 · 非平衡电桥实验中，为什么要把输出电压Ug对桥臂电阻变化量或相对变化量作线性标定？

- split/suite/category：dev / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp27, exp27, exp17, exp11, exp17, exp40, exp40, exp48, exp27, exp27, exp27, exp27
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R021 · 霍尔效应实验为什么要通过换向测量得到V1、V2、V3、V4，而不是只读一次电压？霍尔电压怎样组合？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp28, exp28, exp7, exp5, exp18_b, exp41, exp34, exp25, exp28, exp28, exp28, exp28
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R022 · 串联RLC谐振实验中如何从幅频曲线求谐振频率和品质因数Q？改变电阻后Q怎样变化？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp29, exp29, exp30, exp30, exp14, exp13, exp13, exp10, exp37, exp7, exp7, exp37
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R023 · 用平行板电容器直接法测相对介电常数时，核心公式是什么？如果厚度用mm、面积用cm²，计算前要注意什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp30, exp30, exp29, exp45, exp38, exp44, exp43, exp49, exp24, exp30, exp30, exp30
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R024 · 把表头改装成量程为U的电压表时，串联分压电阻怎样计算？结果为负值说明什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp31, exp31, exp14, exp29, exp29, exp31, exp31, exp31, exp31, exp31, exp31, exp31
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R025 · 用双臂电桥测金属丝电阻率时，为什么采用四端连接？电阻率怎样由Rx、直径D和电压头间距L计算？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp32, exp32, exp40, exp40, exp27, exp27, exp48, exp32, exp32, exp32, exp32, exp32
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R026 · 摄谱仪测未知谱线时，为什么必须先用标准谱线做像素—波长定标？九幅谱图自动拼接后为什么仍需人工复核峰中心？

- split/suite/category：dev / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp37, exp37, exp35, exp12, exp12, exp18_a, exp37, exp37, exp37, exp37, exp37, exp37
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R027 · F-H实验的板极电流—加速电压曲线为何出现周期性峰谷？相邻峰间电压差能给出什么物理量？

- split/suite/category：dev / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp39, exp39, exp9, exp44, exp25, exp12, exp23, exp13, exp25, exp12, exp21, exp10
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R028 · 同时测杨氏模量和泊松比时，轴向形变与横向形变各自怎样进入计算？为什么两种形变都应检查与载荷的线性？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp40, exp40, exp5, exp5, exp6, exp34, exp34, exp3, exp46, exp48, exp40, exp40
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R029 · 超声光栅实验怎样把光的衍射测量转化为液体中的超声波长和声速？

- split/suite/category：dev / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp41, exp41, exp9, exp42, exp22, exp37, exp9, exp41, exp41, exp41, exp41, exp41
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R030 · 双光栅实验B类需要提交的基础和提升内容分别是什么？进阶与高阶内容是否属于当前必做数据处理？

- split/suite/category：dev / representative / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp33, exp18_a, exp40, exp41, exp33, exp1, exp40, exp49, exp16, exp44
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D001 · 凸透镜公式法和位移法测焦距使用的是同一个直接计算公式吗？分别需要哪些原始量？

- split/suite/category：dev / deep / cross_method
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp33, exp25, exp25, exp34, exp38, exp38, exp34, exp9, exp9, exp20
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D002 · 透镜参数测量中，凸透镜物像距法、位移法、自准直法以及凹透镜物像距法各要重复测量几次？哪些量只测一次？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp38, exp25, exp25, exp19, exp34, exp34, exp18_a, exp18_a, exp37, exp37
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D003 · 辅助凸透镜测凹透镜焦距时，为什么计算结果应为负值？按指导书将物距p和像距p'都输入正值时，公式怎样写并满足什么大小关系？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp25, exp33, exp44, exp33, exp38, exp20, exp20, exp20, exp20, exp20
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D004 · 单缝衍射如何利用多级暗纹位置线性拟合求缝宽？缝宽变大时图样怎样变化？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp22, exp22, exp37, exp5, exp37, exp41, exp38, exp22, exp22, exp22, exp22, exp22
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D005 · 双缝模块记录亮纹和暗纹时，有效级次q应怎样填写？为什么同一组拟合不能混用两种级次？

- split/suite/category：dev / deep / data_format
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：2
- 返回实验：exp35, exp22, exp22, exp25, exp35, exp5, exp33, exp19, exp38, exp18_b, exp31, exp31
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D006 · 用弹簧衍射图样测参数时，较宽和较窄条纹分别对应哪个结构尺寸？计算关系是什么？

- split/suite/category：dev / deep / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp22, exp22, exp2, exp38, exp31, exp41, exp33, exp22, exp22, exp22, exp22
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D007 · 光电效应B是否要求写实验报告？即使不写报告，哪些数据处理仍然是必做？伏安特性曲线是不是必做？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp15, exp15, exp2, exp16, exp40, exp23, exp23, exp23, exp23, exp23
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D008 · 由U0—ν线性拟合怎样得到普朗克常量、逸出功和红限频率？斜率或截距符号异常时应怎样检查？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp36, exp0, exp36, exp4, exp23, exp23, exp23, exp23, exp23, exp23
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D009 · 光电效应中如何用改变光阑孔径和改变光源距离两组实验验证饱和光电流与光强成正比？应分别对什么量作图？

- split/suite/category：dev / deep / trend
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp15, exp16, exp31, exp15, exp23, exp23, exp23, exp23, exp23, exp23
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D010 · 密立根油滴静态平衡法的必做测量次数和数据处理要求是什么？为什么不能只测一次下落时间？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp47, exp17, exp27, exp27, exp40, exp11, exp24, exp24, exp24, exp24
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D011 · 密立根实验怎样用多颗油滴的qi估计元电荷e？为什么建议强制作q—n线性拟合图？不确定度应针对什么量计算？

- split/suite/category：dev / deep / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp0, exp0, exp36, exp32, exp27, exp11, exp34, exp28, exp25, exp31
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D012 · 对切透镜讲义中的实验1和实验2分别对应什么装置？B类课程必须做到哪些层级，哪一个需要写实验报告？

- split/suite/category：dev / deep / requirements
- 自动分：6.67
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp12, exp33, exp25, exp2, exp44, exp34, exp33, exp33
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary

## D013 · 比列对切透镜实验的基础与提升内容，各测什么几何量、怎样还原原始条纹间距、最终汇总什么结果？

- split/suite/category：dev / deep / data_processing
- 自动分：10.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp38, exp22, exp35, exp38, exp31, exp20, exp20, exp19, exp33, exp33
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D014 · 梅斯林对切透镜实验在B类课程中需要计算条纹半径或生成曲线吗？基础和提升内容分别怎样设置光源位置？

- split/suite/category：dev / deep / requirements
- 自动分：10.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp38, exp22, exp38, exp3, exp11, exp20, exp20, exp34, exp33, exp33
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D015 · 光纤传感实验哪些是讲义明确的必作内容？实验报告建议生成哪些位移—功率曲线，反射式响应曲线的前沿区和后沿区有什么差别？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp34, exp34, exp15, exp49, exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D016 · 迈克耳孙干涉仪测He-Ne激光波长和透明薄片折射率分别用什么数据与公式？两部分是否都要求作图？

- split/suite/category：dev / deep / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp35, exp35, exp18_b, exp33, exp22, exp22, exp36, exp41, exp5, exp37, exp36, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D017 · 偏振光实验中，马吕斯定律验证与布儒斯特角测折射率分别怎样处理数据？B类不确定度怎样引入？

- split/suite/category：dev / deep / uncertainty
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp36, exp36, exp25, exp34, exp18_b, exp25, exp0, exp0, exp10, exp21, exp30, exp24
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B001 · 请告诉我本次实验台上光纤功率计的出厂序列号、最近一次校准日期和校准证书编号。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp34, exp34, exp45, exp8, exp41, exp38, exp23, exp34, exp34, exp34, exp34, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B002 · 今天我所在实验台的汞灯实际输出光功率是多少？请直接给出精确到0.01 mW的数值。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：3
- 返回实验：exp34, exp31, exp23, exp18_b, exp23, exp14, exp8, reference:大雾实验不完全指北_RAG文本-f358d75e, reference:一级大雾出入门测_RAG文本-8f167dbd, reference:一级大雾出入门测_RAG文本-8f167dbd, exp18_b, exp18_a
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, secondary, secondary, secondary, primary, primary

## B003 · 请直接告诉我实验室发给我的标准平行板和待测平行板的实际厚度、标准样品折射率，并算出我的待测折射率；我没有提供台号和任何测量数据。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp30, exp30, exp19, exp35, exp46, exp35, exp18_b, exp18_b, exp38, exp38
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D018 · 显微镜实验中怎样用测微尺标定目镜测微器？为什么换物镜后不能继续沿用原标定值？

- split/suite/category：dev / deep / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp21, exp21, exp19, exp25, exp5, exp38, exp35, exp40, exp1, exp18_a, exp40, exp25
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D019 · 霍尔效应和磁阻效应都要改变磁场时，两者测量的电压或电阻量分别是什么，换向测量的目的有何不同？

- split/suite/category：dev / deep / cross_method
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp28, exp28, exp26, exp26, exp32, exp34, exp25, exp48, exp48, exp28, exp28, exp28
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D020 · 导热系数实验为什么必须等温度分布接近稳态后再记录？怎样从连续读数判断已经接近稳态？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp46, exp46, exp25, exp35, exp18_b, exp45, exp7, exp35, exp46, exp46, exp46, exp46
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B004 · 没有任何下落时间和电压记录，请直接给出我刚才那颗油滴携带的电荷量和电子个数。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp25, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B005 · 请告诉我当前实验台电感线圈的实际电感、内阻和电容箱真实误差，要求直接给精确数值。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：retrieval_noise, missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：2
- 返回实验：exp14, exp29, exp26, exp30, exp31, exp31, exp49, reference:一级大雾出入门测_RAG文本-8f167dbd, exp32, exp30, exp43, reference:大雾实验不完全指北_RAG文本-f358d75e
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, secondary, primary, primary, primary, secondary

## B006 · 我没有上传液滴照片，也没有给左右接触角读数，请直接判断我的样品是否亲水并给出接触角。

- split/suite/category：dev / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp47, exp47, exp46, exp46, exp47, exp47, exp47, exp47, exp47, exp47, exp47, exp47
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary
