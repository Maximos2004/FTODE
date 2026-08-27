/**
 * Finally that online downloader extension (FTODE) - Options Controller Script
 * Handles settings persistence, native host diagnostics, theme management, and setup assistance.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // DOM Elements - Settings
  const videoFormatSelect = document.getElementById('video-format');
  const videoQualitySelect = document.getElementById('video-quality');
  const audioFormatSelect = document.getElementById('audio-format');
  const audioQualitySelect = document.getElementById('audio-quality');
  const downloadFolderInput = document.getElementById('download-folder');
  const existingFileActionSelect = document.getElementById('existing-file-action');
  const enableDebugToggle = document.getElementById('enable-debug');

  const btnSaveSettings = document.getElementById('btn-save-settings');
  const btnResetSettings = document.getElementById('btn-reset-settings');

  // DOM Elements - Host & Diagnostics
  const hostBubble = document.getElementById('host-bubble');
  const hostLabel = document.getElementById('host-label');
  const btnTestHost = document.getElementById('btn-test-host');
  const extensionIdVal = document.getElementById('extension-id-val');
  const btnCopyExtId = document.getElementById('btn-copy-ext-id');
  const diagYtdlp = document.getElementById('diag-ytdlp');
  const diagFfmpeg = document.getElementById('diag-ffmpeg');

  // Theme Toggle
  const toggleTheme = document.getElementById('toggle-theme');

  // Toast
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toast-message');

  const DEFAULTS = {
    videoFormat: 'MP4',
    videoQuality: 'best',
    audioFormat: 'MP3',
    audioQuality: 'best',
    downloadFolder: 'FTODE',
    existingFileAction: 'copy',
    enableDebug: true,
    theme: 'dark'
  };

  /**
   * Load current extension ID & Version
   */
  const extId = chrome.runtime.id || 'unknown';
  if (extensionIdVal) extensionIdVal.textContent = extId;

  const manifest = chrome.runtime.getManifest ? chrome.runtime.getManifest() : null;
  const currentExtVersion = manifest?.version || '1.0.0';
  const footerVersionEl = document.getElementById('footer-version');
  if (footerVersionEl) footerVersionEl.textContent = `v${currentExtVersion}`;

  const diagExtVersion = document.getElementById('diag-ext-version');
  const diagExtBadge = document.getElementById('diag-ext-badge');
  const extUpdateCard = document.getElementById('ext-update-card');
  const extNewVersion = document.getElementById('ext-new-version');
  const btnGithubDownload = document.getElementById('btn-github-download');

  if (diagExtVersion) {
    diagExtVersion.textContent = `v${currentExtVersion}`;
    diagExtVersion.style.color = '#6bd29d';
  }

  if (btnCopyExtId) {
    btnCopyExtId.addEventListener('click', () => {
      navigator.clipboard.writeText(extId).then(() => {
        btnCopyExtId.textContent = 'Copied!';
        setTimeout(() => { btnCopyExtId.textContent = 'Copy'; }, 1500);
      });
    });
  }

  /**
   * Semantic Version comparator (e.g. '1.1.0' > '1.0.0')
   */
  function compareSemver(v1, v2) {
    const p1 = (v1 || '').replace(/^v/, '').split('.').map(n => parseInt(n, 10) || 0);
    const p2 = (v2 || '').replace(/^v/, '').split('.').map(n => parseInt(n, 10) || 0);
    const len = Math.max(p1.length, p2.length);
    for (let i = 0; i < len; i++) {
      const num1 = p1[i] || 0;
      const num2 = p2[i] || 0;
      if (num1 > num2) return 1;
      if (num1 < num2) return -1;
    }
    return 0;
  }

  /**
   * Checks GitHub Releases and raw repository for newer FTODE Extension versions
   */
  async function checkGitHubExtensionUpdate() {
    const GITHUB_REPO = 'Maximos2004/FTODE';
    try {
      // 1. Check GitHub Latest Release endpoint
      const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
        headers: { 'Accept': 'application/vnd.github.v3+json' },
        cache: 'no-store'
      });

      if (res.ok) {
        const data = await res.json();
        const latestTag = data.tag_name || '';
        const cleanVer = latestTag.replace(/^v/, '');
        const releaseUrl = data.html_url || `https://github.com/${GITHUB_REPO}/releases/latest`;

        if (cleanVer && compareSemver(cleanVer, currentExtVersion) > 0) {
          return { hasUpdate: true, latestVersion: cleanVer, releaseUrl };
        }
      }
    } catch (e) {
      console.warn('[Options] GitHub release API check failed:', e);
    }

    try {
      // 2. Fallback check raw manifest.json on main branch
      const rawRes = await fetch(`https://raw.githubusercontent.com/${GITHUB_REPO}/main/extension/manifest.json`, {
        cache: 'no-store'
      });
      if (rawRes.ok) {
        const rawData = await rawRes.json();
        const rawVer = rawData.version || '';
        if (rawVer && compareSemver(rawVer, currentExtVersion) > 0) {
          return { hasUpdate: true, latestVersion: rawVer, releaseUrl: `https://github.com/${GITHUB_REPO}/releases/latest` };
        }
      }
    } catch (e) {
      console.warn('[Options] GitHub raw manifest check failed:', e);
    }

    return { hasUpdate: false, currentVersion: currentExtVersion };
  }

  /**
   * Applies update check result to GUI badge and alert box
   */
  function applyExtensionUpdateUI(updateResult) {
    if (updateResult && updateResult.hasUpdate) {
      if (diagExtVersion) {
        diagExtVersion.textContent = `v${currentExtVersion} (Update: v${updateResult.latestVersion})`;
        diagExtVersion.style.color = '#fbbf24';
      }
      if (extUpdateCard) {
        if (extNewVersion) extNewVersion.textContent = `v${updateResult.latestVersion}`;
        if (btnGithubDownload && updateResult.releaseUrl) {
          btnGithubDownload.href = updateResult.releaseUrl;
        }
        extUpdateCard.classList.remove('hidden');
      }
    } else {
      if (diagExtVersion) {
        diagExtVersion.textContent = `v${currentExtVersion}`;
        diagExtVersion.style.color = '#6bd29d';
      }
      if (extUpdateCard) {
        extUpdateCard.classList.add('hidden');
      }
    }
  }

  /**
   * Theme Management (Light / Dark mode)
   */
  async function loadTheme() {
    try {
      const data = await chrome.storage.sync.get({ theme: 'dark' });
      const isLight = data.theme === 'light';
      if (isLight) {
        document.documentElement.classList.add('light-theme');
        document.body.classList.add('light-theme');
        try { localStorage.setItem('ftode_theme', 'light'); } catch {}
        if (toggleTheme) toggleTheme.checked = true;
      } else {
        document.documentElement.classList.remove('light-theme');
        document.body.classList.remove('light-theme');
        try { localStorage.setItem('ftode_theme', 'dark'); } catch {}
        if (toggleTheme) toggleTheme.checked = false;
      }
    } catch (e) {
      console.error('[Options] Theme load error:', e);
    }
  }

  if (toggleTheme) {
    toggleTheme.addEventListener('change', async () => {
      const isLight = toggleTheme.checked;
      if (isLight) {
        document.documentElement.classList.add('light-theme');
        document.body.classList.add('light-theme');
        try { localStorage.setItem('ftode_theme', 'light'); } catch {}
      } else {
        document.documentElement.classList.remove('light-theme');
        document.body.classList.remove('light-theme');
        try { localStorage.setItem('ftode_theme', 'dark'); } catch {}
      }
      await chrome.storage.sync.set({ theme: isLight ? 'light' : 'dark' });
    });
  }

  /**
   * Load saved settings
   */
  async function loadSettings() {
    try {
      const settings = await chrome.storage.sync.get(DEFAULTS);

      videoFormatSelect.value = settings.videoFormat || 'MP4';
      videoQualitySelect.value = settings.videoQuality || 'best';
      audioFormatSelect.value = settings.audioFormat || 'MP3';
      audioQualitySelect.value = settings.audioQuality || 'best';
      downloadFolderInput.value = settings.downloadFolder || 'FTODE';
      if (existingFileActionSelect) {
        existingFileActionSelect.value = settings.existingFileAction || 'copy';
      }
      enableDebugToggle.checked = settings.enableDebug !== false;
      try { localStorage.setItem('ftode_settings', JSON.stringify(settings)); } catch {}
    } catch (err) {
      console.error('[Options] Load settings error:', err);
    }
  }

  /**
   * Save settings
   */
  async function saveSettings(showToast = true) {
    const toSave = {
      videoFormat: videoFormatSelect.value,
      videoQuality: videoQualitySelect.value,
      audioFormat: audioFormatSelect.value,
      audioQuality: audioQualitySelect.value,
      downloadFolder: downloadFolderInput.value.trim() || 'FTODE',
      existingFileAction: existingFileActionSelect ? existingFileActionSelect.value : 'copy',
      enableDebug: enableDebugToggle.checked
    };

    try {
      try { localStorage.setItem('ftode_settings', JSON.stringify(toSave)); } catch {}
      await chrome.storage.sync.set(toSave);
      if (showToast) {
        showToastNotification('Settings saved successfully!');
      }
    } catch (err) {
      console.error('[Options] Save settings error:', err);
      if (showToast) {
        showToastNotification('Failed to save settings: ' + err.message, true);
      }
    }
  }

  /**
   * Reset settings to default values
   */
  async function resetSettings() {
    videoFormatSelect.value = DEFAULTS.videoFormat;
    videoQualitySelect.value = DEFAULTS.videoQuality;
    audioFormatSelect.value = DEFAULTS.audioFormat;
    audioQualitySelect.value = DEFAULTS.audioQuality;
    downloadFolderInput.value = DEFAULTS.downloadFolder;
    if (existingFileActionSelect) {
      existingFileActionSelect.value = DEFAULTS.existingFileAction;
    }
    enableDebugToggle.checked = DEFAULTS.enableDebug;

    await chrome.storage.sync.set(DEFAULTS);
    showToastNotification('Reset to default settings');
  }

  /**
   * Show animated floating toast feedback (Middle Top)
   */
  let toastTimer = null;
  function showToastNotification(msg, isError = false) {
    if (toastTimer) clearTimeout(toastTimer);
    toastMessage.textContent = msg;

    if (isError) {
      toast.classList.add('toast-error');
    } else {
      toast.classList.remove('toast-error');
    }

    toast.classList.remove('hidden');

    toastTimer = setTimeout(() => {
      toast.classList.add('hidden');
    }, 2800);
  }

  // Bootstrap & Update state
  let currentToolMode = 'check'; // 'check' | 'install'
  const btnBootstrapTools = document.getElementById('btn-bootstrap-tools');
  const labelBootstrapTools = document.getElementById('label-bootstrap-tools');
  const bootstrapProgressBox = document.getElementById('bootstrap-progress-box');
  const bootstrapStatusText = document.getElementById('bootstrap-status-text');
  const bootstrapFill = document.getElementById('bootstrap-fill');

  /**
   * Test Native Host connectivity & retrieve versions
   */
  async function testHost(showToast = false) {
    if (showToast) {
      hostBubble.className = 'status-bubble';
      hostLabel.textContent = 'Testing Host Connection...';
      btnTestHost.disabled = true;
    }

    try {
      const response = await chrome.runtime.sendMessage({ type: 'TEST_HOST_CONNECTION' });

      if (response && response.connected) {
        hostBubble.className = 'status-bubble connected';
        hostLabel.textContent = 'Connected & Operational';

        const data = response.data || {};
        const formatToolVersion = (ver, isAvailable) => {
          if (!ver || ver === 'Available') return isAvailable ? 'Available' : 'Not Installed';
          return ver.startsWith('v') ? ver : `v${ver}`;
        };

        diagYtdlp.textContent = formatToolVersion(data.ytdlp_version, data.ytdlp_available);
        diagYtdlp.style.color = data.ytdlp_available ? '#6bd29d' : '#f87171';

        diagFfmpeg.textContent = formatToolVersion(data.ffmpeg_version, data.ffmpeg_available);
        diagFfmpeg.style.color = data.ffmpeg_available ? '#6bd29d' : '#f87171';

        try {
          localStorage.setItem('ftode_host_info', JSON.stringify({
            connected: true,
            ytdlp_version: data.ytdlp_version,
            ytdlp_available: data.ytdlp_available,
            ffmpeg_version: data.ffmpeg_version,
            ffmpeg_available: data.ffmpeg_available
          }));
        } catch {}

        // Update button state dynamically based on tool availability
        if (data.ytdlp_available && data.ffmpeg_available) {
          currentToolMode = 'check';
          if (labelBootstrapTools) labelBootstrapTools.textContent = 'Check for Updates';
          if (btnBootstrapTools) {
            btnBootstrapTools.classList.remove('btn-install');
            btnBootstrapTools.title = 'Check for yt-dlp & FFmpeg updates';
          }
        } else {
          currentToolMode = 'install';
          if (labelBootstrapTools) labelBootstrapTools.textContent = 'Install yt-dlp & FFmpeg (1-Click)';
          if (btnBootstrapTools) {
            btnBootstrapTools.classList.add('btn-install');
            btnBootstrapTools.title = 'Install missing yt-dlp or FFmpeg binaries';
          }
        }

        if (showToast) {
          showToastNotification('Native host connected successfully!');
        }
      } else {
        hostBubble.className = 'status-bubble offline';
        hostLabel.textContent = 'Disconnected / Not Registered';
        diagYtdlp.textContent = 'Host Offline';
        diagFfmpeg.textContent = 'Host Offline';
        diagYtdlp.style.color = '#f87171';
        diagFfmpeg.style.color = '#f87171';

        try {
          localStorage.setItem('ftode_host_info', JSON.stringify({ connected: false }));
        } catch {}

        if (showToast) {
          const errMsg = response ? response.error : 'Unknown host error';
          showToastNotification('Native host offline. See setup instructions.', true);
        }
      }
    } catch (err) {
      hostBubble.className = 'status-bubble offline';
      hostLabel.textContent = 'Connection Failed';
      diagYtdlp.textContent = 'Error';
      diagFfmpeg.textContent = 'Error';
      if (showToast) {
        showToastNotification('Host check failed: ' + err.message, true);
      }
    } finally {
      btnTestHost.disabled = false;
    }
  }

  // Event Listeners
  btnSaveSettings.addEventListener('click', () => saveSettings(true));
  btnResetSettings.addEventListener('click', resetSettings);
  btnTestHost.addEventListener('click', () => testHost(true));

  async function handleToolAction() {
    btnBootstrapTools.disabled = true;
    bootstrapProgressBox.classList.remove('hidden');
    bootstrapFill.style.width = '10%';

    if (currentToolMode === 'install') {
      bootstrapStatusText.textContent = 'Installing missing binaries (yt-dlp & FFmpeg)...';
      try {
        const response = await chrome.runtime.sendMessage({
          type: 'BOOTSTRAP_BINARIES',
          force: false
        });

        if (response && response.success) {
          showToastNotification('yt-dlp and FFmpeg successfully installed!');
          bootstrapStatusText.textContent = 'Installation complete! Binaries ready.';
          bootstrapFill.style.width = '100%';
          setTimeout(() => {
            bootstrapProgressBox.classList.add('hidden');
            btnBootstrapTools.disabled = false;
            testHost(false);
          }, 1500);
        } else {
          const err = response ? response.error : 'Installation failed';
          showToastNotification(err, true);
          bootstrapStatusText.textContent = 'Error: ' + err;
          btnBootstrapTools.disabled = false;
        }
      } catch (err) {
        showToastNotification('Installation error: ' + err.message, true);
        bootstrapStatusText.textContent = 'Error: ' + err.message;
        btnBootstrapTools.disabled = false;
      }
    } else {
      // Check for Updates Mode (Checks both GitHub Extension & Native Host Tools)
      bootstrapStatusText.textContent = 'Checking for Extension, yt-dlp & FFmpeg updates...';
      bootstrapFill.style.width = '25%';

      try {
        // 1. Check GitHub for Extension update concurrently with Host tool check
        const [extUpdate, hostResponse] = await Promise.allSettled([
          checkGitHubExtensionUpdate(),
          chrome.runtime.sendMessage({ type: 'CHECK_UPDATES' })
        ]);

        bootstrapFill.style.width = '75%';

        let extUpdateResult = null;
        if (extUpdate.status === 'fulfilled') {
          extUpdateResult = extUpdate.value;
          applyExtensionUpdateUI(extUpdateResult);
        }

        let hostSuccess = false;
        let hostMsg = 'Tools up to date.';
        if (hostResponse.status === 'fulfilled' && hostResponse.value && hostResponse.value.success) {
          hostSuccess = true;
          hostMsg = hostResponse.value.data?.message || 'yt-dlp & FFmpeg are up to date!';
        }

        bootstrapFill.style.width = '100%';

        if (extUpdateResult && extUpdateResult.hasUpdate) {
          const bannerMsg = `🎉 New FTODE v${extUpdateResult.latestVersion} available on GitHub!`;
          showToastNotification(bannerMsg);
          bootstrapStatusText.textContent = bannerMsg;
        } else if (hostSuccess) {
          showToastNotification('Everything is up to date!');
          bootstrapStatusText.textContent = 'Extension, yt-dlp & FFmpeg are all up to date!';
        } else {
          showToastNotification(hostMsg);
          bootstrapStatusText.textContent = hostMsg;
        }

        setTimeout(() => {
          bootstrapProgressBox.classList.add('hidden');
          btnBootstrapTools.disabled = false;
          testHost(false);
        }, 2200);
      } catch (err) {
        showToastNotification('Update check error: ' + err.message, true);
        bootstrapStatusText.textContent = 'Error: ' + err.message;
        btnBootstrapTools.disabled = false;
      }
    }
  }

  if (btnBootstrapTools) {
    btnBootstrapTools.addEventListener('click', handleToolAction);
  }

  // Listen for broadcast progress events
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.type === 'BOOTSTRAP_PROGRESS') {
      if (bootstrapProgressBox) {
        bootstrapProgressBox.classList.remove('hidden');
        bootstrapStatusText.textContent = msg.line || 'Downloading tools...';
        const pct = Math.min(100, Math.max(0, Math.round(msg.percent || 0)));
        bootstrapFill.style.width = `${pct}%`;
      }
    }
  });

  // Auto-save on dropdown/input changes for seamless UX (silent background save)
  videoFormatSelect.addEventListener('change', () => saveSettings(false));
  videoQualitySelect.addEventListener('change', () => saveSettings(false));
  audioFormatSelect.addEventListener('change', () => saveSettings(false));
  audioQualitySelect.addEventListener('change', () => saveSettings(false));
  if (existingFileActionSelect) {
    existingFileActionSelect.addEventListener('change', () => saveSettings(false));
  }
  downloadFolderInput.addEventListener('change', () => saveSettings(false));
  enableDebugToggle.addEventListener('change', () => saveSettings(false));

  // Synchronously pre-populate from localStorage cache if available for instant baseline
  try {
    const cachedSettings = localStorage.getItem('ftode_settings');
    if (cachedSettings) {
      const s = JSON.parse(cachedSettings);
      if (s.videoFormat) videoFormatSelect.value = s.videoFormat;
      if (s.videoQuality) videoQualitySelect.value = s.videoQuality;
      if (s.audioFormat) audioFormatSelect.value = s.audioFormat;
      if (s.audioQuality) audioQualitySelect.value = s.audioQuality;
      if (s.downloadFolder) downloadFolderInput.value = s.downloadFolder;
      if (s.existingFileAction && existingFileActionSelect) existingFileActionSelect.value = s.existingFileAction;
      if (s.enableDebug !== undefined) enableDebugToggle.checked = s.enableDebug;
    }
    const cachedTheme = localStorage.getItem('ftode_theme');
    if (cachedTheme === 'light') {
      document.documentElement.classList.add('light-theme');
      document.body.classList.add('light-theme');
      if (toggleTheme) toggleTheme.checked = true;
    } else if (cachedTheme === 'dark') {
      document.documentElement.classList.remove('light-theme');
      document.body.classList.remove('light-theme');
      if (toggleTheme) toggleTheme.checked = false;
    }
    const cachedHost = localStorage.getItem('ftode_host_info');
    if (cachedHost) {
      const h = JSON.parse(cachedHost);
      if (h.connected) {
        hostBubble.className = 'status-bubble connected';
        hostLabel.textContent = 'Connected & Operational';
        if (h.ytdlp_version) {
          diagYtdlp.textContent = `v${h.ytdlp_version}`;
          diagYtdlp.style.color = '#6bd29d';
        }
        if (h.ffmpeg_version) {
          diagFfmpeg.textContent = `v${h.ffmpeg_version}`;
          diagFfmpeg.style.color = '#6bd29d';
        }
      }
    }
  } catch {}

  // Initialize Theme and Settings asynchronously from chrome.storage
  try {
    await Promise.all([loadTheme(), loadSettings()]);
  } catch (err) {
    console.error('[Options] Init error:', err);
  } finally {
    // Reveal GUI in fully initialized state, then remove preload after painted
    document.body.classList.add('ready');
    requestAnimationFrame(() => {
      setTimeout(() => {
        document.documentElement.classList.remove('preload');
      }, 50);
    });
  }

  // Safety fallback to guarantee GUI is visible
  setTimeout(() => {
    document.body.classList.add('ready');
    document.documentElement.classList.remove('preload');
  }, 200);

  // Background host test & GitHub update check (silent, no popup toast on startup)
  testHost(false);
  checkGitHubExtensionUpdate().then(applyExtensionUpdateUI).catch(() => {});
});
