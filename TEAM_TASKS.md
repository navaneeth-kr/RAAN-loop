# Brightloop Software — Subscription Management System
## Four-Person Team Collaboration Architecture (`TEAM_TASKS.md`)

This document defines the team responsibilities, shared data models, dependencies, integration contracts, and Git branch workflows for the **Brightloop Software Subscription Management System**.

---

### 1. Team Allocation & Responsibilities

| Team Member | Module & Responsibilities | Core Deliverables | Git Branch |
|---|---|---|---|
| **Person 1** | **Authentication, User Roles & Security** | • Django Custom Auth & Role-based Access Control (Admin, Staff, Customer)<br>• Staff Management (`/staff/`, provision, edit, toggle status)<br>• Customer Self-Service Registration (`/register/` with password strength rules)<br>• Customer Management (`/customers/`, 360° profile view with history tabs)<br>• Audit Logs & Activity Trail (`/audit-logs/`) | `person-1` |
| **Person 2** | **Catalog, Plans & Executive Dashboard** | • Executive KPI Dashboard (`/` with 6 metric cards & Chart.js charts)<br>• Product Management (`/products/`, type, cost/sale price, availability)<br>• Product Multi-tier Variants (`/variants/`, price modifiers)<br>• Subscription Plan Management (`/plans/`, 4 billing frequencies, renewal/pause/closure policies)<br>• Global Admin Settings (`/settings/`)<br>• Data Export & System Backup (`/exports/`) | `person-2` |
| **Person 3** | **Subscription Lifecycle & Customer Operations** | • Subscription Lifecycle Engine (`/subscriptions/`, draft, confirmed, active, paused, canceled, closed)<br>• Pause, Resume, Cancel with mandatory reason tracking<br>• Commercial Quotations (`/quotations/`, create, print proposal, 1-click convert)<br>• Customer Portal (`/portal/`, isolated dashboard, subscriptions, invoices, profile)<br>• Recurring Billing Automation (`python manage.py run_recurring_billing`)<br>• In-App Notifications (`/notifications/`, navbar badge)<br>• Email Dispatcher (`core/notifications.py`)<br>• Financial & Operational Reporting (`/reports/`) | `person-3` |
| **Person 4** | **Billing, Finance & Document Generation** | • Invoice Management (`/invoices/`, number formatting, calculation preview, mark paid)<br>• Discount Management (`/discounts/`, percentage/fixed, validity window, status toggle)<br>• Payment Management (`/payments/`, multiple gateways, auto-settlement, refund handling)<br>• Regional Tax Configuration (`/taxes/`, jurisdictional rules, default sync)<br>• ReportLab PDF Engine (`core/pdf_utils.py` for Invoices, Quotations, Receipts)<br>• Comprehensive Automated Testing & End-to-End Integration | `person-4` |

---

### 2. Shared Data Models & Dependency Map

All team members share a unified database schema located across modular Django apps:

```
[User (Django Auth)]
   │
   ├── (1-to-1) ──> [StaffProfile (core)]
   │                   Role: admin, billing_manager, sales_lead, support_lead
   │
   └── (1-to-1) ──> [Customer (subscriptions)]
                       Full Name, Email, Phone, Company, Address, Spend Metrics
                       │
                       ├── (1-to-Many) ──> [Subscription (subscriptions)]
                       │                      Plan, Variant, Qty, Amount, Dates, Status
                       │                      │
                       │                      └── (1-to-Many) ──> [Invoice (subscriptions)]
                       │                                             Amount, Tax, Discount, Total
                       │                                             │
                       │                                             └── (1-to-Many) ──> [Payment (subscriptions)]
                       │
                       └── (1-to-Many) ──> [Quotation (subscriptions)]
                                              Plan, Variant, Qty, Terms, Convert Target

[Product (products)] ── (1-to-Many) ──> [ProductVariant (products)]
   │
   └── (1-to-Many) ──> [SubscriptionPlan (plans)]
```

---

### 3. Git Workflow & Integration Instructions

1. **Main Branch Protection:**
   The `main` branch contains verified, production-ready, passing code.

2. **Feature Branching:**
   Each member works on their designated branch:
   ```bash
   git checkout -b person-1 origin/main  # Person 1
   git checkout -b person-2 origin/main  # Person 2
   git checkout -b person-3 origin/main  # Person 3
   git checkout -b person-4 origin/main  # Person 4
   ```

3. **Database Migration Rules:**
   - Coordinate model field changes before running `makemigrations`.
   - Never edit generated migration files manually once applied.
   - Always run test suite before merging into `main`.

4. **Integration Verification Command:**
   ```bash
   python manage.py test
   ```
