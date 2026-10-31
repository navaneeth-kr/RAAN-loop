# Brightloop Software — Enterprise Subscription Management System

A multi-tenant, full-featured executive SaaS Subscription Management Platform built with **Python**, **Django**, **Bootstrap 5**, **Chart.js**, **ReportLab**, and **SQLite**.

Designed and implemented in accordance with the Brightloop Software Master Architectural Specification across all 4 collaborative engineering domains.

---

## 👥 Four-Member Team Collaboration & Architecture

```text
Brightloop Subscription Management System
├── Person 1: Authentication, Staff Management, Customer 360 Profiles, Audit Logs & Security
├── Person 2: Executive Admin Dashboard, Product Catalog, Multi-Tier Variants, Plan Management, Settings, Exports
├── Person 3: Subscription Lifecycle, Commercial Quotations, Customer Portal, Billing Automation, Notifications, Reports
└── Person 4: Invoicing Engine, Discounts, Multi-Gateway Payments, Tax Configuration, PDF Document Generation
```

### 1. Person 1 — Authentication, Users & Security
- **Role-based Access Control (RBAC)**: Distinct access tiers for Super Administrators, Staff Members, and Customers.
- **Customer Self-Service Registration** (`/register/`): Enforces email uniqueness and strong password validation (>8 characters, uppercase, lowercase, special character).
- **Staff Provisioning** (`/staff/`): Create staff accounts, assign operational roles, edit details, and toggle active status.
- **Customer Profile 360° Management** (`/customers/`): Full customer CRUD with tabbed history for Subscriptions, Invoices, Payments, and Quotations.
- **System Audit Logs** (`/audit-logs/`): Real-time tamper-evident audit trail capturing security events, billing transactions, and data mutations.

### 2. Person 2 — Products, Plans & Administration
- **Executive Admin Dashboard** (`/`): Real-time MRR, ARR, active contracts, and interactive Chart.js revenue telemetry.
- **Product Catalog & Multi-Tier Variants** (`/products/`, `/variants/`): Base SaaS products with add-ons and brand variants.
- **Subscription Plan Management** (`/plans/`): Daily, weekly, monthly, and yearly frequencies with pause, renewal, and cancellation policies.
- **System Settings** (`/settings/`): Global configuration for company branding, currency symbols, and notification triggers.
- **Data Export & Backup Center** (`/exports/`): Streaming CSV & JSON data downloads plus full SQLite binary snapshot backups.

### 3. Person 3 — Subscriptions, Quotations & Customer Portal
- **Subscription Lifecycle Management** (`/subscriptions/`): Draft, confirmed, active, paused, canceled, and closed states.
- **Lifecycle Actions**: Pause (with plan policy checks), Resume, Cancel, and Manual Renewal.
- **Commercial Quotations** (`/quotations/`): Sales proposals with validity tracking and **1-click conversion** to active subscriptions and initial invoices.
- **Isolated Customer Portal** (`/portal/`): Dedicated customer self-service dashboard with subscriptions, invoices, payment history, and profile editing.
- **Recurring Billing Automation**: Independent Django command (`python manage.py run_recurring_billing`) with duplicate prevention and automated billing cycle advances.
- **Notifications**: In-app alert dropdown with unread badge counter (`/notifications/`) and SMTP/console email dispatching.
- **Reporting Suite** (`/reports/`): Period revenue, YTD revenue, churn analysis, overdue invoice aging, and CSV export.

### 4. Person 4 — Billing, Finance & PDF Engine
- **Invoice Management** (`/invoices/`): Automated number formatting (`INV-YYYYMM-XXXX`), dynamic calculation previews, due date tracking, and settlement.
- **Discount Management** (`/discounts/`): Percentage and fixed amount promo codes with validity windows and usage counters.
- **Payment Gateway Management** (`/payments/`): Multi-gateway support (Stripe, PayPal, Credit Card, Wire, UPI) with automatic invoice reconciliation and refund handling.
- **Regional Tax Configuration** (`/taxes/`): Jurisdictional tax rates with automatic default rate synchronization.
- **ReportLab PDF Generation**: Print-ready, executive PDF generation for Invoices (`/invoices/<id>/pdf/`), Quotations (`/quotations/<id>/pdf/`), and Payment Receipts (`/payments/<id>/pdf/`).

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13, Django 6.1
- **Database**: SQLite3 (Production-ready relational schema)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3.3, Bootstrap Icons
- **PDF Engine**: ReportLab 5.1
- **Charts & Visualization**: Chart.js 4.4.1
- **Automated Tasks**: Django Management Commands (`run_recurring_billing`, `seed_saas_data`)

---

## 💻 Installation & Local Setup

### 1. Clone & Activate Virtual Environment
```bash
git clone https://github.com/navaneeth-kr/RAAN-loop.git
cd Subscription_Management_System
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows
# source .venv/bin/activate    # On Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Apply Database Migrations
```bash
python manage.py migrate
```

### 4. Populate Database with Enterprise Demonstration Data
```bash
python manage.py seed_saas_data
```

### 5. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 6. Run Automated Test Suite
```bash
python manage.py test
```

### 7. Start Local Development Server
```bash
python manage.py runserver
```
Navigate to:
- **Admin Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Customer Portal**: [http://127.0.0.1:8000/portal/](http://127.0.0.1:8000/portal/)
- **Sign In / Demo Login**: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- **Customer Registration**: [http://127.0.0.1:8000/register/](http://127.0.0.1:8000/register/)

---

## 🤖 Recurring Billing Automation Command

Execute the automated billing engine at any time (or configure via Cron / Windows Task Scheduler):
```bash
# Dry run simulation (safe preview)
python manage.py run_recurring_billing --dry-run

# Execute live billing cycle
python manage.py run_recurring_billing
```

---

## 🌿 Git Branch Workflow for Team Members

Collaborative Git branches are structured as:
```bash
# Person 1: Authentication & Security
git checkout -b person-1 origin/main

# Person 2: Catalog & Dashboard
git checkout -b person-2 origin/main

# Person 3: Subscriptions & Portal
git checkout -b person-3 origin/main

# Person 4: Billing & Finance
git checkout -b person-4 origin/main
```
All feature branches merge directly into `main` after passing `python manage.py test`.

---

## 🔒 Security & Best Practices

- Django password hashing using PBKDF2 with SHA256.
- Role-based authorization mixins enforcing strict customer isolation.
- Automatic activity audit trails and CSRF protection.
- Environment variables configured via `.env` (template in `.env.example`).
