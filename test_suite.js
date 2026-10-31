// Comprehensive Automated Test Suite for Brightloop Subscription Management System
const http = require('http');

const PORT = 3000;
const BASE_URL = `http://localhost:${PORT}`;

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    const reqOptions = {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-user-role': options.role || 'admin',
        'x-user-name': options.userName || 'Sarah Jenkins (Admin)',
        ...(options.customerId ? { 'x-user-customer-id': options.customerId } : {}),
        ...(options.headers || {})
      }
    };

    const req = http.request(url, reqOptions, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = data ? JSON.parse(data) : {};
          resolve({ status: res.statusCode, body: json });
        } catch (e) {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });

    req.on('error', reject);
    if (options.body) {
      req.write(JSON.stringify(options.body));
    }
    req.end();
  });
}

let passed = 0;
let failed = 0;

function assert(condition, testName) {
  if (condition) {
    console.log(`  ✓ PASS: ${testName}`);
    passed++;
  } else {
    console.error(`  ✕ FAIL: ${testName}`);
    failed++;
  }
}

async function runTests() {
  console.log('\n=======================================================');
  console.log('STARTING SUBSCRIPTION MANAGEMENT TEST SUITE');
  console.log('=======================================================\n');

  try {
    // 1. Get initial subscriptions list
    console.log('TEST GROUP 1: Subscription Listing & Retrieval');
    const listRes = await request('/api/subscriptions');
    assert(listRes.status === 200, 'GET /api/subscriptions returns 200 OK');
    assert(Array.isArray(listRes.body), 'Subscriptions list is an array');
    assert(listRes.body.length > 0, `Initial subscriptions preloaded: ${listRes.body.length}`);

    // 2. Search subscriptions
    console.log('\nTEST GROUP 2: Search & Filter functionality');
    const searchRes = await request('/api/subscriptions?search=Acme');
    assert(searchRes.status === 200, 'Search returns 200');
    assert(searchRes.body.every(s => s.customer.name.includes('Acme')), 'All search results belong to Acme');

    // Filter by status
    const filterActive = await request('/api/subscriptions?status=Active');
    assert(filterActive.status === 200, 'Filter by Active returns 200');
    assert(filterActive.body.every(s => s.status === 'Active'), 'All filtered results have status=Active');

    // 3. Create Subscription
    console.log('\nTEST GROUP 3: Create Subscription with amounts and unique number');
    const newSubPayload = {
      customerId: 'cust-1',
      planId: 'plan-business-monthly',
      startDate: '2026-11-01',
      expiryDate: '2026-12-01',
      paymentTerms: '30 Days',
      autoClose: false,
      notes: 'Automated test suite subscription',
      status: 'Draft',
      items: [
        {
          productId: 'prod-1',
          productName: 'Cloud ERP Core',
          variant: 'Standard Edition',
          quantity: 3,
          unitPrice: 150.0,
          taxRate: 10
        },
        {
          productId: 'prod-2',
          productName: 'CRM Pro & Sales Pipeline',
          variant: 'Odoo Brand Edition',
          quantity: 3,
          unitPrice: 625.0,
          taxRate: 10
        }
      ]
    };

    const createRes = await request('/api/subscriptions', { method: 'POST', body: newSubPayload });
    assert(createRes.status === 201, 'POST /api/subscriptions returns 201 Created');
    const createdSub = createRes.body;
    assert(createdSub.subscriptionNumber.startsWith('SUB-2026-'), `Generated unique number: ${createdSub.subscriptionNumber}`);
    assert(createdSub.status === 'Draft', 'Initial status is Draft');

    // Expected subtotal: 3 * 150 (450) + 3 * 625 (1875) = 2325
    // Tax: 10% of 2325 = 232.50
    // Total: 2557.50
    assert(createdSub.subtotal === 2325.0, `Correct subtotal: $${createdSub.subtotal} (Expected: 2325)`);
    assert(createdSub.taxTotal === 232.5, `Correct taxTotal: $${createdSub.taxTotal} (Expected: 232.5)`);
    assert(createdSub.totalAmount === 2557.5, `Correct totalAmount: $${createdSub.totalAmount} (Expected: 2557.5)`);

    // 4. View Subscription Details
    console.log('\nTEST GROUP 4: View Subscription Details');
    const detailRes = await request(`/api/subscriptions/${createdSub.id}`);
    assert(detailRes.status === 200, 'GET /api/subscriptions/:id returns 200');
    assert(detailRes.body.customer.name === 'Acme Corporation', 'Customer details correctly linked');
    assert(detailRes.body.plan.name === 'Business Pro (Monthly)', 'Plan details correctly linked');
    assert(detailRes.body.items.length === 2, '2 line items present in detail');

    // 5. Edit Subscription
    console.log('\nTEST GROUP 5: Edit Subscription');
    const editPayload = {
      notes: 'Updated notes via test suite',
      items: [
        {
          productId: 'prod-1',
          productName: 'Cloud ERP Core',
          variant: 'Standard Edition',
          quantity: 4,
          unitPrice: 150.0,
          taxRate: 10
        }
      ]
    };
    const editRes = await request(`/api/subscriptions/${createdSub.id}`, { method: 'PUT', body: editPayload });
    assert(editRes.status === 200, 'PUT /api/subscriptions/:id returns 200');
    assert(editRes.body.notes === 'Updated notes via test suite', 'Notes updated');
    assert(editRes.body.items[0].quantity === 4, 'Quantity updated to 4');
    // 4 * 150 = 600, tax 60 = 660
    assert(editRes.body.totalAmount === 660, `Recalculated total after edit: $${editRes.body.totalAmount} (Expected: 660)`);

    // 6. Enforce Valid Status Transitions
    console.log('\nTEST GROUP 6: Strict Status Transitions');
    // Invalid transition: Draft -> Active (must go through Quotation -> Confirmed or Quotation)
    const invalidTrans = await request(`/api/subscriptions/${createdSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Active' }
    });
    assert(invalidTrans.status === 400, 'Illegal transition Draft -> Active rejected with 400');

    // Valid: Draft -> Quotation
    const transQuote = await request(`/api/subscriptions/${createdSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Quotation', note: 'Sent quote to customer' }
    });
    assert(transQuote.status === 200 && transQuote.body.status === 'Quotation', 'Valid transition Draft -> Quotation succeeds');

    // Valid: Quotation -> Confirmed
    const transConf = await request(`/api/subscriptions/${createdSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Confirmed', note: 'Customer accepted offer' }
    });
    assert(transConf.status === 200 && transConf.body.status === 'Confirmed', 'Valid transition Quotation -> Confirmed succeeds');

    // Valid: Confirmed -> Active
    const transAct = await request(`/api/subscriptions/${createdSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Active', note: 'Provisioned services' }
    });
    assert(transAct.status === 200 && transAct.body.status === 'Active', 'Valid transition Confirmed -> Active succeeds');

    // 7. Additional Features: Pause, Resume, Renew, Cancel
    console.log('\nTEST GROUP 7: Additional Features (Pause, Resume, Renew, Cancel)');
    // Pause
    const pauseRes = await request(`/api/subscriptions/${createdSub.id}/pause`, {
      method: 'POST',
      body: { note: 'Client maintenance freeze' }
    });
    assert(pauseRes.status === 200 && pauseRes.body.status === 'Paused', 'Pause subscription moves status to Paused');

    // Resume
    const resumeRes = await request(`/api/subscriptions/${createdSub.id}/resume`, {
      method: 'POST',
      body: { note: 'Freeze lifted' }
    });
    assert(resumeRes.status === 200 && resumeRes.body.status === 'Active', 'Resume subscription moves status back to Active');

    // Renew
    const origExpiry = resumeRes.body.expiryDate;
    const renewRes = await request(`/api/subscriptions/${createdSub.id}/renew`, {
      method: 'POST',
      body: { intervalDays: 30, note: 'Renewed for another month' }
    });
    assert(renewRes.status === 200, 'Renew subscription returns 200');
    assert(renewRes.body.newExpiryDate > origExpiry, `Expiry date extended from ${origExpiry} to ${renewRes.body.newExpiryDate}`);

    // Cancel
    const cancelRes = await request(`/api/subscriptions/${createdSub.id}/cancel`, {
      method: 'POST',
      body: { reason: 'Client requested migration' }
    });
    assert(cancelRes.status === 200 && cancelRes.body.status === 'Closed', 'Cancel subscription moves status to Closed');

    // 8. Auto-Close Expired Subscriptions
    console.log('\nTEST GROUP 8: Auto-Close Expired Subscriptions');
    const autoCloseRes = await request('/api/cron/auto-close-expired', { method: 'POST' });
    assert(autoCloseRes.status === 200, 'Auto-close trigger returns 200');
    assert(typeof autoCloseRes.body.closedCount === 'number', `Closed ${autoCloseRes.body.closedCount} expired subscriptions`);

    // 9. Role-Based Access Control (RBAC)
    console.log('\nTEST GROUP 9: Role-Based Access Control');
    // Customer query: customer can only see own subscriptions
    const custRes = await request('/api/subscriptions', {
      role: 'customer',
      customerId: 'cust-1',
      userName: 'John Davis'
    });
    assert(custRes.status === 200, 'Customer query returns 200');
    assert(custRes.body.every(s => s.customerId === 'cust-1'), 'Customer only received subscriptions belonging to cust-1');

    // Customer forbidden from creating subscriptions directly
    const custCreate = await request('/api/subscriptions', {
      method: 'POST',
      role: 'customer',
      customerId: 'cust-1',
      body: newSubPayload
    });
    assert(custCreate.status === 403, 'Customer forbidden from POST /api/subscriptions (403)');

    // Customer forbidden from pausing subscriptions
    const custPause = await request(`/api/subscriptions/${createdSub.id}/pause`, {
      method: 'POST',
      role: 'customer',
      customerId: 'cust-1'
    });
    assert(custPause.status === 403, 'Customer forbidden from pausing subscriptions (403)');

    // 10. Invoicing & Billing
    console.log('\nTEST GROUP 10: Invoices & Payment Settlement');
    const genInv = await request(`/api/invoices/generate-from-subscription/${createdSub.id}`, { method: 'POST' });
    assert(genInv.status === 201, 'Generate invoice from subscription returns 201 Created');
    assert(genInv.body.invoiceNumber.startsWith('INV-2026-'), `Generated invoice number: ${genInv.body.invoiceNumber}`);
    assert(genInv.body.status === 'Draft', 'Initial invoice status is Draft');

    // Confirm invoice
    const confInv = await request(`/api/invoices/${genInv.body.id}/confirm`, { method: 'POST' });
    assert(confInv.status === 200 && confInv.body.status === 'Confirmed', 'Invoice confirmed');

    // Pay invoice
    const payInv = await request(`/api/invoices/${genInv.body.id}/pay`, {
      method: 'POST',
      body: {
        amount: genInv.body.totalAmount,
        method: 'Bank Transfer',
        reference: 'WIRE-TEST-999'
      }
    });
    assert(payInv.status === 200 && payInv.body.status === 'Paid', 'Invoice settled and marked Paid');

    console.log('\n=======================================================');
    console.log(`TEST SUMMARY: ${passed} PASSED, ${failed} FAILED`);
    console.log('=======================================================\n');

    process.exit(failed > 0 ? 1 : 0);

  } catch (err) {
    console.error('Test execution error:', err);
    process.exit(1);
  }
}

runTests();
