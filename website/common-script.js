// Theme toggle functionality
const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme') || 'light';

// Set initial theme
document.body.setAttribute('data-theme', currentTheme);

themeToggle.addEventListener('click', () => {
  const currentTheme = document.body.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

  document.body.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
});