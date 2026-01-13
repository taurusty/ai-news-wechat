@echo off
chcp 65001 >nul
echo ============================================
echo     Git 推送到 GitHub
echo ============================================
echo.

REM 检查是否已初始化Git仓库
if not exist .git (
    echo [步骤 1/5] 初始化Git仓库...
    git init
    echo.
) else (
    echo [✓] Git仓库已存在
    echo.
)

REM 设置Git用户信息（如果还没设置）
echo [步骤 2/5] 检查Git配置...
git config user.name >nul 2>&1
if errorlevel 1 (
    echo 请设置Git用户信息：
    set /p username="输入你的GitHub用户名: "
    set /p email="输入你的GitHub邮箱: "
    git config --global user.name "%username%"
    git config --global user.email "%email%"
    echo Git配置完成！
) else (
    echo [✓] Git配置已存在
)
echo.

REM 添加所有文件
echo [步骤 3/5] 添加文件到暂存区...
git add .
echo [✓] 文件已添加
echo.

REM 提交
echo [步骤 4/5] 提交到本地仓库...
set /p commit_msg="输入提交信息 (直接回车使用默认): "
if "%commit_msg%"=="" (
    set commit_msg=v1.1.0: AI资讯简报生成器 - 修复数据源并优化输出
)
git commit -m "%commit_msg%"
echo [✓] 提交完成
echo.

REM 检查是否已关联远程仓库
echo [步骤 5/5] 推送到GitHub...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo     首次推送 - 需要关联远程仓库
    echo ============================================
    echo.
    echo 请先在GitHub创建新仓库，然后输入仓库地址
    echo 格式示例: https://github.com/用户名/仓库名.git
    echo.
    set /p repo_url="GitHub仓库地址: "
    git remote add origin %repo_url%
    git branch -M main
    echo.
    echo 正在推送...
    git push -u origin main
) else (
    echo 正在推送到远程仓库...
    git push origin main
)

echo.
if errorlevel 1 (
    echo ============================================
    echo     ❌ 推送失败
    echo ============================================
    echo.
    echo 可能的原因：
    echo 1. 网络连接问题
    echo 2. 需要GitHub认证（使用Personal Access Token）
    echo 3. 远程仓库地址错误
    echo.
    echo 请查看错误信息，或参考 推送到GitHub.md 文档
) else (
    echo ============================================
    echo     ✅ 推送成功！
    echo ============================================
    echo.
    echo 你的代码已成功推送到GitHub
    echo 访问你的仓库查看：
    git remote get-url origin
)

echo.
pause
