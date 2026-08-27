#!/usr/bin/env python3
"""
Finally that online downloader extension (FTODE) - Build & Release Packaging Tool
Creates a clean, branded release package containing:
1. FTODE Host Setup.bat (1-Click Installer - installs Native Host to %LOCALAPPDATA%\\FTODE)
2. FTODE Host Uninstall.bat (1-Click Uninstaller - cleans registry & removes host files)
3. FTODE-Extension.zip (Universal single-file extension package for Chrome/Edge/Opera/Firefox)
4. _backend\\ (Native Host backend files & engine bootstrapper)
5. Instructions.txt (Clear 2-step setup & uninstall instructions)
"""

import os
import sys
import io
import json
import base64
import shutil
import zipfile
import subprocess
import argparse

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_DIR = os.path.join(ROOT_DIR, 'extension')
NATIVE_HOST_DIR = os.path.join(ROOT_DIR, 'native_host')
DIST_DIR = os.path.join(ROOT_DIR, 'dist')
ICO_PATH = os.path.join(DIST_DIR, 'ftode_logo.ico')

# Files and directories to exclude from releases
EXCLUDE_PATTERNS = {
    '__pycache__',
    '.git',
    '.github',
    '.vs',
    '.vscode',
    '.idea',
    'debug_host.log',
    'debug_host.log.old',
    'cookies.txt',
    '*.tmp',
    '*.bak',
    '*.old',
    'Thumbs.db',
    'Desktop.ini',
    '.DS_Store'
}

INSTRUCTIONS_TEXT = """====================================================================
  Finally that online downloader extension (FTODE)
  Quick Setup & Uninstall Instructions
====================================================================

========================
>>> HOW TO INSTALL <<<
========================

STEP 1: Run Setup (Do this once)
--------------------------------------------------------------------
1. Double-click "FTODE Host Setup.bat" in this folder.
2. The setup will automatically install the background downloader
   engine (Host backend) into your system and register it across
   your browsers.
3. When you see "Setup Complete!", press any key to close.

* Note: Make sure Python 3.7+ is installed (from python.org or the
  Microsoft Store) with "Add Python to PATH" enabled.


STEP 2: Add Extension to Your Browser
--------------------------------------------------------------------
>>> For Google Chrome, Microsoft Edge, Brave, Opera, Opera GX:
1. Open your browser and go to your extensions manager:
   - Chrome / Brave:  chrome://extensions
   - Microsoft Edge:  edge://extensions
   - Opera:           opera://extensions
2. Turn ON "Developer mode" (toggle switch in top-right corner).
3. Drag and drop "FTODE-Extension.zip" directly onto the extensions page!
   (OR extract "FTODE-Extension.zip" into a folder and click "Load unpacked").
4. Pin the FTODE icon to your toolbar.

>>> For Mozilla Firefox / Floorp / LibreWolf:
1. Open Firefox and go to:  about:debugging#/runtime/this-firefox
2. Click "Load Temporary Add-on...".
3. Select the "FTODE-Extension.zip" file.


==========================
>>> HOW TO UNINSTALL <<<
==========================

1. Remove from Browser:
   - Right-click the FTODE icon in your browser toolbar.
   - Click "Remove from Chrome" / "Remove from Edge" / "Remove Extension".

2. Remove Native Host:
   - Double-click "FTODE Host Uninstall.bat" in this folder.
   - It will automatically clean all registry keys and remove backend files.
====================================================================
"""


def get_version():
    manifest_path = os.path.join(EXTENSION_DIR, 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', '1.0.1')
    except Exception:
        return '1.0.1'


def should_exclude(file_or_dir_name):
    name = os.path.basename(file_or_dir_name)
    if name in EXCLUDE_PATTERNS:
        return True
    for pat in EXCLUDE_PATTERNS:
        if pat.startswith('*.') and name.endswith(pat[1:]):
            return True
    return False


def format_size(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.2f} MB"


def generate_ftode_logo_ico(output_path):
    """Generates a high-res Windows .ico file using the official FTODE Logo."""
    try:
        from PIL import Image
        png_candidates = [
            os.path.join(EXTENSION_DIR, 'icons', 'logo512.png'),
            os.path.join(EXTENSION_DIR, 'icons', 'logo.png'),
            os.path.join(EXTENSION_DIR, 'icons', 'icon512.png')
        ]
        png_path = None
        for p in png_candidates:
            if os.path.isfile(p):
                png_path = p
                break

        if not png_path:
            print("[!] Warning: Logo PNG not found.")
            return False

        img = Image.open(png_path)
        sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
        img.save(output_path, sizes=sizes)
        return True
    except Exception as e:
        print(f"[!] Warning: Could not generate .ico: {e}")
        return False


def build_extension_archive(version, dist_path):
    """Builds a universal clean .zip containing the extension."""
    zip_name = f"FTODE-Extension-v{version}.zip"
    zip_path = os.path.join(dist_path, zip_name)

    file_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for file in files:
                if should_exclude(file):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, EXTENSION_DIR)
                zf.write(full_path, rel_path)
                file_count += 1

    size = os.path.getsize(zip_path)
    return zip_name, zip_path, file_count, size


def get_native_host_base64_payload():
    """Generates in-memory zip payload of native_host files as base64 string."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(NATIVE_HOST_DIR):
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for file in files:
                if should_exclude(file):
                    continue
                if file.lower().endswith('.exe'):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, NATIVE_HOST_DIR)
                zf.write(full_path, rel_path)

    return base64.b64encode(buf.getvalue()).decode('ascii')


def get_setup_bat_content(version, payload_b64):
    return f"""@echo off
title FTODE - 1-Click Host Setup
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
echo   FTODE - 1-Click Host Setup (v{version})
echo   Finally that online downloader extension
echo ===================================================
echo.

set "TARGET_DIR=%LOCALAPPDATA%\\FTODE"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [*] Installing FTODE Host backend to %TARGET_DIR%...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$b64='{payload_b64}'; $bytes=[Convert]::FromBase64String($b64); $tempZip=[IO.Path]::Combine([IO.Path]::GetTempPath(), 'ftode_setup_host.zip'); [IO.File]::WriteAllBytes($tempZip, $bytes); Expand-Archive -Path $tempZip -DestinationPath '%TARGET_DIR%' -Force; Remove-Item $tempZip -Force;"

if exist "%TARGET_DIR%\\install_host.bat" (
    cd /d "%TARGET_DIR%"
    call install_host.bat
) else (
    echo [v] Setup Complete! Extension is ready to use.
    echo.
    pause
)
"""


def get_uninstall_bat_content(version):
    return f"""@echo off
title FTODE - 1-Click Host Uninstaller
setlocal enabledelayedexpansion

echo ===================================================
echo   FTODE - 1-Click Host Uninstaller (v{version})
echo   Finally that online downloader extension
echo ===================================================
echo.

set "TARGET_DIR=%LOCALAPPDATA%\\FTODE"

echo [*] Stopping any active FTODE tasks...
taskkill /f /im yt-dlp.exe >nul 2>&1
taskkill /f /im ffmpeg.exe >nul 2>&1

echo [*] Removing FTODE Native Messaging Registry keys...
reg delete "HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts\\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Edge\\NativeMessagingHosts\\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\\Software\\Chromium\\NativeMessagingHosts\\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\\Software\\Mozilla\\NativeMessagingHosts\\com.ftode.host" /f >nul 2>&1

if exist "%TARGET_DIR%" (
    echo [*] Removing installed backend files from %TARGET_DIR%...
    rmdir /s /q "%TARGET_DIR%" >nul 2>&1
)

echo.
echo ===================================================
echo     FTODE Native Host Uninstalled Successfully!
echo ===================================================
echo.
echo Final Step:
echo Right-click the FTODE icon in your browser toolbar
echo and click "Remove from Chrome" / "Remove from Edge".
echo.
pause
"""


def build_clean_release_zip(version, dist_path, ext_zip_path):
    """
    Builds the clean 4-item release ZIP:
    1. FTODE Host Setup.bat (Self-contained 1-Click installer)
    2. FTODE Host Uninstall.bat (1-Click uninstaller)
    3. FTODE-Extension.zip (Universal extension package)
    4. Instructions.txt (Clear 2-step setup & uninstall guide)
    """
    release_zip_name = f"FTODE-v{version}-Release.zip"
    release_zip_path = os.path.join(dist_path, release_zip_name)
    base_folder = f"FTODE-v{version}"

    payload_b64 = get_native_host_base64_payload()
    setup_bat = get_setup_bat_content(version, payload_b64)
    uninstall_bat = get_uninstall_bat_content(version)

    temp_zip = os.path.join(dist_path, f"temp_release_{os.getpid()}.zip")
    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. FTODE Host Setup.bat (Self-contained)
        zf.writestr(os.path.join(base_folder, 'FTODE Host Setup.bat'), setup_bat)

        # 2. FTODE Host Uninstall.bat
        zf.writestr(os.path.join(base_folder, 'FTODE Host Uninstall.bat'), uninstall_bat)

        # 3. Universal Extension zip
        zf.write(ext_zip_path, os.path.join(base_folder, 'FTODE-Extension.zip'))

        # 4. Instructions.txt
        zf.writestr(os.path.join(base_folder, 'Instructions.txt'), INSTRUCTIONS_TEXT)

    # Safely replace the target zip
    for attempt in range(10):
        try:
            if os.path.isfile(release_zip_path):
                os.remove(release_zip_path)
            shutil.move(temp_zip, release_zip_path)
            break
        except Exception:
            import time
            time.sleep(0.5)
    else:
        fallback_name = f"FTODE-v{version}-Release-New.zip"
        fallback_path = os.path.join(dist_path, fallback_name)
        shutil.move(temp_zip, fallback_path)
        release_zip_name = fallback_name
        release_zip_path = fallback_path

    size = os.path.getsize(release_zip_path)
    return release_zip_name, release_zip_path, size


def main():
    parser = argparse.ArgumentParser(description="FTODE Build & Distribution Packager")
    args = parser.parse_args()

    version = get_version()

    print("=====================================================")
    print(f"   FTODE - Packaging Release v{version}")
    print("=====================================================")
    print("")

    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Generate High-Res Windows .ico from FTODE Logo
    print("[*] Generating high-resolution FTODE Logo .ico (from logo512.png)...")
    generate_ftode_logo_ico(ICO_PATH)

    # 2. Build Extension single file (.zip works for Chrome, Edge, Opera & Firefox)
    print("\n[*] Packaging Extension into universal single file (FTODE-Extension.zip)...")
    ext_name, ext_path, ext_count, ext_size = build_extension_archive(version, DIST_DIR)
    print(f"    [v] {ext_name} ({ext_count} files, {format_size(ext_size)})")

    # 3. Build Release ZIP
    print("\n[*] Packaging Release ZIP with 4 clean standalone items...")
    rel_name, rel_path, rel_size = build_clean_release_zip(version, DIST_DIR, ext_path)
    print(f"    [v] {rel_name} ({format_size(rel_size)})")

    print("\n=====================================================")
    print(f" [SUCCESS] Release archive created in: dist/")
    print("=====================================================")
    print(f" Release ZIP: {rel_name} ({format_size(rel_size)})")
    print(f"")
    print(f" Files inside {rel_name}:")
    print(f" |-- FTODE Host Setup.bat     (1-Click Self-Contained Installer - No SmartScreen)")
    print(f" |-- FTODE Host Uninstall.bat (1-Click Uninstaller - No SmartScreen)")
    print(f" |-- FTODE-Extension.zip      (Universal extension package for all browsers)")
    print(f" |-- Instructions.txt         (Simple 2-step setup & uninstall instructions)")
    print("=====================================================\n")


if __name__ == '__main__':
    main()
