#!/usr/bin/env python3
"""
Max's Downloader - Python Native Messaging Host Backend
Interfaces Chrome extension with yt-dlp and FFmpeg using Native Messaging.
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

# Official direct release URLs for Windows
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_ZIP_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_BACKUP_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Global active process & write locks
active_process = None
active_lock = threading.Lock()
stdout_lock = threading.Lock()
bootstrap_lock = threading.Lock()


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
            sys.stderr.write(f"[MaxsDownloader Host Error] send_message failed: {e}\n")


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
        sys.stderr.write(f"[MaxsDownloader Host Error] read_message failed: {e}\n")
        return None


def read_unbuffered_lines(process):
    """
    Yields decoded, non-empty lines from process.stdout in real time.
    Handles both \r (carriage return progress) and \n (newlines).
    """
    buffer = []
    while True:
        try:
            char = process.stdout.read(1)
        except Exception:
            break
        if not char:
            if process.poll() is not None:
                break
            continue
        if char == '\r' or char == '\n':
            line = ''.join(buffer).strip()
            buffer = []
            if line:
                yield line
        else:
            buffer.append(char)
    if buffer:
        line = ''.join(buffer).strip()
        if line:
            yield line


def find_executable(name, custom_path=None):
    """
    Locate yt-dlp or ffmpeg executable.
    Priority:
      1. Custom path in settings
      2. Local prepackaged native_host/bin/
      3. System PATH
      4. Common install folders (WinGet, Scoop, Python Scripts, Program Files)
    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    exe_name = f"{name}.exe" if sys.platform == 'win32' and not name.endswith('.exe') else name

    # 1. Check local native_host/bin/
    local_bin = os.path.join(get_bin_dir(), exe_name)
    if os.path.isfile(local_bin):
        return local_bin

    # 2. Check system PATH
    found = shutil.which(name)
    if found:
        return found

    # 3. Check Windows common package locations
    if sys.platform == 'win32':
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

    return None


def get_version(executable_path):
    """
    Get version string from executable.
    """
    if not executable_path or not os.path.isfile(executable_path):
        return None
    try:
        res = subprocess.run([executable_path, '--version'], capture_output=True, text=True, timeout=3, stdin=subprocess.DEVNULL)
        if res.returncode == 0:
            return res.stdout.strip().split('\n')[0]
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
    only if missing (or if force=True).
    """
    with bootstrap_lock:
        bin_dir = get_bin_dir()
        ytdlp_dest = os.path.join(bin_dir, 'yt-dlp.exe')
        ffmpeg_dest = os.path.join(bin_dir, 'ffmpeg.exe')

        # 1. Check / Download yt-dlp (Only if missing or force)
        needs_ytdlp = force or not find_executable('yt-dlp')
        if needs_ytdlp:
            if callback:
                callback(0, 0, 0, "[INFO] Downloading standalone yt-dlp.exe from official release...")

            temp_ytdlp = ytdlp_dest + ".tmp"
            try:
                def on_ytdlp_prog(pct, dl, tot, lbl):
                    mb_dl = dl / (1024 * 1024)
                    mb_tot = tot / (1024 * 1024)
                    if callback:
                        callback(pct, dl, tot, f"[INFO] Downloading yt-dlp.exe: {pct:.1f}% ({mb_dl:.1f}/{mb_tot:.1f} MB)")

                download_file_with_progress(YTDLP_DOWNLOAD_URL, temp_ytdlp, "yt-dlp", on_ytdlp_prog)
                if os.path.isfile(ytdlp_dest):
                    try: os.remove(ytdlp_dest)
                    except Exception: pass
                os.replace(temp_ytdlp, ytdlp_dest)

                if callback:
                    callback(100, 0, 0, "[SUCCESS] yt-dlp.exe installed into native_host/bin/")
            except Exception as e:
                if os.path.isfile(temp_ytdlp):
                    try: os.remove(temp_ytdlp)
                    except Exception: pass
                raise RuntimeError(f"Failed to download yt-dlp: {e}")

        # 2. Check / Download FFmpeg (Only if missing or force)
        needs_ffmpeg = force or not find_executable('ffmpeg')
        if needs_ffmpeg:
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
        'version': '1.0.0',
        'python_version': sys.version.split()[0],
        'ytdlp_available': ytdlp_bin is not None,
        'ytdlp_path': ytdlp_bin,
        'ytdlp_version': get_version(ytdlp_bin) if ytdlp_bin else None,
        'ffmpeg_available': ffmpeg_bin is not None,
        'ffmpeg_path': ffmpeg_bin,
        'ffmpeg_version': get_version(ffmpeg_bin) if ffmpeg_bin else None,
        'bin_dir': get_bin_dir()
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


def handle_cancel():
    """
    Terminate currently executing download process.
    """
    global active_process
    with active_lock:
        if active_process and active_process.poll() is None:
            try:
                active_process.terminate()
            except Exception:
                try:
                    active_process.kill()
                except Exception:
                    pass
            active_process = None
            send_message({'status': 'log', 'line': '[INFO] Subprocess cancelled by user request.'})


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


def handle_download(payload):
    """
    Execute yt-dlp download and stream real-time logs / progress to extension.
    Auto-downloads binaries only if missing.
    """
    global active_process

    url = payload.get('url') or payload.get('pageUrl')
    if not url:
        send_message({'status': 'error', 'message': 'No media URL provided.'})
        return

    raw_type = str(payload.get('type') or payload.get('mediaType') or payload.get('targetType') or '').lower()
    target_format = str(payload.get('format', 'mp4')).lower()
    audio_formats = ('mp3', 'm4a', 'wav', 'flac', 'ogg', 'aac', 'opus')
    if raw_type == 'audio' or target_format in audio_formats:
        media_type = 'audio'
    else:
        media_type = 'video'
    folder_name = payload.get('downloadFolder', 'MaxsDownloads').strip() or 'MaxsDownloads'
    video_quality = payload.get('videoQuality', 'best')
    audio_quality = payload.get('audioQuality', 'best')
    custom_ytdlp = payload.get('customYtdlpPath')
    custom_ffmpeg = payload.get('customFfmpegPath')

    # Resolve output directory
    user_home = os.path.expanduser('~')
    output_dir = os.path.join(user_home, 'Downloads', folder_name)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        send_message({'status': 'error', 'message': f"Failed to create download folder: {e}"})
        return

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
    # Respect explicit isPlaylist boolean from extension.
    # Single video watch URLs (/watch?v=...) must ALWAYS download just that single video!
    is_playlist_req = payload.get('isPlaylist')
    url_lower = url.lower()

    if is_playlist_req is not None:
        is_playlist = bool(is_playlist_req)
    else:
        if '/watch' in url_lower or 'v=' in url_lower:
            is_playlist = False
        elif '/playlist' in url_lower or '/sets/' in url_lower or '/album/' in url_lower:
            is_playlist = True
        elif 'list=' in url_lower and 'list=ll' not in url_lower and 'list=wl' not in url_lower:
            is_playlist = True
        else:
            is_playlist = False

    # Output template: If playlist -> create dedicated folder named after Playlist Title
    if is_playlist:
        output_template = os.path.join(output_dir, '%(playlist_title|Playlist)s', '%(playlist_index)02d - %(title).150s.%(ext)s')
        playlist_args = ['--yes-playlist']
        send_message({'status': 'log', 'line': f"[INFO] Playlist mode active. Creating folder under ~/Downloads/{folder_name}/<Playlist_Name>/"})
    else:
        output_template = os.path.join(output_dir, '%(title).150s.%(ext)s')
        playlist_args = ['--no-playlist']

    ytdlp_cmd = [ytdlp_bin]
    cmd_args = list(ytdlp_cmd)
    cmd_args.extend([
        '--newline',
        '--no-colors',
        '--progress',
        '--progress-template', 'download-progress:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._total_bytes_str)s|%(info.playlist_index)s|%(info.n_entries)s|%(info.title)s',
        *playlist_args,
        '--ignore-errors',
        '--no-abort-on-error',
        '--compat-options', 'no-youtube-unavailable-videos',
        '--geo-bypass',
        '--no-check-certificates',
        '--extractor-retries', '10',
        '--sleep-interval', '1',
        '--retry-sleep', 'exp=1:10',
        '--windows-filenames',
        '--retries', '10',
        '--fragment-retries', '10',
        '--file-access-retries', '5',
        '-o', output_template
    ])

    # Browser authenticated cookies injection
    cookies_text = payload.get('cookiesText')
    cookies_file = None
    if cookies_text and isinstance(cookies_text, str) and len(cookies_text) > 30:
        try:
            temp_dir = tempfile.gettempdir()
            cookies_file = os.path.join(temp_dir, f"max_dl_cookies_{os.getpid()}_{int(time.time())}.txt")
            with open(cookies_file, 'w', encoding='utf-8') as f:
                f.write(cookies_text)
            cmd_args.extend(['--cookies', cookies_file])
            send_message({'status': 'log', 'line': '[INFO] Attached browser session authentication cookies.'})
        except Exception as e:
            send_message({'status': 'log', 'line': f'[WARN] Could not write session cookies: {e}'})

    if ffmpeg_bin:
        ffmpeg_dir = os.path.dirname(ffmpeg_bin) if ffmpeg_bin.endswith('.exe') else ffmpeg_bin
        cmd_args.extend(['--ffmpeg-location', ffmpeg_dir])

    if media_type == 'video':
        # Quality selector for video resolution (Highest available: 4K / 1080p / 720p)
        if video_quality == '4320p':
            format_spec = "bv*[height<=4320]+ba/b[height<=4320]/best"
        elif video_quality == '2160p':
            format_spec = "bv*[height<=2160]+ba/b[height<=2160]/best"
        elif video_quality == '1440p':
            format_spec = "bv*[height<=1440]+ba/b[height<=1440]/best"
        elif video_quality == '1080p':
            format_spec = "bv*[height<=1080]+ba/b[height<=1080]/best"
        elif video_quality == '720p':
            format_spec = "bv*[height<=720]+ba/b[height<=720]/best"
        elif video_quality == '480p':
            format_spec = "bv*[height<=480]+ba/b[height<=480]/best"
        elif video_quality == '360p':
            format_spec = "bv*[height<=360]+ba/b[height<=360]/best"
        elif video_quality == '240p':
            format_spec = "bv*[height<=240]+ba/b[height<=240]/best"
        else:
            format_spec = "bv*+ba/b"

        if target_format == 'gif':
            cmd_args.extend([
                '-f', format_spec,
                '--recode-video', 'gif'
            ])
        elif target_format in ('avi', 'wmv', 'flv', 'ts', '3gp', 'ogv'):
            cmd_args.extend([
                '-f', format_spec,
                '--recode-video', target_format
            ])
        else:
            cmd_args.extend([
                '-f', format_spec,
                '--merge-output-format', target_format
            ])

    elif media_type == 'audio':
        fmt = 'vorbis' if target_format == 'ogg' else target_format
        cmd_args.extend([
            '-f', 'bestaudio[ext=m4a]/bestaudio/140/251/250/249/18/ba/b',
            '-x',
            '--audio-format', fmt
        ])
        if audio_quality and audio_quality != 'best':
            bitrate_clean = audio_quality.replace('k', '')
            cmd_args.extend(['--audio-quality', bitrate_clean])

    # Target URL
    cmd_args.append(url)

    send_message({
        'status': 'log',
        'line': f"[INFO] Spawning yt-dlp: {cmd_args[0]} [target: {url}]"
    })

    # Regex patterns for fallback progress parsing
    progress_regex = re.compile(r'\[download\]\s+([\d\.]+)%\s+of\s+~?([\d\.]+\w+)\s+at\s+([\d\.]+\w+/s)\s+ETA\s+([\d:]+)')
    dest_regex = re.compile(r'\[(?:download|Merger|ExtractAudio)\]\s+(?:Destination:\s*|Merging formats into\s*"?)([^"\n\r]+)')
    ffmpeg_prog_regex = re.compile(r'frame=\s*(\d+).*time=\s*([\d:\.]+).*speed=\s*([\d\.]+x)')

    last_file = None
    accumulated_errors = []
    zero_items_detected = False
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

    def scan_dir_files(root_dir):
        if not os.path.isdir(root_dir):
            return set()
        res = set()
        for root, _, filenames in os.walk(root_dir):
            for f in filenames:
                res.add(os.path.join(root, f))
        return res

    # Snapshot files before execution recursively to detect newly created files
    files_before = scan_dir_files(output_dir)

    try:
        with active_lock:
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0x08000000

            active_process = subprocess.Popen(
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

        # Stream unbuffered stdout line by line
        for clean_line in read_unbuffered_lines(active_process):
            # Check for zero items
            if 'Downloading 0 items' in clean_line:
                zero_items_detected = True

            # Match item N of M in logs
            item_match = re.search(r'Downloading (?:item|video)\s+(\d+)\s+of\s+(\d+)', clean_line)
            if item_match:
                current_track_index = int(item_match.group(1))
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
                        current_track_index = int(parts[4].strip())
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
            active_process.stdout.close()
        except Exception:
            pass

        return_code = active_process.wait()

        with active_lock:
            active_process = None

        files_after = scan_dir_files(output_dir)
        new_files = list(files_after - files_before)

        if new_files or (last_file and os.path.isfile(last_file)):
            # Files were successfully written!
            resolved_target = new_files[0] if new_files else last_file
            if len(new_files) > 1:
                msg = f"Saved {len(new_files)} track(s) to playlist folder!"
            else:
                msg = f"Saved: {os.path.basename(resolved_target)}"

            send_message({
                'status': 'complete',
                'file': resolved_target,
                'message': msg
            })
        elif return_code == 0 and not zero_items_detected:
            send_message({
                'status': 'complete',
                'file': output_dir,
                'message': 'Download completed successfully!'
            })
        else:
            err_details = accumulated_errors[-1] if accumulated_errors else f"Process exited with code {return_code}"
            send_message({
                'status': 'error',
                'message': f"yt-dlp: {err_details}"
            })

    except Exception as e:
        with active_lock:
            active_process = None
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


def handle_cancel(message=None):
    """
    Terminates the active yt-dlp / FFmpeg process tree immediately.
    """
    global active_process
    with active_lock:
        if active_process is not None:
            pid = active_process.pid
            try:
                if sys.platform == 'win32':
                    # Terminate process and all child subprocesses (yt-dlp + ffmpeg)
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    active_process.kill()
            except Exception:
                try:
                    active_process.kill()
                except Exception:
                    pass
            active_process = None
            send_message({
                'status': 'error',
                'message': 'Download job cancelled by user.'
            })
        else:
            send_message({
                'status': 'log',
                'line': '[INFO] No active process to cancel.'
            })


def install_registry(extension_id=None):
    """
    Self-installer helper for Windows Chrome Native Messaging registration.
    Uses the fixed permanent Extension ID by default.
    """
    if sys.platform != 'win32':
        print("[!] Self-installation registry script is for Windows.")
        return

    import winreg

    # Permanent Extension ID from manifest.json fixed RSA key
    if not extension_id or extension_id == 'ALLOWED_EXTENSION_ID':
        extension_id = 'iabbelaamkcbkklcipbbkgegfenjhklc'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, 'com.maxsdownloader.host.json')
    bat_path = os.path.join(script_dir, 'run_host.bat')

    manifest_data = {
        "name": "com.maxsdownloader.host",
        "description": "Max's Downloader Native Messaging Host",
        "path": bat_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2)

    # Register in Windows Current User Registry for Chrome
    reg_key_path = r"Software\Google\Chrome\NativeMessagingHosts\com.maxsdownloader.host"
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key_path)
        winreg.SetValue(key, "", winreg.REG_SZ, manifest_path)
        winreg.CloseKey(key)
        print(f"[v] Successfully registered com.maxsdownloader.host in Windows Registry!")
        print(f"    Registry Key: HKCU\\{reg_key_path}")
        print(f"    Manifest: {manifest_path}")
        print(f"    Allowed Origin: chrome-extension://{extension_id}/")
    except Exception as e:
        print(f"[x] Registry installation failed: {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--install', '-i', 'install'):
        ext_id = sys.argv[2] if len(sys.argv) > 2 else None
        install_registry(ext_id)
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
    while True:
        message = read_message()
        if message is None:
            break

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
            handle_cancel()
        else:
            send_message({
                'status': 'error',
                'message': f"Unknown action: {action}"
            })


if __name__ == '__main__':
    main()
