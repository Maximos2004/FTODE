/**
 * Finally that online downloader extension (FTODE) - Popup Script
 * Coordinates UI updates, format bindings, real-time download streaming,
 * and user interactions.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // DOM Elements
  const btnRefresh = document.getElementById('btn-refresh');
  const btnToggleTerminal = document.getElementById('btn-toggle-terminal');
  const btnOptions = document.getElementById('btn-options');

  const statusBadge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');
  const mediaTypeTag = document.getElementById('media-type-tag');
  const mediaTitle = document.getElementById('media-title');
  const sourceDomain = document.getElementById('source-domain');
  const streamsCount = document.getElementById('streams-count');

  const hostAlert = document.getElementById('host-alert');
  const btnSetupHost = document.getElementById('btn-setup-host');

  const btnDownloadVideo = document.getElementById('btn-download-video');
  const labelVideo = document.getElementById('label-video');
  const badgeVideoFormat = document.getElementById('badge-video-format');

  const btnDownloadAudio = document.getElementById('btn-download-audio');
  const labelAudio = document.getElementById('label-audio');
  const badgeAudioFormat = document.getElementById('badge-audio-format');

  const progressSection = document.getElementById('progress-section');
  const progressStatus = document.getElementById('progress-status');
  const progressPercent = document.getElementById('progress-percent');
  const progressFill = document.getElementById('progress-fill');
  const metricSpeed = document.getElementById('metric-speed');
  const metricEta = document.getElementById('metric-eta');
  const btnCancelJob = document.getElementById('btn-cancel-job');

  const streamsAccordion = document.getElementById('streams-accordion');
  const btnAccordionToggle = document.getElementById('btn-accordion-toggle');
  const streamsList = document.getElementById('streams-list');
  const accordionCount = document.getElementById('accordion-count');

  const terminalContainer = document.getElementById('terminal-container');
  const terminalBody = document.getElementById('terminal-body');
  const btnTermCopy = document.getElementById('btn-term-copy');
  const btnTermClear = document.getElementById('btn-term-clear');

  const hostPill = document.getElementById('host-pill');
  const hostPillText = document.getElementById('host-pill-text');
  const footerFolder = document.getElementById('footer-folder');

  // Local state
  let currentTab = null;
  let tabMediaState = null;
  let currentSettings = {
    videoFormat: 'MP4',
    audioFormat: 'MP3',
    downloadFolder: 'FTODE',
    enableDebug: true
  };
  let isTerminalVisible = false;
  let currentJob = null;
  let isHostConnected = false;

  function isHomePageOrFeed(url) {
    if (!url) return true;
    try {
      const u = new URL(url);
      const host = u.hostname.toLowerCase();
      const path = u.pathname.toLowerCase().replace(/\/+$/, '') || '/';
      const search = u.search.toLowerCase();

      // Generic root homepage
      if (path === '/' || path === '' || path === '/home' || path === '/index.html' || path === '/index.php') {
        return true;
      }

      // YouTube home feeds & navigation
      if (host.includes('youtube.com') || host.includes('youtu.be')) {
        if (path === '/watch' || path.startsWith('/shorts/') || path.startsWith('/live/') || path.startsWith('/embed/')) {
          return false;
        }
        if (path === '/playlist' && search.includes('list=')) {
          return false;
        }
        if (
          path === '/' || path === '' ||
          path.startsWith('/feed') ||
          path === '/results' ||
          path === '/gaming' ||
          path === '/explore' ||
          path === '/trending' ||
          path.startsWith('/channel') ||
          path.startsWith('/c/') ||
          path.startsWith('/user/') ||
          path.startsWith('/@')
        ) {
          return true;
        }
      }

      // Twitch
      if (host.includes('twitch.tv')) {
        if (path === '/' || path === '/directory' || path.startsWith('/directory/') || path.startsWith('/p/')) {
          return true;
        }
      }

      // SoundCloud
      if (host.includes('soundcloud.com')) {
        if (path === '/' || path === '/discover' || path === '/stream' || path === '/feed' || path === '/charts' || path.startsWith('/you/') || path === '/search') {
          return true;
        }
      }

      // Vimeo
      if (host.includes('vimeo.com')) {
        if (path === '/' || path === '/home' || path === '/watch' || path === '/explore' || path === '/channels' || path === '/categories') {
          return true;
        }
      }

      // TikTok
      if (host.includes('tiktok.com')) {
        if (path === '/' || path === '/foryou' || path === '/following' || path === '/explore' || path === '/live') {
          return true;
        }
      }

      // Twitter / X
      if (host.includes('twitter.com') || host.includes('x.com')) {
        if (path === '/' || path === '/home' || path === '/explore' || path === '/notifications' || path === '/messages' || path === '/search') {
          return true;
        }
      }

      // Reddit
      if (host.includes('reddit.com')) {
        if (path === '/' || path === '/r/all' || path === '/r/popular' || (path.startsWith('/r/') && !path.includes('/comments/')) || path.startsWith('/user/') || path === '/hot' || path === '/new' || path === '/top') {
          return true;
        }
      }

      // Facebook
      if (host.includes('facebook.com') || host.includes('fb.watch')) {
        if (path === '/' || path === '/home.php' || path === '/feed' || (path === '/watch' && !search.includes('v='))) {
          return true;
        }
      }

      // Instagram
      if (host.includes('instagram.com')) {
        if (path === '/' || path === '/explore' || path === '/explore/' || path === '/reels' || path === '/reels/' || path === '/direct/') {
          return true;
        }
      }

      // Bandcamp
      if (host.includes('bandcamp.com')) {
        if (path === '/' || path.startsWith('/tag/') || path === '/discover') {
          return true;
        }
      }

      // Dailymotion
      if (host.includes('dailymotion.com')) {
        if (path === '/' || path === '/feed' || path === '/trending') {
          return true;
        }
      }

      // Bilibili
      if (host.includes('bilibili.com')) {
        if (path === '/' || path.startsWith('/v/')) {
          return true;
        }
      }

      // Kick
      if (host.includes('kick.com')) {
        if (path === '/' || path === '/browse' || path.startsWith('/category/')) {
          return true;
        }
      }

      // Rumble
      if (host.includes('rumble.com')) {
        if (path === '/' || path === '/videos' || path === '/browse') {
          return true;
        }
      }

      return false;
    } catch {
      return false;
    }
  }

  /**
   * Initialize popup
   */
  async function init() {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        currentTab = tabs[0];
      }

      // Request fresh state from background
      const response = await chrome.runtime.sendMessage({
        type: 'GET_POPUP_STATE',
        tabId: currentTab ? currentTab.id : null
      });

      if (response) {
        tabMediaState = response.tabState;
        currentSettings = response.settings || currentSettings;
        currentJob = response.currentJob;
      }

      if (currentTab && currentTab.url && isHomePageOrFeed(currentTab.url)) {
        if (tabMediaState) {
          tabMediaState.items = [];
          tabMediaState.isStreamDomain = false;
          tabMediaState.isPlaylist = false;
          tabMediaState.hasMediaTags = false;
          tabMediaState.pageTitle = 'No media detected';
          tabMediaState.playlistTitle = null;
        }
      }

      // Also trigger content script scan for immediate live update
      if (currentTab && currentTab.id) {
        chrome.tabs.sendMessage(currentTab.id, { type: 'SCAN_MEDIA_DOM' }, (res) => {
          if (!chrome.runtime.lastError && res) {
            if (tabMediaState) {
              tabMediaState.pageUrl = res.pageUrl || tabMediaState.pageUrl;
              tabMediaState.pageTitle = res.pageTitle || tabMediaState.pageTitle;
              tabMediaState.playlistTitle = res.playlistTitle || null;
              tabMediaState.isPlaylist = res.isPlaylist !== undefined ? res.isPlaylist : tabMediaState.isPlaylist;
              tabMediaState.isStreamDomain = res.isStreamDomain !== undefined ? res.isStreamDomain : tabMediaState.isStreamDomain;
              tabMediaState.hasMediaTags = res.hasMediaTags;
              if (Array.isArray(res.items)) {
                tabMediaState.items = res.items;
              }
            }
            renderUI();
          }
        });
      }

      // Check Native Host status
      checkNativeHost();

      // Render initial UI
      renderUI();
    } catch (err) {
      console.error('[Popup] Init error:', err);
      renderUI();
    }
  }

  /**
   * Check Python native host connection
   */
  async function checkNativeHost() {
    try {
      const res = await chrome.runtime.sendMessage({ type: 'TEST_HOST_CONNECTION' });
      if (res && res.connected) {
        isHostConnected = true;
        hostPill.className = 'host-pill online';
        hostPillText.textContent = 'Host: Connected';
        hostAlert.classList.add('hidden');
      } else {
        isHostConnected = false;
        hostPill.className = 'host-pill offline';
        hostPillText.textContent = 'Host: Disconnected';
        hostAlert.classList.remove('hidden');
      }
    } catch (e) {
      isHostConnected = false;
      hostPill.className = 'host-pill offline';
      hostPillText.textContent = 'Host: Disconnected';
      hostAlert.classList.remove('hidden');
    }
  }

  function isPlaylistPageUrl(url) {
    if (!url) return false;
    if (isHomePageOrFeed(url)) return false;
    try {
      const u = new URL(url);
      const host = u.hostname.toLowerCase();
      const path = u.pathname.toLowerCase();
      const search = u.search.toLowerCase();
      if (host.includes('youtube.com') || host.includes('youtu.be')) {
        return path.includes('/playlist') && search.includes('list=');
      }
      if (host.includes('soundcloud.com') && (path.includes('/sets/') || path.includes('/albums/'))) {
        return true;
      }
      if (host.includes('bandcamp.com') && path.includes('/album/')) {
        return true;
      }
      if (path.includes('/playlist/') || path.includes('/playlists/') || path.includes('/album/')) {
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * Render popup UI based on current tab state
   */
  function renderUI() {
    const isHome = (currentTab && currentTab.url && isHomePageOrFeed(currentTab.url)) || (tabMediaState && isHomePageOrFeed(tabMediaState.pageUrl));

    // 1. Settings & Button Labels
    const vFmt = (currentSettings.videoFormat || 'MP4').toUpperCase();
    const aFmt = (currentSettings.audioFormat || 'MP3').toUpperCase();
    const isPlaylist = !isHome && ((tabMediaState && tabMediaState.isPlaylist) || (currentTab && isPlaylistPageUrl(currentTab.url)));

    if (isPlaylist) {
      labelVideo.textContent = `Download Playlist (${vFmt})`;
      labelAudio.textContent = `Download Playlist (${aFmt})`;
    } else {
      labelVideo.textContent = `Download ${vFmt}`;
      labelAudio.textContent = `Download ${aFmt}`;
    }
    badgeVideoFormat.textContent = vFmt;
    badgeAudioFormat.textContent = aFmt;

    footerFolder.textContent = `Folder: ${currentSettings.downloadFolder || 'FTODE'}`;

    // 2. Detection Status
    const isStream = isHome ? false : (tabMediaState ? tabMediaState.isStreamDomain : false);
    const items = (!isHome && tabMediaState && tabMediaState.items) ? tabMediaState.items : [];
    const hasVideo = !isHome && (isStream || items.some(i => i.type === 'video'));
    const hasAudio = !isHome && (isStream || items.some(i => i.type === 'audio'));
    const hasAnyMedia = !isHome && (isPlaylist || hasVideo || hasAudio);
    const totalCount = isStream ? Math.max(1, items.length) : items.length;

    // Display title & domain
    let displayTitle = hasAnyMedia ? 'Media Stream' : 'No media detected';
    let domainStr = 'No source';

    if (currentTab && currentTab.url) {
      try {
        domainStr = new URL(currentTab.url).hostname.replace('www.', '');
      } catch {}
    }

    if (hasAnyMedia) {
      if (tabMediaState && tabMediaState.isPlaylist && tabMediaState.playlistTitle) {
        displayTitle = tabMediaState.playlistTitle;
      } else if (tabMediaState && tabMediaState.pageTitle && tabMediaState.pageTitle !== 'No media detected' && tabMediaState.pageTitle !== 'Media Stream') {
        displayTitle = tabMediaState.pageTitle;
      } else if (currentTab && currentTab.title && currentTab.title !== 'YouTube') {
        displayTitle = currentTab.title;
      } else if (tabMediaState && tabMediaState.pageTitle) {
        displayTitle = tabMediaState.pageTitle;
      }
      displayTitle = displayTitle.replace(/^(?:\[?\s*(?:Unpaid\/Self Promotion|Self Promotion|Sponsor(?:ed)?|Interaction(?: Reminder)?|Intro|Outro|Preview|Filler|Highlight|Music: Non-Music Section|Exclusive Access|Patreon)\s*\]?)\s*[-:]?\s*/i, '');
      displayTitle = displayTitle.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();
    }

    mediaTitle.textContent = displayTitle;
    mediaTitle.title = displayTitle;
    sourceDomain.textContent = domainStr;
    streamsCount.textContent = hasAnyMedia ? (isPlaylist ? 'Full Playlist Batch' : (isStream ? 'High Quality Media Stream' : `${totalCount} media source(s)`)) : 'No media detected';

    // Status Badge States
    statusBadge.className = 'status-badge';

    if (isPlaylist) {
      statusBadge.classList.add('playlist-detected');
      statusText.textContent = 'Playlist Detected';
      mediaTypeTag.textContent = 'PLAYLIST';

      btnDownloadVideo.disabled = false;
      btnDownloadAudio.disabled = false;
    } else if (hasVideo || isStream) {
      statusBadge.classList.add('video-detected');
      statusText.textContent = 'Video Stream Detected';
      mediaTypeTag.textContent = 'VIDEO';

      btnDownloadVideo.disabled = false;
      btnDownloadAudio.disabled = false;
    } else if (hasAudio) {
      statusBadge.classList.add('audio-detected');
      statusText.textContent = 'Audio Stream Detected';
      mediaTypeTag.textContent = 'AUDIO';

      btnDownloadVideo.disabled = true;
      btnDownloadAudio.disabled = false;
    } else {
      statusBadge.classList.add('no-media');
      statusText.textContent = 'No Media Detected';
      mediaTypeTag.textContent = 'IDLE';

      btnDownloadVideo.disabled = true;
      btnDownloadAudio.disabled = true;
    }

    // 3. Streams Accordion (Deduplicated)
    const uniqueItems = [];
    const seenMap = new Set();
    items.forEach(item => {
      const key = `${item.type}_${item.url}`;
      if (!seenMap.has(key)) {
        seenMap.add(key);
        uniqueItems.push(item);
      }
    });

    if (hasAnyMedia && uniqueItems.length === 0) {
      uniqueItems.push({
        type: 'video',
        url: currentTab ? currentTab.url : '',
        mimeType: 'Adaptive Stream (HD/4K)',
        isBlob: false,
        isManifest: true,
        title: displayTitle
      });
    }

    if (uniqueItems.length > 0) {
      streamsAccordion.classList.remove('hidden');
      accordionCount.textContent = uniqueItems.length;
      renderStreamsList(uniqueItems);
    } else {
      streamsAccordion.classList.add('hidden');
    }

    // 4. Active Download Job UI
    renderJobState();
  }

  /**
   * Render individual stream items inside accordion
   */
  function renderStreamsList(items) {
    streamsList.innerHTML = '';
    items.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'stream-item-row';

      const info = document.createElement('div');
      info.className = 'stream-item-info';

      const title = document.createElement('span');
      title.className = 'stream-item-title';
      title.textContent = item.title || `Media Stream #${index + 1}`;
      title.title = item.url;

      const sub = document.createElement('span');
      sub.className = 'stream-item-sub';
      const sizeStr = item.sizeBytes ? ` • ${(item.sizeBytes / (1024 * 1024)).toFixed(1)} MB` : '';
      const mimeStr = item.isManifest ? 'Adaptive Manifest' : (item.mimeType || item.type.toUpperCase());
      sub.textContent = `${item.type.toUpperCase()} • ${mimeStr}${sizeStr}`;

      info.appendChild(title);
      info.appendChild(sub);

      const btn = document.createElement('button');
      btn.className = 'btn-mini-download';
      btn.textContent = 'Download';
      btn.onclick = () => {
        let downloadTarget = (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || item.url;
        startDownloadJob(item.type, downloadTarget, item.title || (tabMediaState ? tabMediaState.pageTitle : ''));
      };

      row.appendChild(info);
      row.appendChild(btn);
      streamsList.appendChild(row);
    });
  }

  let errorDismissTimer = null;

  /**
   * Render active download progress & logs
   */
  function renderJobState() {
    if (!currentJob || currentJob.status === 'idle') {
      progressSection.classList.add('hidden');
      return;
    }

    progressSection.classList.remove('hidden');

    const percent = Math.round(currentJob.percent || 0);
    progressPercent.textContent = `${percent}%`;
    progressFill.style.width = `${percent}%`;

    // Reset status color to default
    progressStatus.style.color = '';

    if (currentJob.status === 'downloading') {
      if (errorDismissTimer) {
        clearTimeout(errorDismissTimer);
        errorDismissTimer = null;
      }
      const isPl = currentJob.isPlaylist;
      progressStatus.textContent = isPl ? 'Downloading Playlist...' : `Downloading ${currentJob.mediaType.toUpperCase()}...`;
      metricSpeed.textContent = currentJob.speed || 'Calculating...';
      metricEta.textContent = currentJob.eta || '--:--';
      btnCancelJob.classList.remove('hidden');
    } else if (currentJob.status === 'remuxing') {
      if (errorDismissTimer) {
        clearTimeout(errorDismissTimer);
        errorDismissTimer = null;
      }
      const isPl = currentJob.isPlaylist;
      progressStatus.textContent = isPl ? 'Processing Playlist Tracks...' : 'Merging & Converting Formats...';
      metricSpeed.textContent = currentJob.speed || 'Processing...';
      metricEta.textContent = currentJob.eta || '--:--';
      btnCancelJob.classList.remove('hidden');
    } else if (currentJob.status === 'complete') {
      progressStatus.textContent = 'Download Complete!';
      progressPercent.textContent = '100%';
      progressFill.style.width = '100%';
      metricSpeed.textContent = 'Saved';
      metricEta.textContent = '00:00';
      btnCancelJob.classList.add('hidden');

      if (!errorDismissTimer) {
        errorDismissTimer = setTimeout(() => {
          if (currentJob && currentJob.status === 'complete') {
            progressSection.classList.add('hidden');
            currentJob.status = 'idle';
          }
          errorDismissTimer = null;
        }, 5000);
      }
    } else if (currentJob.status === 'error') {
      progressStatus.textContent = 'Download Cancelled / Stopped';
      progressStatus.style.color = '#ef4444';
      metricSpeed.textContent = 'Stopped';
      metricEta.textContent = '--';
      btnCancelJob.classList.add('hidden');

      if (!errorDismissTimer) {
        errorDismissTimer = setTimeout(() => {
          if (currentJob && currentJob.status === 'error') {
            progressSection.classList.add('hidden');
            currentJob.status = 'idle';
          }
          errorDismissTimer = null;
        }, 5000);
      }
    }

    // Auto-open terminal if debug is enabled or during active downloading
    if (currentSettings.enableDebug && (currentJob.status === 'downloading' || currentJob.status === 'remuxing')) {
      showTerminal(true);
    }

    // Render terminal logs
    if (currentJob.logs && currentJob.logs.length > 0) {
      renderTerminalLogs(currentJob.logs);
    }
  }

  /**
   * Render terminal logs
   */
  function renderTerminalLogs(logs) {
    terminalBody.innerHTML = '';
    logs.forEach(line => {
      const lineDiv = document.createElement('div');
      lineDiv.className = 'term-line';

      if (line.includes('[INFO]') || line.includes('[SYSTEM]')) {
        lineDiv.classList.add('info');
      } else if (line.includes('[download]') || line.includes('[ExtractAudio]')) {
        lineDiv.classList.add('download');
      } else if (line.includes('[Merger]') || line.includes('[ffmpeg]') || line.includes('[Remux]')) {
        lineDiv.classList.add('remux');
      } else if (line.includes('WARNING:') || line.includes('[WARN]')) {
        lineDiv.classList.add('warn');
      } else if (line.includes('ERROR:') || line.includes('[ERROR]')) {
        lineDiv.classList.add('error');
      } else if (line.includes('[SUCCESS]')) {
        lineDiv.classList.add('success');
      }

      lineDiv.textContent = line;
      terminalBody.appendChild(lineDiv);
    });

    // Auto-scroll to bottom
    terminalBody.scrollTop = terminalBody.scrollHeight;
  }

  function showTerminal(show) {
    isTerminalVisible = show;
    if (isTerminalVisible) {
      terminalContainer.classList.remove('hidden');
    } else {
      terminalContainer.classList.add('hidden');
    }
  }

  /**
   * Trigger download via Native Messaging
   */
  async function startDownloadJob(targetType, targetUrl, targetTitle) {
    const format = targetType === 'audio' ? currentSettings.audioFormat : currentSettings.videoFormat;
    const url = targetUrl || (currentTab ? currentTab.url : '');
    const isPlaylist = isPlaylistPageUrl(currentTab ? currentTab.url : '') || isPlaylistPageUrl(url) || (tabMediaState ? Boolean(tabMediaState.isPlaylist) : false);
    const title = targetTitle || (tabMediaState ? tabMediaState.pageTitle : (currentTab ? currentTab.title : 'Media Download'));

    if (!url) {
      alert('No media URL detected to download.');
      return;
    }

    if (currentSettings.enableDebug) {
      showTerminal(true);
    }

    try {
      const res = await chrome.runtime.sendMessage({
        type: 'START_DOWNLOAD',
        payload: {
          url: url,
          pageUrl: currentTab ? currentTab.url : url,
          title: title,
          mediaType: targetType,
          targetType: targetType,
          format: format,
          isPlaylist: isPlaylist
        }
      });

      if (res && res.status === 'error') {
        alert(`Could not start download: ${res.message}`);
      }
    } catch (err) {
      console.error('[Popup] Start download error:', err);
      alert(`Download trigger error: ${err.message}`);
    }
  }

  // ==========================================================================
  // Event Listeners
  // ==========================================================================

  // Action Buttons
  btnDownloadVideo.addEventListener('click', () => {
    let targetUrl = (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || '';
    if (!targetUrl && tabMediaState && tabMediaState.items) {
      const v = tabMediaState.items.find(i => i.type === 'video' && !i.isBlob && !i.isManifest);
      if (v) targetUrl = v.url;
    }
    startDownloadJob('video', targetUrl, tabMediaState ? tabMediaState.pageTitle : '');
  });

  btnDownloadAudio.addEventListener('click', () => {
    let targetUrl = (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || '';
    if (!targetUrl && tabMediaState && tabMediaState.items) {
      const a = tabMediaState.items.find(i => i.type === 'audio' && !i.isBlob && !i.isManifest);
      if (a) targetUrl = a.url;
    }
    startDownloadJob('audio', targetUrl, tabMediaState ? tabMediaState.pageTitle : '');
  });

  btnCancelJob.addEventListener('click', async () => {
    await chrome.runtime.sendMessage({ type: 'CANCEL_DOWNLOAD' });
  });

  // Top header actions
  btnRefresh.addEventListener('click', async () => {
    btnRefresh.style.transform = 'rotate(360deg)';
    setTimeout(() => { btnRefresh.style.transform = ''; }, 400);
    await init();
  });

  btnToggleTerminal.addEventListener('click', () => {
    showTerminal(!isTerminalVisible);
  });

  btnOptions.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  btnSetupHost.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Accordion toggle
  btnAccordionToggle.addEventListener('click', () => {
    const isHidden = streamsList.classList.contains('hidden');
    const icon = btnAccordionToggle.querySelector('.toggle-icon');
    if (isHidden) {
      streamsList.classList.remove('hidden');
      icon.classList.add('expanded');
    } else {
      streamsList.classList.add('hidden');
      icon.classList.remove('expanded');
    }
  });

  // Terminal actions
  btnTermCopy.addEventListener('click', () => {
    const text = currentJob && currentJob.logs ? currentJob.logs.join('\n') : terminalBody.innerText;
    navigator.clipboard.writeText(text).then(() => {
      btnTermCopy.textContent = 'Copied!';
      setTimeout(() => { btnTermCopy.textContent = 'Copy'; }, 1500);
    });
  });

  btnTermClear.addEventListener('click', async () => {
    terminalBody.innerHTML = '';
    await chrome.runtime.sendMessage({ type: 'CLEAR_LOGS' });
  });

  // Listen for real-time progress broadcasts from background service worker
  chrome.runtime.onMessage.addListener((message) => {
    if (message && message.type === 'JOB_UPDATED') {
      currentJob = message.job;
      renderJobState();
    }
  });

  // Start initialization
  init();
});
