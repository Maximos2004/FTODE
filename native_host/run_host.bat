@echo off
REM Finally that online downloader extension (FTODE) - Native Messaging Host Launcher
REM Ensures Python runs in unbuffered binary mode for browser stdio

set "PY_EXE="

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_EXE=python"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_EXE=py -3"
    )
)

if not defined PY_EXE (
    REM Check default user AppData Python locations (e.g. if browser was open before Python was installed)
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
        set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) else (
        set "PY_EXE=python"
    )
)

%PY_EXE% -u "%~dp0host.py" %*
exit /b %ERRORLEVEL%


