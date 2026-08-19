/**
 * Finally that online downloader extension (FTODE) - Content Script (Pass 1: DOM Inspector)
 * Scans active web page for HTML5 media elements, player streams, and known streaming platforms.
 */

(function () {
  'use strict';

  // Prevent duplicate injection in the same frame
  if (window.__FTODE_INJECTED__) {
    return;
  }
  window.__FTODE_INJECTED__ = true;

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

  let lastReportedHash = '';
  let debounceTimeout = null;

  /**
   * Helper to check if current URL is a feed / homepage / search page with no primary video
   */
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
   * Helper to determine if current domain is a known stream site playing media
   */
  function isStreamingDomain(url) {
    if (isHomePageOrFeed(url)) return false;
    try {
      const hostname = new URL(url).hostname.toLowerCase();
      return STREAMING_DOMAINS.some(domain => hostname === domain || hostname.endsWith('.' + domain));
    } catch {
      return false;
    }
  }

  /**
   * Helper to determine if current URL is a playlist / album / set
   */
  function isPlaylistPage(url) {
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
      // SoundCloud Sets/Playlists/Albums
      if (host.includes('soundcloud.com') && (path.includes('/sets/') || path.includes('/albums/'))) {
        return true;
      }
      // Bandcamp Albums
      if (host.includes('bandcamp.com') && path.includes('/album/')) {
        return true;
      }
      // Generic playlist / album paths
      if (path.includes('/playlist/') || path.includes('/playlists/') || path.includes('/album/')) {
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * Validate if extracted text is a genuine playlist title
   */
  function isValidPlaylistTitle(str) {
    if (!str || typeof str !== 'string') return false;
    const clean = str.trim();
    if (!clean || clean.length < 3) return false;
    if (clean.includes('NaN') || clean.includes('undefined')) return false;
    if (/^\d+\s*\/\s*\d+$/.test(clean)) return false;
    if (clean.toLowerCase() === 'playlist' || clean.toLowerCase() === 'media stream') return false;
    return true;
  }

  /**
   * Extract dedicated playlist / album title from DOM
   */
  function getPlaylistTitle() {
    // 1. YouTube playlist panel header in watch view (watch?v=...&list=...)
    const ytWatchSelectors = [
      'ytd-playlist-panel-renderer #header-description h3 a',
      'ytd-playlist-panel-renderer .playlist-header-title',
      'ytd-playlist-panel-renderer #title a',
      'ytd-playlist-panel-renderer h3.title a',
      'ytd-watch-flexy ytd-playlist-panel-renderer h3',
      '#playlist #header-description a'
    ];
    for (const sel of ytWatchSelectors) {
      const el = document.querySelector(sel);
      if (el && isValidPlaylistTitle(el.innerText)) {
        return el.innerText.trim();
      }
    }

    // 2. YouTube dedicated playlist page header (playlist?list=...)
    const ytPageSelectors = [
      'ytd-playlist-header-renderer .yt-dynamic-sizing-formatted-string',
      'ytd-playlist-header-renderer h1 yt-formatted-string',
      'ytd-playlist-header-renderer h1',
      'yt-page-header-renderer h1',
      'ytd-browse[page-subtype="playlist"] h1'
    ];
    for (const sel of ytPageSelectors) {
      const el = document.querySelector(sel);
      if (el && isValidPlaylistTitle(el.innerText)) {
        return el.innerText.trim();
      }
    }

    // 3. Check YouTube player attributes
    const ytFlexy = document.querySelector('ytd-watch-flexy');
    if (ytFlexy && ytFlexy.getAttribute('playlist-title')) {
      const pt = ytFlexy.getAttribute('playlist-title').trim();
      if (isValidPlaylistTitle(pt)) return pt;
    }

    // 4. SoundCloud Sets / Playlists
    const scSetTitle = document.querySelector('.soundTitle__title, .fullHero__title');
    if (scSetTitle && isValidPlaylistTitle(scSetTitle.innerText)) {
      return scSetTitle.innerText.trim();
    }

    // 5. Bandcamp Album
    const bcAlbumTitle = document.querySelector('#name-section .trackTitle, .albumTitle');
    if (bcAlbumTitle && isValidPlaylistTitle(bcAlbumTitle.innerText)) {
      return bcAlbumTitle.innerText.trim();
    }

    return null;
  }

  /**
   * Remove SponsorBlock badges, extension tags, and platform suffixes from titles
   */
  function cleanTitleString(text) {
    if (!text || typeof text !== 'string') return '';
    let clean = text.trim();
    // Remove SponsorBlock injected categories
    clean = clean.replace(/^(?:\[?\s*(?:Unpaid\/Self Promotion|Self Promotion|Sponsor(?:ed)?|Interaction(?: Reminder)?|Intro|Outro|Preview|Filler|Highlight|Music: Non-Music Section|Exclusive Access|Patreon)\s*\]?)\s*[-:]?\s*/i, '');
    // Clean platform suffixes
    clean = clean.replace(/ - YouTube$/i, '').replace(/ \| SoundCloud$/i, '').replace(/ - Vimeo$/i, '').trim();
    return clean;
  }

  /**
   * Clone a title DOM element and strip third party extension badge nodes (SponsorBlock, etc.)
   */
  function extractCleanTitleFromNode(node) {
    if (!node) return '';
    try {
      const clone = node.cloneNode(true);
      const junk = clone.querySelectorAll(
        '[class*="sponsor"], [id*="sponsor"], [class*="sponsorBlock"], ' +
        '[class*="sponsorblock"], [id*="sponsorblock"], [data-sponsorblock], ' +
        'ytd-badge-supported-renderer, .badge, .yt-badge, [class*="badge-style"], ' +
        'button, svg, .yt-spec-button-shape-next'
      );
      junk.forEach(el => el.remove());
      const text = clone.innerText || clone.textContent || '';
      return cleanTitleString(text);
    } catch {
      return cleanTitleString(node.innerText || node.textContent || '');
    }
  }

  /**
   * Extract high quality page or media title
   */
  function getBestPageTitle() {
    // 1. YouTube specific title element (with SponsorBlock strip)
    const ytVideoTitle = document.querySelector(
      '#title h1 yt-formatted-string, ' +
      'ytd-watch-metadata #title h1, ' +
      'ytd-watch-metadata h1.ytd-watch-metadata, ' +
      '#above-the-fold #title h1, ' +
      'h1.title.style-scope.ytd-video-primary-info-renderer'
    );
    if (ytVideoTitle) {
      const clean = extractCleanTitleFromNode(ytVideoTitle);
      if (clean && clean.length > 2) return clean;
    }

    // 2. Document Title (clean up standard YouTube / site suffix)
    if (document.title && document.title.trim()) {
      const docTitle = cleanTitleString(document.title);
      if (docTitle && docTitle.toLowerCase() !== 'youtube') {
        return docTitle;
      }
    }

    // 3. Check main h1
    const h1 = document.querySelector('h1');
    if (h1) {
      const clean = extractCleanTitleFromNode(h1);
      if (clean && clean.length > 3) return clean;
    }

    // 4. Check OpenGraph title
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle && ogTitle.content && ogTitle.content.trim()) {
      return cleanTitleString(ogTitle.content);
    }

    // 5. Check Twitter title
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle && twitterTitle.content && twitterTitle.content.trim()) {
      return cleanTitleString(twitterTitle.content);
    }

    return 'Media Stream';
  }

  /**
   * Inspect all video & audio elements in current document context
   */
  function scanDomMedia() {
    const isTopFrame = window === window.top;
    const isHome = isHomePageOrFeed(window.location.href);

    if (isHome) {
      return {
        pageUrl: window.location.href,
        pageTitle: 'No media detected',
        playlistTitle: null,
        isStreamDomain: false,
        isPlaylist: false,
        hasMediaTags: false,
        items: [],
        isTopFrame
      };
    }

    const mediaItems = [];
    const seenUrls = new Set();
    const isStreamSite = isStreamingDomain(window.location.href);
    const isPlaylist = isTopFrame ? isPlaylistPage(window.location.href) : false;
    let playlistTitle = null;
    let pageTitle = isTopFrame ? getBestPageTitle() : 'Media Stream';

    if (isTopFrame && isPlaylist) {
      playlistTitle = getPlaylistTitle();
      if (playlistTitle) {
        pageTitle = playlistTitle;
      }
    }

    // 1. Scan <video> elements
    let videos = Array.from(document.querySelectorAll('video'));

    // Filter out thumbnail previews, hover players, and miniplayers
    if (window.location.hostname.includes('youtube.com')) {
      const mainVideo = document.querySelector('video.html5-main-video') || document.querySelector('#movie_player video') || document.querySelector('.html5-video-container video');
      if (mainVideo) {
        videos = [mainVideo];
      } else {
        videos = videos.filter(v => !v.closest('ytd-miniplayer, ytd-inline-preview-renderer, ytd-thumbnail-overlay-loading-preview-renderer, .ytd-thumbnail-overlay-hover-playback-renderer'));
      }
    } else {
      videos = videos.filter(v => {
        const isPreview = v.closest && v.closest('.preview, [data-preview], .hover-player, .thumbnail-preview, .mini-player');
        return !isPreview;
      });
    }

    videos.forEach((video, index) => {
      const srcList = [];

      if (video.currentSrc) srcList.push({ src: video.currentSrc, type: 'video/currentSrc' });
      if (video.src && video.src !== video.currentSrc) srcList.push({ src: video.src, type: 'video/src' });

      // Check <source> tags
      const sources = video.querySelectorAll('source');
      sources.forEach(source => {
        const src = source.getAttribute('src') || source.getAttribute('data-src');
        const type = source.getAttribute('type') || 'video/*';
        if (src) srcList.push({ src: resolveUrl(src), type });
      });

      // Check common data attributes for player configs
      const dataSrcAttrs = ['data-src', 'data-video-url', 'data-mp4', 'data-hls-url', 'data-m3u8'];
      dataSrcAttrs.forEach(attr => {
        const val = video.getAttribute(attr);
        if (val) srcList.push({ src: resolveUrl(val), type: 'video/data-attr' });
      });

      // If video has no src attribute yet, register the stream context
      if (srcList.length === 0 && isStreamSite) {
        srcList.push({ src: window.location.href, type: 'video/adaptive-stream' });
      }

      // Filter and register
      srcList.forEach(item => {
        if (!item.src || seenUrls.has(item.src)) return;
        seenUrls.add(item.src);

        const isBlob = item.src.startsWith('blob:');
        const isManifest = item.src.includes('.m3u8') || item.src.includes('.mpd');
        const itemLabel = videos.length === 1 ? pageTitle : `${pageTitle} (Video #${index + 1})`;

        mediaItems.push({
          type: 'video',
          url: item.src,
          mimeType: isBlob ? 'video/mp4 (Adaptive Stream)' : item.type,
          isBlob: isBlob,
          isManifest: isManifest,
          title: video.getAttribute('aria-label') || video.getAttribute('title') || itemLabel,
          poster: video.poster || '',
          duration: video.duration && !isNaN(video.duration) ? Math.round(video.duration) : null,
          width: video.videoWidth || null,
          height: video.videoHeight || null
        });
      });
    });

    // Fallback for stream pages if video element had no src attached yet
    if (isStreamSite && mediaItems.length === 0 && !isHome) {
      mediaItems.push({
        type: 'video',
        url: window.location.href,
        mimeType: 'video/mp4 (Adaptive Stream)',
        isBlob: false,
        isManifest: true,
        title: pageTitle,
        duration: null
      });
    }

    // 2. Scan <audio> elements
    let audios = Array.from(document.querySelectorAll('audio'));
    audios = audios.filter(a => {
      const isPreview = a.closest && a.closest('.preview, [data-preview], .hover-player, .mini-player');
      return !isPreview;
    });

    audios.forEach((audio, index) => {
      const srcList = [];

      if (audio.currentSrc) srcList.push({ src: audio.currentSrc, type: 'audio/currentSrc' });
      if (audio.src && audio.src !== audio.currentSrc) srcList.push({ src: audio.src, type: 'audio/src' });

      const sources = audio.querySelectorAll('source');
      sources.forEach(source => {
        const src = source.getAttribute('src') || source.getAttribute('data-src');
        const type = source.getAttribute('type') || 'audio/*';
        if (src) srcList.push({ src: resolveUrl(src), type });
      });

      srcList.forEach(item => {
        if (!item.src || seenUrls.has(item.src)) return;
        seenUrls.add(item.src);

        const itemLabel = audios.length === 1 ? pageTitle : `${pageTitle} (Audio #${index + 1})`;

        mediaItems.push({
          type: 'audio',
          url: item.src,
          mimeType: item.type,
          isBlob: item.src.startsWith('blob:'),
          isManifest: item.src.includes('.m3u8') || item.src.includes('.mpd'),
          title: audio.getAttribute('aria-label') || audio.getAttribute('title') || itemLabel,
          duration: audio.duration && !isNaN(audio.duration) ? Math.round(audio.duration) : null
        });
      });
    });

    return {
      isTopFrame: isTopFrame,
      pageUrl: window.location.href,
      pageTitle: pageTitle,
      playlistTitle: playlistTitle,
      isStreamDomain: isStreamSite,
      isPlaylist: isPlaylist,
      hasMediaTags: mediaItems.length > 0 || videos.length > 0 || audios.length > 0,
      items: mediaItems
    };
  }

  function resolveUrl(relative) {
    try {
      return new URL(relative, window.location.href).href;
    } catch {
      return relative;
    }
  }

  /**
   * Send scan result to background worker if changed
   */
  function broadcastScanResults() {
    const payload = scanDomMedia();
    const hash = JSON.stringify({
      url: payload.pageUrl,
      title: payload.pageTitle,
      itemsCount: payload.items.length,
      isStream: payload.isStreamDomain,
      isPlaylist: payload.isPlaylist,
      firstUrl: payload.items[0]?.url || ''
    });

    if (hash === lastReportedHash) {
      return;
    }
    lastReportedHash = hash;

    try {
      chrome.runtime.sendMessage({
        type: 'MEDIA_DETECTED_DOM',
        payload: payload
      }).catch(() => {
        // Background might be inactive or reloading
      });
    } catch {
      // Ignored
    }
  }

  function scheduleDebouncedScan() {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(broadcastScanResults, 300);
  }

  // 1. Initial scan on script load
  scheduleDebouncedScan();

  // 2. Set up MutationObserver to watch for dynamically added video/audio elements
  const observer = new MutationObserver(mutations => {
    let shouldScan = false;
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'VIDEO' || node.tagName === 'AUDIO' || node.querySelector('video, audio, source')) {
              shouldScan = true;
              break;
            }
          }
        }
      } else if (mutation.type === 'attributes') {
        const target = mutation.target;
        if (target.tagName === 'VIDEO' || target.tagName === 'AUDIO' || target.tagName === 'SOURCE') {
          shouldScan = true;
          break;
        }
      }
      if (shouldScan) break;
    }

    if (shouldScan) {
      scheduleDebouncedScan();
    }
  });

  try {
    observer.observe(document.documentElement || document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['src', 'currentSrc', 'data-src', 'poster']
    });
  } catch (e) {
    console.warn("[FTODE] Observer init warning:", e);
  }

  // 3. Attach media playback and navigation event listeners
  function attachMediaListeners() {
    const mediaElements = document.querySelectorAll('video, audio');
    mediaElements.forEach(elem => {
      if (!elem.__ftode_listener_attached__) {
        elem.__ftode_listener_attached__ = true;
        elem.addEventListener('play', scheduleDebouncedScan, { passive: true });
        elem.addEventListener('playing', scheduleDebouncedScan, { passive: true });
        elem.addEventListener('loadeddata', scheduleDebouncedScan, { passive: true });
      }
    });
  }

  // SPA navigation hooks (YouTube, SoundCloud, Twitter/X, TikTok)
  function handleSpaNavigation() {
    lastReportedHash = null;
    scheduleDebouncedScan();
    setTimeout(scheduleDebouncedScan, 300);
    setTimeout(scheduleDebouncedScan, 800);
  }

  window.addEventListener('yt-navigate-start', handleSpaNavigation, { passive: true });
  window.addEventListener('yt-navigate-finish', handleSpaNavigation, { passive: true });
  window.addEventListener('yt-page-data-updated', handleSpaNavigation, { passive: true });
  window.addEventListener('popstate', handleSpaNavigation, { passive: true });
  window.addEventListener('hashchange', handleSpaNavigation, { passive: true });

  window.addEventListener('load', () => {
    scheduleDebouncedScan();
    attachMediaListeners();
  });

  // 4. Listen for explicit scan messages from background/popup
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message && message.type === 'SCAN_MEDIA_DOM') {
      const data = scanDomMedia();
      sendResponse(data);
    }
    return false;
  });

})();
