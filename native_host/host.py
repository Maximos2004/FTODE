#!/usr/bin/env python3
"""
Finally that online downloader extension (FTODE) - Python Native Messaging Host Backend
Interfaces browser extension with yt-dlp and FFmpeg using Native Messaging.
Includes automatic self-bootstrapping and fast update checks.
"""

import sys
import os
import json
import struct
import subprocess
import shutil
import re
import threading
import urllib.request
import zipfile
import time
import tempfile

if sys.platform == 'win32':
    import winreg
    import msvcrt
    try:
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except Exception:
        pass

# Official direct release URLs for Windows & Linux
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YTDLP_LINUX_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
FFMPEG_ZIP_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_BACKUP_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_LINUX_TAR_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"


# Global active process & write locks
active_jobs = {}  # jobId -> {'process': proc, 'context': ctx}
last_download_context = None
active_lock = threading.Lock()
stdout_lock = threading.Lock()
bootstrap_lock = threading.Lock()


def sanitize_log_payload(obj):
    """
    Sanitize sensitive authentication cookies, passwords, and tokens before logging.
    """
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if k.lower() in ('cookiestext', 'cookies', 'cookie', 'password', 'token', 'auth'):
                clean[k] = '[REDACTED_AUTHENTICATION_COOKIES]' if v else None
            else:
                clean[k] = sanitize_log_payload(v)
        return clean
    elif isinstance(obj, list):
        return [sanitize_log_payload(item) for item in obj]
    return obj


def log_debug(msg):
    try:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_host.log')
        # Cap log size to 5MB to prevent unbounded disk growth
        if os.path.isfile(log_file) and os.path.getsize(log_file) > 5 * 1024 * 1024:
            old_log = log_file + '.old'
            try:
                if os.path.isfile(old_log):
                    os.remove(old_log)
                os.rename(log_file, old_log)
            except Exception:
                pass
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def scan_dir_files(root_dir):
    """
    Recursively scans and returns a set of absolute file paths inside root_dir.
    """
    if not root_dir or not os.path.isdir(root_dir):
        return set()
    res = set()
    for root, _, filenames in os.walk(root_dir):
        for f in filenames:
            res.add(os.path.abspath(os.path.join(root, f)))
    return res


def scan_dir_folders(root_dir):
    """
    Recursively scans and returns a set of absolute subdirectory paths inside root_dir.
    """
    if not root_dir or not os.path.isdir(root_dir):
        return set()
    res = set()
    for root, dirnames, _ in os.walk(root_dir):
        for d in dirnames:
            res.add(os.path.abspath(os.path.join(root, d)))
    return res


def safe_delete_file(file_path, retries=15, delay=0.2):
    """
    Safely deletes a file with retries in case Windows file locks are temporarily held post-process termination.
    """
    if not file_path:
        return False
    for i in range(retries):
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                try:
                    os.chmod(file_path, 0o777)
                except Exception:
                    pass
                os.remove(file_path)
                log_debug(f"[CLEANUP] Deleted residue file: {file_path}")
                return True
            else:
                return True
        except Exception as e:
            log_debug(f"[CLEANUP] Retry {i+1}/{retries} deleting {file_path}: {e}")
            time.sleep(delay)
    return False


def cleanup_download_residue(ctx):
    """
    Cleans up any partial / intermediate files, residue (.part, .ytdl, temp streams, etc.),
    incomplete in-progress tracks, and empty subdirectories left behind by a cancelled or failed download.
    STRICT SAFETY GUARANTEE: Preserves all previously completed tracks and existing user files.
    """
    if not ctx:
        return
    output_dir = ctx.get('output_dir')
    if not output_dir or not os.path.isdir(output_dir):
        return

    files_before = ctx.get('files_before')
    dirs_before = ctx.get('dirs_before', set())
    is_playlist = ctx.get('is_playlist', False)
    current_idx = ctx.get('current_track_index')
    completed_indices = ctx.get('completed_track_indices', set())
    target_format = ctx.get('target_format', '').lower().lstrip('.')
    target_ext = '.' + target_format if target_format else ''
    if target_ext == '.vorbis':
        target_ext = '.ogg'

    # Snapshot current files in output directory recursively
    files_after = scan_dir_files(output_dir)
    new_files = files_after - files_before if files_before is not None else set()

    # Suffixes strictly indicating unfinished/temporary download parts
    residue_suffixes = (
        '.part', '.ytdl', '.temp', '.tmp', '.aria2', '.frag'
    )

    to_delete = set()

    for f_path in files_after:
        f_name = os.path.basename(f_path).lower()

        # 1. Any file ending with temporary residue suffixes (.part, .ytdl, .tmp, etc.)
        if f_name.endswith(residue_suffixes):
            to_delete.add(f_path)
            continue

        # 2. Fragmented stream chunks (.part-Frag123)
        if '.part-frag' in f_name or '.part-' in f_name:
            to_delete.add(f_path)
            continue

        # 3. Only inspect newly created files in this session
        if f_path in new_files:
            # For audio downloads: clean up intermediate video/audio container streams (e.g. .m4a, .webm when target is .mp3)
            if target_ext and not f_name.endswith(target_ext):
                to_delete.add(f_path)
                continue

            if not is_playlist:
                # Single download was cancelled mid-way -> delete the partial/incomplete file
                if not ctx.get('is_completed', False):
                    to_delete.add(f_path)
            else:
                # Playlist download was cancelled mid-way:
                # Check if this file belongs to the incomplete in-progress track
                if current_idx is not None:
                    idx_prefix1 = f"{current_idx:02d} - "
                    idx_prefix2 = f"{current_idx} - "
                    if (f_name.startswith(idx_prefix1.lower()) or f_name.startswith(idx_prefix2.lower())) and current_idx not in completed_indices:
                        to_delete.add(f_path)

    # Safely delete only confirmed residue / incomplete files
    for f_path in to_delete:
        safe_delete_file(f_path)

    # Clean up empty subdirectories created during this session (strictly if empty)
    try:
        dirs_after = scan_dir_folders(output_dir)
        new_dirs = sorted(list(dirs_after - dirs_before), key=lambda d: len(d), reverse=True)
        for d in new_dirs:
            try:
                if os.path.isdir(d) and len(os.listdir(d)) == 0:
                    os.rmdir(d)
                    log_debug(f"[CLEANUP] Removed empty folder: {d}")
            except Exception as e:
                log_debug(f"[CLEANUP] Could not remove folder {d}: {e}")
    except Exception:
        pass

    # Clean up session cookies temp file if exists
    cookies_file = ctx.get('cookies_file')
    if cookies_file and os.path.exists(cookies_file):
        try:
            os.remove(cookies_file)
        except Exception:
            pass


def cleanup_all_processes():
    """
    Terminates any active child subprocess tree when host exits.
    Prevents orphaned yt-dlp or ffmpeg processes and deletes unfinished download residue.
    """
    global active_jobs, last_download_context
    log_debug("[EXIT] cleanup_all_processes invoked")
    with active_lock:
        jobs_to_clean = list(active_jobs.values())
        if not jobs_to_clean and last_download_context:
            jobs_to_clean = [{'process': None, 'context': last_download_context}]
        active_jobs.clear()

    for item in jobs_to_clean:
        ctx = item.get('context')
        proc = item.get('process')
        if ctx is not None:
            ctx['is_cancelled'] = True

        if proc is not None:
            pid = proc.pid
            log_debug(f"[EXIT] Terminating active process PID {pid}")
            try:
                if sys.platform == 'win32':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception as e:
                log_debug(f"[EXIT] Process kill error: {e}")
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=2.0)
            except Exception:
                pass

        if ctx is not None and not ctx.get('is_completed', False):
            target_dir = ctx.get('output_dir')
            if target_dir and os.path.isdir(target_dir):
                log_debug(f"[EXIT] Cleaning residue in output_dir: {target_dir}")
                try:
                    cleanup_download_residue(ctx)
                except Exception as e:
                    log_debug(f"[EXIT] cleanup_download_residue error: {e}")


import atexit
import signal

atexit.register(cleanup_all_processes)
try:
    signal.signal(signal.SIGTERM, lambda *_: cleanup_all_processes())
    signal.signal(signal.SIGINT, lambda *_: cleanup_all_processes())
except Exception:
    pass



def get_bin_dir():
    """
    Get or create local bin directory for bundled executables (native_host/bin/).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(script_dir, 'bin')
    os.makedirs(bin_dir, exist_ok=True)
    return bin_dir


def send_message(message_dict):
    """
    Send JSON message to Chrome Native Messaging client with 4-byte length prefix.
    Thread-safe binary stdout write.
    """
    with stdout_lock:
        try:
            encoded_data = json.dumps(message_dict).encode('utf-8')
            length_prefix = struct.pack('=I', len(encoded_data))
            sys.stdout.buffer.write(length_prefix)
            sys.stdout.buffer.write(encoded_data)
            sys.stdout.buffer.flush()
        except Exception as e:
            sys.stderr.write(f"[FTODE Host Error] send_message failed: {e}\n")


def read_message():
    """
    Read incoming JSON message from Chrome Native Messaging client with 4-byte length prefix.
    """
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) < 4:
            return None
        message_length = struct.unpack('=I', raw_length)[0]
        message_bytes = sys.stdin.buffer.read(message_length)
        if not message_bytes or len(message_bytes) < message_length:
            return None
        return json.loads(message_bytes.decode('utf-8'))
    except Exception as e:
        sys.stderr.write(f"[FTODE Host Error] read_message failed: {e}\n")
        return None


def read_unbuffered_lines(proc):
    """
    Generator reading unbuffered output chunks from subprocess,
    splitting on both carriage returns (\\r) and newlines (\\n).
    """
    buffer = ''
    while True:
        try:
            chunk = proc.stdout.read(128)
        except Exception:
            break
        if not chunk:
            if buffer.strip():
                yield buffer.strip()
            break
        buffer += chunk
        while '\n' in buffer or '\r' in buffer:
            n_idx = buffer.find('\n')
            r_idx = buffer.find('\r')
            if n_idx != -1 and (r_idx == -1 or n_idx < r_idx):
                line, buffer = buffer[:n_idx], buffer[n_idx + 1:]
            else:
                line, buffer = buffer[:r_idx], buffer[r_idx + 1:]
            line = line.strip()
            if line:
                yield line


def find_executable(name, custom_path=None):
    """
    Locate yt-dlp or ffmpeg executable.
    Priority:
      1. Custom path in settings
      2. Local prepackaged native_host/bin/
      3. System PATH
      4. Common install folders (Windows & Linux)
    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    is_win = sys.platform == 'win32'
    exe_name = f"{name}.exe" if is_win and not name.endswith('.exe') else name

    # 1. Check local native_host/bin/
    local_bin = os.path.join(get_bin_dir(), exe_name)
    if os.path.isfile(local_bin):
        return local_bin

    # 2. Check system PATH
    found = shutil.which(name)
    if found:
        return found

    # 3. Check Windows common package locations
    if is_win:
        user_profile = os.environ.get('USERPROFILE', '')
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')

        common_locations = [
            os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Links', exe_name),
            os.path.join(user_profile, 'AppData', 'Roaming', 'Python', 'Python314', 'Scripts', exe_name),
            os.path.join(user_profile, 'AppData', 'Roaming', 'Python', 'Python312', 'Scripts', exe_name),
            os.path.join(user_profile, 'AppData', 'Roaming', 'Python', 'Python311', 'Scripts', exe_name),
            os.path.join(user_profile, 'AppData', 'Roaming', 'Python', 'Python310', 'Scripts', exe_name),
            os.path.join(user_profile, 'AppData', 'Local', 'Programs', 'Python', 'Python314', 'Scripts', exe_name),
            os.path.join(user_profile, 'scoop', 'shims', exe_name),
            os.path.join(local_app_data, 'Programs', 'yt-dlp', exe_name),
            os.path.join(local_app_data, 'Programs', 'ffmpeg', 'bin', exe_name),
            os.path.join(program_files, 'yt-dlp', exe_name),
            os.path.join(program_files, 'ffmpeg', 'bin', exe_name),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), exe_name)
        ]

        # Scan WinGet Packages directory
        winget_pkgs = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages')
        if os.path.isdir(winget_pkgs):
            for root, _, files in os.walk(winget_pkgs):
                if exe_name.lower() in (f.lower() for f in files):
                    return os.path.join(root, exe_name)

        for loc in common_locations:
            if os.path.isfile(loc):
                return loc
    else:
        # Linux / Unix common paths
        home = os.path.expanduser('~')
        linux_locations = [
            os.path.join(home, '.local', 'bin', exe_name),
            f'/usr/local/bin/{exe_name}',
            f'/usr/bin/{exe_name}',
            f'/bin/{exe_name}',
            f'/snap/bin/{exe_name}',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), exe_name)
        ]
        for loc in linux_locations:
            if os.path.isfile(loc) and os.access(loc, os.X_OK):
                return loc

    return None


def get_version(executable_path):
    """
    Get version string from executable.
    """
    if not executable_path or not os.path.isfile(executable_path):
        return None
    try:
        is_ffmpeg = 'ffmpeg' in os.path.basename(executable_path).lower()
        flag = '-version' if is_ffmpeg else '--version'
        res = subprocess.run([executable_path, flag], capture_output=True, text=True, timeout=3, stdin=subprocess.DEVNULL)
        if res.returncode == 0:
            first_line = res.stdout.strip().split('\n')[0]
            if is_ffmpeg:
                import re
                m = re.search(r'ffmpeg version\s+([^\s]+)', first_line, re.IGNORECASE)
                if m:
                    return m.group(1)
            return first_line
    except Exception:
        pass
    return "Available"


def download_file_with_progress(url, dest_path, label="Downloading", callback=None):
    """
    Download a file from URL to dest_path with progress callback.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'}
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded = 0
        chunk_size = 64 * 1024  # 64 KB chunks

        with open(dest_path, 'wb') as out_file:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)

                if callback:
                    percent = (downloaded / total_size * 100) if total_size > 0 else 0
                    callback(percent, downloaded, total_size, label)


def bootstrap_dependencies(force=False, callback=None):
    """
    Download and install yt-dlp and FFmpeg to native_host/bin/
    only if missing (or if force=True). Supports Windows & Linux.
    """
    with bootstrap_lock:
        is_win = sys.platform == 'win32'
        bin_dir = get_bin_dir()
        ytdlp_exe = 'yt-dlp.exe' if is_win else 'yt-dlp'
        ffmpeg_exe = 'ffmpeg.exe' if is_win else 'ffmpeg'
        ytdlp_dest = os.path.join(bin_dir, ytdlp_exe)
        ffmpeg_dest = os.path.join(bin_dir, ffmpeg_exe)

        # 1. Check / Download yt-dlp (Only if missing or force)
        needs_ytdlp = force or not find_executable('yt-dlp')
        if needs_ytdlp:
            if callback:
                callback(0, 0, 0, f"[INFO] Downloading standalone {ytdlp_exe} from official release...")

            temp_ytdlp = ytdlp_dest + ".tmp"
            try:
                def on_ytdlp_prog(pct, dl, tot, lbl):
                    mb_dl = dl / (1024 * 1024)
                    mb_tot = tot / (1024 * 1024)
                    if callback:
                        callback(pct, dl, tot, f"[INFO] Downloading {ytdlp_exe}: {pct:.1f}% ({mb_dl:.1f}/{mb_tot:.1f} MB)")

                url = YTDLP_DOWNLOAD_URL if is_win else YTDLP_LINUX_URL
                download_file_with_progress(url, temp_ytdlp, "yt-dlp", on_ytdlp_prog)
                if os.path.isfile(ytdlp_dest):
                    try: os.remove(ytdlp_dest)
                    except Exception: pass
                os.replace(temp_ytdlp, ytdlp_dest)
                if not is_win:
                    try:
                        os.chmod(ytdlp_dest, 0o755)
                    except Exception:
                        pass

                if callback:
                    callback(100, 0, 0, f"[SUCCESS] {ytdlp_exe} installed into native_host/bin/")
            except Exception as e:
                if os.path.isfile(temp_ytdlp):
                    try: os.remove(temp_ytdlp)
                    except Exception: pass
                raise RuntimeError(f"Failed to download yt-dlp: {e}")

        # 2. Check / Download FFmpeg (Only if missing or force)
        needs_ffmpeg = force or not find_executable('ffmpeg')
        if needs_ffmpeg:
            if is_win:
                if callback:
                    callback(0, 0, 0, "[INFO] Downloading FFmpeg build for Windows...")

                zip_temp = os.path.join(bin_dir, 'ffmpeg_temp.zip')
                try:
                    def on_ffmpeg_prog(pct, dl, tot, lbl):
                        mb_dl = dl / (1024 * 1024)
                        mb_tot = tot / (1024 * 1024)
                        if callback:
                            callback(pct, dl, tot, f"[INFO] Downloading FFmpeg build: {pct:.1f}% ({mb_dl:.1f}/{mb_tot:.1f} MB)")

                    # Try primary then backup URL
                    try:
                        download_file_with_progress(FFMPEG_ZIP_URL, zip_temp, "FFmpeg", on_ffmpeg_prog)
                    except Exception:
                        download_file_with_progress(FFMPEG_BACKUP_ZIP_URL, zip_temp, "FFmpeg", on_ffmpeg_prog)

                    if callback:
                        callback(95, 0, 0, "[INFO] Extracting ffmpeg.exe & ffprobe.exe...")

                    # Extract only ffmpeg.exe and ffprobe.exe
                    with zipfile.ZipFile(zip_temp, 'r') as zip_ref:
                        for member in zip_ref.namelist():
                            basename = os.path.basename(member).lower()
                            if basename in ('ffmpeg.exe', 'ffprobe.exe'):
                                target_path = os.path.join(bin_dir, basename)
                                with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)

                    try:
                        os.remove(zip_temp)
                    except Exception:
                        pass

                    if callback:
                        callback(100, 0, 0, "[SUCCESS] FFmpeg installed into native_host/bin/")
                except Exception as e:
                    if os.path.isfile(zip_temp):
                        try: os.remove(zip_temp)
                        except Exception: pass
                    raise RuntimeError(f"Failed to download FFmpeg: {e}")
            else:
                # Linux FFmpeg: Try downloading static tar.xz or warn user
                if callback:
                    callback(0, 0, 0, "[INFO] Downloading static FFmpeg build for Linux...")

                tar_temp = os.path.join(bin_dir, 'ffmpeg_temp.tar.xz')
                try:
                    def on_ffmpeg_prog_linux(pct, dl, tot, lbl):
                        mb_dl = dl / (1024 * 1024)
                        mb_tot = tot / (1024 * 1024)
                        if callback:
                            callback(pct, dl, tot, f"[INFO] Downloading FFmpeg build: {pct:.1f}% ({mb_dl:.1f}/{mb_tot:.1f} MB)")

                    download_file_with_progress(FFMPEG_LINUX_TAR_URL, tar_temp, "FFmpeg", on_ffmpeg_prog_linux)
                    if callback:
                        callback(95, 0, 0, "[INFO] Extracting ffmpeg & ffprobe...")

                    import tarfile
                    with tarfile.open(tar_temp, 'r:*') as tar:
                        for member in tar.getmembers():
                            basename = os.path.basename(member.name).lower()
                            if basename in ('ffmpeg', 'ffprobe'):
                                f_obj = tar.extractfile(member)
                                if f_obj:
                                    target_path = os.path.join(bin_dir, basename)
                                    with open(target_path, 'wb') as out_f:
                                        shutil.copyfileobj(f_obj, out_f)
                                    os.chmod(target_path, 0o755)

                    try:
                        os.remove(tar_temp)
                    except Exception:
                        pass

                    if callback:
                        callback(100, 0, 0, "[SUCCESS] FFmpeg installed into native_host/bin/")
                except Exception as e:
                    if os.path.isfile(tar_temp):
                        try: os.remove(tar_temp)
                        except Exception: pass
                    log_debug(f"[BOOTSTRAP] FFmpeg Linux auto-download error: {e}")
                    if callback:
                        callback(100, 0, 0, "[!] Note: FFmpeg can also be installed with: sudo apt install ffmpeg (or pacman -S ffmpeg)")

        return find_executable('yt-dlp'), find_executable('ffmpeg')


def handle_ping(payload):
    """
    Respond to extension PING request with system diagnostic details.
    """
    custom_ytdlp = payload.get('customYtdlpPath')
    custom_ffmpeg = payload.get('customFfmpegPath')

    ytdlp_bin = find_executable('yt-dlp', custom_ytdlp)
    ffmpeg_bin = find_executable('ffmpeg', custom_ffmpeg)

    send_message({
        'status': 'pong',
        'version': '1.0.2',
        'python_version': sys.version.split()[0],
        'ytdlp_available': ytdlp_bin is not None,
        'ytdlp_path': ytdlp_bin,
        'ytdlp_version': get_version(ytdlp_bin) if ytdlp_bin else None,
        'ffmpeg_available': ffmpeg_bin is not None,
        'ffmpeg_path': ffmpeg_bin,
        'ffmpeg_version': get_version(ffmpeg_bin) if ffmpeg_bin else None,
        'bin_dir': get_bin_dir(),
        'default_downloads': get_system_downloads_dir()
    })


def handle_bootstrap(payload):
    """
    Install missing dependencies (force=False).
    """
    force = payload.get('force', False)

    def on_prog(pct, dl, tot, msg):
        send_message({
            'status': 'bootstrap_progress',
            'percent': pct,
            'line': msg
        })

    try:
        ytdlp_bin, ffmpeg_bin = bootstrap_dependencies(force=force, callback=on_prog)
        send_message({
            'status': 'bootstrap_complete',
            'ytdlp_path': ytdlp_bin,
            'ytdlp_version': get_version(ytdlp_bin),
            'ffmpeg_path': ffmpeg_bin,
            'ffmpeg_version': get_version(ffmpeg_bin),
            'message': 'yt-dlp and FFmpeg are installed and operational!'
        })
    except Exception as e:
        send_message({
            'status': 'error',
            'message': f"Installation failed: {str(e)}"
        })


def handle_check_updates(payload):
    """
    Fast update check: runs yt-dlp --update and verifies binaries.
    """
    def on_prog(pct, dl, tot, msg):
        send_message({
            'status': 'bootstrap_progress',
            'percent': pct,
            'line': msg
        })

    try:
        ytdlp_bin = find_executable('yt-dlp')
        ffmpeg_bin = find_executable('ffmpeg')

        # If either is missing, install them first
        if not ytdlp_bin or not ffmpeg_bin:
            ytdlp_bin, ffmpeg_bin = bootstrap_dependencies(force=False, callback=on_prog)

        # Run yt-dlp in-place update check
        on_prog(50, 0, 0, "[INFO] Checking for yt-dlp updates from GitHub...")
        update_res = subprocess.run([ytdlp_bin, '--update'], capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL)
        update_line = update_res.stdout.strip().split('\n')[-1] if update_res.stdout.strip() else 'yt-dlp is up to date'

        on_prog(100, 0, 0, f"[INFO] {update_line}")

        send_message({
            'status': 'update_complete',
            'ytdlp_path': ytdlp_bin,
            'ytdlp_version': get_version(ytdlp_bin),
            'ffmpeg_path': ffmpeg_bin,
            'ffmpeg_version': get_version(ffmpeg_bin),
            'message': update_line
        })
    except Exception as e:
        send_message({
            'status': 'error',
            'message': f"Update check failed: {str(e)}"
        })


RICH_STREAMING_DOMAINS = (
    'youtube.com', 'youtu.be', 'vimeo.com', 'soundcloud.com', 'twitch.tv',
    'tiktok.com', 'twitter.com', 'x.com', 'reddit.com', 'dailymotion.com',
    'bilibili.com', 'instagram.com', 'facebook.com', 'fb.watch',
    'bandcamp.com', 'rumble.com', 'kick.com', 'odysee.com', 'mixcloud.com',
    'streamable.com', 'bitchute.com', 'threads.net'
)


def is_rich_streaming_domain(url):
    """
    Check if URL is on a known streaming platform where yt-dlp has specialized extractors.
    """
    if not url:
        return False
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith('.' + d) for d in RICH_STREAMING_DOMAINS)
    except Exception:
        return False


def is_homepage_or_feed(url):
    """
    Check if URL is a homepage, search page, or feed with no single media target.
    """
    if not url:
        return True
    try:
        from urllib.parse import urlparse
        u = urlparse(url)
        host = u.netloc.lower()
        path = u.path.lower().rstrip('/') or '/'
        search = u.query.lower()

        if path in ('/', '', '/home', '/index.html', '/index.php'):
            return True
        if 'youtube.com' in host:
            if path in ('/watch', '/embed', '/clip') or path.startswith(('/shorts/', '/live/', '/embed/', '/clip/')):
                return False
            if path == '/playlist' and 'list=' in search:
                return False
            return True
        if 'youtu.be' in host:
            if path in ('/', ''):
                return True
            return False
        if 'twitch.tv' in host and (path in ('/', '/directory') or path.startswith(('/directory/', '/p/'))):
            return True
        if 'soundcloud.com' in host and (path in ('/', '/discover', '/stream', '/feed', '/charts', '/search') or path.startswith('/you/')):
            return True
        if 'vimeo.com' in host and path in ('/', '/home', '/watch', '/explore', '/channels', '/categories'):
            return True
        if 'tiktok.com' in host and path in ('/', '/foryou', '/following', '/explore', '/live'):
            return True
        if ('twitter.com' in host or 'x.com' in host) and path in ('/', '/home', '/explore', '/notifications', '/messages', '/search'):
            return True
        if 'reddit.com' in host and (path in ('/', '/r/all', '/r/popular', '/hot', '/new', '/top') or (path.startswith('/r/') and '/comments/' not in path) or path.startswith('/user/')):
            return True
        if ('facebook.com' in host or 'fb.watch' in host) and (path in ('/', '/home.php', '/feed') or (path == '/watch' and 'v=' not in search)):
            return True
        if 'instagram.com' in host and (path in ('/', '/explore', '/explore/', '/reels', '/reels/', '/direct/')):
            return True
        if 'bandcamp.com' in host and (path == '/' or path.startswith('/tag/') or path == '/discover'):
            return True
        if 'dailymotion.com' in host and path in ('/', '/feed', '/trending'):
            return True
        if 'bilibili.com' in host and (path == '/' or path.startswith('/v/')):
            return True
        if 'kick.com' in host and (path == '/' or path.startswith('/category/') or path == '/browse'):
            return True
        if 'rumble.com' in host and (path in ('/', '/videos', '/browse')):
            return True
        return False
    except Exception:
        return False


def get_system_downloads_dir():
    """
    Determines the user's actual Downloads folder location across all platforms.
    On Windows, handles redirected/custom Downloads locations (e.g. D:\\Downloads)
    using SHGetKnownFolderPath (FOLDERID_Downloads) and Windows Registry.
    """
    if sys.platform == 'win32':
        # 1. Try Windows Shell API (SHGetKnownFolderPath with FOLDERID_Downloads)
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)
                ]

            FOLDERID_Downloads = GUID(
                0x374DE290, 0x123F, 0x4565,
                (wintypes.BYTE * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B)
            )
            SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
            ]
            SHGetKnownFolderPath.restype = ctypes.c_long

            path_ptr = ctypes.c_wchar_p()
            res = SHGetKnownFolderPath(ctypes.byref(FOLDERID_Downloads), 0, None, ctypes.byref(path_ptr))
            if res == 0 and path_ptr.value:
                resolved = path_ptr.value
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                if os.path.isdir(resolved):
                    return os.path.abspath(resolved)
        except Exception as e:
            log_debug(f"[FOLDER] SHGetKnownFolderPath failed: {e}")

        # 2. Try Windows Registry (User Shell Folders)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                for val_name in ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads"):
                    try:
                        val, _ = winreg.QueryValueEx(key, val_name)
                        if val:
                            expanded = os.path.abspath(os.path.expandvars(str(val)))
                            if os.path.isdir(expanded):
                                return expanded
                    except Exception:
                        pass
        except Exception as e:
            log_debug(f"[FOLDER] Registry check failed: {e}")

        # 3. Try Windows Registry (Shell Folders)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                val, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                if val:
                    expanded = os.path.abspath(os.path.expandvars(str(val)))
                    if os.path.isdir(expanded):
                        return expanded
        except Exception:
            pass

    elif sys.platform.startswith('linux'):
        try:
            res = subprocess.run(['xdg-user-dir', 'DOWNLOAD'], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                p = res.stdout.strip()
                if os.path.isdir(p):
                    return os.path.abspath(p)
        except Exception:
            pass

    # Standard fallback: ~/Downloads
    user_home = os.path.expanduser('~')
    return os.path.abspath(os.path.join(user_home, 'Downloads'))


def resolve_download_dir(raw_folder_or_path):
    """
    Resolves the target download directory based on user settings.
    Supports:
      1. Full custom absolute paths on any drive (e.g. 'D:\\Downloads\\FTODE', 'D:/Videos', 'E:\\Media')
      2. Relative subfolder names (e.g. 'FTODE', 'Music/FTODE') resolved inside the system Downloads folder.
    Automatically creates the destination folder if it does not exist.
    """
    default_base = get_system_downloads_dir()

    if not raw_folder_or_path or not str(raw_folder_or_path).strip():
        target = os.path.join(default_base, 'FTODE')
    else:
        cleaned = str(raw_folder_or_path).strip().strip('"').strip("'")
        cleaned = os.path.expanduser(os.path.expandvars(cleaned))

        # Check if cleaned is an absolute path (Windows drive like D:\ or C:/ or UNC \\ or POSIX /)
        is_abs = os.path.isabs(cleaned) or bool(re.match(r'^[a-zA-Z]:[\\/]', cleaned)) or cleaned.startswith('\\\\')

        if is_abs:
            target = os.path.abspath(cleaned)
        else:
            # Relative folder name -> place inside system Downloads
            parts = [p for p in re.split(r'[\\/]+', cleaned) if p and p not in ('.', '..')]
            if not parts:
                parts = ['FTODE']
            target = os.path.abspath(os.path.join(default_base, *parts))

    try:
        os.makedirs(target, exist_ok=True)
    except Exception as e:
        log_debug(f"[FOLDER] Failed to create folder {target}: {e}")
        target = os.path.abspath(os.path.join(default_base, 'FTODE'))
        os.makedirs(target, exist_ok=True)

    return target


def sanitize_filename(name):
    """
    Sanitize string for Windows filename compatibility.
    """
    if not name:
        return "Media"
    name = str(name).strip()
    # Remove SponsorBlock prefixes if any
    name = re.sub(r'^(?:\[?\s*(?:Unpaid/Self Promotion|Self Promotion|Sponsor(?:ed)?|Interaction(?: Reminder)?|Intro|Outro|Preview|Filler|Highlight|Music: Non-Music Section|Exclusive Access|Patreon)\s*\]?)\s*[-:]?\s*', '', name, flags=re.IGNORECASE)
    # Remove platform suffixes
    name = re.sub(r' - YouTube$', '', name, flags=re.IGNORECASE)
    name = re.sub(r' \| SoundCloud$', '', name, flags=re.IGNORECASE)
    name = re.sub(r' - Vimeo$', '', name, flags=re.IGNORECASE).strip()
    # Replace invalid Windows characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name[:150].strip().rstrip('.')


def handle_download(payload):
    """
    Execute yt-dlp download and stream real-time logs / progress to extension.
    Auto-downloads binaries only if missing.
    """
    global active_process

    log_debug(f"DOWNLOAD PAYLOAD: {json.dumps(sanitize_log_payload(payload))}")

    # Smart extraction URL selection:
    # 1. If pageUrl is on a known rich streaming platform (YouTube, Vimeo, SoundCloud, etc.),
    #    prefer pageUrl so yt-dlp uses its full extractor to get best quality formats & metadata.
    # 2. Otherwise, if raw_url is a direct media stream / manifest (from DOM or sniffer), prefer raw_url.
    # 3. Fallback smoothly between page_url and raw_url.
    page_url = payload.get('pageUrl')
    raw_url = payload.get('url')

    if page_url and is_rich_streaming_domain(page_url) and not is_homepage_or_feed(page_url):
        url = page_url
    elif raw_url and raw_url.startswith('http'):
        url = raw_url
    elif page_url and page_url.startswith('http') and not is_homepage_or_feed(page_url):
        url = page_url
    else:
        url = raw_url or page_url

    log_debug(f"SELECTED EXTRACTION URL: {url}")

    if not url:
        send_message({'status': 'error', 'message': 'No media URL provided.'})
        return

    # Safety guard: Refuse homepage or feed URLs to prevent downloading whole feeds
    if is_homepage_or_feed(url):
        send_message({
            'status': 'error',
            'message': 'No downloadable media stream on homepage/feed. Please open a specific video or playlist.'
        })
        return

    job_id = str(payload.get('jobId') or f"job_{int(time.time() * 1000)}")

    raw_type = str(payload.get('type') or payload.get('mediaType') or payload.get('targetType') or '').lower()
    raw_format = str(payload.get('format', 'mp4')).lower().strip().lstrip('.')

    valid_video_formats = ('mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', 'gif')
    valid_audio_formats = ('mp3', 'm4a', 'wav', 'flac', 'ogg', 'opus', 'aac', 'alac', 'vorbis')

    if raw_format in valid_audio_formats:
        target_format = raw_format
        media_type = 'audio'
    elif raw_format in valid_video_formats:
        target_format = raw_format
        media_type = 'video' if raw_type != 'audio' else 'audio'
    else:
        target_format = 'mp3' if raw_type == 'audio' else 'mp4'
        media_type = 'audio' if raw_type == 'audio' else 'video'

    raw_folder = str(payload.get('downloadFolder', 'FTODE') or 'FTODE').strip()
    raw_video_quality = str(payload.get('videoQuality', 'best')).lower().strip()
    raw_audio_quality = str(payload.get('audioQuality', 'best')).lower().strip()

    res_map = {
        '4320p': 4320,
        '2160p': 2160,
        '1440p': 1440,
        '1080p': 1080,
        '720p': 720,
        '480p': 480,
        '360p': 360,
        '240p': 240
    }
    video_quality = raw_video_quality if raw_video_quality in res_map else 'best'

    if raw_audio_quality and raw_audio_quality != 'best':
        clean_bitrate = raw_audio_quality.replace('kbps', '').replace('k', '').strip()
        if clean_bitrate.isdigit() and 0 <= int(clean_bitrate) <= 1000:
            audio_quality = clean_bitrate
        else:
            audio_quality = '0'
    else:
        audio_quality = '0'

    existing_file_action = str(payload.get('existingFileAction', 'copy')).lower()
    if existing_file_action not in ('copy', 'overwrite', 'skip'):
        existing_file_action = 'copy'

    custom_ytdlp = payload.get('customYtdlpPath')
    custom_ffmpeg = payload.get('customFfmpegPath')
    title_hint = payload.get('title')

    # Resolve output directory (supports full absolute paths across drives D:, E:, etc. and relative subfolders)
    output_dir = resolve_download_dir(raw_folder)
    send_message({'status': 'log', 'line': f"[INFO] Destination folder: {output_dir}"})

    # Check if yt-dlp or FFmpeg are missing -> auto-bootstrap only if missing
    ytdlp_bin = find_executable('yt-dlp', custom_ytdlp)
    ffmpeg_bin = find_executable('ffmpeg', custom_ffmpeg)

    if not ytdlp_bin or not ffmpeg_bin:
        send_message({'status': 'log', 'line': '[INFO] Missing yt-dlp or FFmpeg. Auto-downloading tools...'})

        def on_auto_bootstrap(pct, dl, tot, msg):
            send_message({
                'status': 'progress',
                'line': msg,
                'percent': pct * 0.1,
                'speed': 'Downloading tools...',
                'eta': '--',
                'stage': 'downloading'
            })

        try:
            ytdlp_bin, ffmpeg_bin = bootstrap_dependencies(force=False, callback=on_auto_bootstrap)
            send_message({'status': 'log', 'line': '[INFO] Tools ready. Proceeding with media extraction...'})
        except Exception as e:
            send_message({'status': 'error', 'message': f"Failed to auto-install dependencies: {e}"})
            return

    # Check if URL or payload represents a playlist
    is_playlist_req = payload.get('isPlaylist')
    url_lower = (url or '').lower()
    page_url_lower = (page_url or '').lower()

    if is_playlist_req is True:
        is_playlist = True
    elif '/playlist' in url_lower or '/playlist' in page_url_lower or '/sets/' in url_lower or '/album/' in url_lower or '/playlists/' in url_lower:
        is_playlist = True
    elif ('list=' in url_lower or 'list=' in page_url_lower) and 'list=ll' not in url_lower and 'list=wl' not in url_lower and '/watch' not in url_lower and 'v=' not in url_lower:
        is_playlist = True
    else:
        is_playlist = bool(is_playlist_req)

    target_ext = '.' + target_format.lower().lstrip('.')
    if target_ext == '.vorbis':
        target_ext = '.ogg'

    # Output template & Duplicate Handling
    if is_playlist:
        playlist_args = ['--yes-playlist']
        playlist_title = None
        if title_hint and title_hint not in ('Media Download', 'Media Stream', 'No media detected'):
            playlist_title = sanitize_filename(title_hint)
        else:
            # Probe yt-dlp quickly for the true playlist title
            try:
                probe_cmd = [
                    ytdlp_bin,
                    '--flat-playlist',
                    '--dump-single-json',
                    '--playlist-items', '1',
                    '--no-warnings',
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--',
                    url
                ]
                res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=6, stdin=subprocess.DEVNULL)
                if res.returncode == 0 and res.stdout.strip():
                    info_data = json.loads(res.stdout)
                    raw_title = info_data.get('title') or info_data.get('playlist_title')
                    if raw_title:
                        playlist_title = sanitize_filename(raw_title)
            except Exception as e:
                log_debug(f"Playlist title probe: {e}")

        safe_pl_title = playlist_title or 'Playlist'

        if existing_file_action == 'copy':
            existing_dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))] if os.path.isdir(output_dir) else []

            candidate_idx = 0
            while True:
                target_folder_name = safe_pl_title if candidate_idx == 0 else f"{safe_pl_title} ({candidate_idx})"
                matched_dir = next((d for d in existing_dirs if d.lower() == target_folder_name.lower()), None)

                if not matched_dir:
                    break

                full_matched_path = os.path.join(output_dir, matched_dir)
                dir_files = os.listdir(full_matched_path) if os.path.isdir(full_matched_path) else []
                has_target_format = any(
                    f.lower().endswith(target_ext) and not f.endswith('.part') and not f.endswith('.ytdl')
                    for f in dir_files
                )
                if not has_target_format:
                    # Target folder exists (e.g. contains .mp3), but has no files of target_ext (e.g. .mp4) -> use same folder
                    break

                candidate_idx += 1

            if candidate_idx == 0:
                output_template = os.path.join(output_dir, safe_pl_title, '%(playlist_index,autonumber)02d - %(title).150s.%(ext)s')
                send_message({'status': 'log', 'line': f"[INFO] Playlist mode active. Saving to {output_dir}/{safe_pl_title}/"})
            else:
                folder_dest_name = f"{safe_pl_title} ({candidate_idx})"
                output_template = os.path.join(output_dir, folder_dest_name, '%(playlist_index,autonumber)02d - %(title).150s.%(ext)s')
                send_message({'status': 'log', 'line': f"[INFO] Playlist '{safe_pl_title}' with {target_ext} already exists. Creating new playlist folder '{folder_dest_name}'."})
        else:
            output_template = os.path.join(output_dir, safe_pl_title, '%(playlist_index,autonumber)02d - %(title).150s.%(ext)s')
            send_message({'status': 'log', 'line': f"[INFO] Playlist mode active. Saving to {output_dir}/{safe_pl_title}/"})
    else:
        playlist_args = ['--no-playlist']
        if existing_file_action == 'copy':
            target_title = None
            if title_hint and title_hint not in ('Media Download', 'Media Stream', 'No media detected'):
                target_title = sanitize_filename(title_hint)
            else:
                # Probe title from yt-dlp quickly
                try:
                    probe_cmd = [
                        ytdlp_bin,
                        '--print', '%(title).150s',
                        '--no-warnings',
                        '--skip-download',
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--',
                        url
                    ]
                    res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=6, stdin=subprocess.DEVNULL)
                    if res.returncode == 0 and res.stdout.strip():
                        target_title = sanitize_filename(res.stdout.strip().split('\n')[0])
                except Exception as e:
                    log_debug(f"Title probe error: {e}")

            if target_title:
                safe_title = target_title
                existing_files = os.listdir(output_dir) if os.path.isdir(output_dir) else []

                def norm_str(s):
                    return re.sub(r'[\W_]+', '', s).lower()

                s_norm = norm_str(safe_title)
                used_indices = set()
                has_base_match = False

                for f in existing_files:
                    if f.endswith('.part') or f.endswith('.ytdl'):
                        continue
                    if not f.lower().endswith(target_ext):
                        continue
                    f_base = os.path.splitext(f)[0]

                    # Extract existing copy index (1), (2), etc.
                    m = re.search(r'\s*\((\d+)\)$', f_base.strip())
                    if m:
                        idx = int(m.group(1))
                        f_clean = re.sub(r'\s*\(\d+\)$', '', f_base.strip())
                    else:
                        idx = None
                        f_clean = f_base.strip()

                    f_norm = norm_str(f_clean)

                    # Compare normalized representations to ignore bracket variations, whitespace, and unicode symbols
                    if f_norm == s_norm or f_norm.startswith(s_norm) or s_norm.startswith(f_norm) or (len(s_norm) > 4 and s_norm in f_norm) or (len(f_norm) > 4 and f_norm in s_norm):
                        has_base_match = True
                        if idx is not None:
                            used_indices.add(idx)

                if has_base_match:
                    copy_idx = 1
                    while copy_idx in used_indices:
                        copy_idx += 1
                    output_template = os.path.join(output_dir, f"%(title).150s ({copy_idx}).%(ext)s")
                    send_message({'status': 'log', 'line': f"[INFO] File '{safe_title}' already exists in folder. Creating copy '({copy_idx})'."})
                else:
                    output_template = os.path.join(output_dir, '%(title).150s.%(ext)s')
            else:
                output_template = os.path.join(output_dir, '%(title).150s.%(ext)s')
        else:
            output_template = os.path.join(output_dir, '%(title).150s.%(ext)s')





    # Overwrite parameters
    if existing_file_action == 'overwrite':
        overwrite_args = ['--force-overwrites']
    else:
        overwrite_args = ['--no-force-overwrites']

    ytdlp_cmd = [ytdlp_bin]
    cmd_args = list(ytdlp_cmd)
    cmd_args.extend([
        '--newline',
        '--no-colors',
        '--progress',
        '--progress-template', 'download-progress:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._total_bytes_str)s|%(info.playlist_index)s|%(info.n_entries)s|%(info.title)s',
        *playlist_args,
        *overwrite_args,
        '--ignore-errors',
        '--no-abort-on-error',
        '--compat-options', 'no-youtube-unavailable-videos',
        '--extractor-args', 'generic:impersonate;youtube:player_client=android,web,web_embedded,mweb,ios',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        '--geo-bypass',
        '--extractor-retries', '10',
        '--sleep-interval', '1',
        '--retry-sleep', 'exp=1:10',
        '--windows-filenames',
        '--retries', '10',
        '--fragment-retries', '10',
        '--file-access-retries', '5',
        '-o', output_template
    ])

    page_url = payload.get('pageUrl')
    if page_url and page_url != url:
        cmd_args.extend(['--referer', page_url])

    # Browser authenticated cookies injection
    # Do NOT inject cookies for YouTube URLs by default to prevent YouTube's SABR / TV 360p downgrade!
    cookies_text = payload.get('cookiesText')
    cookies_file = None
    is_yt = 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

    if cookies_text and isinstance(cookies_text, str) and len(cookies_text) > 30 and not is_yt:
        try:
            fd, cookies_file = tempfile.mkstemp(prefix=f"ftode_cookies_{os.getpid()}_", suffix=".txt")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(cookies_text)
            cmd_args.extend(['--cookies', cookies_file])
            send_message({'status': 'log', 'line': '[INFO] Attached browser session authentication cookies.'})
        except Exception as e:
            send_message({'status': 'log', 'line': f'[WARN] Could not write session cookies: {e}'})

    if ffmpeg_bin:
        ffmpeg_dir = os.path.dirname(ffmpeg_bin) if ffmpeg_bin.endswith('.exe') else ffmpeg_bin
        cmd_args.extend(['--ffmpeg-location', ffmpeg_dir])

    # Audio-only platform detection (SoundCloud, Bandcamp, Mixcloud, etc.)
    AUDIO_ONLY_DOMAINS = (
        'soundcloud.com',
        'bandcamp.com',
        'mixcloud.com',
        'audiomack.com',
        'spotify.com',
        'music.apple.com',
        'deezer.com',
        'tidal.com'
    )
    is_audio_domain = any(d in url.lower() for d in AUDIO_ONLY_DOMAINS)

    if is_audio_domain and media_type == 'video':
        media_type = 'audio'
        if target_format in ('mp4', 'mkv', 'webm', 'avi', 'mov', 'flv'):
            target_format = 'mp3'
        send_message({
            'status': 'log',
            'line': f"[INFO] Audio-only stream detected. Automatically extracting audio ({target_format.upper()})."
        })

    if media_type == 'video':
        res_map = {
            '4320p': 4320,
            '2160p': 2160,
            '1440p': 1440,
            '1080p': 1080,
            '720p': 720,
            '480p': 480,
            '360p': 360,
            '240p': 240
        }
        target_res = res_map.get(video_quality)
        format_spec = "bv*+ba/b"

        # Prioritize original/default audio tracks ('lang') over auto-translations and dubs
        if target_res:
            cmd_args.extend(['--format-sort', f"lang,res:{target_res},fps,quality,br"])
        else:
            cmd_args.extend(['--format-sort', "lang,res,fps,quality,br"])

        if target_format == 'gif':
            cmd_args.extend([
                '-f', format_spec,
                '--recode-video', 'gif'
            ])
        elif target_format in ('avi', 'flv', 'mov', 'mp4', 'mkv', 'webm'):
            cmd_args.extend([
                '-f', format_spec,
                '--merge-output-format', target_format
            ])
        else:
            cmd_args.extend([
                '-f', format_spec,
                '--merge-output-format', 'mp4'
            ])


    elif media_type == 'audio':
        fmt = 'vorbis' if target_format in ('ogg', 'vorbis') else target_format
        cmd_args.extend([
            '--format-sort', 'lang,quality,br',
            '-f', 'bestaudio/best',
            '-x',
            '--audio-format', fmt
        ])
        cmd_args.extend(['--audio-quality', audio_quality])

    # Target URL (guarded with '--' to prevent CLI option injection)
    cmd_args.extend(['--', url])

    log_debug(f"SPAWNING CMD: {' '.join(cmd_args)}")

    send_message({
        'status': 'log',
        'line': f"[INFO] Spawning yt-dlp: {cmd_args[0]} [target: {url}]"
    })


    # Regex patterns for fallback progress parsing
    progress_regex = re.compile(r'\[download\]\s+([\d\.]+)%\s+of\s+~?([\d\.]+\w+)\s+at\s+([\d\.]+\w+/s)\s+ETA\s+([\d:]+)')
    dest_regex = re.compile(r'\[(?:download|Merger|ExtractAudio)\]\s+(?:Destination:\s*|Merging formats into\s*"?)([^"\n\r]+)')
    already_dl_regex = re.compile(r'\[download\]\s+(.+?)\s+has already been downloaded')
    ffmpeg_prog_regex = re.compile(r'frame=\s*(\d+).*time=\s*([\d:\.]+).*speed=\s*([\d\.]+x)')

    last_file = None
    accumulated_errors = []
    zero_items_detected = False
    skipped_already_exists = 0
    current_track_index = 1
    total_playlist_items = None
    current_track_title = ''
    start_time = time.time()
    last_eta_estimate = None

    def format_time_eta(seconds):
        if seconds is None or seconds < 0 or seconds > 86400 * 7:
            return '--:--'
        secs = int(round(seconds))
        if secs < 3:
            return 'Almost done'
        if secs < 60:
            return f"00:{secs:02d}"
        hours = secs // 3600
        mins = (secs % 3600) // 60
        rem_secs = secs % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{rem_secs:02d}"
        return f"{mins:02d}:{rem_secs:02d}"

    def calculate_playlist_eta(overall_pct):
        nonlocal last_eta_estimate
        elapsed = time.time() - start_time
        if elapsed < 2 or overall_pct < 0.5:
            return '--:--'
        total_expected = elapsed / (overall_pct / 100.0)
        remaining = max(0, total_expected - elapsed)
        if last_eta_estimate is not None:
            remaining = 0.7 * last_eta_estimate + 0.3 * remaining
        last_eta_estimate = remaining
        return format_time_eta(remaining)

    # Snapshot files and directories before execution recursively to detect newly created files
    files_before = scan_dir_files(output_dir)
    dirs_before = scan_dir_folders(output_dir)

    download_ctx = {
        'job_id': job_id,
        'output_dir': output_dir,
        'files_before': files_before,
        'dirs_before': dirs_before,
        'is_cancelled': False,
        'is_playlist': is_playlist,
        'target_format': target_format,
        'current_track_index': 1,
        'completed_track_indices': set(),
        'completed_files': set(),
        'cookies_file': cookies_file
    }

    try:
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0x08000000

        proc = subprocess.Popen(
            cmd_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            creationflags=creation_flags
        )
        download_ctx['process'] = proc

        with active_lock:
            last_download_context = download_ctx
            active_jobs[job_id] = {
                'process': proc,
                'context': download_ctx
            }

        # Stream unbuffered stdout line by line
        for clean_line in read_unbuffered_lines(proc):
            if download_ctx.get('is_cancelled'):
                break
            log_debug(f"YT-DLP: {clean_line}")
            # Check for zero items
            if 'Downloading 0 items' in clean_line:
                zero_items_detected = True

            # Match already downloaded files
            adl_match = already_dl_regex.search(clean_line)
            if adl_match:
                skipped_already_exists += 1
                skipped_name = os.path.basename(adl_match.group(1).strip().strip('"'))
                send_message({
                    'status': 'log',
                    'line': f"[INFO] Already downloaded (skipped): {skipped_name}"
                })

            # Match item N of M in logs
            item_match = re.search(r'Downloading (?:item|video)\s+(\d+)\s+of\s+(\d+)', clean_line)
            if item_match:
                new_idx = int(item_match.group(1))
                if new_idx > current_track_index:
                    download_ctx['completed_track_indices'].add(current_track_index)
                    current_track_index = new_idx
                    download_ctx['current_track_index'] = current_track_index
                total_playlist_items = int(item_match.group(2))
                N = max(1, total_playlist_items)
                i = max(1, min(current_track_index, N))
                overall_pct = min(99.0, ((i - 1) / N) * 100.0)
                send_message({
                    'status': 'progress',
                    'line': f"[{i}/{N}] Starting track download...",
                    'percent': round(overall_pct, 1),
                    'speed': f"Starting ({i}/{N})",
                    'eta': calculate_playlist_eta(overall_pct),
                    'stage': 'downloading'
                })

            # Check for structured progress template
            if clean_line.startswith('download-progress:'):
                try:
                    payload_part = clean_line.split('download-progress:')[1].strip()
                    parts = payload_part.split('|')
                    raw_pct = parts[0].replace('%', '').strip()
                    pct = float(raw_pct) if raw_pct and raw_pct != 'N/A' else 0.0
                    spd = parts[1].strip() if len(parts) > 1 and parts[1].strip() != 'N/A' else ''
                    eta_str = parts[2].strip() if len(parts) > 2 and parts[2].strip() != 'N/A' else ''

                    if len(parts) > 4 and parts[4].strip().isdigit():
                        new_idx = int(parts[4].strip())
                        if new_idx > current_track_index:
                            download_ctx['completed_track_indices'].add(current_track_index)
                            current_track_index = new_idx
                            download_ctx['current_track_index'] = current_track_index
                    if len(parts) > 5 and parts[5].strip().isdigit():
                        total_playlist_items = int(parts[5].strip())
                    if len(parts) > 6 and parts[6].strip():
                        current_track_title = parts[6].strip()

                    if is_playlist or (total_playlist_items and total_playlist_items > 1):
                        N = max(1, total_playlist_items or 1)
                        i = max(1, min(current_track_index, N))
                        overall_pct = min(99.0, (((i - 1) + (pct / 100.0)) / N) * 100.0)
                        est_eta = calculate_playlist_eta(overall_pct)
                        if est_eta == '--:--' and eta_str and eta_str != '--:--':
                            est_eta = eta_str

                        send_message({
                            'status': 'progress',
                            'line': f"[{i}/{N}] Downloading {pct:.0f}% ({spd}) ETA {est_eta}".strip(),
                            'percent': round(overall_pct, 1),
                            'speed': f"{spd} ({i}/{N})" if spd else f"Downloading ({i}/{N})",
                            'eta': est_eta,
                            'stage': 'downloading'
                        })
                    else:
                        send_message({
                            'status': 'progress',
                            'line': f"[download] {pct:.1f}% of {parts[3] if len(parts) > 3 else ''} at {spd} ETA {eta_str}".strip(),
                            'percent': pct,
                            'speed': spd or 'Downloading',
                            'eta': eta_str or '--:--',
                            'stage': 'downloading'
                        })
                    continue
                except Exception:
                    pass

            # Destination filename extraction
            dest_match = dest_regex.search(clean_line)
            if dest_match:
                last_file = dest_match.group(1).strip().strip('"')
                if is_playlist and last_file and not last_file.endswith('.part') and not last_file.endswith('.ytdl'):
                    download_ctx['completed_files'].add(os.path.abspath(last_file))

            # Fallback regex progress
            prog_match = progress_regex.search(clean_line)
            if prog_match:
                percent = float(prog_match.group(1))
                speed = prog_match.group(3)
                eta = prog_match.group(4)
                if is_playlist or (total_playlist_items and total_playlist_items > 1):
                    N = max(1, total_playlist_items or 1)
                    i = max(1, min(current_track_index, N))
                    overall_pct = min(99.0, (((i - 1) + (percent / 100.0)) / N) * 100.0)
                    est_eta = calculate_playlist_eta(overall_pct)
                    if est_eta == '--:--' and eta and eta != '--:--':
                        est_eta = eta
                    send_message({
                        'status': 'progress',
                        'line': f"[{i}/{N}] Downloading {percent:.0f}% ({speed}) ETA {est_eta}".strip(),
                        'percent': round(overall_pct, 1),
                        'speed': f"{speed} ({i}/{N})" if speed else f"Downloading ({i}/{N})",
                        'eta': est_eta,
                        'stage': 'downloading'
                    })
                else:
                    send_message({
                        'status': 'progress',
                        'line': clean_line,
                        'percent': percent,
                        'speed': speed,
                        'eta': eta,
                        'stage': 'downloading'
                    })
            elif ffmpeg_prog_regex.search(clean_line):
                f_match = ffmpeg_prog_regex.search(clean_line)
                speed_str = f_match.group(3)
                if is_playlist or (total_playlist_items and total_playlist_items > 1):
                    N = max(1, total_playlist_items or 1)
                    i = max(1, min(current_track_index, N))
                    overall_pct = min(99.0, (i / N) * 100.0)
                    est_eta = calculate_playlist_eta(overall_pct)
                    send_message({
                        'status': 'progress',
                        'line': f"[{i}/{N}] Processing audio/video remuxing...",
                        'percent': round(overall_pct, 1),
                        'speed': f"{speed_str} ({i}/{N})",
                        'eta': est_eta,
                        'stage': 'remuxing'
                    })
                else:
                    send_message({
                        'status': 'progress',
                        'line': clean_line,
                        'percent': 95,
                        'speed': f"{speed_str} (FFmpeg)",
                        'eta': 'Almost done',
                        'stage': 'remuxing'
                    })
            elif '[Merger]' in clean_line or '[ffmpeg]' in clean_line or '[ExtractAudio]' in clean_line:
                if is_playlist or (total_playlist_items and total_playlist_items > 1):
                    N = max(1, total_playlist_items or 1)
                    i = max(1, min(current_track_index, N))
                    overall_pct = min(99.0, (i / N) * 100.0)
                    est_eta = calculate_playlist_eta(overall_pct)
                    send_message({
                        'status': 'progress',
                        'line': f"[{i}/{N}] Converting track format...",
                        'percent': round(overall_pct, 1),
                        'speed': f"Converting ({i}/{N})",
                        'eta': est_eta,
                        'stage': 'remuxing'
                    })
                else:
                    send_message({
                        'status': 'progress',
                        'line': clean_line,
                        'percent': 95,
                        'speed': 'Converting',
                        'eta': 'Almost done',
                        'stage': 'remuxing'
                    })
            else:
                if 'ERROR:' in clean_line:
                    accumulated_errors.append(clean_line)
                send_message({
                    'status': 'log',
                    'line': clean_line
                })

        try:
            if proc and proc.stdout:
                proc.stdout.close()
        except Exception:
            pass

        return_code = 0
        try:
            if proc:
                return_code = proc.wait()
        except Exception:
            pass

        # Check if download was cancelled by user
        if download_ctx.get('is_cancelled'):
            log_debug(f"Download [{job_id}] was cancelled. Running final residue cleanup.")
            cleanup_download_residue(download_ctx)
            with active_lock:
                active_jobs.pop(job_id, None)
            return

        with active_lock:
            active_jobs.pop(job_id, None)

        files_after = scan_dir_files(output_dir)
        new_files = list(files_after - files_before)

        # Filter out partial / residue files from completed files list
        real_new_files = [f for f in new_files if not f.endswith('.part') and not f.endswith('.ytdl') and '.part-' not in f and not f.endswith('.tmp') and not f.endswith('.temp')]

        if real_new_files or (last_file and os.path.isfile(last_file) and not last_file.endswith('.part') and not last_file.endswith('.ytdl')):
            # Files were successfully written!
            download_ctx['is_completed'] = True
            resolved_target = real_new_files[0] if real_new_files else last_file
            if len(real_new_files) > 1:
                skip_info = f" ({skipped_already_exists} skipped - already downloaded)" if skipped_already_exists > 0 else ""
                msg = f"Saved {len(real_new_files)} track(s) to playlist folder!{skip_info}"
            else:
                msg = f"Saved: {os.path.basename(resolved_target)}"

            send_message({
                'status': 'complete',
                'file': resolved_target,
                'message': msg
            })
        elif skipped_already_exists > 0:
            download_ctx['is_completed'] = True
            skip_msg = f"Completed! {skipped_already_exists} file(s) already existed in folder and were skipped."
            send_message({
                'status': 'complete',
                'file': output_dir,
                'message': skip_msg
            })
        else:
            cleanup_download_residue(download_ctx)
            err_details = accumulated_errors[-1] if accumulated_errors else f"Process exited with code {return_code}"
            send_message({
                'status': 'error',
                'message': f"yt-dlp: {err_details}"
            })

    except Exception as e:
        log_debug(f"HANDLE_DOWNLOAD EXCEPTION [{job_id}]: {e}")
        with active_lock:
            if download_ctx.get('is_cancelled'):
                cleanup_download_residue(download_ctx)
                active_jobs.pop(job_id, None)
                return
            active_jobs.pop(job_id, None)
        send_message({
            'status': 'error',
            'message': f"Process execution error: {str(e)}"
        })
    finally:
        if cookies_file and os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
            except Exception:
                pass
        with active_lock:
            active_jobs.pop(job_id, None)


def handle_cancel(message=None):
    """
    Terminates the active yt-dlp / FFmpeg process tree immediately and cleans up residue files.
    Supports cancelling a specific job by jobId or all active jobs.
    """
    global active_jobs, last_download_context
    target_job_id = message.get('jobId') if isinstance(message, dict) else None

    jobs_to_cancel = []
    with active_lock:
        if target_job_id and target_job_id in active_jobs:
            jobs_to_cancel.append(active_jobs.pop(target_job_id))
        elif active_jobs:
            jobs_to_cancel.extend(active_jobs.values())
            active_jobs.clear()
        elif last_download_context:
            jobs_to_cancel.append({'process': None, 'context': last_download_context})

    for item in jobs_to_cancel:
        ctx = item.get('context')
        proc = item.get('process')
        if ctx is not None:
            ctx['is_cancelled'] = True

        if proc is not None:
            pid = proc.pid
            log_debug(f"[CANCEL] Terminating active process PID {pid}")
            try:
                if sys.platform == 'win32':
                    # Terminate process and all child subprocesses (yt-dlp + ffmpeg)
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception as e:
                log_debug(f"[CANCEL] taskkill error: {e}")

            try:
                proc.kill()
            except Exception:
                pass

            # Wait briefly for process to exit so Windows releases all file handles
            try:
                proc.wait(timeout=2.0)
            except Exception:
                pass

        time.sleep(0.3)

        target_dir = ctx.get('output_dir') if ctx else None
        if not target_dir:
            target_dir = resolve_download_dir('FTODE')

        if target_dir and os.path.isdir(target_dir):
            log_debug(f"[CANCEL] Cleaning up residue for output_dir: {target_dir}")
            try:
                cleanup_download_residue(ctx or {'output_dir': target_dir})
            except Exception as e:
                log_debug(f"[CANCEL] cleanup error: {e}")

    send_message({
        'status': 'cancelled',
        'message': 'Download job cancelled by user. Partial files cleaned up.'
    })


def get_linux_browser_manifest_dirs():
    """
    Standard Linux user-level native messaging host directories.
    """
    home = os.path.expanduser('~')
    return {
        'Google Chrome': os.path.join(home, '.config', 'google-chrome', 'NativeMessagingHosts'),
        'Chromium': os.path.join(home, '.config', 'chromium', 'NativeMessagingHosts'),
        'Brave': os.path.join(home, '.config', 'BraveSoftware', 'Brave-Browser', 'NativeMessagingHosts'),
        'Microsoft Edge': os.path.join(home, '.config', 'microsoft-edge', 'NativeMessagingHosts'),
        'Opera': os.path.join(home, '.config', 'opera', 'NativeMessagingHosts'),
        'Vivaldi': os.path.join(home, '.config', 'vivaldi', 'NativeMessagingHosts'),
        'Mozilla Firefox': os.path.join(home, '.mozilla', 'native-messaging-hosts')
    }


def install_registry(extension_id=None):
    """
    Cross-platform self-installer for Native Messaging registration (Windows & Linux).
    Uses the fixed permanent Extension ID by default.
    """
    if not extension_id or extension_id == 'ALLOWED_EXTENSION_ID':
        extension_id = 'iabbelaamkcbkklcipbbkgegfenjhklc'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    is_win = sys.platform == 'win32'
    launcher_path = os.path.join(script_dir, 'run_host.bat' if is_win else 'run_host.sh')

    if not is_win:
        # Ensure execution permissions on Linux
        try:
            os.chmod(os.path.join(script_dir, 'host.py'), 0o755)
            if os.path.isfile(launcher_path):
                os.chmod(launcher_path, 0o755)
        except Exception:
            pass

    chrome_manifest_path = os.path.join(script_dir, 'com.ftode.host.json')
    firefox_manifest_path = os.path.join(script_dir, 'com.ftode.host-firefox.json')

    # 1. Chrome / Chromium Manifest
    chrome_manifest_data = {
        "name": "com.ftode.host",
        "description": "Finally that online downloader extension (FTODE) Native Messaging Host",
        "path": launcher_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }
    with open(chrome_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(chrome_manifest_data, f, indent=2)

    # 2. Mozilla Firefox Manifest
    firefox_manifest_data = {
        "name": "com.ftode.host",
        "description": "Finally that online downloader extension (FTODE) Native Messaging Host",
        "path": launcher_path,
        "type": "stdio",
        "allowed_extensions": [
            "ftode@maxakt.local"
        ]
    }
    with open(firefox_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(firefox_manifest_data, f, indent=2)

    if is_win:
        import winreg
        reg_keys = [
            (r"Software\Google\Chrome\NativeMessagingHosts\com.ftode.host", "Google Chrome", chrome_manifest_path),
            (r"Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host", "Microsoft Edge", chrome_manifest_path),
            (r"Software\Chromium\NativeMessagingHosts\com.ftode.host", "Chromium / Opera / Brave", chrome_manifest_path),
            (r"Software\Mozilla\NativeMessagingHosts\com.ftode.host", "Mozilla Firefox", firefox_manifest_path)
        ]
        for reg_key_path, browser_name, m_path in reg_keys:
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key_path)
                winreg.SetValue(key, "", winreg.REG_SZ, m_path)
                winreg.CloseKey(key)
                print(f"[v] Successfully registered for {browser_name} in Windows Registry!")
            except Exception as e:
                print(f"[x] Registry installation failed for {browser_name}: {e}")
    else:
        # Linux filesystem registration
        browser_dirs = get_linux_browser_manifest_dirs()
        for browser_name, target_dir in browser_dirs.items():
            try:
                os.makedirs(target_dir, exist_ok=True)
                dest_file = os.path.join(target_dir, 'com.ftode.host.json')
                src_data = firefox_manifest_data if 'Firefox' in browser_name else chrome_manifest_data
                with open(dest_file, 'w', encoding='utf-8') as f:
                    json.dump(src_data, f, indent=2)
                print(f"[v] Installed manifest for {browser_name} -> {dest_file}")
            except Exception as e:
                print(f"[x] Could not write manifest for {browser_name}: {e}")

    print(f"    Chrome Manifest: {chrome_manifest_path}")
    print(f"    Firefox Manifest: {firefox_manifest_path}")
    print(f"    Allowed Origin: chrome-extension://{extension_id}/")
    print(f"    Gecko Extension ID: ftode@maxakt.local")


def uninstall_registry():
    """
    Unregisters the Native Messaging Host across browsers (Windows & Linux).
    """
    if sys.platform == 'win32':
        import winreg
        reg_keys = [
            (r"Software\Google\Chrome\NativeMessagingHosts\com.ftode.host", "Google Chrome"),
            (r"Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host", "Microsoft Edge"),
            (r"Software\Chromium\NativeMessagingHosts\com.ftode.host", "Chromium / Opera / Brave"),
            (r"Software\Mozilla\NativeMessagingHosts\com.ftode.host", "Mozilla Firefox")
        ]

        print("[*] Removing FTODE Native Host from Windows Registry...")
        for reg_key_path, browser_name in reg_keys:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_key_path)
                print(f"[v] Successfully removed registry key for {browser_name}!")
            except FileNotFoundError:
                print(f"[-] Registry key already clean for {browser_name}.")
            except Exception as e:
                print(f"[x] Could not delete registry key for {browser_name}: {e}")
    else:
        print("[*] Removing FTODE Native Host manifests on Linux...")
        browser_dirs = get_linux_browser_manifest_dirs()
        for browser_name, target_dir in browser_dirs.items():
            dest_file = os.path.join(target_dir, 'com.ftode.host.json')
            if os.path.isfile(dest_file):
                try:
                    os.remove(dest_file)
                    print(f"[v] Removed manifest for {browser_name}: {dest_file}")
                except Exception as e:
                    print(f"[x] Could not remove manifest for {browser_name}: {e}")

    print("\n[v] FTODE Native Host unregistration complete.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--install', '-i', 'install'):
        ext_id = sys.argv[2] if len(sys.argv) > 2 else None
        install_registry(ext_id)
        return

    if len(sys.argv) > 1 and sys.argv[1] in ('--uninstall', '-u', 'uninstall'):
        uninstall_registry()
        return

    if len(sys.argv) > 1 and sys.argv[1] in ('--bootstrap', '-b', 'bootstrap'):
        print("[*] Checking yt-dlp & FFmpeg binaries...")
        def cli_callback(pct, dl, tot, msg):
            print(msg)
        ytdlp_bin, ffmpeg_bin = bootstrap_dependencies(force=False, callback=cli_callback)
        print(f"[v] yt-dlp: {ytdlp_bin}")
        print(f"[v] FFmpeg: {ffmpeg_bin}")
        return

    # Normal Native Messaging loop
    log_debug("HOST PROCESS STARTED (listening for messages)")
    try:
        while True:
            message = read_message()
            if message is None:
                log_debug("HOST STDIN CLOSED (exiting)")
                break

            log_debug(f"MESSAGE RECEIVED: {json.dumps(sanitize_log_payload(message))}")
            action = message.get('action', '').upper()

            if action == 'PING':
                handle_ping(message)
            elif action == 'CHECK_UPDATES' or action == 'UPDATE_BINARIES':
                thread = threading.Thread(target=handle_check_updates, args=(message,), daemon=True)
                thread.start()
            elif action == 'BOOTSTRAP_BINARIES' or action == 'INSTALL_BINARIES':
                thread = threading.Thread(target=handle_bootstrap, args=(message,), daemon=True)
                thread.start()
            elif action == 'DOWNLOAD':
                thread = threading.Thread(target=handle_download, args=(message,), daemon=True)
                thread.start()
            elif action == 'CANCEL':
                try:
                    handle_cancel(message)
                except Exception as e:
                    log_debug(f"HANDLE_CANCEL EXCEPTION: {e}")
            else:
                send_message({
                    'status': 'error',
                    'message': f"Unknown action: {action}"
                })
    finally:
        cleanup_all_processes()



if __name__ == '__main__':
    main()
