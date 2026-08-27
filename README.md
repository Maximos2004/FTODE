# Finally That Online Downloader Extension (FTODE)

A simple browser extension + Python backend that lets you download video and audio from almost any website (YouTube, SoundCloud, Vimeo, Twitch, Reddit, and more) with 1 click.

![Manifest](https://img.shields.io/badge/Extension-Manifest%20V3-6366f1)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux-blue)
![Browsers](https://img.shields.io/badge/Browsers-Chrome%20%7C%20Edge%20%7C%20Opera%20%7C%20Firefox-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)

---

## ✨ Features

- **1-Click Downloads:** Download video (MP4/WEBM/MKV) or music (MP3/FLAC/WAV) with a single click.
- **Zero Setup for Tools:** You don't need to manually install `yt-dlp` or `ffmpeg`. The setup script gets them for you automatically!
- **Auto Stream Detection:** Detects videos playing on the page and direct stream links.
- **Dark & Light Mode:** Looks clean and matches your style.
- **Customizable:** Change download formats, quality (up to 8K), and choose where your files get saved.
- **Live Progress:** Shows download speed, percentage, and ETA in the popup.

---

## 🚀 How to Install

### What you need:
- **Windows 10/11** or **Linux**
- **Python 3.8+** installed:
  - **Windows:** Download from [python.org](https://www.python.org/downloads/) *(Make sure to check "Add Python to PATH")*
  - **Linux:** Comes pre-installed on most distros, or install with `sudo apt install python3 ffmpeg` / `sudo pacman -S python ffmpeg`

---

### Step 1: Add Extension to your Browser
1. Open your browser extensions page:
   - **Chrome / Chromium / Brave:** `chrome://extensions`
   - **Edge:** `edge://extensions`
   - **Opera:** `opera://extensions`
   - **Firefox:** `about:debugging#/runtime/this-firefox`
2. Turn on **Developer mode** (top right switch).
3. Click **Load unpacked** (or "Load Temporary Add-on" in Firefox) and select the `extension` folder from this repo.
4. Pin the extension to your toolbar so you can click it easily.

---

### Step 2: Run Setup
- **Windows:** Double-click **`setup.bat`**
- **Linux:** Open a terminal in this folder and run **`bash setup.sh`**

It will connect the extension with Python and make sure `yt-dlp` and `ffmpeg` are ready. Done!

---

### Step 3: Download Stuff!
1. Go to any video or music page (YouTube, Vimeo, SoundCloud, etc.).
2. Click the **FTODE** icon in your toolbar.
3. Click **Download MP4** or **Download MP3**.
4. The file will be saved in your `Downloads/FTODE` folder!

---

## ⚙️ Settings

Right-click the extension icon and choose **Options** (or click the gear icon in the popup):
- Pick your preferred video quality & format (MP4, WEBM, MKV, GIF, etc.).
- Pick your preferred audio format (MP3, FLAC, WAV, OPUS, etc.).
- Set a custom download folder (like `D:\Downloads\FTODE` or `~/Videos/FTODE`).
- Click "Check for Updates" to update `yt-dlp` and `ffmpeg` anytime.

---

## 🗑️ How to Uninstall

1. Run the uninstaller:
   - **Windows:** Double-click **`uninstall.bat`**
   - **Linux:** Run **`bash uninstall.sh`**
2. Right-click the extension icon in your browser and click **Remove from Chrome/Firefox**.

---

## 📦 Building Releases (Optional)

If you want to package the project into zip files to share:
- Run **`build.bat`** (or `python build.py`).
- It automatically creates 2 standalone release bundles in `dist/`:
  - **`FTODE-v1.0.1-Windows.zip`** (for Windows users)
  - **`FTODE-v1.0.1-Linux.zip`** (for Linux users)
  - **`FTODE-Extension-v1.0.1.zip`** (universal extension)

---

## 💖 Credits & Support

If you like this project, feel free to support it:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)

- **Made by:** MaxAkt
- **Powered by:**
  - [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Media downloader
  - [FFmpeg](https://ffmpeg.org) — Audio/Video converter

---

## 📄 License

This project is open-source under the [GNU General Public License v3.0 (GPLv3)](LICENSE).
