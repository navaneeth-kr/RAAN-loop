// Brightloop Software — Subscription Management Application Logic

// Application State
const state = {
  currentUser: {
    role: 'admin',
    customerId: null,
    userName: 'Sarah Jenkins (Admin)'
  },
  activeTab: 'subscriptions',
  subscriptions: [],
  currentSubscription: null,
  customers: [],
  plans: [],
  products: [],
  templates: [],
  invoices: [],
  stats: null,
  filters: {
    status: 'All',
    search: '',
    planId: 'All',
    customerId: 'All'
  },
  editingSubscriptionId: null,
  targetActionSubId: null // for pause/renew/cancel modals
};

// ==========================================
// API CLIENT
// ==========================================
async function apiRequest(endpoint, method = 'GET', data = null) {
  const headers = {
    'Content-Type': 'application/json',
    'x-user-role': state.currentUser.role,
    'x-user-name': state.currentUser.userName
  };
  if (state.currentUser.customerId) {
    headers['x-user-customer-id'] = state.currentUser.customerId;
  }

  const options = { method, headers };
  if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
    options.body = JSON.stringify(data);
  }

  try {
    const res = await fetch(endpoint, options);
    const json = await res.json();
    if (!res.ok) {
      throw new Error(json.error || `HTTP error ${res.status}`);
    }
    return json;
  } catch (err) {
    console.error(`API Error on ${method} ${endpoint}:`, err);
    throw err;
  }
}

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
  await loadInitialMetadata();
  await refreshData();
});

async function loadInitialMetadata() {
  try {
    const [customers, plans, products, templates] = await Promise.all([
      apiRequest('/api/customers'),
      apiRequest('/api/plans'),
      apiRequest('/api/products'),
      apiRequest('/api/quotation-templates')
    ]);

    state.customers = customers;
    state.plans = plans;
    state.products = products;
    state.templates = templates;

    populateDropdowns();
  } catch (err) {
    showToast('Failed to load initial metadata: ' + err.message, 'error');
  }
}

async function refreshData() {
  try {
    let url = `/api/subscriptions?search=${encodeURIComponent(state.filters.search)}`;
    if (state.filters.status !== 'All') url += `&status=${encodeURIComponent(state.filters.status)}`;
    if (state.filters.planId !== 'All') url += `&planId=${encodeURIComponent(state.filters.planId)}`;
    if (state.filters.customerId !== 'All') url += `&customerId=${encodeURIComponent(state.filters.customerId)}`;

    const [subs, stats, invoices] = await Promise.all([
      apiRequest(url),
      apiRequest('/api/dashboard/stats'),
      apiRequest('/api/invoices')
    ]);

    state.subscriptions = subs;
    state.stats = stats;
    state.invoices = invoices;

    renderMetrics();
    renderSubscriptionsTable();
    renderInvoicesTable();
    renderTemplatesView();
    renderCatalogView();
    renderAnalyticsView();

    // If on details view, refresh the currently open subscription
    if (state.currentSubscription) {
      const updated = subs.find(s => s.id === state.currentSubscription.id);
      if (updated) {
        viewSubscriptionDetail(updated.id);
      }
    }
  } catch (err) {
    showToast('Failed to fetch subscriptions data: ' + err.message, 'error');
  }
}

// ==========================================
// ROLE SWITCHING & PERMISSIONS
// ==========================================
function handleRoleChange(value) {
  const roleTag = document.getElementById('role-tag');
  const btnCreateTop = document.getElementById('btn-create-sub-top');
  const btnRunAutoClose = document.getElementById('btn-run-autoclose');

  if (value.startsWith('customer:')) {
    const parts = value.split(':');
    state.currentUser.role = 'customer';
    state.currentUser.customerId = parts[1];
    
    const cust = state.customers.find(c => c.id === parts[1]);
    state.currentUser.userName = cust ? `${cust.contactName} (${cust.name})` : 'Customer';

    roleTag.className = 'active-role-tag role-customer';
    roleTag.textContent = 'Customer Portal';

    if (btnCreateTop) btnCreateTop.style.display = 'none';
    if (btnRunAutoClose) btnRunAutoClose.style.display = 'none';
  } else if (value === 'staff') {
    state.currentUser.role = 'staff';
    state.currentUser.customerId = null;
    state.currentUser.userName = 'Alex Miller (Sales Staff)';

    roleTag.className = 'active-role-tag role-staff';
    roleTag.textContent = 'Staff';

    if (btnCreateTop) btnCreateTop.style.display = 'inline-flex';
    if (btnRunAutoClose) btnRunAutoClose.style.display = 'inline-flex';
  } else {
    state.currentUser.role = 'admin';
    state.currentUser.customerId = null;
    state.currentUser.userName = 'Sarah Jenkins (Admin)';

    roleTag.className = 'active-role-tag role-admin';
    roleTag.textContent = 'Admin';

    if (btnCreateTop) btnCreateTop.style.display = 'inline-flex';
    if (btnRunAutoClose) btnRunAutoClose.style.display = 'inline-flex';
  }

  showToast(`Switched active session to: ${state.currentUser.userName}`, 'info');
  refreshData();
}

// ==========================================
// NAVIGATION & TABS
// ==========================================
function switchTab(tabName) {
  state.activeTab = tabName;
  
  // Close details view if open
  document.getElementById('view-subscription-detail').style.display = 'none';
  state.currentSubscription = null;

  // Update tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.toggle('active', tab.getAttribute('data-tab') === tabName);
  });

  // Toggle views
  document.getElementById('view-subscriptions-list').style.display = tabName === 'subscriptions' ? 'block' : 'none';
  document.getElementById('view-invoices').style.display = tabName === 'invoices' ? 'block' : 'none';
  document.getElementById('view-templates').style.display = tabName === 'templates' ? 'block' : 'none';
  document.getElementById('view-catalog').style.display = tabName === 'catalog' ? 'block' : 'none';
  document.getElementById('view-analytics').style.display = tabName === 'analytics' ? 'block' : 'none';
}

function backToSubscriptionsList() {
  document.getElementById('view-subscription-detail').style.display = 'none';
  document.getElementById('view-subscriptions-list').style.display = 'block';
  state.currentSubscription = null;
  refreshData();
}

// ==========================================
// METRICS RENDERING
// ==========================================
function renderMetrics() {
  if (!state.stats) return;

  const { counts, mrr, totalRevenuePaid, totalOutstanding } = state.stats;

  document.getElementById('metric-active-subs').textContent = counts.active;
  document.getElementById('metric-total-subs').textContent = `${counts.all} total subscriptions on record`;
  document.getElementById('metric-mrr').textContent = `$${mrr.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('metric-paid-rev').textContent = `$${totalRevenuePaid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('metric-outstanding').textContent = `$${totalOutstanding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Status pill counts
  document.getElementById('count-all').textContent = counts.all;
  document.getElementById('count-draft').textContent = counts.draft;
  document.getElementById('count-quotation').textContent = counts.quotation;
  document.getElementById('count-confirmed').textContent = counts.confirmed;
  document.getElementById('count-active').textContent = counts.active;
  document.getElementById('count-paused').textContent = counts.paused;
  document.getElementById('count-closed').textContent = counts.closed;
}

// ==========================================
// DROPDOWNS POPULATION
// ==========================================
function populateDropdowns() {
  // Plan filter
  const planFilter = document.getElementById('sub-plan-filter');
  planFilter.innerHTML = '<option value="All">All Plans</option>' +
    state.plans.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');

  // Customer filter
  const custFilter = document.getElementById('sub-customer-filter');
  custFilter.innerHTML = '<option value="All">All Customers</option>' +
    state.customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');

  // Modal customer select
  const modalCust = document.getElementById('modal-sub-customer');
  modalCust.innerHTML = '<option value="">-- Select Customer --</option>' +
    state.customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${escapeHtml(c.company)})</option>`).join('');

  // Modal plan select
  const modalPlan = document.getElementById('modal-sub-plan');
  modalPlan.innerHTML = '<option value="">-- Select Subscription Plan --</option>' +
    state.plans.map(p => `<option value="${p.id}">${escapeHtml(p.name)} - $${p.basePrice}/${p.billingFrequency}</option>`).join('');

  // Modal template select
  const modalTpl = document.getElementById('modal-template-select');
  modalTpl.innerHTML = '<option value="">-- Choose a template to pre-fill lines and plan --</option>' +
    state.templates.map(t => `<option value="${t.id}">⚡ ${escapeHtml(t.name)} (${t.items.length} items)</option>`).join('');
}

// ==========================================
// SEARCH & FILTER HANDLERS
// ==========================================
let searchDebounceTimer = null;
function handleSearchInput(value) {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    state.filters.search = value;
    refreshData();
  }, 250);
}

function filterByStatus(status) {
  state.filters.status = status;
  document.querySelectorAll('.status-pill').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-status') === status);
  });
  refreshData();
}

function handlePlanFilter(planId) {
  state.filters.planId = planId;
  refreshData();
}

function handleCustomerFilter(customerId) {
  state.filters.customerId = customerId;
  refreshData();
}

function resetFilters() {
  state.filters.status = 'All';
  state.filters.search = '';
  state.filters.planId = 'All';
  state.filters.customerId = 'All';

  document.getElementById('sub-search-input').value = '';
  document.getElementById('sub-plan-filter').value = 'All';
  document.getElementById('sub-customer-filter').value = 'All';

  document.querySelectorAll('.status-pill').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-status') === 'All');
  });

  refreshData();
}

// ==========================================
// SUBSCRIPTIONS LIST TABLE RENDERING
// ==========================================
function renderSubscriptionsTable() {
  const tbody = document.getElementById('subscriptions-table-body');
  const emptyState = document.getElementById('sub-empty-state');
  tbody.innerHTML = '';

  if (state.subscriptions.length === 0) {
    emptyState.style.display = 'block';
    return;
  }
  emptyState.style.display = 'none';

  state.subscriptions.forEach(sub => {
    const tr = document.createElement('tr');

    const custName = sub.customer ? sub.customer.name : 'Unknown Customer';
    const custEmail = sub.customer ? sub.customer.email : '';
    const planName = sub.plan ? sub.plan.name : 'Custom Plan';
    const planFreq = sub.plan ? sub.plan.billingFrequency : 'monthly';

    // Summary of product items
    const itemsSummary = (sub.items || []).map(i => `${i.productName} (${i.quantity})`).join(', ');

    // Status class
    const statusLower = (sub.status || 'draft').toLowerCase();

    // Contextual action buttons in row
    let actionsHtml = `
      <button class="btn btn-secondary btn-sm" onclick="viewSubscriptionDetail('${sub.id}')" title="View details page">
        View
      </button>
    `;

    // Only staff/admin or quotation acceptance
    if (state.currentUser.role !== 'customer') {
      if (['Draft', 'Quotation'].includes(sub.status)) {
        actionsHtml += `
          <button class="btn btn-secondary btn-sm" onclick="openEditSubscription('${sub.id}')" title="Edit subscription">
            ✏️
          </button>
        `;
      }
      if (sub.status === 'Active') {
        actionsHtml += `
          <button class="btn btn-warning btn-sm" onclick="openPauseModal('${sub.id}')" title="Pause subscription">
            ⏸
          </button>
        `;
      } else if (sub.status === 'Paused') {
        actionsHtml += `
          <button class="btn btn-success btn-sm" onclick="resumeSubscription('${sub.id}')" title="Resume subscription">
            ▶
          </button>
        `;
      }
    } else {
      // Customer view
      if (sub.status === 'Quotation') {
        actionsHtml += `
          <button class="btn btn-success btn-sm" onclick="transitionStatus('${sub.id}', 'Confirmed', 'Quotation accepted by customer via portal')" title="Accept Quotation">
            Accept Quote
          </button>
        `;
      }
    }

    tr.innerHTML = `
      <td>
        <span class="sub-num-cell" style="cursor: pointer;" onclick="viewSubscriptionDetail('${sub.id}')">
          ${escapeHtml(sub.subscriptionNumber)}
        </span>
      </td>
      <td>
        <div class="cust-name">${escapeHtml(custName)}</div>
        <div class="cust-sub">${escapeHtml(custEmail)}</div>
      </td>
      <td>
        <div style="font-weight: 600;">${escapeHtml(planName)}</div>
        <div class="cust-sub" style="text-transform: capitalize;">Billed ${escapeHtml(planFreq)}</div>
      </td>
      <td>
        <div style="font-size: 0.85rem; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(itemsSummary)}">
          ${escapeHtml(itemsSummary || 'No items')}
        </div>
      </td>
      <td>
        <div style="font-weight: 700; color: var(--neutral-900);">
          $${(sub.totalAmount || 0).toFixed(2)}
        </div>
      </td>
      <td><span style="font-size: 0.85rem;">${sub.startDate || '-'}</span></td>
      <td><span style="font-size: 0.85rem; ${isPastDate(sub.expiryDate) && sub.status !== 'Closed' ? 'color: var(--danger); font-weight: 700;' : ''}">${sub.expiryDate || '-'}</span></td>
      <td>
        <span class="badge-status ${statusLower}">${escapeHtml(sub.status)}</span>
      </td>
      <td style="text-align: right; white-space: nowrap;">
        ${actionsHtml}
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function isPastDate(dateStr) {
  if (!dateStr) return false;
  const today = new Date().toISOString().split('T')[0];
  return dateStr < today;
}

// ==========================================
// SUBSCRIPTION DETAILS PAGE VIEW
// ==========================================
async function viewSubscriptionDetail(subId) {
  try {
    const sub = await apiRequest(`/api/subscriptions/${subId}`);
    state.currentSubscription = sub;

    // Switch to details section
    document.getElementById('view-subscriptions-list').style.display = 'none';
    document.getElementById('view-subscription-detail').style.display = 'block';

    // Populate Header
    document.getElementById('det-sub-number').textContent = sub.subscriptionNumber;
    const badge = document.getElementById('det-sub-status-badge');
    badge.className = `badge-status ${(sub.status || 'draft').toLowerCase()}`;
    badge.textContent = sub.status;

    const autoCloseInd = document.getElementById('det-autoclose-indicator');
    autoCloseInd.style.display = (sub.autoClose || (sub.plan && sub.plan.autoClose)) ? 'inline-block' : 'none';

    document.getElementById('det-sub-subtitle').textContent = `Created for ${sub.customer ? sub.customer.name : 'Unknown Customer'} on ${formatDateTime(sub.createdAt)}`;
    document.getElementById('det-sub-total-header').textContent = `$${(sub.totalAmount || 0).toFixed(2)}`;
    document.getElementById('det-sub-payment-terms-header').textContent = `Payment Terms: ${sub.paymentTerms || '30 Days'}`;

    // Update Stepper
    updateStatusStepper(sub.status);

    // Customer & Plan info
    document.getElementById('det-cust-name').textContent = sub.customer ? sub.customer.name : 'N/A';
    document.getElementById('det-cust-email').textContent = sub.customer ? sub.customer.email : 'N/A';
    document.getElementById('det-cust-phone').textContent = sub.customer && sub.customer.phone ? sub.customer.phone : 'N/A';
    document.getElementById('det-cust-address').textContent = sub.customer && sub.customer.address ? sub.customer.address : 'N/A';

    document.getElementById('det-plan-name').textContent = sub.plan ? sub.plan.name : 'N/A';
    document.getElementById('det-plan-freq').textContent = sub.plan ? `${sub.plan.billingFrequency} (${sub.plan.intervalDays} days)` : 'Monthly';
    document.getElementById('det-start-date').textContent = sub.startDate || 'N/A';
    document.getElementById('det-expiry-date').textContent = sub.expiryDate || 'N/A';
    document.getElementById('det-payment-terms').textContent = sub.paymentTerms || '30 Days';
    document.getElementById('det-autoclose-val').textContent = (sub.autoClose || (sub.plan && sub.plan.autoClose)) ? 'Enabled (Auto-terminate on expiry)' : 'Disabled';
    document.getElementById('det-notes').textContent = sub.notes || 'No notes recorded.';

    // Product lines table
    const prodTbody = document.getElementById('det-products-table-body');
    prodTbody.innerHTML = '';
    (sub.items || []).forEach(item => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>
          <div style="font-weight: 700; color: var(--neutral-900);">${escapeHtml(item.productName)}</div>
          <div style="font-size: 0.78rem; color: var(--neutral-500);">${escapeHtml(item.variant || 'Standard Edition')}</div>
        </td>
        <td style="text-align: center; font-weight: 600;">${item.quantity}</td>
        <td style="text-align: right;">$${parseFloat(item.unitPrice).toFixed(2)}</td>
        <td style="text-align: right;">${item.taxRate}%</td>
        <td style="text-align: right; color: var(--neutral-600);">$${parseFloat(item.taxAmount || 0).toFixed(2)}</td>
        <td style="text-align: right; font-weight: 700; color: var(--neutral-900);">$${parseFloat(item.lineTotal || 0).toFixed(2)}</td>
      `;
      prodTbody.appendChild(row);
    });

    // Totals
    document.getElementById('det-subtotal-val').textContent = `$${(sub.subtotal || 0).toFixed(2)}`;
    document.getElementById('det-tax-val').textContent = `$${(sub.taxTotal || 0).toFixed(2)}`;
    document.getElementById('det-grandtotal-val').textContent = `$${(sub.totalAmount || 0).toFixed(2)}`;

    // Linked Invoices
    renderDetailInvoices(sub);

    // Audit Trail
    renderTimeline(sub.timeline || []);

    // Contextual Action Buttons in Details Header
    renderDetailActionButtons(sub);

  } catch (err) {
    showToast('Failed to load subscription details: ' + err.message, 'error');
  }
}

// Update status stepper progress bar
function updateStatusStepper(currentStatus) {
  const steps = ['Draft', 'Quotation', 'Confirmed', 'Active', 'Closed'];
  const curIndex = steps.indexOf(currentStatus);

  steps.forEach((step, idx) => {
    const el = document.getElementById(`step-${step.toLowerCase()}`);
    if (!el) return;

    el.className = 'stepper-step';

    if (currentStatus === 'Paused' && step === 'Active') {
      el.classList.add('paused-step');
    } else if (idx < curIndex && currentStatus !== 'Closed') {
      el.classList.add('completed');
    } else if (step === currentStatus) {
      if (step === 'Closed') el.classList.add('closed-step');
      else el.classList.add('current');
    }
  });
}

// Render contextual action buttons in details view
function renderDetailActionButtons(sub) {
  const bar = document.getElementById('detail-actions-bar');
  bar.innerHTML = '';

  const isCustomer = state.currentUser.role === 'customer';
  const isStaffOrAdmin = !isCustomer;

  // Print button always available
  const printBtn = document.createElement('button');
  printBtn.className = 'btn btn-secondary';
  printBtn.innerHTML = '🖨️ Print / Export';
  printBtn.onclick = () => window.print();
  bar.appendChild(printBtn);

  // Edit details button permissions
  const btnEdit = document.getElementById('btn-edit-subscription-details');
  if (btnEdit) {
    btnEdit.style.display = isStaffOrAdmin ? 'inline-flex' : 'none';
  }

  // Invoice generation button permissions
  const btnGenInv = document.getElementById('btn-gen-invoice-detail');
  if (btnGenInv) {
    btnGenInv.style.display = isStaffOrAdmin && ['Confirmed', 'Active', 'Closed'].includes(sub.status) ? 'inline-flex' : 'none';
  }

  // State-specific actions:
  if (sub.status === 'Draft' && isStaffOrAdmin) {
    bar.appendChild(createBtn('btn-primary', 'Send Quotation →', () => transitionStatus(sub.id, 'Quotation', 'Quotation prepared and sent to customer')));
    bar.appendChild(createBtn('btn-danger', 'Cancel Draft', () => openCancelModal(sub.id)));
  } 
  else if (sub.status === 'Quotation') {
    if (isStaffOrAdmin) {
      bar.appendChild(createBtn('btn-success', 'Confirm Subscription ✓', () => transitionStatus(sub.id, 'Confirmed', 'Quotation confirmed by sales')));
      bar.appendChild(createBtn('btn-secondary', 'Revise to Draft', () => transitionStatus(sub.id, 'Draft', 'Reverted quotation to draft for revision')));
      bar.appendChild(createBtn('btn-danger', 'Cancel Quote', () => openCancelModal(sub.id)));
    } else {
      // Customer portal: Can accept quotation!
      bar.appendChild(createBtn('btn-success', '✓ Accept & Confirm Quotation', () => transitionStatus(sub.id, 'Confirmed', 'Quotation accepted by customer via portal')));
    }
  } 
  else if (sub.status === 'Confirmed' && isStaffOrAdmin) {
    bar.appendChild(createBtn('btn-success', '🚀 Activate Subscription', () => transitionStatus(sub.id, 'Active', 'Subscription activated and provisioned')));
    bar.appendChild(createBtn('btn-secondary', '🧾 Generate Invoice', () => generateInvoiceForCurrentSub()));
    bar.appendChild(createBtn('btn-danger', 'Cancel Subscription', () => openCancelModal(sub.id)));
  } 
  else if (sub.status === 'Active') {
    if (isStaffOrAdmin) {
      bar.appendChild(createBtn('btn-secondary', '🧾 Generate Invoice', () => generateInvoiceForCurrentSub()));
      bar.appendChild(createBtn('btn-warning', '⏸ Pause Subscription', () => openPauseModal(sub.id)));
      bar.appendChild(createBtn('btn-success', '🔄 Renew Subscription', () => openRenewModal(sub.id)));
      bar.appendChild(createBtn('btn-danger', 'Cancel Subscription', () => openCancelModal(sub.id)));
    }
  } 
  else if (sub.status === 'Paused' && isStaffOrAdmin) {
    bar.appendChild(createBtn('btn-success', '▶ Resume Subscription', () => resumeSubscription(sub.id)));
    bar.appendChild(createBtn('btn-danger', 'Cancel Subscription', () => openCancelModal(sub.id)));
  } 
  else if (sub.status === 'Closed' && isStaffOrAdmin) {
    bar.appendChild(createBtn('btn-success', '🔄 Renew / Reopen Subscription', () => openRenewModal(sub.id)));
  }
}

function createBtn(className, text, onClick) {
  const btn = document.createElement('button');
  btn.className = `btn ${className}`;
  btn.textContent = text;
  btn.onclick = onClick;
  return btn;
}

// Render Linked Invoices in Details
function renderDetailInvoices(sub) {
  const container = document.getElementById('det-invoices-list');
  const invoices = sub.invoices || [];

  if (invoices.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.5rem 0; color: var(--neutral-400); font-size: 0.88rem;">
        No invoices generated yet.
      </div>
    `;
    return;
  }

  container.innerHTML = invoices.map(inv => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--neutral-200);">
      <div>
        <div style="font-weight: 700; font-family: monospace; color: var(--primary);">${escapeHtml(inv.invoiceNumber)}</div>
        <div style="font-size: 0.78rem; color: var(--neutral-500);">Due: ${inv.dueDate} · ${inv.paymentTerms}</div>
      </div>
      <div style="text-align: right;">
        <div style="font-weight: 700; color: var(--neutral-900);">$${inv.totalAmount.toFixed(2)}</div>
        <span class="badge-status ${inv.status.toLowerCase()}">${inv.status}</span>
        ${inv.status !== 'Paid' && state.currentUser.role !== 'customer' ? `
          <button class="btn btn-success btn-sm" style="margin-left: 0.5rem; padding: 0.2rem 0.5rem;" onclick="openPaymentModal('${inv.id}', ${inv.totalAmount})">
            Record Pay
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

// Render Audit Trail Timeline
function renderTimeline(timeline) {
  const container = document.getElementById('det-timeline-list');
  if (timeline.length === 0) {
    container.innerHTML = '<li>No events recorded.</li>';
    return;
  }

  container.innerHTML = timeline.map(event => `
    <li class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-header">
        <span class="timeline-title">${escapeHtml(event.status)}</span>
        <span class="timeline-date">${formatDateTime(event.date)}</span>
      </div>
      <div class="timeline-user">By: ${escapeHtml(event.user || 'System')}</div>
      ${event.note ? `<div class="timeline-note">${escapeHtml(event.note)}</div>` : ''}
    </li>
  `).join('');
}

// ==========================================
// STATUS TRANSITION ACTIONS
// ==========================================
async function transitionStatus(subId, targetStatus, note) {
  try {
    const updated = await apiRequest(`/api/subscriptions/${subId}/transition`, 'POST', {
      status: targetStatus,
      note: note
    });

    showToast(`Subscription transitioned to ${targetStatus}!`, 'success');
    viewSubscriptionDetail(subId);
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Pause Subscription Modal & Execution
function openPauseModal(subId) {
  state.targetActionSubId = subId;
  document.getElementById('pause-modal-note').value = '';
  openModal('modal-pause');
}

async function confirmPauseSubscription() {
  if (!state.targetActionSubId) return;
  const note = document.getElementById('pause-modal-note').value.trim() || 'Subscription paused by staff';

  try {
    await apiRequest(`/api/subscriptions/${state.targetActionSubId}/pause`, 'POST', { note });
    closeModal('modal-pause');
    showToast('Subscription paused.', 'warning');
    if (state.currentSubscription && state.currentSubscription.id === state.targetActionSubId) {
      viewSubscriptionDetail(state.targetActionSubId);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Resume Subscription
async function resumeSubscription(subId) {
  try {
    await apiRequest(`/api/subscriptions/${subId}/resume`, 'POST', {
      note: 'Subscription resumed from paused state'
    });
    showToast('Subscription resumed and active!', 'success');
    if (state.currentSubscription && state.currentSubscription.id === subId) {
      viewSubscriptionDetail(subId);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Renew Subscription Modal & Execution
function openRenewModal(subId) {
  state.targetActionSubId = subId;
  document.getElementById('renew-modal-note').value = '';
  openModal('modal-renew');
}

async function confirmRenewSubscription() {
  if (!state.targetActionSubId) return;
  const intervalDays = parseInt(document.getElementById('renew-modal-interval').value, 10);
  const note = document.getElementById('renew-modal-note').value.trim();

  try {
    const res = await apiRequest(`/api/subscriptions/${state.targetActionSubId}/renew`, 'POST', {
      intervalDays,
      note
    });
    closeModal('modal-renew');
    showToast(`Subscription renewed! New expiry: ${res.newExpiryDate}`, 'success');
    if (state.currentSubscription && state.currentSubscription.id === state.targetActionSubId) {
      viewSubscriptionDetail(state.targetActionSubId);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Cancel Subscription Modal & Execution
function openCancelModal(subId) {
  state.targetActionSubId = subId;
  document.getElementById('cancel-modal-reason').value = '';
  openModal('modal-cancel');
}

async function confirmCancelSubscription() {
  if (!state.targetActionSubId) return;
  const reason = document.getElementById('cancel-modal-reason').value.trim() || 'Cancelled per customer/staff request';

  try {
    await apiRequest(`/api/subscriptions/${state.targetActionSubId}/cancel`, 'POST', { reason });
    closeModal('modal-cancel');
    showToast('Subscription cancelled and marked Closed.', 'info');
    if (state.currentSubscription && state.currentSubscription.id === state.targetActionSubId) {
      viewSubscriptionDetail(state.targetActionSubId);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Trigger Auto-Close Expired Check
async function triggerAutoCloseExpired() {
  try {
    const res = await apiRequest('/api/cron/auto-close-expired', 'POST');
    if (res.closedCount > 0) {
      showToast(`⚡ Expired Check Completed: Closed ${res.closedCount} past-due subscriptions!`, 'warning');
    } else {
      showToast('⚡ Expired Check Completed: No active expired subscriptions needed closing.', 'info');
    }
    refreshData();
  } catch (err) {
    showToast('Auto-close execution failed: ' + err.message, 'error');
  }
}

// ==========================================
// INVOICES & PAYMENTS HANDLING
// ==========================================
async function generateInvoiceForCurrentSub() {
  if (!state.currentSubscription) return;
  try {
    const inv = await apiRequest(`/api/invoices/generate-from-subscription/${state.currentSubscription.id}`, 'POST');
    showToast(`Invoice ${inv.invoiceNumber} generated for $${inv.totalAmount.toFixed(2)}!`, 'success');
    viewSubscriptionDetail(state.currentSubscription.id);
    refreshData();
  } catch (err) {
    showToast('Failed to generate invoice: ' + err.message, 'error');
  }
}

function renderInvoicesTable() {
  const tbody = document.getElementById('invoices-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  state.invoices.forEach(inv => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="sub-num-cell">${escapeHtml(inv.invoiceNumber)}</span></td>
      <td><span style="font-family: monospace;">${escapeHtml(inv.subscriptionNumber || 'N/A')}</span></td>
      <td><strong>${escapeHtml(inv.customerName || 'Customer')}</strong></td>
      <td>${inv.issueDate}</td>
      <td>${inv.dueDate}</td>
      <td>${inv.paymentTerms}</td>
      <td style="font-weight: 700; color: var(--neutral-900);">$${inv.totalAmount.toFixed(2)}</td>
      <td><span class="badge-status ${inv.status.toLowerCase()}">${inv.status}</span></td>
      <td style="text-align: right;">
        ${inv.status === 'Draft' && state.currentUser.role !== 'customer' ? `
          <button class="btn btn-secondary btn-sm" onclick="confirmInvoice('${inv.id}')">Confirm</button>
        ` : ''}
        ${inv.status !== 'Paid' && state.currentUser.role !== 'customer' ? `
          <button class="btn btn-success btn-sm" onclick="openPaymentModal('${inv.id}', ${inv.totalAmount})">Record Pay</button>
        ` : ''}
        ${inv.status === 'Paid' ? `
          <span style="color: var(--success); font-weight: 700; font-size: 0.82rem;">✓ Settled</span>
        ` : ''}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function confirmInvoice(invId) {
  try {
    await apiRequest(`/api/invoices/${invId}/confirm`, 'POST');
    showToast('Invoice confirmed.', 'success');
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

let activePaymentInvoiceId = null;
function openPaymentModal(invId, totalAmount) {
  activePaymentInvoiceId = invId;
  document.getElementById('pay-modal-amount').value = totalAmount.toFixed(2);
  document.getElementById('pay-modal-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('pay-modal-ref').value = `REF-${Math.floor(100000 + Math.random() * 900000)}`;
  document.getElementById('pay-modal-notes').value = 'Settled via online gateway';
  openModal('modal-payment');
}

async function submitRecordPayment() {
  if (!activePaymentInvoiceId) return;
  const amount = parseFloat(document.getElementById('pay-modal-amount').value);
  const method = document.getElementById('pay-modal-method').value;
  const reference = document.getElementById('pay-modal-ref').value;
  const date = document.getElementById('pay-modal-date').value;
  const notes = document.getElementById('pay-modal-notes').value;

  if (isNaN(amount) || amount <= 0) {
    return showToast('Please enter a valid payment amount.', 'warning');
  }

  try {
    await apiRequest(`/api/invoices/${activePaymentInvoiceId}/pay`, 'POST', {
      amount, method, reference, date, notes
    });
    closeModal('modal-payment');
    showToast(`Payment of $${amount.toFixed(2)} recorded! Invoice marked Paid.`, 'success');
    if (state.currentSubscription) {
      viewSubscriptionDetail(state.currentSubscription.id);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// TEMPLATES VIEW RENDERING
// ==========================================
function renderTemplatesView() {
  const grid = document.getElementById('templates-grid');
  if (!grid) return;
  grid.innerHTML = '';

  state.templates.forEach(t => {
    const plan = state.plans.find(p => p.id === t.planId) || {};
    const card = document.createElement('div');
    card.className = 'card';
    card.style.margin = '0';
    card.innerHTML = `
      <div class="card-header">
        <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--primary);">${escapeHtml(t.name)}</h4>
      </div>
      <p style="font-size: 0.85rem; color: var(--neutral-600); margin-bottom: 0.75rem;">
        Plan: <strong>${escapeHtml(plan.name || 'Custom Plan')}</strong><br>
        Payment Terms: <strong>${escapeHtml(t.paymentTerms)}</strong><br>
        Validity: <strong>${t.validityDays} days</strong>
      </p>
      <div style="background: var(--neutral-50); padding: 0.5rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
        <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--neutral-500); margin-bottom: 0.25rem;">Included Product Lines:</div>
        <ul style="font-size: 0.82rem; padding-left: 1.25rem; color: var(--neutral-700);">
          ${t.items.map(item => {
            const prod = state.products.find(p => p.id === item.productId) || {};
            return `<li>${prod.name || 'Product'} (${item.variant}) × ${item.quantity}</li>`;
          }).join('')}
        </ul>
      </div>
      <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="startSubscriptionFromTemplate('${t.id}')">
        ⚡ Launch Offer From Template
      </button>
    `;
    grid.appendChild(card);
  });
}

function startSubscriptionFromTemplate(templateId) {
  openCreateSubscriptionModal();
  document.getElementById('modal-template-select').value = templateId;
  applyQuotationTemplate(templateId);
}

// ==========================================
// CATALOG VIEW RENDERING
// ==========================================
function renderCatalogView() {
  const prodTbody = document.getElementById('products-catalog-body');
  if (prodTbody) {
    prodTbody.innerHTML = state.products.map(p => `
      <tr>
        <td><strong>${escapeHtml(p.name)}</strong><br><span style="font-size: 0.78rem; color: var(--neutral-500);">${escapeHtml(p.notes || '')}</span></td>
        <td><span class="badge-status draft">${p.type}</span></td>
        <td><strong>$${p.salesPrice.toFixed(2)}</strong></td>
        <td>$${p.costPrice.toFixed(2)}</td>
        <td>${p.taxRate}%</td>
        <td>
          ${(p.variants || []).map(v => `<span style="display: inline-block; background: var(--neutral-100); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.78rem; margin: 0.15rem;">${v.name} (${v.priceDelta >= 0 ? '+' : ''}$${v.priceDelta})</span>`).join(' ')}
        </td>
      </tr>
    `).join('');
  }

  const planTbody = document.getElementById('plans-catalog-body');
  if (planTbody) {
    planTbody.innerHTML = state.plans.map(p => `
      <tr>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td style="text-transform: capitalize;">${p.billingFrequency}</td>
        <td>${p.intervalDays} days</td>
        <td><strong>$${p.basePrice.toFixed(2)}</strong></td>
        <td>${p.minQuantity} min</td>
        <td>
          ${p.autoClose ? '<span style="color: var(--danger); font-weight: 700;">✓ Auto-Closes</span>' : '<span style="color: var(--neutral-400);">Manual / Renewable</span>'}
        </td>
        <td style="font-size: 0.8rem;">
          ${p.canPause ? '⏸ Pause ' : ''}
          ${p.canRenew ? '🔄 Renew ' : ''}
        </td>
      </tr>
    `).join('');
  }
}

// ==========================================
// ANALYTICS VIEW RENDERING
// ==========================================
function renderAnalyticsView() {
  if (!state.stats) return;
  const { mrr, totalRevenuePaid, totalOutstanding, activeCustomerCount } = state.stats;

  document.getElementById('lead-arr').textContent = `$${(mrr * 12).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('lead-active-cust').textContent = activeCustomerCount;
  document.getElementById('lead-collected').textContent = `$${totalRevenuePaid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('lead-unpaid').textContent = `$${totalOutstanding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ==========================================
// CREATE / EDIT SUBSCRIPTION MODAL & FORM
// ==========================================
function openCreateSubscriptionModal() {
  state.editingSubscriptionId = null;
  document.getElementById('sub-modal-title').textContent = 'Create New Subscription';
  document.getElementById('template-loader-row').style.display = 'block';
  document.getElementById('modal-template-select').value = '';
  document.getElementById('modal-sub-number').value = 'SUB-2026-XXXX (Auto-Generated)';
  document.getElementById('modal-sub-status').value = 'Draft';
  document.getElementById('modal-sub-status').disabled = false;
  document.getElementById('modal-sub-customer').value = '';
  document.getElementById('modal-sub-plan').value = '';
  document.getElementById('modal-sub-notes').value = '';

  const todayStr = new Date().toISOString().split('T')[0];
  document.getElementById('modal-sub-start-date').value = todayStr;
  
  // Set default expiry 30 days ahead
  const d = new Date();
  d.setDate(d.getDate() + 30);
  document.getElementById('modal-sub-expiry-date').value = d.toISOString().split('T')[0];
  document.getElementById('modal-sub-payment-terms').value = '30 Days';
  document.getElementById('modal-sub-autoclose').checked = false;

  // Clear line items and add default row
  const container = document.getElementById('modal-line-items-container');
  container.innerHTML = '';
  addLineItemRow();

  recalculateModalTotals();
  openModal('modal-sub-form');
}

function openEditSubscription(subId) {
  const sub = state.subscriptions.find(s => s.id === subId);
  if (!sub) return;

  state.editingSubscriptionId = sub.id;
  document.getElementById('sub-modal-title').textContent = `Edit Subscription ${sub.subscriptionNumber}`;
  document.getElementById('template-loader-row').style.display = 'none';
  document.getElementById('modal-sub-number').value = sub.subscriptionNumber;
  document.getElementById('modal-sub-status').value = sub.status;
  document.getElementById('modal-sub-status').disabled = true;
  document.getElementById('modal-sub-customer').value = sub.customerId;
  document.getElementById('modal-sub-plan').value = sub.planId;
  document.getElementById('modal-sub-start-date').value = sub.startDate;
  document.getElementById('modal-sub-expiry-date').value = sub.expiryDate;
  document.getElementById('modal-sub-payment-terms').value = sub.paymentTerms || '30 Days';
  document.getElementById('modal-sub-autoclose').checked = Boolean(sub.autoClose);
  document.getElementById('modal-sub-notes').value = sub.notes || '';

  // Populate lines
  const container = document.getElementById('modal-line-items-container');
  container.innerHTML = '';
  (sub.items || []).forEach(item => {
    addLineItemRow(item);
  });

  recalculateModalTotals();
  openModal('modal-sub-form');
}

function openEditCurrentSubscription() {
  if (state.currentSubscription) {
    openEditSubscription(state.currentSubscription.id);
  }
}

// Dynamic Line Items Builder
function addLineItemRow(data = null) {
  const container = document.getElementById('modal-line-items-container');
  const rowId = `item-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

  const row = document.createElement('div');
  row.className = 'line-item-row';
  row.id = rowId;

  // Product select options
  const prodOptions = state.products.map(p => `
    <option value="${p.id}" ${data && data.productId === p.id ? 'selected' : ''}>
      ${escapeHtml(p.name)}
    </option>
  `).join('');

  row.innerHTML = `
    <div>
      <select class="form-control item-product" onchange="onItemProductChanged('${rowId}')">
        <option value="">-- Choose Product --</option>
        ${prodOptions}
      </select>
    </div>
    <div>
      <select class="form-control item-variant" onchange="onItemVariantChanged('${rowId}')">
        <!-- populated based on product -->
      </select>
    </div>
    <div>
      <input type="number" class="form-control item-qty" min="1" value="${data ? data.quantity : 1}" oninput="recalculateModalTotals()" placeholder="Qty">
    </div>
    <div>
      <input type="number" class="form-control item-price" step="0.01" value="${data ? data.unitPrice : 0}" oninput="recalculateModalTotals()" placeholder="Unit Price">
    </div>
    <div>
      <select class="form-control item-tax" onchange="recalculateModalTotals()">
        <option value="10" ${data && data.taxRate === 10 ? 'selected' : ''}>Tax: 10%</option>
        <option value="15" ${data && data.taxRate === 15 ? 'selected' : ''}>Tax: 15%</option>
        <option value="18" ${data && data.taxRate === 18 ? 'selected' : ''}>Tax: 18%</option>
        <option value="0" ${data && data.taxRate === 0 ? 'selected' : ''}>Tax: 0%</option>
      </select>
    </div>
    <div style="text-align: center;">
      <button type="button" class="btn-icon-danger" onclick="removeLineItemRow('${rowId}')" title="Delete Line Item">
        🗑️
      </button>
    </div>
  `;

  container.appendChild(row);

  // If data provided or initial product selected, populate variants
  const initialProdId = data ? data.productId : (state.products[0] ? state.products[0].id : null);
  if (data && data.productId) {
    row.querySelector('.item-product').value = data.productId;
  } else if (!data && initialProdId) {
    row.querySelector('.item-product').value = initialProdId;
  }

  updateVariantsForProduct(rowId, data ? data.variant : null);

  if (!data && initialProdId) {
    onItemProductChanged(rowId);
  }

  recalculateModalTotals();
}

function removeLineItemRow(rowId) {
  const row = document.getElementById(rowId);
  if (row) {
    row.remove();
    recalculateModalTotals();
  }
}

function onItemProductChanged(rowId) {
  const row = document.getElementById(rowId);
  if (!row) return;

  const prodId = row.querySelector('.item-product').value;
  const prod = state.products.find(p => p.id === prodId);
  if (!prod) return;

  updateVariantsForProduct(rowId);

  // Update base price
  const priceInput = row.querySelector('.item-price');
  priceInput.value = prod.salesPrice.toFixed(2);

  // Update tax
  if (prod.taxRate !== undefined) {
    row.querySelector('.item-tax').value = String(prod.taxRate);
  }

  recalculateModalTotals();
}

function updateVariantsForProduct(rowId, selectedVariantName = null) {
  const row = document.getElementById(rowId);
  if (!row) return;

  const prodId = row.querySelector('.item-product').value;
  const prod = state.products.find(p => p.id === prodId);
  const variantSelect = row.querySelector('.item-variant');

  if (!prod || !prod.variants || prod.variants.length === 0) {
    variantSelect.innerHTML = '<option value="Standard Edition">Standard Edition</option>';
    return;
  }

  variantSelect.innerHTML = prod.variants.map(v => `
    <option value="${escapeHtml(v.name)}" data-delta="${v.priceDelta}" ${selectedVariantName === v.name ? 'selected' : ''}>
      ${escapeHtml(v.name)} (${v.priceDelta >= 0 ? '+' : ''}$${v.priceDelta})
    </option>
  `).join('');
}

function onItemVariantChanged(rowId) {
  const row = document.getElementById(rowId);
  if (!row) return;

  const prodId = row.querySelector('.item-product').value;
  const prod = state.products.find(p => p.id === prodId);
  if (!prod) return;

  const variantSelect = row.querySelector('.item-variant');
  const selectedOpt = variantSelect.selectedOptions[0];
  const delta = selectedOpt ? parseFloat(selectedOpt.getAttribute('data-delta') || 0) : 0;

  const priceInput = row.querySelector('.item-price');
  priceInput.value = (prod.salesPrice + delta).toFixed(2);

  recalculateModalTotals();
}

// Live Financial Recalculation
function recalculateModalTotals() {
  const rows = document.querySelectorAll('.line-item-row');
  let subtotal = 0;
  let taxTotal = 0;

  rows.forEach(row => {
    const qty = Math.max(1, parseInt(row.querySelector('.item-qty').value, 10) || 1);
    const price = parseFloat(row.querySelector('.item-price').value) || 0;
    const taxRate = parseFloat(row.querySelector('.item-tax').value) || 0;

    const lineSubtotal = qty * price;
    const lineTax = lineSubtotal * (taxRate / 100);

    subtotal += lineSubtotal;
    taxTotal += lineTax;
  });

  const grandTotal = subtotal + taxTotal;

  document.getElementById('modal-calc-subtotal').textContent = `$${subtotal.toFixed(2)}`;
  document.getElementById('modal-calc-tax').textContent = `$${taxTotal.toFixed(2)}`;
  document.getElementById('modal-calc-total').textContent = `$${grandTotal.toFixed(2)}`;
}

// Plan changed handler in modal
function onPlanSelectionChanged() {
  const planId = document.getElementById('modal-sub-plan').value;
  const plan = state.plans.find(p => p.id === planId);
  if (!plan) return;

  // Auto-set auto-close flag based on plan configuration
  document.getElementById('modal-sub-autoclose').checked = Boolean(plan.autoClose);

  calculateDefaultExpiryDate();
}

function calculateDefaultExpiryDate() {
  const planId = document.getElementById('modal-sub-plan').value;
  const plan = state.plans.find(p => p.id === planId);
  const startDateStr = document.getElementById('modal-sub-start-date').value;
  if (!startDateStr) return;

  const intervalDays = plan ? plan.intervalDays : 30;
  const d = new Date(startDateStr);
  d.setDate(d.getDate() + intervalDays);

  document.getElementById('modal-sub-expiry-date').value = d.toISOString().split('T')[0];
}

// Fast loader from template
function applyQuotationTemplate(templateId) {
  if (!templateId) return;
  const tpl = state.templates.find(t => t.id === templateId);
  if (!tpl) return;

  document.getElementById('modal-sub-plan').value = tpl.planId;
  document.getElementById('modal-sub-payment-terms').value = tpl.paymentTerms;
  onPlanSelectionChanged();

  // Clear line items and populate template items
  const container = document.getElementById('modal-line-items-container');
  container.innerHTML = '';

  tpl.items.forEach(item => {
    const prod = state.products.find(p => p.id === item.productId);
    addLineItemRow({
      productId: item.productId,
      productName: prod ? prod.name : 'Product',
      variant: item.variant,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
      taxRate: item.taxRate
    });
  });

  recalculateModalTotals();
  showToast(`Applied template: "${tpl.name}"`, 'info');
}

// Form Submission for Create or Edit
async function submitSubscriptionForm() {
  const customerId = document.getElementById('modal-sub-customer').value;
  const planId = document.getElementById('modal-sub-plan').value;
  const startDate = document.getElementById('modal-sub-start-date').value;
  const expiryDate = document.getElementById('modal-sub-expiry-date').value;
  const paymentTerms = document.getElementById('modal-sub-payment-terms').value;
  const autoClose = document.getElementById('modal-sub-autoclose').checked;
  const notes = document.getElementById('modal-sub-notes').value.trim();
  const status = document.getElementById('modal-sub-status').value;

  if (!customerId) return showToast('Please select a customer.', 'warning');
  if (!planId) return showToast('Please select a plan.', 'warning');
  if (!startDate) return showToast('Please select a start date.', 'warning');
  if (!expiryDate) return showToast('Please select an expiry date.', 'warning');

  // Collect line items
  const rows = document.querySelectorAll('.line-item-row');
  if (rows.length === 0) return showToast('Please add at least one product line item.', 'warning');

  const items = [];
  for (const row of rows) {
    const prodId = row.querySelector('.item-product').value;
    const prod = state.products.find(p => p.id === prodId);
    if (!prodId || !prod) {
      return showToast('Please select a valid product for all line rows.', 'warning');
    }

    const variant = row.querySelector('.item-variant').value;
    const qty = parseInt(row.querySelector('.item-qty').value, 10) || 1;
    const price = parseFloat(row.querySelector('.item-price').value) || 0;
    const taxRate = parseFloat(row.querySelector('.item-tax').value) || 0;

    items.push({
      productId: prodId,
      productName: prod.name,
      variant: variant,
      quantity: qty,
      unitPrice: price,
      taxRate: taxRate
    });
  }

  // Plan minimum quantity check
  const plan = state.plans.find(p => p.id === planId);
  const totalQty = items.reduce((sum, i) => sum + i.quantity, 0);
  if (plan && plan.minQuantity && totalQty < plan.minQuantity) {
    return showToast(`The selected plan "${plan.name}" requires a minimum total quantity of ${plan.minQuantity} seats/units.`, 'warning');
  }

  const payload = {
    customerId,
    planId,
    startDate,
    expiryDate,
    paymentTerms,
    autoClose,
    notes,
    items,
    status
  };

  try {
    if (state.editingSubscriptionId) {
      // Edit PUT
      const updated = await apiRequest(`/api/subscriptions/${state.editingSubscriptionId}`, 'PUT', payload);
      closeModal('modal-sub-form');
      showToast(`Subscription ${updated.subscriptionNumber} updated successfully!`, 'success');
      if (state.currentSubscription && state.currentSubscription.id === updated.id) {
        viewSubscriptionDetail(updated.id);
      }
    } else {
      // Create POST
      const created = await apiRequest('/api/subscriptions', 'POST', payload);
      closeModal('modal-sub-form');
      showToast(`Subscription ${created.subscriptionNumber} created successfully!`, 'success');
      viewSubscriptionDetail(created.id);
    }
    refreshData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Quick Add Customer
function openQuickAddCustomerModal() {
  document.getElementById('cust-modal-name').value = '';
  document.getElementById('cust-modal-contact').value = '';
  document.getElementById('cust-modal-email').value = '';
  document.getElementById('cust-modal-phone').value = '';
  document.getElementById('cust-modal-address').value = '';
  openModal('modal-quick-customer');
}

async function submitQuickCustomer() {
  const name = document.getElementById('cust-modal-name').value.trim();
  const contactName = document.getElementById('cust-modal-contact').value.trim();
  const email = document.getElementById('cust-modal-email').value.trim();
  const phone = document.getElementById('cust-modal-phone').value.trim();
  const address = document.getElementById('cust-modal-address').value.trim();

  if (!name || !email) {
    return showToast('Customer name and email are required.', 'warning');
  }

  try {
    const newCust = await apiRequest('/api/customers', 'POST', {
      name, contactName, email, phone, address
    });

    state.customers.push(newCust);
    populateDropdowns();
    document.getElementById('modal-sub-customer').value = newCust.id;

    closeModal('modal-quick-customer');
    showToast(`Customer "${newCust.name}" added and selected.`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// MODAL HELPERS & UTILITIES
// ==========================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠️',
    info: 'ℹ️'
  };

  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDateTime(isoStr) {
  if (!isoStr) return '-';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return isoStr;
  }
}
