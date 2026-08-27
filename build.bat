@echo off
title FTODE - Build Release
setlocal enabledelayedexpansion

echo =====================================================
echo   FTODE - Release Packager
echo   Building distribution ZIPs (Setup + Extension)
echo =====================================================
echo.

cd /d "%~dp0"

python build.py

if errorlevel 1 (
    echo.
    echo [x] Build failed! Please ensure Python is installed and in your PATH.
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
