#!/usr/bin/env python3
"""
Finally that online downloader extension (FTODE) - Build & Release Packaging Tool
Creates a clean, branded release package containing exactly 4 items:
1. FTODE Setup.exe (1-Click Installer with embedded FTODE Logo icon - installs Native Host to %LOCALAPPDATA%\\FTODE)
2. FTODE Uninstall.exe (1-Click Uninstaller with embedded FTODE Logo icon - cleans registry & removes host files)
3. FTODE-Extension.zip (Universal single-file extension package for Chrome/Edge/Opera/Firefox)
4. Instructions.txt (Clear 2-step setup & uninstall instructions)
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
1. Double-click "FTODE Host Setup.exe" in this folder.
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
   - Double-click "FTODE Host Uninstall.exe" in this folder.
   - It will automatically clean all registry keys and remove backend files.
====================================================================
"""


def get_version():
    manifest_path = os.path.join(EXTENSION_DIR, 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', '1.0.0')
    except Exception:
        return '1.0.0'


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


def find_csc():
    """Finds the built-in Windows C# compiler."""
    candidates = [
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def compile_csharp_launcher(csc_path, cs_code, out_exe, ico_path=None):
    """Compiles a small C# wrapper executable with an embedded icon and assembly metadata."""
    temp_cs = out_exe + ".cs"
    try:
        with open(temp_cs, 'w', encoding='utf-8') as f:
            f.write(cs_code)

        cmd = [csc_path, "/nologo", "/target:exe", f"/out:{out_exe}"]
        if ico_path and os.path.isfile(ico_path):
            cmd.append(f"/win32icon:{ico_path}")
        cmd.append(temp_cs)

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] Compilation error: {res.stderr}")
            return False
        return True
    finally:
        if os.path.isfile(temp_cs):
            try:
                os.remove(temp_cs)
            except Exception:
                pass


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


def get_setup_cs_code(payload_b64, version):
    return f"""using System;
using System.IO;
using System.Diagnostics;
using System.Reflection;
using Microsoft.Win32;

[assembly: AssemblyTitle("FTODE Host Setup")]
[assembly: AssemblyDescription("Finally that online downloader extension (FTODE) - 1-Click Host Setup")]
[assembly: AssemblyCompany("MaxAkt")]
[assembly: AssemblyProduct("FTODE")]
[assembly: AssemblyCopyright("Copyright (C) 2026 MaxAkt")]
[assembly: AssemblyVersion("{version}.0")]
[assembly: AssemblyFileVersion("{version}.0")]

namespace FTODE {{
    class Program {{
        static int Main(string[] args) {{
            Console.Title = "FTODE - 1-Click Host Setup";
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("===================================================");
            Console.WriteLine("  FTODE - 1-Click Host Setup");
            Console.WriteLine("  Finally that online downloader extension");
            Console.WriteLine("===================================================\\n");
            Console.ResetColor();

            try {{
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string targetDir = Path.Combine(localAppData, "FTODE");
                if (!Directory.Exists(targetDir)) {{
                    Directory.CreateDirectory(targetDir);
                }}

                Console.WriteLine("[*] Installing FTODE Host backend to: " + targetDir);

                string base64Payload = "{payload_b64}";
                byte[] zipBytes = Convert.FromBase64String(base64Payload);
                string tempZip = Path.Combine(Path.GetTempPath(), "ftode_setup_host.zip");
                File.WriteAllBytes(tempZip, zipBytes);

                ProcessStartInfo extractPsi = new ProcessStartInfo {{
                    FileName = "powershell.exe",
                    Arguments = "-NoProfile -ExecutionPolicy Bypass -Command \\"Expand-Archive -Path '" + tempZip + "' -DestinationPath '" + targetDir + "' -Force; Remove-Item '" + tempZip + "' -Force;\\"",
                    UseShellExecute = false,
                    CreateNoWindow = true
                }};
                Process pExtract = Process.Start(extractPsi);
                pExtract.WaitForExit();

                string installBat = Path.Combine(targetDir, "install_host.bat");
                if (File.Exists(installBat)) {{
                    ProcessStartInfo psi = new ProcessStartInfo {{
                        FileName = "cmd.exe",
                        Arguments = "/c \\"" + installBat + "\\"",
                        WorkingDirectory = targetDir,
                        UseShellExecute = false
                    }};
                    Process p = Process.Start(psi);
                    p.WaitForExit();
                    return p.ExitCode;
                }} else {{
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("[v] Setup Complete! Extension is ready to use.\\n");
                    Console.ResetColor();
                }}
            }} catch (Exception ex) {{
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[x] Setup Error: " + ex.Message);
                Console.ResetColor();
                Console.WriteLine("\\nPress any key to exit...");
                Console.ReadKey();
                return 1;
            }}
            return 0;
        }}
    }}
}}
"""


def get_uninstall_cs_code(version):
    return f"""using System;
using System.IO;
using System.Diagnostics;
using System.Reflection;
using Microsoft.Win32;

[assembly: AssemblyTitle("FTODE Host Uninstall")]
[assembly: AssemblyDescription("Finally that online downloader extension (FTODE) - 1-Click Host Uninstaller")]
[assembly: AssemblyCompany("MaxAkt")]
[assembly: AssemblyProduct("FTODE")]
[assembly: AssemblyCopyright("Copyright (C) 2026 MaxAkt")]
[assembly: AssemblyVersion("{version}.0")]
[assembly: AssemblyFileVersion("{version}.0")]

namespace FTODE {{
    class Program {{
        static int Main(string[] args) {{
            Console.Title = "FTODE - Host Uninstaller";
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("===================================================");
            Console.WriteLine("  FTODE - 1-Click Host Uninstaller");
            Console.WriteLine("  Finally that online downloader extension");
            Console.WriteLine("===================================================\\n");
            Console.ResetColor();

            try {{
                Console.WriteLine("[*] Stopping any active FTODE tasks...");
                try {{
                    foreach (var proc in Process.GetProcessesByName("yt-dlp")) {{
                        try {{ proc.Kill(); }} catch {{ }}
                    }}
                    foreach (var proc in Process.GetProcessesByName("ffmpeg")) {{
                        try {{ proc.Kill(); }} catch {{ }}
                    }}
                }} catch {{ }}

                Console.WriteLine("[*] Removing FTODE Native Messaging Registry keys...");
                string[] regKeys = new string[] {{
                    @"Software\\Google\\Chrome\\NativeMessagingHosts\\com.ftode.host",
                    @"Software\\Microsoft\\Edge\\NativeMessagingHosts\\com.ftode.host",
                    @"Software\\Chromium\\NativeMessagingHosts\\com.ftode.host",
                    @"Software\\Mozilla\\NativeMessagingHosts\\com.ftode.host"
                }};

                foreach (string subKey in regKeys) {{
                    try {{
                        Registry.CurrentUser.DeleteSubKeyTree(subKey, false);
                        Console.WriteLine("    [v] Removed: HKCU\\\\" + subKey);
                    }} catch {{ }}
                }}

                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string targetDir = Path.Combine(localAppData, "FTODE");

                if (Directory.Exists(targetDir)) {{
                    Console.WriteLine("[*] Removing installed backend files from: " + targetDir);
                    try {{
                        Directory.Delete(targetDir, true);
                        Console.WriteLine("    [v] Deleted backend directory successfully.");
                    }} catch (Exception ex) {{
                        Console.WriteLine("    [!] Notice: " + ex.Message);
                    }}
                }}

                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("\\n===================================================");
                Console.WriteLine("   FTODE Native Host Uninstalled Successfully!");
                Console.WriteLine("===================================================\\n");
                Console.ResetColor();

                Console.WriteLine("Final Step:");
                Console.WriteLine("1. Right-click the FTODE icon in your browser toolbar.");
                Console.WriteLine("2. Click 'Remove from Chrome' / 'Remove from Edge' / 'Remove Extension'.\\n");
            }} catch (Exception ex) {{
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[x] Error during uninstallation: " + ex.Message);
                Console.ResetColor();
            }}

            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
            return 0;
        }}
    }}
}}
"""


def build_clean_release_zip(version, dist_path, ext_zip_path, csc_path, ico_path):
    """
    Builds the clean 4-item release ZIP:
    1. FTODE Setup.exe (With official FTODE Logo Icon)
    2. FTODE Uninstall.exe (With official FTODE Logo Icon)
    3. FTODE-Extension.zip (Universal extension package)
    4. Instructions.txt (Clear 2-step setup & uninstall guide)
    """
    release_zip_name = f"FTODE-v{version}-Release.zip"
    release_zip_path = os.path.join(dist_path, release_zip_name)
    base_folder = f"FTODE-v{version}"

    # Compile .exe launchers with FTODE Logo icon & names
    setup_exe_name = "FTODE Host Setup.exe"
    uninstall_exe_name = "FTODE Host Uninstall.exe"
    setup_exe_path = os.path.join(dist_path, setup_exe_name)
    uninstall_exe_path = os.path.join(dist_path, uninstall_exe_name)

    payload_b64 = get_native_host_base64_payload()
    setup_cs = get_setup_cs_code(payload_b64, version)
    uninstall_cs = get_uninstall_cs_code(version)

    ok1 = compile_csharp_launcher(csc_path, setup_cs, setup_exe_path, ico_path)
    ok2 = compile_csharp_launcher(csc_path, uninstall_cs, uninstall_exe_path, ico_path)
    # Write zip to temp file first to prevent PermissionError if Explorer preview is active
    temp_zip = os.path.join(dist_path, f"temp_release_{os.getpid()}.zip")
    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. FTODE Setup.exe (With FTODE Logo Icon)
        if os.path.isfile(setup_exe_path):
            zf.write(setup_exe_path, os.path.join(base_folder, setup_exe_name))

        # 2. FTODE Uninstall.exe (With FTODE Logo Icon)
        if os.path.isfile(uninstall_exe_path):
            zf.write(uninstall_exe_path, os.path.join(base_folder, uninstall_exe_name))

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
        # If still locked, fallback to alternative name
        fallback_name = f"FTODE-v{version}-Release-New.zip"
        fallback_path = os.path.join(dist_path, fallback_name)
        shutil.move(temp_zip, fallback_path)
        release_zip_name = fallback_name
        release_zip_path = fallback_path

    size = os.path.getsize(release_zip_path)
    return release_zip_name, release_zip_path, size, setup_exe_name, uninstall_exe_name


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

    # 3. Find C# compiler for icon-embedded executables
    csc_path = find_csc()
    if not csc_path:
        print("[x] Error: Windows C# compiler (csc.exe) not found!")
        sys.exit(1)

    print(f"\n[*] Compiling 'FTODE Setup.exe' & 'FTODE Uninstall.exe' with FTODE Logo Icon...")

    # 4. Build Release ZIP
    rel_name, rel_path, rel_size, s_name, u_name = build_clean_release_zip(version, DIST_DIR, ext_path, csc_path, ICO_PATH)
    print(f"    [v] {rel_name} ({format_size(rel_size)})")

    print("\n=====================================================")
    print(f" [SUCCESS] Release archive created in: dist/")
    print("=====================================================")
    print(f" Release ZIP: {rel_name} ({format_size(rel_size)})")
    print(f"")
    print(f" Files inside {rel_name}:")
    print(f" |-- {s_name:<20} (1-Click Installer WITH FTODE Logo Icon)")
    print(f" |-- {u_name:<20} (1-Click Uninstaller WITH FTODE Logo Icon)")
    print(f" |-- FTODE-Extension.zip  (Universal extension package for all browsers)")
    print(f" |-- Instructions.txt     (Simple 2-step setup & uninstall instructions)")
    print("=====================================================\n")


if __name__ == '__main__':
    main()
