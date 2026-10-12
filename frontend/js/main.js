/**
 * SMART INDIAN RAILWAY SYSTEM - CORE UTILITIES & APPLICATION RUNTIME
 */

// Determine API Base URL dynamically (works both when served by Flask on any cloud/local port, or via local static dev servers)
const isLocalStaticDevServer = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  && window.location.port
  && window.location.port !== '5000'
  && window.location.port !== '';

const API_BASE_URL = (!window.location.protocol.startsWith('file:') && !isLocalStaticDevServer)
  ? '/api'
  : 'http://127.0.0.1:5000/api';

// Unique persistent session ID for seat locking
function getSessionId() {
  let sid = localStorage.getItem('railway_session_id');
  if (!sid) {
    sid = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    localStorage.setItem('railway_session_id', sid);
  }
  return sid;
}

// User Session Management
function getCurrentUser() {
  const userStr = localStorage.getItem('railway_user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (e) {
      localStorage.removeItem('railway_user');
    }
  }
  return null;
}

function setCurrentUser(user) {
  if (user) {
    localStorage.setItem('railway_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('railway_user');
  }
  renderAuthNav();
}

async function logoutUser() {
  try {
    await fetchApi('/auth/logout', { method: 'POST' });
  } catch (e) {
    console.error('Logout error:', e);
  }
  setCurrentUser(null);
  showToast('Logged out successfully.', 'info', 'Logout');
  setTimeout(() => {
    window.location.href = 'index.html';
  }, 600);
}

// Global API Fetch Helper with 10s finite timeout
async function fetchApi(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json'
  };

  const controller = new AbortController();
  const timeoutMs = options.timeout || 10000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const config = {
    ...options,
    signal: options.signal || controller.signal,
    headers: {
      ...defaultHeaders,
      ...options.headers
    },
    credentials: 'include' // allow Flask sessions
  };

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);
    let data;
    try {
      data = await response.json();
    } catch (parseErr) {
      data = { success: false, message: 'Invalid server response format.' };
    }
    return { ok: response.ok, status: response.status, ...data };
  } catch (err) {
    clearTimeout(timeoutId);
    const isTimeout = err.name === 'AbortError';
    console.error(`API Fetch Error [${endpoint}]:`, err);
    return {
      ok: false,
      status: 0,
      success: false,
      message: isTimeout 
        ? 'Search request timed out after 10 seconds. Please try again.'
        : 'Network error or backend server unreachable. Make sure python run.py is running.'
    };
  }
}

// Indian Rupee Currency Formatter
function formatINR(amount) {
  const num = parseFloat(amount || 0);
  return '₹' + num.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// URL Query Param Helper
function getQueryParam(param) {
  const params = new URLSearchParams(window.location.search);
  return params.get(param);
}

// Toast Notification Manager
function showToast(message, type = 'info', title = '') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = {
    success: 'fa-circle-check',
    error: 'fa-triangle-exclamation',
    warning: 'fa-circle-exclamation',
    info: 'fa-circle-info'
  };

  const defaultTitles = {
    success: 'Success',
    error: 'Error',
    warning: 'Notice',
    info: 'Information'
  };

  toast.innerHTML = `
    <div class="toast-icon">
      <i class="fa-solid ${iconMap[type] || 'fa-bell'}"></i>
    </div>
    <div class="toast-content">
      <div class="toast-title">${title || defaultTitles[type] || 'Alert'}</div>
      <div class="toast-msg">${message}</div>
    </div>
  `;

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto remove
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 300);
  }, 4200);
}

// Update Top Navigation depending on Auth state
function renderAuthNav() {
  const authContainer = document.getElementById('nav-auth-container');
  if (!authContainer) return;

  const user = getCurrentUser();
  if (user) {
    const isAdmin = user.role === 'ADMIN';
    authContainer.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        ${isAdmin ? `<a href="admin-dashboard.html" class="btn btn-sm btn-outline"><i class="fa-solid fa-gauge-high"></i> Admin</a>` : ''}
        <span style="font-size: 0.85rem; font-weight: 600; color: var(--primary-navy);">
          <i class="fa-regular fa-circle-user" style="color: var(--accent-saffron); font-size: 1.1rem; margin-right: 4px;"></i> ${user.name.split(' ')[0]}
        </span>
        <button onclick="logoutUser()" class="btn btn-sm btn-outline" title="Sign out">
          <i class="fa-solid fa-arrow-right-from-bracket"></i>
        </button>
      </div>
    `;
  } else {
    authContainer.innerHTML = `
      <a href="login.html" class="btn btn-sm btn-outline"><i class="fa-solid fa-user"></i> Login</a>
      <a href="register.html" class="btn btn-sm btn-accent">Register</a>
    `;
  }
}

// Mobile Hamburger Toggle
function setupMobileNav() {
  const toggle = document.querySelector('.mobile-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      navLinks.classList.toggle('show');
    });
  }
}

// Highlight current page in navbar
function highlightActiveNav() {
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', () => {
  renderAuthNav();
  setupMobileNav();
  highlightActiveNav();
  getSessionId(); // initialize session id
});
