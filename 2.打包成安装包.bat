@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

set "ISS_FILE=%~1"
if not defined ISS_FILE set "ISS_FILE=打包成安装器.iss"

if not exist "%ISS_FILE%" (
    echo [错误] 找不到 .iss 文件：
    echo "%ISS_FILE%"
    echo.
    echo [提示] 把 build_installer.bat 放到 .iss 同目录，或者把 .iss 路径作为第一个参数传进来。
    pause
    exit /b 1
)

set "ISCC_PATH="

if defined INNO_SETUP_COMPILER (
    if exist "%INNO_SETUP_COMPILER%" (
        set "ISCC_PATH=%INNO_SETUP_COMPILER%"
    )
)

if not defined ISCC_PATH (
    for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do (
        set "ISCC_PATH=%%i"
        goto :编译器已找到
    )
)

if not defined ISCC_PATH (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC_PATH (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC_PATH (
    if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
    )
)

if not defined ISCC_PATH (
    if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles%\Inno Setup 5\ISCC.exe"
    )
)

:编译器已找到
if not defined ISCC_PATH (
    echo [错误] 没找到 Inno Setup Compiler 的 ISCC.exe
    echo.
    echo 你可以用下面任意一种方式修复：
    echo 1. 安装 Inno Setup
    echo 2. 把 ISCC.exe 所在目录加到 PATH
    echo 3. 手动设置环境变量 INNO_SETUP_COMPILER
    echo.
    echo 例如：
    echo set "INNO_SETUP_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    echo.
    pause
    exit /b 1
)

echo [信息] 使用编译器：
echo "%ISCC_PATH%"
echo.
echo [信息] 使用脚本：
echo "%ISS_FILE%"
echo.
echo [开始] 正在调用 Inno Setup Compiler...
echo.

"%ISCC_PATH%" "%ISS_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [失败] 安装器打包失败，退出码：%EXIT_CODE%
    pause
    exit /b %EXIT_CODE%
)

echo [完成] 安装器打包成功
pause
exit /b 0