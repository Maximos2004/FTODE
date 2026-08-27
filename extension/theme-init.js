/**
 * Finally that online downloader extension (FTODE) - Theme Initializer
 * Runs synchronously in <head> to suppress startup transitions and apply theme immediately.
 * Complies with Manifest V3 CSP (no inline scripts).
 */
(function() {
  'use strict';
  try {
    document.documentElement.classList.add('preload');
    if (localStorage.getItem('ftode_theme') === 'light') {
      document.documentElement.classList.add('light-theme');
    } else if (localStorage.getItem('ftode_theme') === 'dark') {
      document.documentElement.classList.remove('light-theme');
    }
  } catch (e) {
    // Fallback if localStorage is inaccessible
    document.documentElement.classList.add('preload');
  }
})();
