/**
 * App.js - Dashboard and Subscription List Controller
 */

let allSubscriptions = [];
let activeFilters = {
  status: 'all',
  planId: 'all',
  customerId: 'all',
  paymentTerms: 'all',
  expiryState: 'all',
  search: ''
};

let currentModalSubId = null;

// Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
  currentModalSubId = null;
}

document.addEventListener('DOMContentLoaded', async () => {
  await initCurrentUser();
  await setupHeaderNavigation('subscriptions');
  renderRoleBanner();
  await loadFilterOptions();
  await refreshDashboard();
  setupEventListeners();
});

// Display alert explaining current role's view
function renderRoleBanner() {
  const banner = document.getElementById('roleAlertBanner');
  if (!banner) return;

  const isCustomer = currentUser.role === 'customer';
  const newSubBtn = document.getElementById('btnNewSubscription');
  const autoCloseBtn = document.getElementById('btnAutoCloseTrigger');

  if (isCustomer) {
    if (newSubBtn) newSubBtn.style.display = 'none';
    if (autoCloseBtn) autoCloseBtn.style.display = 'none';
    banner.innerHTML = `
      <div class="alert-banner customer-notice">
        <div>
          <strong>👤 Customer Portal View:</strong> Welcome, <strong>${currentUser.name}</strong>. You are viewing your company's registered subscriptions, invoices, and service terms.
        </div>
        <div style="font-size:0.8rem;opacity:0.85;">Read-Only Customer View</div>
      </div>
    `;
  } else {
    if (newSubBtn) newSubBtn.style.display = 'inline-flex';
    if (autoCloseBtn) autoCloseBtn.style.display = 'inline-flex';
    banner.innerHTML = `
      <div class="alert-banner info">
        <div>
          <strong>🛡️ ${currentUser.role === 'admin' ? 'Administrator' : 'Staff'} Console:</strong> Logged in as <strong>${currentUser.name}</strong>. Full access to create, edit, pause, resume, renew, cancel, and auto-close subscriptions.
        </div>
        <span class="role-badge ${currentUser.role}">Full Access</span>
      </div>
    `;
  }
}

// Load dropdowns for filtering
async function loadFilterOptions() {
  try {
    const plans = await fetchPlans();
    const planSelect = document.getElementById('planFilter');
    if (planSelect) {
      plans.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.billingCycle})`;
        planSelect.appendChild(opt);
      });
    }

    const isCustomer = currentUser.role === 'customer';
    const custSelect = document.getElementById('customerFilter');
    if (custSelect) {
      if (isCustomer) {
        custSelect.style.display = 'none';
      } else {
        const customers = await fetchCustomers();
        customers.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = `${c.name} (${c.company})`;
          custSelect.appendChild(opt);
        });
      }
    }
  } catch (err) {
    console.error('Failed to load filter options:', err);
  }
}

// Refresh KPI metrics and subscriptions list
async function refreshDashboard() {
  await loadMetrics();
  await loadSubscriptions();
}

async function loadMetrics() {
  try {
    const metrics = await fetchMetrics();
    if (!metrics) return;

    document.getElementById('kpiTotal').textContent = metrics.total;
    document.getElementById('kpiActive').textContent = metrics.active;
    document.getElementById('kpiPipeline').textContent = (metrics.draft || 0) + (metrics.quotation || 0) + (metrics.confirmed || 0);
    document.getElementById('kpiMrr').textContent = formatCurrency(metrics.mrr);
    document.getElementById('kpiExpiring').textContent = (metrics.expiringSoon || 0) + (metrics.expiredUnclosed || 0);

    const expiringSub = document.getElementById('kpiExpiringSub');
    if (expiringSub) {
      expiringSub.textContent = `${metrics.expiringSoon || 0} soon, ${metrics.expiredUnclosed || 0} overdue`;
    }

    // Status Tab Counts
    document.getElementById('countAll').textContent = metrics.total;
    document.getElementById('countDraft').textContent = metrics.draft || 0;
    document.getElementById('countQuotation').textContent = metrics.quotation || 0;
    document.getElementById('countConfirmed').textContent = metrics.confirmed || 0;
    document.getElementById('countActive').textContent = metrics.active || 0;
    document.getElementById('countPaused').textContent = metrics.paused || 0;
    document.getElementById('countClosed').textContent = metrics.closed || 0;
  } catch (err) {
    console.error('Failed to load metrics:', err);
  }
}

async function loadSubscriptions() {
  const tbody = document.getElementById('subscriptionsTableBody');
  tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem;">Loading subscriptions...</td></tr>`;

  try {
    const res = await fetchSubscriptions(activeFilters);
    allSubscriptions = res.subscriptions || [];

    if (allSubscriptions.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8">
            <div class="empty-state">
              <div class="empty-icon">📂</div>
              <h3>No subscriptions found</h3>
              <p>Try adjusting your search query, status tabs, or filter settings.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const today = new Date().toISOString().split('T')[0];
    const canManage = currentUser.role === 'admin' || currentUser.role === 'staff';

    tbody.innerHTML = allSubscriptions.map(sub => {
      const isExpired = sub.expiryDate && sub.expiryDate < today;
      let expiryHtml = formatDate(sub.expiryDate);

      if (isExpired && sub.status !== 'Closed') {
        expiryHtml = `<div class="expiry-danger">⚠️ ${formatDate(sub.expiryDate)}<br><small>EXPIRED</small></div>`;
      } else if (sub.status === 'Active') {
        const daysLeft = Math.ceil((new Date(sub.expiryDate) - new Date()) / (1000 * 60 * 60 * 24));
        if (daysLeft <= 15 && daysLeft >= 0) {
          expiryHtml = `<div class="expiry-warning">⏳ ${formatDate(sub.expiryDate)}<br><small>${daysLeft} days left</small></div>`;
        }
      }

      // Plan & Add-ons Summary
      const planName = sub.plan ? sub.plan.name : 'Unknown Plan';
      const prodCount = (sub.products || []).length;
      const itemsSummary = prodCount > 0 ? `${planName} <small style="color:var(--text-muted);">(+${prodCount} add-on${prodCount > 1 ? 's' : ''})</small>` : planName;

      // Customer Info
      const custName = sub.customer ? sub.customer.name : 'Customer';
      const custCompany = sub.customer ? sub.customer.company : '';

      // Actions buttons based on status & role
      let actionButtons = `
        <a href="/subscription-details.html?id=${sub.id}" class="btn btn-secondary btn-sm" title="View complete details">
          Details
        </a>
      `;

      if (canManage) {
        // Edit button for non-closed or admin
        if (sub.status !== 'Closed') {
          actionButtons += `
            <a href="/subscription-form.html?id=${sub.id}" class="btn btn-secondary btn-sm" title="Edit subscription">
              Edit
            </a>
          `;
        }

        // Contextual quick status actions
        if (sub.status === 'Active') {
          actionButtons += `
            <button class="btn btn-warning btn-sm" onclick="promptPause('${sub.id}', '${sub.subscriptionNumber}')" title="Pause services">
              Pause
            </button>
            <button class="btn btn-success btn-sm" onclick="promptRenew('${sub.id}', '${sub.subscriptionNumber}')" title="Renew validity">
              Renew
            </button>
          `;
        } else if (sub.status === 'Paused') {
          actionButtons += `
            <button class="btn btn-success btn-sm" onclick="handleResume('${sub.id}')" title="Resume active services">
              Resume
            </button>
            <button class="btn btn-danger btn-sm" onclick="promptCancel('${sub.id}', '${sub.subscriptionNumber}')" title="Cancel subscription">
              Cancel
            </button>
          `;
        } else if (sub.status === 'Draft') {
          actionButtons += `
            <button class="btn btn-primary btn-sm" onclick="handleQuickTransition('${sub.id}', 'Quotation', 'Generated quotation for customer')" title="Send Quote">
              Send Quote
            </button>
          `;
        } else if (sub.status === 'Quotation') {
          actionButtons += `
            <button class="btn btn-success btn-sm" onclick="handleQuickTransition('${sub.id}', 'Confirmed', 'Customer confirmed quotation')" title="Confirm order">
              Confirm
            </button>
          `;
        } else if (sub.status === 'Confirmed') {
          actionButtons += `
            <button class="btn btn-primary btn-sm" onclick="handleQuickTransition('${sub.id}', 'Active', 'Payment verified and service activated')" title="Activate">
              Activate
            </button>
          `;
        } else if (sub.status === 'Closed') {
          actionButtons += `
            <button class="btn btn-outline btn-sm" onclick="promptRenew('${sub.id}', '${sub.subscriptionNumber}')" title="Reactivate via renewal">
              Reactivate
            </button>
          `;
        }
      }

      return `
        <tr>
          <td>
            <a href="/subscription-details.html?id=${sub.id}" class="sub-num-link">
              ${sub.subscriptionNumber}
            </a>
            ${sub.autoCloseOnExpiry ? '<div style="font-size:0.7rem;color:var(--text-muted);" title="Configured to automatically close on expiry">🤖 Auto-Close On</div>' : ''}
          </td>
          <td>
            <div class="customer-cell">
              <span class="customer-name">${custName}</span>
              <span class="customer-company">${custCompany}</span>
            </div>
          </td>
          <td>
            <span class="plan-pill">${itemsSummary}</span>
          </td>
          <td style="font-size:0.85rem;">${formatDate(sub.startDate)}</td>
          <td>${expiryHtml}</td>
          <td class="amount-cell">${formatCurrency(sub.totalAmount, sub.currency)}</td>
          <td>${getStatusBadge(sub.status)}</td>
          <td>
            <div class="actions-cell">
              ${actionButtons}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load subscriptions:', err);
    tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center; padding:2rem;">Error loading subscriptions: ${err.message}</td></tr>`;
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Search Input with debounce
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        activeFilters.search = e.target.value;
        loadSubscriptions();
      }, 250);
    });
  }

  // Filter dropdowns
  const planFilter = document.getElementById('planFilter');
  if (planFilter) {
    planFilter.addEventListener('change', (e) => {
      activeFilters.planId = e.target.value;
      loadSubscriptions();
    });
  }

  const customerFilter = document.getElementById('customerFilter');
  if (customerFilter) {
    customerFilter.addEventListener('change', (e) => {
      activeFilters.customerId = e.target.value;
      loadSubscriptions();
    });
  }

  const paymentTermsFilter = document.getElementById('paymentTermsFilter');
  if (paymentTermsFilter) {
    paymentTermsFilter.addEventListener('change', (e) => {
      activeFilters.paymentTerms = e.target.value;
      loadSubscriptions();
    });
  }

  const expiryFilter = document.getElementById('expiryFilter');
  if (expiryFilter) {
    expiryFilter.addEventListener('change', (e) => {
      activeFilters.expiryState = e.target.value;
      loadSubscriptions();
    });
  }

  // Reset Filters
  const btnReset = document.getElementById('btnResetFilters');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      activeFilters = {
        status: 'all',
        planId: 'all',
        customerId: 'all',
        paymentTerms: 'all',
        expiryState: 'all',
        search: ''
      };
      if (searchInput) searchInput.value = '';
      if (planFilter) planFilter.value = 'all';
      if (customerFilter) customerFilter.value = 'all';
      if (paymentTermsFilter) paymentTermsFilter.value = 'all';
      if (expiryFilter) expiryFilter.value = 'all';

      document.querySelectorAll('.status-tab').forEach(t => t.classList.remove('active'));
      document.querySelector('.status-tab[data-status="all"]')?.classList.add('active');

      loadSubscriptions();
    });
  }

  // Status Tabs
  const statusTabs = document.getElementById('statusTabs');
  if (statusTabs) {
    statusTabs.addEventListener('click', (e) => {
      const tab = e.target.closest('.status-tab');
      if (!tab) return;
      document.querySelectorAll('.status-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeFilters.status = tab.getAttribute('data-status');
      loadSubscriptions();
    });
  }

  // Auto-Close Trigger Button
  const btnAutoClose = document.getElementById('btnAutoCloseTrigger');
  if (btnAutoClose) {
    btnAutoClose.addEventListener('click', async () => {
      try {
        btnAutoClose.disabled = true;
        btnAutoClose.innerHTML = '<span>⏳</span> Checking expired...';
        const res = await autoCloseExpiredSubscriptions();
        if (res.count > 0) {
          showToast(`Successfully auto-closed ${res.count} expired subscription(s)!`, 'success');
        } else {
          showToast('No active expired subscriptions eligible for automated closure.', 'success');
        }
        await refreshDashboard();
      } catch (err) {
        showToast(`Auto-close check error: ${err.message}`, 'error');
      } finally {
        btnAutoClose.disabled = false;
        btnAutoClose.innerHTML = '<span>⚡</span> Run Auto-Close Check';
      }
    });
  }

  // Modal confirm buttons
  const btnConfirmPause = document.getElementById('btnConfirmPause');
  if (btnConfirmPause) {
    btnConfirmPause.addEventListener('click', async () => {
      const reason = document.getElementById('pauseReasonInput').value.trim();
      if (!reason) {
        alert('Please enter a pause reason');
        return;
      }
      try {
        await pauseSubscription(currentModalSubId, reason);
        showToast('Subscription paused successfully', 'success');
        closeModal('pauseModal');
        await refreshDashboard();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  const btnConfirmRenew = document.getElementById('btnConfirmRenew');
  if (btnConfirmRenew) {
    btnConfirmRenew.addEventListener('click', async () => {
      const duration = parseInt(document.getElementById('renewDurationSelect').value, 10);
      const notes = document.getElementById('renewNotesInput').value.trim();
      try {
        await renewSubscription(currentModalSubId, duration, notes);
        showToast('Subscription renewed successfully', 'success');
        closeModal('renewModal');
        await refreshDashboard();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  const btnConfirmCancel = document.getElementById('btnConfirmCancel');
  if (btnConfirmCancel) {
    btnConfirmCancel.addEventListener('click', async () => {
      const reason = document.getElementById('cancelReasonInput').value.trim();
      if (!reason) {
        alert('Please provide a reason for cancellation');
        return;
      }
      try {
        await cancelSubscription(currentModalSubId, reason);
        showToast('Subscription cancelled (Closed)', 'success');
        closeModal('cancelModal');
        await refreshDashboard();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }
}

// Global actions called from table buttons
window.promptPause = function(id, num) {
  currentModalSubId = id;
  document.getElementById('pauseSubNumber').textContent = num;
  document.getElementById('pauseReasonInput').value = '';
  openModal('pauseModal');
};

window.promptRenew = function(id, num) {
  currentModalSubId = id;
  document.getElementById('renewSubNumber').textContent = num;
  document.getElementById('renewNotesInput').value = '';
  openModal('renewModal');
};

window.promptCancel = function(id, num) {
  currentModalSubId = id;
  document.getElementById('cancelSubNumber').textContent = num;
  document.getElementById('cancelReasonInput').value = '';
  openModal('cancelModal');
};

window.handleResume = async function(id) {
  if (!confirm('Are you sure you want to resume this paused subscription to Active?')) return;
  try {
    await resumeSubscription(id);
    showToast('Subscription resumed to Active', 'success');
    await refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.handleQuickTransition = async function(id, targetStatus, note) {
  try {
    await transitionStatus(id, targetStatus, note);
    showToast(`Status updated to ${targetStatus}`, 'success');
    await refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
};
