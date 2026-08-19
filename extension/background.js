/**
 * Finally that online downloader extension (FTODE) - Background Service Worker
 * Coordinates Dual-Pass media detection, tab state, browser badges,
 * and Native Messaging communication with the Python yt-dlp backend.
 */

const NATIVE_HOST_NAME = 'com.ftode.host';

const DEFAULT_SETTINGS = {
  videoFormat: 'MP4',
  audioFormat: 'MP3',
  downloadFolder: 'FTODE',
  enableDebug: true,
  videoQuality: 'best',
  audioQuality: 'best',
  existingFileAction: 'copy', // 'copy' (add (1)) | 'skip' | 'overwrite'
  customYtdlpPath: '',
  customFfmpegPath: ''
};

async function getSettings() {
  try {
    const data = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    return { ...DEFAULT_SETTINGS, ...data };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

// In-memory tab media store: tabId -> { pageUrl, pageTitle, isStreamDomain, items: [], lastUpdated }
const tabMediaStore = new Map();

// Active download job tracking
let currentJob = {
  id: null,
  url: '',
  title: '',
  mediaType: 'video',
  format: 'mp4',
  status: 'idle', // 'idle' | 'downloading' | 'remuxing' | 'complete' | 'error'
  percent: 0,
  speed: '',
  eta: '',
  line: '',
  logs: [],
  error: null,
  resultFile: null,
  startTime: null
};

// Active Native Messaging port
let nativePort = null;

/**
 * Initialize default settings in storage if not set
 */
chrome.runtime.onInstalled.addListener(async () => {
  try {
    const existing = await chrome.storage.sync.get(null);
    const toSet = {};
    for (const [key, value] of Object.entries(DEFAULT_SETTINGS)) {
      if (existing[key] === undefined) {
        toSet[key] = value;
      }
    }
    if (Object.keys(toSet).length > 0) {
      await chrome.storage.sync.set(toSet);
    }
  } catch (err) {
    console.error('[FTODE] Storage init error:', err);
  }
});

/**
 * Get or create tab media state
 */
function getOrCreateTabState(tabId) {
  if (!tabMediaStore.has(tabId)) {
    tabMediaStore.set(tabId, {
      tabId,
      pageUrl: '',
      pageTitle: '',
      isStreamDomain: false,
      hasMediaTags: false,
      items: [],
      lastUpdated: Date.now()
    });
  }
  return tabMediaStore.get(tabId);
}

/**
 * Update Chrome extension badge for a tab based on detected media count
 */
function updateTabBadge(tabId) {
  const state = tabMediaStore.get(tabId);
  if (!state || isHomePageOrFeed(state.pageUrl)) {
    chrome.action.setBadgeText({ text: '', tabId }).catch(() => {});
    return;
  }

  if (state.isPlaylist) {
    chrome.action.setBadgeText({ text: 'LIST', tabId }).catch(() => {});
    chrome.action.setBadgeBackgroundColor({ color: '#8b5cf6', tabId }).catch(() => {});
    return;
  }

  if (state.isStreamDomain) {
    chrome.action.setBadgeText({ text: '1', tabId }).catch(() => {});
    chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId }).catch(() => {});
    return;
  }

  const hasVideo = state.items.some(i => i.type === 'video');
  const hasAudio = state.items.some(i => i.type === 'audio');
  const count = state.items.length;

  if (count > 0) {
    chrome.action.setBadgeText({ text: String(count), tabId }).catch(() => {});
    if (hasVideo) {
      chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId }).catch(() => {});
    } else if (hasAudio) {
      chrome.action.setBadgeBackgroundColor({ color: '#06b6d4', tabId }).catch(() => {});
    } else {
      chrome.action.setBadgeBackgroundColor({ color: '#6366f1', tabId }).catch(() => {});
    }
  } else {
    chrome.action.setBadgeText({ text: '', tabId }).catch(() => {});
  }
}

/**
 * Known streaming domains
 */
const KNOWN_STREAMING_DOMAINS = [
  'youtube.com', 'youtu.be', 'vimeo.com', 'soundcloud.com', 'twitch.tv',
  'tiktok.com', 'twitter.com', 'x.com', 'reddit.com', 'dailymotion.com',
  'bilibili.com', 'instagram.com', 'facebook.com', 'fb.watch',
  'bandcamp.com', 'rumble.com', 'kick.com', 'odysee.com', 'mixcloud.com'
];

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

function isStreamingUrl(url) {
  if (!url) return false;
  if (isHomePageOrFeed(url)) return false;
  try {
    const host = new URL(url).hostname.toLowerCase();
    return KNOWN_STREAMING_DOMAINS.some(d => host === d || host.endsWith('.' + d));
  } catch {
    return false;
  }
}

function isPlaylistUrl(url) {
  if (!url) return false;
  if (isHomePageOrFeed(url)) return false;
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    const path = u.pathname.toLowerCase();
    const search = u.search.toLowerCase();

    // YouTube Playlists (only dedicated playlist view pages, not single watch pages)
    if (host.includes('youtube.com') || host.includes('youtu.be')) {
      if (path.includes('/playlist') && search.includes('list=')) {
        return true;
      }
    }
    // SoundCloud Sets / Playlists
    if (host.includes('soundcloud.com') && (path.includes('/sets/') || path.includes('/albums/'))) {
      return true;
    }
    // Bandcamp Albums
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
 * PASS 2: Network Sniffing Engine
 * Intercepts media responses via chrome.webRequest.onHeadersReceived
 */
const MEDIA_EXT_REGEX = /\.(mp4|webm|mkv|mov|avi|flv|m3u8|mpd|m4s|ts|mp3|m4a|flac|wav|ogg|opus|aac)(\?.*)?$/i;

chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    // Only monitor valid tab requests (ignore background or internal -1)
    if (details.tabId < 0) return;

    const url = details.url;
    // Ignore internal / extension / tracking assets
    if (url.startsWith('chrome-extension://') || url.startsWith('blob:') || url.startsWith('data:') || url.includes('google-analytics')) return;

    // Ignore known UI notification sound effects
    if (url.endsWith('open.mp3') || url.endsWith('success.mp3') || url.endsWith('notification.mp3') || url.endsWith('beep.mp3')) return;

    let contentType = '';
    let contentLength = 0;

    if (details.responseHeaders) {
      for (const header of details.responseHeaders) {
        const name = header.name.toLowerCase();
        if (name === 'content-type') {
          contentType = header.value ? header.value.toLowerCase() : '';
        } else if (name === 'content-length') {
          contentLength = parseInt(header.value, 10) || 0;
        }
      }
    }

    // Ignore tiny audio files < 100KB (typically button clicks / UI sounds)
    if (contentLength > 0 && contentLength < 100000 && (contentType.includes('audio') || url.endsWith('.mp3'))) {
      return;
    }

    // Determine media classification
    let mediaType = null;
    let isManifest = false;

    // Check MIME type
    if (
      contentType.includes('video/') ||
      contentType.includes('application/x-mpegurl') ||
      contentType.includes('application/vnd.apple.mpegurl') ||
      contentType.includes('application/dash+xml')
    ) {
      mediaType = 'video';
      isManifest = contentType.includes('mpegurl') || contentType.includes('dash+xml') || url.includes('.m3u8') || url.includes('.mpd');
    } else if (
      contentType.includes('audio/') ||
      contentType.includes('audio/mpeg') ||
      contentType.includes('audio/mp3')
    ) {
      mediaType = 'audio';
    } else if (MEDIA_EXT_REGEX.test(url)) {
      const match = url.match(MEDIA_EXT_REGEX);
      const ext = match ? match[1].toLowerCase() : '';
      if (['mp3', 'm4a', 'flac', 'wav', 'ogg', 'opus', 'aac'].includes(ext)) {
        mediaType = 'audio';
      } else {
        mediaType = 'video';
      }
      isManifest = ['m3u8', 'mpd'].includes(ext);
    }

    if (!mediaType) return;

    // Filter out tiny segment chunks if we already have manifests to avoid spamming
    if ((url.includes('.m4s') || url.includes('.ts')) && contentLength > 0 && contentLength < 300000) {
      // Chunk segment, ignore individual chunks
      return;
    }

    const state = getOrCreateTabState(details.tabId);

    // If on a home/feed page or major streaming platform, ignore background network chunks
    if (isHomePageOrFeed(state.pageUrl) || state.isStreamDomain || (state.pageUrl && state.pageUrl.includes('youtube.com')) || (url && url.includes('googlevideo.com'))) {
      return;
    }

    // Check for duplicates
    const exists = state.items.some(item => item.url === url);
    if (!exists) {
      // Clean filename from URL for display title
      let itemTitle = 'Network Media Stream';
      try {
        const parsed = new URL(url);
        const pathParts = parsed.pathname.split('/').filter(Boolean);
        if (pathParts.length > 0) {
          itemTitle = decodeURIComponent(pathParts[pathParts.length - 1]);
        }
      } catch {
        // Fallback
      }

      state.items.push({
        type: mediaType,
        url: url,
        mimeType: contentType || `media/${mediaType}`,
        isBlob: false,
        isManifest: isManifest,
        sizeBytes: contentLength,
        title: itemTitle,
        source: 'network'
      });

      state.lastUpdated = Date.now();
      updateTabBadge(details.tabId);
    }
  },
  { urls: ['<all_urls>'] },
  ['responseHeaders']
);

/**
 * Handle Tab lifecycle events
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const urlChanged = Boolean(changeInfo.url);
  const statusLoading = changeInfo.status === 'loading';

  if (urlChanged || statusLoading) {
    const targetUrl = changeInfo.url || (tab && tab.url) || '';
    const isHome = isHomePageOrFeed(targetUrl);
    // Reset tab media store when navigating to a new URL or refreshing the page
    tabMediaStore.set(tabId, {
      tabId,
      pageUrl: targetUrl,
      pageTitle: isHome ? 'No media detected' : ((tab && tab.title) || ''),
      playlistTitle: null,
      isStreamDomain: isHome ? false : isStreamingUrl(targetUrl),
      isPlaylist: isHome ? false : isPlaylistUrl(targetUrl),
      hasMediaTags: false,
      items: [],
      lastUpdated: Date.now()
    });
    updateTabBadge(tabId);
  } else if (changeInfo.title && tabMediaStore.has(tabId)) {
    const state = tabMediaStore.get(tabId);
    if (!isHomePageOrFeed(state.pageUrl)) {
      state.pageTitle = changeInfo.title;
    }
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabMediaStore.delete(tabId);
});

chrome.tabs.onActivated.addListener((activeInfo) => {
  updateTabBadge(activeInfo.tabId);
});

/**
 * Handle messages from Content Script and Popup UI
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return false;

  switch (message.type) {
    case 'MEDIA_DETECTED_DOM': {
      // Message sent from content.js (Pass 1)
      const tabId = sender.tab ? sender.tab.id : null;
      if (tabId !== null && tabId !== undefined) {
        const state = getOrCreateTabState(tabId);
        const payload = message.payload || {};
        const isTop = (sender.frameId === 0) || (payload.isTopFrame === true);

        if (isTop) {
          state.pageUrl = payload.pageUrl || sender.tab.url || state.pageUrl;
          const isHome = isHomePageOrFeed(state.pageUrl);

          if (isHome) {
            state.items = [];
            state.hasMediaTags = false;
            state.isStreamDomain = false;
            state.isPlaylist = false;
            state.pageTitle = 'No media detected';
            state.playlistTitle = null;
            state.lastUpdated = Date.now();
            updateTabBadge(tabId);
            sendResponse({ status: 'ok' });
            return true;
          }

          state.pageTitle = payload.pageTitle || sender.tab.title || state.pageTitle;
          state.playlistTitle = payload.playlistTitle || state.playlistTitle || null;
          state.isStreamDomain = payload.isStreamDomain !== undefined ? payload.isStreamDomain : isStreamingUrl(state.pageUrl);
          state.isPlaylist = payload.isPlaylist !== undefined ? payload.isPlaylist : isPlaylistUrl(state.pageUrl);
          state.hasMediaTags = payload.hasMediaTags;

          // Fresh top-level scan: replace DOM items to prevent stale blob accumulation from refresh
          if (Array.isArray(payload.items)) {
            const networkItems = state.items.filter(i => i.source === 'network');
            const newDomItems = payload.items.map(item => ({ ...item, source: 'dom' }));

            const merged = [...newDomItems];
            networkItems.forEach(netItem => {
              if (!merged.some(m => m.url === netItem.url)) {
                merged.push(netItem);
              }
            });
            state.items = merged;
          }
        } else {
          // Sub-frame scan: append items uniquely
          if (Array.isArray(payload.items)) {
            payload.items.forEach(newItem => {
              if (!state.items.some(i => i.url === newItem.url)) {
                state.items.push({ ...newItem, source: 'dom' });
              }
            });
          }
        }

        state.lastUpdated = Date.now();
        updateTabBadge(tabId);
      }
      sendResponse({ status: 'ok' });
      return true;
    }

    case 'GET_POPUP_STATE': {
      // Popup requests active tab media, download progress, and config
      handleGetPopupState(message.tabId).then(sendResponse);
      return true;
    }

    case 'START_DOWNLOAD': {
      // Start download through Native Messaging
      handleStartDownload(message.payload)
        .then(res => sendResponse(res))
        .catch(err => sendResponse({ status: 'error', message: err.message }));
      return true;
    }

    case 'CANCEL_DOWNLOAD': {
      handleCancelDownload().then(sendResponse);
      return true;
    }

    case 'DISMISS_JOB': {
      if (currentJob && (currentJob.status === 'complete' || currentJob.status === 'error')) {
        currentJob.status = 'idle';
        currentJob.percent = 0;
        currentJob.speed = '';
        currentJob.eta = '';
      }
      sendResponse({ status: 'ok' });
      return true;
    }

    case 'CLEAR_LOGS': {
      currentJob.logs = [];
      sendResponse({ status: 'ok' });
      return true;
    }

    case 'TEST_HOST_CONNECTION': {
      testNativeHost().then(sendResponse);
      return true;
    }

    case 'BOOTSTRAP_BINARIES': {
      handleBootstrapBinaries(message.force).then(sendResponse);
      return true;
    }

    case 'CHECK_UPDATES': {
      handleCheckUpdates().then(sendResponse);
      return true;
    }

    default:
      return false;
  }
});

/**
 * Assemble popup state payload
 */
async function handleGetPopupState(requestedTabId) {
  let activeTab = null;
  if (requestedTabId) {
    try {
      activeTab = await chrome.tabs.get(requestedTabId);
    } catch {}
  }

  if (!activeTab) {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      activeTab = tabs[0];
    }
  }

  let tabState = null;
  if (activeTab && activeTab.id) {
    tabState = getOrCreateTabState(activeTab.id);
    if (!tabState.pageUrl) tabState.pageUrl = activeTab.url || '';
    if (!tabState.pageTitle) tabState.pageTitle = activeTab.title || '';
    tabState.isStreamDomain = isStreamingUrl(tabState.pageUrl);
  }

  // If a finished download job is from another tab or page, reset it to idle immediately
  if (currentJob && (currentJob.status === 'complete' || currentJob.status === 'error')) {
    const currentUrl = activeTab ? activeTab.url : '';
    const jobUrl = currentJob.pageUrl || currentJob.url || '';
    const isDifferentPage = currentUrl && jobUrl && currentUrl !== jobUrl;
    const isDifferentTab = activeTab && currentJob.tabId && activeTab.id !== currentJob.tabId;
    if (isDifferentPage || isDifferentTab) {
      currentJob.status = 'idle';
      currentJob.percent = 0;
      currentJob.speed = '';
      currentJob.eta = '';
    }
  }

  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);

  return {
    tabState: tabState || {
      pageUrl: '',
      pageTitle: '',
      isStreamDomain: false,
      hasMediaTags: false,
      items: []
    },
    currentJob,
    settings
  };
}

/**
 * Native Messaging: Test connectivity with Python Host
 */
function testNativeHost() {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST_NAME,
        { action: 'PING' },
        (response) => {
          if (chrome.runtime.lastError) {
            resolve({
              connected: false,
              error: chrome.runtime.lastError.message
            });
          } else {
            resolve({
              connected: true,
              data: response
            });
          }
        }
      );
    } catch (err) {
      resolve({
        connected: false,
        error: err.message || 'Failed to initiate native communication'
      });
    }
  });
}

/**
 * Export browser session cookies for target domain in Netscape format
 */
async function getNetscapeCookiesForUrl(targetUrl) {
  try {
    if (!chrome.cookies || !targetUrl) return null;
    const urlObj = new URL(targetUrl);
    let cookies = await chrome.cookies.getAll({ url: targetUrl });
    if (!cookies || cookies.length === 0) {
      cookies = await chrome.cookies.getAll({ domain: urlObj.hostname });
    }
    if (!cookies || cookies.length === 0) {
      const parts = urlObj.hostname.split('.');
      if (parts.length >= 2) {
        const rootDomain = parts.slice(-2).join('.');
        cookies = await chrome.cookies.getAll({ domain: rootDomain });
      }
    }
    if (!cookies || cookies.length === 0) return null;

    let text = "# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file!  Do not edit.\n\n";
    for (const c of cookies) {
      const domain = c.domain.startsWith('.') ? c.domain : ('.' + c.domain);
      const flag = domain.startsWith('.') ? 'TRUE' : 'FALSE';
      const path = c.path || '/';
      const secure = c.secure ? 'TRUE' : 'FALSE';
      const expiry = Math.round(c.expirationDate || (Date.now() / 1000 + 86400 * 365));
      text += `${domain}\t${flag}\t${path}\t${secure}\t${expiry}\t${c.name}\t${c.value}\n`;
    }
    return text;
  } catch (err) {
    console.warn('[FTODE] Cookie extraction warning:', err);
    return null;
  }
}

/**
 * Start downloading via Native Host
 */
async function handleStartDownload(msg) {
  try {
    const settings = await getSettings();
    const rawMediaType = msg.mediaType || msg.targetType || msg.type;
    const audioFormats = ['mp3', 'm4a', 'wav', 'flac', 'ogg', 'aac', 'opus'];
    const targetFormat = msg.format || (rawMediaType === 'audio' ? settings.audioFormat : settings.videoFormat);
    const isAudio = rawMediaType === 'audio' || (targetFormat && audioFormats.includes(targetFormat.toLowerCase()));
    const finalMediaType = isAudio ? 'audio' : 'video';
    const tabId = msg.tabId || null;
    const pageUrl = msg.pageUrl || (tabId && tabMediaStore.has(tabId) ? tabMediaStore.get(tabId).pageUrl : null) || msg.url;

    // Safety guard: Refuse to start batch download on entire home feeds or search result pages
    if (isHomePageOrFeed(msg.url) || isHomePageOrFeed(pageUrl)) {
      return {
        status: 'error',
        message: 'No video stream on homepage/feed. Please open a specific video or playlist page.'
      };
    }

    let isPlaylist = msg.isPlaylist;
    if (isPlaylist === undefined && tabId && tabMediaStore.has(tabId)) {
      isPlaylist = tabMediaStore.get(tabId).isPlaylist;
    }
    if (!isPlaylist && (isPlaylistUrl(pageUrl) || isPlaylistUrl(msg.url))) {
      isPlaylist = true;
    }

    currentJob = {
      id: 'job_' + Date.now(),
      tabId: tabId,
      url: msg.url,
      pageUrl: pageUrl,
      title: msg.title || (tabId && tabMediaStore.has(tabId) ? tabMediaStore.get(tabId).pageTitle : 'Media Download'),
      mediaType: finalMediaType,
      format: targetFormat,
      downloadFolder: settings.downloadFolder || 'FTODE',
      isPlaylist: Boolean(isPlaylist),
      status: 'downloading',
      percent: 0,
      speed: '--',
      eta: '--',
      totalBytes: '--',
      error: null,
      logs: [
        `[INFO] Starting ${isPlaylist ? 'playlist batch' : finalMediaType} download: "${msg.title || 'Media Download'}"`,
        `[INFO] Target format: ${targetFormat.toUpperCase()}`
      ],
      downloadId: null,
      startTime: Date.now()
    };

    broadcastToPopup({
      type: 'JOB_UPDATED',
      job: currentJob
    });

    // Connect native port
    if (nativePort) {
      try { nativePort.disconnect(); } catch {}
      nativePort = null;
    }

    nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);

    nativePort.onMessage.addListener((msg) => {
      handleNativeHostMessage(msg);
    });

    nativePort.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError ? chrome.runtime.lastError.message : 'Native host disconnected';
      console.warn('[FTODE] Native port disconnected:', err);

      if (currentJob.status === 'downloading' || currentJob.status === 'remuxing') {
        currentJob.status = 'error';
        currentJob.error = err || 'Native host closed unexpectedly';
        currentJob.logs.push(`[ERROR] Connection lost: ${currentJob.error}`);
        currentJob.logs.push(`[TIP] Run install_host.bat once in native_host/ to register.`);
        broadcastToPopup({ type: 'JOB_UPDATED', job: currentJob });
      }
      nativePort = null;
    });

    const cookiesText = await getNetscapeCookiesForUrl(pageUrl || currentJob.url);

    const requestPayload = {
      action: 'DOWNLOAD',
      jobId: currentJob.id,
      url: currentJob.url,
      pageUrl: pageUrl || currentJob.url,
      title: currentJob.title,
      type: finalMediaType,
      mediaType: finalMediaType,
      format: currentJob.format,
      isPlaylist: isPlaylist,
      downloadFolder: settings.downloadFolder || 'FTODE',
      videoQuality: settings.videoQuality || 'best',
      audioQuality: settings.audioQuality || 'best',
      existingFileAction: settings.existingFileAction || 'copy',
      cookiesText: cookiesText
    };

    nativePort.postMessage(requestPayload);
    return { status: 'started', jobId: currentJob.id };
  } catch (err) {
    if (currentJob) {
      currentJob.status = 'error';
      currentJob.error = err.message || 'Failed to connect to native host';
      currentJob.logs.push(`[ERROR] Native connection failed: ${currentJob.error}`);
      currentJob.logs.push(`[TIP] Run install_host.bat once in native_host/ to register.`);
      broadcastToPopup({ type: 'JOB_UPDATED', job: currentJob });
    }

    return {
      status: 'error',
      message: err.message || 'Failed to initiate download'
    };
  }
}

/**
 * Parse incoming messages from Python Native Host
 */
function handleNativeHostMessage(msg) {
  if (!msg) return;

  if (msg.status === 'progress') {
    if (msg.percent !== undefined && !isNaN(msg.percent)) {
      currentJob.percent = Math.min(100, Math.max(0, parseFloat(msg.percent)));
    }
    if (msg.speed) currentJob.speed = msg.speed;
    if (msg.eta) currentJob.eta = msg.eta;
    if (msg.stage) currentJob.status = msg.stage === 'remuxing' ? 'remuxing' : 'downloading';
    if (msg.line) {
      currentJob.line = msg.line;
      appendJobLog(msg.line);
    }
  } else if (msg.status === 'log') {
    if (msg.line) appendJobLog(msg.line);
  } else if (msg.status === 'complete') {
    currentJob.status = 'complete';
    currentJob.percent = 100;
    currentJob.speed = 'Done';
    currentJob.eta = '00:00';
    currentJob.resultFile = msg.file || null;
    currentJob.line = 'Download completed successfully!';
    const folderPath = currentJob.downloadFolder ? `Downloads/${currentJob.downloadFolder}` : 'Downloads/FTODE';
    appendJobLog(`[SUCCESS] Download completed! Saved to: ${msg.file || folderPath}`);
    if (nativePort) {
      try { nativePort.disconnect(); } catch {}
      nativePort = null;
    }
    setTimeout(() => {
      if (currentJob && currentJob.status === 'complete') {
        currentJob.status = 'idle';
        currentJob.percent = 0;
        currentJob.speed = '';
        currentJob.eta = '';
        broadcastToPopup({ type: 'JOB_UPDATED', job: currentJob });
      }
    }, 5000);
  } else if (msg.status === 'error') {
    currentJob.status = 'error';
    currentJob.speed = 'Failed';
    currentJob.eta = '--';
    currentJob.error = msg.message || 'An error occurred during download.';
    appendJobLog(`[ERROR] ${currentJob.error}`);
    if (nativePort) {
      try { nativePort.disconnect(); } catch {}
      nativePort = null;
    }
    setTimeout(() => {
      if (currentJob && currentJob.status === 'error') {
        currentJob.status = 'idle';
        currentJob.percent = 0;
        currentJob.speed = '';
        currentJob.eta = '';
        broadcastToPopup({ type: 'JOB_UPDATED', job: currentJob });
      }
    }, 5000);
  }

  broadcastToPopup({
    type: 'JOB_UPDATED',
    job: currentJob
  });
}

function appendJobLog(line) {
  if (!line) return;
  currentJob.logs.push(line);
  // Keep buffer bounded
  if (currentJob.logs.length > 250) {
    currentJob.logs.shift();
  }
}

/**
 * Cancel active download
 */
async function handleCancelDownload() {
  if (nativePort) {
    try {
      nativePort.postMessage({ action: 'CANCEL', jobId: currentJob.id });
    } catch {}
    setTimeout(() => {
      try {
        if (nativePort) {
          nativePort.disconnect();
        }
      } catch {}
      nativePort = null;
    }, 150);
  }

  currentJob.status = 'error';
  currentJob.error = 'Download cancelled by user';
  currentJob.logs.push('[INFO] Download cancelled by user.');
  broadcastToPopup({ type: 'JOB_UPDATED', job: currentJob });

  return { status: 'cancelled' };
}

/**
 * Handle on-demand binary installation
 */
function handleBootstrapBinaries(force = false) {
  return new Promise((resolve) => {
    let tempPort = null;
    try {
      tempPort = chrome.runtime.connectNative(NATIVE_HOST_NAME);

      tempPort.onMessage.addListener((msg) => {
        if (!msg) return;

        if (msg.status === 'bootstrap_progress') {
          broadcastToPopup({
            type: 'BOOTSTRAP_PROGRESS',
            percent: msg.percent,
            line: msg.line
          });
        } else if (msg.status === 'bootstrap_complete') {
          broadcastToPopup({
            type: 'BOOTSTRAP_COMPLETE',
            data: msg
          });
          try { tempPort.disconnect(); } catch {}
          resolve({ success: true, data: msg });
        } else if (msg.status === 'error') {
          broadcastToPopup({
            type: 'BOOTSTRAP_ERROR',
            error: msg.message
          });
          try { tempPort.disconnect(); } catch {}
          resolve({ success: false, error: msg.message });
        }
      });

      tempPort.onDisconnect.addListener(() => {
        const err = chrome.runtime.lastError ? chrome.runtime.lastError.message : 'Disconnected';
        resolve({ success: false, error: err });
      });

      tempPort.postMessage({
        action: 'BOOTSTRAP_BINARIES',
        force: !!force
      });
    } catch (err) {
      resolve({ success: false, error: err.message });
    }
  });
}

/**
 * Handle fast update check for yt-dlp & FFmpeg
 */
function handleCheckUpdates() {
  return new Promise((resolve) => {
    let tempPort = null;
    try {
      tempPort = chrome.runtime.connectNative(NATIVE_HOST_NAME);

      tempPort.onMessage.addListener((msg) => {
        if (!msg) return;

        if (msg.status === 'bootstrap_progress') {
          broadcastToPopup({
            type: 'BOOTSTRAP_PROGRESS',
            percent: msg.percent,
            line: msg.line
          });
        } else if (msg.status === 'update_complete' || msg.status === 'bootstrap_complete') {
          broadcastToPopup({
            type: 'UPDATE_COMPLETE',
            data: msg
          });
          try { tempPort.disconnect(); } catch {}
          resolve({ success: true, data: msg });
        } else if (msg.status === 'error') {
          broadcastToPopup({
            type: 'BOOTSTRAP_ERROR',
            error: msg.message
          });
          try { tempPort.disconnect(); } catch {}
          resolve({ success: false, error: msg.message });
        }
      });

      tempPort.onDisconnect.addListener(() => {
        const err = chrome.runtime.lastError ? chrome.runtime.lastError.message : 'Disconnected';
        resolve({ success: false, error: err });
      });

      tempPort.postMessage({
        action: 'CHECK_UPDATES'
      });
    } catch (err) {
      resolve({ success: false, error: err.message });
    }
  });
}

/**
 * Broadcast event to popup/options listeners
 */
function broadcastToPopup(message) {
  try {
    chrome.runtime.sendMessage(message).catch(() => {
      // Ignored if popup is not open
    });
  } catch {}
}
