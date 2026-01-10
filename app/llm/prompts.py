from typing import List, Dict, Any


def build_daily_summary_prompt(articles: List[Dict[str, Any]], date_str: str, *, min_items: int = 5, max_items: int = 10) -> List[Dict[str, str]]:
    """构建日常总结的提示词

    关键约束：
    - 必须基于提供的 articles 内容撰写，不允许编造不存在的新闻
    - 输出至少 min_items 条、最多 max_items 条要点（使用 Markdown 无序列表，每条以 '- ' 开头）
    - 要点顺序必须与输入 articles 顺序一致（方便我们逐条插图与引用来源）
    """

    # 为了避免模型“凭空扩写”，提供更强的结构化输入
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
            "content": f"""你是一位专业的AI新闻编辑，负责为中文微信公众号撰写每日AI新闻简报。

硬性要求（必须遵守）：
1) 只能基于我提供的新闻列表写作，不允许编造任何未在列表中出现的事实、公司动态、产品发布、数据或引用。
2) 输出必须包含一个 Markdown 无序列表，列出不少于{min_items}条且不超过{max_items}条“今日要点”。
3) 列表条目的顺序必须与输入新闻的顺序一致（即先用[1]，再[2]，依此类推），每条前缀必须是 '- '。
4) 每条要点建议 1-2 句话，最后带一句简短“结论/影响”（同样不能编造）。
5) 总字数尽量控制在800-1000字。

输出格式要求：
- 先给 1-2 句话开篇概述。
- 然后输出“今日要点”无序列表（每条以 '- ' 开头）。
- 最后给 1-2 句收尾观察。
""",
        },
        {
            "role": "user",
            "content": f"""今天是{date_str}。请基于以下新闻列表生成推文：

{articles_text}

直接输出推文内容，不要附加任何解释。""",
        },
    ]


def build_deep_dive_prompt(article: Dict[str, Any]) -> List[Dict[str, str]]:
    """构建深度解读的提示词"""
    return [
        {
            "role": "system",
            "content": """你是一位资深的AI行业分析师，负责为中文读者撰写深度解读文章。

要求：
1. 风格：专业、深入、有洞察力（产业分析 + 产品评测视角优先）
2. 结构：
   - 标题：吸引人且准确反映内容
   - 导语：概述新闻事件及其重要性
   - 背景：相关技术/公司/人物的背景信息
   - 分析：事件的影响、意义和可能的发展
   - 行业影响：对AI产业的影响
   - 结语：总结和展望
3. 字数：2500-3000字
4. 语言：使用中文，专业术语可保留英文
5. 只能基于提供新闻内容写作，不要编造不存在的事实
6. 格式：使用Markdown格式，包含标题、副标题、加粗重点和分段""",
        },
        {
            "role": "user",
            "content": f"""请根据以下新闻撰写一篇深度解读文章（围绕这一条新闻展开，不要扩展成未提供的事实）：

标题: {article.get('title','')}
来源: {article.get('source_name','')}
链接: {article.get('url','')}
发布时间: {article.get('publish_time','')}
内容:
{(article.get('content','') or '')[:6000]}...

请直接输出Markdown正文，不要包含其他说明。""",
        },
    ]


def build_article_metadata_prompt(title: str, content: str) -> List[Dict[str, str]]:
    """构建生成文章元数据的提示词"""
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


def build_wechat_html_prompt(article: Dict[str, Any]) -> List[Dict[str, str]]:
    """（暂未使用）构建生成微信公众号HTML的提示词"""
    return [
        {
            "role": "system",
            "content": """你是一位专业的微信公众号编辑，负责将文章转换为微信公众号友好的HTML格式。

要求：
1. 使用内联样式，确保在微信公众号编辑器中直接粘贴后格式正确
2. 保留原文的所有标题、段落、列表等结构
3. 为标题、引用、强调文本添加合适的样式
4. 确保代码块和链接格式正确
5. 输出完整的HTML文档，包含必要的样式""",
        },
        {
            "role": "user",
            "content": f"""请将以下Markdown文章转换为微信公众号HTML格式：

# {article.get('title','')}

{article.get('content','')}

请直接输出HTML代码，不要包含其他说明。""",
        },
    ]
