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

  const detectionSection = document.getElementById('detection-section');
  const statusCard = document.getElementById('status-card');
  const detectionIconWrapper = document.getElementById('detection-icon-wrapper');
  const statusBadge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');
  const mediaTypeTag = document.getElementById('media-type-tag');
  const mediaTitle = document.getElementById('media-title');
  const sourceDomain = document.getElementById('source-domain');
  const streamsCount = document.getElementById('streams-count');

  const hostAlert = document.getElementById('host-alert');
  const btnSetupHost = document.getElementById('btn-setup-host');

  const actionGrid = document.getElementById('action-grid');
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

  const capsuleDropdownCue = document.getElementById('capsule-dropdown-cue');
  const sourceCountPill = document.getElementById('source-count-pill');
  const sourceDropdownMenu = document.getElementById('source-dropdown-menu');
  const sourceDropdownList = document.getElementById('source-dropdown-list');
  const dropdownSourceCount = document.getElementById('dropdown-source-count');

  const terminalContainer = document.getElementById('terminal-container');
  const terminalBody = document.getElementById('terminal-body');
  const btnTermCopy = document.getElementById('btn-term-copy');
  const btnTermClear = document.getElementById('btn-term-clear');

  const hostPill = document.getElementById('host-pill');
  const hostPillText = document.getElementById('host-pill-text');
  const footerPlaylistChip = document.getElementById('footer-playlist-chip');
  const footerFolder = document.getElementById('footer-folder');

  // SVG Detection Icons
  const ICONS = {
    video: `<svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
      <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM10 14.5v-5l4 2.5-4 2.5z"/>
    </svg>`,
    audio: `<svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 3v9.28c-.47-.17-.97-.28-1.5-.28C8.01 12 6 14.01 6 16.5S8.01 21 10.5 21c2.31 0 4.2-1.75 4.45-4H15V6h4V3h-7z"/>
    </svg>`,
    playlist: `<svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
      <path d="M4 10h12v2H4zm0-4h12v2H4zm0 8h8v2H4zm10 0v6l5-3z"/>
    </svg>`,
    idle: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    </svg>`
  };

  // Local state
  let currentTab = null;
  let tabMediaState = null;
  let detectedMediaList = [];
  let selectedMediaIndex = 0;
  let isSourceDropdownOpen = false;
  let currentSettings = {
    videoFormat: 'MP4',
    audioFormat: 'MP3',
    downloadFolder: 'FTODE',
    enableDebug: true
  };

  try {
    const cachedSettings = localStorage.getItem('ftode_settings');
    if (cachedSettings) {
      currentSettings = { ...currentSettings, ...JSON.parse(cachedSettings) };
    }
    const cachedTheme = localStorage.getItem('ftode_theme');
    if (cachedTheme === 'light') {
      document.documentElement.classList.add('light-theme');
      document.body.classList.add('light-theme');
    } else if (cachedTheme === 'dark') {
      document.documentElement.classList.remove('light-theme');
      document.body.classList.remove('light-theme');
    }
  } catch {}

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
      if (host.includes('youtube.com')) {
        if (path === '/watch' || path.startsWith('/shorts/') || path.startsWith('/live/') || path.startsWith('/embed/') || path.startsWith('/clip/')) {
          return false;
        }
        if (path === '/playlist' && search.includes('list=')) {
          return false;
        }
        return true;
      }
      if (host.includes('youtu.be')) {
        if (path === '/' || path === '') {
          return true;
        }
        return false;
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

  function extractDomainString(url) {
    if (!url || typeof url !== 'string') return 'No source';
    try {
      let cleanUrl = url.trim();
      if (cleanUrl.startsWith('blob:')) {
        cleanUrl = cleanUrl.replace(/^blob:/i, '');
      }
      const u = new URL(cleanUrl);
      const host = u.hostname.replace(/^www\./i, '');
      return host || 'No source';
    } catch {
      return 'No source';
    }
  }

  function normalizeMediaUrl(url) {
    if (!url || typeof url !== 'string') return '';
    try {
      const u = new URL(url);
      u.hash = '';
      const stripParams = ['range', 'bytes', 'start', 'end', 'chunk', 'segment', 'ts', 'offset', 'byte_offset', '_'];
      stripParams.forEach(p => u.searchParams.delete(p));
      return u.href;
    } catch {
      return url;
    }
  }

  function getDeduplicatedMediaItems(items) {
    if (!Array.isArray(items) || items.length === 0) return [];
    const result = [];
    const seenUrls = new Set();
    const seenNormalized = new Set();

    items.forEach(item => {
      if (!item || !item.url) return;
      const directUrl = item.url.trim();
      const normUrl = normalizeMediaUrl(directUrl);
      const key = `${item.type || 'video'}_${normUrl}`;

      if (!seenUrls.has(directUrl) && !seenNormalized.has(key)) {
        seenUrls.add(directUrl);
        seenNormalized.add(key);
        result.push(item);
      }
    });

    return result;
  }

  const STREAMING_DOMAINS = [
    'youtube.com',
    'youtu.be',
    'vimeo.com',
    'soundcloud.com',
    'twitch.tv',
    'tiktok.com',
    'twitter.com',
    'x.com',
    'reddit.com',
    'dailymotion.com',
    'bilibili.com',
    'instagram.com',
    'facebook.com',
    'fb.watch',
    'bandcamp.com',
    'rumble.com',
    'kick.com',
    'odysee.com',
    'mixcloud.com',
    'streamable.com',
    'bitchute.com',
    'threads.net'
  ];

  function isStreamingUrl(url) {
    if (!url) return false;
    if (isHomePageOrFeed(url)) return false;
    try {
      const hostname = new URL(url).hostname.toLowerCase();
      return STREAMING_DOMAINS.some(domain => hostname === domain || hostname.endsWith('.' + domain));
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
        try { localStorage.setItem('ftode_settings', JSON.stringify(currentSettings)); } catch {}
        currentJob = response.currentJob;

        // If the popup was just opened and the previous download was already complete/errored/cancelled,
        // immediately dismiss it so the user can download right away without waiting!
        if (currentJob && (currentJob.status === 'complete' || currentJob.status === 'error' || currentJob.status === 'cancelled')) {
          currentJob.status = 'idle';
          currentJob.thumbnail = null;
          currentJob.url = '';
          currentJob.pageUrl = '';
          currentJob.title = '';
          chrome.runtime.sendMessage({ type: 'DISMISS_JOB' }).catch(() => {});
        }
      }

      if (currentTab && currentTab.url && isHomePageOrFeed(currentTab.url)) {
        if (tabMediaState) {
          tabMediaState.items = [];
          tabMediaState.isStreamDomain = false;
          tabMediaState.isPlaylist = false;
          tabMediaState.hasMediaTags = false;
          tabMediaState.pageTitle = 'No media detected';
          tabMediaState.playlistTitle = null;
          tabMediaState.thumbnail = null;
        }
      } else if (currentTab && currentTab.url && isStreamingUrl(currentTab.url)) {
        if (!tabMediaState) {
          tabMediaState = {
            pageUrl: currentTab.url,
            pageTitle: (currentTab.title && currentTab.title.toLowerCase() !== 'youtube') ? currentTab.title : 'Media Stream',
            playlistTitle: null,
            isStreamDomain: true,
            isAudioOnly: isAudioOnlyUrl(currentTab.url),
            isPlaylist: isPlaylistPageUrl(currentTab.url),
            hasMediaTags: false,
            thumbnail: null,
            items: []
          };
        } else {
          tabMediaState.isStreamDomain = true;
          if (!tabMediaState.pageUrl) tabMediaState.pageUrl = currentTab.url;
        }
      }

      // Also trigger content script scan for immediate live update from top frame specifically
      if (currentTab && currentTab.id) {
        chrome.tabs.sendMessage(currentTab.id, { type: 'SCAN_MEDIA_DOM' }, { frameId: 0 }, (res) => {
          if (!chrome.runtime.lastError && res) {
            if (tabMediaState) {
              if (res.isTopFrame !== false) {
                tabMediaState.pageUrl = res.pageUrl || tabMediaState.pageUrl;
                tabMediaState.pageTitle = res.pageTitle || tabMediaState.pageTitle;
                tabMediaState.playlistTitle = res.playlistTitle || null;
                tabMediaState.isPlaylist = res.isPlaylist !== undefined ? res.isPlaylist : tabMediaState.isPlaylist;
                tabMediaState.isStreamDomain = res.isStreamDomain !== undefined ? res.isStreamDomain : isStreamingUrl(tabMediaState.pageUrl);
                tabMediaState.hasMediaTags = res.hasMediaTags;
                tabMediaState.thumbnail = res.thumbnail || null;
                if (Array.isArray(res.items)) {
                  const existingNetworkItems = (tabMediaState.items || []).filter(i => i.source === 'network');
                  const domItems = res.items.map(i => ({ ...i, source: 'dom' }));
                  tabMediaState.items = getDeduplicatedMediaItems([...domItems, ...existingNetworkItems]);
                }
              } else if (Array.isArray(res.items) && res.items.length > 0) {
                const domItems = res.items.map(i => ({ ...i, source: 'dom' }));
                tabMediaState.items = getDeduplicatedMediaItems([...(tabMediaState.items || []), ...domItems]);
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

      // Reveal GUI in fully loaded state without jumping/flashing
      document.body.classList.add('ready');
      requestAnimationFrame(() => {
        setTimeout(() => {
          document.documentElement.classList.remove('preload');
        }, 50);
      });
    } catch (err) {
      console.error('[Popup] Init error:', err);
      renderUI();
      document.body.classList.add('ready');
      document.documentElement.classList.remove('preload');
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
        if (hostPill) hostPill.className = 'status-chip host-chip';
        if (hostPillText) hostPillText.textContent = 'Host: Connected';
        if (hostAlert) hostAlert.classList.add('hidden');
      } else {
        isHostConnected = false;
        if (hostPill) hostPill.className = 'status-chip host-chip offline';
        if (hostPillText) hostPillText.textContent = 'Host: Disconnected';
        if (hostAlert) hostAlert.classList.remove('hidden');
      }
    } catch (e) {
      isHostConnected = false;
      if (hostPill) hostPill.className = 'status-chip host-chip offline';
      if (hostPillText) hostPillText.textContent = 'Host: Disconnected';
      if (hostAlert) hostAlert.classList.remove('hidden');
    }
  }

  const AUDIO_ONLY_DOMAINS = [
    'soundcloud.com',
    'bandcamp.com',
    'mixcloud.com',
    'audiomack.com',
    'spotify.com',
    'music.apple.com',
    'deezer.com',
    'tidal.com'
  ];

  function isAudioOnlyUrl(url) {
    if (!url) return false;
    try {
      const host = new URL(url).hostname.toLowerCase();
      return AUDIO_ONLY_DOMAINS.some(d => host === d || host.endsWith('.' + d));
    } catch {
      return false;
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
   * Extract best video or media thumbnail URL
   */
  function getMediaThumbnail(url, state) {
    if (!url) return (state && state.thumbnail) || null;
    try {
      const u = new URL(url);
      const host = u.hostname.toLowerCase();
      if (host.includes('youtube.com')) {
        if (u.searchParams.has('v')) {
          return `https://i.ytimg.com/vi/${u.searchParams.get('v')}/mqdefault.jpg`;
        }
        const parts = u.pathname.split('/').filter(Boolean);
        const shortsIdx = parts.indexOf('shorts');
        if (shortsIdx !== -1 && parts[shortsIdx + 1]) {
          return `https://i.ytimg.com/vi/${parts[shortsIdx + 1]}/mqdefault.jpg`;
        }
        const embedIdx = parts.indexOf('embed');
        if (embedIdx !== -1 && parts[embedIdx + 1]) {
          return `https://i.ytimg.com/vi/${parts[embedIdx + 1]}/mqdefault.jpg`;
        }
        const liveIdx = parts.indexOf('live');
        if (liveIdx !== -1 && parts[liveIdx + 1]) {
          return `https://i.ytimg.com/vi/${parts[liveIdx + 1]}/mqdefault.jpg`;
        }
        const vIdx = parts.indexOf('v');
        if (vIdx !== -1 && parts[vIdx + 1]) {
          return `https://i.ytimg.com/vi/${parts[vIdx + 1]}/mqdefault.jpg`;
        }
      } else if (host.includes('youtu.be')) {
        const id = u.pathname.replace(/^\//, '').split('/')[0].split('?')[0];
        if (id) return `https://i.ytimg.com/vi/${id}/mqdefault.jpg`;
      }
      return (state && state.thumbnail) || null;
    } catch {
      return (state && state.thumbnail) || null;
    }
  }

  /**
   * Render either the media thumbnail or the fallback SVG icon
   */
  function renderDetectionIcon(type, thumbUrl) {
    detectionIconWrapper.replaceChildren();
    if (thumbUrl) {
      detectionIconWrapper.classList.add('has-thumb');
      const img = document.createElement('img');
      img.className = 'detection-thumb-img';
      img.alt = 'Thumbnail';
      img.onerror = () => {
        detectionIconWrapper.classList.remove('has-thumb');
        detectionIconWrapper.innerHTML = ICONS[type] || ICONS.idle;
      };
      img.src = thumbUrl;
      detectionIconWrapper.appendChild(img);
    } else {
      detectionIconWrapper.classList.remove('has-thumb');
      detectionIconWrapper.innerHTML = ICONS[type] || ICONS.idle;
    }
  }

  /**
   * Helper to check if there is an active running download job
   */
  function isJobActive() {
    return Boolean(currentJob && currentJob.status && currentJob.status !== 'idle');
  }

  /**
   * Toggle the source selection dropdown menu
   */
  function toggleSourceDropdown(forceState) {
    if (isJobActive() || detectedMediaList.length <= 1) {
      isSourceDropdownOpen = false;
      if (sourceDropdownMenu) sourceDropdownMenu.classList.add('hidden');
      if (statusCard) {
        statusCard.classList.remove('dropdown-open');
        statusCard.setAttribute('aria-expanded', 'false');
      }
      return;
    }

    if (typeof forceState === 'boolean') {
      isSourceDropdownOpen = forceState;
    } else {
      isSourceDropdownOpen = !isSourceDropdownOpen;
    }

    if (isSourceDropdownOpen) {
      if (sourceDropdownMenu) sourceDropdownMenu.classList.remove('hidden');
      if (statusCard) {
        statusCard.classList.add('dropdown-open');
        statusCard.setAttribute('aria-expanded', 'true');
      }
    } else {
      if (sourceDropdownMenu) sourceDropdownMenu.classList.add('hidden');
      if (statusCard) {
        statusCard.classList.remove('dropdown-open');
        statusCard.setAttribute('aria-expanded', 'false');
      }
    }
  }

  /**
   * Render individual stream source options in the selection dropdown
   */
  function renderSourceDropdownList(items, selectedIdx) {
    if (!sourceDropdownList) return;
    sourceDropdownList.innerHTML = '';

    items.forEach((item, index) => {
      const isSelected = (index === selectedIdx);
      const row = document.createElement('div');
      row.className = 'source-dropdown-item' + (isSelected ? ' active' : '');
      row.setAttribute('role', 'option');
      row.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      row.tabIndex = 0;

      // Thumbnail / format icon
      const thumbWrap = document.createElement('div');
      thumbWrap.className = 'source-item-thumb ' + (item.type === 'audio' ? 'audio-type' : 'video-type');

      const itemThumb = item.thumbnail || item.poster || getMediaThumbnail(item.url, tabMediaState);
      if (itemThumb) {
        const img = document.createElement('img');
        img.className = 'source-item-thumb-img';
        img.src = itemThumb;
        img.alt = 'Thumbnail';
        img.onerror = () => {
          thumbWrap.innerHTML = item.type === 'audio' ? ICONS.audio : ICONS.video;
        };
        thumbWrap.appendChild(img);
      } else {
        thumbWrap.innerHTML = item.type === 'audio' ? ICONS.audio : ICONS.video;
      }

      // Information
      const info = document.createElement('div');
      info.className = 'source-item-info';

      const title = document.createElement('span');
      title.className = 'source-item-title';
      title.textContent = item.title || `Media Stream #${index + 1}`;
      title.title = item.url;

      const meta = document.createElement('span');
      meta.className = 'source-item-meta';
      const sizeStr = item.sizeBytes ? ` • ${(item.sizeBytes / (1024 * 1024)).toFixed(1)} MB` : '';
      const mimeStr = item.isManifest ? 'Adaptive Manifest' : (item.mimeType || (item.type || 'video').toUpperCase());
      const resStr = (item.width && item.height) ? ` • ${item.width}x${item.height}` : '';
      meta.textContent = `${(item.type || 'video').toUpperCase()} • ${mimeStr}${resStr}${sizeStr}`;

      info.appendChild(title);
      info.appendChild(meta);

      // Checkmark icon
      const check = document.createElement('div');
      check.className = 'source-item-check';
      check.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

      row.appendChild(thumbWrap);
      row.appendChild(info);
      row.appendChild(check);

      const selectThisItem = (e) => {
        e.stopPropagation();
        selectedMediaIndex = index;
        toggleSourceDropdown(false);
        renderUI();
      };

      row.addEventListener('click', selectThisItem);
      row.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectThisItem(e);
        }
      });

      sourceDropdownList.appendChild(row);
    });
  }

  /**
   * Render detection and media status in the Popup UI
   */
  function renderUI() {
    const hasActiveJob = isJobActive();
    const isHome = currentTab && isHomePageOrFeed(currentTab.url);
    const activeUrl = (hasActiveJob && currentJob && (currentJob.pageUrl || currentJob.url)) || (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || '';
    const isAudioDomain = !isHome && (isAudioOnlyUrl(activeUrl) || Boolean(tabMediaState && tabMediaState.isAudioOnly));

    // 1. Settings & Button Labels
    const isPlaylist = hasActiveJob ? Boolean(currentJob.isPlaylist) : (!isHome && ((tabMediaState && tabMediaState.isPlaylist) || (currentTab && isPlaylistPageUrl(currentTab.url))));

    if (isPlaylist && tabMediaState && tabMediaState.playlistTitle) {
      footerFolder.textContent = `Current Playlist: ${tabMediaState.playlistTitle}`;
    } else if (isPlaylist && hasActiveJob && currentJob.title) {
      footerFolder.textContent = `Current Playlist: ${currentJob.title}`;
    } else {
      footerFolder.textContent = `Folder: ${currentSettings.downloadFolder || 'FTODE'}`;
    }

    // 2. Build media stream items list
    const isStream = isHome ? false : (
      (tabMediaState && tabMediaState.isStreamDomain) ||
      isStreamingUrl(activeUrl)
    );
    const rawItems = (!isHome && tabMediaState && tabMediaState.items) ? tabMediaState.items : [];
    let uniqueItems = getDeduplicatedMediaItems(rawItems);

    let defaultPageTitle = (tabMediaState && tabMediaState.isPlaylist && tabMediaState.playlistTitle) ||
                           (tabMediaState && tabMediaState.pageTitle && tabMediaState.pageTitle !== 'No media detected' && tabMediaState.pageTitle !== 'Media Stream' ? tabMediaState.pageTitle : '') ||
                           (currentTab && currentTab.title && currentTab.title.toLowerCase() !== 'youtube' ? currentTab.title : '') ||
                           (tabMediaState && tabMediaState.pageTitle) ||
                           'Media Stream';
    defaultPageTitle = defaultPageTitle.replace(/^\(\d+\+?\)\s*/, '').replace(/^[▶►]\s*/, '').trim();
    defaultPageTitle = defaultPageTitle.replace(/^(?:\[?\s*(?:Unpaid\/Self Promotion|Self Promotion|Sponsor(?:ed)?|Interaction(?: Reminder)?|Intro|Outro|Preview|Filler|Highlight|Music: Non-Music Section|Exclusive Access|Patreon)\s*\]?)\s*[-:]?\s*/i, '');
    defaultPageTitle = defaultPageTitle.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();

    if (!isHome && (isStream || isPlaylist || uniqueItems.length === 0) && (isStream || isPlaylist || (currentTab && currentTab.url && isStreamingUrl(currentTab.url)))) {
      // If on a stream site and no network/dom items were gathered yet or 0 items, ensure the primary page stream is present
      if (uniqueItems.length === 0) {
        uniqueItems.push({
          type: isAudioDomain ? 'audio' : 'video',
          url: currentTab ? currentTab.url : (tabMediaState ? tabMediaState.pageUrl : ''),
          mimeType: 'Adaptive Stream (HD/4K)',
          isBlob: false,
          isManifest: true,
          title: defaultPageTitle,
          thumbnail: (tabMediaState ? tabMediaState.thumbnail : null) || getMediaThumbnail(activeUrl, tabMediaState)
        });
      }
    }

    detectedMediaList = uniqueItems;
    if (selectedMediaIndex >= detectedMediaList.length) {
      selectedMediaIndex = 0;
    }

    const selectedItem = detectedMediaList.length > 0 ? detectedMediaList[selectedMediaIndex] : null;

    const hasVideo = !isHome && !isAudioDomain && (isStream || detectedMediaList.some(i => i.type === 'video'));
    const hasAudio = !isHome && (isAudioDomain || isStream || detectedMediaList.some(i => i.type === 'audio'));
    const hasAnyMedia = hasActiveJob || (!isHome && (isPlaylist || hasVideo || hasAudio || detectedMediaList.length > 0));

    // Determine display title & domain
    let displayTitle = hasActiveJob && currentJob.title ? currentJob.title : (hasAnyMedia ? (selectedItem && selectedItem.title ? selectedItem.title : defaultPageTitle) : 'No media detected');

    // Website link/domain determination (prioritize the page URL, fallback to media URL)
    const sourceUrlForDomain = (hasActiveJob && currentJob && (currentJob.pageUrl || currentJob.url)) ||
                               (currentTab && currentTab.url) ||
                               (tabMediaState && tabMediaState.pageUrl) ||
                               (selectedItem && selectedItem.url) ||
                               '';
    const domainStr = extractDomainString(sourceUrlForDomain);

    if (displayTitle) {
      displayTitle = displayTitle.replace(/^\(\d+\+?\)\s*/, '').replace(/^[▶►]\s*/, '').trim();
      displayTitle = displayTitle.replace(/^(?:\[?\s*(?:Unpaid\/Self Promotion|Self Promotion|Sponsor(?:ed)?|Interaction(?: Reminder)?|Intro|Outro|Preview|Filler|Highlight|Music: Non-Music Section|Exclusive Access|Patreon)\s*\]?)\s*[-:]?\s*/i, '');
      displayTitle = displayTitle.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();
    }

    mediaTitle.textContent = displayTitle;
    mediaTitle.title = displayTitle;
    sourceDomain.textContent = domainStr;
    sourceDomain.title = sourceUrlForDomain || domainStr;
    if (streamsCount) streamsCount.textContent = hasAnyMedia ? (isPlaylist ? 'Full Playlist Batch' : (isStream ? (isAudioDomain ? 'SoundCloud Audio Stream' : 'High Quality Media Stream') : `${detectedMediaList.length} media source(s)`)) : 'No media detected';

    let thumbUrl = null;
    if (hasActiveJob) {
      thumbUrl = (currentJob && currentJob.thumbnail) ||
                 (tabMediaState ? tabMediaState.thumbnail : null) ||
                 getMediaThumbnail(currentJob ? (currentJob.pageUrl || currentJob.url) : null, tabMediaState);
    } else if (!isHome && hasAnyMedia) {
      thumbUrl = (selectedItem && (selectedItem.thumbnail || selectedItem.poster)) ||
                 (tabMediaState ? tabMediaState.thumbnail : null) ||
                 getMediaThumbnail(selectedItem ? selectedItem.url : activeUrl, tabMediaState);
    }

    // Status Card & Header Label Theming
    if (detectionSection) detectionSection.className = 'detection-section';
    statusCard.className = 'status-card';
    if (statusBadge) statusBadge.className = 'status-badge';

    // Dropdown Cue and List Management
    const canDropdown = !hasActiveJob && !isHome && detectedMediaList.length > 1;
    if (canDropdown) {
      statusCard.classList.add('is-dropdown');
      if (capsuleDropdownCue) {
        capsuleDropdownCue.classList.remove('hidden');
        if (sourceCountPill) sourceCountPill.textContent = detectedMediaList.length;
      }
      if (dropdownSourceCount) dropdownSourceCount.textContent = detectedMediaList.length;
      renderSourceDropdownList(detectedMediaList, selectedMediaIndex);
      if (isSourceDropdownOpen) {
        statusCard.classList.add('dropdown-open');
        statusCard.setAttribute('aria-expanded', 'true');
        if (sourceDropdownMenu) sourceDropdownMenu.classList.remove('hidden');
      } else {
        statusCard.classList.remove('dropdown-open');
        statusCard.setAttribute('aria-expanded', 'false');
        if (sourceDropdownMenu) sourceDropdownMenu.classList.add('hidden');
      }
    } else {
      isSourceDropdownOpen = false;
      statusCard.classList.remove('is-dropdown', 'dropdown-open');
      statusCard.setAttribute('aria-expanded', 'false');
      if (capsuleDropdownCue) capsuleDropdownCue.classList.add('hidden');
      if (sourceDropdownMenu) sourceDropdownMenu.classList.add('hidden');
    }

    const selectedIsAudio = selectedItem ? (selectedItem.type === 'audio') : isAudioDomain;

    if (hasActiveJob) {
      const isJobAudio = currentJob.mediaType === 'audio' || (currentJob.format && ['mp3', 'm4a', 'wav', 'flac', 'ogg', 'aac', 'opus'].includes(String(currentJob.format).toLowerCase()));
      const isJobPlaylist = Boolean(currentJob.isPlaylist);

      if (isJobPlaylist) {
        if (detectionSection) detectionSection.classList.add('playlist-detected');
        statusCard.classList.add('playlist-detected');
        if (statusBadge) statusBadge.classList.add('playlist-detected');
        statusText.textContent = isJobAudio ? 'Downloading Audio Playlist...' : 'Downloading Playlist...';
        if (mediaTypeTag) mediaTypeTag.textContent = 'PLAYLIST';
        renderDetectionIcon('playlist', thumbUrl);
      } else if (isJobAudio) {
        if (detectionSection) detectionSection.classList.add('audio-detected');
        statusCard.classList.add('audio-detected');
        if (statusBadge) statusBadge.classList.add('audio-detected');
        statusText.textContent = 'Downloading Audio...';
        if (mediaTypeTag) mediaTypeTag.textContent = 'AUDIO';
        renderDetectionIcon('audio', thumbUrl);
      } else {
        if (detectionSection) detectionSection.classList.add('video-detected');
        statusCard.classList.add('video-detected');
        if (statusBadge) statusBadge.classList.add('video-detected');
        statusText.textContent = 'Downloading Video...';
        if (mediaTypeTag) mediaTypeTag.textContent = 'VIDEO';
        renderDetectionIcon('video', thumbUrl);
      }

      btnDownloadVideo.disabled = true;
      btnDownloadAudio.disabled = true;
    } else if (isPlaylist) {
      if (detectionSection) detectionSection.classList.add('playlist-detected');
      statusCard.classList.add('playlist-detected');
      if (statusBadge) statusBadge.classList.add('playlist-detected');
      statusText.textContent = isAudioDomain ? 'Audio Playlist / Album' : 'Playlist Detected';
      if (mediaTypeTag) mediaTypeTag.textContent = 'PLAYLIST';
      renderDetectionIcon('playlist', thumbUrl);

      btnDownloadVideo.disabled = isAudioDomain;
      btnDownloadAudio.disabled = false;
    } else if (selectedIsAudio || (hasAudio && !hasVideo)) {
      if (detectionSection) detectionSection.classList.add('audio-detected');
      statusCard.classList.add('audio-detected');
      if (statusBadge) statusBadge.classList.add('audio-detected');
      statusText.textContent = 'Audio Stream Detected';
      if (mediaTypeTag) mediaTypeTag.textContent = 'AUDIO';
      renderDetectionIcon('audio', thumbUrl);

      btnDownloadVideo.disabled = true;
      btnDownloadAudio.disabled = false;
    } else if (hasVideo || isStream || detectedMediaList.length > 0) {
      if (detectionSection) detectionSection.classList.add('video-detected');
      statusCard.classList.add('video-detected');
      if (statusBadge) statusBadge.classList.add('video-detected');
      statusText.textContent = 'Video Stream Detected';
      if (mediaTypeTag) mediaTypeTag.textContent = 'VIDEO';
      renderDetectionIcon('video', thumbUrl);

      btnDownloadVideo.disabled = false;
      btnDownloadAudio.disabled = false;
    } else {
      if (detectionSection) detectionSection.classList.add('no-media');
      statusCard.classList.add('no-media');
      if (statusBadge) statusBadge.classList.add('no-media');
      statusText.textContent = 'No Media Detected';
      if (mediaTypeTag) mediaTypeTag.textContent = 'IDLE';
      renderDetectionIcon('idle', null);

      btnDownloadVideo.disabled = true;
      btnDownloadAudio.disabled = true;
    }

    // 3. Active Download Job UI
    renderJobState();
  }

  let errorDismissTimer = null;

  function dismissJobWithAnimation() {
    if (progressSection && !progressSection.classList.contains('hidden')) {
      progressSection.classList.add('is-leaving');
      setTimeout(() => {
        progressSection.classList.add('hidden');
        progressSection.classList.remove('is-leaving');
        if (currentJob) {
          currentJob.status = 'idle';
          currentJob.thumbnail = null;
          currentJob.url = '';
          currentJob.pageUrl = '';
          currentJob.title = '';
        }
        if (actionGrid) {
          actionGrid.classList.remove('hidden');
          actionGrid.classList.add('is-entering');
          setTimeout(() => actionGrid.classList.remove('is-entering'), 300);
        }
        chrome.runtime.sendMessage({ type: 'DISMISS_JOB' }).catch(() => {});
      }, 180);
    } else {
      if (currentJob) {
        currentJob.status = 'idle';
        currentJob.thumbnail = null;
        currentJob.url = '';
        currentJob.pageUrl = '';
        currentJob.title = '';
      }
      if (actionGrid) actionGrid.classList.remove('hidden');
      chrome.runtime.sendMessage({ type: 'DISMISS_JOB' }).catch(() => {});
    }
  }

  /**
   * Render active download progress & logs
   */
  function renderJobState() {
    const isJobActive = currentJob && currentJob.status && currentJob.status !== 'idle';

    if (!isJobActive) {
      progressSection.classList.add('hidden');
      if (actionGrid) actionGrid.classList.remove('hidden');
      return;
    }

    // Smoothly reveal progress section if action grid was visible
    if (actionGrid && !actionGrid.classList.contains('hidden')) {
      actionGrid.classList.add('hidden');
      progressSection.classList.remove('hidden');
      progressSection.classList.add('is-entering');
      setTimeout(() => progressSection.classList.remove('is-entering'), 350);
    } else {
      progressSection.classList.remove('hidden');
    }

    const percent = Math.round(currentJob.percent || 0);
    progressPercent.textContent = `${percent}%`;
    progressFill.style.width = `${percent}%`;

    if (progressStatus) progressStatus.style.color = '';

    if (currentJob.status === 'downloading') {
      if (errorDismissTimer) {
        clearTimeout(errorDismissTimer);
        errorDismissTimer = null;
      }
      progressFill.style.background = 'var(--accent-video)';
      const isPl = currentJob.isPlaylist;
      if (progressStatus) progressStatus.textContent = isPl ? 'Downloading Playlist...' : `Downloading ${(currentJob.mediaType || 'Media').toUpperCase()}...`;
      metricSpeed.textContent = currentJob.speed || 'Starting...';
      metricEta.textContent = currentJob.eta || '--:--';
      btnCancelJob.classList.remove('hidden');
    } else if (currentJob.status === 'remuxing') {
      if (errorDismissTimer) {
        clearTimeout(errorDismissTimer);
        errorDismissTimer = null;
      }
      progressFill.style.background = 'var(--accent-video)';
      const isPl = currentJob.isPlaylist;
      progressPercent.textContent = `${percent}%`;
      if (progressStatus) progressStatus.textContent = isPl ? 'Processing Playlist Tracks...' : 'Merging & Converting Formats...';
      metricSpeed.textContent = currentJob.speed || 'Processing...';
      metricEta.textContent = currentJob.eta || '--:--';
      btnCancelJob.classList.remove('hidden');
    } else if (currentJob.status === 'complete') {
      progressPercent.textContent = 'Completed!';
      if (progressStatus) progressStatus.textContent = 'Download Complete!';
      progressFill.style.width = '100%';
      progressFill.style.background = 'var(--accent-video)';
      metricSpeed.textContent = 'Saved';
      metricEta.textContent = '00:00';
      btnCancelJob.classList.add('hidden');

      if (!errorDismissTimer) {
        errorDismissTimer = setTimeout(() => {
          dismissJobWithAnimation();
          errorDismissTimer = null;
        }, 4000);
      }
    } else if (currentJob.status === 'cancelled') {
      progressPercent.textContent = 'Cancelled';
      if (progressStatus) {
        progressStatus.textContent = 'Download Cancelled';
        progressStatus.style.color = '#ef4444';
      }
      progressFill.style.background = 'var(--accent-cancel)';
      metricSpeed.textContent = 'Stopped';
      metricEta.textContent = '--';
      btnCancelJob.classList.add('hidden');

      if (!errorDismissTimer) {
        errorDismissTimer = setTimeout(() => {
          dismissJobWithAnimation();
          errorDismissTimer = null;
        }, 4000);
      }
    } else if (currentJob.status === 'error') {
      progressPercent.textContent = 'Failed';
      if (progressStatus) {
        progressStatus.textContent = currentJob.error || 'Download Failed';
        progressStatus.style.color = '#ef4444';
      }
      progressFill.style.background = 'var(--accent-error)';
      metricSpeed.textContent = 'Failed';
      metricEta.textContent = '--';
      btnCancelJob.classList.add('hidden');

      if (!errorDismissTimer) {
        errorDismissTimer = setTimeout(() => {
          dismissJobWithAnimation();
          errorDismissTimer = null;
        }, 4000);
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
      if (btnToggleTerminal) {
        btnToggleTerminal.style.background = 'var(--bg-circle-btn-hover)';
        btnToggleTerminal.style.color = 'var(--accent-video)';
      }
    } else {
      terminalContainer.classList.add('hidden');
      if (btnToggleTerminal) {
        btnToggleTerminal.style.background = '';
        btnToggleTerminal.style.color = '';
      }
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

    const activeThumb = (tabMediaState ? tabMediaState.thumbnail : null) ||
                        getMediaThumbnail(url, tabMediaState) ||
                        getMediaThumbnail(currentTab ? currentTab.url : null, tabMediaState);

    // Smoothly transition from action buttons to download progress bar
    currentJob = {
      id: 'job_' + Date.now(),
      status: 'downloading',
      url: url,
      pageUrl: currentTab ? currentTab.url : url,
      mediaType: targetType,
      format: format,
      title: title,
      thumbnail: activeThumb,
      percent: 0,
      speed: 'Starting...',
      eta: '--:--',
      isPlaylist: isPlaylist,
      logs: [
        `[INFO] Starting ${isPlaylist ? 'playlist batch' : targetType} download: "${title}"`,
        `[INFO] Target format: ${format.toUpperCase()}`
      ]
    };
    renderJobState();

    try {
      const res = await chrome.runtime.sendMessage({
        type: 'START_DOWNLOAD',
        payload: {
          url: url,
          pageUrl: currentTab ? currentTab.url : url,
          title: title,
          thumbnail: activeThumb,
          mediaType: targetType,
          targetType: targetType,
          format: format,
          isPlaylist: isPlaylist
        }
      });

      if (res && res.status === 'error') {
        alert(`Could not start download: ${res.message}`);
        currentJob.status = 'error';
        currentJob.error = res.message;
        renderJobState();
      }
    } catch (err) {
      console.error('[Popup] Start download error:', err);
      alert(`Download trigger error: ${err.message}`);
      currentJob.status = 'error';
      currentJob.error = err.message;
      renderJobState();
    }
  }

  // ==========================================================================
  // Event Listeners
  // ==========================================================================

  // Action Buttons
  btnDownloadVideo.addEventListener('click', () => {
    const selectedItem = detectedMediaList.length > 0 ? detectedMediaList[selectedMediaIndex] : null;
    const pageUrl = (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || '';
    let targetUrl = (selectedItem && selectedItem.url) || pageUrl;

    const isDedicatedPlatform = pageUrl && (
      pageUrl.includes('youtube.com') ||
      pageUrl.includes('youtu.be') ||
      pageUrl.includes('soundcloud.com') ||
      pageUrl.includes('vimeo.com') ||
      pageUrl.includes('twitch.tv') ||
      pageUrl.includes('tiktok.com')
    );

    if (isDedicatedPlatform && (!selectedItem || selectedItem.isBlob || selectedItem.url === pageUrl)) {
      targetUrl = pageUrl;
    }

    let title = (selectedItem && selectedItem.title) ||
                (tabMediaState && tabMediaState.playlistTitle) ||
                (tabMediaState && tabMediaState.pageTitle && tabMediaState.pageTitle !== 'Media Stream' && tabMediaState.pageTitle !== 'No media detected' ? tabMediaState.pageTitle : '') ||
                (currentTab ? currentTab.title : '');
    if (title) {
      title = title.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();
    }
    startDownloadJob('video', targetUrl, title);
  });

  btnDownloadAudio.addEventListener('click', () => {
    const selectedItem = detectedMediaList.length > 0 ? detectedMediaList[selectedMediaIndex] : null;
    const pageUrl = (currentTab && currentTab.url) || (tabMediaState && tabMediaState.pageUrl) || '';
    let targetUrl = (selectedItem && selectedItem.url) || pageUrl;

    const isDedicatedPlatform = pageUrl && (
      pageUrl.includes('youtube.com') ||
      pageUrl.includes('youtu.be') ||
      pageUrl.includes('soundcloud.com') ||
      pageUrl.includes('vimeo.com') ||
      pageUrl.includes('twitch.tv') ||
      pageUrl.includes('tiktok.com')
    );

    if (isDedicatedPlatform && (!selectedItem || selectedItem.isBlob || selectedItem.url === pageUrl)) {
      targetUrl = pageUrl;
    }

    let title = (selectedItem && selectedItem.title) ||
                (tabMediaState && tabMediaState.playlistTitle) ||
                (tabMediaState && tabMediaState.pageTitle && tabMediaState.pageTitle !== 'Media Stream' && tabMediaState.pageTitle !== 'No media detected' ? tabMediaState.pageTitle : '') ||
                (currentTab ? currentTab.title : '');
    if (title) {
      title = title.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();
    }
    startDownloadJob('audio', targetUrl, title);
  });

  // Main Capsule selection dropdown toggle
  statusCard.addEventListener('click', (e) => {
    if (detectedMediaList.length > 1 && !isJobActive()) {
      toggleSourceDropdown();
    }
  });

  statusCard.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      if (detectedMediaList.length > 1 && !isJobActive()) {
        e.preventDefault();
        toggleSourceDropdown();
      }
    }
  });

  // Close dropdown on click outside or Escape
  document.addEventListener('click', (e) => {
    if (!isSourceDropdownOpen) return;
    if (statusCard && !statusCard.contains(e.target) && sourceDropdownMenu && !sourceDropdownMenu.contains(e.target)) {
      toggleSourceDropdown(false);
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isSourceDropdownOpen) {
      toggleSourceDropdown(false);
    }
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

  btnCancelJob.addEventListener('click', async () => {
    if (currentJob) {
      currentJob.status = 'cancelled';
      renderJobState();
    }
    await chrome.runtime.sendMessage({ type: 'CANCEL_DOWNLOAD' });
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
      if (currentJob && currentJob.status === 'cancelled' && message.job && message.job.status !== 'cancelled' && message.job.status !== 'idle') {
        return;
      }
      currentJob = message.job;
      renderJobState();
    }
  });

  // Dismiss completed / errored / cancelled job immediately when popup closes (click outside)
  const handlePopupDismiss = () => {
    if (currentJob && (currentJob.status === 'complete' || currentJob.status === 'error' || currentJob.status === 'cancelled')) {
      chrome.runtime.sendMessage({ type: 'DISMISS_JOB' }).catch(() => {});
    }
  };
  window.addEventListener('pagehide', handlePopupDismiss);
  window.addEventListener('beforeunload', handlePopupDismiss);

  /**
   * Theme Management (Synchronized with Options)
   */
  async function applyTheme() {
    try {
      const data = await chrome.storage.sync.get({ theme: 'dark' });
      const isLight = data.theme === 'light';
      if (isLight) {
        document.documentElement.classList.add('light-theme');
        document.body.classList.add('light-theme');
        try { localStorage.setItem('ftode_theme', 'light'); } catch {}
      } else {
        document.documentElement.classList.remove('light-theme');
        document.body.classList.remove('light-theme');
        try { localStorage.setItem('ftode_theme', 'dark'); } catch {}
      }
    } catch (e) {
      console.error('[Popup] Theme load error:', e);
    }
  }

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'sync' && changes.theme) {
      const isLight = changes.theme.newValue === 'light';
      if (isLight) {
        document.documentElement.classList.add('light-theme');
        document.body.classList.add('light-theme');
        try { localStorage.setItem('ftode_theme', 'light'); } catch {}
      } else {
        document.documentElement.classList.remove('light-theme');
        document.body.classList.remove('light-theme');
        try { localStorage.setItem('ftode_theme', 'dark'); } catch {}
      }
    }
  });

  // Safety timeout fallback to guarantee GUI is revealed
  setTimeout(() => {
    document.documentElement.classList.remove('preload');
    document.body.classList.add('ready');
  }, 150);

  // Start initialization
  await applyTheme();
  await init();
});
