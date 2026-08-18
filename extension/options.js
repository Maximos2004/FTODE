/**
 * Max's Downloader - Options Controller Script
 * Handles settings persistence, native host diagnostics, and setup assistance.
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

  // Toast
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toast-message');

  const DEFAULTS = {
    videoFormat: 'MP4',
    videoQuality: 'best',
    audioFormat: 'MP3',
    audioQuality: 'best',
    downloadFolder: 'MaxsDownloads',
    existingFileAction: 'copy',
    enableDebug: true
  };

  /**
   * Load current extension ID
   */
  const extId = chrome.runtime.id || 'unknown';
  extensionIdVal.textContent = extId;

  btnCopyExtId.addEventListener('click', () => {
    navigator.clipboard.writeText(extId).then(() => {
      btnCopyExtId.textContent = 'Copied!';
      setTimeout(() => { btnCopyExtId.textContent = 'Copy'; }, 1500);
    });
  });

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
      downloadFolderInput.value = settings.downloadFolder || 'MaxsDownloads';
      if (existingFileActionSelect) {
        existingFileActionSelect.value = settings.existingFileAction || 'copy';
      }
      enableDebugToggle.checked = settings.enableDebug !== false;
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
      downloadFolder: downloadFolderInput.value.trim() || 'MaxsDownloads',
      existingFileAction: existingFileActionSelect ? existingFileActionSelect.value : 'copy',
      enableDebug: enableDebugToggle.checked
    };

    try {
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
   * Show animated toast feedback
   */
  let toastTimer = null;
  function showToastNotification(msg, isError = false) {
    if (toastTimer) clearTimeout(toastTimer);
    toastMessage.textContent = msg;
    toast.style.borderColor = isError ? '#ef4444' : '#10b981';
    toast.classList.remove('hidden');

    toastTimer = setTimeout(() => {
      toast.classList.add('hidden');
    }, 2500);
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
  async function testHost() {
    hostBubble.className = 'status-bubble';
    hostLabel.textContent = 'Testing Host Connection...';
    btnTestHost.disabled = true;

    try {
      const response = await chrome.runtime.sendMessage({ type: 'TEST_HOST_CONNECTION' });

      if (response && response.connected) {
        hostBubble.className = 'status-bubble connected';
        hostLabel.textContent = 'Connected & Operational';

        const data = response.data || {};
        diagYtdlp.textContent = data.ytdlp_version ? `v${data.ytdlp_version}` : (data.ytdlp_available ? 'Available' : 'Not Installed');
        diagYtdlp.style.color = data.ytdlp_available ? '#34d399' : '#f87171';

        diagFfmpeg.textContent = data.ffmpeg_version ? `v${data.ffmpeg_version}` : (data.ffmpeg_available ? 'Available' : 'Not Installed');
        diagFfmpeg.style.color = data.ffmpeg_available ? '#34d399' : '#f87171';

        // Update button state dynamically based on tool availability
        if (data.ytdlp_available && data.ffmpeg_available) {
          currentToolMode = 'check';
          if (labelBootstrapTools) labelBootstrapTools.textContent = 'Check for Updates';
          if (btnBootstrapTools) {
            btnBootstrapTools.classList.remove('install-needed');
            btnBootstrapTools.title = 'Check for yt-dlp & FFmpeg updates';
          }
        } else {
          currentToolMode = 'install';
          if (labelBootstrapTools) labelBootstrapTools.textContent = 'Install yt-dlp & FFmpeg (1-Click)';
          if (btnBootstrapTools) {
            btnBootstrapTools.classList.add('install-needed');
            btnBootstrapTools.title = 'Install missing yt-dlp or FFmpeg binaries';
          }
        }

        showToastNotification('Native host connected successfully!');
      } else {
        hostBubble.className = 'status-bubble error';
        hostLabel.textContent = 'Disconnected / Not Registered';
        diagYtdlp.textContent = 'Host Offline';
        diagFfmpeg.textContent = 'Host Offline';
        diagYtdlp.style.color = '#f87171';
        diagFfmpeg.style.color = '#f87171';

        const errMsg = response ? response.error : 'Unknown host error';
        showToastNotification('Native host offline. See setup instructions.', true);
      }
    } catch (err) {
      hostBubble.className = 'status-bubble error';
      hostLabel.textContent = 'Connection Failed';
      diagYtdlp.textContent = 'Error';
      diagFfmpeg.textContent = 'Error';
      showToastNotification('Host check failed: ' + err.message, true);
    } finally {
      btnTestHost.disabled = false;
    }
  }

  // Event Listeners
  btnSaveSettings.addEventListener('click', () => saveSettings(true));
  btnResetSettings.addEventListener('click', resetSettings);
  btnTestHost.addEventListener('click', testHost);

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
            testHost();
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
      // Check for Updates Mode
      bootstrapStatusText.textContent = 'Checking for yt-dlp & FFmpeg updates...';
      try {
        const response = await chrome.runtime.sendMessage({
          type: 'CHECK_UPDATES'
        });

        if (response && response.success) {
          const resultMsg = response.data && response.data.message ? response.data.message : 'Tools are up to date!';
          showToastNotification(resultMsg);
          bootstrapStatusText.textContent = resultMsg;
          bootstrapFill.style.width = '100%';
          setTimeout(() => {
            bootstrapProgressBox.classList.add('hidden');
            btnBootstrapTools.disabled = false;
            testHost();
          }, 2000);
        } else {
          const err = response ? response.error : 'Update check failed';
          showToastNotification(err, true);
          bootstrapStatusText.textContent = 'Error: ' + err;
          btnBootstrapTools.disabled = false;
        }
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

  // Auto-save on dropdown/input changes for seamless UX
  videoFormatSelect.addEventListener('change', () => saveSettings(true));
  videoQualitySelect.addEventListener('change', () => saveSettings(true));
  audioFormatSelect.addEventListener('change', () => saveSettings(true));
  audioQualitySelect.addEventListener('change', () => saveSettings(true));
  enableDebugToggle.addEventListener('change', () => saveSettings(true));

  // Initialize
  await loadSettings();
  testHost();
});
