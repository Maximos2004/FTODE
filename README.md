# Finally That Online Downloader Extension (FTODE)

A simple browser extension + Python backend that lets you download video and audio from almost any website (YouTube, SoundCloud, Vimeo, Twitch, Reddit, and more) with 1 click.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F6V82112T7)

![Browsers](https://img.shields.io/badge/Browsers-Chrome%20%7C%20Edge%20%7C%20Opera%20%7C%20Firefox-10b981)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20yt--dlp-06b6d4)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## ✨ Features

- **1-Click Downloads:** Download video (MP4/WEBM/MKV) or music (MP3/FLAC/WAV) with a single click.
- **Zero Setup for Tools:** You don't need to manually install `yt-dlp` or `ffmpeg`. The setup script downloads them for you automatically!
- **Auto Stream Detection:** Detects videos playing on the page and direct stream links.
- **Dark & Light Mode:** Looks clean and matches your style.
- **Customizable:** Change download formats, quality (up to 8K), and choose where your files get saved.
- **Live Progress:** Shows download speed, percentage, and ETA in the popup.

---

## 🚀 How to Install

### What you need:
- Windows 10/11
- **Python 3.8+** installed ([python.org](https://www.python.org/downloads/)) *(Make sure to check "Add Python to PATH" when installing!)*

---

### Step 1: Add Extension to your Browser
1. Open your browser extensions page:
   - **Chrome / Brave / Opera:** `chrome://extensions`
   - **Edge:** `edge://extensions`
2. Turn on **Developer mode** (top right switch).
3. Click **Load unpacked** and select the `extension` folder from this repo.
4. Pin the extension to your toolbar so you can click it easily.

---

### Step 2: Run Setup
1. Double-click **`setup.bat`** in the main project folder.
2. It will connect the extension with Python and download `yt-dlp` and `ffmpeg` if you don't have them.
3. Done!

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
- Set a custom download folder (like `D:\Downloads\FTODE`).
- Click "Check for Updates" to update `yt-dlp` and `ffmpeg` anytime.

---

## 🗑️ How to Uninstall

1. Double-click **`uninstall.bat`** (this cleans up registry keys and backend files).
2. Right-click the extension icon in your browser and click **Remove from Chrome/Edge**.

---

## 📦 Building a Release (Optional)

If you want to package the project into a zip file to share with friends:
- Run **`build.bat`** (or `python build.py`).
- It creates a clean release package inside the `dist/` folder.

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
