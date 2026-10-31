# Subscription Management System - Brightloop Software

Enterprise-grade SaaS Subscription Management web application built with Django, Bootstrap 5, and SQLite for **Brightloop Software**.

---

## 🚀 Technologies
- **Backend**: Python 3.12+, Django 6.1+
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3.3, Bootstrap Icons 1.11.3
- **Database**: SQLite3 (Local development ready)
- **Design Language**: Modern SaaS Dashboard (Navy Blue, White, and Light Grey)

---

## 📁 Architecture & Apps

```
subscription_management/
├── config/                  # Core Django configuration & root URL router
├── accounts/                # Customer organizations & user profile management
├── products/                # Software products & feature definitions
├── plans/                   # Pricing tiers & billing frequencies
├── subscriptions/           # Active subscriptions & lifecycle management
├── billing/                 # Invoices, tax, and billing automation
├── payments/                # Payment gateway integration & audit logs
├── dashboard/               # Executive SaaS metrics (MRR, Churn, Active Subs)
├── templates/               # Reusable templates & modular components
│   ├── base.html            # Main base HTML template
│   ├── includes/            # Navbar, Sidebar, Messages, Footer partials
│   └── [app]/               # App-specific views
├── static/                  # Static assets (custom SaaS styles & scripts)
│   ├── css/style.css
│   ├── js/main.js
│   └── images/
├── media/                   # User and tenant uploaded files (invoices, logos)
├── manage.py                # Django CLI management script
└── db.sqlite3               # SQLite database
```

---

## 🛠️ Quick Start & Running the Server

### 1. Navigate to the project directory:
```bash
cd "C:\Users\Aman sony\.gemini\antigravity\scratch\subscription_management"
```

### 2. Run Database Migrations:
```bash
python manage.py migrate
```

### 3. Run Automated Foundation Tests:
```bash
python manage.py test
```

### 4. Start the Django Development Server:
```bash
python manage.py runserver
```

Open your browser and navigate to:
**`http://127.0.0.1:8000/`**
