"""大学物理实验 RAG 查询清洗与术语别名表。

用途
====
本模块用于解决学生口语问法、教材规范术语、历史译名和中英文缩写不一致造成的
检索漏召回。它不直接修改知识库内容，也不调用大模型或网络接口。

推荐接入方式
------------
1. 调用 :func:`build_query_variants` 为原问题生成若干短查询；
2. 对每条短查询分别调用现有 ``retrieve()``；
3. 按文档来源、章节和文本去重，对同一块保留最高分；
4. 最终回答仍以检索到的实验指导为准，别名表不能作为实验结论来源。

为什么不把所有词拼成一个长查询：当前项目检索器按子串与中文 bigram 重叠度打分，
盲目扩写会增加分母、稀释相关词得分。多条短查询合并召回更适合现有实现。

数据原则
--------
* ``EXPERIMENT_ALIASES`` 和 ``TERM_ALIASES`` 仅放可安全互换的名称、译名和常见写法；
* ``RELATED_QUERY_EXPANSIONS`` 只表示同一实验中经常一起检索的概念，默认不启用；
* ``CONTEXTUAL_ALIASES`` 只有同时命中指定上下文时才生效；
* “误差/不确定度”“介电常数/相对介电常数”等不能无条件互换的概念明确隔离；
* 原查询始终保留，别名扩展只增加召回入口，不覆盖学生原意。

资料范围
--------
别名以“RAG相关资料整理/第一优先级”和“第二优先级”的实验指导、题库资料为主，
并用高校物理实验教学中心、大学物理教学论文和国家标准信息平台公开资料核对。
最后人工整理日期：2026-08-30。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping


ALIAS_DATA_VERSION = "2026.08.30"


# 供维护者复核用；运行时不访问这些地址。
ONLINE_REFERENCE_URLS: tuple[str, ...] = (
    "https://phyedu.dlut.edu.cn/info/1047/1042.htm",  # 迈克耳孙/迈克尔孙/迈克尔逊写法
    "https://physlab.bupt.edu.cn/wskc/gksy/jcwl/kewdqcdzdz/syyl.htm",  # 双臂/凯尔文电桥
    "https://tcep.pku.edu.cn/",  # 声速实验：极值、驻波、相位、李萨如
    "https://physlab.bupt.edu.cn/wskc/gksy/jcwl/gdpz/syyl.htm",  # 偏振、起偏器、检偏器、o/e 光
    "https://www.sy.uestc.edu.cn/cn/article/doi/10.12179/1672-4550.20230486",  # 液体黏滞系数
    "https://phylab.nuaa.edu.cn/2019/0219/c4085a148230/page.htm",  # 热导率/导热系数
    "https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D8230BD3A7E05397BE0A0AB82A",  # 测量不确定度
)


# ---------------------------------------------------------------------------
# 1. 学生问法清洗
# ---------------------------------------------------------------------------

POLITE_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^(?:请问|请教一下|麻烦问一下|麻烦你|劳驾)[，,：:\s]*",
        r"^(?:请介绍一下|请解释一下|请说明一下|请告诉我)[，,：:\s]*",
        r"^(?:我想知道|我想问一下|我不太明白|我没看懂)[，,：:\s]*",
        r"^(?:能否|可以|能不能)(?:请你)?(?:告诉我|解释一下|说明一下)?[，,：\s]*",
    )
)


def normalize_query(query: str | None, *, strip_polite: bool = True) -> str:
    """做保守的查询归一化，不删除公式符号、数字、单位或否定词。

    处理全角字符、常见破折号、微米符号和多余空白。礼貌前缀只从句首删除，
    不会删除“不是”“不要”等影响语义的词。
    """

    text = unicodedata.normalize("NFKC", query or "")
    text = (
        text.replace("µ", "μ")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("－", "-")
        .replace("·", "·")
    )
    text = re.sub(r"\s+", " ", text).strip()

    if strip_polite:
        previous = None
        while text and text != previous:
            previous = text
            for pattern in POLITE_PREFIX_PATTERNS:
                text = pattern.sub("", text, count=1).strip()
        text = text.lstrip("，,。.!！?？:：;； ")
    return text


def _search_form(text: str | None) -> str:
    """生成仅用于别名命中的形式，兼容 F-H、F H、F_H 等写法。"""

    normalized = normalize_query(text, strip_polite=False).casefold()
    return re.sub(r"[\s_\-]+", "", normalized)


# ---------------------------------------------------------------------------
# 2. 实验名称别名
# ---------------------------------------------------------------------------

# 规范名尽量与当前实验指导/知识库来源标题一致。单字母和单个物理符号不作为别名，
# 避免在普通问句中误命中。
EXPERIMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "平均值、标准差与不确定度计算": (
        "平均值标准差不确定度",
        "平均值和不确定度",
        "不确定度计算工具",
    ),
    "单摆法测重力加速度": (
        "单摆实验",
        "单摆测重力加速度",
        "单摆测g",
    ),
    "表面张力": ("表面张力实验", "表面张力系数测量"),
    "液体黏滞系数": (
        "液体粘滞系数",
        "液体粘性系数",
        "落球法测黏度",
        "落球法测粘度",
        "斯托克斯法测黏度",
        "斯托克斯法测粘度",
    ),
    "密度的测量": ("密度测量", "测密度"),
    "杨氏模量": (
        "杨氏弹性模量",
        "拉伸模量",
        "纵向弹性模量",
        "光杠杆法测杨氏模量",
    ),
    "切变模量": ("剪切模量", "刚性模量", "扭转法测切变模量"),
    "固体比热": ("固体比热容", "测固体比热", "量热法测比热"),
    "匀加速运动": ("匀变速运动", "匀加速直线运动"),
    "声速测量": ("声速的测量", "测声速", "测量空气中的声速", "超声波测声速"),
    "磁力摆": ("磁力摆实验", "亥姆霍兹线圈磁力摆"),
    "半导体温度计": ("半导体温度传感器", "半导体测温"),
    "示波器的使用": ("示波器实验", "示波器的调节与使用"),
    "整流滤波": ("整流与滤波", "整流滤波实验", "RC滤波实验"),
    "直流电源特性": ("直流稳压电源特性", "电源外特性"),
    "硅光电池": ("硅光电池特性", "太阳能电池特性"),
    "配色实验": ("RGB配色", "三基色配色", "颜色合成实验"),
    "数字体温计": ("数字温度计", "电子体温计"),
    "分光计的调节和使用": ("分光计调节", "分光计的调整", "分光计实验"),
    "用分光计测三棱镜折射率": (
        "三棱镜折射率",
        "最小偏向角法测折射率",
        "分光计测折射率",
    ),
    "干涉法测微小量": (
        "牛顿环实验",
        "牛顿环测曲率半径",
        "干涉法测头发丝直径",
    ),
    "透镜参数测量": (
        "透镜焦距测量",
        "薄透镜焦距",
        "公式法测焦距",
        "位移法测焦距",
        "自准直法测焦距",
    ),
    "显微镜的使用": ("显微镜实验", "光学显微镜的使用"),
    "衍射实验": (
        "单缝衍射",
        "双缝衍射",
        "衍射法测弹簧参数",
        "衍射实验B",
    ),
    "光电效应": (
        "光电效应测普朗克常量",
        "光电效应测普朗克常数",
        "光电管伏安特性",
    ),
    "密立根油滴实验": (
        "密里根油滴实验",
        "密立坎油滴实验",
        "Millikan油滴实验",
        "油滴法测元电荷",
        "油滴法测电子电荷",
    ),
    "生活中的物理实验": ("生活中的物理",),
    "磁阻效应": ("磁电阻效应", "MR效应", "磁阻特性"),
    "非平衡电桥": ("不平衡电桥", "非平衡直流电桥"),
    "霍尔效应": ("Hall效应", "霍耳效应", "霍尔实验"),
    "交流谐振电路": (
        "RLC串联谐振",
        "串联谐振电路",
        "电压谐振电路",
        "交流电路谐振",
    ),
    "介电常数": ("介电常数测量", "介质介电常数", "电容法测介电常数"),
    "数字表改装": ("数字电表改装", "数字万用表改装"),
    "双臂电桥": (
        "开尔文电桥",
        "凯尔文电桥",
        "Kelvin电桥",
        "直流双臂电桥",
        "双臂电桥测低电阻",
    ),
    "对切透镜的光学实验": (
        "对切透镜实验",
        "对切透镜光学实验1",
        "对切透镜光学实验2",
        "对切透镜法",
    ),
    "光纤传感器": ("光纤传感实验", "光纤传感器实验"),
    "迈克耳孙干涉仪": (
        "迈克尔孙干涉仪",
        "迈克尔逊干涉仪",
        "迈克耳逊干涉仪",
        "迈氏干涉仪",
        "Michelson干涉仪",
        "迈克耳孙实验",
    ),
    "偏振光": ("光的偏振", "偏振光实验", "偏振实验"),
    "摄谱仪与单色仪": (
        "摄谱仪和单色仪",
        "摄谱仪实验",
        "单色仪实验",
        "摄谱单色仪",
    ),
    "双光栅实验": ("双光栅", "双光栅测微弱振动", "双光栅拍频实验"),
    "弗兰克-赫兹实验": (
        "夫兰克-赫兹实验",
        "Franck-Hertz实验",
        "F-H实验",
    ),
    "测量金属丝的杨氏模量及泊松比": (
        "杨氏模量及泊松比",
        "金属丝泊松比",
        "杨氏模量和泊松比",
    ),
    "超声光栅": ("声光栅", "超声光栅实验", "声光衍射实验"),
    "超声定位与形貌成像": ("超声定位", "超声形貌成像", "超声成像实验"),
    "刚体转动惯量": ("刚体的转动惯量", "转动惯量实验"),
    "凯特摆": ("可倒摆", "可逆摆", "Kater摆", "凯特摆测重力加速度"),
    "空气阻尼": ("空气阻尼测定", "风阻测定", "流阻测量"),
    "导热系数": ("热导率", "热导系数", "导热率", "稳态法测导热系数"),
    "接触角仪": ("接触角测量", "液滴接触角", "接触角实验"),
    "传感器实验": ("传感器特性", "传感器综合实验"),
    "电子小制作": ("电子制作实验", "电子小制作实验"),
    "医学物理实验": ("医学物理", "纯音听阈测试", "电测听实验"),
}


# ---------------------------------------------------------------------------
# 3. 物理术语、方法与仪器别名
# ---------------------------------------------------------------------------

TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "算术平均值": ("平均值", "算术均值", "样本均值"),
    "样本标准差": ("实验标准差", "贝塞尔标准差", "标准偏差"),
    "A类标准不确定度": ("A类不确定度", "不确定度A类评定", "A类评定"),
    "B类标准不确定度": ("B类不确定度", "不确定度B类评定", "B类评定"),
    "合成标准不确定度": ("合成不确定度", "标准不确定度合成"),
    "扩展不确定度": ("展伸不确定度",),
    "不确定度传播": ("不确定度传递", "误差传递公式"),
    "最小二乘线性拟合": (
        "最小二乘法",
        "线性回归",
        "直线拟合",
        "最小二乘直线拟合",
    ),
    "相关系数": ("皮尔逊相关系数", "线性相关系数"),
    "逐差法": ("逐差处理", "逐差计算"),
    "相对误差": ("百分相对误差", "相对百分误差"),
    "重力加速度": ("自由落体加速度", "当地重力加速度"),
    "劲度系数": ("弹簧常量", "弹簧刚度系数", "弹性系数"),
    "液体黏滞系数": (
        "液体粘滞系数",
        "液体粘性系数",
        "内摩擦系数",
        "动力黏度",
        "动力粘度",
        "黏度",
        "粘度",
    ),
    "斯托克斯定律": ("Stokes定律", "斯托克斯公式"),
    "比热容": ("比热", "质量热容"),
    "光杠杆": ("光学杠杆", "镜尺法"),
    "亥姆霍兹线圈": ("Helmholtz线圈", "赫姆霍兹线圈"),
    "示波器触发": ("示波器同步", "触发同步"),
    "时基": ("扫描速度", "水平方向灵敏度", "时间基准"),
    "脉冲宽度": ("脉宽",),
    "直流电": ("直流", "DC", "Direct Current"),
    "交流电": ("交流", "AC", "Alternating Current"),
    "全波整流": ("全波整流电路", "双半波整流"),
    "π型RC滤波": ("π形RC滤波", "派型RC滤波", "π型滤波"),
    "纹波": ("交流纹波", "纹波电压"),
    "开路电压": ("空载电压",),
    "短路电流": ("短路光电流",),
    "三基色": ("RGB三基色", "红绿蓝三基色"),
    "最小偏向角": ("最小偏角", "最小偏转角"),
    "物方焦距": ("前焦距",),
    "像方焦距": ("后焦距",),
    "自准直法": ("平面镜反射法", "自准法"),
    "位移法": ("贝塞尔法", "二次成像法"),
    "光学显微镜": ("OM", "Optical Microscope"),
    "暗条纹级次": ("暗纹级次", "暗纹序数"),
    "He-Ne激光": ("氦氖激光", "HeNe激光", "氦氖激光器"),
    "标称值": ("名义值", "铭牌值"),
    "普朗克常量": ("普朗克常数", "Planck常量"),
    "饱和光电流": ("饱和电流", "光电饱和电流"),
    "元电荷": ("基本电荷", "电子电荷量", "基本电荷量"),
    "平衡测量法": ("静态法", "平衡法"),
    "磁阻率": ("磁电阻率", "磁阻比"),
    "取样电阻": ("采样电阻", "分流电阻"),
    "对称测量法": ("对称消除法", "换向法"),
    "幅频特性": ("幅频响应", "振幅频率特性", "谐振曲线"),
    "品质因数": ("Q值", "品质因素"),
    "相对介电常数": ("介电常数比", "相对电容率"),
    "电容率": ("绝对介电常数", "介质电容率"),
    "功能型光纤传感器": ("传感型光纤传感器",),
    "非功能型光纤传感器": ("传光型光纤传感器", "传光型传感器"),
    "马吕斯定律": ("Malus定律", "马律"),
    "布儒斯特角": ("布鲁斯特角", "起偏角", "完全偏振角"),
    "起偏器": ("起偏振器", "偏振器"),
    "检偏器": ("检偏振器", "分析器", "Analyzer"),
    "偏振化方向": ("透光轴", "透振方向", "偏振轴"),
    "寻常光": ("o光", "ordinary ray"),
    "非寻常光": ("e光", "非常光", "extraordinary ray"),
    "四分之一波片": ("1/4波片", "四分之一波长片", "λ/4波片"),
    "二分之一波片": ("1/2波片", "半波片", "λ/2波片"),
    "恒偏向棱镜": ("定偏向棱镜",),
    "电荷耦合器件": ("CCD", "Charge Coupled Device", "CCD图像传感器"),
    "第一辅线系": ("漫线系",),
    "第二辅线系": ("锐线系",),
    "柏格曼线系": ("基线系",),
    "超声致光衍射": ("声光效应", "声光衍射"),
    "光拍频": ("拍频", "差频"),
    "泊松比": ("泊松系数", "横向变形系数"),
    "热电偶": ("温差电偶", "热电偶温度计"),
    "导热系数": ("热导率", "热导系数", "导热率"),
    "接触角": ("润湿角", "液滴接触角"),
    "单向晶闸管": ("单向可控硅", "SCR", "晶闸管"),
    "交流直流变换": ("AC/DC变换", "交直流变换", "整流变换"),
    "声级计": ("分贝计", "噪声计"),
    "照度计": ("勒克斯计", "lux计"),
    "纯音听阈测试": ("纯音测听", "电测听", "行为测听"),
    "李萨如图形": ("李萨茹图形", "李沙育图形", "Lissajous图形"),
    "共振干涉法": ("驻波法", "极值法", "共振法"),
    "相位比较法": ("相位法", "行波法", "同相点法"),
}


# 只有出现相应上下文，才把这些表述视作同义。避免“截止电压”“拐点”等普通词
# 在其他电学问题中被误扩展。
CONTEXTUAL_ALIASES: tuple[dict[str, tuple[str, ...] | str], ...] = (
    {
        "canonical": "遏止电压",
        "aliases": ("截止电压", "截止电势", "遏止电势", "反向截止电压"),
        "requires_any": ("光电效应", "光电管", "光电子", "普朗克常量", "普朗克常数"),
    },
    {
        "canonical": "遏止电压拐点法",
        "aliases": ("拐点法", "伏安特性拐点"),
        "requires_any": ("光电效应", "遏止电压", "截止电压"),
    },
    {
        "canonical": "零电流法",
        "aliases": ("零电流点法",),
        "requires_any": ("光电效应", "遏止电压", "截止电压"),
    },
)


# ---------------------------------------------------------------------------
# 4. 相关概念扩展（默认关闭）
# ---------------------------------------------------------------------------

# 这些词不是同义词。仅当调用者明确设置 include_related=True 时，作为额外短查询
# 参与召回。适合“请全面介绍某实验”一类宽问题，不建议用于精确数值/公式问题。
RELATED_QUERY_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "不确定度": (
        "A类标准不确定度",
        "B类标准不确定度",
        "合成标准不确定度",
        "扩展不确定度",
        "灵敏系数",
    ),
    "单摆法测重力加速度": ("周期", "摆长", "线性拟合", "有效摆长"),
    "液体黏滞系数": ("斯托克斯定律", "终端速度", "雷诺数", "落球法"),
    "声速测量": ("共振干涉法", "相位比较法", "李萨如图形", "逐差法"),
    "示波器的使用": ("时基", "触发同步", "垂直灵敏度", "李萨如图形"),
    "透镜参数测量": ("公式法", "位移法", "自准直法", "焦距"),
    "衍射实验": ("单缝衍射", "双缝衍射", "线性拟合", "相对误差"),
    "光电效应": ("遏止电压", "伏安特性", "饱和光电流", "普朗克常量"),
    "密立根油滴实验": ("平衡测量法", "元电荷", "斯托克斯定律", "电荷量子化"),
    "霍尔效应": ("霍尔电压", "霍尔系数", "载流子浓度", "对称测量法"),
    "交流谐振电路": ("幅频特性", "谐振频率", "品质因数", "RLC串联电路"),
    "双臂电桥": ("低电阻", "四端接法", "附加电阻", "电阻率"),
    "迈克耳孙干涉仪": ("等倾干涉", "非定域干涉", "条纹吞吐", "激光波长"),
    "偏振光": ("马吕斯定律", "布儒斯特角", "起偏器", "检偏器", "波片"),
    "弗兰克-赫兹实验": ("第一激发电位", "非弹性碰撞", "原子能级", "拒斥电压"),
    "导热系数": ("稳态法", "热电偶", "冷却速率", "热传导"),
}


_UNCERTAINTY_RELATED_INTENTS: tuple[str, ...] = (
    "怎么", "如何", "怎样", "计算", "公式", "评定", "处理", "分析",
    "是什么", "介绍", "说明",
)

_SPECIFIC_UNCERTAINTY_TERMS: tuple[str, ...] = (
    "A类标准不确定度", "A类不确定度", "B类标准不确定度", "B类不确定度",
    "合成标准不确定度", "合成不确定度", "扩展不确定度", "展伸不确定度",
    "不确定度传播", "不确定度传递", "灵敏系数",
)


# 明确禁止做无条件同义替换的高风险概念，供代码审查和测试使用。
DO_NOT_MERGE_NOTES: dict[str, str] = {
    "误差 vs 不确定度": "二者定义不同；学生口语可用于查询相关章节，但不可互相替换或据此作答。",
    "准确度 vs 精密度": "准确度涉及接近真值，精密度涉及重复测量的一致程度。",
    "标准差 vs 标准不确定度": "数值和适用对象可能不同，不能仅凭名称等同。",
    "介电常数 vs 相对介电常数": "前者在资料中可能指电容率或俗称相对介电常数，必须结合公式和单位。",
    "摄谱仪 vs 单色仪": "同属光谱仪器但功能不同，一个记录光谱，一个选择窄波段。",
    "起偏器 vs 检偏器": "器件可互换使用，但在具体光路中的功能角色不同。",
    "干涉 vs 衍射": "都是波动现象，但实验原理、公式和数据处理不能混用。",
    "霍尔效应 vs 磁阻效应": "都与磁场有关，但测量量与物理机制不同。",
}


# ---------------------------------------------------------------------------
# 5. 匹配与查询变体 API
# ---------------------------------------------------------------------------

def _iter_groups(
    groups: Mapping[str, Iterable[str]],
) -> Iterable[tuple[str, tuple[str, ...]]]:
    for canonical, aliases in groups.items():
        yield canonical, tuple(dict.fromkeys((canonical, *aliases)))


def _match_groups(query: str, groups: Mapping[str, Iterable[str]]) -> list[str]:
    query_form = _search_form(query)
    if not query_form:
        return []

    matches: list[tuple[int, str]] = []
    for canonical, aliases in _iter_groups(groups):
        matched_lengths = [
            len(_search_form(alias))
            for alias in aliases
            if _search_form(alias) and _search_form(alias) in query_form
        ]
        if matched_lengths:
            matches.append((max(matched_lengths), canonical))

    # 优先返回命中的长词组，降低“光电效应测普朗克常量”被短词抢占的影响。
    matches.sort(key=lambda item: (-item[0], item[1]))
    return list(dict.fromkeys(canonical for _, canonical in matches))


def _match_contextual_aliases(query: str) -> list[str]:
    query_form = _search_form(query)
    result: list[str] = []
    for item in CONTEXTUAL_ALIASES:
        canonical = str(item["canonical"])
        aliases = tuple(item["aliases"])
        required = tuple(item["requires_any"])
        alias_hit = any(_search_form(alias) in query_form for alias in aliases)
        context_hit = any(_search_form(term) in query_form for term in required)
        if alias_hit and context_hit:
            result.append(canonical)
    return result


def detect_canonical_terms(query: str | None) -> dict[str, tuple[str, ...]]:
    """返回问句命中的规范实验名、规范术语和上下文别名。"""

    cleaned = normalize_query(query)
    return {
        "experiments": tuple(_match_groups(cleaned, EXPERIMENT_ALIASES)),
        "terms": tuple(_match_groups(cleaned, TERM_ALIASES)),
        "contextual": tuple(_match_contextual_aliases(cleaned)),
    }


def _append_unique(target: list[str], values: Iterable[str], max_items: int) -> None:
    for value in values:
        value = normalize_query(value, strip_polite=False)
        if value and value not in target:
            target.append(value)
        if len(target) >= max_items:
            return


def build_query_variants(
    query: str | None,
    *,
    include_related: bool = False,
    max_variants: int = 10,
) -> list[str]:
    """为一次学生提问生成适合“分别检索、合并召回”的短查询列表。

    返回顺序为：原问题、清洗后的问题、命中的规范实验名/术语、清洗问题加规范词。
    ``include_related`` 默认关闭；开启后只在剩余容量内加入相关概念短查询。
    """

    if max_variants < 1:
        raise ValueError("max_variants 必须大于 0")

    original = normalize_query(query, strip_polite=False)
    cleaned = normalize_query(query, strip_polite=True)
    if not original:
        return []

    variants: list[str] = []
    _append_unique(variants, (original, cleaned), max_variants)

    detected = detect_canonical_terms(cleaned)
    canonicals = list(
        dict.fromkeys(
            (*detected["experiments"], *detected["terms"], *detected["contextual"])
        )
    )
    _append_unique(variants, canonicals, max_variants)

    combined = (f"{cleaned} {canonical}" for canonical in canonicals)
    _append_unique(variants, combined, max_variants)

    if include_related and len(variants) < max_variants:
        related: list[str] = []
        for canonical in canonicals:
            related.extend(RELATED_QUERY_EXPANSIONS.get(canonical, ()))
        # 若学生直接输入“误差/不确定度”等宽词，也允许从键名触发。
        for trigger, terms in RELATED_QUERY_EXPANSIONS.items():
            if _search_form(trigger) in _search_form(cleaned):
                related.extend(terms)
        _append_unique(variants, related, max_variants)

    return variants[:max_variants]


def should_include_related_expansions(query: str | None) -> bool:
    """仅为宽泛的不确定度问法启用相关概念扩展。

    具体到 A/B 类、合成、扩展或传播的问题已经具有明确检索词，不再加入整组
    相关概念，避免稀释精确问题。该判定只依赖当前问题，保证新会话和已有历史
    中的同一句独立问题生成一致的检索变体。
    """

    cleaned = normalize_query(query)
    query_form = _search_form(cleaned)
    uncertainty_form = _search_form("不确定度")
    if not query_form or uncertainty_form not in query_form:
        return False
    if any(_search_form(term) in query_form for term in _SPECIFIC_UNCERTAINTY_TERMS):
        return False
    return query_form == uncertainty_form or any(
        _search_form(intent) in query_form for intent in _UNCERTAINTY_RELATED_INTENTS
    )


def expand_query_text(query: str | None, *, include_related: bool = False) -> str:
    """返回单条扩展文本，适合词项型检索；bigram 检索优先用多查询 API。"""

    cleaned = normalize_query(query)
    if not cleaned:
        return ""
    detected = detect_canonical_terms(cleaned)
    terms = list(
        dict.fromkeys(
            (*detected["experiments"], *detected["terms"], *detected["contextual"])
        )
    )
    if include_related:
        for canonical in tuple(terms):
            terms.extend(RELATED_QUERY_EXPANSIONS.get(canonical, ()))
    return " ".join(dict.fromkeys((cleaned, *terms)))


def validate_alias_data() -> list[str]:
    """检查空项、组内重复和跨规范词冲突；返回问题列表，空列表表示通过。"""

    problems: list[str] = []
    for group_name, groups in (
        ("EXPERIMENT_ALIASES", EXPERIMENT_ALIASES),
        ("TERM_ALIASES", TERM_ALIASES),
    ):
        reverse: dict[str, str] = {}
        for canonical, aliases in groups.items():
            if not canonical.strip():
                problems.append(f"{group_name}: 存在空规范名")
                continue
            normalized_aliases = [_search_form(alias) for alias in aliases]
            if any(not alias for alias in normalized_aliases):
                problems.append(f"{group_name}[{canonical}]: 存在空别名")
            if len(normalized_aliases) != len(set(normalized_aliases)):
                problems.append(f"{group_name}[{canonical}]: 存在重复别名")
            for alias in (_search_form(canonical), *normalized_aliases):
                owner = reverse.get(alias)
                if owner is not None and owner != canonical:
                    problems.append(
                        f"{group_name}: {alias!r} 同时属于 {owner!r} 与 {canonical!r}"
                    )
                reverse[alias] = canonical
    return problems


__all__ = [
    "ALIAS_DATA_VERSION",
    "EXPERIMENT_ALIASES",
    "TERM_ALIASES",
    "CONTEXTUAL_ALIASES",
    "RELATED_QUERY_EXPANSIONS",
    "DO_NOT_MERGE_NOTES",
    "normalize_query",
    "detect_canonical_terms",
    "build_query_variants",
    "expand_query_text",
    "validate_alias_data",
]


if __name__ == "__main__":
    issues = validate_alias_data()
    if issues:
        raise SystemExit("\n".join(issues))

    examples = (
        "请问迈克尔逊干涉仪怎么测氦氖激光波长？",
        "我想知道开尔文电桥为什么适合测低电阻",
        "密里根油滴实验怎样算电子电荷量",
        "请解释一下光电效应的截止电压怎么找",
        "李萨茹图形测声速是什么方法",
    )
    for example in examples:
        print(f"原问题：{example}")
        print("查询变体：")
        for variant in build_query_variants(example):
            print(f"  - {variant}")
        print()
