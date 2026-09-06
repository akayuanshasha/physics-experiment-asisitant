# RAG 评测失败案例

> 自动标记用于定位问题，P0/P1结论仍需人工复核。

共 5 题需要复核。

## R060 · 生活中的物理课堂上至少完成几个实验？要交什么，还需要预习报告或课后报告吗？

- split/suite/category：test / representative / requirements
- 自动分：100.0
- 标记：retrieval_noise
- 首个正确实验排名：1
- 返回实验：exp25, exp38, exp12, exp45, exp34, exp41, exp33, exp2, exp11, exp24, exp42, exp49
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R061 · 超声实验怎样用两组目标距离和回波时差测量水中声速？为什么距离差要乘2？

- split/suite/category：test / representative / formula
- 自动分：60.0
- 标记：forbidden_claim
- 首个正确实验排名：1
- 返回实验：exp42, exp9, exp42, exp41, exp41, exp9, exp42, exp42, exp42, exp9, exp42, exp41
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R062 · 用三线摆测圆盘和圆环的转动惯量时，周期怎样测，放置圆环时有什么对中要求？

- split/suite/category：test / representative / procedure
- 自动分：77.5
- 标记：missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp43, exp43, exp6, exp44, exp44, exp43, exp43, exp43, exp43, exp43, exp43, exp43
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R066 · 电子元件实验中，测量待测电解电容前要先做什么？高阶电路应在哪些安全电压下进行，课后是否需要完整报告？

- split/suite/category：test / representative / safety
- 自动分：88.75
- 标记：missing_answer_points
- 首个正确实验排名：2
- 返回实验：exp34, exp49, exp49, exp14, exp31, exp38, exp15, exp13, exp22, exp32, exp37, exp6
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary

## R068 · 某份学生指北说“生活中的物理必须课后写完整报告”，但我想按本学期正式讲义执行。到底要交什么？

- split/suite/category：test / boundary / source_conflict
- 自动分：88.75
- 标记：retrieval_noise, missing_answer_points
- 首个正确实验排名：1
- 返回实验：exp25, exp12, exp40, exp45, exp31, exp5, exp24, exp41, exp25, exp33, exp25, exp25
- 返回资料等级：primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary, primary
