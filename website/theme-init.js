// Early theme initialization to prevent flicker
(function() {
  // Set theme as early as possible
  const savedTheme = localStorage.getItem('theme') || 'dark';

  // Apply theme to html element immediately (before body exists)
  document.documentElement.setAttribute('data-theme', savedTheme);
})();