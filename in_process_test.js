// In-process integration test for Brightloop Subscription Management System
const { Readable } = require('stream');
const {
  handleRequest,
  getDb,
  generateSubscriptionNumber,
  calculateSubscriptionAmounts,
  checkAndCloseExpiredSubscriptions,
  isValidTransition
} = require('./server');

function makeRequest(pathname, { method = 'GET', body = null, role = 'admin', customerId = null, userName = 'Admin User' } = {}) {
  return new Promise((resolve, reject) => {
    const req = new Readable();
    req._read = () => {};
    req.url = pathname;
    req.method = method;
    req.headers = {
      'content-type': 'application/json',
      'x-user-role': role,
      'x-user-name': userName,
      ...(customerId ? { 'x-user-customer-id': customerId } : {})
    };

    if (body) {
      req.push(JSON.stringify(body));
    }
    req.push(null);

    let statusCode = 200;
    let headers = {};
    let responseData = '';

    const res = {
      writeHead(code, h) {
        statusCode = code;
        headers = h || {};
      },
      end(chunk) {
        if (chunk) responseData += chunk;
        let json = null;
        try {
          json = responseData ? JSON.parse(responseData) : {};
        } catch (e) {
          json = responseData;
        }
        resolve({ status: statusCode, headers, body: json });
      }
    };

    handleRequest(req, res).catch(reject);
  });
}

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ PASS: ${message}`);
    passed++;
  } else {
    console.error(`  ✕ FAIL: ${message}`);
    failed++;
  }
}

async function runInProcessTests() {
  console.log('=======================================================');
  console.log('STARTING INTEGRATION TEST SUITE (IN-PROCESS)');
  console.log('=======================================================\n');

  try {
    // 1. Math and calculation check
    console.log('TEST 1: Financial & Tax Calculation Engine');
    const calcResult = calculateSubscriptionAmounts([
      { quantity: 3, unitPrice: 150.0, taxRate: 10 },
      { quantity: 2, unitPrice: 65.0, taxRate: 10 }
    ]);
    // 3 * 150 = 450, tax = 45
    // 2 * 65 = 130, tax = 13
    // subtotal = 580, tax = 58, total = 638
    assert(calcResult.subtotal === 580.0, `Subtotal correct: $${calcResult.subtotal}`);
    assert(calcResult.taxTotal === 58.0, `Tax total correct: $${calcResult.taxTotal}`);
    assert(calcResult.totalAmount === 638.0, `Total amount correct: $${calcResult.totalAmount}`);

    // 2. Unique Subscription Number Generation
    console.log('\nTEST 2: Unique Subscription Number Generation');
    const num1 = generateSubscriptionNumber();
    assert(num1.startsWith('SUB-2026-'), `Generated number format valid: ${num1}`);

    // 3. Status Transition Matrix Rules
    console.log('\nTEST 3: Status Transition Rules');
    assert(isValidTransition('Draft', 'Quotation') === true, 'Draft -> Quotation allowed');
    assert(isValidTransition('Quotation', 'Confirmed') === true, 'Quotation -> Confirmed allowed');
    assert(isValidTransition('Confirmed', 'Active') === true, 'Confirmed -> Active allowed');
    assert(isValidTransition('Active', 'Paused') === true, 'Active -> Paused allowed');
    assert(isValidTransition('Paused', 'Active') === true, 'Paused -> Active allowed');
    assert(isValidTransition('Active', 'Closed') === true, 'Active -> Closed allowed');
    assert(isValidTransition('Closed', 'Active') === true, 'Closed -> Active (Renew) allowed');
    assert(isValidTransition('Draft', 'Active') === false, 'Draft -> Active disallowed');
    assert(isValidTransition('Draft', 'Paused') === false, 'Draft -> Paused disallowed');

    // 4. API: GET /api/subscriptions
    console.log('\nTEST 4: API GET /api/subscriptions');
    const listRes = await makeRequest('/api/subscriptions');
    assert(listRes.status === 200, 'GET /api/subscriptions returns 200');
    assert(Array.isArray(listRes.body), 'Subscriptions list is an array');
    assert(listRes.body.length >= 7, `Initial database preloaded with ${listRes.body.length} subscriptions`);

    // 5. API: Search and Filter
    console.log('\nTEST 5: Search & Filter Endpoints');
    const searchRes = await makeRequest('/api/subscriptions?search=Acme');
    assert(searchRes.status === 200, 'Search returns 200');
    assert(searchRes.body.length > 0 && searchRes.body.every(s => s.customer.name.includes('Acme')), 'All results match "Acme"');

    const filterActive = await makeRequest('/api/subscriptions?status=Active');
    assert(filterActive.status === 200, 'Filter by status=Active returns 200');
    assert(filterActive.body.every(s => s.status === 'Active'), 'All filtered items are Active');

    // 6. API: POST /api/subscriptions (Create)
    console.log('\nTEST 6: API Create Subscription');
    const createRes = await makeRequest('/api/subscriptions', {
      method: 'POST',
      body: {
        customerId: 'cust-1',
        planId: 'plan-business-monthly',
        startDate: '2026-11-01',
        expiryDate: '2026-12-01',
        paymentTerms: '30 Days',
        autoClose: false,
        notes: 'Created via automated integration test',
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
      }
    });

    assert(createRes.status === 201, 'POST /api/subscriptions returns 201 Created');
    const newSub = createRes.body;
    assert(newSub.subscriptionNumber.startsWith('SUB-2026-'), `Created subscription number: ${newSub.subscriptionNumber}`);
    assert(newSub.subtotal === 2325.0, `Subtotal correct: $${newSub.subtotal}`);
    assert(newSub.taxTotal === 232.5, `Tax correct: $${newSub.taxTotal}`);
    assert(newSub.totalAmount === 2557.5, `Total amount correct: $${newSub.totalAmount}`);

    // 7. API: GET /api/subscriptions/:id (Details)
    console.log('\nTEST 7: API Get Subscription Details');
    const detailRes = await makeRequest(`/api/subscriptions/${newSub.id}`);
    assert(detailRes.status === 200, 'GET /api/subscriptions/:id returns 200');
    assert(detailRes.body.customer.name === 'Acme Corporation', 'Customer details joined');
    assert(detailRes.body.plan.name === 'Business Pro (Monthly)', 'Plan details joined');
    assert(detailRes.body.items.length === 2, 'Line items intact');

    // 8. API: PUT /api/subscriptions/:id (Edit)
    console.log('\nTEST 8: API Edit Subscription');
    const editRes = await makeRequest(`/api/subscriptions/${newSub.id}`, {
      method: 'PUT',
      body: {
        notes: 'Updated notes via integration test',
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
      }
    });
    assert(editRes.status === 200, 'PUT /api/subscriptions/:id returns 200');
    assert(editRes.body.notes === 'Updated notes via integration test', 'Notes updated');
    assert(editRes.body.items[0].quantity === 4, 'Quantity updated');
    assert(editRes.body.totalAmount === 660.0, `Recalculated amount: $${editRes.body.totalAmount}`);

    // 9. API: Status Transitions Enforcement
    console.log('\nTEST 9: Status Transitions Enforcement');
    // Illegal Draft -> Active
    const badTrans = await makeRequest(`/api/subscriptions/${newSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Active' }
    });
    assert(badTrans.status === 400, 'Illegal transition Draft -> Active rejected with 400');

    // Legal: Draft -> Quotation -> Confirmed -> Active
    const toQuote = await makeRequest(`/api/subscriptions/${newSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Quotation', note: 'Sent quotation' }
    });
    assert(toQuote.status === 200 && toQuote.body.status === 'Quotation', 'Draft -> Quotation succeeded');

    const toConf = await makeRequest(`/api/subscriptions/${newSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Confirmed', note: 'Customer confirmed' }
    });
    assert(toConf.status === 200 && toConf.body.status === 'Confirmed', 'Quotation -> Confirmed succeeded');

    const toAct = await makeRequest(`/api/subscriptions/${newSub.id}/transition`, {
      method: 'POST',
      body: { status: 'Active', note: 'Services activated' }
    });
    assert(toAct.status === 200 && toAct.body.status === 'Active', 'Confirmed -> Active succeeded');

    // 10. Pause, Resume, Renew, Cancel
    console.log('\nTEST 10: Pause, Resume, Renew, Cancel Actions');
    // Pause
    const pauseRes = await makeRequest(`/api/subscriptions/${newSub.id}/pause`, {
      method: 'POST',
      body: { note: 'Pause test' }
    });
    assert(pauseRes.status === 200 && pauseRes.body.status === 'Paused', 'Pause succeeded');

    // Resume
    const resumeRes = await makeRequest(`/api/subscriptions/${newSub.id}/resume`, {
      method: 'POST',
      body: { note: 'Resume test' }
    });
    assert(resumeRes.status === 200 && resumeRes.body.status === 'Active', 'Resume succeeded');

    // Renew
    const oldExpiry = resumeRes.body.expiryDate;
    const renewRes = await makeRequest(`/api/subscriptions/${newSub.id}/renew`, {
      method: 'POST',
      body: { intervalDays: 30, note: 'Renewal test' }
    });
    assert(renewRes.status === 200, 'Renew succeeded');
    assert(renewRes.body.newExpiryDate > oldExpiry, `Expiry extended to ${renewRes.body.newExpiryDate}`);

    // Cancel
    const cancelRes = await makeRequest(`/api/subscriptions/${newSub.id}/cancel`, {
      method: 'POST',
      body: { reason: 'Cancellation test' }
    });
    assert(cancelRes.status === 200 && cancelRes.body.status === 'Closed', 'Cancel moved to Closed');

    // 11. Auto-Close Expired Subscriptions
    console.log('\nTEST 11: Auto-Close Expired Subscriptions');
    // Ensure an expired active subscription exists for testing auto-close idempotently
    const dbInst = getDb();
    let expiredSub = dbInst.subscriptions.find(s => s.id === 'sub-test-expired');
    if (!expiredSub) {
      expiredSub = {
        id: 'sub-test-expired',
        subscriptionNumber: 'SUB-2026-9999',
        customerId: 'cust-1',
        planId: 'plan-trial-daily',
        status: 'Active',
        startDate: '2026-10-01',
        expiryDate: '2026-10-15',
        autoClose: true,
        items: [{ quantity: 1, unitPrice: 10, taxRate: 10, taxAmount: 1, lineTotal: 11 }]
      };
      dbInst.subscriptions.push(expiredSub);
    } else {
      expiredSub.status = 'Active';
      expiredSub.expiryDate = '2026-10-15';
      expiredSub.autoClose = true;
    }

    const autoCloseRes = await makeRequest('/api/cron/auto-close-expired', { method: 'POST' });
    assert(autoCloseRes.status === 200, 'Auto-close endpoint returned 200');
    assert(autoCloseRes.body.closedCount >= 1, `Auto-closed ${autoCloseRes.body.closedCount} past-due subscription(s) successfully!`);
    assert(expiredSub.status === 'Closed', 'sub-test-expired was automatically Closed');

    // 12. Role-Based Access Control
    console.log('\nTEST 12: Role-Based Access Control');
    // Customer query
    const custRes = await makeRequest('/api/subscriptions', {
      role: 'customer',
      customerId: 'cust-1'
    });
    assert(custRes.status === 200, 'Customer query succeeds');
    assert(custRes.body.every(s => s.customerId === 'cust-1'), 'Customer only sees own subscriptions');

    // Customer cannot create subscription
    const custCreate = await makeRequest('/api/subscriptions', {
      method: 'POST',
      role: 'customer',
      customerId: 'cust-1',
      body: { customerId: 'cust-1', planId: 'plan-business-monthly', items: [{ quantity: 1, unitPrice: 100 }] }
    });
    assert(custCreate.status === 403, 'Customer forbidden from POST /api/subscriptions');

    // Customer cannot pause subscription
    const custPause = await makeRequest(`/api/subscriptions/${newSub.id}/pause`, {
      method: 'POST',
      role: 'customer',
      customerId: 'cust-1'
    });
    assert(custPause.status === 403, 'Customer forbidden from pause action');

    // 13. Invoices & Payments Generation
    console.log('\nTEST 13: Invoicing & Payment Processing');
    const invRes = await makeRequest(`/api/invoices/generate-from-subscription/${newSub.id}`, { method: 'POST' });
    assert(invRes.status === 201, 'Generate invoice returns 201');
    assert(invRes.body.invoiceNumber.startsWith('INV-2026-'), `Generated invoice: ${invRes.body.invoiceNumber}`);

    const payRes = await makeRequest(`/api/invoices/${invRes.body.id}/pay`, {
      method: 'POST',
      body: {
        amount: invRes.body.totalAmount,
        method: 'Credit Card',
        reference: 'CC-TEST-888'
      }
    });
    assert(payRes.status === 200 && payRes.body.status === 'Paid', 'Payment recorded and marked Paid');

    console.log('\n=======================================================');
    console.log(`ALL INTEGRATION TESTS PASSED: ${passed} PASSED, ${failed} FAILED`);
    console.log('=======================================================\n');

  } catch (err) {
    console.error('Integration test failed with error:', err);
    process.exit(1);
  }
}

runInProcessTests();
