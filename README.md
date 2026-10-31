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
```

---

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