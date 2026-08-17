@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  Output-algo 项目初始化并推送到 GitHub 的一键脚本
REM  使用前请先：
REM    1. 安装 Git for Windows：https://git-scm.com/download/win
REM    2. 到 GitHub 创建好仓库
REM    3. 修改下方 REMOTE_URL 为你的仓库地址
REM ============================================================

REM ===== 在此填写你的 GitHub 仓库 HTTPS 地址 =====
set "REMOTE_URL=https://github.com/shaohui0505/Output-algo.git"
REM  例如: set "REMOTE_URL=https://github.com/zhangsan/output-algo.git"

REM ===== 你的 Git 用户名和邮箱（提交记录会显示） =====
set "GIT_NAME=shaohui0505"
set "GIT_EMAIL=shaohui0505@users.noreply.github.com"

REM ========== 以下无需修改 ==========

cd /d "%~dp0"

echo.
echo ==== 正在检查 Git 环境 ====
where git >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 git 命令。
    echo 请先安装 Git: https://git-scm.com/download/win
    echo 安装完成后关闭本窗口，重新双击运行。
    pause
    exit /b 1
)
echo [OK] Git 已安装
for /f "delims=" %%v in ('git --version') do echo      %%v

echo.
echo ==== 配置仓库 ====
set "URL_OK=1"
echo "%REMOTE_URL%" | findstr /c:"你的用户名" >nul && set "URL_OK=0"
echo "%REMOTE_URL%" | findstr /c:"你的仓库名" >nul && set "URL_OK=0"
if "%URL_OK%"=="0" (
    echo [错误] REMOTE_URL 还没有改为你的真实仓库地址。
    echo 请右键编辑本 .bat 文件，把 REMOTE_URL 这一行改成你 GitHub 仓库的 HTTPS 地址。
    echo 格式示例: https://github.com/zhangsan/output-algo.git
    echo.
    echo 修改后保存，再双击运行本脚本。
    pause
    exit /b 1
)
echo [OK] 远程仓库地址: %REMOTE_URL%

echo.
echo ==== 配置提交人信息（仅本仓库生效）====
git config --local user.name "%GIT_NAME%"
git config --local user.email "%GIT_EMAIL%"
git config --local core.autocrlf true
echo [OK] user.name = %GIT_NAME%
echo [OK] user.email = %GIT_EMAIL%

echo.
echo ==== 初始化仓库（若已初始化会跳过）====
if exist ".git" (
    echo [跳过] 仓库已初始化
) else (
    git init
    if errorlevel 1 (
        echo [错误] git init 失败
        pause
        exit /b 1
    )
    echo [OK] git init 完成
)

echo.
echo ==== 添加远程 origin（若已存在会跳过）====
git remote get-url origin >nul 2>nul
if errorlevel 1 (
    git remote add origin "%REMOTE_URL%"
    echo [OK] 已添加 origin = %REMOTE_URL%
) else (
    for /f "delims=" %%u in ('git remote get-url origin') do echo [跳过] origin 已存在: %%u
)

echo.
echo ==== 添加文件 ====
git add -A
echo [OK] git add 完成

echo.
echo ==== 提交 ====
git status --short
git diff --cached --quiet
if not errorlevel 1 (
    echo [跳过] 没有可提交的改动（工作区干净）
) else (
    git commit -m "feat: 初始提交 Output-algo 手表日志分组工具"
    if errorlevel 1 (
        echo [错误] git commit 失败
        pause
        exit /b 1
    )
    echo [OK] 提交完成
)

echo.
echo ==== 推送到 GitHub ====
REM 第一次推送用 -u，后续可直接 git push
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo ============================================================
    echo [错误] 推送失败。常见原因：
    echo   1. 需要身份验证（GitHub 不再支持账号密码）
    echo      - 解决：在 GitHub Settings  ^> Developer settings ^> Personal access tokens
    echo        生成 Token（勾选 repo 权限）。在被要求输入密码时，粘贴 Token。
    echo      - 或者：安装 GitHub CLI，运行 `gh auth login` 登录后再执行本脚本。
    echo   2. 远程仓库 URL 填错。
    echo   3. 远程仓库不是空的（已有 README 或 LICENSE 等）
    echo      - 解决：改为 `git push -u origin main --force`（会覆盖远程文件，谨慎！）
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ===== 推送成功！ =====
echo 可访问以下地址查看你的仓库:
echo   %REMOTE_URL%
echo.
pause
endlocal
