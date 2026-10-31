const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const db = require('./data/db.js');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');

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

// Helper: parse request body JSON
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 5 * 1024 * 1024) { // 5MB limit
        reject(new Error('Payload too large'));
      }
    });
    req.on('end', () => {
      if (!body) return resolve({});
      try {
        resolve(JSON.parse(body));
      } catch (err) {
        reject(new Error('Invalid JSON payload'));
      }
    });
    req.on('error', err => reject(err));
  });
}

// Helper: send JSON response
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=UTF-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-User-Role'
  });
  res.end(JSON.stringify(data));
}

// Helper: send Error response
function sendError(res, statusCode, message, details = null) {
  sendJson(res, statusCode, {
    error: true,
    message,
    details
  });
}

// Identify user from headers or query parameters (Supports rapid role switching in frontend)
function authenticateUser(req, parsedUrl) {
  const userId = req.headers['x-user-id'] || parsedUrl.query.asUser || parsedUrl.query.userId || 'admin-01';
  const user = db.getUserById(userId);
  if (user) return user;
  // Default fallback to admin if not specified
  return {
    id: 'admin-01',
    name: 'Sarah Jenkins',
    email: 'sarah.admin@cloudflow.io',
    role: 'admin'
  };
}

// Serve static assets
function serveStaticFile(req, res, pathname) {
  let safePath = pathname;
  if (safePath === '/' || safePath === '') safePath = '/index.html';
  if (safePath === '/details' || safePath === '/details.html') safePath = '/subscription-details.html';
  if (safePath === '/create' || safePath === '/new' || safePath === '/edit') safePath = '/subscription-form.html';

  const filePath = path.join(PUBLIC_DIR, safePath);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    return sendError(res, 403, 'Forbidden file access');
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      return sendError(res, 404, 'Page or asset not found');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stats.size,
      'Cache-Control': 'no-cache'
    });

    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
}

// Background scheduler for automatic expiration closure
let autoCloseInterval = null;
function startAutoCloseScheduler() {
  const settings = db.getSystemSettings();
  if (autoCloseInterval) clearInterval(autoCloseInterval);

  const seconds = settings.autoCloseCheckIntervalSeconds || 60;
  console.log(`[Auto-Close Scheduler] Initialized to run every ${seconds} seconds.`);

  autoCloseInterval = setInterval(() => {
    const currentSettings = db.getSystemSettings();
    if (currentSettings.autoCloseExpiredCronEnabled) {
      try {
        const result = db.autoCloseExpiredSubscriptions();
        if (result.count > 0) {
          console.log(`[Auto-Close Scheduler] Automatically closed ${result.count} expired subscription(s):`, result.closedSubscriptions.map(s => s.subscriptionNumber).join(', '));
        }
      } catch (err) {
        console.error('[Auto-Close Scheduler] Error during background check:', err);
      }
    }
  }, seconds * 1000);
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method;

  // Handle CORS pre-flight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-User-Role'
    });
    return res.end();
  }

  // API Routes
  if (pathname.startsWith('/api/')) {
    const user = authenticateUser(req, parsedUrl);

    try {
      // 1. Current user session
      if (pathname === '/api/me' && method === 'GET') {
        return sendJson(res, 200, { user });
      }

      // 2. Users list for switcher
      if (pathname === '/api/users' && method === 'GET') {
        return sendJson(res, 200, { users: db.getUsers() });
      }

      // 3. Customers
      if (pathname === '/api/customers' && method === 'GET') {
        return sendJson(res, 200, { customers: db.getCustomers() });
      }

      if (pathname.startsWith('/api/customers/') && method === 'GET') {
        const custId = pathname.replace('/api/customers/', '');
        const cust = db.getCustomerById(custId);
        if (!cust) return sendError(res, 404, 'Customer not found');
        return sendJson(res, 200, { customer: cust });
      }

      // 4. Plans
      if (pathname === '/api/plans' && method === 'GET') {
        return sendJson(res, 200, { plans: db.getPlans() });
      }

      // 5. Products
      if (pathname === '/api/products' && method === 'GET') {
        return sendJson(res, 200, { products: db.getProducts() });
      }

      // 6. Settings
      if (pathname === '/api/settings') {
        if (method === 'GET') {
          return sendJson(res, 200, { settings: db.getSystemSettings() });
        }
        if (method === 'PUT') {
          const body = await parseBody(req);
          const updated = db.updateSystemSettings(body, user);
          startAutoCloseScheduler(); // restart with new timing if changed
          return sendJson(res, 200, { settings: updated });
        }
      }

      // 7. Dashboard Metrics
      if (pathname === '/api/metrics' && method === 'GET') {
        const metrics = db.getDashboardMetrics(user);
        return sendJson(res, 200, { metrics });
      }

      // 8. Auto-close expired subscriptions trigger (manual or cron)
      if (pathname === '/api/subscriptions/auto-close-expired' && method === 'POST') {
        const result = db.autoCloseExpiredSubscriptions(user);
        return sendJson(res, 200, result);
      }

      // 9. Subscriptions Collection (List & Create)
      if (pathname === '/api/subscriptions' || pathname === '/api/subscriptions/') {
        if (method === 'GET') {
          const filters = {
            status: parsedUrl.query.status,
            planId: parsedUrl.query.planId,
            customerId: parsedUrl.query.customerId,
            paymentTerms: parsedUrl.query.paymentTerms,
            expiryState: parsedUrl.query.expiryState,
            search: parsedUrl.query.search
          };
          const subscriptions = db.getSubscriptions(filters, user);
          return sendJson(res, 200, {
            count: subscriptions.length,
            subscriptions,
            currentUserRole: user.role
          });
        }

        if (method === 'POST') {
          const body = await parseBody(req);
          const newSub = db.createSubscription(body, user);
          return sendJson(res, 201, {
            success: true,
            subscription: newSub,
            message: `Subscription ${newSub.subscriptionNumber} created successfully`
          });
        }
      }

      // 10. Single Subscription Actions & Endpoints
      const subMatch = pathname.match(/^\/api\/subscriptions\/([^/]+)(.*)$/);
      if (subMatch) {
        const subId = subMatch[1];
        const subAction = subMatch[2]; // e.g. /pause, /resume, /renew, /cancel, /transition

        // Check single subscription GET
        if (subAction === '' && method === 'GET') {
          const subscription = db.getSubscriptionById(subId, user);
          if (!subscription) return sendError(res, 404, 'Subscription not found');
          return sendJson(res, 200, { subscription, currentUserRole: user.role });
        }

        // Single subscription PUT (Edit)
        if (subAction === '' && method === 'PUT') {
          const body = await parseBody(req);
          const updated = db.updateSubscription(subId, body, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Subscription ${updated.subscriptionNumber} updated successfully`
          });
        }

        // Status transition
        if (subAction === '/transition' && method === 'POST') {
          const body = await parseBody(req);
          if (!body.toStatus) return sendError(res, 400, 'Target status (toStatus) is required');
          const updated = db.transitionStatus(subId, body.toStatus, {
            reason: body.reason,
            notes: body.notes,
            action: body.action
          }, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Status transitioned to ${updated.status}`
          });
        }

        // Pause
        if (subAction === '/pause' && method === 'POST') {
          const body = await parseBody(req);
          const updated = db.pauseSubscription(subId, body.reason, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Subscription ${updated.subscriptionNumber} paused`
          });
        }

        // Resume
        if (subAction === '/resume' && method === 'POST') {
          const updated = db.resumeSubscription(subId, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Subscription ${updated.subscriptionNumber} resumed to Active`
          });
        }

        // Renew
        if (subAction === '/renew' && method === 'POST') {
          const body = await parseBody(req);
          const updated = db.renewSubscription(subId, body, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Subscription ${updated.subscriptionNumber} renewed until ${updated.expiryDate}`
          });
        }

        // Cancel
        if (subAction === '/cancel' && method === 'POST') {
          const body = await parseBody(req);
          const updated = db.cancelSubscription(subId, body.reason, user);
          return sendJson(res, 200, {
            success: true,
            subscription: updated,
            message: `Subscription ${updated.subscriptionNumber} cancelled (Closed)`
          });
        }
      }

      // No API route matched
      return sendError(res, 404, `API route not found: ${method} ${pathname}`);
    } catch (err) {
      console.error('API Error:', err);
      const statusCode = err.statusCode || 400;
      return sendError(res, statusCode, err.message || 'Internal server error');
    }
  }

  // Static Assets
  serveStaticFile(req, res, pathname);
});

// Start scheduler and listen
startAutoCloseScheduler();

server.listen(PORT, () => {
  console.log(`=======================================================`);
  console.log(` Subscription Management System is LIVE`);
  console.log(` Server running at: http://localhost:${PORT}`);
  console.log(` Local Time: 2026-10-31`);
  console.log(`=======================================================`);
});

module.exports = server;
