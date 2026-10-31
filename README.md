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
```

---

## Database Transactions

All state-changing operations use `db.session.begin()` context managers to ensure atomicity:
- `create_invoice()` — atomic invoice + history creation
- `confirm_invoice()` — atomic status update with history
- `mark_paid()` — atomic status update with history
- `cancel_invoice()` — atomic cancel + reason history
- `send_invoice_email()` — atomic email timestamp + history
- Auto-billing loop — each period's invoice + subscription date update is atomic
