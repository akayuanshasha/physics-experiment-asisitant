# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 35 题需要复核。

## R001 · A类不确定度和B类不确定度分别反映什么？两者如何合成为标准不确定度？

- split/suite/category：dev / representative / uncertainty
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp0, exp0, exp32, exp32, exp2, exp27, exp1, exp38, exp27, exp31, exp24, exp38

## R002 · 单摆法测重力加速度时，重力加速度怎样由摆长和周期计算？实际摆长应量到哪里？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp1, exp1, exp1, exp1, exp1, exp1, exp1, exp1, exp1, exp1, exp1, exp1

## R003 · 表面张力实验为什么要先做弹簧定标？定标图的横纵坐标和用途是什么？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp2, exp2, exp2, exp2, exp2, exp2, exp2, exp2, exp2, exp2, exp2, exp25

## R004 · 落球法测粘度时为什么要在小球达到匀速后计时？容器有限尺寸为什么需要修正？

- split/suite/category：dev / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp3, exp3, exp3, exp3, exp3, exp3, exp3, exp3, exp3, exp3, exp24, exp25

## R005 · 用几何法测圆柱体密度时需要测哪些量，密度公式是什么？为什么直径和高度通常要重复测量？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：retrieval_noise, missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp4, exp44, exp37, exp11, exp1, exp3, exp46, exp4, exp5, exp42, exp25, exp30

## R006 · 拉伸法测杨氏模量时为什么对加、减砝码读数取平均，并进行线性拟合？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp5, exp5, exp5, exp5, exp5, exp5, exp5, exp5, exp5, exp5, exp5, exp40

## R007 · 扭摆法计算金属丝切变模量时，为什么需要测空载和加载后的两个周期？若T1²−T0²接近零意味着什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp6, exp6, exp6, exp6, exp6, exp6, exp40, exp40, exp5, exp40, exp40, exp40

## R008 · 固体比热实验为什么要画温度—时间曲线并做雷诺校正，而不能直接取观察到的最高温度？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp7, exp7, exp7, exp7, exp7, exp7, exp7, exp7, exp7, exp46, exp7, exp7

## R009 · 用不同位置的瞬时速度验证匀加速运动时，为什么常作v²对2s的线性图？斜率表示什么？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp8, exp8, exp8, exp8, exp8, exp8, exp8, exp8, exp8, exp8, exp8, exp8

## R010 · 声速测量实验中的驻波法、相位比较法和时差法分别依赖什么可观测量？

- split/suite/category：dev / representative / cross_method
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp9, exp9, exp9, exp9, exp9, exp9, exp9, exp9, exp9, exp9, exp9, exp9

## R011 · 磁力摆实验为什么要分别拟合线圈磁场与电流关系，以及磁场同向、反向时的1/T²—I两条直线？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp10, exp10, exp10, exp10, exp10, exp10, exp25, exp28, exp26, exp25, exp50, exp34

## R012 · 半导体温度计为什么必须先标定I—T关系，标定后如何由电流读数求未知温度？

- split/suite/category：dev / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11, exp11

## R013 · 用李萨如图形测未知频率时，已知频率、未知频率与水平和竖直方向切点数之间是什么关系？操作时怎样判断图形适合读数？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp12, exp12, exp12, exp12, exp9, exp12, exp12, exp29, exp12, exp12, exp29, exp29

## R014 · 在整流滤波实验中，提高信号频率或增大滤波电容通常怎样影响纹波系数？比较时要控制哪些条件？

- split/suite/category：dev / representative / trend
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp13, exp13, exp13, exp14, exp14, exp13, exp13, exp13, exp13, exp13, exp13, exp49

## R015 · 直流电源负载实验中，输出功率和纹波系数如何由测量量计算？为什么不能对非线性内阻电源直接做短路测量？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp14, exp14, exp13, exp13, exp14, exp31, exp13, exp13, exp15, exp15, exp15, exp15

## R016 · 硅光电池实验中，暗伏安特性、输出特性以及开路电压/短路电流随照度变化分别应该画什么关系图？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp15, exp15, exp15, exp15, exp23, exp15, exp23, exp14, exp14, exp15, exp14, exp16

## R017 · 最小偏向角法测三棱镜折射率需要哪两个角度，折射率公式是什么？读数跨越0°/360°时应注意什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp18_b, exp18_b, exp18_b, exp18_b, exp18_b, exp37, exp18_b, exp18_b, exp18_b, exp18_b, exp18_b, exp18_b

## R018 · 用劈尖干涉测头发丝直径时，为什么测多条暗纹的总长度而不是相邻两条？直径怎样由测量量得到？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp19, exp19, exp40, exp19, exp19, exp19, exp19, exp35, exp35, exp33, exp35, exp35

## R019 · 磁阻效应数据为什么常用相对电阻变化ΔR/R(0)表示？作图时横纵坐标如何选择？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp26, exp26, exp26, exp26, exp26, exp26, exp48, exp34, exp42, exp40, exp43, exp50

## R020 · 非平衡电桥实验中，为什么要把输出电压Ug对桥臂电阻变化量或相对变化量作线性标定？

- split/suite/category：dev / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp27, exp27, exp27, exp27, exp27, exp27, exp27, exp27, exp27, exp11, exp27, exp17

## R021 · 霍尔效应实验为什么要通过换向测量得到V1、V2、V3、V4，而不是只读一次电压？霍尔电压怎样组合？

- split/suite/category：dev / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp28, exp28, exp28, exp28, exp28, exp28, exp28, exp28, exp34, exp18_b, exp5, exp7

## R022 · 串联RLC谐振实验中如何从幅频曲线求谐振频率和品质因数Q？改变电阻后Q怎样变化？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp29, exp29, exp29, exp29, exp30, exp29, exp30, exp29, exp30, exp29, exp29, exp29

## R023 · 用平行板电容器直接法测相对介电常数时，核心公式是什么？如果厚度用mm、面积用cm²，计算前要注意什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp30, exp30, exp30, exp30, exp30, exp30, exp30, exp30, exp29, exp46, exp30, exp44

## R024 · 把表头改装成量程为U的电压表时，串联分压电阻怎样计算？结果为负值说明什么？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp31, exp31, exp31, exp31, exp31, exp31, exp31, exp14, exp31, exp31, exp31, exp31

## R025 · 用双臂电桥测金属丝电阻率时，为什么采用四端连接？电阻率怎样由Rx、直径D和电压头间距L计算？

- split/suite/category：dev / representative / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp32, exp32, exp32, exp32, exp32, exp32, exp32, exp32, exp32, exp27, exp17, exp40

## D001 · 凸透镜公式法和位移法测焦距使用的是同一个直接计算公式吗？分别需要哪些原始量？

- split/suite/category：dev / deep / cross_method
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp20, exp20, exp20, exp20, exp33, exp20, exp25, exp25, exp34, exp25

## D002 · 透镜参数测量中，凸透镜物像距法、位移法、自准直法以及凹透镜物像距法各要重复测量几次？哪些量只测一次？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp20, exp20, exp20, exp20, exp20, exp20, exp20, exp20, exp20, exp25

## D003 · 辅助凸透镜测凹透镜焦距时，为什么计算结果应为负值？按指导书将物距p和像距p'都输入正值时，公式怎样写并满足什么大小关系？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp20, exp20, exp20, exp20, exp33, exp20, exp25, exp44, exp33, exp33

## D004 · 单缝衍射如何利用多级暗纹位置线性拟合求缝宽？缝宽变大时图样怎样变化？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp22, exp22, exp22, exp22, exp22, exp22, exp37, exp22, exp37, exp37, exp41, exp38

## D005 · 双缝模块记录亮纹和暗纹时，有效级次q应怎样填写？为什么同一组拟合不能混用两种级次？

- split/suite/category：dev / deep / data_format
- 自动分：20.0
- 标记：retrieval_noise, missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp22, exp5, exp35, exp33, exp35, exp19, exp22, exp22, exp18_b, exp38, exp33, exp35

## D006 · 用弹簧衍射图样测参数时，较宽和较窄条纹分别对应哪个结构尺寸？计算关系是什么？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp22, exp22, exp22, exp22, exp22, exp2, exp22, exp38, exp44, exp38, exp33, exp31

## D007 · 光电效应B是否要求写实验报告？即使不写报告，哪些数据处理仍然是必做？伏安特性曲线是不是必做？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp15

## D008 · 由U0—ν线性拟合怎样得到普朗克常量、逸出功和红限频率？斜率或截距符号异常时应怎样检查？

- split/suite/category：dev / deep / formula
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23

## D009 · 光电效应中如何用改变光阑孔径和改变光源距离两组实验验证饱和光电流与光强成正比？应分别对什么量作图？

- split/suite/category：dev / deep / trend
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23, exp23

## D010 · 密立根油滴静态平衡法的必做测量次数和数据处理要求是什么？为什么不能只测一次下落时间？

- split/suite/category：dev / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24
