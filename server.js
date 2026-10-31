const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');
const DB_FILE = path.join(__dirname, 'database.json');

// Default initial state fallback
const DEFAULT_DB = {
  systemSettings: {
    autoCloseExpiredIntervalMinutes: 60,
    lastAutoCloseRun: null,
    companyName: 'Brightloop Software',
    currency: 'USD',
    currencySymbol: '$',
    taxRateDefault: 10
  },
  customers: [],
  plans: [],
  products: [],
  quotationTemplates: [],
  paymentTermsOptions: ['Immediate Payment', '15 Days', '30 Days', 'Net 60'],
  subscriptions: [],
  invoices: []
};

// Database Read/Write helper with in-memory cache and atomic file persist
let memoryDb = null;

function getDb() {
  if (!memoryDb) {
    try {
      if (fs.existsSync(DB_FILE)) {
        const raw = fs.readFileSync(DB_FILE, 'utf8');
        memoryDb = JSON.parse(raw);
      } else {
        memoryDb = JSON.parse(JSON.stringify(DEFAULT_DB));
        saveDb();
      }
    } catch (e) {
      console.error('Error loading DB file, fallback to empty:', e);
      memoryDb = JSON.parse(JSON.stringify(DEFAULT_DB));
    }
  }
  return memoryDb;
}

function saveDb() {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(memoryDb, null, 2), 'utf8');
  } catch (e) {
    console.error('Failed to write DB:', e);
  }
}

// Generate Unique Subscription Number: SUB-YYYY-XXXX
function generateSubscriptionNumber() {
  const db = getDb();
  const currentYear = new Date().getFullYear();
  let maxSeq = 0;
  
  const regex = new RegExp(`^SUB-${currentYear}-(\\d{4})$`);
  for (const sub of db.subscriptions) {
    if (sub.subscriptionNumber) {
      const match = sub.subscriptionNumber.match(regex);
      if (match) {
        const num = parseInt(match[1], 10);
        if (num > maxSeq) maxSeq = num;
      }
    }
  }
  
  const nextSeq = String(maxSeq + 1).padStart(4, '0');
  return `SUB-${currentYear}-${nextSeq}`;
}

// Generate Unique Invoice Number: INV-YYYY-XXXX
function generateInvoiceNumber() {
  const db = getDb();
  const currentYear = new Date().getFullYear();
  let maxSeq = 0;
  
  const regex = new RegExp(`^INV-${currentYear}-(\\d{4})$`);
  for (const inv of (db.invoices || [])) {
    if (inv.invoiceNumber) {
      const match = inv.invoiceNumber.match(regex);
      if (match) {
        const num = parseInt(match[1], 10);
        if (num > maxSeq) maxSeq = num;
      }
    }
  }
  
  const nextSeq = String(maxSeq + 1).padStart(4, '0');
  return `INV-${currentYear}-${nextSeq}`;
}

// Recalculate line totals, subtotal, taxTotal, and grand total
function calculateSubscriptionAmounts(items) {
  let subtotal = 0;
  let taxTotal = 0;

  const calculatedItems = (items || []).map((item, index) => {
    const qty = Math.max(1, parseInt(item.quantity, 10) || 1);
    const price = parseFloat(item.unitPrice) || 0;
    const taxRate = parseFloat(item.taxRate) || 0;
    
    const lineSubtotal = Math.round(qty * price * 100) / 100;
    const taxAmount = Math.round(lineSubtotal * (taxRate / 100) * 100) / 100;
    const lineTotal = Math.round((lineSubtotal + taxAmount) * 100) / 100;

    subtotal += lineSubtotal;
    taxTotal += taxAmount;

    return {
      id: item.id || `line-${Date.now()}-${index}`,
      productId: item.productId || '',
      productName: item.productName || 'Product',
      variant: item.variant || 'Standard',
      quantity: qty,
      unitPrice: price,
      taxRate: taxRate,
      taxAmount: taxAmount,
      lineTotal: lineTotal
    };
  });

  subtotal = Math.round(subtotal * 100) / 100;
  taxTotal = Math.round(taxTotal * 100) / 100;
  const totalAmount = Math.round((subtotal + taxTotal) * 100) / 100;

  return { items: calculatedItems, subtotal, taxTotal, totalAmount };
}

// Enforce Valid Subscription Status Transitions
// 1. Draft -> Quotation, Closed
// 2. Quotation -> Confirmed, Draft, Closed
// 3. Confirmed -> Active, Quotation, Closed
// 4. Active -> Paused, Closed
// 5. Paused -> Active, Closed
// 6. Closed -> Active (Renew)
const VALID_TRANSITIONS = {
  'Draft': ['Quotation', 'Closed'],
  'Quotation': ['Confirmed', 'Draft', 'Closed'],
  'Confirmed': ['Active', 'Quotation', 'Closed'],
  'Active': ['Paused', 'Closed'],
  'Paused': ['Active', 'Closed'],
  'Closed': ['Active'] // Can be reopened via renewal
};

function isValidTransition(currentStatus, targetStatus) {
  const allowed = VALID_TRANSITIONS[currentStatus] || [];
  return allowed.includes(targetStatus);
}

// Background / On-demand Auto-Close Expired Subscriptions
function checkAndCloseExpiredSubscriptions() {
  const db = getDb();
  const todayStr = new Date().toISOString().split('T')[0];
  let closedCount = 0;
  const closedSubs = [];

  for (const sub of db.subscriptions) {
    if (sub.status !== 'Closed') {
      // Find plan
      const plan = db.plans.find(p => p.id === sub.planId);
      const shouldAutoClose = sub.autoClose === true || (plan && plan.autoClose === true);

      if (shouldAutoClose && sub.expiryDate && sub.expiryDate < todayStr) {
        const oldStatus = sub.status;
        sub.status = 'Closed';
        sub.updatedAt = new Date().toISOString();
        if (!sub.timeline) sub.timeline = [];
        sub.timeline.push({
          status: 'Closed',
          date: new Date().toISOString(),
          user: 'System (Auto-Close Service)',
          note: `Automatically closed expired subscription. Expired on ${sub.expiryDate} (Configured auto-close enabled on plan/subscription). Was ${oldStatus}.`
        });
        closedCount++;
        closedSubs.push({
          id: sub.id,
          subscriptionNumber: sub.subscriptionNumber,
          expiryDate: sub.expiryDate
        });
      }
    }
  }

  if (closedCount > 0) {
    db.systemSettings.lastAutoCloseRun = new Date().toISOString();
    saveDb();
    console.log(`[Auto-Close] Closed ${closedCount} expired subscriptions.`);
  }

  return { closedCount, closedSubs, ranAt: new Date().toISOString() };
}

// Run auto-close check periodically every 15 minutes (unref so tests/scripts exit cleanly)
if (require.main === module) {
  const autoCloseTimer = setInterval(() => {
    try {
      checkAndCloseExpiredSubscriptions();
    } catch (e) {
      console.error('Periodic auto-close error:', e);
    }
  }, 15 * 60 * 1000);
  if (autoCloseTimer.unref) autoCloseTimer.unref();
}

// Helper to parse JSON request bodies
function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 2 * 1024 * 1024) {
        req.destroy();
        reject(new Error('Request body too large'));
      }
    });
    req.on('end', () => {
      if (!body) return resolve({});
      try {
        resolve(JSON.parse(body));
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

// MIME types for static assets
const MIME_TYPES = {
  '.html': 'text/html; charset=UTF-8',
  '.css': 'text/css; charset=UTF-8',
  '.js': 'application/javascript; charset=UTF-8',
  '.json': 'application/json; charset=UTF-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

// Response helper
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, x-user-role, x-user-customer-id, x-user-name'
  });
  res.end(JSON.stringify(data));
}

// HTTP Server Request Handler
async function handleRequest(req, res) {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method;

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, x-user-role, x-user-customer-id, x-user-name'
    });
    return res.end();
  }

  // Extract Auth / Role headers
  const userRole = req.headers['x-user-role'] || parsedUrl.query.userRole || 'admin'; // 'admin' | 'staff' | 'customer'
  const customerId = req.headers['x-user-customer-id'] || parsedUrl.query.customerId || null;
  const userName = req.headers['x-user-name'] || (userRole === 'admin' ? 'Sarah Jenkins (Admin)' : userRole === 'staff' ? 'Alex Miller (Staff)' : 'Customer User');

  // ==========================================
  // API ROUTES
  // ==========================================

  // --- GET /api/auth/current-user ---
  if (pathname === '/api/auth/current-user' && method === 'GET') {
    return sendJson(res, 200, {
      role: userRole,
      customerId: customerId,
      userName: userName
    });
  }

  // --- GET /api/customers ---
  if (pathname === '/api/customers' && method === 'GET') {
    const db = getDb();
    if (userRole === 'customer' && customerId) {
      return sendJson(res, 200, db.customers.filter(c => c.id === customerId));
    }
    return sendJson(res, 200, db.customers);
  }

  // --- POST /api/customers ---
  if (pathname === '/api/customers' && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Customers are not permitted to create customer accounts.' });
    }
    try {
      const data = await parseJsonBody(req);
      if (!data.name || !data.email) {
        return sendJson(res, 400, { error: 'Customer name and email are required.' });
      }
      const db = getDb();
      const newCust = {
        id: `cust-${Date.now()}`,
        name: data.name,
        company: data.company || data.name,
        contactName: data.contactName || data.name,
        email: data.email,
        phone: data.phone || '',
        address: data.address || '',
        taxId: data.taxId || ''
      };
      db.customers.push(newCust);
      saveDb();
      return sendJson(res, 201, newCust);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- GET /api/plans ---
  if (pathname === '/api/plans' && method === 'GET') {
    const db = getDb();
    return sendJson(res, 200, db.plans);
  }

  // --- POST /api/plans ---
  if (pathname === '/api/plans' && method === 'POST') {
    if (userRole !== 'admin') {
      return sendJson(res, 403, { error: 'Only admins can create or configure plans.' });
    }
    try {
      const data = await parseJsonBody(req);
      const db = getDb();
      const newPlan = {
        id: `plan-${Date.now()}`,
        name: data.name || 'Custom Plan',
        billingFrequency: data.billingFrequency || 'monthly',
        intervalDays: parseInt(data.intervalDays, 10) || 30,
        basePrice: parseFloat(data.basePrice) || 0,
        minQuantity: parseInt(data.minQuantity, 10) || 1,
        autoClose: Boolean(data.autoClose),
        canPause: data.canPause !== false,
        canRenew: data.canRenew !== false,
        description: data.description || '',
        availableFrom: data.availableFrom || new Date().toISOString().split('T')[0],
        availableTo: data.availableTo || '2028-12-31'
      };
      db.plans.push(newPlan);
      saveDb();
      return sendJson(res, 201, newPlan);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- GET /api/products ---
  if (pathname === '/api/products' && method === 'GET') {
    const db = getDb();
    return sendJson(res, 200, db.products);
  }

  // --- POST /api/products ---
  if (pathname === '/api/products' && method === 'POST') {
    if (userRole !== 'admin') {
      return sendJson(res, 403, { error: 'Only administrators can create products.' });
    }
    try {
      const data = await parseJsonBody(req);
      const db = getDb();
      const newProd = {
        id: `prod-${Date.now()}`,
        name: data.name,
        type: data.type || 'Service',
        salesPrice: parseFloat(data.salesPrice) || 0,
        costPrice: parseFloat(data.costPrice) || 0,
        taxRate: parseFloat(data.taxRate) || 10,
        notes: data.notes || '',
        variants: Array.isArray(data.variants) ? data.variants : [{ name: 'Standard Edition', priceDelta: 0 }]
      };
      db.products.push(newProd);
      saveDb();
      return sendJson(res, 201, newProd);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- GET /api/quotation-templates ---
  if (pathname === '/api/quotation-templates' && method === 'GET') {
    const db = getDb();
    return sendJson(res, 200, db.quotationTemplates);
  }

  // --- GET /api/subscriptions ---
  // Supports query params: search, status, planId, customerId
  if (pathname === '/api/subscriptions' && method === 'GET') {
    const db = getDb();
    let results = [...db.subscriptions];

    // RBAC: Customer can ONLY see their own subscriptions
    if (userRole === 'customer') {
      if (!customerId) {
        return sendJson(res, 200, []);
      }
      results = results.filter(s => s.customerId === customerId);
    } else if (parsedUrl.query.customerId) {
      results = results.filter(s => s.customerId === parsedUrl.query.customerId);
    }

    // Filter by status (Draft, Quotation, Confirmed, Active, Closed, Paused)
    if (parsedUrl.query.status && parsedUrl.query.status !== 'All') {
      results = results.filter(s => s.status.toLowerCase() === parsedUrl.query.status.toLowerCase());
    }

    // Filter by plan
    if (parsedUrl.query.planId && parsedUrl.query.planId !== 'All') {
      results = results.filter(s => s.planId === parsedUrl.query.planId);
    }

    // Search by subscription number, customer name, email, plan name, or product name
    const q = (parsedUrl.query.search || '').trim().toLowerCase();
    if (q) {
      results = results.filter(s => {
        const cust = db.customers.find(c => c.id === s.customerId) || {};
        const plan = db.plans.find(p => p.id === s.planId) || {};
        const matchNum = (s.subscriptionNumber || '').toLowerCase().includes(q);
        const matchCust = (cust.name || '').toLowerCase().includes(q) || (cust.company || '').toLowerCase().includes(q) || (cust.email || '').toLowerCase().includes(q);
        const matchPlan = (plan.name || '').toLowerCase().includes(q);
        const matchProduct = (s.items || []).some(item => (item.productName || '').toLowerCase().includes(q));
        return matchNum || matchCust || matchPlan || matchProduct;
      });
    }

    // Enrich with customer and plan details for display
    const enriched = results.map(s => {
      const customer = db.customers.find(c => c.id === s.customerId) || null;
      const plan = db.plans.find(p => p.id === s.planId) || null;
      return {
        ...s,
        customer,
        plan
      };
    });

    // Sort by createdAt descending
    enriched.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));

    return sendJson(res, 200, enriched);
  }

  // --- GET /api/subscriptions/:id ---
  const subDetailMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)$/);
  if (subDetailMatch && method === 'GET') {
    const subId = subDetailMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId || s.subscriptionNumber === subId);
    
    if (!sub) {
      return sendJson(res, 404, { error: 'Subscription not found' });
    }

    // RBAC: Customer check
    if (userRole === 'customer' && sub.customerId !== customerId) {
      return sendJson(res, 403, { error: 'Access denied: You can only view your own subscriptions.' });
    }

    const customer = db.customers.find(c => c.id === sub.customerId) || null;
    const plan = db.plans.find(p => p.id === sub.planId) || null;
    const linkedInvoices = (db.invoices || []).filter(inv => inv.subscriptionId === sub.id);

    return sendJson(res, 200, {
      ...sub,
      customer,
      plan,
      invoices: linkedInvoices
    });
  }

  // --- POST /api/subscriptions (Create) ---
  if (pathname === '/api/subscriptions' && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Customers cannot create subscriptions directly. Please contact staff or sales.' });
    }

    try {
      const data = await parseJsonBody(req);
      const db = getDb();

      // Required fields validation
      if (!data.customerId) {
        return sendJson(res, 400, { error: 'Customer is required' });
      }
      if (!data.planId) {
        return sendJson(res, 400, { error: 'Subscription plan is required' });
      }
      if (!Array.isArray(data.items) || data.items.length === 0) {
        return sendJson(res, 400, { error: 'At least one product line item is required' });
      }

      const plan = db.plans.find(p => p.id === data.planId);
      if (!plan) {
        return sendJson(res, 400, { error: 'Selected plan does not exist' });
      }

      // Check min quantity on plan if applicable
      const totalQty = data.items.reduce((sum, item) => sum + (parseInt(item.quantity, 10) || 0), 0);
      if (plan.minQuantity && totalQty < plan.minQuantity) {
        return sendJson(res, 400, { error: `Plan requires a minimum total quantity of ${plan.minQuantity} items/seats.` });
      }

      // Generate Unique Subscription Number
      const subscriptionNumber = generateSubscriptionNumber();

      // Calculate start and expiry dates if not fully provided
      const startDate = data.startDate || new Date().toISOString().split('T')[0];
      let expiryDate = data.expiryDate;
      if (!expiryDate) {
        const d = new Date(startDate);
        d.setDate(d.getDate() + (plan.intervalDays || 30));
        expiryDate = d.toISOString().split('T')[0];
      }

      // Calculate amounts correctly
      const { items, subtotal, taxTotal, totalAmount } = calculateSubscriptionAmounts(data.items);

      const newSub = {
        id: `sub-${Date.now()}`,
        subscriptionNumber: subscriptionNumber,
        customerId: data.customerId,
        planId: data.planId,
        status: data.status || 'Draft',
        startDate: startDate,
        expiryDate: expiryDate,
        paymentTerms: data.paymentTerms || '30 Days',
        autoClose: data.autoClose !== undefined ? Boolean(data.autoClose) : (plan.autoClose || false),
        items: items,
        subtotal: subtotal,
        taxTotal: taxTotal,
        totalAmount: totalAmount,
        notes: data.notes || '',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        timeline: [
          {
            status: data.status || 'Draft',
            date: new Date().toISOString(),
            user: userName,
            note: 'Subscription created.'
          }
        ]
      };

      db.subscriptions.push(newSub);
      saveDb();

      return sendJson(res, 201, newSub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- PUT /api/subscriptions/:id (Edit) ---
  const subEditMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)$/);
  if (subEditMatch && method === 'PUT') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Customers cannot edit subscriptions.' });
    }

    const subId = subEditMatch[1];
    const db = getDb();
    const subIndex = db.subscriptions.findIndex(s => s.id === subId);

    if (subIndex === -1) {
      return sendJson(res, 404, { error: 'Subscription not found' });
    }

    const sub = db.subscriptions[subIndex];

    try {
      const data = await parseJsonBody(req);

      // In Draft or Quotation, full edit is allowed. In Active/Confirmed, items & dates are guarded but updateable with timeline note.
      if (data.customerId) sub.customerId = data.customerId;
      if (data.planId) sub.planId = data.planId;
      if (data.startDate) sub.startDate = data.startDate;
      if (data.expiryDate) sub.expiryDate = data.expiryDate;
      if (data.paymentTerms) sub.paymentTerms = data.paymentTerms;
      if (data.notes !== undefined) sub.notes = data.notes;
      if (data.autoClose !== undefined) sub.autoClose = Boolean(data.autoClose);

      if (Array.isArray(data.items) && data.items.length > 0) {
        const { items, subtotal, taxTotal, totalAmount } = calculateSubscriptionAmounts(data.items);
        sub.items = items;
        sub.subtotal = subtotal;
        sub.taxTotal = taxTotal;
        sub.totalAmount = totalAmount;
      }

      sub.updatedAt = new Date().toISOString();
      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: sub.status,
        date: new Date().toISOString(),
        user: userName,
        note: data.editReason || 'Subscription details updated.'
      });

      saveDb();
      return sendJson(res, 200, sub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/subscriptions/:id/transition (Strict Status Transition) ---
  const transitionMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)\/transition$/);
  if (transitionMatch && method === 'POST') {
    const subId = transitionMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) {
      return sendJson(res, 404, { error: 'Subscription not found' });
    }

    try {
      const body = await parseJsonBody(req);
      const targetStatus = body.status;
      const note = body.note || '';

      if (!targetStatus) {
        return sendJson(res, 400, { error: 'Target status is required' });
      }

      // Customer authorization check:
      // Customers can ONLY transition from Quotation -> Confirmed (accept quote) for their own subscription
      if (userRole === 'customer') {
        if (sub.customerId !== customerId) {
          return sendJson(res, 403, { error: 'Permission denied: This is not your subscription.' });
        }
        if (!(sub.status === 'Quotation' && targetStatus === 'Confirmed')) {
          return sendJson(res, 403, { error: 'Customers can only accept quotations into Confirmed status.' });
        }
      }

      // Enforce valid transitions
      if (!isValidTransition(sub.status, targetStatus)) {
        return sendJson(res, 400, {
          error: `Invalid status transition: Cannot transition from '${sub.status}' to '${targetStatus}'. Allowed: ${(VALID_TRANSITIONS[sub.status] || []).join(', ') || 'None'}`
        });
      }

      const prevStatus = sub.status;
      sub.status = targetStatus;
      sub.updatedAt = new Date().toISOString();
      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: targetStatus,
        date: new Date().toISOString(),
        user: userName,
        note: note || `Status transitioned from ${prevStatus} to ${targetStatus}`
      });

      saveDb();
      return sendJson(res, 200, sub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/subscriptions/:id/pause ---
  const pauseMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)\/pause$/);
  if (pauseMatch && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Only staff or admin can pause subscriptions.' });
    }
    const subId = pauseMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) return sendJson(res, 404, { error: 'Subscription not found' });
    if (sub.status !== 'Active') {
      return sendJson(res, 400, { error: `Only Active subscriptions can be paused. Current status is ${sub.status}.` });
    }

    try {
      const body = await parseJsonBody(req);
      sub.status = 'Paused';
      sub.updatedAt = new Date().toISOString();
      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: 'Paused',
        date: new Date().toISOString(),
        user: userName,
        note: body.note || 'Subscription paused by staff.'
      });
      saveDb();
      return sendJson(res, 200, sub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/subscriptions/:id/resume ---
  const resumeMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)\/resume$/);
  if (resumeMatch && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Only staff or admin can resume subscriptions.' });
    }
    const subId = resumeMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) return sendJson(res, 404, { error: 'Subscription not found' });
    if (sub.status !== 'Paused') {
      return sendJson(res, 400, { error: `Only Paused subscriptions can be resumed. Current status is ${sub.status}.` });
    }

    try {
      const body = await parseJsonBody(req);
      sub.status = 'Active';
      sub.updatedAt = new Date().toISOString();
      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: 'Active',
        date: new Date().toISOString(),
        user: userName,
        note: body.note || 'Subscription resumed. Service active.'
      });
      saveDb();
      return sendJson(res, 200, sub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/subscriptions/:id/renew ---
  const renewMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)\/renew$/);
  if (renewMatch && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Only staff or admin can execute subscription renewals.' });
    }
    const subId = renewMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) return sendJson(res, 404, { error: 'Subscription not found' });
    if (!['Active', 'Closed'].includes(sub.status)) {
      return sendJson(res, 400, { error: `Cannot renew a subscription in '${sub.status}' status. Subscriptions must be Active or Closed.` });
    }

    try {
      const body = await parseJsonBody(req);
      const plan = db.plans.find(p => p.id === sub.planId);
      const intervalDays = body.intervalDays || (plan ? plan.intervalDays : 30);

      // Compute new expiry date extending from current expiry or today
      const baseDate = (sub.expiryDate && new Date(sub.expiryDate) > new Date()) 
        ? new Date(sub.expiryDate) 
        : new Date();
      
      baseDate.setDate(baseDate.getDate() + intervalDays);
      const newExpiry = baseDate.toISOString().split('T')[0];
      const oldExpiry = sub.expiryDate;

      sub.expiryDate = newExpiry;
      sub.status = 'Active';
      sub.updatedAt = new Date().toISOString();

      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: 'Active',
        date: new Date().toISOString(),
        user: userName,
        note: body.note || `Subscription renewed (+${intervalDays} days). New expiry date: ${newExpiry} (Previous: ${oldExpiry}).`
      });

      saveDb();
      return sendJson(res, 200, {
        message: 'Subscription successfully renewed.',
        subscription: sub,
        newExpiryDate: newExpiry
      });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/subscriptions/:id/cancel ---
  const cancelMatch = pathname.match(/^\/api\/subscriptions\/([a-zA-Z0-9_-]+)\/cancel$/);
  if (cancelMatch && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Customers must submit a cancellation request to staff.' });
    }
    const subId = cancelMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) return sendJson(res, 404, { error: 'Subscription not found' });
    if (sub.status === 'Closed') {
      return sendJson(res, 400, { error: 'Subscription is already Closed.' });
    }

    try {
      const body = await parseJsonBody(req);
      const prevStatus = sub.status;
      sub.status = 'Closed';
      sub.updatedAt = new Date().toISOString();

      if (!sub.timeline) sub.timeline = [];
      sub.timeline.push({
        status: 'Closed',
        date: new Date().toISOString(),
        user: userName,
        note: body.reason ? `Subscription cancelled: ${body.reason}` : `Subscription cancelled from ${prevStatus}.`
      });

      saveDb();
      return sendJson(res, 200, sub);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- POST /api/cron/auto-close-expired ---
  // Demonstrates and triggers auto-close on expired subscriptions
  if (pathname === '/api/cron/auto-close-expired' && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Permission denied.' });
    }
    try {
      const result = checkAndCloseExpiredSubscriptions();
      return sendJson(res, 200, {
        success: true,
        message: `Auto-close check executed. Closed ${result.closedCount} expired subscription(s).`,
        ...result
      });
    } catch (err) {
      return sendJson(res, 500, { error: err.message });
    }
  }

  // --- POST /api/invoices/generate-from-subscription/:id ---
  const genInvMatch = pathname.match(/^\/api\/invoices\/generate-from-subscription\/([a-zA-Z0-9_-]+)$/);
  if (genInvMatch && method === 'POST') {
    if (userRole === 'customer') {
      return sendJson(res, 403, { error: 'Only staff or admin can generate invoices.' });
    }
    const subId = genInvMatch[1];
    const db = getDb();
    const sub = db.subscriptions.find(s => s.id === subId);

    if (!sub) return sendJson(res, 404, { error: 'Subscription not found' });
    const cust = db.customers.find(c => c.id === sub.customerId) || { name: 'Valued Customer' };

    const invNum = generateInvoiceNumber();
    const todayStr = new Date().toISOString().split('T')[0];

    // Compute due date from payment terms
    let dueDays = 30;
    if (sub.paymentTerms === 'Immediate Payment') dueDays = 0;
    else if (sub.paymentTerms === '15 Days') dueDays = 15;
    else if (sub.paymentTerms === 'Net 60') dueDays = 60;

    const dueDateObj = new Date();
    dueDateObj.setDate(dueDateObj.getDate() + dueDays);
    const dueDateStr = dueDateObj.toISOString().split('T')[0];

    const invoiceItems = (sub.items || []).map(item => ({
      description: `${item.productName} (${item.variant}) x${item.quantity}`,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
      amount: item.lineTotal,
      taxRate: item.taxRate
    }));

    const newInvoice = {
      id: `inv-${Date.now()}`,
      invoiceNumber: invNum,
      subscriptionId: sub.id,
      subscriptionNumber: sub.subscriptionNumber,
      customerId: sub.customerId,
      customerName: cust.name,
      issueDate: todayStr,
      dueDate: dueDateStr,
      status: 'Draft',
      paymentTerms: sub.paymentTerms,
      subtotal: sub.subtotal,
      taxTotal: sub.taxTotal,
      totalAmount: sub.totalAmount,
      items: invoiceItems,
      payments: []
    };

    if (!db.invoices) db.invoices = [];
    db.invoices.push(newInvoice);

    if (!sub.timeline) sub.timeline = [];
    sub.timeline.push({
      status: sub.status,
      date: new Date().toISOString(),
      user: userName,
      note: `Generated Invoice ${invNum} for $${sub.totalAmount.toFixed(2)}.`
    });

    saveDb();
    return sendJson(res, 201, newInvoice);
  }

  // --- GET /api/invoices ---
  if (pathname === '/api/invoices' && method === 'GET') {
    const db = getDb();
    let invoices = db.invoices || [];

    if (userRole === 'customer') {
      if (!customerId) return sendJson(res, 200, []);
      invoices = invoices.filter(inv => inv.customerId === customerId);
    } else if (parsedUrl.query.subscriptionId) {
      invoices = invoices.filter(inv => inv.subscriptionId === parsedUrl.query.subscriptionId);
    }

    return sendJson(res, 200, invoices);
  }

  // --- POST /api/invoices/:id/confirm ---
  const confInvMatch = pathname.match(/^\/api\/invoices\/([a-zA-Z0-9_-]+)\/confirm$/);
  if (confInvMatch && method === 'POST') {
    const invId = confInvMatch[1];
    const db = getDb();
    const inv = (db.invoices || []).find(i => i.id === invId);
    if (!inv) return sendJson(res, 404, { error: 'Invoice not found' });
    if (inv.status !== 'Draft') return sendJson(res, 400, { error: `Invoice is already ${inv.status}.` });

    inv.status = 'Confirmed';
    saveDb();
    return sendJson(res, 200, inv);
  }

  // --- POST /api/invoices/:id/pay (Record Payment) ---
  const payInvMatch = pathname.match(/^\/api\/invoices\/([a-zA-Z0-9_-]+)\/pay$/);
  if (payInvMatch && method === 'POST') {
    const invId = payInvMatch[1];
    const db = getDb();
    const inv = (db.invoices || []).find(i => i.id === invId);
    if (!inv) return sendJson(res, 404, { error: 'Invoice not found' });

    try {
      const body = await parseJsonBody(req);
      const amountPaid = parseFloat(body.amount) || inv.totalAmount;
      const method = body.method || 'Credit Card';
      const reference = body.reference || `TXN-${Date.now().toString().slice(-6)}`;
      const date = body.date || new Date().toISOString().split('T')[0];
      const notes = body.notes || 'Payment recorded via portal/staff';

      if (!inv.payments) inv.payments = [];
      inv.payments.push({
        paymentId: `pay-${Date.now()}`,
        amount: amountPaid,
        method: method,
        reference: reference,
        date: date,
        notes: notes
      });

      // Calculate total paid
      const totalPaid = inv.payments.reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
      if (totalPaid >= inv.totalAmount) {
        inv.status = 'Paid';
      }

      saveDb();
      return sendJson(res, 200, inv);
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // --- GET /api/dashboard/stats ---
  if (pathname === '/api/dashboard/stats' && method === 'GET') {
    const db = getDb();
    let subs = db.subscriptions;
    let invs = db.invoices || [];

    if (userRole === 'customer') {
      subs = subs.filter(s => s.customerId === customerId);
      invs = invs.filter(i => i.customerId === customerId);
    }

    const counts = {
      all: subs.length,
      draft: subs.filter(s => s.status === 'Draft').length,
      quotation: subs.filter(s => s.status === 'Quotation').length,
      confirmed: subs.filter(s => s.status === 'Confirmed').length,
      active: subs.filter(s => s.status === 'Active').length,
      paused: subs.filter(s => s.status === 'Paused').length,
      closed: subs.filter(s => s.status === 'Closed').length
    };

    // Calculate Monthly Recurring Revenue (MRR)
    let mrr = 0;
    for (const sub of subs) {
      if (sub.status === 'Active') {
        const plan = db.plans.find(p => p.id === sub.planId);
        const total = sub.totalAmount || 0;
        if (plan) {
          if (plan.billingFrequency === 'monthly') mrr += total;
          else if (plan.billingFrequency === 'yearly') mrr += total / 12;
          else if (plan.billingFrequency === 'weekly') mrr += total * 4.33;
          else if (plan.billingFrequency === 'daily') mrr += total * 30;
        } else {
          mrr += total;
        }
      }
    }

    // Invoice revenue stats
    let totalRevenuePaid = 0;
    let totalOutstanding = 0;
    for (const inv of invs) {
      const paid = (inv.payments || []).reduce((s, p) => s + (p.amount || 0), 0);
      totalRevenuePaid += paid;
      if (inv.status !== 'Paid') {
        totalOutstanding += Math.max(0, inv.totalAmount - paid);
      }
    }

    return sendJson(res, 200, {
      counts,
      mrr: Math.round(mrr * 100) / 100,
      totalRevenuePaid: Math.round(totalRevenuePaid * 100) / 100,
      totalOutstanding: Math.round(totalOutstanding * 100) / 100,
      activeCustomerCount: new Set(subs.filter(s => s.status === 'Active').map(s => s.customerId)).size
    });
  }

  // --- POST /api/reset-data (Reset to seed data) ---
  if (pathname === '/api/reset-data' && method === 'POST') {
    if (userRole !== 'admin') {
      return sendJson(res, 403, { error: 'Only admins can trigger a database reset.' });
    }
    // Read the original file or reload
    try {
      // Reload from disk or default
      memoryDb = null;
      getDb();
      return sendJson(res, 200, { message: 'Database reset successfully to seed state.' });
    } catch (err) {
      return sendJson(res, 500, { error: err.message });
    }
  }

  // ==========================================
  // STATIC ASSETS
  // ==========================================
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  
  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Fallback for single-page routing or 404
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        return res.end('Server Error loading file');
      }
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    });
  });
}

const server = http.createServer(handleRequest);

if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`=======================================================`);
    console.log(`Brightloop Subscription Management Server Running`);
    console.log(`URL: http://localhost:${PORT}`);
    console.log(`Time: ${new Date().toISOString()}`);
    console.log(`=======================================================`);
  });
}

module.exports = {
  server,
  handleRequest,
  getDb,
  saveDb,
  generateSubscriptionNumber,
  calculateSubscriptionAmounts,
  checkAndCloseExpiredSubscriptions,
  isValidTransition,
  VALID_TRANSITIONS
};
