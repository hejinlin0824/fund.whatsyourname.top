SCREENING_PROMPT = """你是基金投研助理。下面按分类给出今日新闻标题，以及用户的持仓画像。
请挑出与【用户持仓市场/行业】最相关、最值得深读的条目（最多 15 条），忽略无关的。
只返回 JSON：{"picks":[{"id":<int>,"reason":"一句话为何相关"}]}。不要解释。

持仓画像：
{portfolio}

今日标题（按分类，格式 分类: id=标题）：
{titles}"""

ANALYSIS_SYSTEM = "你是资深基金投顾，用中文输出严格 JSON，面向基金小白，语气通俗、结论明确。"

ANALYSIS_PROMPT_NOON = """基于以下筛选后的新闻摘要与用户持仓，生成【午间速览】。只返回 JSON，结构：
{"market_brief":{"politics":[{"title":"","impact":""}],"finance_cn":[],"finance_oversea":[],"tech":[]},
 "bias":[{"fund":"","direction":"利好|利空|中性","reason":""}],
 "position_advice":[{"fund":"","action":"继续定投|暂停|减仓|加仓|观望","reason":""}],
 "lesson":{"title":"","body":""}}
说明：direction/action 必须点名用户具体基金；末尾免责声明由系统加，你不用写。
持仓：
{portfolio}
筛选后新闻摘要（id=标题：摘要）：
{summaries}"""

ANALYSIS_PROMPT_EVENING = ANALYSIS_PROMPT_NOON.replace(
    "生成【午间速览】", "生成【一日总结+明日预判】") + """
额外字段 tomorrow：{"events":[{"time":"","event":""}],"watch":"明日关注点位/数据一句话"}
即在 JSON 顶层追加 "tomorrow" 对象。"""
