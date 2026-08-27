#!/usr/bin/env python3
"""
Finally that online downloader extension (FTODE) - Build & Release Packaging Tool
Creates clean, branded release packages:
1. FTODE-Extension-v{version}.zip (Universal browser extension)
2. FTODE-v{version}-Windows.zip   (Self-contained 1-Click Windows release bundle)
3. FTODE-v{version}-Linux.zip     (Self-contained 1-Click Linux release bundle)
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

INSTRUCTIONS_WINDOWS_TEXT = """====================================================================
  Finally that online downloader extension (FTODE)
  Quick Setup & Uninstall Instructions (Windows)
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

* Note: Make sure Python 3.8+ is installed (from python.org or the
  Microsoft Store) with "Add Python to PATH" enabled.


STEP 2: Add Extension to Your Browser
--------------------------------------------------------------------
>>> For Google Chrome, Microsoft Edge, Brave, Opera, Opera GX:
1. Open your browser and go to your extensions manager:
   - Chrome / Brave:  chrome://extensions
   - Microsoft Edge:  edge://extensions
   - Opera / Opera GX: opera://extensions
2. Turn ON "Developer mode" (toggle switch in top-right corner).
3. Drag and drop "FTODE-Extension-Chrome.zip" directly onto the page!
   (OR extract it into a folder and click "Load unpacked").
4. Pin the FTODE icon to your toolbar.

>>> For Mozilla Firefox / Floorp / LibreWolf:
1. Open Firefox and go to:  about:debugging#/runtime/this-firefox
2. Click "Load Temporary Add-on...".
3. Select the "FTODE-Extension-Firefox.zip" file.


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

INSTRUCTIONS_LINUX_TEXT = """====================================================================
  Finally that online downloader extension (FTODE)
  Quick Setup & Uninstall Instructions (Linux)
====================================================================

========================
>>> HOW TO INSTALL <<<
========================

STEP 1: Run Setup (Do this once)
--------------------------------------------------------------------
1. Open a terminal in this folder and run:
   bash "FTODE Host Setup.sh"
   (or make executable: chmod +x "FTODE Host Setup.sh" && ./"FTODE Host Setup.sh")

2. The setup will automatically install the background downloader
   engine into ~/.local/share/FTODE/ and register it across your browsers.

* Note: Make sure Python 3.8+ is installed. You can also install FFmpeg:
  - Ubuntu/Debian/Mint:  sudo apt install python3 ffmpeg
  - Arch/Manjaro:        sudo pacman -S python ffmpeg
  - Fedora:              sudo dnf install python3 ffmpeg


STEP 2: Add Extension to Your Browser
--------------------------------------------------------------------
>>> For Google Chrome, Chromium, Brave, Edge, Opera, Vivaldi:
1. Open your browser and go to your extensions manager:
   - Chrome / Chromium / Brave: chrome://extensions
   - Microsoft Edge:            edge://extensions
   - Opera / Opera GX:          opera://extensions
2. Turn ON "Developer mode" (toggle switch in top-right corner).
3. Extract "FTODE-Extension-Chrome.zip" and click "Load unpacked" (or drag & drop the zip).
4. Pin the FTODE icon to your toolbar.

>>> For Mozilla Firefox / Floorp / LibreWolf:
1. Open Firefox and go to:  about:debugging#/runtime/this-firefox
2. Click "Load Temporary Add-on...".
3. Select the "FTODE-Extension-Firefox.zip" file.


==========================
>>> HOW TO UNINSTALL <<<
==========================

1. Remove from Browser:
   - Right-click the FTODE icon in your browser toolbar and click Remove.

2. Remove Native Host:
   - Open a terminal and run: bash "FTODE Host Uninstall.sh"
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
            return False

        img = Image.open(png_path)
        sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
        img.save(output_path, sizes=sizes)
        return True
    except Exception:
        return False


def build_extension_archives(version, dist_path):
    """Builds clean dedicated .zip packages for Chrome/Opera/Edge and Firefox."""
    chrome_zip_name = f"FTODE-Extension-Chrome-v{version}.zip"
    chrome_zip_path = os.path.join(dist_path, chrome_zip_name)
    firefox_zip_name = f"FTODE-Extension-Firefox-v{version}.zip"
    firefox_zip_path = os.path.join(dist_path, firefox_zip_name)

    firefox_manifest_source = os.path.join(EXTENSION_DIR, 'manifest.firefox.json')
    has_firefox_manifest = os.path.isfile(firefox_manifest_source)

    # 1. Build Chrome / Chromium (Opera, Edge, Brave) Extension Archive
    chrome_count = 0
    with zipfile.ZipFile(chrome_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for file in files:
                if should_exclude(file) or file == 'manifest.firefox.json':
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, EXTENSION_DIR)
                zf.write(full_path, rel_path)
                chrome_count += 1

    # 2. Build Firefox Extension Archive
    firefox_count = 0
    with zipfile.ZipFile(firefox_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for file in files:
                if should_exclude(file) or file == 'manifest.firefox.json':
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, EXTENSION_DIR)
                if file == 'manifest.json' and has_firefox_manifest:
                    zf.write(firefox_manifest_source, 'manifest.json')
                else:
                    zf.write(full_path, rel_path)
                firefox_count += 1

    # Default universal extension alias pointing to Chrome build
    universal_zip_name = f"FTODE-Extension-v{version}.zip"
    universal_zip_path = os.path.join(dist_path, universal_zip_name)
    shutil.copyfile(chrome_zip_path, universal_zip_path)

    chrome_size = os.path.getsize(chrome_zip_path)
    firefox_size = os.path.getsize(firefox_zip_path)
    universal_size = os.path.getsize(universal_zip_path)

    return (
        chrome_zip_name, chrome_zip_path, chrome_count, chrome_size,
        firefox_zip_name, firefox_zip_path, firefox_count, firefox_size,
        universal_zip_name, universal_zip_path, universal_size
    )


def get_native_host_base64_payload():
    """Generates in-memory zip payload of native_host files as base64 string."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(NATIVE_HOST_DIR):
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for file in files:
                if should_exclude(file):
                    continue
                if file.lower().endswith(('.exe', '.tar.xz', '.zip')):
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

REM ---------------------------------------------------------
REM Check if Python is installed and accessible
REM ---------------------------------------------------------
python -c "import sys; assert sys.version_info >= (3, 7)" >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        goto :python_missing
    )
)

echo ===================================================
echo   FTODE - 1-Click Host Setup (Windows v{version})
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
exit /b %ERRORLEVEL%

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
echo  FTODE requires Python 3.8 or newer to run the background downloader engine.
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
echo  3. After Python finishes installing, run this Setup again.
echo  ==========================================================================
echo.
set /p "OPEN_PY=Would you like to open the Python download page now? (Y/N): "
if /i "!OPEN_PY!"=="Y" (
    start https://www.python.org/downloads/
)
echo.
pause
exit /b 1
"""


def get_uninstall_bat_content(version):
    return f"""@echo off
title FTODE - 1-Click Host Uninstaller
setlocal enabledelayedexpansion

echo ===================================================
echo   FTODE - 1-Click Host Uninstaller (Windows v{version})
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


def get_setup_sh_content(version, payload_b64):
    return f"""#!/usr/bin/env bash
set -e

# Verify python3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "\\033[1;31m"
    echo "=============================================================================="
    echo " [X] FATAL ERROR: python3 is not installed or not in PATH!"
    echo "=============================================================================="
    echo " FTODE requires Python 3.8+ to download media and run the backend host."
    echo ""
    echo " Please install Python 3 and FFmpeg using your package manager:"
    echo "   Ubuntu / Debian / Mint:  sudo apt install python3 ffmpeg"
    echo "   Arch / Manjaro:         sudo pacman -S python ffmpeg"
    echo "   Fedora / RHEL:          sudo dnf install python3 ffmpeg"
    echo "   openSUSE:               sudo zypper install python3 ffmpeg"
    echo "=============================================================================="
    echo -e "\\033[0m"
    exit 1
fi

echo "==================================================="
echo "  FTODE - 1-Click Host Setup (Linux v{version})"
echo "  Finally that online downloader extension"
echo "==================================================="
echo ""

TARGET_DIR="$HOME/.local/share/FTODE"
mkdir -p "$TARGET_DIR"

echo "[*] Installing FTODE Host backend to $TARGET_DIR..."

python3 -c "import base64, io, zipfile, os; b64='{payload_b64}'; raw=base64.b64decode(b64); z=zipfile.ZipFile(io.BytesIO(raw)); z.extractall(os.path.expanduser('~/.local/share/FTODE'))"

chmod +x "$TARGET_DIR/host.py" "$TARGET_DIR/run_host.sh" 2>/dev/null || true

if [ -f "$TARGET_DIR/install_host.sh" ]; then
    chmod +x "$TARGET_DIR/install_host.sh"
    bash "$TARGET_DIR/install_host.sh"
else
    python3 "$TARGET_DIR/host.py" --install
    python3 "$TARGET_DIR/host.py" --bootstrap
fi
"""


def get_uninstall_sh_content(version):
    return f"""#!/usr/bin/env bash
echo "==================================================="
echo "  FTODE - 1-Click Host Uninstaller (Linux v{version})"
echo "  Finally that online downloader extension"
echo "==================================================="
echo ""

TARGET_DIR="$HOME/.local/share/FTODE"

echo "[*] Removing FTODE Native Messaging manifests..."
if [ -f "$TARGET_DIR/host.py" ]; then
    python3 "$TARGET_DIR/host.py" --uninstall
fi

if [ -d "$TARGET_DIR" ]; then
    echo "[*] Removing installed backend files from $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
fi

echo ""
echo "==================================================="
echo "    FTODE Native Host Uninstalled Successfully!"
echo "==================================================="
echo ""
echo "Final Step:"
echo "Right-click the FTODE icon in your browser toolbar"
echo "and click \\"Remove from Chrome\\" / \\"Remove from Firefox\\"."
echo ""
"""


def build_windows_release_zip(version, dist_path, chrome_ext_path, firefox_ext_path, payload_b64):
    """Builds the clean Windows release bundle."""
    release_zip_name = f"FTODE-v{version}-Windows.zip"
    release_zip_path = os.path.join(dist_path, release_zip_name)
    base_folder = f"FTODE-v{version}-Windows"

    setup_bat = get_setup_bat_content(version, payload_b64)
    uninstall_bat = get_uninstall_bat_content(version)

    temp_zip = os.path.join(dist_path, f"temp_win_{os.getpid()}.zip")
    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(os.path.join(base_folder, 'FTODE Host Setup.bat'), setup_bat)
        zf.writestr(os.path.join(base_folder, 'FTODE Host Uninstall.bat'), uninstall_bat)
        zf.write(chrome_ext_path, os.path.join(base_folder, 'FTODE-Extension-Chrome.zip'))
        zf.write(firefox_ext_path, os.path.join(base_folder, 'FTODE-Extension-Firefox.zip'))
        zf.write(chrome_ext_path, os.path.join(base_folder, 'FTODE-Extension.zip'))
        zf.writestr(os.path.join(base_folder, 'Instructions.txt'), INSTRUCTIONS_WINDOWS_TEXT)

    for attempt in range(10):
        try:
            if os.path.isfile(release_zip_path):
                os.remove(release_zip_path)
            shutil.move(temp_zip, release_zip_path)
            break
        except Exception:
            import time
            time.sleep(0.5)

    size = os.path.getsize(release_zip_path)
    return release_zip_name, release_zip_path, size


def build_linux_release_zip(version, dist_path, chrome_ext_path, firefox_ext_path, payload_b64):
    """Builds the clean Linux release bundle."""
    release_zip_name = f"FTODE-v{version}-Linux.zip"
    release_zip_path = os.path.join(dist_path, release_zip_name)
    base_folder = f"FTODE-v{version}-Linux"

    setup_sh = get_setup_sh_content(version, payload_b64)
    uninstall_sh = get_uninstall_sh_content(version)

    temp_zip = os.path.join(dist_path, f"temp_linux_{os.getpid()}.zip")
    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        setup_info = zipfile.ZipInfo(os.path.join(base_folder, 'FTODE Host Setup.sh'))
        setup_info.external_attr = 0o755 << 16
        zf.writestr(setup_info, setup_sh)

        uninstall_info = zipfile.ZipInfo(os.path.join(base_folder, 'FTODE Host Uninstall.sh'))
        uninstall_info.external_attr = 0o755 << 16
        zf.writestr(uninstall_info, uninstall_sh)

        zf.write(chrome_ext_path, os.path.join(base_folder, 'FTODE-Extension-Chrome.zip'))
        zf.write(firefox_ext_path, os.path.join(base_folder, 'FTODE-Extension-Firefox.zip'))
        zf.write(chrome_ext_path, os.path.join(base_folder, 'FTODE-Extension.zip'))
        zf.writestr(os.path.join(base_folder, 'Instructions.txt'), INSTRUCTIONS_LINUX_TEXT)

    for attempt in range(10):
        try:
            if os.path.isfile(release_zip_path):
                os.remove(release_zip_path)
            shutil.move(temp_zip, release_zip_path)
            break
        except Exception:
            import time
            time.sleep(0.5)

    size = os.path.getsize(release_zip_path)
    return release_zip_name, release_zip_path, size


def main():
    parser = argparse.ArgumentParser(description="FTODE Build & Distribution Packager")
    args = parser.parse_args()

    version = get_version()

    print("=====================================================")
    print(f"   FTODE - Packaging Releases v{version}")
    print("=====================================================")
    print("")

    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Generate High-Res Windows .ico from FTODE Logo
    print("[*] Generating high-resolution FTODE Logo .ico (from logo512.png)...")
    generate_ftode_logo_ico(ICO_PATH)

    # 2. Build Extension archives for Chrome/Chromium and Firefox
    print("\n[*] Packaging Browser Extension archives...")
    (
        chrome_name, chrome_path, chrome_count, chrome_size,
        firefox_name, firefox_path, firefox_count, firefox_size,
        uni_name, uni_path, uni_size
    ) = build_extension_archives(version, DIST_DIR)
    print(f"    [v] Chrome / Opera / Edge: {chrome_name} ({chrome_count} files, {format_size(chrome_size)})")
    print(f"    [v] Mozilla Firefox:       {firefox_name} ({firefox_count} files, {format_size(firefox_size)})")

    # 3. Generate native host payload
    payload_b64 = get_native_host_base64_payload()

    # 4. Build Windows Release ZIP
    print("\n[*] Packaging Windows Release ZIP...")
    win_name, win_path, win_size = build_windows_release_zip(version, DIST_DIR, chrome_path, firefox_path, payload_b64)
    print(f"    [v] {win_name} ({format_size(win_size)})")

    # 5. Build Linux Release ZIP
    print("\n[*] Packaging Linux Release ZIP...")
    linux_name, linux_path, linux_size = build_linux_release_zip(version, DIST_DIR, chrome_path, firefox_path, payload_b64)
    print(f"    [v] {linux_name} ({format_size(linux_size)})")

    print("\n=====================================================")
    print(f" [SUCCESS] Standalone Release bundles created in: dist/")
    print("=====================================================")
    print(f" 1. Windows Bundle: {win_name} ({format_size(win_size)})")
    print(f"    |-- FTODE Host Setup.bat")
    print(f"    |-- FTODE Host Uninstall.bat")
    print(f"    |-- FTODE-Extension-Chrome.zip   (Chrome / Edge / Opera / Brave)")
    print(f"    |-- FTODE-Extension-Firefox.zip  (Firefox / Floorp / LibreWolf)")
    print(f"    |-- Instructions.txt")
    print(f"")
    print(f" 2. Linux Bundle:   {linux_name} ({format_size(linux_size)})")
    print(f"    |-- FTODE Host Setup.sh")
    print(f"    |-- FTODE Host Uninstall.sh")
    print(f"    |-- FTODE-Extension-Chrome.zip   (Chrome / Edge / Opera / Brave)")
    print(f"    |-- FTODE-Extension-Firefox.zip  (Firefox / Floorp / LibreWolf)")
    print(f"    |-- Instructions.txt")
    print(f"")
    print(f" 3. Standalone Extensions:")
    print(f"    |-- {chrome_name} ({format_size(chrome_size)})")
    print(f"    |-- {firefox_name} ({format_size(firefox_size)})")
    print("=====================================================\n")


if __name__ == '__main__':
    main()
