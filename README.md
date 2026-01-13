# AI资讯简报生成器

一个自动化的AI资讯聚合与生成工具，专为微信公众号设计。每天自动抓取多个科技网站的AI相关新闻，进行智能筛选、去重、排序，并调用DeepSeek大模型生成适合公众号发布的精美HTML内容。

## ✨ 主要特性

### 📰 三大核心栏目

1. **每日资讯** - 聚合国内外AI热点新闻（5-10条）
2. **科创头条** - 精选科创板AI相关要闻（5-10条）
3. **学术动态** - 精选arXiv AI领域最新论文（10条）

### 🎯 核心功能

- **多源数据抓取**
  - 🇨🇳 中文源：机器之心、新智元(AIERA)、科创板日报
  - 🇺🇸 英文源：Engadget、CNET、TechCrunch
  - 📚 学术源：arXiv CS.AI

- **智能过滤与去重**
  - 关键词智能过滤（支持中英文）
  - URL去重 + SimHash标题相似度去重
  - SQLite历史数据库防止重复推送

- **AI驱动内容生成**
  - 基于DeepSeek大模型生成专业资讯摘要
  - 智能提取核心要点，通俗易懂
  - 自动生成引言和总结

- **完美适配微信公众号**
  - 生成可直接粘贴的HTML格式
  - 自动下载并命名文章配图
  - 文献来源以可点击超链接形式呈现
  - 支持复制到公众号后保持链接可用

- **稳定性保障**
  - 单源超时保护（默认30秒）
  - 详细的进度日志和错误处理
  - 自动降级和备用源机制

## 🚀 快速开始

### 环境要求

- **操作系统**: Windows 10/11
- **Python**: 3.11 或 3.12（推荐）
- **API密钥**: DeepSeek API Key

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/linux_ai_news.git
cd linux_ai_news
```

#### 2. 创建虚拟环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. 安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 配置环境变量

```powershell
copy env.example .env
notepad .env
```

在`.env`文件中填写：

```env
DEEPSEEK_API_KEY=你的DeepSeek_API密钥
DEEPSEEK_MODEL=deepseek-chat
```

#### 5. 运行程序

```powershell
# 方式1：使用Python直接运行
python -m app.main

# 方式2：使用批处理脚本（推荐Windows用户）
运行.bat
```

## 📂 输出说明

运行成功后，会在`output/YYYY-MM-DD/`目录生成：

```
output/2026-01-13/
├── wechat.html              # 公众号HTML（可直接粘贴）
├── 每日资讯_markdown.md      # 每日资讯原始Markdown
├── 科创头条_markdown.md      # 科创头条原始Markdown
├── 学术动态_markdown.md      # 学术动态原始Markdown
├── images/                  # 文章配图（需手动上传到公众号）
│   ├── 每日资讯_01_xxx.jpg
│   ├── 科创头条_02_xxx.png
│   └── ...
└── aggregated.json         # 原始数据（用于调试）
```

### 如何发布到微信公众号

1. 用浏览器打开`wechat.html`，全选复制内容
2. 粘贴到微信公众号编辑器
3. 手动上传`images/`文件夹中的图片到公众号
4. 根据文件名提示，将图片插入对应位置
5. 验证超链接是否可点击，然后发布

> **注意**: 微信公众号编辑器不支持直接携带本地图片，需要手动上传。但文章链接会自动保留并可点击。

## ⚙️ 配置说明

配置文件：`config/config.yaml`

### 主要配置项

```yaml
columns:
  每日资讯:
    sources:
      - jiqizhixin      # 机器之心
      - aiera           # 新智元
      - engadget        # Engadget
      - cnet            # CNET
      - techcrunch_ai   # TechCrunch AI
    min_items: 5        # 最少5条
    max_items: 10       # 最多10条

  科创头条:
    sources:
      - chinastarmarket # 科创板日报
    min_items: 5
    max_items: 10

  学术动态:
    sources:
      - arxiv_cs_ai     # arXiv CS.AI
    min_items: 10
    max_items: 10

filter:
  keywords_any:         # 关键词白名单（命中即保留）
    - AI
    - 人工智能
    - machine learning
    # ... 更多关键词
  
  keywords_not:         # 关键词黑名单（命中即过滤）
    - 游戏
    - 娱乐
    # ... 更多关键词

timeouts:
  per_source_seconds: 30      # 单个数据源超时时间
  arxiv_source_seconds: 120   # arXiv超时时间（较大）
```

## 🛠️ 项目结构

```
linux_ai_news/
├── app/
│   ├── main.py              # 主程序入口
│   ├── sources/             # 数据源爬虫
│   │   ├── jiqizhixin.py    # 机器之心（API接口）
│   │   ├── aiera.py         # 新智元（WordPress解析）
│   │   ├── chinastarmarket.py # 科创板（Next.js数据提取）
│   │   ├── arxiv_cs_ai.py   # arXiv学术论文
│   │   └── ...
│   ├── pipeline/            # 数据处理流程
│   │   ├── filtering.py     # 关键词过滤
│   │   ├── dedup.py         # 去重（URL + SimHash）
│   │   ├── ranking.py       # 排序选择
│   │   └── writing.py       # AI写作
│   ├── llm/                 # 大模型交互
│   │   ├── deepseek_client.py
│   │   └── prompts.py       # 提示词模板
│   ├── render/              # HTML渲染
│   │   └── wechat_html.py   # 微信公众号HTML
│   └── images/              # 图片处理
│       └── pipeline.py      # 图片下载与命名
├── config/
│   └── config.yaml          # 主配置文件
├── db/
│   └── articles.sqlite3     # 历史数据库
├── output/                  # 输出目录（每日）
├── requirements.txt         # Python依赖
├── env.example              # 环境变量示例
└── 运行.bat                 # Windows启动脚本
```

## 🔧 常见问题

### 1. 某些网站抓取失败

**原因**: 网站可能有反爬虫保护、动态渲染、或临时故障

**解决方案**:
- 程序会自动跳过失败的源
- 可在`config/config.yaml`中禁用特定源
- 查看控制台日志了解具体失败原因

### 2. Engadget经常超时

**解决方案**:
- 这是正常现象，Engadget服务器响应较慢
- 可以增加超时时间或禁用该源
- 其他源足以满足最低5条新闻的要求

### 3. 科创头条内容为空

**已修复**: 最新版本已支持从Next.js页面的`__NEXT_DATA__`提取完整内容

### 4. 学术动态编号错误

**已修复**: 优化了LLM提示词，确保生成连续的有序列表

### 5. 图片无法在公众号显示

**说明**: 这是微信公众号的限制，不是程序问题
- 图片已下载到`images/`文件夹
- 需要手动上传到公众号后台
- 文件名已清晰标注对应的文章

## 📝 最新更新

### v1.1.0 (2026-01-13)

#### 🐛 Bug修复
- **机器之心**: 修复React动态渲染导致无法抓取的问题，改用官方API接口
- **新智元(AIERA)**: 适配WordPress的`<article>`标签结构
- **Engadget**: 简化URL匹配逻辑，提高抓取成功率
- **科创板日报**: 支持从`__NEXT_DATA__` JSON提取完整文章内容
- **arXiv**: 修复日期分组解析错误，确保能正确抓取当天论文

#### ✨ 功能改进
- **图片处理**: 图片不再嵌入HTML，改为独立文件夹，便于上传到公众号
- **文献来源**: 文章标题+可点击超链接，复制到公众号后仍可点击
- **列表编号**: 优化LLM提示词，确保生成正确的连续编号
- **HTML结构**: 只保留三个主标题，去除多余的子标题

#### 📊 数据抓取改进
- 每日资讯：从0篇提升到15-19篇
- 科创头条：稳定抓取17篇
- 学术动态：稳定抓取20篇

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 项目地址: [https://github.com/your-username/linux_ai_news](https://github.com/your-username/linux_ai_news)
- 问题反馈: [Issues](https://github.com/your-username/linux_ai_news/issues)

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的AI大模型支持
- 各个数据源网站 - 提供优质的AI资讯内容
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML解析
- [httpx](https://www.python-httpx.org/) - 异步HTTP客户端

---

**⚠️ 免责声明**: 本工具仅用于学习和个人使用，请遵守各数据源网站的robots.txt和使用条款。
