@echo off
chcp 65001 >nul
echo ========================================
echo AI新闻简报生成器
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行以下命令：
    echo.
    echo   py -3.12 -m venv .venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 检查.env文件是否存在
if not exist ".env" (
    echo [错误] 未找到.env文件，请先配置：
    echo.
    echo   1. copy env.example .env
    echo   2. 编辑.env文件，填写DEEPSEEK_API_KEY
    echo.
    pause
    exit /b 1
)

echo [启动] 正在生成今日简报...
echo.

REM 运行主程序
.venv\Scripts\python.exe -m app.main --date today

echo.
echo ========================================
echo [完成] 简报生成完毕！
echo ========================================
echo.
echo 输出目录：output\%date:~0,4%-%date:~5,2%-%date:~8,2%\
echo.
echo 下一步：
echo   1. 用浏览器打开 wechat.html
echo   2. 复制内容到微信公众号后台
echo   3. 手动上传 cover.png 和 images\ 中的图片
echo.
pause
