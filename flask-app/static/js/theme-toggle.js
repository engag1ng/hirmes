const toggleButton = document.getElementById('theme-toggle');
const root = document.documentElement;

function setTheme(theme) {
  root.setAttribute('data-theme', theme);
  toggleButton.setAttribute('aria-label', `Change to ${theme === 'dark' ? 'light' : 'dark'} theme`);
  toggleButton.textContent = theme === 'dark' ? '🌙' : '🌞';
  localStorage.setItem('theme', theme);
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
setTheme(savedTheme);

// Toggle on click
toggleButton.addEventListener('click', () => {
  const newTheme = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
  setTheme(newTheme);
});
