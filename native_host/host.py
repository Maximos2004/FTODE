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
        if 'youtube.com' in host or 'youtu.be' in host:
            if path in ('/watch', '/embed') or path.startswith(('/shorts/', '/live/')):
                return False
            if path == '/playlist' and 'list=' in search:
                return False
            if (
                path in ('/', '') or
                path.startswith(('/feed', '/channel', '/c/', '/user/', '/@')) or
                path in ('/results', '/gaming', '/explore', '/trending')
            ):
                return True
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

    log_debug(f"DOWNLOAD PAYLOAD: {json.dumps(payload)}")

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
    existing_file_action = str(payload.get('existingFileAction', 'copy')).lower()
    custom_ytdlp = payload.get('customYtdlpPath')
    custom_ffmpeg = payload.get('customFfmpegPath')
    title_hint = payload.get('title')

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
    is_playlist_req = payload.get('isPlaylist')
    url_lower = url.lower()

    if is_playlist_req is True:
        is_playlist = True
    elif '/playlist' in url_lower or '/sets/' in url_lower or '/album/' in url_lower or ('list=' in url_lower and 'list=ll' not in url_lower and 'list=wl' not in url_lower and '/watch' not in url_lower and 'v=' not in url_lower):
        is_playlist = True
    elif is_playlist_req is False:
        is_playlist = False
    else:
        is_playlist = False

    # Output template & Duplicate Handling
    if is_playlist:
        output_template = os.path.join(output_dir, '%(playlist_title,playlist,album|Playlist)s', '%(playlist_index,autonumber)02d - %(title).150s.%(ext)s')
        playlist_args = ['--yes-playlist']
        send_message({'status': 'log', 'line': f"[INFO] Playlist mode active. Saving to ~/Downloads/{folder_name}/<Playlist_Name>/"})
    else:
        playlist_args = ['--no-playlist']
        if existing_file_action == 'copy' and title_hint and title_hint not in ('Media Download', 'Media Stream', 'No media detected'):
            safe_title = sanitize_filename(title_hint)
            existing_files = os.listdir(output_dir) if os.path.isdir(output_dir) else []
            base_matches = [f for f in existing_files if f.startswith(safe_title) and not f.endswith('.part') and not f.endswith('.ytdl')]
            if base_matches:
                copy_idx = 1
                while any(f.startswith(f"{safe_title} ({copy_idx})") for f in existing_files):
                    copy_idx += 1
                output_template = os.path.join(output_dir, f"%(title).150s ({copy_idx}).%(ext)s")
                send_message({'status': 'log', 'line': f"[INFO] File '{safe_title}' already exists. Creating copy '({copy_idx})'."})
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
        '--extractor-args', 'youtube:player_client=default,web_embedded,web,android,mweb,ios',
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
    # Do NOT inject cookies for YouTube URLs by default to prevent YouTube's SABR / TV 360p downgrade!
    cookies_text = payload.get('cookiesText')
    cookies_file = None
    is_yt = 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

    if cookies_text and isinstance(cookies_text, str) and len(cookies_text) > 30 and not is_yt:
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

        if target_res:
            cmd_args.extend(['--format-sort', f"res:{target_res},fps,br"])
        else:
            cmd_args.extend(['--format-sort', "res,fps,br"])

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
            '-f', 'bestaudio/best',
            '-x',
            '--audio-format', fmt
        ])
        if audio_quality and audio_quality != 'best':
            bitrate_clean = audio_quality.replace('k', '')
            cmd_args.extend(['--audio-quality', bitrate_clean])
        else:
            cmd_args.extend(['--audio-quality', '0'])

    # Target URL
    cmd_args.append(url)

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
                skip_info = f" ({skipped_already_exists} skipped - already downloaded)" if skipped_already_exists > 0 else ""
                msg = f"Saved {len(new_files)} track(s) to playlist folder!{skip_info}"
            else:
                msg = f"Saved: {os.path.basename(resolved_target)}"

            send_message({
                'status': 'complete',
                'file': resolved_target,
                'message': msg
            })
        elif skipped_already_exists > 0 or (return_code == 0 and not zero_items_detected):
            skip_msg = f"Completed! {skipped_already_exists} file(s) already existed in folder and were skipped." if skipped_already_exists > 0 else "Download completed successfully!"
            send_message({
                'status': 'complete',
                'file': output_dir,
                'message': skip_msg
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
    chrome_manifest_path = os.path.join(script_dir, 'com.maxsdownloader.host.json')
    firefox_manifest_path = os.path.join(script_dir, 'com.maxsdownloader.host-firefox.json')
    bat_path = os.path.join(script_dir, 'run_host.bat')

    # 1. Chrome / Chromium Manifest
    chrome_manifest_data = {
        "name": "com.maxsdownloader.host",
        "description": "Max's Downloader Native Messaging Host",
        "path": bat_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }
    with open(chrome_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(chrome_manifest_data, f, indent=2)

    # 2. Mozilla Firefox Manifest
    firefox_manifest_data = {
        "name": "com.maxsdownloader.host",
        "description": "Max's Downloader Native Messaging Host",
        "path": bat_path,
        "type": "stdio",
        "allowed_extensions": [
            "maxs-downloader@maxakt.local"
        ]
    }
    with open(firefox_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(firefox_manifest_data, f, indent=2)

    # Register in Windows Current User Registry across all supported browsers
    reg_keys = [
        (r"Software\Google\Chrome\NativeMessagingHosts\com.maxsdownloader.host", "Google Chrome", chrome_manifest_path),
        (r"Software\Microsoft\Edge\NativeMessagingHosts\com.maxsdownloader.host", "Microsoft Edge", chrome_manifest_path),
        (r"Software\Chromium\NativeMessagingHosts\com.maxsdownloader.host", "Chromium / Opera / Brave", chrome_manifest_path),
        (r"Software\Mozilla\NativeMessagingHosts\com.maxsdownloader.host", "Mozilla Firefox", firefox_manifest_path)
    ]
    for reg_key_path, browser_name, m_path in reg_keys:
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key_path)
            winreg.SetValue(key, "", winreg.REG_SZ, m_path)
            winreg.CloseKey(key)
            print(f"[v] Successfully registered for {browser_name} in Windows Registry!")
            print(f"    Registry Key: HKCU\\{reg_key_path}")
        except Exception as e:
            print(f"[x] Registry installation failed for {browser_name}: {e}")

    print(f"    Chrome Manifest: {chrome_manifest_path}")
    print(f"    Firefox Manifest: {firefox_manifest_path}")
    print(f"    Allowed Origin: chrome-extension://{extension_id}/")
    print(f"    Gecko Extension ID: maxs-downloader@maxakt.local")


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
    log_debug("HOST PROCESS STARTED (listening for messages)")
    while True:
        message = read_message()
        if message is None:
            log_debug("HOST STDIN CLOSED (exiting)")
            break

        log_debug(f"MESSAGE RECEIVED: {json.dumps(message)}")
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
