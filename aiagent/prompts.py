SCREENING_PROMPT = """你是基金投研助理。下面按分类给出今日新闻标题，以及用户的持仓画像。
请挑出与【用户持仓市场/行业】最相关、最值得深读的条目（最多 15 条），忽略无关的。
只返回 JSON：{"picks":[{"id":<int>,"reason":"一句话为何相关"}]}。不要解释。

持仓画像：
{portfolio}

今日标题（按分类，格式 分类: id=标题）：
{titles}"""

ANALYSIS_SYSTEM = "你是资深基金投顾，用中文输出严格 JSON，面向基金小白，语气通俗、结论明确、有据可依。"

_REFS_RULE = """硬性要求：
1. direction/action 必须点名用户持有的具体基金。
2. 每条 bias 与 position_advice 都必须带 refs 数组（至少 1 条），注明结论参考了什么：
   - kind="仓位"：具体到哪只基金及其现状（市场/类型/市值/收益率/定投状态）。
   - kind="新闻"：点明参考的新闻标题。
3. 免责声明由系统加，你不用写。"""

ANALYSIS_PROMPT_NOON = """基于以下筛选后的新闻摘要、用户持仓与今日操作，生成【午间速览】。只返回 JSON：
{"market_brief":{"politics":[{"title":"","impact":""}],"finance_cn":[],"finance_oversea":[],"tech":[]},
 "bias":[{"fund":"","direction":"利好|利空|中性","reason":"","refs":[{"kind":"仓位|新闻","text":""}]}],
 "position_advice":[{"fund":"","action":"继续定投|暂停|减仓|加仓|观望","reason":"","refs":[{"kind":"仓位|新闻","text":""}]}],
 "lesson":{"title":"","body":""}}
""" + _REFS_RULE + """
额外：不要输出 tomorrow 字段（午间版无明日预判）。
持仓：
{portfolio}
{operations}
筛选后新闻摘要（id=标题：摘要）：
{summaries}"""

ANALYSIS_PROMPT_EVENING = """基于以下筛选后的新闻摘要、用户持仓与今日操作，生成【一日总结+明日预判】。只返回 JSON：
{"market_brief":{"politics":[{"title":"","impact":""}],"finance_cn":[],"finance_oversea":[],"tech":[]},
 "bias":[{"fund":"","direction":"利好|利空|中性","reason":"","refs":[{"kind":"仓位|新闻","text":""}]}],
 "position_advice":[{"fund":"","action":"继续定投|暂停|减仓|加仓|观望","reason":"","refs":[{"kind":"仓位|新闻","text":""}]}],
 "tomorrow":{"events":[{"time":"","event":""}],"watch":""},
 "lesson":{"title":"","body":""}}
""" + _REFS_RULE + """
额外：tomorrow 给出明日关键事件/数据与关注点位。
持仓：
{portfolio}
{operations}
筛选后新闻摘要（id=标题：摘要）：
{summaries}"""
