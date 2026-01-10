# 微信公众号 AI 热点推文生成器

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
- 输出
  - `output/YYYY-MM-DD/wechat.html`：公众号粘贴用 HTML
  - `output/YYYY-MM-DD/wechat_draft.json`：LLM 草稿（Markdown + 引用新闻）
  - `output/YYYY-MM-DD/images/` 与 `cover.png`：本地图片（用于手动上传到公众号）
  - `sources_preview.json`、`aggregated.json`：抓取与选题过程数据
- 稳定性
  - 进度日志：每一步打印 `[START]/[DONE]` 和耗时
  - 单站点整体超时：默认 25 秒，超时自动跳过该站点

## 环境要求

- Windows
- Python 3.12（推荐；3.11 也可）
- DeepSeek API Key

## 安装与运行

### 1) 创建虚拟环境并安装依赖

PowerShell（推荐）：

```powershell
cd C:\Users\zang\Desktop\linux_ai_news
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) 配置 `.env`

复制并编辑：

```powershell
copy env.example .env
notepad .env
```

填写：

```
DEEPSEEK_API_KEY=你的key
DEEPSEEK_MODEL=deepseek-chat
```

### 3) 运行

```powershell
python -m app.main --date today
```

## 输出与微信公众号发布流程

**重要说明：微信公众号后台粘贴 HTML 时不会携带你本地磁盘上的图片文件**（这是微信编辑器机制）。

推荐流程：

1. 运行生成器，得到：
   - `output/YYYY-MM-DD/wechat.html`
   - `output/YYYY-MM-DD/cover.png`
   - `output/YYYY-MM-DD/images/*`
2. 打开 `wechat.html`，复制正文到公众号后台。
3. 在公众号后台手动上传 `cover.png` 和 `images/` 中图片。
4. 按正文中图片位置插入上传后的图片（本项目输出的 HTML 在本地浏览器预览含图，但粘贴到公众号需要手动上传替换）。

## 配置说明

配置文件：`config/config.yaml`

常用项：
- `sources`: 开关各站点、设置权重
- `filter.keywords_any / keywords_not`: 关键词白名单/黑名单
- `timeouts.per_source_seconds`: 单个站点整体抓取超时（默认 25s）

## 常见问题

### 1) 某些站点抓不到/429
- VentureBeat 经常返回 429，程序会自动跳过。
- 你可在 `config/config.yaml` 里将其 `enabled: false`。

### 2) 运行卡住很久
- 现在已加进度日志与单站点整体超时。
- 如果仍卡住，查看控制台停在 `[START]` 哪一步，即可定位是：抓取 / LLM / 下载图片。

### 3) Python 3.14 装依赖失败
- 请使用 Python 3.12 或 3.11（Windows 下 lxml/Pillow 等需要预编译 wheel）。

## 目录结构

- `app/`
  - `main.py` 主流程
  - `sources/` 站点抓取适配器
  - `pipeline/` 过滤/去重/排序/写作
  - `llm/` DeepSeek 客户端与提示词
  - `images/` 封面生成、图片下载
  - `render/` HTML 渲染
  - `utils/` 进度日志
- `config/config.yaml`
- `output/` 每日输出
- `db/` SQLite 历史库

## 对话过程摘要（便于后续调试）

见 `PROJECT_NOTES.md`。
