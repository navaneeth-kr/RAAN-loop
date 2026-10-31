# Brightloop Software — Subscription Management System

A unified, full-lifecycle **Subscription Management System** built for modern SaaS businesses (inspired by Odoo and Brightloop Software requirements). It handles subscription plans, quotation generation, automated billing, status lifecycle transitions, invoice creation, and customer portal views.

---

## 🚀 Quick Start

### 1. Launch the Application
Run the provided batch file or execute `node server.js`:
```cmd
cd C:\Users\alanj\.gemini\antigravity\scratch\subscription-management-system
node server.js
```
Or double-click `start.bat`.

### 2. Open in Browser
Visit **`http://localhost:3000`** in your browser.

---

## 🌟 Implemented Features

### 1. Subscription Management Hub
- **Create Subscriptions**:
  - Automatically generates unique sequential numbers (e.g. `SUB-2026-0001`, `SUB-2026-0002`).
  - Connects customer accounts with plans and product lines.
  - Multi-line item support with product variant pricing (e.g., standard price vs. Odoo Brand edition fee `+$560`).
  - Automatic tax calculation (`qty * unitPrice * taxRate / 100`).
  - Correct subtotal, tax total, and total amount calculation.
  - Start date, expiry date, payment terms (`Immediate Payment`, `15 Days`, `30 Days`, `Net 60`), and auto-close toggle.
- **View Subscriptions**:
  - Comprehensive table with subscription #, customer, plan, frequency, products summary, total amount, dates, status badges, and quick actions.
- **Edit Subscriptions**:
  - Full editing of Draft and Quotation subscriptions (quantities, variants, dates, terms).
  - Recalculates all financial totals upon saving.
- **Search Subscriptions**:
  - Real-time search by subscription number, customer name, contact email, plan name, or product name.
- **Filter by Status**:
  - Instant status tab filters: **All**, **Draft**, **Quotation**, **Confirmed**, **Active**, **Paused**, **Closed**.
  - Dropdown filters by Plan and by Customer.

### 2. Subscription Details Page (Deep View)
- Dedicated comprehensive detail view for every subscription.
- **Status Stepper / Progress Bar**: Visual progress indicator (`Draft` ➔ `Quotation` ➔ `Confirmed` ➔ `Active` ➔ `Closed`).
- **Customer Overview**: Company, contact person, email, phone, billing address.
- **Plan & Terms Overview**: Plan name, billing frequency, interval in days, start date, expiry date, payment terms, auto-close configuration.
- **Line Items & Calculation Table**: Every product line item with variant, quantity, unit price, tax rate %, tax amount $, and line total $.
- **Financial Breakdown Card**: Clear subtotal, tax amount, and grand total.
- **Audit Trail & Timeline**: Complete chronological history of status changes, timestamps, and acting users.
- **Linked Invoices**: Directly view, generate, and record payments for linked invoices.
- **Print / Export**: Print-ready quotation and agreement view.

### 3. Subscription Statuses & Strict Transitions
Enforces valid status transitions:
1. **Draft**: Initial draft order created by staff.
   - *Allowed transitions*: ➔ `Quotation`, ➔ `Closed`
2. **Quotation**: Official offer transmitted to the customer.
   - *Allowed transitions*: ➔ `Confirmed` (by customer or sales), ➔ `Draft` (revision), ➔ `Closed`
3. **Confirmed**: Accepted order awaiting deployment or activation.
   - *Allowed transitions*: ➔ `Active`, ➔ `Quotation`, ➔ `Closed`
4. **Active**: Live subscription with service provisioned.
   - *Allowed transitions*: ➔ `Paused`, ➔ `Closed`
5. **Closed**: Terminated, cancelled, or expired contract.
   - *Allowed transitions*: ➔ `Active` (via Renewal)

### 4. Additional Lifecycle Features
- **Pause Subscription**: Temporarily pauses active subscriptions (`Active` ➔ `Paused`) with a reason note.
- **Resume Subscription**: Restores paused subscriptions back to `Active`.
- **Renew Subscription**: Extends the subscription term (e.g. +30 days, +1 year), resets status to `Active`, and records an audit log.
- **Cancel Subscription**: Cancels active or quote subscriptions with a cancellation reason into `Closed`.
- **Auto-Close Expired Subscriptions**:
  - Subscriptions with `autoClose: true` and `expiryDate < today` are automatically closed.
  - Automatically runs periodically in the background (every 15 minutes).
  - Can be tested immediately via the **`⚡ Run Expired Check`** button in the header or via `POST /api/cron/auto-close-expired`.

### 5. Role-Based Access Control (RBAC)
- **Interactive Role Switcher** at the top of the app:
  - 👑 **Admin (Sarah Jenkins)**: Full control over all subscriptions, plans, products, customer accounts, and settings.
  - 👔 **Staff (Alex Miller)**: Can create, edit, search, pause, resume, renew, and cancel subscriptions, as well as generate invoices.
  - 👤 **Customer (Acme Corp / John Davis)**: Restricted portal view. Customers **only see their own subscriptions**, cannot edit staff settings, but can review and **Accept Quotations**.
  - 👤 **Customer (Nimbus Cloud / Emma Watson)**: Independent customer account seeing only Nimbus subscriptions.

### 6. Billing & Invoice Generation
- Generates customer invoices directly from subscriptions in 1 click.
- Automatic tax calculation matching the subscription line items.
- Status transition: `Draft` ➔ `Confirmed` ➔ `Paid`.
- Record payments with method (`Credit Card`, `Bank Transfer`, `PayPal`), transaction reference, amount, and notes.

---

## 📁 Project Structure

```
subscription-management-system/
├── server.js              # REST API & static server with RBAC & auto-close logic
├── database.json          # Persistent JSON store pre-seeded with Brightloop data
├── start.bat              # Batch script to launch server on port 3000
├── in_process_test.js     # Comprehensive automated test suite (52 tests)
├── README.md              # Documentation and system guide
└── public/
    ├── index.html         # Single-Page Application with all views and modals
    ├── styles.css         # Modern Odoo/Linear inspired SaaS interface
    └── app.js             # Client state management, calculations, and UI handlers
```

---

## 🧪 Automated Test Verification

Run the comprehensive test suite:
```cmd
node in_process_test.js
```
**Results: 52 PASSED, 0 FAILED** covering all calculation formulas, unique ID generation, status transitions, role permissions, and auto-close triggers.
