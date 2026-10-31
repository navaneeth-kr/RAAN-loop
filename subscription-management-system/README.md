<<<<<<< HEAD
# Subscription Management System

> **Enterprise-grade Subscription Lifecycle Management Platform** with automated expiration closure, dynamic multi-product line calculations, strict status transitions, and Role-Based Access Control (RBAC).

---

## 🌟 Key Features

### 1. Subscription Lifecycle & State Machine
- **Core Statuses:**
  1. `Draft`: Creation and modification of terms and proposals.
  2. `Quotation`: Formal proposals submitted for client review.
  3. `Confirmed`: Agreement accepted, ready for provisioning.
  4. `Active`: Operational and generating recurring revenue.
  5. `Closed`: Finalized, terminated, cancelled, or auto-closed upon expiry.
- **Additional Operational Actions:**
  - **Pause Subscription**: Suspend services with reason tracking.
  - **Resume Subscription**: Restore paused subscriptions directly back to `Active`.
  - **Renew Subscription**: Extend validity term (+1 Month, +1 Quarter, +1 Year), increment renewal count, and log audit history.
  - **Cancel Subscription**: Terminate active or paused subscriptions with cancellation reason.
  - **Auto-Close Expired Subscriptions**: Periodic background worker and on-demand trigger that automatically closes subscriptions past their expiry date when configured (`autoCloseOnExpiry: true`).

### 2. Comprehensive Subscription Information
- **Unique Subscription Number:** Atomic generator producing formatted identifiers (e.g., `SUB-202610-00101`).
- **Customer Association:** Linked to customer profile (Company, Contact Name, Email, Phone, Address, Tax ID).
- **Plan Association:** Selected tier (Starter, Professional, Enterprise, Custom Infrastructure) with billing cycles (Monthly, Quarterly, Annually).
- **Multi-Product Line Items:** Attached add-ons (Extra Team Seats, 1TB NVMe Storage, 24/7 SLA, Dedicated IP, SOC2 Audit Vault, API Burst Packs).
- **Correct Financial & Tax Calculations:**
  - Base plan subtotal & tax (standard 10%).
  - Line-by-line product calculations: `(Quantity * Unit Price) * (1 - Discount/100)`.
  - Individual tax rates (10%, 18%).
  - Strict mathematical rounding to 2 decimal places.
  - Net Subtotal, Total Taxes, and Total Invoiced Amount.
- **Dates & Terms:** Start Date, Expiry Date, Days Remaining countdown, Payment Terms (`Net 15`, `Net 30`, `Net 60`, `Due on Receipt`, `Prepaid`).

### 3. Dedicated User Interfaces
- **Subscriptions Dashboard (`/index.html`):**
  - KPI summary metric cards (Total, Active, Pipeline, MRR, Expired/Overdue).
  - Live search across subscription number, customer, plan, and product add-ons.
  - Filter tabs by status and dropdowns by plan, customer, payment terms, and expiry timeframe.
  - Auto-close trigger button with instant feedback.
- **Subscription Details Page (`/subscription-details.html`):**
  - Interactive visual lifecycle pipeline stepper.
  - Complete line items table with quantities, prices, taxes, and totals.
  - Customer contact and billing profile card.
  - Validity schedule with countdown days and renewal history counter.
  - Immutable audit trail and chronological activity log.
  - Printable invoice/quotation view.
- **Subscription Form (`/subscription-form.html`):**
  - Dynamic line item builder with live calculation updating as you type.
  - Customer and plan linkers with automatic base price and term population.
  - Expiry preset buttons (+30d, +90d, +365d) and auto-close toggle.

### 4. Role-Based Access Control (RBAC)
- **Fast Role Switcher** in the top navigation bar to test roles in real time:
  - 👑 **Administrator** (`Sarah Jenkins`): Full create, edit, pause, resume, renew, cancel, delete, and auto-close capabilities.
  - 💼 **Staff / Sales** (`Alex Rivera`): Full subscription management and status transitions.
  - 👤 **Customers** (`John Doe`, `Elena Rostova`, `David Kim`): Read-only access restricted strictly to their own company's subscriptions.

---

## 🚀 Running the Project

### Start the Server
```bash
# Using Node directly:
node server.js

# Or using batch file:
start.bat

# Or using PowerShell:
.\start.ps1
```

Once running, navigate to:
[http://localhost:3000](http://localhost:3000)

### Run Automated Tests
```bash
node --test tests/test_subscriptions.js
=======
<<<<<<< HEAD
# Subscription Management System

A full-featured **Subscription & Invoice Management System** built with Flask, SQLAlchemy, Bootstrap 5, and APScheduler.

---

## Features

### 📄 Invoice Management
| Feature | Description |
|---|---|
| Generate Invoices | Create invoices manually or auto-generate from subscriptions |
| View Invoices | Professional table with search, filter, and pagination |
| Confirm Invoices | Draft → Confirmed workflow |
| Mark as Paid | Confirmed → Paid workflow |
| Cancel Invoices | Cancel with reason (Draft or Confirmed only) |
| Print Invoices | Browser-printable invoice document |
| PDF Download | ReportLab-generated professional PDF |
| Send by Email | HTML email sent to customer via SMTP |
| Search & Filter | By invoice #, customer, product, status, date range |

### 🔄 Automatic Billing
- Generates invoices from **active subscriptions** when `next_billing_date <= today`
- Catches up **missed billing periods** (no skipped cycles)
- **Duplicate prevention**: checks `(subscription_id, billing_period_start)`
- Runs daily at midnight via **APScheduler**
- Can also be triggered manually from the UI

### 💰 Invoice Details
- Unique invoice number (`INV-YYYYMM-NNNNN`)
- Customer details (snapshot)
- Subscription number linkage
- Product name, description, quantity, unit price
- Discount (%)
- Tax (configurable via Admin → Tax Configuration)
- Subtotal, Tax Amount, Discount Amount, **Total Due**
- Invoice date & due date
- Full invoice history log

### 📊 Invoice Statuses
| Status | Description |
|---|---|
| **Draft** | Newly created, editable |
| **Confirmed** | Approved, ready to send |
| **Paid** | Payment received |
| **Cancelled** | Voided (with reason) |

### ⚙️ Admin
- **Tax Configuration**: Add/edit/delete named tax rates (GST, VAT, etc.)
- **Products**: Manage subscription products with pricing & billing cycles
- **Customers**: Full CRUD for customer records

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ · Flask 3 |
| Database | SQLite (SQLAlchemy ORM) |
| Frontend | Bootstrap 5.3 · Jinja2 |
| PDF | ReportLab |
| Email | Flask-Mail (SMTP) |
| Scheduler | APScheduler |

---

## Setup

### 1. Clone & Install

```bash
git clone <repo-url>
cd "Subscription Management System"

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
pip install python-dateutil
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your SMTP credentials and company details
```

### 3. Run

```bash
python app.py
```

Open http://localhost:5000 — the app auto-seeds demo data on first run.

---

## Project Structure

```
Subscription Management System/
├── app.py                   # Flask app factory + demo seed + scheduler
├── config.py                # Configuration from environment
├── extensions.py            # db, mail instances
├── requirements.txt
├── .env.example
├── models/
│   ├── customer.py          # Customer model
│   ├── product.py           # Product model
│   ├── subscription.py      # Subscription model (with billing cycle logic)
│   ├── invoice.py           # Invoice + InvoiceHistory models
│   └── tax_config.py        # Admin tax rate configuration
├── routes/
│   ├── invoices.py          # All invoice endpoints
│   ├── subscriptions.py     # Subscription CRUD
│   ├── customers.py         # Customer CRUD
│   └── admin.py             # Tax + Product admin
├── services/
│   ├── invoice_service.py   # Core invoice logic + DB transactions
│   ├── billing_service.py   # Auto billing scheduler
│   ├── email_service.py     # Email sending
│   └── pdf_service.py       # PDF generation (ReportLab)
├── templates/
│   ├── base.html
│   ├── invoices/            # list, detail, create, print, email
│   ├── subscriptions/       # list, detail, create
│   ├── customers/           # list, create, edit
│   └── admin/               # tax & product forms
└── static/
    ├── css/style.css
    └── js/main.js
=======
# Brightloop Software — Subscription Management System

A multi-tenant executive SaaS Subscription Management Platform built with **Python 3.13**, **Django 6.1**, **Bootstrap 5**, **Chart.js**, and **SQLite**.

---

## 👥 Four-Member Team Architecture

```text
Subscription Management System
├── Person 1: Authentication, Staff Management, Customer Profiles, Database Security
├── Person 2 (Implemented):
│   ├── Admin Dashboard (Real-time MRR, ARR, Churn, Chart.js telemetry)
│   ├── Product Management (SaaS offerings, categories, SKU tracking, lifecycle)
│   ├── Product Variants (Tiers, billing cycles, quotas, seat packs)
│   ├── Subscription Plan Management (Pricing models, trial periods, feature matrix)
│   ├── Search, Filtering & Pagination (Cross-catalog query preservation)
│   ├── Admin Settings (Global SaaS configuration, tax, currency, alerts)
│   ├── Data Export Interface (Streaming CSV & JSON data downloads)
│   └── Frontend UI/UX Enhancement (Modern SaaS design system, responsive layout)
├── Person 3: Subscription Management, Quotation Management, Customer Portal, Renewal Automation
└── Person 4: Invoice Management, Discount Management, Payment Gateways, Tax Configuration
>>>>>>> a68f587962c95873aa83cce70783dd32e74042d8
>>>>>>> 73a1cc59811d2d7386ebbce3f5c456242c4759b8
```

---

<<<<<<< HEAD
## 📁 Project Structure

```
subscription-management-system/
├── server.js                        # Node native HTTP server + REST API endpoints
├── package.json                     # Project manifest and test runner script
├── start.bat                        # Windows 1-click launch batch file
├── start.ps1                        # PowerShell launch script
├── README.md                        # Project documentation
├── data/
│   ├── database.json                # Seed database (Customers, Plans, Products, Subscriptions)
│   └── db.js                        # Business logic, state machine, financial engine, RBAC
├── public/
│   ├── index.html                   # Main Dashboard & Subscriptions list
│   ├── subscription-details.html    # Dedicated Subscription Details page
│   ├── subscription-form.html       # Create & Edit subscription wizard
│   ├── css/
│   │   ├── styles.css               # Clean SaaS design system & responsive styling
│   │   └── print.css                # Print/PDF invoice & quotation stylesheet
│   └── js/
│       ├── api.js                   # API client, auth session, and shared helpers
│       ├── app.js                   # Dashboard table, KPI, search, and filter controller
│       ├── details.js               # Details page controller and state actions
│       └── form.js                  # Line item builder and real-time calculator
└── tests/
    └── test_subscriptions.js        # Automated unit and integration test suite
```
=======
<<<<<<< HEAD
## Database Transactions

All state-changing operations use `db.session.begin()` context managers to ensure atomicity:
- `create_invoice()` — atomic invoice + history creation
- `confirm_invoice()` — atomic status update with history
- `mark_paid()` — atomic status update with history
- `cancel_invoice()` — atomic cancel + reason history
- `send_invoice_email()` — atomic email timestamp + history
- Auto-billing loop — each period's invoice + subscription date update is atomic

=======
## 🚀 Key Features Implemented (Person 2)

### 1. Executive Admin Dashboard
* **Real-time Financial Telemetry**: Dynamic calculations for **MRR (Monthly Recurring Revenue)**, **ARR (Annual Run Rate)**, Active Subscriptions, and Churn Rate.
* **Interactive Chart.js Visualizations**:
  * 6-Month Revenue Inflow & Growth Trend Area Chart (gradient fill).
  * Subscription Status Doughnut Chart (Active, Trialing, Past Due, Canceled).
  * Plan Popularity Bar Chart.
* **Live Activity Audit Feed**: Automatic logging of administrative actions across products, plans, settings, and exports.

### 2. Product & Variant Catalog
* Full CRUD for SaaS Products with category classification, SKU codes, description, and status tags (`Active`, `Draft`, `Archived`).
* Product Variants supporting **Standard**, **Pro**, and **Enterprise** tiers with custom resource quotas (max seats, storage in GB, daily API limits, and SLA response levels).

### 3. Subscription Plan Management & Comparison Matrix
* Plan configuration supporting recurring billing cycles (`Monthly`, `Quarterly`, `Annual`).
* Trial period configuration and setup fee customization.
* Granular **Plan Feature Entitlements** with quota values.
* Interactive side-by-side **Comparison Matrix** for plan tier evaluations.

### 4. Search, Multi-Filter & Reusable Pagination
* Live search by name, SKU, tagline, or description.
* Multi-select dropdown filters (Category, Tier, Billing Cycle, Status) and sorting options (Price, Date, Name).
* Reusable pagination component maintaining active query strings across page navigation.

### 5. Admin Settings Configuration
* Singleton configuration model for Company Branding, Support & Billing emails.
* Dynamic Currency symbols (`$`, `€`, `£`, `₹`) and default tax rate percentage.
* Lifecycle defaults (Trial days, grace periods, invoice prefixes).
* Operational toggles (Public signup, maintenance mode, notification triggers).

### 6. Data Export Interface
* Stream-generated file downloads for **Products**, **Variants**, **Plans**, **Subscriptions**, and **Customers**.
* Export formats supported: **CSV** (for Excel/Google Sheets) and **JSON** (for REST API ingestion).

---

## 🛠️ Technology Stack
* **Backend**: Python 3.13, Django 6.1
* **Frontend**: HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3.3, Bootstrap Icons
* **Charts & Analytics**: Chart.js 4.4.1
* **Database**: SQLite (relational schema coordinated with Persons 1, 3, and 4)

---

## 💻 Local Setup & Running

1. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Seed Database with Initial Records**:
   ```bash
   python manage.py seed_saas_data
   ```

4. **Run Unit Tests**:
   ```bash
   python manage.py test
   ```

5. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```
   Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
>>>>>>> a68f587962c95873aa83cce70783dd32e74042d8
>>>>>>> 73a1cc59811d2d7386ebbce3f5c456242c4759b8
