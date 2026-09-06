# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 18 题需要复核。

## R002 · 单摆法测重力加速度时，重力加速度怎样由摆长和周期计算？实际摆长应量到哪里？

- split/suite/category：dev / representative / formula
- 自动分：85.0
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp1, exp1, exp44, exp44, exp8, exp3, exp8, exp1, exp1, exp1, exp1, exp1
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R007 · 扭摆法计算金属丝切变模量时，为什么需要测空载和加载后的两个周期？若T1²−T0²接近零意味着什么？

- split/suite/category：dev / representative / formula
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp6, exp6, exp43, exp40, exp5, exp40, exp1, exp4, exp43, exp44, exp5, exp30
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R010 · 声速测量实验中的驻波法、相位比较法和时差法分别依赖什么可观测量？

- split/suite/category：dev / representative / cross_method
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp9, exp9, exp42, exp12, exp29, exp25, exp19, exp25, exp29, exp19, exp7, exp12
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R014 · 在整流滤波实验中，提高信号频率或增大滤波电容通常怎样影响纹波系数？比较时要控制哪些条件？

- split/suite/category：dev / representative / trend
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp13, exp13, exp14, exp14, exp2, exp49, exp12, exp49, exp12, exp25, exp25, exp35
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R020 · 非平衡电桥实验中，为什么要把输出电压Ug对桥臂电阻变化量或相对变化量作线性标定？

- split/suite/category：dev / representative / calibration
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp27, exp27, exp11, exp17, exp11, exp40, exp17, exp40, exp27, exp27, exp27, exp27
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R025 · 用双臂电桥测金属丝电阻率时，为什么采用四端连接？电阻率怎样由Rx、直径D和电压头间距L计算？

- split/suite/category：dev / representative / formula
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp32, exp32, exp40, exp40, exp27, exp27, exp48, exp32, exp32, exp32, exp32, exp32
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R030 · 双光栅实验B类需要提交的基础和提升内容分别是什么？进阶与高阶内容是否属于当前必做数据处理？

- split/suite/category：dev / representative / requirements
- 自动分：82.0
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp33, exp18_a, exp36, exp36, exp41, exp1, exp33, exp40, exp40, exp49
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D001 · 凸透镜公式法和位移法测焦距使用的是同一个直接计算公式吗？分别需要哪些原始量？

- split/suite/category：dev / deep / cross_method
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp20, exp20, exp33, exp33, exp25, exp38, exp25, exp34, exp19, exp9, exp34, exp9
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D006 · 用弹簧衍射图样测参数时，较宽和较窄条纹分别对应哪个结构尺寸？计算关系是什么？

- split/suite/category：dev / deep / unanswerable
- 自动分：67.5
- 标记：missing_answer_points, boundary_failure
- 首个正确实验排名：1
- 返回实验：exp22, exp22, exp2, exp38, exp31, exp33, exp22, exp22, exp22, exp22, exp22, exp22
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D007 · 光电效应B是否要求写实验报告？即使不写报告，哪些数据处理仍然是必做？伏安特性曲线是不是必做？

- split/suite/category：dev / deep / requirements
- 自动分：57.0
- 标记：missing_answer_points, forbidden_claim
- 首个正确实验排名：1
- 返回实验：exp23, exp23, exp15, exp15, exp2, exp34, exp38, exp16, exp12, exp36, exp27, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D010 · 密立根油滴静态平衡法的必做测量次数和数据处理要求是什么？为什么不能只测一次下落时间？

- split/suite/category：dev / deep / requirements
- 自动分：73.0
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp3, exp3, exp17, exp27, exp17, exp27, exp4, exp4, exp47, exp45
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D012 · 对切透镜讲义中的实验1和实验2分别对应什么装置？B类课程必须做到哪些层级，哪一个需要写实验报告？

- split/suite/category：dev / deep / requirements
- 自动分：68.67
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp12, exp20, exp2, exp25, exp44, exp38, exp36, exp45, exp20, exp34
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D013 · 比列对切透镜实验的基础与提升内容，各测什么几何量、怎样还原原始条纹间距、最终汇总什么结果？

- split/suite/category：dev / deep / data_processing
- 自动分：82.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp20, exp20, exp19, exp38, exp22, exp35, exp38, exp19, exp41, exp25
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D017 · 偏振光实验中，马吕斯定律验证与布儒斯特角测折射率分别怎样处理数据？B类不确定度怎样引入？

- split/suite/category：dev / deep / uncertainty
- 自动分：92.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp36, exp36, exp25, exp34, exp25, exp18_b, exp18_b, exp34, exp0, exp26, exp41, exp0
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B001 · 请告诉我本次实验台上光纤功率计的出厂序列号、最近一次校准日期和校准证书编号。

- split/suite/category：dev / boundary / unanswerable
- 自动分：77.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp34, exp34, exp36, exp8, exp11, exp45, exp22, exp15, exp11, exp38, exp37, exp37
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B003 · 请直接告诉我实验室发给我的标准平行板和待测平行板的实际厚度、标准样品折射率，并算出我的待测折射率；我没有提供台号和任何测量数据。

- split/suite/category：dev / boundary / unanswerable
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp35, exp30, exp35, exp18_b, exp18_b, exp36, exp30, exp19, exp19, exp46
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## D020 · 导热系数实验为什么必须等温度分布接近稳态后再记录？怎样从连续读数判断已经接近稳态？

- split/suite/category：dev / deep / requirements
- 自动分：77.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp46, exp46, exp25, exp35, exp7, exp18_b, exp45, exp46, exp46, exp46, exp46, exp46
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B005 · 请告诉我当前实验台电感线圈的实际电感、内阻和电容箱真实误差，要求直接给精确数值。

- split/suite/category：dev / boundary / unanswerable
- 自动分：85.0
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp29, exp49, exp30, exp29, exp14, exp30, exp26, exp31, exp31, exp3, exp32, exp13
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary
