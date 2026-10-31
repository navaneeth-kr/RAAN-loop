# Brightloop Software — Subscription Management System

A subscription lifecycle management platform built with Python, Django, Bootstrap 5, and SQLite.

## Features

### Subscription Management
- Create, view, and edit subscriptions.
- Generate unique subscription numbers.
- Associate subscriptions with customers, plans, and products.
- Track subscription start dates, expiry dates, billing cycles, and payment terms.
- Support subscription statuses: Draft, Quotation, Confirmed, Active, and Closed.
- Pause, resume, renew, and cancel subscriptions.
- Search, filter, and paginate subscription records.
- Track subscription activity and renewal history.

### Quotation Management
- Create quotations for customers.
- Associate quotations with subscription plans and products.
- Track quotation status and customer approval.

### Customer Portal
- Allow customers to view their own subscription information.
- Restrict customer access to their own company's records.

### Invoices and Payments
- Generate and manage invoices.
- Track invoice status and payment information.
- Configure taxes and discounts.
- Support invoice history and PDF generation where implemented.

### Dashboard and Administration
- Dashboard with subscription and revenue metrics.
- Product, product variant, and subscription plan management.
- Search, filtering, and pagination.
- Administrative settings and data export.

## Team Architecture

- **Person 1:** Authentication, staff management, customer profiles, and database security.
- **Person 2:** Dashboard, products, product variants, plans, settings, search, and data export.
- **Person 3:** Subscription management, quotations, customer portal, notifications, and renewal automation.
- **Person 4:** Invoice management, discounts, payments, and tax configuration.

## Technology Stack

- **Backend:** Python and Django
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Database:** SQLite
- **Charts:** Chart.js

## Setup and Running

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Apply database migrations

```powershell
python manage.py migrate
```

### 4. Run tests

```powershell
python manage.py test
```

### 5. Start the development server

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

## Project Notes

- Keep environment variables and secrets out of Git.
- Coordinate database models and migrations across team members.
- Run tests before merging changes.
- Use feature branches and pull requests when possible to avoid conflicts.