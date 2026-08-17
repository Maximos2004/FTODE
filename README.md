# Max's Downloader

> A minimalist, high-performance media stream sniffer and video/audio downloader for Google Chrome powered by Python Native Messaging and `yt-dlp`.

---
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)
## ⚡ Overview

**Max's Downloader** is a modern Chrome Manifest V3 extension paired with a Python Native Messaging backend. It detects media streams in real-time across the web (including direct HTML5 media and adaptive HLS / DASH / YouTube / Vimeo streams) and provides a two-button download interface for the highest quality video and audio.

![Theme](https://img.shields.io/badge/Theme-Obsidian%20Dark-6366f1)
![Manifest](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
![Zero-Setup](https://img.shields.io/badge/Binaries-Auto--Bootstrapped-10b981)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## 📂 Project Hierarchy

```
Maxs-Downloader/
├── extension/
│   ├── manifest.json            # Chrome Manifest V3 specification
│   ├── popup.html               # Sleek obsidian dark UI
│   ├── popup.css                # Polished styling & animations
│   ├── popup.js                 # UI controller & live stream log renderer
│   ├── options.html             # Settings & host diagnostics page
│   ├── options.css              # Options layout & design tokens
│   ├── options.js               # Storage sync & host connectivity tester
│   ├── background.js            # Dual-pass sniffer & native messaging manager
│   ├── content.js               # DOM media inspector (Pass 1)
│   └── icons/                   # High-res icons (16, 32, 48, 128)
└── native_host/
    ├── host.py                  # Python Native Messaging protocol handler
    ├── run_host.bat             # Chrome stdio launcher wrapper
    ├── com.maxsdownloader.host.json # Native messaging host manifest
    ├── install_host.bat         # 1-Click Windows installer
    ├── install_host.ps1         # PowerShell installer script
    └── bin/                     # Prepackaged / auto-downloaded binaries
        ├── yt-dlp.exe
        ├── ffmpeg.exe
        └── ffprobe.exe
```

---

## ✨ Features & Architecture

### 1. Zero Manual Software Installation (Self-Bootstrapping)
* **Prepackaged & Auto-Downloaded Tools:** You do **not** need to manually download or configure `yt-dlp` or `FFmpeg` on your system.
* **Auto-Installer:** The Python Native Host automatically downloads the latest official Windows standalone releases of `yt-dlp.exe`, `ffmpeg.exe`, and `ffprobe.exe` directly into `native_host/bin/` if not present.
* **1-Click Update from Options UI:** Click the "Auto-Install / Update yt-dlp & FFmpeg" button in the extension settings at any time to upgrade to the latest versions.

### 2. Dual-Pass Media Sniffing Engine
* **Pass 1 (DOM Inspector - `content.js`):**
  * Continuously scans `<video>` and `<audio>` elements, `src`, `currentSrc`, `<source>` tags, and video posters.
  * Reactive `MutationObserver` and playback event hooks (`play`, `playing`, `loadstart`) catch dynamically injected web players.
  * Detects popular streaming platforms (YouTube, Vimeo, SoundCloud, Twitch, TikTok, Twitter/X, Reddit, Dailymotion, Bilibili, etc.) and supports Single Page Application (SPA) navigation.
* **Pass 2 (Network Interceptor - `background.js`):**
  * Intercepts media responses via `chrome.webRequest.onHeadersReceived` matching MIME types (`video/*`, `audio/*`, `application/vnd.apple.mpegurl`, `application/dash+xml`) and extensions (`.mp4`, `.webm`, `.mp3`, `.m3u8`, `.mpd`, `.flac`, `.opus`, etc.).
  * Updates Chrome toolbar badge in real-time (`VID` green / `AUD` cyan).

### 3. Sleek Obsidian UI & Dynamic Actions
* **Obsidian Dark Aesthetic:** Deep obsidian `#0f1117`, slate cards `#1a1d27`, crisp glowing accents (`#6366f1` Indigo, `#10b981` Emerald, `#06b6d4` Cyan).
* **Detection Status Header:** Real-time badge indicating `"Video Detected"`, `"Audio Detected"`, or `"No Media Detected"`.
* **Two Primary Action Buttons:**
  * `Download [Video Format]` (e.g., `Download MP4` / `Download WEBM`)
  * `Download [Audio Format]` (e.g., `Download MP3` / `Download FLAC`)
* **Live Terminal Stream:** Inline collapsible console showing unbuffered real-time `yt-dlp` logs, download percentage, speed (MB/s), ETA, and FFmpeg remuxing logs.

---

## 🚀 Quick Start & Installation

### Prerequisites
* **Python 3.8+** installed on Windows.

### Step 1: Load the Chrome Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** (top-right corner).
3. Click **Load unpacked** and select the `Maxs-Downloader/extension` folder.
*(The extension automatically uses a permanent, fixed ID: `iabbelaamkcbkklcipbbkgegfenjhklc`).*

### Step 2: Run 1-Click Automatic Setup
Double-click **`setup.bat`** in the root project folder.
*(This automatically registers the Native Host in Windows Registry AND downloads the latest `yt-dlp` and `FFmpeg` binaries into `native_host/bin/` if missing. Zero manual configuration required!).*

### Step 3: Test & Download!
1. Open any media page (e.g., YouTube, Vimeo, direct MP4/MP3).
2. Click the **Max's Downloader** icon in your Chrome toolbar.
3. Click **Download MP4** or **Download MP3**.
4. Files are saved directly to `~/Downloads/MaxsDownloads/`!

---

## ⚙️ Configuration & Options

Access the Options page by clicking the **Gear** icon in the popup or right-clicking the extension icon -> **Options**:
* **Video Formats:** `MP4`, `WEBM`, `MKV`, `MOV`, `AVI`, `WMV`, `FLV`, `TS`, `3GP`, `OGV`, `GIF` (Animated GIF).
* **Video Resolutions:** `Best Available (up to 8K)`, `8K (4320p)`, `4K (2160p)`, `2K (1440p)`, `1080p (Full HD)`, `720p (HD)`, `480p`, `360p`, `240p`.
* **Audio Formats:** `MP3`, `M4A (AAC)`, `FLAC (Lossless)`, `WAV (PCM)`, `OPUS`, `OGG (Vorbis)`, `AAC`, `ALAC (Apple Lossless)`, `WMA`, `AIFF`, `AC3 (Dolby)`, `MP2`.
* **Audio Bitrates:** `Best Available`, `320 kbps (Extreme)`, `256 kbps`, `192 kbps`, `160 kbps`, `128 kbps`, `96 kbps (Voice/Podcast)`, `64 kbps (Data Saver)`.
* **Download Directory:** Custom relative folder inside Downloads (default: `MaxsDownloads`).
* **Live Debug Console:** Toggle inline terminal stream.
* **Auto-Installer / Updater:** 1-Click button to check for updates or download tools.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for details.

