# 项目过程摘要（用于后续调试）

> 不包含任何 API Key、账号密码等敏感信息。

## 目标

- 每天抓取多个科技网站的 AI 相关新闻
- 自动汇总生成中文微信公众号推文 HTML
  - 周一：深度解读（约 3000 字，产业分析 + 产品评测视角）
  - 其他天：干货总结（800-1000 字左右，**5-10 条要点**）
- 配图策略：
  - 正文每条要点尽量配图（优先新闻原图，失败用占位分隔图）
  - “今日资讯来源”仅作为参考文献：**只保留标题列表，不包含链接/图片**
- 不使用定时任务：手动每日运行

## 关键实现点

- Windows 本地运行（Python 3.12），不依赖 Docker
- 站点抓取适配器：`app/sources/*`
  - 机器之心、AIERA、VentureBeat、Engadget、CNET、TechCrunch AI
  - 处理 429/5xx：基础重试；VentureBeat 经常 429，允许跳过
- 过滤/去重/选题：
  - 关键词过滤：`app/pipeline/filtering.py`
  - URL 去重 + 标题相似去重（SimHash）：`app/pipeline/dedup.py`
  - SQLite 历史库：`db/articles.sqlite3`
  - 选题条数：每天选 5-10 条
  - 若当天不足 5 条：尝试从 `output/前一天/sources_preview.json` 回填（真实来源，不编造）
- LLM 写作（DeepSeek）：
  - 客户端：`app/llm/deepseek_client.py`（OpenAI 兼容 `/v1/chat/completions`）
  - 提示词：`app/llm/prompts.py`
    - 强约束：只基于输入新闻，不得编造
    - 干货总结必须输出 5-10 条 `- ` 列表项，顺序与输入一致
- 渲染：
  - `app/render/wechat_html.py`：公众号用 HTML（内联样式）
  - 文末“今日资讯来源”仅输出标题列表
- 图片：
  - 下载新闻原图：`app/images/downloader.py`
  - 生成封面：`app/images/cover.py`
  - 生成占位分隔图：`app/images/separator.py`

## 稳定性与调试

- `app/main.py` 中每一步增加进度与耗时日志：`[START]/[DONE]`
- 单站点整体超时：`config/config.yaml -> timeouts.per_source_seconds`（默认 25s）
  - 超时后跳过该 source，继续后续站点

## 常见问题

- 公众号后台粘贴 HTML 不会带本地图片：需要在后台手动上传图片并插入
- Python 3.14 下依赖（lxml/Pillow/pydantic-core）容易因无 wheel 需要编译：推荐 Python 3.12

## 当前状态

- 生成流程已跑通：抓取 -> 过滤/去重 -> 选题 -> DeepSeek 写作 -> 下载/生成图片 -> 输出 `wechat.html`
- 已加入进度日志与单站点超时，减少卡死概率
