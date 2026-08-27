# Finally that online downloader extension (FTODE)

> A minimalist, high-performance media stream sniffer and video/audio downloader for Google Chrome, Opera, Edge, Brave, and Mozilla Firefox powered by Python Native Messaging and `yt-dlp`.

---
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)
## ⚡ Overview

**Finally that online downloader extension (FTODE)** is a modern browser extension paired with a Python Native Messaging backend. It detects media streams in real-time across the web (including direct HTML5 media and adaptive HLS / DASH / YouTube / Vimeo / SoundCloud streams) and provides a sleek two-button download interface for the highest quality video and audio.

![Theme](https://img.shields.io/badge/Theme-Dark%20%7C%20Light%20Mode-6366f1)
![Browsers](https://img.shields.io/badge/Browsers-Chrome%20%7C%20Opera%20%7C%20Edge%20%7C%20Firefox-10b981)
![Manifest](https://img.shields.io/badge/Extension-Manifest%20V3-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
![Vibe Coded](https://img.shields.io/badge/Crafted%20with-Vibe%20Coding%20✨-ec4899)
![Zero-Setup](https://img.shields.io/badge/Binaries-Auto--Bootstrapped-10b981)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

> ✨ **Note:** This project is **~80% Vibe Coded** — crafted with modern agentic workflows, clean aesthetics, obsidian glassmorphism, and instant zero-friction usability.

---

## 📂 Project Hierarchy

```
Maxs-Downloader/
├── extension/
│   ├── manifest.json                    # Universal Manifest V3 specification
│   ├── theme-init.js                    # Zero-flash instant Dark/Light theme initializer
│   ├── popup.html                       # Modern popup interface
│   ├── popup.css                        # Obsidian glassmorphism & responsive styles
│   ├── popup.js                         # Dynamic stream controller & live download manager
│   ├── options.html                     # Full settings, diagnostics & host manager
│   ├── options.css                      # Settings design system & dual-theme tokens
│   ├── options.js                       # Preference persistence & tool auto-updater
│   ├── background.js                    # Dual-pass media sniffer & native messaging bridge
│   ├── content.js                       # DOM media inspector & title sanitizer (Pass 1)
│   └── icons/                           # High-res logos & engine branding assets
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
├── build.bat                            # 1-Click release packager launcher
├── build.py                             # Automated release zip packaging tool
└── setup.bat                            # 1-Click root setup launcher
```

---

## ✨ Features & Architecture

### 1. Zero Manual Software Installation (Self-Bootstrapping)
* **Prepackaged & Auto-Downloaded Tools:** You do **not** need to manually install or configure `yt-dlp` or `FFmpeg` on your system.
* **Auto-Installer:** The Python Native Host automatically downloads the latest official Windows standalone releases of `yt-dlp.exe`, `ffmpeg.exe`, and `ffprobe.exe` directly into `native_host/bin/` if not present.
* **1-Click Update from Options UI:** Click the "Check for Updates" button in the extension settings at any time to upgrade to the latest versions with a live progress bar.

### 2. Dual-Pass Media Sniffing Engine
* **Pass 1 (DOM Inspector - `content.js`):**
  * Continuously scans `<video>` and `<audio>` elements, `src`, `currentSrc`, `<source>` tags, and video posters.
  * Reactive `MutationObserver` and playback event hooks (`play`, `playing`, `loadstart`) catch dynamically injected web players.
  * Detects popular streaming platforms (YouTube, Vimeo, SoundCloud, Twitch, TikTok, Twitter/X, Reddit, Dailymotion, Bilibili, etc.) and supports Single Page Application (SPA) navigation.
  * Cleans SponsorBlock titles, junk tags, and platform suffixes automatically.
* **Pass 2 (Network Interceptor - `background.js`):**
  * Intercepts media responses via `chrome.webRequest.onHeadersReceived` matching MIME types (`video/*`, `audio/*`, `application/vnd.apple.mpegurl`, `application/dash+xml`) and extensions (`.mp4`, `.webm`, `.mp3`, `.m3u8`, `.mpd`, `.flac`, `.opus`, etc.).
  * Updates toolbar badge in real-time (`VID` green / `AUD` cyan / `LIST` purple).

### 3. Modern UI & Dynamic Interface

#### 🌗 Dual Theme Support (Dark & Light)
* **Obsidian Dark Theme:** Deep obsidian `#12171d` background, slate glass cards `#1f2732`, crisp borders, and glowing accents.
* **Clean Light Theme:** Soft slate `#f1f5f9` background, pure white `#ffffff` cards, and high-contrast typography.
* **Zero Theme Flashing:** `theme-init.js` immediately applies user preferences before DOM render to eliminate flicker.

#### 🎛️ Interactive Extension Popup (`popup.html`)
* **Detection Status Card:** Displays real-time detection status (`Video Stream Detected`, `Audio Stream Detected`, `Playlist Detected`), cleaned media title, and source website domain.
* **Two Primary Pill Action Buttons:**
  * `Download [Video Format]` (Emerald green accent, e.g. `Download MP4` / `Download WEBM`)
  * `Download [Audio Format]` (Amber gold accent, e.g. `Download MP3` / `Download FLAC`)
* **Live Download Progress & Metrics:** Real-time percentage fill bar, transfer speed (MB/s), ETA countdown, and an inline `Cancel Download` button.
* **Detected Streams Accordion:** Collapsible stream inspector showing individual resolutions, bitrates, and direct stream links.
* **Embedded Console Terminal:** Collapsible live terminal window displaying unbuffered `yt-dlp` logs with 1-click **Copy** and **Clear** controls.
* **Live Status Footer Chips:** Displays real-time host connectivity (`Host: Ready`) and destination directory chip (`Folder: FTODE`).
* **Host Setup Alert Banner:** Non-intrusive warning alert that appears only if the local Python Native Host needs registration.

#### ⚙️ Settings & Host Management (`options.html`)
* **Interactive Header:** Live version badge, animated Ko-fi support button with playful wiggle animation, and Dark/Light mode toggle switch.
* **Media Format & Quality Pickers:** Configure target video formats (`MP4`, `WEBM`, `MKV`, `MOV`, `AVI`, `FLV`, `GIF`), video resolutions (up to 8K), audio formats (`MP3`, `M4A`, `FLAC`, `WAV`, `OPUS`, `OGG`, `AAC`, `ALAC`), and bitrates (up to 320 kbps).
* **Storage & Collision Handling:** Custom relative download folder name (inside `~/Downloads/`) and duplicate file actions (`Download Again (Copy)`, `Skip`, `Overwrite`).
* **Console Streaming Toggle:** Easily enable or disable inline terminal output in the popup.
* **Native Host Diagnostics:** Live status bubble, connectivity tester, Extension ID copy tool, and detected tool versions.
* **Self-Bootstrapping Engine Manager:** 1-Click "Check for Updates" button with an animated progress bar.
* **Floating Toast Feedback:** Centered floating toast alerts confirming saved preferences.
* **Subtle Footer Credits:** Clean attribution to **MaxAkt**, open-source dependencies, and GPL-3.0.

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

## 📦 Building & Packaging Releases

To package the project into a clean, branded release ZIP file for sharing with others:

1. Double-click **`build.bat`** (or run `python build.py`).
2. The packager will create clean zip archives inside the **`dist/`** directory:
   * **`FTODE-v1.0.0-Release.zip`**: Streamlined release bundle (~475 KB) containing exactly **4 items**:
     * `FTODE Host Setup.exe` (1-Click installer for Host backend with embedded **FTODE Logo Icon**)
     * `FTODE Host Uninstall.exe` (1-Click uninstaller for Host backend with embedded **FTODE Logo Icon**)
     * `FTODE-Extension.zip` (Universal single-file extension package for Chrome, Edge, Opera, and Firefox)
     * `Instructions.txt` (Clear 2-step setup & uninstall instructions)
   * **`FTODE-Extension-v1.0.0.zip`**: Standalone extension archive ready for direct upload to the Chrome Web Store Developer Dashboard or Firefox AMO.

---

## 🗑️ Uninstallation

1. **Remove Extension from Browser:** Right-click the FTODE icon in your browser toolbar and click **"Remove from Chrome"** / **"Remove from Edge"** / **"Remove Extension"**.
2. **Remove Native Host Backend:** Double-click **`FTODE Host Uninstall.exe`**, which cleanly deregisters all browser registry keys and removes the local backend directory.

---

## 💖 Credits & Acknowledgements

**FTODE** is built with modern vibe coding workflows and powered by open-source foundations:

* **Creator & Developer:** **MaxAkt**
* **Core Media Engines:**
  * **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — Universal media stream extraction and downloading engine.
  * **[FFmpeg](https://ffmpeg.org)** & **[ffprobe](https://ffmpeg.org)** — Multimedia multiplexing, format conversion, and GIF creation framework.
* **Typography:** [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans) & [Outfit](https://fonts.google.com/specimen/Outfit).

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for details.

