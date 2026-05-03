// Early theme initialization to prevent flicker
(function() {
  // Set theme as early as possible
  const savedTheme = localStorage.getItem('theme') || 'dark';

  // Apply theme to body attribute immediately
  document.body.setAttribute('data-theme', savedTheme);

  // Also set it in the head to prevent FOUC
  if (document.head) {
    const themeStyle = document.createElement('style');
    themeStyle.textContent = `
      body[data-theme="dark"] {
        --bg-color: #1a1a1a;
        --text-color: #f0f0f0;
        --accent-color: #4CAF50;
        --border-color: #333333;
        --shadow: rgba(0, 0, 0, 0.3);
      }

      body[data-theme="light"] {
        --bg-color: #ffffff;
        --text-color: #333333;
        --accent-color: #2E6F40;
        --border-color: #e0e0e0;
        --shadow: rgba(0, 0, 0, 0.1);
      }
    `;
    document.head.appendChild(themeStyle);
  }
})();