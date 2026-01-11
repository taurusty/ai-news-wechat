# 微信公众号 AI 热点推文生成器

> **最近更新（2026-01-11）**  
> - 修复有序列表编号在微信 HTML 中全部渲染为 **1.** 的问题。
> - 去除“**结论/影响：**”前缀，仅保留结论文字，提升阅读体验。
> - 代码已兼容 Python 3.12，并通过 Windows / macOS 双平台验证。

在 Windows 本地运行：每天抓取多个科技网站的 AI 相关新闻，做关键词筛选/去重/排序，调用 DeepSeek 生成中文推文，并输出适合粘贴到微信公众号后台的 HTML（含本地图片文件）。

## 功能概览

- 抓取来源（可在 `config/config.yaml` 开关）
  - 机器之心 `jiqizhixin.com`
  - AIERA `aiera.com.cn`
  - VentureBeat `venturebeat.com`（可能 429，被自动跳过）
  - Engadget `engadget.com`
  - CNET `cnet.com/news/`
  - TechCrunch AI `techcrunch.com/category/artificial-intelligence/`
- 过滤与去重
  - 关键词过滤（中英文关键词）
  - URL 去重 + 标题相似去重（SimHash）
  - SQLite 历史库：`db/articles.sqlite3`
- 选题
  - 每天选 5-10 条（不足 5 条会尝试从前一天 `output/` 回填真实来源；找不到则不硬凑）
- 写作
  - 周一：深度解读（围绕 Top 1）
  - 其他天：干货总结（5-10 条要点列表）
  - **严格要求不编造**：只基于输入新闻内容
  - **今日要点**：每条结尾自动去掉“结论/影响”前缀；HTML 渲染保证编号连续
- 输出
  - `output/YYYY-MM-DD/wechat.html`：公众号粘贴用 HTML
  - `output/YYYY-MM-DD/wechat_draft.json`：LLM 草稿（Markdown + 引用新闻）
  - `output/YYYY-MM-DD/images/` 与 `cover.png`：本地图片（用于手动上传到公众号）
  - `sources_preview.json`、`aggregated.json`：抓取与选题过程数据
- 稳定性
  - 进度日志：每一步打印 `[START]/[DONE]` 和耗时
  - 单站点整体超时：默认 25 秒，超时自动跳过该站点

## 环境要求

- Windows / macOS
- Python 3.12（推荐；3.11 亦可）
- DeepSeek API Key

...（其余内容保持不变）