/**
 * API Client & Global Helpers for Subscription Management System
 */

const API_BASE = '/api';

// Current active user stored in localStorage (defaults to admin-01)
let currentUser = {
  id: localStorage.getItem('sms_user_id') || 'admin-01',
  role: localStorage.getItem('sms_user_role') || 'admin',
  name: localStorage.getItem('sms_user_name') || 'Sarah Jenkins'
};

// Global Fetch helper adding user auth headers
async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': currentUser.id,
    'X-User-Role': currentUser.role,
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.message || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}

// User & Session API
async function initCurrentUser() {
  try {
    const res = await apiFetch(`/me?userId=${currentUser.id}`);
    if (res.user) {
      currentUser = res.user;
      localStorage.setItem('sms_user_id', currentUser.id);
      localStorage.setItem('sms_user_role', currentUser.role);
      localStorage.setItem('sms_user_name', currentUser.name);
    }
  } catch (err) {
    console.error('Failed to init user session:', err);
  }
  return currentUser;
}

async function fetchUsers() {
  const res = await apiFetch('/users');
  return res.users || [];
}

function switchUser(userId, userName, userRole) {
  currentUser.id = userId;
  currentUser.name = userName;
  currentUser.role = userRole;
  localStorage.setItem('sms_user_id', userId);
  localStorage.setItem('sms_user_role', userRole);
  localStorage.setItem('sms_user_name', userName);
  window.location.reload();
}

// Subscriptions API
async function fetchSubscriptions(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== 'all') params.append('status', filters.status);
  if (filters.planId && filters.planId !== 'all') params.append('planId', filters.planId);
  if (filters.customerId && filters.customerId !== 'all') params.append('customerId', filters.customerId);
  if (filters.paymentTerms && filters.paymentTerms !== 'all') params.append('paymentTerms', filters.paymentTerms);
  if (filters.expiryState && filters.expiryState !== 'all') params.append('expiryState', filters.expiryState);
  if (filters.search && filters.search.trim()) params.append('search', filters.search.trim());

  const query = params.toString() ? `?${params.toString()}` : '';
  return await apiFetch(`/subscriptions${query}`);
}

async function fetchSubscriptionById(id) {
  const res = await apiFetch(`/subscriptions/${encodeURIComponent(id)}`);
  return res.subscription;
}

async function createSubscription(payload) {
  return await apiFetch('/subscriptions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

async function updateSubscription(id, payload) {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  });
}

async function transitionStatus(id, toStatus, reason = '', notes = '') {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}/transition`, {
    method: 'POST',
    body: JSON.stringify({ toStatus, reason, notes })
  });
}

async function pauseSubscription(id, reason) {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}/pause`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

async function resumeSubscription(id) {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}/resume`, {
    method: 'POST'
  });
}

async function renewSubscription(id, durationDays = 30, notes = '') {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}/renew`, {
    method: 'POST',
    body: JSON.stringify({ durationDays, notes })
  });
}

async function cancelSubscription(id, reason) {
  return await apiFetch(`/subscriptions/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

async function autoCloseExpiredSubscriptions() {
  return await apiFetch('/subscriptions/auto-close-expired', {
    method: 'POST'
  });
}

// Metadata APIs
async function fetchMetrics() {
  const res = await apiFetch('/metrics');
  return res.metrics;
}

async function fetchCustomers() {
  const res = await apiFetch('/customers');
  return res.customers || [];
}

async function fetchPlans() {
  const res = await apiFetch('/plans');
  return res.plans || [];
}

async function fetchProducts() {
  const res = await apiFetch('/products');
  return res.products || [];
}

async function fetchSettings() {
  const res = await apiFetch('/settings');
  return res.settings;
}

async function updateSettings(settings) {
  const res = await apiFetch('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings)
  });
  return res.settings;
}

// UI Helpers
function formatCurrency(amount, currency = 'USD') {
  const num = Number(amount) || 0;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(num);
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }
  return dateStr;
}

function getStatusBadge(status) {
  const s = (status || 'draft').toLowerCase();
  return `<span class="badge badge-${s}"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;"></span>${status}</span>`;
}

function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Render dynamic header with active user switcher
async function setupHeaderNavigation(activePage = 'subscriptions') {
  const headerContainer = document.getElementById('appHeader');
  if (!headerContainer) return;

  const users = await fetchUsers();
  const isCustomer = currentUser.role === 'customer';

  headerContainer.innerHTML = `
    <div class="header-nav">
      <a href="/" class="brand">
        <div class="brand-icon">S</div>
        <div>Subscription Hub</div>
      </a>

      <div class="nav-links">
        <a href="/" class="nav-item ${activePage === 'subscriptions' ? 'active' : ''}">Subscriptions</a>
        ${!isCustomer ? `<a href="/subscription-form.html" class="nav-item ${activePage === 'create' ? 'active' : ''}">+ New Subscription</a>` : ''}
      </div>

      <div class="user-switcher-container">
        <span class="role-badge ${currentUser.role}">${currentUser.role}</span>
        <select id="userSelector" class="user-select" title="Switch User Role to test permissions">
          ${users.map(u => `
            <option value="${u.id}" data-role="${u.role}" data-name="${u.name}" ${u.id === currentUser.id ? 'selected' : ''}>
              ${u.name} (${u.role.toUpperCase()})
            </option>
          `).join('')}
        </select>
      </div>
    </div>
  `;

  const selector = document.getElementById('userSelector');
  if (selector) {
    selector.addEventListener('change', (e) => {
      const selected = selector.options[selector.selectedIndex];
      const uid = selected.value;
      const uname = selected.getAttribute('data-name');
      const urole = selected.getAttribute('data-role');
      switchUser(uid, uname, urole);
    });
  }
}
