const test = require('node:test');
const assert = require('node:assert');
const path = require('path');
const fs = require('fs');
const db = require('../data/db.js');

test('1. Unique Subscription Number Generation', (t) => {
  const database = db.getDb();
  const num1 = db.generateUniqueSubscriptionNumber(database);
  assert.ok(num1.startsWith('SUB-'), 'Subscription number should start with SUB-');
  assert.match(num1, /^SUB-\d{6}-\d{5}$/, 'Should follow SUB-YYYYMM-XXXXX pattern');

  // Add dummy to test sequence increment
  const simulatedDb = {
    subscriptions: [
      { subscriptionNumber: num1 }
    ]
  };
  const num2 = db.generateUniqueSubscriptionNumber(simulatedDb);
  assert.notStrictEqual(num1, num2, 'Generated numbers must be distinct');
});

test('2. Financial Calculations with Plan and Products', (t) => {
  const plan = {
    id: 'plan-test',
    basePrice: 100.00
  };

  const products = [
    {
      productId: 'p1',
      productName: 'Seats',
      sku: 'SKU-1',
      quantity: 2,
      unitPrice: 20.00,
      discount: 0,
      taxRate: 10.0
    },
    {
      productId: 'p2',
      productName: 'Support',
      sku: 'SKU-2',
      quantity: 1,
      unitPrice: 50.00,
      discount: 10.0, // 50 - 5 = 45
      taxRate: 18.0
    }
  ];

  // Plan: 100 * 1 = 100, tax 10% = 10
  // Product 1: 2 * 20 = 40, tax 10% = 4
  // Product 2: 1 * 50 * 0.9 = 45, tax 18% = 8.10
  // Total Subtotal: 100 + 40 + 45 = 185
  // Total Tax: 10 + 4 + 8.10 = 22.10
  // Total Amount: 185 + 22.10 = 207.10

  const fin = db.calculateSubscriptionFinancials(plan, products, 1, 100.00, 0);

  assert.strictEqual(fin.subtotal, 185.00, 'Subtotal calculation is correct');
  assert.strictEqual(fin.tax, 22.10, 'Tax calculation is correct');
  assert.strictEqual(fin.totalAmount, 207.10, 'Total amount calculation is correct');
});

test('3. Enforce Valid Status Transitions', (t) => {
  // Valid transitions
  assert.ok(db.isValidTransition('Draft', 'Quotation'), 'Draft -> Quotation must be valid');
  assert.ok(db.isValidTransition('Quotation', 'Confirmed'), 'Quotation -> Confirmed must be valid');
  assert.ok(db.isValidTransition('Confirmed', 'Active'), 'Confirmed -> Active must be valid');
  assert.ok(db.isValidTransition('Active', 'Paused'), 'Active -> Paused must be valid');
  assert.ok(db.isValidTransition('Paused', 'Active'), 'Paused -> Active must be valid');
  assert.ok(db.isValidTransition('Active', 'Closed'), 'Active -> Closed must be valid');
  assert.ok(db.isValidTransition('Closed', 'Draft'), 'Closed -> Draft must be valid');

  // Invalid transitions
  assert.strictEqual(db.isValidTransition('Draft', 'Active'), false, 'Draft directly to Active should be blocked');
  assert.strictEqual(db.isValidTransition('Quotation', 'Paused'), false, 'Quotation to Paused should be blocked');
  assert.strictEqual(db.isValidTransition('Paused', 'Draft'), false, 'Paused directly to Draft should be blocked');
  assert.strictEqual(db.isValidTransition('Closed', 'Paused'), false, 'Closed directly to Paused should be blocked');
});

test('4. RBAC: Customer vs Staff/Admin Access', (t) => {
  const adminUser = { id: 'admin-01', role: 'admin' };
  const staffUser = { id: 'staff-01', role: 'staff' };
  const customer1 = { id: 'user-01', role: 'customer', customerId: 'cust-01' };
  const customer2 = { id: 'user-02', role: 'customer', customerId: 'cust-02' };

  assert.ok(db.canManageSubscriptions(adminUser), 'Admin can manage');
  assert.ok(db.canManageSubscriptions(staffUser), 'Staff can manage');
  assert.strictEqual(db.canManageSubscriptions(customer1), false, 'Customer cannot manage');

  const subCust1 = { id: 'sub-test-1', customerId: 'cust-01' };
  assert.ok(db.canViewSubscription(subCust1, adminUser), 'Admin can view any sub');
  assert.ok(db.canViewSubscription(subCust1, staffUser), 'Staff can view any sub');
  assert.ok(db.canViewSubscription(subCust1, customer1), 'Customer can view own sub');
  assert.strictEqual(db.canViewSubscription(subCust1, customer2), false, 'Customer cannot view other sub');
});

test('5. Auto-Close Expired Subscriptions', (t) => {
  const adminUser = { id: 'admin-01', name: 'Sarah Jenkins', role: 'admin' };
  const result = db.autoCloseExpiredSubscriptions(adminUser);

  assert.ok(result.success, 'Auto-close execution succeeded');
  // sub-008 in seed data has expiryDate 2026-10-25 and status Active with autoCloseOnExpiry: true
  // So it should have been closed!
  const updatedSub8 = db.getSubscriptionById('sub-008', adminUser);
  assert.strictEqual(updatedSub8.status, 'Closed', 'Expired sub-008 should now be Closed');
  assert.ok(updatedSub8.closedReason.includes('Expired on 2026-10-25'), 'Closed reason should mention expiry date');
});

test('6. Subscription Lifecycle Actions: Pause, Resume, Renew, Cancel', (t) => {
  const adminUser = { id: 'admin-01', name: 'Sarah Jenkins', role: 'admin' };

  // Create a fresh test subscription
  const created = db.createSubscription({
    customerId: 'cust-01',
    planId: 'plan-starter',
    quantity: 1,
    paymentTerms: 'Net 30',
    notes: 'Lifecycle test'
  }, adminUser);

  assert.strictEqual(created.status, 'Draft');

  // Transition to Quotation
  const quote = db.transitionStatus(created.id, 'Quotation', { notes: 'Quotation sent' }, adminUser);
  assert.strictEqual(quote.status, 'Quotation');

  // Transition to Confirmed
  const confirmed = db.transitionStatus(created.id, 'Confirmed', { notes: 'Customer accepted' }, adminUser);
  assert.strictEqual(confirmed.status, 'Confirmed');

  // Transition to Active
  const active = db.transitionStatus(created.id, 'Active', { notes: 'Activated' }, adminUser);
  assert.strictEqual(active.status, 'Active');

  // Pause
  const paused = db.pauseSubscription(created.id, 'Maintenance pause', adminUser);
  assert.strictEqual(paused.status, 'Paused');
  assert.strictEqual(paused.pauseReason, 'Maintenance pause');

  // Resume
  const resumed = db.resumeSubscription(created.id, adminUser);
  assert.strictEqual(resumed.status, 'Active');

  // Renew
  const renewed = db.renewSubscription(created.id, { durationDays: 60, notes: 'Extended term' }, adminUser);
  assert.strictEqual(renewed.status, 'Active');
  assert.strictEqual(renewed.renewalCount, 1);

  // Cancel
  const cancelled = db.cancelSubscription(created.id, 'Service no longer needed', adminUser);
  assert.strictEqual(cancelled.status, 'Closed');
  assert.strictEqual(cancelled.closedReason, 'Service no longer needed');
});

test('7. Edit Subscription & Dynamic Financial Recalculation', (t) => {
  const adminUser = { id: 'admin-01', name: 'Sarah Jenkins', role: 'admin' };

  // Create a draft subscription
  const sub = db.createSubscription({
    customerId: 'cust-01',
    planId: 'plan-starter', // base price 49
    quantity: 1,
    paymentTerms: 'Net 15',
    products: []
  }, adminUser);

  assert.strictEqual(sub.quantity, 1);
  assert.strictEqual(sub.paymentTerms, 'Net 15');

  // Edit subscription: update quantity to 3, add product, change payment terms to Net 60
  const updated = db.updateSubscription(sub.id, {
    quantity: 3,
    paymentTerms: 'Net 60',
    products: [
      {
        productId: 'prod-seats',
        productName: 'Additional Team Seat',
        quantity: 2,
        unitPrice: 15.00,
        taxRate: 10.0
      }
    ],
    notes: 'Updated via customer request'
  }, adminUser);

  // Plan: 3 * 49 = 147, 10% tax = 14.70 -> plan total 161.70
  // Product: 2 * 15 = 30, 10% tax = 3.00 -> product total 33.00
  // Subtotal = 147 + 30 = 177
  // Tax = 14.70 + 3.00 = 17.70
  // Total = 177 + 17.70 = 194.70
  assert.strictEqual(updated.quantity, 3);
  assert.strictEqual(updated.paymentTerms, 'Net 60');
  assert.strictEqual(updated.subtotal, 177.00);
  assert.strictEqual(updated.tax, 17.70);
  assert.strictEqual(updated.totalAmount, 194.70);
  assert.strictEqual(updated.products.length, 1);
  assert.strictEqual(updated.notes, 'Updated via customer request');
});

test('8. Search and Filter by Status (Draft, Quotation, Confirmed, Active, Closed)', (t) => {
  const adminUser = { id: 'admin-01', name: 'Sarah Jenkins', role: 'admin' };

  // Test status filters
  const draftSubs = db.getSubscriptions({ status: 'Draft' }, adminUser);
  assert.ok(draftSubs.every(s => s.status.toLowerCase() === 'draft'), 'All returned must be Draft');

  const activeSubs = db.getSubscriptions({ status: 'Active' }, adminUser);
  assert.ok(activeSubs.every(s => s.status.toLowerCase() === 'active'), 'All returned must be Active');

  const quoteSubs = db.getSubscriptions({ status: 'Quotation' }, adminUser);
  assert.ok(quoteSubs.every(s => s.status.toLowerCase() === 'quotation'), 'All returned must be Quotation');

  const confirmedSubs = db.getSubscriptions({ status: 'Confirmed' }, adminUser);
  assert.ok(confirmedSubs.every(s => s.status.toLowerCase() === 'confirmed'), 'All returned must be Confirmed');

  const closedSubs = db.getSubscriptions({ status: 'Closed' }, adminUser);
  assert.ok(closedSubs.every(s => s.status.toLowerCase() === 'closed'), 'All returned must be Closed');

  // Test search by customer company name
  const searched = db.getSubscriptions({ search: 'Acme' }, adminUser);
  assert.ok(searched.length > 0, 'Search should find Acme Corporation');
  assert.ok(searched.some(s => s.customer && s.customer.company.includes('Acme')), 'Match found for Acme');

  // Test search by subscription number prefix
  const searchedByNum = db.getSubscriptions({ search: 'SUB-' }, adminUser);
  assert.ok(searchedByNum.length > 0, 'Search should find subscriptions starting with SUB-');
});

test('9. RBAC: Unauthorized User cannot Edit or Manage Subscriptions', (t) => {
  const customerUser = { id: 'user-cust-01', role: 'customer', customerId: 'cust-01' };

  // Customer cannot create
  assert.throws(() => {
    db.createSubscription({ customerId: 'cust-01', planId: 'plan-starter' }, customerUser);
  }, /Access denied/, 'Customer must not be allowed to create subscription');

  // Customer cannot change status
  assert.throws(() => {
    db.transitionStatus('sub-001', 'Active', {}, customerUser);
  }, /Access denied/, 'Customer must not be allowed to transition status');

  // Customer cannot pause
  assert.throws(() => {
    db.pauseSubscription('sub-001', 'pause', customerUser);
  }, /Access denied/, 'Customer must not be allowed to pause subscription');
});
