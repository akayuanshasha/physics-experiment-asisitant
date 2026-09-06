# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 7 题需要复核。

## R058 · 数字体温计实验的基础内容和提升内容分别要做什么？

- split/suite/category：test / representative / requirements
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp17, exp17, exp50, exp50, exp27, exp31, exp33, exp11, exp1, exp30, exp7, exp7
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R060 · 生活中的物理课堂上至少完成几个实验？要交什么，还需要预习报告或课后报告吗？

- split/suite/category：test / representative / requirements
- 自动分：100.0
- 标记：retrieval_noise
- 首个正确实验排名：1
- 返回实验：exp25, exp33, exp12, exp38, exp41, exp11, exp23, exp24, exp50, exp34, exp45, exp48
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R061 · 超声实验怎样用两组目标距离和回波时差测量水中声速？为什么距离差要乘2？

- split/suite/category：test / representative / formula
- 自动分：100.0
- 标记：possible_forbidden_paraphrase
- 首个正确实验排名：1
- 返回实验：exp42, exp42, exp9, exp41, exp41, exp9, exp42, exp42, exp9, exp9, exp9, exp9
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R062 · 用三线摆测圆盘和圆环的转动惯量时，周期怎样测，放置圆环时有什么对中要求？

- split/suite/category：test / representative / procedure
- 自动分：77.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp43, exp43, exp6, exp44, exp44, exp4, exp4, exp43, exp43, exp43, exp43, exp43
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R066 · 电子元件实验中，测量待测电解电容前要先做什么？高阶电路应在哪些安全电压下进行，课后是否需要完整报告？

- split/suite/category：test / representative / safety
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp49, exp49, exp31, exp34, exp24, exp29, exp11, exp12, exp14, exp28, exp31, exp38
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R068 · 某份学生指北说“生活中的物理必须课后写完整报告”，但我想按本学期正式讲义执行。到底要交什么？

- split/suite/category：test / boundary / source_conflict
- 自动分：88.75
- 标记：retrieval_noise, missing_answer_points
- 首个正确实验排名：2
- 返回实验：exp12, exp25, exp31, exp41, exp33, exp50, exp40, exp36, exp19, exp38, exp48, exp45
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## B007 · 我没有上传液滴图片，请直接把知识库里的示例数据当成我的数据，判断样品是否亲水并给出角度。

- split/suite/category：test / boundary / example_boundary
- 自动分：100.0
- 标记：unexpected_source_tier, example_data_misuse
- 首个正确实验排名：1
- 返回实验：exp47, exp47, exp47, exp36, exp4, exp30, exp36, exp2, exp2, exp24, exp2, exp38
- 返回资料等级：primary, primary, example, example, example, example, primary, example, primary, example, example, primary
