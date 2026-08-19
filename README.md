# Finally that online downloader extension (FTODE)

> A minimalist, high-performance media stream sniffer and video/audio downloader for Google Chrome, Opera, Edge, Brave, and Mozilla Firefox powered by Python Native Messaging and `yt-dlp`.

---
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)
## ⚡ Overview

**Finally that online downloader extension (FTODE)** is a modern browser extension paired with a Python Native Messaging backend. It detects media streams in real-time across the web (including direct HTML5 media and adaptive HLS / DASH / YouTube / Vimeo / SoundCloud streams) and provides a sleek two-button download interface for the highest quality video and audio.

![Theme](https://img.shields.io/badge/Theme-Obsidian%20Dark-6366f1)
![Browsers](https://img.shields.io/badge/Browsers-Chrome%20%7C%20Opera%20%7C%20Edge%20%7C%20Firefox-10b981)
![Manifest](https://img.shields.io/badge/Extension-Manifest%20V3-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
![Vibe Coded](https://img.shields.io/badge/Crafted%20with-Vibe%20Coding%20✨-ec4899)
![Zero-Setup](https://img.shields.io/badge/Binaries-Auto--Bootstrapped-10b981)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

> ✨ **Note:** This project is **100% Vibe Coded** — crafted with modern agentic workflows, clean aesthetics, obsidian glassmorphism, and instant zero-friction usability.

---

## 📂 Project Hierarchy

```
Maxs-Downloader/
├── extension/
│   ├── manifest.json                    # Universal Manifest V3 specification
│   ├── popup.html                       # Sleek obsidian dark UI
│   ├── popup.css                        # Polished styling & animations
│   ├── popup.js                         # UI controller & live stream log renderer
│   ├── options.html                     # Settings & host diagnostics page
│   ├── options.css                      # Options layout & design tokens
│   ├── options.js                       # Storage sync & host connectivity tester
│   ├── background.js                    # Dual-pass sniffer & native messaging manager
│   ├── content.js                       # DOM media inspector (Pass 1)
│   └── icons/                           # High-res icons (16, 32, 48, 128)
├── native_host/
│   ├── host.py                          # Python Native Messaging protocol handler
│   ├── run_host.bat                     # Windows stdio launcher wrapper
│   ├── com.ftode.host.json              # Chromium native host manifest
│   ├── com.ftode.host-firefox.json      # Firefox native host manifest
│   ├── install_host.bat                 # 1-Click Multi-Browser Windows installer
│   ├── install_host.ps1                 # PowerShell installer script
│   └── bin/                             # Prepackaged / auto-downloaded binaries
│       ├── yt-dlp.exe
│       ├── ffmpeg.exe
│       └── ffprobe.exe
└── setup.bat                            # 1-Click setup root launcher
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
  * Cleans SponsorBlock titles, junk tags, and platform suffixes automatically.
* **Pass 2 (Network Interceptor - `background.js`):**
  * Intercepts media responses via `chrome.webRequest.onHeadersReceived` matching MIME types (`video/*`, `audio/*`, `application/vnd.apple.mpegurl`, `application/dash+xml`) and extensions (`.mp4`, `.webm`, `.mp3`, `.m3u8`, `.mpd`, `.flac`, `.opus`, etc.).
  * Updates toolbar badge in real-time (`VID` green / `AUD` cyan / `LIST` purple).

### 3. Sleek Obsidian UI & Dynamic Actions
* **Obsidian Dark Aesthetic:** Deep obsidian `#0f1117`, slate cards `#1a1d27`, crisp glowing accents (`#6366f1` Indigo, `#10b981` Emerald, `#06b6d4` Cyan).
* **Detection Status Header:** Real-time badge indicating `"Video Stream Detected"`, `"Audio Stream Detected"`, `"Playlist Detected"`, or `"No Media Detected"`.
* **Two Primary Action Buttons:**
  * `Download [Video Format]` (e.g., `Download MP4` / `Download WEBM`)
  * `Download [Audio Format]` (e.g., `Download MP3` / `Download FLAC`)
* **Live Terminal Stream:** Inline collapsible console showing unbuffered real-time `yt-dlp` logs, download percentage, speed (MB/s), ETA, and FFmpeg remuxing logs.

---

## 🚀 Quick Start & Installation

### Prerequisites
* **Python 3.8+** installed on Windows.

---

### Step 1: Load the Extension into Your Browser

#### 🌐 For Chrome, Opera, Opera GX, Edge, Brave, Vivaldi:
1. Open your browser and navigate to the extensions page:
   - **Chrome:** `chrome://extensions/`
   - **Opera / Opera GX:** `opera://extensions/`
   - **Edge:** `edge://extensions/`
   - **Brave:** `brave://extensions/`
2. Turn ON **Developer mode** (toggle in top-right or top-left corner).
3. Click **Load unpacked** (or *Load extension*) and select the `Maxs-Downloader/extension` folder.
*(The extension automatically uses a permanent, fixed ID: `iabbelaamkcbkklcipbbkgegfenjhklc`).*

#### 🦊 For Mozilla Firefox, Floorp, LibreWolf, Waterfox:
1. In Firefox, navigate to: `about:debugging#/runtime/this-firefox`
2. Click **"Load Temporary Add-on..."**
3. Select the `Maxs-Downloader/extension/manifest.json` file.

---

### Step 2: Run 1-Click Automatic Setup
Double-click **`setup.bat`** in the root project folder (or run `install_host.bat` inside `native_host/`).

*(This automatically registers the Native Host across Windows Registry for **Chrome, Opera, Edge, Brave, and Firefox** simultaneously AND bootstraps the latest `yt-dlp` and `FFmpeg` binaries into `native_host/bin/` if missing. Zero manual command-line configuration required!).*

---

### Step 3: Test & Download!
1. Open any media page (e.g., YouTube, SoundCloud, Vimeo, TikTok, direct MP4/MP3).
2. Click the **FTODE** icon in your browser toolbar.
3. Click **Download MP4** or **Download MP3**.
4. Files are saved directly to `~/Downloads/FTODE/`!

---

## ⚙️ Configuration & Options

Access the Options page by clicking the **Gear** icon in the popup or right-clicking the extension icon -> **Options**:
* **Video Formats:** `MP4`, `WEBM`, `MKV`, `MOV`, `AVI`, `FLV`, `GIF` (Animated GIF).
* **Video Resolutions:** `Best Available (up to 8K)`, `8K (4320p)`, `4K (2160p)`, `2K (1440p)`, `1080p (Full HD)`, `720p (HD)`, `480p`, `360p`, `240p`.
* **Audio Formats:** `MP3`, `M4A (AAC)`, `FLAC (Lossless)`, `WAV (PCM)`, `OPUS`, `OGG (Vorbis)`, `AAC`, `ALAC (Apple Lossless)`.

* **Audio Bitrates:** `Best Available`, `320 kbps (Extreme)`, `256 kbps`, `192 kbps`, `160 kbps`, `128 kbps`, `96 kbps (Voice/Podcast)`, `64 kbps (Data Saver)`.
* **Download Directory:** Custom relative folder inside Downloads (default: `FTODE`).
* **Live Debug Console:** Toggle inline terminal stream.
* **Auto-Installer / Updater:** 1-Click button to check for updates or download tools.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for details.
