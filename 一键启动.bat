@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "REQ_FILE=requirements.txt"
set "ENTRY_FILE=main.py"
set "PY_BOOTSTRAP="
set "PY_EXACT_VERSION=3.10.11"
set "VENV_CREATED=0"
set "STAMP_FILE=%VENV_DIR%\requirements.stamp"
set "APP_TRIED_SAFE=0"

call :detect_python
if not defined PY_BOOTSTRAP (
    echo [BOOT] Python 3.10 not found. Trying automatic install...
    call :install_python_310
    call :detect_python
)

if not defined PY_BOOTSTRAP (
    echo [ERROR] Python 3.10 was not prepared successfully.
    echo Please install Python 3.10 and run this script again.
    pause
    exit /b 1
)

call :ensure_venv
if errorlevel 1 (
    pause
    exit /b 1
)

set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_TS="
set "LAST_REQ_TS="
set "NEED_INSTALL=0"

echo [2/4] Preparing dependencies...
if exist "%REQ_FILE%" (
    for %%I in ("%REQ_FILE%") do set "REQ_TS=%%~tI"
    if "%VENV_CREATED%"=="1" (
        set "NEED_INSTALL=1"
    ) else (
        if not exist "%STAMP_FILE%" (
            set "NEED_INSTALL=1"
        ) else (
            set /p LAST_REQ_TS=<"%STAMP_FILE%"
            if /I not "!LAST_REQ_TS!"=="!REQ_TS!" set "NEED_INSTALL=1"
        )
    )

    if "!NEED_INSTALL!"=="1" (
        echo [3/4] Installing and updating dependencies...
        "%VENV_PY%" -m pip install --upgrade pip
        if errorlevel 1 (
            echo [ERROR] Failed to upgrade pip.
            pause
            exit /b 1
        )

        "%VENV_PY%" -m pip install -r "%REQ_FILE%"
        if errorlevel 1 (
            echo [ERROR] Failed to install dependencies.
            pause
            exit /b 1
        )

        > "%STAMP_FILE%" echo !REQ_TS!
    ) else (
        echo [3/4] Dependency check passed - already up to date.
    )
) else (
    echo [WARN] requirements.txt was not found, skipping dependency installation.
    echo [3/4] Dependency step skipped.
)

if not exist "%ENTRY_FILE%" (
    echo [ERROR] %ENTRY_FILE% was not found.
    pause
    exit /b 1
)

echo [4/4] Starting application...
call :run_app_normal
set "APP_EXIT=%ERRORLEVEL%"

if "%APP_EXIT%"=="-1073741819" call :run_app_safe_retry
if "%APP_EXIT%"=="3221225477" call :run_app_safe_retry

if not "%APP_EXIT%"=="0" (
    echo.
    echo Application exited with code %APP_EXIT%.
    echo Runtime log: logs\runtime.log
    echo Fatal log: logs\fatal_readable.log
    pause
)

exit /b %APP_EXIT%

:run_app_safe_retry
if "%APP_TRIED_SAFE%"=="1" goto :eof
set "APP_TRIED_SAFE=1"
echo [BOOT] Native crash detected (code %APP_EXIT%).
echo [BOOT] Retrying in safe mode: CPU renderer + windowed startup...
call :run_app_safe
set "APP_EXIT=%ERRORLEVEL%"
goto :eof

:run_app_normal
set "PYTHONFAULTHANDLER=1"
set "E5CM_SAFE_GC=1"
set "E5CM_RENDER_BACKEND="
set "E5CM_GPU_PIPELINE="
set "E5CM_HIGHDPI_SAFE_LAUNCH="
set "E5CM_VIDEO_DISABLE_GRAB="
set "E5CM_VIDEO_DISABLE_DECODER="
set "SDL_RENDER_DRIVER="
"%VENV_PY%" "%ENTRY_FILE%"
exit /b %ERRORLEVEL%

:run_app_safe
set "PYTHONFAULTHANDLER=1"
set "E5CM_SAFE_GC=1"
set "E5CM_RENDER_BACKEND=software"
set "E5CM_GPU_PIPELINE=0"
set "E5CM_HIGHDPI_SAFE_LAUNCH=off"
set "E5CM_VIDEO_DISABLE_GRAB=1"
set "E5CM_VIDEO_DISABLE_DECODER=1"
set "SDL_RENDER_DRIVER=software"
"%VENV_PY%" "%ENTRY_FILE%"
exit /b %ERRORLEVEL%

:ensure_venv
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo [BOOT] Existing virtual environment is not usable on this machine. Recreating...
        rmdir /s /q "%VENV_DIR%" >nul 2>nul
        if exist "%VENV_DIR%" (
            echo [ERROR] Failed to remove broken virtual environment: %VENV_DIR%
            exit /b 1
        )
    )
)

if not exist "%VENV_PY%" (
    echo [1/4] Creating virtual environment...
    call %PY_BOOTSTRAP% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
    set "VENV_CREATED=1"
)

set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment python executable was not found.
    exit /b 1
)

"%VENV_PY%" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Virtual environment python is still unavailable.
    exit /b 1
)
exit /b 0

:detect_python
set "PY_BOOTSTRAP="

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3.10 --version >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PY_BOOTSTRAP=py -3.10"
        goto :eof
    )
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PY_VERSION_TEXT="
    set "PY_MAJOR="
    set "PY_MINOR="
    for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set "PY_VERSION_TEXT=%%V"
    if defined PY_VERSION_TEXT (
        for /f "tokens=1,2 delims=." %%A in ("!PY_VERSION_TEXT!") do (
            set "PY_MAJOR=%%A"
            set "PY_MINOR=%%B"
        )
        if defined PY_MAJOR if defined PY_MINOR (
            if !PY_MAJOR! GTR 3 (
                set "PY_BOOTSTRAP=python"
                goto :eof
            )
            if !PY_MAJOR! EQU 3 if !PY_MINOR! GEQ 10 (
                set "PY_BOOTSTRAP=python"
                goto :eof
            )
        )
    )
)

if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PY_BOOTSTRAP="%LocalAppData%\Programs\Python\Python310\python.exe""
    goto :eof
)

if exist "%ProgramFiles%\Python310\python.exe" (
    set "PY_BOOTSTRAP="%ProgramFiles%\Python310\python.exe""
    goto :eof
)

if exist "%ProgramFiles(x86)%\Python310-32\python.exe" (
    set "PY_BOOTSTRAP="%ProgramFiles(x86)%\Python310-32\python.exe""
    goto :eof
)

goto :eof

:install_python_310
set "PY_INSTALLER=%TEMP%\python-%PY_EXACT_VERSION%-amd64.exe"

where winget >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [BOOT] Installing Python 3.10 via winget...
    winget install --id Python.Python.3.10 -e --scope user --silent --accept-package-agreements --accept-source-agreements >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        goto :eof
    )
    echo [BOOT] winget install failed. Switching to direct installer...
) else (
    echo [BOOT] winget was not found. Switching to direct installer...
)

echo [BOOT] Downloading Python 3.10 installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PY_EXACT_VERSION%/python-%PY_EXACT_VERSION%-amd64.exe' -OutFile '%PY_INSTALLER%'" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to download Python installer.
    goto :cleanup_python_installer
)

echo [BOOT] Running Python installer...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 Include_launcher=1
if errorlevel 1 (
    echo [ERROR] Python installer exited with an error.
)

:cleanup_python_installer
if exist "%PY_INSTALLER%" del /f /q "%PY_INSTALLER%" >nul 2>nul
goto :eof
