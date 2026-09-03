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
  const downloadFolderHint = document.getElementById('download-folder-hint');
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
  const diagnosticsPanel = document.getElementById('diagnostics-panel');

  // DOM Elements - Companion Setup Guide & Downloader
  const hostSetupCard = document.getElementById('host-setup-card');
  const hostSetupGuide = document.getElementById('host-setup-guide');
  const tabOsWin = document.getElementById('tab-os-win');
  const tabOsLinux = document.getElementById('tab-os-linux');
  const btnDownloadSetup = document.getElementById('btn-download-setup');
  const btnDlTitle = document.getElementById('btn-dl-title');
  const stepHeading1 = document.getElementById('step-heading-1');
  const stepHint1 = document.getElementById('step-hint-1');
  const stepHeading2 = document.getElementById('step-heading-2');
  const stepArchiveName = document.getElementById('step-archive-name');
  const stepScriptName = document.getElementById('step-script-name');
  const stepRunHint = document.getElementById('step-run-hint');
  const autoDetectRadar = document.getElementById('auto-detect-radar');
  const radarText = document.getElementById('radar-text');
  const smartscreenTip = document.getElementById('smartscreen-tip');

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
  const currentExtVersion = manifest?.version || '1.0.3';
  const footerVersionEl = document.getElementById('footer-version');
  if (footerVersionEl) footerVersionEl.textContent = `v${currentExtVersion}`;

  const diagExtVersion = document.getElementById('diag-ext-version');
  const diagExtBadge = document.getElementById('diag-ext-badge');
  const extUpdateCard = document.getElementById('ext-update-card');
  const extNewVersion = document.getElementById('ext-new-version');
  const btnGithubDownload = document.getElementById('btn-github-download');
  const btnDismissUpdate = document.getElementById('btn-dismiss-update');
  let currentUpdateResult = null;

  async function isUpdateDismissed(version) {
    try {
      const data = await chrome.storage.local.get('dismissed_ext_update_version');
      return data.dismissed_ext_update_version === version;
    } catch {
      return false;
    }
  }

  async function setUpdateDismissed(version) {
    try {
      await chrome.storage.local.set({ dismissed_ext_update_version: version });
    } catch {}
  }

  if (btnDismissUpdate) {
    btnDismissUpdate.addEventListener('click', async () => {
      if (extUpdateCard) {
        extUpdateCard.classList.add('hidden');
      }
      if (currentUpdateResult && currentUpdateResult.latestVersion) {
        await setUpdateDismissed(currentUpdateResult.latestVersion);
      }
      showToastNotification('Update notification dismissed');
    });
  }

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
  async function applyExtensionUpdateUI(updateResult, isManualCheck = false) {
    currentUpdateResult = updateResult;
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
        const dismissed = await isUpdateDismissed(updateResult.latestVersion);
        if (isManualCheck || !dismissed) {
          extUpdateCard.classList.remove('hidden');
        } else {
          extUpdateCard.classList.add('hidden');
        }
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
   * Updates dynamic hint under download folder input based on whether it's absolute or relative
   */
  function updateFolderHint() {
    if (!downloadFolderHint || !downloadFolderInput) return;
    const val = downloadFolderInput.value.trim();
    downloadFolderHint.replaceChildren();

    if (!val) {
      downloadFolderHint.appendChild(document.createTextNode('Enter a subfolder name (e.g. '));
      const code1 = document.createElement('code');
      code1.textContent = 'FTODE';
      downloadFolderHint.appendChild(code1);
      downloadFolderHint.appendChild(document.createTextNode(') or full path (e.g. '));
      const code2 = document.createElement('code');
      code2.textContent = 'D:\\Downloads\\FTODE';
      downloadFolderHint.appendChild(code2);
      downloadFolderHint.appendChild(document.createTextNode(').'));
      return;
    }

    const isAbs = /^[a-zA-Z]:[\\/]/.test(val) || val.startsWith('/') || val.startsWith('\\\\');
    if (isAbs) {
      downloadFolderHint.appendChild(document.createTextNode('Custom path: '));
      const code = document.createElement('code');
      code.textContent = val;
      downloadFolderHint.appendChild(code);
    } else {
      downloadFolderHint.appendChild(document.createTextNode('Subfolder: '));
      const code = document.createElement('code');
      code.textContent = `Downloads/${val}`;
      downloadFolderHint.appendChild(code);
      downloadFolderHint.appendChild(document.createTextNode(' (inside your system Downloads folder).'));
    }
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
      updateFolderHint();
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
      updateFolderHint();
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
    updateFolderHint();

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

  // OS Tab Selection & Setup Logic
  let selectedOS = (navigator.platform && navigator.platform.toLowerCase().includes('linux')) ? 'linux' : 'win';
  let hostPollTimer = null;

  function updateOSTab(os) {
    selectedOS = os;
    if (tabOsWin) tabOsWin.classList.toggle('active', os === 'win');
    if (tabOsLinux) tabOsLinux.classList.toggle('active', os === 'linux');

    if (os === 'win') {
      if (btnDlTitle) btnDlTitle.textContent = 'Download Host Setup (.exe)';
      if (stepHeading1) stepHeading1.textContent = 'Download Setup Wizard';
      if (stepArchiveName) stepArchiveName.textContent = 'FTODE-Host-Setup-Windows.exe';
      if (stepHeading2) stepHeading2.textContent = 'Run Setup Wizard';
      if (stepRunHint) {
        stepRunHint.replaceChildren(
          document.createTextNode('Run '),
          Object.assign(document.createElement('code'), { textContent: 'FTODE-Host-Setup-Windows.exe' }),
          document.createTextNode('. The 1-click wizard configures browser registries (Firefox, Opera, Chrome, Edge), installs yt-dlp & FFmpeg, and integrates with Windows Control Panel.')
        );
      }
      if (smartscreenTip) smartscreenTip.classList.remove('hidden');
    } else {
      if (btnDlTitle) btnDlTitle.textContent = 'Download Host Setup (Linux .zip)';
      if (stepHeading1) stepHeading1.textContent = 'Download & Extract Archive';
      if (stepArchiveName) stepArchiveName.textContent = 'FTODE-Host-Setup-Linux.zip';
      if (stepHeading2) stepHeading2.textContent = 'Run 1-Click Setup Script';
      if (stepRunHint) {
        stepRunHint.replaceChildren(
          document.createTextNode('Open a terminal in the extracted folder and run: '),
          Object.assign(document.createElement('code'), { textContent: 'bash "FTODE Host Setup.sh"' }),
          document.createTextNode('. It registers the manifest across your browsers and configures yt-dlp & FFmpeg.')
        );
      }
      if (smartscreenTip) smartscreenTip.classList.add('hidden');
    }
  }

  if (tabOsWin) tabOsWin.addEventListener('click', () => updateOSTab('win'));
  if (tabOsLinux) tabOsLinux.addEventListener('click', () => updateOSTab('linux'));

  /**
   * Triggers direct browser download of the companion setup archive
   */
  async function downloadCompanionSetup() {
    const isWin = selectedOS === 'win';
    const targetFileName = isWin ? 'FTODE-Host-Setup-Windows.exe' : 'FTODE-Host-Setup-Linux.zip';
    const GITHUB_REPO = 'Maximos2004/FTODE';
    let downloadUrl = `https://github.com/${GITHUB_REPO}/releases/latest/download/${targetFileName}`;

    if (btnDownloadSetup) {
      btnDownloadSetup.classList.add('downloading');
      btnDownloadSetup.disabled = true;
    }

    try {
      // Query latest release assets dynamically
      const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
        headers: { 'Accept': 'application/vnd.github.v3+json' },
        cache: 'no-store'
      });

      if (res.ok) {
        const releaseData = await res.json();
        const assets = releaseData.assets || [];
        const match = assets.find(a => a.name && (
          a.name.toLowerCase() === targetFileName.toLowerCase() ||
          (isWin && a.name.toLowerCase().includes('windows') && (a.name.endsWith('.exe') || a.name.endsWith('.zip'))) ||
          (!isWin && a.name.toLowerCase().includes('linux') && a.name.endsWith('.zip'))
        ));

        if (match && match.browser_download_url) {
          downloadUrl = match.browser_download_url;
        } else if (releaseData.html_url) {
          downloadUrl = releaseData.html_url;
        }
      }
    } catch (e) {
      console.warn('[Options] Dynamic release fetch error, using direct download URL:', e);
    }

    // Trigger browser download via invisible link element
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = targetFileName;
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    a.remove();

    const toastMsg = isWin
      ? `Downloading ${targetFileName}! Run the setup wizard to connect the companion host.`
      : `Downloading ${targetFileName}! Extract the archive and run FTODE Host Setup.sh.`;
    showToastNotification(toastMsg);

    setTimeout(() => {
      if (btnDownloadSetup) {
        btnDownloadSetup.classList.remove('downloading');
        btnDownloadSetup.disabled = false;
      }
    }, 1500);

    // Ensure polling is active so when the user runs the setup, it auto-detects immediately
    startHostPolling();
  }

  if (btnDownloadSetup) {
    btnDownloadSetup.addEventListener('click', downloadCompanionSetup);
  }

  function startHostPolling() {
    if (hostPollTimer) return;
    hostPollTimer = setInterval(async () => {
      await testHost(false, true);
    }, 2500);
  }

  function stopHostPolling() {
    if (hostPollTimer) {
      clearInterval(hostPollTimer);
      hostPollTimer = null;
    }
  }

  /**
   * Test Native Host connectivity & retrieve versions
   */
  async function testHost(showToast = false, isPolled = false) {
    if (showToast) {
      hostBubble.className = 'status-bubble';
      hostLabel.textContent = 'Testing Host Connection...';
      btnTestHost.disabled = true;
    }

    try {
      const response = await chrome.runtime.sendMessage({ type: 'TEST_HOST_CONNECTION' });

      if (response && response.connected) {
        const wasDisconnected = hostBubble.classList.contains('offline');
        hostBubble.className = 'status-bubble connected';
        hostLabel.textContent = 'Connected & Operational';

        // Collapse setup guide when connected
        if (hostSetupGuide) {
          hostSetupGuide.classList.add('hidden');
        }
        if (diagnosticsPanel) {
          diagnosticsPanel.classList.remove('hidden');
        }

        stopHostPolling();

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
        } else if (isPolled && wasDisconnected) {
          showToastNotification('🎉 Companion Host Connected Successfully!');
          if (hostSetupCard) {
            hostSetupCard.classList.add('highlight-success');
            setTimeout(() => hostSetupCard.classList.remove('highlight-success'), 3500);
          }
        }
      } else {
        hostBubble.className = 'status-bubble offline';
        hostLabel.textContent = 'Disconnected / Setup Required';
        diagYtdlp.textContent = 'Host Offline';
        diagFfmpeg.textContent = 'Host Offline';
        diagYtdlp.style.color = '#f87171';
        diagFfmpeg.style.color = '#f87171';

        // Show setup guide when disconnected
        if (hostSetupGuide) {
          hostSetupGuide.classList.remove('hidden');
        }
        if (autoDetectRadar) {
          autoDetectRadar.classList.remove('hidden');
        }

        startHostPolling();

        try {
          localStorage.setItem('ftode_host_info', JSON.stringify({ connected: false }));
        } catch {}

        if (showToast) {
          showToastNotification('Native host offline. Download and run setup above.', true);
        }
      }
    } catch (err) {
      hostBubble.className = 'status-bubble offline';
      hostLabel.textContent = 'Connection Failed';
      diagYtdlp.textContent = 'Error';
      diagFfmpeg.textContent = 'Error';
      if (hostSetupGuide) hostSetupGuide.classList.remove('hidden');
      startHostPolling();
      if (showToast) {
        showToastNotification('Host check failed: ' + err.message, true);
      }
    } finally {
      btnTestHost.disabled = false;
    }
  }

  function checkUrlHash() {
    if (window.location.hash === '#host-setup' || window.location.hash === '#setup' || window.location.search.includes('setup=1')) {
      if (hostSetupGuide) {
        hostSetupGuide.classList.remove('hidden');
      }
      if (hostSetupCard) {
        setTimeout(() => {
          hostSetupCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
          hostSetupCard.classList.add('highlight-pulse');
          setTimeout(() => hostSetupCard.classList.remove('highlight-pulse'), 3000);
        }, 150);
      }
    }
  }

  window.addEventListener('hashchange', checkUrlHash);

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
          await applyExtensionUpdateUI(extUpdateResult, true);
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
  downloadFolderInput.addEventListener('input', updateFolderHint);
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
        if (hostSetupGuide) hostSetupGuide.classList.add('hidden');
        if (diagnosticsPanel) diagnosticsPanel.classList.remove('hidden');
        if (h.ytdlp_version) {
          diagYtdlp.textContent = `v${h.ytdlp_version}`;
          diagYtdlp.style.color = '#6bd29d';
        }
        if (h.ffmpeg_version) {
          diagFfmpeg.textContent = `v${h.ffmpeg_version}`;
          diagFfmpeg.style.color = '#6bd29d';
        }
      } else {
        hostBubble.className = 'status-bubble offline';
        hostLabel.textContent = 'Disconnected / Setup Required';
        if (hostSetupGuide) hostSetupGuide.classList.remove('hidden');
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

  // Initialize OS selector tab & check hash for direct setup navigation
  updateOSTab(selectedOS);
  checkUrlHash();

  // Background host test & GitHub update check (silent, no popup toast on startup)
  testHost(false);
  checkGitHubExtensionUpdate().then((res) => applyExtensionUpdateUI(res, false)).catch(() => {});
});
