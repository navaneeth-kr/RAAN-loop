/**
 * Form.js - Subscription Creation & Editing Controller
 */

let allCustomers = [];
let allPlans = [];
let allProducts = [];
let editingSubscriptionId = null;
let currentProductRows = [];

document.addEventListener('DOMContentLoaded', async () => {
  await initCurrentUser();
  await setupHeaderNavigation('create');

  // Enforce RBAC: Customers cannot manage subscriptions
  if (currentUser.role === 'customer') {
    alert('Access Denied: Only authorized staff and administrators can create or edit subscriptions.');
    window.location.href = '/';
    return;
  }

  await loadMetadata();

  const params = new URLSearchParams(window.location.search);
  const editId = params.get('id');
  const cloneId = params.get('cloneId');

  if (editId) {
    editingSubscriptionId = editId;
    await setupEditMode(editId);
  } else if (cloneId) {
    await setupCloneMode(cloneId);
  } else {
    setupNewMode();
  }

  setupFormEventHandlers();
  calculateLiveTotals();
});

// Load reference metadata from API
async function loadMetadata() {
  try {
    [allCustomers, allPlans, allProducts] = await Promise.all([
      fetchCustomers(),
      fetchPlans(),
      fetchProducts()
    ]);

    // Populate Customer Dropdown
    const custSelect = document.getElementById('customerSelect');
    allCustomers.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.name} - ${c.company}`;
      custSelect.appendChild(opt);
    });

    // Populate Plan Dropdown
    const planSelect = document.getElementById('planSelect');
    allPlans.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.name} ($${p.basePrice.toFixed(2)} / ${p.billingCycle})`;
      planSelect.appendChild(opt);
    });
  } catch (err) {
    console.error('Error loading metadata:', err);
    showToast('Failed to load customers and plans catalog', 'error');
  }
}

// Setup New Subscription default values
function setupNewMode() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('startDateInput').value = today;

  // Default expiry 30 days
  const expiry = new Date();
  expiry.setDate(expiry.getDate() + 30);
  document.getElementById('expiryDateInput').value = expiry.toISOString().split('T')[0];

  // Pick first plan as default
  if (allPlans.length > 0) {
    const defaultPlan = allPlans[0];
    document.getElementById('planSelect').value = defaultPlan.id;
    onPlanSelected(defaultPlan.id);
  }
}

// Setup Edit Mode
async function setupEditMode(subId) {
  try {
    const sub = await fetchSubscriptionById(subId);
    if (!sub) throw new Error('Subscription not found');

    document.getElementById('formPageTitle').textContent = `Edit Subscription: ${sub.subscriptionNumber}`;
    document.getElementById('formPageSubtitle').textContent = `Updating subscription record • Status: ${sub.status}`;
    document.getElementById('btnSubmitForm').innerHTML = '<span>💾</span> Update Subscription';

    document.getElementById('customerSelect').value = sub.customerId;
    onCustomerSelected(sub.customerId);

    document.getElementById('planSelect').value = sub.planId;
    onPlanSelected(sub.planId, false);

    document.getElementById('planQuantity').value = sub.quantity || 1;
    document.getElementById('planUnitPrice').value = sub.unitPrice || 0;

    document.getElementById('startDateInput').value = sub.startDate;
    document.getElementById('expiryDateInput').value = sub.expiryDate;
    document.getElementById('paymentTermsSelect').value = sub.paymentTerms || 'Net 30';

    const statusSelect = document.getElementById('initialStatusSelect');
    statusSelect.innerHTML = `<option value="${sub.status}" selected>${sub.status} (Current)</option>`;
    statusSelect.disabled = true;

    document.getElementById('autoCloseCheckbox').checked = Boolean(sub.autoCloseOnExpiry);
    document.getElementById('notesTextarea').value = sub.notes || '';

    // Load existing line items
    currentProductRows = (sub.products || []).map(p => ({
      productId: p.productId,
      quantity: p.quantity,
      unitPrice: p.unitPrice,
      taxRate: p.taxRate,
      sku: p.sku,
      productName: p.productName
    }));

    renderProductRows();
    calculateLiveTotals();
  } catch (err) {
    alert(`Failed to load subscription: ${err.message}`);
    window.location.href = '/';
  }
}

// Setup Clone Mode
async function setupCloneMode(cloneId) {
  try {
    const sub = await fetchSubscriptionById(cloneId);
    document.getElementById('formPageTitle').textContent = `Clone Subscription as New Draft`;
    document.getElementById('formPageSubtitle').textContent = `Cloned configuration from ${sub.subscriptionNumber}`;

    document.getElementById('customerSelect').value = sub.customerId;
    onCustomerSelected(sub.customerId);

    document.getElementById('planSelect').value = sub.planId;
    onPlanSelected(sub.planId, false);

    document.getElementById('planQuantity').value = sub.quantity || 1;
    document.getElementById('planUnitPrice').value = sub.unitPrice || 0;

    setupNewMode(); // Reset dates to fresh terms

    currentProductRows = (sub.products || []).map(p => ({
      productId: p.productId,
      quantity: p.quantity,
      unitPrice: p.unitPrice,
      taxRate: p.taxRate,
      sku: p.sku,
      productName: p.productName
    }));

    renderProductRows();
    calculateLiveTotals();
  } catch (err) {
    console.error('Clone error:', err);
  }
}

// Handlers for Selection Changes
function onCustomerSelected(custId) {
  const cust = allCustomers.find(c => c.id === custId);
  const box = document.getElementById('customerPreviewBox');
  if (cust) {
    box.style.display = 'block';
    document.getElementById('prevCustCompany').textContent = cust.company || 'N/A';
    document.getElementById('prevCustEmail').textContent = cust.email || 'N/A';
    document.getElementById('prevCustTaxId').textContent = cust.taxId || 'N/A';
    document.getElementById('prevCustAddress').textContent = cust.address || 'N/A';
  } else {
    box.style.display = 'none';
  }
}

function onPlanSelected(planId, updateDates = true) {
  const plan = allPlans.find(p => p.id === planId);
  const descBox = document.getElementById('planDescriptionBox');
  if (plan) {
    descBox.style.display = 'block';
    document.getElementById('planDescText').textContent = `${plan.description} (Billing: ${plan.billingCycle})`;
    document.getElementById('planUnitPrice').value = plan.basePrice.toFixed(2);

    if (updateDates && !editingSubscriptionId) {
      const days = plan.durationDays || 30;
      setPresetExpiry(days);
    }
  } else {
    descBox.style.display = 'none';
  }
  calculateLiveTotals();
}

function setPresetExpiry(days) {
  const startVal = document.getElementById('startDateInput').value;
  const start = startVal ? new Date(startVal) : new Date();
  start.setDate(start.getDate() + days);
  document.getElementById('expiryDateInput').value = start.toISOString().split('T')[0];
}

// Product Line Items Builder
function addProductRow(productId = '') {
  let prod = allProducts.find(p => p.id === productId) || allProducts[0];
  if (!prod) return;

  currentProductRows.push({
    productId: prod.id,
    quantity: 1,
    unitPrice: prod.unitPrice,
    taxRate: prod.taxRate,
    sku: prod.sku,
    productName: prod.name
  });

  renderProductRows();
  calculateLiveTotals();
}

function removeProductRow(index) {
  currentProductRows.splice(index, 1);
  renderProductRows();
  calculateLiveTotals();
}

function renderProductRows() {
  const tbody = document.getElementById('productRowsBody');
  const notice = document.getElementById('noProductsNotice');

  if (currentProductRows.length === 0) {
    tbody.innerHTML = '';
    notice.style.display = 'block';
    return;
  }

  notice.style.display = 'none';
  tbody.innerHTML = currentProductRows.map((row, idx) => {
    const lineSubtotal = (row.quantity * row.unitPrice);
    const lineTax = lineSubtotal * (row.taxRate / 100);
    const lineTotal = lineSubtotal + lineTax;

    return `
      <tr>
        <td>
          <select class="form-control" style="font-size:0.85rem;" onchange="onRowProductChange(${idx}, this.value)">
            ${allProducts.map(p => `
              <option value="${p.id}" ${p.id === row.productId ? 'selected' : ''}>
                ${p.name} ($${p.unitPrice.toFixed(2)})
              </option>
            `).join('')}
          </select>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px; font-family:monospace;">SKU: ${row.sku || ''}</div>
        </td>
        <td>
          <input type="number" class="form-control" style="font-size:0.85rem; text-align:center;" min="1" step="1" value="${row.quantity}" oninput="onRowQtyChange(${idx}, this.value)">
        </td>
        <td>
          <input type="number" class="form-control" style="font-size:0.85rem; text-align:right;" min="0" step="0.01" value="${row.unitPrice.toFixed(2)}" oninput="onRowPriceChange(${idx}, this.value)">
        </td>
        <td style="text-align:right; font-size:0.85rem; color:var(--text-secondary);">
          ${row.taxRate}%
        </td>
        <td style="text-align:right; font-weight:700; font-size:0.9rem;">
          $${lineTotal.toFixed(2)}
        </td>
        <td style="text-align:center;">
          <button type="button" style="background:none; border:none; color:#dc2626; cursor:pointer; font-size:1.1rem;" onclick="removeProductRow(${idx})" title="Remove line item">&times;</button>
        </td>
      </tr>
    `;
  }).join('');
}

window.onRowProductChange = function(index, productId) {
  const prod = allProducts.find(p => p.id === productId);
  if (!prod) return;
  currentProductRows[index].productId = prod.id;
  currentProductRows[index].productName = prod.name;
  currentProductRows[index].sku = prod.sku;
  currentProductRows[index].unitPrice = prod.unitPrice;
  currentProductRows[index].taxRate = prod.taxRate;
  renderProductRows();
  calculateLiveTotals();
};

window.onRowQtyChange = function(index, val) {
  currentProductRows[index].quantity = Math.max(1, parseInt(val, 10) || 1);
  renderProductRows();
  calculateLiveTotals();
};

window.onRowPriceChange = function(index, val) {
  currentProductRows[index].unitPrice = Math.max(0, parseFloat(val) || 0);
  calculateLiveTotals();
};

// Live Calculations
function calculateLiveTotals() {
  const planQty = Math.max(1, parseInt(document.getElementById('planQuantity').value, 10) || 1);
  const planPrice = Math.max(0, parseFloat(document.getElementById('planUnitPrice').value) || 0);

  const planSubtotal = planQty * planPrice;
  const planTax = planSubtotal * 0.10; // 10% plan standard tax

  let addonsSubtotal = 0;
  let addonsTax = 0;

  currentProductRows.forEach(row => {
    const rowSubtotal = row.quantity * row.unitPrice;
    const rowTax = rowSubtotal * (row.taxRate / 100);
    addonsSubtotal += rowSubtotal;
    addonsTax += rowTax;
  });

  const netSubtotal = planSubtotal + addonsSubtotal;
  const totalTax = planTax + addonsTax;
  const grandTotal = netSubtotal + totalTax;

  document.getElementById('calcPlanSubtotal').textContent = formatCurrency(planSubtotal);
  document.getElementById('calcAddonsSubtotal').textContent = formatCurrency(addonsSubtotal);
  document.getElementById('calcNetSubtotal').textContent = formatCurrency(netSubtotal);
  document.getElementById('calcTotalTax').textContent = formatCurrency(totalTax);
  document.getElementById('calcGrandTotal').textContent = formatCurrency(grandTotal);
}

// Form Event Listeners & Submit
function setupFormEventHandlers() {
  document.getElementById('customerSelect').addEventListener('change', (e) => {
    onCustomerSelected(e.target.value);
  });

  document.getElementById('planSelect').addEventListener('change', (e) => {
    onPlanSelected(e.target.value);
  });

  document.getElementById('planQuantity').addEventListener('input', calculateLiveTotals);
  document.getElementById('planUnitPrice').addEventListener('input', calculateLiveTotals);

  document.getElementById('btnAddProductRow').addEventListener('click', () => {
    addProductRow();
  });

  document.getElementById('subscriptionForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const customerId = document.getElementById('customerSelect').value;
    const planId = document.getElementById('planSelect').value;
    const quantity = parseInt(document.getElementById('planQuantity').value, 10) || 1;
    const unitPrice = parseFloat(document.getElementById('planUnitPrice').value) || 0;
    const startDate = document.getElementById('startDateInput').value;
    const expiryDate = document.getElementById('expiryDateInput').value;
    const paymentTerms = document.getElementById('paymentTermsSelect').value;
    const autoCloseOnExpiry = document.getElementById('autoCloseCheckbox').checked;
    const notes = document.getElementById('notesTextarea').value.trim();
    const status = document.getElementById('initialStatusSelect').value;

    if (!customerId) {
      alert('Please select a customer');
      return;
    }
    if (!planId) {
      alert('Please select a plan tier');
      return;
    }
    if (!startDate || !expiryDate) {
      alert('Start date and expiry date are required');
      return;
    }
    if (expiryDate <= startDate) {
      if (!confirm('Warning: Expiry date is on or before the start date. Do you want to proceed?')) {
        return;
      }
    }

    const payload = {
      customerId,
      planId,
      quantity,
      unitPrice,
      startDate,
      expiryDate,
      paymentTerms,
      autoCloseOnExpiry,
      notes,
      products: currentProductRows
    };

    if (!editingSubscriptionId) {
      payload.status = status;
    }

    const submitBtn = document.getElementById('btnSubmitForm');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>⏳</span> Saving...';

    try {
      let result;
      if (editingSubscriptionId) {
        result = await updateSubscription(editingSubscriptionId, payload);
        showToast('Subscription updated successfully!', 'success');
        setTimeout(() => {
          window.location.href = `/subscription-details.html?id=${editingSubscriptionId}`;
        }, 600);
      } else {
        result = await createSubscription(payload);
        showToast(`Subscription ${result.subscription.subscriptionNumber} created!`, 'success');
        setTimeout(() => {
          window.location.href = `/subscription-details.html?id=${result.subscription.id}`;
        }, 600);
      }
    } catch (err) {
      showToast(err.message, 'error');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>💾</span> Save Subscription';
    }
  });
}
