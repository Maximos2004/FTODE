<div align="center">

<img src="assets/logo.png" alt="FTODE Logo" width="128" height="128">

# Finally That Online Downloader Extension (FTODE)

**A modern 1-click video and audio downloader browser extension powered by Python & yt-dlp.**

![Manifest](https://img.shields.io/badge/Extension-Manifest%20V3-6366f1)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux-blue)
![Browsers](https://img.shields.io/badge/Browsers-Chrome%20%7C%20Edge%20%7C%20Opera%20%7C%20Firefox-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

<br>

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)

<br><br>

<img src="assets/showcase-video-download.gif" alt="1-Click Video Download Showcase" width="750">

*Effortless 1-click downloads with live speed, progress percentage, and console output.*

</div>

---

## ✨ Features & Visual Tour

### 🎵 1-Click Audio & Music Extraction
Turn any video or music track into high-fidelity audio files (MP3, FLAC, WAV, OPUS) with one click.

<p align="center">
  <img src="assets/showcase-audio-download.gif" alt="Audio Download Showcase" width="750">
</p>

---

### 📋 Full Playlist & Batch Downloads
Download entire YouTube playlists or music albums sequentially with live queue tracking.

<p align="center">
  <img src="assets/showcase-playlist-download.gif" alt="Playlist Download Showcase" width="750">
</p>

---

### 🌐 Universal Multi-Site Support
Download from **SoundCloud, Vimeo, Twitch, Reddit, Twitter/X, Dailymotion**, and hundreds of other supported platforms.

<p align="center">
  <img src="assets/showcase-other-sites-download.gif" alt="SoundCloud and Multi-Site Showcase" width="750">
</p>

---

### ⚙️ Powerful Customization
Tailor the downloader to your exact workflow:
- **Video Formats & Quality:** MP4, WEBM, MKV, GIF up to 8K resolution.
- **Audio Formats & Bitrates:** MP3 (320kbps), FLAC (lossless), WAV, OPUS, AAC.
- **Custom Save Directories:** Choose any destination directory or drive on your machine.
- **1-Click Updates:** Easily keep `yt-dlp` and `ffmpeg` up to date with a single click.

<p align="center">
  <img src="assets/showcase-settings.gif" alt="Settings Showcase" width="750">
</p>

---

## 🚀 How to Install

### What you need:
- **Windows 10/11** or **Linux**
- A Browser (**Chrome**, **Edge**, **Brave**, **Opera / Opera GX**, or **Firefox**)
- **Python 3.8+** installed:
  - **Windows:** Download from [python.org](https://www.python.org/downloads/) *(Make sure to check "Add Python to PATH")*
  - **Linux:** Comes pre-installed on most distros, or install with `sudo apt install python3 ffmpeg` / `sudo pacman -S python ffmpeg`

---

### Step 1: Add Extension to your Browser
1. Open your browser extensions page:
   - **Chrome / Chromium / Brave:** `chrome://extensions`
   - **Edge:** `edge://extensions`
   - **Opera / Opera GX:** `opera://extensions`
   - **Firefox:** `about:debugging#/runtime/this-firefox`
2. Turn on **Developer mode** (top right switch).
3. Load the extension:
   - **Chrome / Opera / Edge / Brave:** Click **Load unpacked** and select the `extension` folder (or drag & drop `FTODE-Extension-Chrome.zip`).
   - **Firefox:** Click **Load Temporary Add-on...** and select `manifest.firefox.json` in the `extension` folder (or select `FTODE-Extension-Firefox.zip`).
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
3. Click **Download MP4**, **Download MP3**, or **Download Playlist**.
4. The files will be saved in your `Downloads/FTODE` folder!

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

If you like this project, feel free to support me :> :

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)

- **Made by:** MaxAkt
- **AI Disclosure:** This project was developed with the help of AI coding assistance.
- **Powered by:**
  - [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Media downloader
  - [FFmpeg](https://ffmpeg.org) — Audio/Video converter

---

## 📄 License

This project is open-source under the [GNU General Public License v3.0 (GPLv3)](LICENSE).
