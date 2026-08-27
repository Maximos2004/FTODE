@echo off
title FTODE - Build Release
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ---------------------------------------------------------
REM Check if Python is installed and accessible
REM ---------------------------------------------------------
python -c "import sys; assert sys.version_info >= (3, 7)" >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        goto :python_missing
    )
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)

echo =====================================================
echo   FTODE - Release Packager
echo   Building distribution ZIPs (Setup + Extension)
echo =====================================================
echo.

!PY_CMD! build.py

if errorlevel 1 (
    color 0C 2>nul
    echo.
    echo =====================================================
    echo  [X] Build failed - Please check error output above.
    echo =====================================================
    echo.
    pause
    exit /b 1
)

echo.
echo [*] Opening dist folder...
if exist "dist" (
    explorer "dist"
)

echo.
pause
exit /b 0

:python_missing
color 0C 2>nul
cls
echo ==============================================================================
echo.
echo   #####  #   # ##### #   #  ###  #   #
echo   #   #   # #    #   #   # #   # ##  #
echo   #####    #     #   ##### #   # # # #
echo   #        #     #   #   # #   # #  ##
echo   #        #     #   #   #  ###  #   #
echo.
echo   #   #  ###  #####   ### #   #  ### #####   ###  #     #     ##### ####
echo   ##  # #   #   #      #  ##  # #      #    #   # #     #     #     #   #
echo   # # # #   #   #      #  # # #  ###   #    ##### #     #     ###   #   #
echo   #  ## #   #   #      #  #  ##     #  #    #   # #     #     #     #   #
echo   #   #  ###    #     ### #   #  ###   #    #   # ##### ##### ##### ####
echo.
echo ==============================================================================
echo  [X] FATAL ERROR: PYTHON IS NOT INSTALLED OR NOT IN PATH
echo ==============================================================================
echo.
echo  FTODE packaging requires Python 3.8 or newer.
echo.
echo  ==========================================================================
echo  HOW TO INSTALL PYTHON:
echo  ==========================================================================
echo  1. Download Python from: https://www.python.org/downloads/
echo     (or install Python from the Microsoft Store)
echo.
echo  2. CRITICAL STEP DURING INSTALLATION:
echo     [IMPORTANT] Make sure to CHECK the box at the bottom of the installer:
echo         [X] Add python.exe to PATH
echo.
echo  3. After Python finishes installing, run build.bat again.
echo  ==========================================================================
echo.
set /p "OPEN_PY=Would you like to open the Python download page now? (Y/N): "
if /i "!OPEN_PY!"=="Y" (
    start https://www.python.org/downloads/
)
echo.
pause
exit /b 1

