/**
 * Details.js - Subscription Details Page Controller
 */

let currentSub = null;

// Modal Helpers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('active');
}

document.addEventListener('DOMContentLoaded', async () => {
  await initCurrentUser();
  await setupHeaderNavigation('subscriptions');

  const params = new URLSearchParams(window.location.search);
  const subId = params.get('id');

  if (!subId) {
    alert('No subscription ID specified in URL');
    window.location.href = '/';
    return;
  }

  await loadSubscriptionDetails(subId);
  setupDetailsListeners();
});

async function loadSubscriptionDetails(subId) {
  try {
    currentSub = await fetchSubscriptionById(subId);
    if (!currentSub) throw new Error('Subscription not found');

    renderHeader();
    renderStepper();
    renderLineItems();
    renderCustomer();
    renderSchedule();
    renderTimeline();
    renderActionButtons();
  } catch (err) {
    console.error('Error loading details:', err);
    alert(`Could not load subscription details: ${err.message}`);
    window.location.href = '/';
  }
}

function renderHeader() {
  document.getElementById('detSubNumber').textContent = currentSub.subscriptionNumber;
  document.getElementById('detStatusBadge').innerHTML = getStatusBadge(currentSub.status);

  const pausePill = document.getElementById('detPausePill');
  if (currentSub.status === 'Paused') {
    pausePill.style.display = 'inline-flex';
  } else {
    pausePill.style.display = 'none';
  }

  const custName = currentSub.customer ? `${currentSub.customer.name} (${currentSub.customer.company})` : 'Customer';
  const planName = currentSub.plan ? currentSub.plan.name : 'Custom Plan';
  document.getElementById('detSubSubtitle').textContent = `Customer: ${custName} • Plan: ${planName} • Created ${formatDate(currentSub.createdAt ? currentSub.createdAt.split('T')[0] : '')}`;

  // Role Indicator
  const roleInd = document.getElementById('roleIndicatorBadge');
  if (roleInd) {
    roleInd.innerHTML = `
      <span style="font-size:0.8rem; color:var(--text-secondary); margin-right:0.5rem;">Acting as:</span>
      <span class="role-badge ${currentUser.role}">${currentUser.name} (${currentUser.role})</span>
    `;
  }
}

function renderStepper() {
  const steps = ['Draft', 'Quotation', 'Confirmed', 'Active', 'Closed'];
  const statusIndex = steps.indexOf(currentSub.status);

  steps.forEach((step, idx) => {
    const el = document.getElementById(`step${step}`);
    if (!el) return;

    el.classList.remove('active', 'completed');

    if (currentSub.status === 'Paused') {
      // Paused is a branch of Active
      if (idx < 3) el.classList.add('completed');
      if (idx === 3) el.classList.add('active'); // show active paused
    } else {
      if (idx < statusIndex) {
        el.classList.add('completed');
      } else if (idx === statusIndex) {
        el.classList.add('active');
      }
    }
  });
}

function renderLineItems() {
  const tbody = document.getElementById('lineItemsTableBody');
  const items = [];

  // 1. Primary Plan Line Item
  const plan = currentSub.plan || { name: 'Standard Plan', code: 'PLAN-BASE' };
  const planQty = currentSub.quantity || 1;
  const planUnitPrice = currentSub.unitPrice || 0;
  const planTaxRate = currentSub.planTaxRate || 10.0;
  const planSubtotal = Math.round(planQty * planUnitPrice * 100) / 100;
  const planTax = currentSub.planTax || Math.round(planSubtotal * (planTaxRate / 100) * 100) / 100;
  const planTotal = Math.round((planSubtotal + planTax) * 100) / 100;

  items.push(`
    <tr style="background-color: #fafafa;">
      <td>
        <strong style="color:var(--text-main);">${plan.name} (Base Subscription Plan)</strong>
        <div style="font-size:0.75rem; color:var(--text-muted);">${plan.description || ''} • Code: ${plan.code || ''}</div>
      </td>
      <td style="text-align: center;">${planQty}</td>
      <td style="text-align: right;">${formatCurrency(planUnitPrice, currentSub.currency)}</td>
      <td style="text-align: right;">${planTaxRate}%</td>
      <td style="text-align: right;">${formatCurrency(planTax, currentSub.currency)}</td>
      <td style="text-align: right; font-weight: 700;">${formatCurrency(planTotal, currentSub.currency)}</td>
    </tr>
  `);

  // 2. Selected Products & Add-ons
  (currentSub.products || []).forEach(p => {
    items.push(`
      <tr>
        <td>
          <div style="font-weight: 600;">${p.productName}</div>
          <div style="font-size:0.75rem; color:var(--text-muted); font-family:monospace;">SKU: ${p.sku}</div>
        </td>
        <td style="text-align: center;">${p.quantity}</td>
        <td style="text-align: right;">${formatCurrency(p.unitPrice, currentSub.currency)}</td>
        <td style="text-align: right;">${p.taxRate}%</td>
        <td style="text-align: right;">${formatCurrency(p.lineTax, currentSub.currency)}</td>
        <td style="text-align: right; font-weight: 700;">${formatCurrency(p.lineTotal, currentSub.currency)}</td>
      </tr>
    `);
  });

  tbody.innerHTML = items.join('');

  // Totals breakdown
  document.getElementById('detSubtotal').textContent = formatCurrency(currentSub.subtotal, currentSub.currency);
  document.getElementById('detTax').textContent = formatCurrency(currentSub.tax, currentSub.currency);
  document.getElementById('detTotalAmount').textContent = formatCurrency(currentSub.totalAmount, currentSub.currency);

  const discountRow = document.getElementById('discountRow');
  if (currentSub.discount && currentSub.discount > 0) {
    discountRow.style.display = 'flex';
    document.getElementById('detDiscount').textContent = `${currentSub.discount}% Applied`;
  } else {
    discountRow.style.display = 'none';
  }

  if (currentSub.plan) {
    document.getElementById('detBillingCycle').textContent = `Cycle: ${currentSub.plan.billingCycle || 'Monthly'}`;
  }
}

function renderCustomer() {
  const cust = currentSub.customer;
  if (!cust) return;

  document.getElementById('detCustName').textContent = cust.name || 'N/A';
  document.getElementById('detCustCompany').textContent = cust.company || 'N/A';
  document.getElementById('detCustEmail').textContent = cust.email || 'N/A';
  document.getElementById('detCustPhone').textContent = cust.phone || 'N/A';
  document.getElementById('detCustAddress').textContent = cust.address || 'N/A';
  document.getElementById('detCustTaxId').textContent = cust.taxId || 'N/A';
}

function renderSchedule() {
  document.getElementById('detStartDate').textContent = formatDate(currentSub.startDate);
  document.getElementById('detExpiryDate').textContent = formatDate(currentSub.expiryDate);
  document.getElementById('detPaymentTerms').textContent = currentSub.paymentTerms || 'Net 30';
  document.getElementById('detCurrency').textContent = `${currentSub.currency || 'USD'} ($)`;
  document.getElementById('detPlanCode').textContent = currentSub.plan ? currentSub.plan.code : 'CUSTOM';

  // Expiry Countdown & Status
  const today = new Date().toISOString().split('T')[0];
  const isPast = currentSub.expiryDate && currentSub.expiryDate < today;
  const countdownEl = document.getElementById('detExpiryCountdown');

  if (currentSub.status === 'Closed') {
    countdownEl.innerHTML = `<span class="badge badge-closed">Closed / Terminated</span>`;
  } else if (isPast) {
    countdownEl.innerHTML = `<span class="badge" style="background:#fee2e2; color:#b91c1c; border:1px solid #f87171;">⚠️ Past Expiry (${formatDate(currentSub.expiryDate)})</span>`;
  } else if (currentSub.expiryDate) {
    const daysLeft = Math.ceil((new Date(currentSub.expiryDate) - new Date()) / (1000 * 60 * 60 * 24));
    countdownEl.innerHTML = `<span class="badge badge-active">Active • ${daysLeft} days remaining</span>`;
  }

  // Auto-close indicator
  const autoCloseBadge = document.getElementById('detAutoCloseBadge');
  if (currentSub.autoCloseOnExpiry) {
    autoCloseBadge.innerHTML = `<span style="color:#059669;">✓ Enabled (Will auto-close on expiry)</span>`;
  } else {
    autoCloseBadge.innerHTML = `<span style="color:#dc2626;">✗ Disabled (Manual review required)</span>`;
  }

  // Renewal count
  document.getElementById('detRenewalCounter').textContent = `Renewals to date: ${currentSub.renewalCount || 0}`;

  // Notes
  if (currentSub.notes) {
    document.getElementById('detNotes').textContent = currentSub.notes;
  }

  // Reason banner for paused or closed
  const notesCard = document.getElementById('cardStatusNotes');
  const notesTitle = document.getElementById('statusNotesTitle');
  const notesBody = document.getElementById('statusNotesBody');

  if (currentSub.status === 'Paused' && currentSub.pauseReason) {
    notesCard.style.display = 'block';
    notesCard.style.borderLeft = '4px solid #f59e0b';
    notesTitle.textContent = '⏸️ Subscription Paused Notice';
    notesBody.innerHTML = `<strong>Reason:</strong> ${currentSub.pauseReason}<br><small style="color:var(--text-muted)">Paused at: ${formatDate(currentSub.pausedAt ? currentSub.pausedAt.split('T')[0] : '')}</small>`;
  } else if (currentSub.status === 'Closed' && currentSub.closedReason) {
    notesCard.style.display = 'block';
    notesCard.style.borderLeft = '4px solid #dc2626';
    notesTitle.textContent = '🔒 Subscription Closed Notice';
    notesBody.innerHTML = `<strong>Closure Reason:</strong> ${currentSub.closedReason}<br><small style="color:var(--text-muted)">Closed at: ${formatDate(currentSub.closedAt ? currentSub.closedAt.split('T')[0] : '')}</small>`;
  } else {
    notesCard.style.display = 'none';
  }
}

function renderTimeline() {
  const container = document.getElementById('auditTimeline');
  const history = currentSub.history || [];

  if (history.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem;">No activity recorded yet.</div>`;
    return;
  }

  container.innerHTML = history.slice().reverse().map(item => {
    const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleString() : '';
    return `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-title">${item.action || 'State Update'}</div>
        <div class="timeline-meta">${timeStr} • By <strong>${item.performedBy || 'System'}</strong></div>
        ${item.notes ? `<div class="timeline-notes">${item.notes}</div>` : ''}
      </div>
    `;
  }).join('');
}

function renderActionButtons() {
  const container = document.getElementById('lifecycleActionsContainer');
  const canManage = currentUser.role === 'admin' || currentUser.role === 'staff';
  let buttons = [];

  // Print button available for all
  buttons.push(`
    <button class="btn btn-secondary" onclick="window.print()" title="Print Quotation / Invoice">
      <span>🖨️</span> Print / PDF
    </button>
  `);

  if (canManage) {
    // Edit (if not closed)
    if (currentSub.status !== 'Closed') {
      buttons.push(`
        <a href="/subscription-form.html?id=${currentSub.id}" class="btn btn-secondary">
          <span>✏️</span> Edit
        </a>
      `);
    }

    // Status-specific workflow actions
    if (currentSub.status === 'Draft') {
      buttons.push(`
        <button class="btn btn-primary" onclick="handleTransition('Quotation', 'Generated and issued formal quotation')">
          <span>📤</span> Send Quotation
        </button>
        <button class="btn btn-danger" onclick="handleCancelPrompt()">
          <span>✕</span> Discard
        </button>
      `);
    } else if (currentSub.status === 'Quotation') {
      buttons.push(`
        <button class="btn btn-success" onclick="handleTransition('Confirmed', 'Quotation approved and order confirmed')">
          <span>✓</span> Confirm Order
        </button>
        <button class="btn btn-secondary" onclick="handleTransition('Draft', 'Revised quote returned to draft')">
          <span>↩</span> Revise to Draft
        </button>
        <button class="btn btn-danger" onclick="handleCancelPrompt()">
          <span>✕</span> Reject Quote
        </button>
      `);
    } else if (currentSub.status === 'Confirmed') {
      buttons.push(`
        <button class="btn btn-primary" onclick="handleTransition('Active', 'Payment verified and subscription activated')">
          <span>⚡</span> Activate Subscription
        </button>
        <button class="btn btn-secondary" onclick="handleTransition('Draft', 'Returned to draft for amendments')">
          <span>↩</span> Reopen Draft
        </button>
        <button class="btn btn-danger" onclick="handleCancelPrompt()">
          <span>✕</span> Cancel Order
        </button>
      `);
    } else if (currentSub.status === 'Active') {
      buttons.push(`
        <button class="btn btn-warning" onclick="openModal('detailsPauseModal')">
          <span>⏸️</span> Pause Subscription
        </button>
        <button class="btn btn-success" onclick="openModal('detailsRenewModal')">
          <span>🔄</span> Renew Subscription
        </button>
        <button class="btn btn-danger" onclick="handleCancelPrompt()">
          <span>✕</span> Cancel Subscription
        </button>
      `);
    } else if (currentSub.status === 'Paused') {
      buttons.push(`
        <button class="btn btn-success" onclick="handleResume()">
          <span>▶️</span> Resume Subscription
        </button>
        <button class="btn btn-danger" onclick="handleCancelPrompt()">
          <span>✕</span> Cancel Subscription
        </button>
      `);
    } else if (currentSub.status === 'Closed') {
      buttons.push(`
        <button class="btn btn-success" onclick="openModal('detailsRenewModal')">
          <span>🔄</span> Reactivate / Renew
        </button>
        <a href="/subscription-form.html?cloneId=${currentSub.id}" class="btn btn-outline">
          <span>📋</span> Clone as New Draft
        </a>
      `);
    }
  }

  container.innerHTML = buttons.join('');
}

// Action Handlers
async function handleTransition(toStatus, reason) {
  try {
    await transitionStatus(currentSub.id, toStatus, reason);
    showToast(`Status updated to ${toStatus}`, 'success');
    await loadSubscriptionDetails(currentSub.id);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleResume() {
  if (!confirm('Resume this paused subscription to Active?')) return;
  try {
    await resumeSubscription(currentSub.id);
    showToast('Subscription resumed to Active', 'success');
    await loadSubscriptionDetails(currentSub.id);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function handleCancelPrompt() {
  openModal('detailsCancelModal');
}

function setupDetailsListeners() {
  // Confirm Pause in Modal
  const btnPause = document.getElementById('btnDetailsConfirmPause');
  if (btnPause) {
    btnPause.addEventListener('click', async () => {
      const reason = document.getElementById('detailsPauseReason').value.trim();
      if (!reason) {
        alert('Please enter a pause reason');
        return;
      }
      try {
        await pauseSubscription(currentSub.id, reason);
        showToast('Subscription paused', 'success');
        closeModal('detailsPauseModal');
        await loadSubscriptionDetails(currentSub.id);
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Confirm Renew in Modal
  const btnRenew = document.getElementById('btnDetailsConfirmRenew');
  if (btnRenew) {
    btnRenew.addEventListener('click', async () => {
      const duration = parseInt(document.getElementById('detailsRenewDuration').value, 10);
      const notes = document.getElementById('detailsRenewNotes').value.trim();
      try {
        await renewSubscription(currentSub.id, duration, notes);
        showToast('Subscription renewed successfully', 'success');
        closeModal('detailsRenewModal');
        await loadSubscriptionDetails(currentSub.id);
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Confirm Cancel in Modal
  const btnCancel = document.getElementById('btnDetailsConfirmCancel');
  if (btnCancel) {
    btnCancel.addEventListener('click', async () => {
      const reason = document.getElementById('detailsCancelReason').value.trim();
      if (!reason) {
        alert('Please enter a cancellation reason');
        return;
      }
      try {
        await cancelSubscription(currentSub.id, reason);
        showToast('Subscription cancelled (Closed)', 'success');
        closeModal('detailsCancelModal');
        await loadSubscriptionDetails(currentSub.id);
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }
}
