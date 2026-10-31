const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, 'database.json');

// Helper to safely read database
function getDb() {
  try {
    if (fs.existsSync(DB_PATH)) {
      const raw = fs.readFileSync(DB_PATH, 'utf8');
      return JSON.parse(raw);
    }
  } catch (err) {
    console.error('Error reading database:', err);
  }
  return {
    systemSettings: {
      autoCloseExpiredCronEnabled: true,
      autoCloseCheckIntervalSeconds: 60,
      defaultPaymentTerms: 'Net 30',
      defaultTaxRate: 10.0,
      currencySymbol: '$',
      currencyCode: 'USD'
    },
    users: [],
    customers: [],
    plans: [],
    products: [],
    subscriptions: []
  };
}

// Helper to safely write database
function saveDb(data) {
  try {
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    console.error('Error writing database:', err);
    throw err;
  }
}

// Round to 2 decimal places safely
function round2(num) {
  return Math.round((Number(num) + Number.EPSILON) * 100) / 100;
}

// Generate unique subscription number: SUB-YYYYMM-XXXXX
function generateUniqueSubscriptionNumber(db) {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const prefix = `SUB-${year}${month}-`;

  let maxSeq = 100;
  for (const sub of db.subscriptions) {
    if (sub.subscriptionNumber && sub.subscriptionNumber.startsWith(prefix)) {
      const parts = sub.subscriptionNumber.split('-');
      if (parts.length >= 3) {
        const num = parseInt(parts[2], 10);
        if (!isNaN(num) && num > maxSeq) {
          maxSeq = num;
        }
      }
    }
  }

  let nextSeq = maxSeq + 1;
  let candidate = `${prefix}${String(nextSeq).padStart(5, '0')}`;
  while (db.subscriptions.some(s => s.subscriptionNumber === candidate)) {
    nextSeq++;
    candidate = `${prefix}${String(nextSeq).padStart(5, '0')}`;
  }
  return candidate;
}

// Calculation engine for amounts and taxes
function calculateSubscriptionFinancials(plan, products = [], customQuantity = 1, customUnitPrice = null, customDiscount = 0) {
  const quantity = Math.max(1, parseInt(customQuantity, 10) || 1);
  const unitPrice = customUnitPrice !== null && customUnitPrice !== undefined ? Number(customUnitPrice) : (plan ? Number(plan.basePrice) : 0);
  const discountPercent = Math.max(0, Math.min(100, Number(customDiscount) || 0));

  // Plan base line item calculation
  const planTaxRate = 10.0; // standard 10% on plan
  const planSubtotal = round2((quantity * unitPrice) * (1 - discountPercent / 100));
  const planTax = round2(planSubtotal * (planTaxRate / 100));
  const planTotal = round2(planSubtotal + planTax);

  let subtotal = planSubtotal;
  let tax = planTax;

  const calculatedProducts = (products || []).map(item => {
    const itemQty = Math.max(1, parseInt(item.quantity, 10) || 1);
    const itemPrice = Math.max(0, Number(item.unitPrice) || 0);
    const itemDisc = Math.max(0, Math.min(100, Number(item.discount) || 0));
    const itemTaxRate = Number(item.taxRate) >= 0 ? Number(item.taxRate) : 10.0;

    const lineSubtotal = round2((itemQty * itemPrice) * (1 - itemDisc / 100));
    const lineTax = round2(lineSubtotal * (itemTaxRate / 100));
    const lineTotal = round2(lineSubtotal + lineTax);

    subtotal = round2(subtotal + lineSubtotal);
    tax = round2(tax + lineTax);

    return {
      productId: item.productId,
      productName: item.productName || 'Product Add-on',
      sku: item.sku || 'SKU-CUSTOM',
      quantity: itemQty,
      unitPrice: itemPrice,
      discount: itemDisc,
      taxRate: itemTaxRate,
      lineSubtotal,
      lineTax,
      lineTotal
    };
  });

  const totalAmount = round2(subtotal + tax);

  return {
    quantity,
    unitPrice,
    planTaxRate,
    planTax,
    products: calculatedProducts,
    subtotal,
    tax,
    discount: discountPercent,
    totalAmount
  };
}

// Strict status transitions
const VALID_TRANSITIONS = {
  'Draft': ['Quotation', 'Closed'],
  'Quotation': ['Draft', 'Confirmed', 'Closed'],
  'Confirmed': ['Draft', 'Active', 'Closed'],
  'Active': ['Paused', 'Closed', 'Active'], // Active -> Active allowed for renewal
  'Paused': ['Active', 'Closed'],
  'Closed': ['Draft', 'Active'] // reactivate or renew closed subscription
};

function isValidTransition(fromStatus, toStatus) {
  if (fromStatus === toStatus && toStatus !== 'Active') return false;
  const allowed = VALID_TRANSITIONS[fromStatus] || [];
  return allowed.includes(toStatus);
}

// RBAC Permissions
function canManageSubscriptions(user) {
  if (!user) return false;
  return user.role === 'admin' || user.role === 'staff';
}

function canViewSubscription(subscription, user) {
  if (!user) return false;
  if (user.role === 'admin' || user.role === 'staff') return true;
  if (user.role === 'customer') {
    return subscription.customerId === user.customerId;
  }
  return false;
}

// Get enriched subscription with plan and customer objects attached
function enrichSubscription(subscription, db) {
  if (!subscription) return null;
  const customer = db.customers.find(c => c.id === subscription.customerId) || null;
  const plan = db.plans.find(p => p.id === subscription.planId) || null;
  return {
    ...subscription,
    customer,
    plan
  };
}

// Format today's date in YYYY-MM-DD
function getTodayString() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

// Public Database API
module.exports = {
  getDb,
  saveDb,
  round2,
  generateUniqueSubscriptionNumber,
  calculateSubscriptionFinancials,
  VALID_TRANSITIONS,
  isValidTransition,
  canManageSubscriptions,
  canViewSubscription,
  getTodayString,

  // Users
  getUsers() {
    const db = getDb();
    return db.users;
  },

  getUserById(id) {
    const db = getDb();
    return db.users.find(u => u.id === id) || null;
  },

  // Customers
  getCustomers() {
    const db = getDb();
    return db.customers;
  },

  getCustomerById(id) {
    const db = getDb();
    return db.customers.find(c => c.id === id) || null;
  },

  // Plans
  getPlans() {
    const db = getDb();
    return db.plans;
  },

  getPlanById(id) {
    const db = getDb();
    return db.plans.find(p => p.id === id) || null;
  },

  // Products
  getProducts() {
    const db = getDb();
    return db.products;
  },

  getProductById(id) {
    const db = getDb();
    return db.products.find(p => p.id === id) || null;
  },

  // Settings
  getSystemSettings() {
    const db = getDb();
    return db.systemSettings;
  },

  updateSystemSettings(newSettings, user) {
    if (!user || user.role !== 'admin') {
      throw new Error('Only administrators can modify system settings');
    }
    const db = getDb();
    db.systemSettings = { ...db.systemSettings, ...newSettings };
    saveDb(db);
    return db.systemSettings;
  },

  // Subscriptions - Query List with RBAC & Filtering
  getSubscriptions(filters = {}, user) {
    const db = getDb();
    let results = db.subscriptions;

    // RBAC: Customers only see their own subscriptions
    if (user && user.role === 'customer') {
      results = results.filter(s => s.customerId === user.customerId);
    }

    // Status filter
    if (filters.status && filters.status !== 'all') {
      results = results.filter(s => s.status.toLowerCase() === filters.status.toLowerCase());
    }

    // Plan filter
    if (filters.planId && filters.planId !== 'all') {
      results = results.filter(s => s.planId === filters.planId);
    }

    // Customer filter (for staff/admin)
    if (filters.customerId && filters.customerId !== 'all') {
      results = results.filter(s => s.customerId === filters.customerId);
    }

    // Payment terms filter
    if (filters.paymentTerms && filters.paymentTerms !== 'all') {
      results = results.filter(s => s.paymentTerms === filters.paymentTerms);
    }

    // Expiry state filter
    const today = getTodayString();
    if (filters.expiryState) {
      if (filters.expiryState === 'expired') {
        results = results.filter(s => s.expiryDate < today);
      } else if (filters.expiryState === 'active_unexpired') {
        results = results.filter(s => s.expiryDate >= today && (s.status === 'Active' || s.status === 'Confirmed'));
      } else if (filters.expiryState === 'expiring_soon') {
        // Expiring in next 30 days
        const target = new Date();
        target.setDate(target.getDate() + 30);
        const targetStr = target.toISOString().split('T')[0];
        results = results.filter(s => s.expiryDate >= today && s.expiryDate <= targetStr);
      }
    }

    // Search query: subscription number, customer name/company, plan name, product name
    if (filters.search && filters.search.trim()) {
      const q = filters.search.trim().toLowerCase();
      results = results.filter(s => {
        const enriched = enrichSubscription(s, db);
        const matchNum = s.subscriptionNumber && s.subscriptionNumber.toLowerCase().includes(q);
        const matchCust = enriched.customer && (
          enriched.customer.name.toLowerCase().includes(q) ||
          enriched.customer.company.toLowerCase().includes(q) ||
          enriched.customer.email.toLowerCase().includes(q)
        );
        const matchPlan = enriched.plan && (
          enriched.plan.name.toLowerCase().includes(q) ||
          enriched.plan.code.toLowerCase().includes(q)
        );
        const matchNotes = s.notes && s.notes.toLowerCase().includes(q);
        const matchProd = (s.products || []).some(p => p.productName.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q));
        return matchNum || matchCust || matchPlan || matchNotes || matchProd;
      });
    }

    // Enrich all results
    const enrichedResults = results.map(s => enrichSubscription(s, db));

    // Sort by default: most recent first
    enrichedResults.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));

    return enrichedResults;
  },

  // Get single subscription
  getSubscriptionById(id, user) {
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === id || s.subscriptionNumber === id);
    if (!sub) return null;

    if (!canViewSubscription(sub, user)) {
      const err = new Error('Access denied: You are not authorized to view this subscription');
      err.statusCode = 403;
      throw err;
    }

    return enrichSubscription(sub, db);
  },

  // Create Subscription
  createSubscription(payload, user) {
    if (!canManageSubscriptions(user)) {
      const err = new Error('Access denied: Only authorized staff and administrators can create subscriptions');
      err.statusCode = 403;
      throw err;
    }

    const db = getDb();

    // Validate Customer
    if (!payload.customerId) {
      throw new Error('Customer is required');
    }
    const customer = db.customers.find(c => c.id === payload.customerId);
    if (!customer) {
      throw new Error(`Customer with ID ${payload.customerId} not found`);
    }

    // Validate Plan
    if (!payload.planId) {
      throw new Error('Plan is required');
    }
    const plan = db.plans.find(p => p.id === payload.planId);
    if (!plan) {
      throw new Error(`Plan with ID ${payload.planId} not found`);
    }

    // Calculate dates
    const startDate = payload.startDate || getTodayString();
    let expiryDate = payload.expiryDate;
    if (!expiryDate) {
      const start = new Date(startDate);
      const days = plan.durationDays || 30;
      start.setDate(start.getDate() + days);
      expiryDate = start.toISOString().split('T')[0];
    }

    // Financial calculations
    const financials = calculateSubscriptionFinancials(
      plan,
      payload.products || [],
      payload.quantity || 1,
      payload.unitPrice !== undefined ? payload.unitPrice : plan.basePrice,
      payload.discount || 0
    );

    // Initial status - Default Draft
    const initialStatus = payload.status && ['Draft', 'Quotation'].includes(payload.status) ? payload.status : 'Draft';

    // Unique subscription number
    const subscriptionNumber = payload.subscriptionNumber || generateUniqueSubscriptionNumber(db);

    const newSub = {
      id: `sub-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 5)}`,
      subscriptionNumber,
      customerId: payload.customerId,
      planId: payload.planId,
      status: initialStatus,
      startDate,
      expiryDate,
      paymentTerms: payload.paymentTerms || db.systemSettings.defaultPaymentTerms || 'Net 30',
      quantity: financials.quantity,
      unitPrice: financials.unitPrice,
      planTaxRate: financials.planTaxRate,
      planTax: financials.planTax,
      products: financials.products,
      subtotal: financials.subtotal,
      tax: financials.tax,
      discount: financials.discount,
      totalAmount: financials.totalAmount,
      currency: payload.currency || db.systemSettings.currencyCode || 'USD',
      autoCloseOnExpiry: payload.autoCloseOnExpiry !== undefined ? Boolean(payload.autoCloseOnExpiry) : true,
      renewalCount: 0,
      notes: payload.notes || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      history: [
        {
          timestamp: new Date().toISOString(),
          fromStatus: 'None',
          toStatus: initialStatus,
          action: `Created ${initialStatus}`,
          performedBy: user ? `${user.name} (${user.role})` : 'System',
          notes: payload.historyNote || 'Initial creation'
        }
      ]
    };

    db.subscriptions.unshift(newSub);
    saveDb(db);

    return enrichSubscription(newSub, db);
  },

  // Edit Subscription
  updateSubscription(id, payload, user) {
    if (!canManageSubscriptions(user)) {
      const err = new Error('Access denied: Only authorized staff and administrators can edit subscriptions');
      err.statusCode = 403;
      throw err;
    }

    const db = getDb();
    const index = db.subscriptions.findIndex(s => s.id === id);
    if (index === -1) {
      throw new Error(`Subscription with ID ${id} not found`);
    }

    const existing = db.subscriptions[index];

    // Cannot edit closed subscriptions unless reactivating
    if (existing.status === 'Closed' && !payload.allowClosedEdit) {
      throw new Error('Closed subscriptions cannot be edited. Please renew or create a draft.');
    }

    // Customer update
    if (payload.customerId && payload.customerId !== existing.customerId) {
      const customer = db.customers.find(c => c.id === payload.customerId);
      if (!customer) throw new Error('Selected customer not found');
      existing.customerId = payload.customerId;
    }

    // Plan update
    let plan = db.plans.find(p => p.id === (payload.planId || existing.planId));
    if (!plan) throw new Error('Selected plan not found');
    existing.planId = plan.id;

    if (payload.startDate) existing.startDate = payload.startDate;
    if (payload.expiryDate) existing.expiryDate = payload.expiryDate;
    if (payload.paymentTerms) existing.paymentTerms = payload.paymentTerms;
    if (payload.notes !== undefined) existing.notes = payload.notes;
    if (payload.autoCloseOnExpiry !== undefined) existing.autoCloseOnExpiry = Boolean(payload.autoCloseOnExpiry);

    // Re-calculate financials
    const financials = calculateSubscriptionFinancials(
      plan,
      payload.products !== undefined ? payload.products : existing.products,
      payload.quantity !== undefined ? payload.quantity : existing.quantity,
      payload.unitPrice !== undefined ? payload.unitPrice : existing.unitPrice,
      payload.discount !== undefined ? payload.discount : existing.discount
    );

    existing.quantity = financials.quantity;
    existing.unitPrice = financials.unitPrice;
    existing.planTaxRate = financials.planTaxRate;
    existing.planTax = financials.planTax;
    existing.products = financials.products;
    existing.subtotal = financials.subtotal;
    existing.tax = financials.tax;
    existing.discount = financials.discount;
    existing.totalAmount = financials.totalAmount;
    existing.updatedAt = new Date().toISOString();

    existing.history.push({
      timestamp: new Date().toISOString(),
      fromStatus: existing.status,
      toStatus: existing.status,
      action: 'Updated Details',
      performedBy: user ? `${user.name} (${user.role})` : 'System',
      notes: payload.updateReason || 'Subscription details and line items updated'
    });

    db.subscriptions[index] = existing;
    saveDb(db);

    return enrichSubscription(existing, db);
  },

  // Transition Subscription Status
  transitionStatus(id, newStatus, options = {}, user) {
    if (!canManageSubscriptions(user)) {
      const err = new Error('Access denied: Only authorized staff and administrators can change subscription status');
      err.statusCode = 403;
      throw err;
    }

    const db = getDb();
    const index = db.subscriptions.findIndex(s => s.id === id);
    if (index === -1) {
      throw new Error(`Subscription with ID ${id} not found`);
    }

    const sub = db.subscriptions[index];
    const oldStatus = sub.status;

    if (!isValidTransition(oldStatus, newStatus)) {
      throw new Error(`Invalid status transition from "${oldStatus}" to "${newStatus}". Allowed transitions are: ${(VALID_TRANSITIONS[oldStatus] || []).join(', ') || 'None'}`);
    }

    sub.status = newStatus;
    sub.updatedAt = new Date().toISOString();

    // Specific status metadata
    if (newStatus === 'Paused') {
      sub.pausedAt = new Date().toISOString();
      sub.pauseReason = options.reason || 'Paused by staff/admin';
    } else if (oldStatus === 'Paused' && newStatus === 'Active') {
      sub.resumedAt = new Date().toISOString();
      delete sub.pauseReason;
    } else if (newStatus === 'Closed') {
      sub.closedAt = new Date().toISOString();
      sub.closedReason = options.reason || 'Closed / Terminated';
    }

    sub.history.push({
      timestamp: new Date().toISOString(),
      fromStatus: oldStatus,
      toStatus: newStatus,
      action: options.action || `Changed status to ${newStatus}`,
      performedBy: user ? `${user.name} (${user.role})` : 'System',
      notes: options.reason || options.notes || `Transitioned from ${oldStatus} to ${newStatus}`
    });

    db.subscriptions[index] = sub;
    saveDb(db);

    return enrichSubscription(sub, db);
  },

  // Pause subscription
  pauseSubscription(id, reason, user) {
    return this.transitionStatus(id, 'Paused', {
      action: 'Paused Subscription',
      reason: reason || 'Customer or staff requested pause'
    }, user);
  },

  // Resume subscription
  resumeSubscription(id, user) {
    return this.transitionStatus(id, 'Active', {
      action: 'Resumed Subscription',
      reason: 'Subscription resumed to Active status'
    }, user);
  },

  // Renew subscription
  renewSubscription(id, renewalOptions = {}, user) {
    if (!canManageSubscriptions(user)) {
      const err = new Error('Access denied: Only authorized staff and administrators can renew subscriptions');
      err.statusCode = 403;
      throw err;
    }

    const db = getDb();
    const index = db.subscriptions.findIndex(s => s.id === id);
    if (index === -1) {
      throw new Error(`Subscription with ID ${id} not found`);
    }

    const sub = db.subscriptions[index];
    const oldExpiry = new Date(sub.expiryDate || getTodayString());
    const baseDate = oldExpiry > new Date() ? oldExpiry : new Date();

    // Interval to extend: days (default 30 or based on cycle)
    const durationDays = renewalOptions.durationDays || (sub.planId === 'plan-enterprise' ? 365 : (sub.planId === 'plan-custom' ? 90 : 30));
    baseDate.setDate(baseDate.getDate() + durationDays);
    const newExpiryDate = renewalOptions.newExpiryDate || baseDate.toISOString().split('T')[0];

    const oldStatus = sub.status;
    sub.status = 'Active'; // Renewing puts it back to Active
    sub.expiryDate = newExpiryDate;
    sub.renewalCount = (sub.renewalCount || 0) + 1;
    sub.updatedAt = new Date().toISOString();

    // Clear closed/paused metadata
    delete sub.pauseReason;
    delete sub.closedReason;

    sub.history.push({
      timestamp: new Date().toISOString(),
      fromStatus: oldStatus,
      toStatus: 'Active',
      action: 'Renewed Subscription',
      performedBy: user ? `${user.name} (${user.role})` : 'System',
      notes: `Renewed for ${durationDays} days. New expiry date: ${newExpiryDate}. Renewal #${sub.renewalCount}. ${renewalOptions.notes || ''}`
    });

    db.subscriptions[index] = sub;
    saveDb(db);

    return enrichSubscription(sub, db);
  },

  // Cancel subscription
  cancelSubscription(id, reason, user) {
    return this.transitionStatus(id, 'Closed', {
      action: 'Cancelled Subscription',
      reason: reason || 'Subscription cancelled by administrator/staff'
    }, user);
  },

  // Automatically close expired subscriptions when configured
  autoCloseExpiredSubscriptions(user) {
    const db = getDb();
    const today = getTodayString();
    const closedIds = [];

    db.subscriptions.forEach(sub => {
      // Condition: autoCloseOnExpiry is true, not already Closed, and expiryDate is strictly past today
      if (
        sub.autoCloseOnExpiry === true &&
        sub.status !== 'Closed' &&
        sub.expiryDate &&
        sub.expiryDate < today
      ) {
        const previousStatus = sub.status;
        sub.status = 'Closed';
        sub.closedAt = new Date().toISOString();
        sub.closedReason = `Expired on ${sub.expiryDate} (Automated System Closure)`;
        sub.updatedAt = new Date().toISOString();
        sub.history.push({
          timestamp: new Date().toISOString(),
          fromStatus: previousStatus,
          toStatus: 'Closed',
          action: 'Auto-Closed on Expiry',
          performedBy: user ? `${user.name} (${user.role}) [Auto-Close Trigger]` : 'System Automated Scheduler',
          notes: `Subscription expired on ${sub.expiryDate}. Automatically closed per configuration policy.`
        });
        closedIds.push({
          id: sub.id,
          subscriptionNumber: sub.subscriptionNumber,
          expiryDate: sub.expiryDate,
          previousStatus
        });
      }
    });

    if (closedIds.length > 0) {
      saveDb(db);
    }

    return {
      success: true,
      count: closedIds.length,
      closedSubscriptions: closedIds,
      checkedAt: new Date().toISOString()
    };
  },

  // Dashboard KPI metrics
  getDashboardMetrics(user) {
    const db = getDb();
    let subs = db.subscriptions;
    if (user && user.role === 'customer') {
      subs = subs.filter(s => s.customerId === user.customerId);
    }

    const today = getTodayString();
    const target30 = new Date();
    target30.setDate(target30.getDate() + 30);
    const target30Str = target30.toISOString().split('T')[0];

    const metrics = {
      total: subs.length,
      draft: 0,
      quotation: 0,
      confirmed: 0,
      active: 0,
      paused: 0,
      closed: 0,
      mrr: 0,
      totalRevenue: 0,
      expiringSoon: 0,
      expiredUnclosed: 0
    };

    subs.forEach(s => {
      const statusKey = s.status ? s.status.toLowerCase() : 'draft';
      if (metrics[statusKey] !== undefined) {
        metrics[statusKey]++;
      }

      if (s.status === 'Active') {
        metrics.totalRevenue = round2(metrics.totalRevenue + (s.totalAmount || 0));
        // Calculate estimated monthly recurring revenue
        if (s.planId === 'plan-enterprise') {
          metrics.mrr = round2(metrics.mrr + ((s.totalAmount || 0) / 12));
        } else if (s.planId === 'plan-custom') {
          metrics.mrr = round2(metrics.mrr + ((s.totalAmount || 0) / 3));
        } else {
          metrics.mrr = round2(metrics.mrr + (s.totalAmount || 0));
        }
      }

      // Check expiring soon
      if (s.status === 'Active' || s.status === 'Confirmed') {
        if (s.expiryDate >= today && s.expiryDate <= target30Str) {
          metrics.expiringSoon++;
        }
        if (s.expiryDate < today) {
          metrics.expiredUnclosed++;
        }
      }
    });

    return metrics;
  }
};
