from typing import List, Dict, Any


def build_arxiv_prompt(
    articles: List[Dict[str, Any]],
    date_str: str,
    *,
    select_count: int = 10,
) -> List[Dict[str, str]]:
    """构建“学术动态”栏目提示词

    约束：
    - 仅基于输入论文内容（标题/摘要/片段）
    - 从输入中挑选 select_count 篇最通俗易懂、最值得关注的
    - 每条至少 3 句话：研究问题/方法/结论（不允许编造）
    """

    articles_text = "\n\n---\n".join(
        f"[{i}] 标题: {a.get('title','')}\n"
        f"[{i}] 来源: arXiv cs.AI\n"
        f"[{i}] 链接: {a.get('url','')}\n"
        f"[{i}] 发布时间: {a.get('publish_time','')}\n"
        f"[{i}] 摘要: {a.get('summary','')}\n"
        f"[{i}] 正文片段: {(a.get('content','') or '')[:1200].replace('\\n',' ')}"
        for i, a in enumerate(articles, 1)
    )

    return [
        {
            "role": "system",
            "content": f"""你是一位AI学术编辑，负责撰写微信公众号栏目《学术动态》（面向非专业读者）。

硬性要求（必须遵守）：
1) 只能基于我提供的论文列表写作，不允许编造未在列表中出现的结论、实验结果、指标或引用。
2) 你需要从输入的论文中挑选{select_count}篇最通俗易懂、最值得读的论文进行介绍。
3) 输出必须是有序列表，正好{select_count}条，每条必须用递增的数字编号（第一条用"1. "，第二条用"2. "，第三条用"3. "，以此类推，不能都用"1. "）。
4) 每条格式要求：
   - 首先给出论文标题的中文翻译（如果标题本身就是中文则保持原样）
   - 然后介绍研究在解决什么问题、核心方法/思路、主要结论/发现（必须来自输入）
   - 总共至少3-4句话
5) 尽量用通俗中文解释专业概念，但不要过度发挥。

输出格式：
- 1-2句总览
- 然后输出有序列表，必须使用递增编号（1. 2. 3. 4. 5. ...），不能重复使用"1. "，每条格式：1. **标题翻译** 研究问题/方法/结论...
""",
        },
        {
            "role": "user",
            "content": f"""今天是{date_str}。请基于以下论文列表生成《学术动态》栏目内容：

{articles_text}

直接输出栏目正文，不要附加任何解释。""",
        },
    ]



def build_daily_summary_prompt(
    articles: List[Dict[str, Any]],
    date_str: str,
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> List[Dict[str, str]]:
    """构建日常总结（每日资讯）的提示词

    关键约束：
    - 必须基于提供的 articles 内容撰写，不允许编造不存在的新闻
    - 输出至少 min_items 条、最多 max_items 条要点（使用 Markdown 无序列表，每条以 '- ' 开头）
    - 要点顺序必须与输入 articles 顺序一致（方便我们逐条插图与引用来源）
    """

    articles_text = "\n\n---\n".join(
        f"[{i}] 标题: {a.get('title','')}\n"
        f"[{i}] 来源: {a.get('source_name','')}\n"
        f"[{i}] 链接: {a.get('url','')}\n"
        f"[{i}] 发布时间: {a.get('publish_time','')}\n"
        f"[{i}] 摘要: {a.get('summary','')}\n"
        f"[{i}] 正文片段: {(a.get('content','') or '')[:600].replace('\n',' ')}"
        for i, a in enumerate(articles, 1)
    )

    return [
        {
            "role": "system",
            "content": f"""你是一位专业的AI新闻编辑，负责为中文微信公众号撰写“每日资讯”栏目。

硬性要求（必须遵守）：
1) 只能基于我提供的新闻列表写作，不允许编造任何未在列表中出现的事实、公司动态、产品发布、数据或引用。
2) 输出必须包含一个有序列表，列出不少于{min_items}条且不超过{max_items}条"今日要点"。
3) 列表条目的顺序必须与输入新闻的顺序一致（即先用[1]，再[2]，依此类推），每条必须用递增的数字编号（第一条用"1. "，第二条用"2. "，第三条用"3. "，以此类推，不能都用"1. "）。
4) 每条要点必须把事情讲清楚（至少2句话），并给出一句简短"结论/影响"（同样不能编造）。
5) 总字数尽量控制在800-1000字。

输出格式要求：
- 先给 1-2 句话开篇概述。
- 然后输出"今日要点"有序列表，必须使用递增编号（1. 2. 3. 4. 5. ...），不能重复使用"1. "。
- 最后给 1-2 句收尾观察。
""",
        },
        {
            "role": "user",
            "content": f"""今天是{date_str}。请基于以下新闻列表生成“每日资讯”栏目内容：

{articles_text}

直接输出栏目正文，不要附加任何解释。""",
        },
    ]


def build_starmarket_prompt(
    articles: List[Dict[str, Any]],
    date_str: str,
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> List[Dict[str, str]]:
    """构建“科创头条”栏目提示词

    约束：
    - 仅基于输入文章内容
    - 输出 5-10 条列表要点（每条至少 3-4 句话，包含结论）
    """

    articles_text = "\n\n---\n".join(
        f"[{i}] 标题: {a.get('title','')}\n"
        f"[{i}] 来源: 科创板日报\n"
        f"[{i}] 链接: {a.get('url','')}\n"
        f"[{i}] 阅读量: {((a.get('extra') or {}).get('view_count',''))}\n"
        f"[{i}] 摘要: {a.get('summary','')}\n"
        f"[{i}] 正文片段: {(a.get('content','') or '')[:900].replace('\n',' ')}"
        for i, a in enumerate(articles, 1)
    )

    return [
        {
            "role": "system",
            "content": f"""你是一位科技与产业新闻编辑，负责撰写微信公众号栏目《科创头条》。

硬性要求（必须遵守）：
1) 只能基于我提供的文章列表写作，不允许编造未在列表中出现的事实。
2) 输出必须包含一个有序列表，列出不少于{min_items}条且不超过{max_items}条"头条要点"。
3) 列表条目的顺序必须与输入文章顺序一致（即先用[1]，再[2]...），每条必须用递增的数字编号（第一条用"1. "，第二条用"2. "，第三条用"3. "，以此类推，不能都用"1. "）。
4) 每条要点不能只有一句话，必须把事情讲清楚：
   - 发生了什么（背景/主体/动作）
   - 关键数字或关键信息（若输入里有）
   - 影响是什么
   - 最后直接给出结论性内容（例如"短期/长期影响"或"最重要的信号"），不要写"结论"、"总结"等字眼
5) 语言：中文。

输出格式：
- 1-2 句话总览
- 然后输出"头条要点"有序列表，必须使用递增编号（1. 2. 3. 4. 5. ...），不能重复使用"1. "，每条最后直接给出结论性内容，不要写"结论"二字
""",
        },
        {
            "role": "user",
            "content": f"""今天是{date_str}。请基于以下文章列表生成《科创头条》栏目内容：

{articles_text}

直接输出栏目正文，不要附加任何解释。""",
        },
    ]


def build_article_metadata_prompt(title: str, content: str) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": """你是一位专业的文章编辑，负责为文章生成元数据。

请根据文章内容：
1. 生成3-5个关键词（keywords）
2. 生成一段100字左右的摘要（summary）
3. 生成3-5个标签（tags）

请以JSON格式输出，包含以下字段：
- keywords: List[str]
- summary: str
- tags: List[str]""",
        },
        {
            "role": "user",
            "content": f"""请为以下文章生成元数据：

标题: {title}

内容:
{content[:2000]}

请直接输出JSON，不要包含其他内容。""",
        },
    ]
