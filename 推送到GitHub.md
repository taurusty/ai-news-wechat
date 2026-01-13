# 推送到GitHub指南

## 方式一：首次推送（新仓库）

### 1. 初始化本地Git仓库

```bash
cd C:\Users\zang\Desktop\linux_ai_news
git init
```

### 2. 添加所有文件

```bash
git add .
```

### 3. 提交到本地仓库

```bash
git commit -m "v1.1.0: AI资讯简报生成器 - 修复数据源抓取问题并优化HTML输出"
```

### 4. 在GitHub创建新仓库

1. 访问 https://github.com/new
2. 仓库名称：`ai-news-generator` 或 `linux_ai_news`
3. 描述：AI资讯简报生成器 - 自动抓取AI资讯并生成微信公众号文章
4. 选择 Public 或 Private
5. **不要**勾选 "Initialize this repository with a README"
6. 点击 "Create repository"

### 5. 关联远程仓库并推送

```bash
# 添加远程仓库（替换为你的GitHub用户名）
git remote add origin https://github.com/你的用户名/ai-news-generator.git

# 推送到GitHub（首次推送）
git branch -M main
git push -u origin main
```

---

## 方式二：更新现有仓库

### 如果已经有GitHub仓库

```bash
cd C:\Users\zang\Desktop\linux_ai_news

# 查看当前状态
git status

# 添加所有更改
git add .

# 提交更改
git commit -m "v1.1.0: 修复数据源抓取问题，优化HTML输出和文献来源链接"

# 推送到GitHub
git push origin main
```

---

## 快速推送脚本（复制使用）

### 首次推送

```bash
cd C:\Users\zang\Desktop\linux_ai_news
git init
git add .
git commit -m "v1.1.0: AI资讯简报生成器首次发布"
git branch -M main
git remote add origin https://github.com/你的用户名/ai-news-generator.git
git push -u origin main
```

### 后续更新

```bash
cd C:\Users\zang\Desktop\linux_ai_news
git add .
git commit -m "更新说明"
git push origin main
```

---

## 常见问题

### 1. 推送时要求输入用户名和密码

GitHub已不再支持密码认证，需要使用Personal Access Token (PAT)：

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token" -> "Generate new token (classic)"
3. 设置权限：勾选 `repo`
4. 生成并复制Token
5. 推送时，用户名填GitHub用户名，密码填Token

### 2. 设置Git用户信息

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

### 3. 使用SSH方式（推荐）

```bash
# 生成SSH密钥
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 添加SSH公钥到GitHub
# 复制 ~/.ssh/id_ed25519.pub 的内容
# 访问 https://github.com/settings/keys 添加

# 使用SSH URL
git remote set-url origin git@github.com:你的用户名/ai-news-generator.git
```

### 4. 查看远程仓库

```bash
git remote -v
```

### 5. 撤销add但还未commit的文件

```bash
git reset HEAD 文件名
```

---

## 推送后的工作

1. 访问你的GitHub仓库页面
2. 检查README是否正确显示
3. 在仓库Settings中：
   - 添加Topics标签：`ai`, `python`, `news-aggregator`, `wechat`, `deepseek`
   - 设置仓库描述
   - （可选）启用GitHub Pages展示项目

4. 创建Release（可选）：
   - 访问 "Releases" -> "Create a new release"
   - Tag version: `v1.1.0`
   - Release title: `v1.1.0 - 数据源修复与HTML优化`
   - 描述：参考 CHANGELOG.md

---

## 注意事项

⚠️ **推送前请确认**：

- [ ] `.env` 文件已被 `.gitignore` 排除（不会推送API密钥）
- [ ] `output/` 文件夹已被排除（不推送生成的输出）
- [ ] `db/*.sqlite3` 已被排除（不推送本地数据库）
- [ ] `.venv/` 已被排除（不推送虚拟环境）

查看将要推送的文件：
```bash
git status
```

---

## 完成！🎉

推送成功后，你的项目将在 GitHub 上公开（或私有），可以：
- 分享给其他人使用
- 在其他电脑上克隆使用
- 接受贡献和Issue反馈
- 作为作品集展示
