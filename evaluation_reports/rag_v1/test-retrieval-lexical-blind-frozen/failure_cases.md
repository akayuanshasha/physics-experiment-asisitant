# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 15 题需要复核。

## R026 · 摄谱仪测未知谱线时，为什么必须先用标准谱线做像素—波长定标？九幅谱图自动拼接后为什么仍需人工复核峰中心？

- split/suite/category：test / representative / calibration
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp37, exp37, exp37, exp37, exp35, exp37, exp37, exp37, exp37, exp12, exp37, exp37

## R027 · F-H实验的板极电流—加速电压曲线为何出现周期性峰谷？相邻峰间电压差能给出什么物理量？

- split/suite/category：test / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp39, exp39, exp39, exp39, exp39, exp44, exp9, exp12, exp25, exp43, exp12, exp13

## R028 · 同时测杨氏模量和泊松比时，轴向形变与横向形变各自怎样进入计算？为什么两种形变都应检查与载荷的线性？

- split/suite/category：test / representative / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp40, exp40, exp40, exp40, exp40, exp40, exp5, exp5, exp5, exp5, exp5, exp5

## R029 · 超声光栅实验怎样把光的衍射测量转化为液体中的超声波长和声速？

- split/suite/category：test / representative / principle
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp41, exp41, exp41, exp41, exp41, exp41, exp41, exp41, exp41, exp41, exp41, exp41

## R030 · 双光栅实验B类需要提交的基础和提升内容分别是什么？进阶与高阶内容是否属于当前必做数据处理？

- split/suite/category：test / representative / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp38, exp18_a, exp41, exp22, exp33, exp33, exp40, exp41, exp40, exp1

## D011 · 密立根实验怎样用多颗油滴的qi估计元电荷e？为什么建议强制作q—n线性拟合图？不确定度应针对什么量计算？

- split/suite/category：test / deep / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24, exp24

## D012 · 对切透镜讲义中的实验1和实验2分别对应什么装置？B类课程必须做到哪些层级，哪一个需要写实验报告？

- split/suite/category：test / deep / requirements
- 自动分：6.67
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp33, exp2, exp25, exp44, exp37, exp34, exp12, exp33, exp49, exp33

## D013 · 比列对切透镜实验的基础与提升内容，各测什么几何量、怎样还原原始条纹间距、最终汇总什么结果？

- split/suite/category：test / deep / data_processing
- 自动分：10.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp38, exp38, exp35

## D014 · 梅斯林对切透镜实验在B类课程中需要计算条纹半径或生成曲线吗？基础和提升内容分别怎样设置光源位置？

- split/suite/category：test / deep / requirements
- 自动分：10.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp33, exp38, exp38

## D015 · 光纤传感实验哪些是讲义明确的必作内容？实验报告建议生成哪些位移—功率曲线，反射式响应曲线的前沿区和后沿区有什么差别？

- split/suite/category：test / deep / requirements
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp34

## D016 · 迈克耳孙干涉仪测He-Ne激光波长和透明薄片折射率分别用什么数据与公式？两部分是否都要求作图？

- split/suite/category：test / deep / data_processing
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp35, exp35, exp35, exp35, exp35, exp35, exp35, exp35, exp35, exp35, exp35, exp35

## D017 · 偏振光实验中，马吕斯定律验证与布儒斯特角测折射率分别怎样处理数据？B类不确定度怎样引入？

- split/suite/category：test / deep / uncertainty
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp36, exp36, exp36, exp36, exp36, exp25, exp36, exp36, exp36, exp34, exp36, exp0

## B001 · 请告诉我本次实验台上光纤功率计的出厂序列号、最近一次校准日期和校准证书编号。

- split/suite/category：test / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp34, exp34, exp34, exp34, exp34, exp34, exp34, exp45, exp34, exp8, exp34, exp34

## B002 · 今天我所在实验台的汞灯实际输出光功率是多少？请直接给出精确到0.01 mW的数值。

- split/suite/category：test / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：3
- 返回实验：exp34, exp31, exp23, exp23, exp23, exp15, exp18_b, exp14, exp34, exp18_b, exp23, exp8

## B003 · 请直接告诉我实验室发给我的标准平行板和待测平行板的实际厚度、标准样品折射率，并算出我的待测折射率；我没有提供台号和任何测量数据。

- split/suite/category：test / boundary / unanswerable
- 自动分：20.0
- 标记：missing_answer_points, boundary_failure, missing_citation
- 首个正确实验排名：1
- 返回实验：exp38, exp38, exp38, exp38, exp38, exp35, exp30, exp30, exp19, exp18_b, exp46, exp35
