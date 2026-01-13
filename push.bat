@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo     推送到 GitHub
echo ============================================
echo.

echo [1/3] 添加文件...
git add .
if errorlevel 1 goto error

echo [2/3] 提交到本地仓库...
git commit -m "v1.1.0: fix data source issues and optimize HTML output"
if errorlevel 1 (
    echo 提示：可能没有新的更改需要提交
)

echo [3/3] 推送到GitHub...
git push origin main
if errorlevel 1 goto error

echo.
echo ============================================
echo     推送成功！
echo ============================================
echo.
echo 访问你的GitHub仓库查看更新
echo.
goto end

:error
echo.
echo ============================================
echo     出现错误
echo ============================================
echo.
echo 请查看上面的错误信息
echo.

:end
pause
