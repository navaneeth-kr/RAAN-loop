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
```

---

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
