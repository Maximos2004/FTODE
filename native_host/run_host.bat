@echo off
REM Finally that online downloader extension (FTODE) - Native Messaging Host Launcher
REM Ensures Python runs in unbuffered binary mode for browser stdio
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python -u "%~dp0host.py" %*
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        py -3 -u "%~dp0host.py" %*
    ) else (
        python -u "%~dp0host.py" %*
    )
)

