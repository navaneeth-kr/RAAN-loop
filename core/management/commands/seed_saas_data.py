from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import SystemSetting, ActivityLog, StaffProfile
from products.models import ProductCategory, Product, ProductVariant
from plans.models import SubscriptionPlan, PlanFeature
from subscriptions.models import Customer, Subscription, Invoice, Payment, Quotation, Discount, TaxRate

class Command(BaseCommand):
    help = "Seeds initial realistic SaaS records for Brightloop Software"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Brightloop SaaS database...")

        # 0. Admin Superuser & Staff
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@brightloop.io",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Alexander",
                "last_name": "Pierce",
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
        
        StaffProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                "role": "admin",
                "department": "Executive Leadership",
                "phone": "+1-800-555-0100"
            }
        )

        staff_data = [
            ("sarah_billing", "sarah@brightloop.io", "Sarah", "Connor", "billing_manager", "Finance & Invoicing", "+1-800-555-0101"),
            ("john_sales", "john@brightloop.io", "John", "Miller", "sales_lead", "Enterprise Sales", "+1-800-555-0102"),
            ("emily_support", "emily@brightloop.io", "Emily", "Watson", "support_lead", "Customer Success", "+1-800-555-0103"),
        ]
        for uname, email, fname, lname, role, dept, ph in staff_data:
            u, _ = User.objects.get_or_create(
                username=uname,
                defaults={"email": email, "first_name": fname, "last_name": lname, "is_staff": True}
            )
            u.set_password("staff123")
            u.save()
            StaffProfile.objects.get_or_create(user=u, defaults={"role": role, "department": dept, "phone": ph})

        self.stdout.write("  [OK] Admin and Staff accounts verified")

        # 1. System Settings
        settings, _ = SystemSetting.objects.get_or_create(id=1)
        settings.company_name = "Brightloop Software"
        settings.support_email = "support@brightloop.io"
        settings.billing_email = "billing@brightloop.io"
        settings.currency_code = "INR"
        settings.currency_symbol = "₹"
        settings.tax_rate = Decimal('18.00')
        settings.default_trial_days = 14
        settings.grace_period_days = 7
        settings.invoice_prefix = "BL-INV-"
        settings.save()
        self.stdout.write("  [OK] System Settings verified (Currency: INR)")

        # 2. Product Categories
        cat_erp, _ = ProductCategory.objects.get_or_create(
            name="Enterprise Applications",
            defaults={"icon": "bi-building-gear", "description": "Enterprise software packages, modular ERP, and business management."}
        )
        cat_sec, _ = ProductCategory.objects.get_or_create(
            name="Cloud Security",
            defaults={"icon": "bi-shield-check", "description": "Continuous cloud perimeter protection, compliance, and threat mitigation."}
        )
        cat_tel, _ = ProductCategory.objects.get_or_create(
            name="Observability & Telemetry",
            defaults={"icon": "bi-activity", "description": "Real-time logging, metrics aggregation, and application tracing."}
        )
        cat_ai, _ = ProductCategory.objects.get_or_create(
            name="AI & Automation",
            defaults={"icon": "bi-robot", "description": "Agentic AI workflows, LLM orchestration, and smart automation pipelines."}
        )
        cat_api, _ = ProductCategory.objects.get_or_create(
            name="Developer Platforms",
            defaults={"icon": "bi-code-slash", "description": "High-throughput API gateways and developer toolkit SDKs."}
        )

        # 3. SaaS Products
        # USER SPECIFICATION FLAGSHIP: Software Package (Base price: ₹500)
        p_pkg, _ = Product.objects.update_or_create(
            sku="BL-SW-PKG-01",
            defaults={
                "name": "Software Package",
                "product_type": "software",
                "category": cat_erp,
                "selling_price": Decimal("500.00"),
                "cost_price": Decimal("250.00"),
                "tagline": "Modular enterprise business software suite",
                "description": "Comprehensive enterprise business software package with modular ERP, CRM, inventory, and automated billing capabilities.",
                "notes": "Flagship offering. Base price ₹500. Variants: Standard (+₹0), Odoo (+₹560), Premium (+₹1,000).",
                "status": "active",
                "is_featured": True,
            }
        )

        p1, _ = Product.objects.update_or_create(
            sku="BL-CSS-01",
            defaults={
                "name": "Cloud Sentinel Suite",
                "product_type": "saas",
                "category": cat_sec,
                "tagline": "Realtime enterprise vulnerability scanning and multi-cloud perimeter security",
                "description": "Cloud Sentinel provides automated real-time compliance monitoring, vulnerability assessment, and threat neutralization across AWS, Azure, and Google Cloud environments.",
                "selling_price": Decimal("49.00"),
                "cost_price": Decimal("18.00"),
                "notes": "Includes multi-cloud IAM scanning and automated SOC2 reports.",
                "status": "active",
                "is_featured": True,
            }
        )

        p2, _ = Product.objects.update_or_create(
            sku="BL-DTE-02",
            defaults={
                "name": "DataPulse Telemetry Engine",
                "product_type": "saas",
                "category": cat_tel,
                "tagline": "Unified log ingestion, distributed tracing, and synthetic monitoring",
                "description": "High-performance telemetry engine capable of streaming up to 2 million events per second with instant anomaly detection and OpenTelemetry native integration.",
                "selling_price": Decimal("29.00"),
                "cost_price": Decimal("10.00"),
                "notes": "High ingestion throughput node.",
                "status": "active",
                "is_featured": False,
            }
        )

        p3, _ = Product.objects.update_or_create(
            sku="BL-AIW-03",
            defaults={
                "name": "BrightAI Workspace",
                "product_type": "software",
                "category": cat_ai,
                "tagline": "Agentic AI assistants and autonomous business workflow agents",
                "description": "Empower your product and engineering teams with collaborative autonomous agents for code review, data synthesis, and customer operations.",
                "selling_price": Decimal("79.00"),
                "cost_price": Decimal("35.00"),
                "notes": "Includes LLM gateway and agent sandboxes.",
                "status": "active",
                "is_featured": True,
            }
        )

        p4, _ = Product.objects.update_or_create(
            sku="BL-AGF-04",
            defaults={
                "name": "API Gateway Flow",
                "product_type": "addon",
                "category": cat_api,
                "tagline": "Ultra-low-latency edge microservices proxy with built-in rate limiting",
                "description": "Sub-millisecond API proxy offering declarative route policies, OAuth2 token enforcement, mTLS termination, and dynamic request transformation.",
                "selling_price": Decimal("19.00"),
                "cost_price": Decimal("6.00"),
                "notes": "Distributed Envoy proxy module.",
                "status": "active",
                "is_featured": False,
            }
        )
        self.stdout.write("  [OK] Products created (including Software Package at Rs.500)")

        # 4. Product Variants
        # USER SPECIFICATION: Standard (₹0 surcharge), Odoo (₹560 surcharge), Premium (₹1000 surcharge)
        v_std, _ = ProductVariant.objects.update_or_create(
            sku="VAR-SW-STD-01",
            defaults={
                "product": p_pkg,
                "name": "Standard",
                "tier": "standard",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("0.00"),
                "max_users": 5,
                "storage_gb": 50,
                "api_rate_limit": 10000,
                "sla_support_level": "Standard Support (24h)",
                "description": "Standard edition with ₹0 additional charge. Final price: ₹500.",
                "is_active": True,
            }
        )

        v_odoo, _ = ProductVariant.objects.update_or_create(
            sku="VAR-SW-ODOO-02",
            defaults={
                "product": p_pkg,
                "name": "Odoo",
                "tier": "odoo",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("560.00"),
                "max_users": 15,
                "storage_gb": 150,
                "api_rate_limit": 50000,
                "sla_support_level": "Priority Support (8h)",
                "description": "Odoo edition with ₹560 additional charge. Final price: ₹1,060.",
                "is_active": True,
            }
        )

        v_prem, _ = ProductVariant.objects.update_or_create(
            sku="VAR-SW-PREM-03",
            defaults={
                "product": p_pkg,
                "name": "Premium",
                "tier": "premium",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("1000.00"),
                "max_users": 50,
                "storage_gb": 500,
                "api_rate_limit": 200000,
                "sla_support_level": "Dedicated Account Manager (1h SLA)",
                "description": "Premium enterprise edition with ₹1,000 additional charge. Final price: ₹1,500.",
                "is_active": True,
            }
        )

        v1_std, _ = ProductVariant.objects.update_or_create(
            sku="VAR-CSS-STD-MO",
            defaults={
                "product": p1,
                "name": "Standard Cloud (Monthly)",
                "tier": "standard",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("0.00"),
                "max_users": 5,
                "storage_gb": 50,
                "api_rate_limit": 25000,
                "sla_support_level": "Standard Email (24h)",
            }
        )
        v1_pro, _ = ProductVariant.objects.update_or_create(
            sku="VAR-CSS-PRO-MO",
            defaults={
                "product": p1,
                "name": "Professional Dedicated (Monthly)",
                "tier": "odoo",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("80.00"),
                "max_users": 20,
                "storage_gb": 250,
                "api_rate_limit": 100000,
                "sla_support_level": "Priority Slack & Phone (4h)",
            }
        )
        v1_ent, _ = ProductVariant.objects.update_or_create(
            sku="VAR-CSS-ENT-YR",
            defaults={
                "product": p1,
                "name": "Enterprise Cluster (Annual)",
                "tier": "premium",
                "billing_cycle": "annual",
                "additional_charge": Decimal("1141.00"),
                "max_users": 100,
                "storage_gb": 1000,
                "api_rate_limit": 500000,
                "sla_support_level": "Dedicated Solutions Engineer (1h SLA)",
            }
        )

        v3_pro, _ = ProductVariant.objects.update_or_create(
            sku="VAR-AIW-PRO-MO",
            defaults={
                "product": p3,
                "name": "Pro Agent Pack (Monthly)",
                "tier": "odoo",
                "billing_cycle": "monthly",
                "additional_charge": Decimal("20.00"),
                "max_users": 10,
                "storage_gb": 100,
                "api_rate_limit": 50000,
                "sla_support_level": "Priority Email & Chat",
            }
        )
        self.stdout.write("  [OK] Product Variants created (Standard +0, Odoo +560, Premium +1000)")

        # 5. Subscription Plans
        plan_sw_std, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SW-STD-500",
            defaults={
                "product": p_pkg,
                "variant": v_std,
                "name": "Software Package (Standard)",
                "tier": "starter",
                "billing_cycle": "monthly",
                "price": Decimal("500.00"),
                "min_quantity": 1,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": True,
                "allow_pausing": True,
                "allow_renewal": True,
                "trial_days": 14,
                "status": "active",
                "is_featured": False,
                "sort_order": 0,
                "description": "Standard software package offering with monthly billing and 1-seat minimum."
            }
        )
        plan_sw_odoo, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SW-ODOO-1060",
            defaults={
                "product": p_pkg,
                "variant": v_odoo,
                "name": "Software Package (Odoo Edition)",
                "tier": "growth",
                "billing_cycle": "monthly",
                "price": Decimal("1060.00"),
                "min_quantity": 1,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": True,
                "allow_pausing": True,
                "allow_renewal": True,
                "trial_days": 14,
                "status": "active",
                "is_featured": True,
                "sort_order": 1,
                "description": "Odoo edition with ERP module attachments and priority SLA."
            }
        )
        plan_sw_prem, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SW-PREM-1500",
            defaults={
                "product": p_pkg,
                "variant": v_prem,
                "name": "Software Package (Premium Monthly)",
                "tier": "enterprise",
                "billing_cycle": "monthly",
                "price": Decimal("1500.00"),
                "min_quantity": 2,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": False,
                "allow_pausing": True,
                "allow_renewal": True,
                "trial_days": 30,
                "status": "active",
                "is_featured": True,
                "sort_order": 2,
                "description": "Enterprise software tier with dedicated support and 2-seat minimum."
            }
        )
        plan_sw_yr, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SW-PREM-YR",
            defaults={
                "product": p_pkg,
                "variant": v_prem,
                "name": "Software Package (Annual Enterprise)",
                "tier": "enterprise",
                "billing_cycle": "yearly",
                "price": Decimal("15000.00"),
                "min_quantity": 5,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": False,
                "allow_pausing": False,
                "allow_renewal": True,
                "trial_days": 30,
                "status": "active",
                "is_featured": False,
                "sort_order": 3,
                "description": "Yearly enterprise commitment with 5-seat minimum and volume savings."
            }
        )

        # Daily Billing Frequency Plan
        plan_daily, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-DAILY-API",
            defaults={
                "product": p4,
                "name": "API Gateway (Daily Pass)",
                "tier": "starter",
                "billing_cycle": "daily",
                "price": Decimal("50.00"),
                "min_quantity": 1,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": True,
                "allow_pausing": False,
                "allow_renewal": True,
                "trial_days": 0,
                "status": "active",
                "is_featured": False,
                "sort_order": 4,
                "description": "On-demand daily compute burst pass for peak traffic events."
            }
        )

        # Weekly Billing Frequency Plan
        plan_weekly, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-WEEKLY-DP",
            defaults={
                "product": p2,
                "name": "DataPulse (Weekly Sprint)",
                "tier": "growth",
                "billing_cycle": "weekly",
                "price": Decimal("200.00"),
                "min_quantity": 2,
                "start_date": timezone.now().date(),
                "end_date": None,
                "auto_close": False,
                "allow_early_cancellation": True,
                "allow_pausing": True,
                "allow_renewal": True,
                "trial_days": 3,
                "status": "active",
                "is_featured": False,
                "sort_order": 5,
                "description": "Weekly telemetry sprint package for project-based engineering teams."
            }
        )

        plan1, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SENTINEL-STARTER",
            defaults={
                "product": p1,
                "variant": v1_std,
                "name": "Sentinel Starter",
                "tier": "starter",
                "billing_cycle": "monthly",
                "price": Decimal("49.00"),
                "min_quantity": 1,
                "start_date": timezone.now().date(),
                "trial_days": 14,
                "status": "active",
                "is_featured": False,
                "sort_order": 6,
            }
        )
        plan2, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SENTINEL-GROWTH",
            defaults={
                "product": p1,
                "variant": v1_pro,
                "name": "Sentinel Growth Pro",
                "tier": "growth",
                "billing_cycle": "monthly",
                "price": Decimal("129.00"),
                "min_quantity": 1,
                "start_date": timezone.now().date(),
                "trial_days": 14,
                "status": "active",
                "is_featured": True,
                "sort_order": 7,
            }
        )
        plan3, _ = SubscriptionPlan.objects.update_or_create(
            code="PLAN-SENTINEL-ENTERPRISE",
            defaults={
                "product": p1,
                "variant": v1_ent,
                "name": "Sentinel Enterprise",
                "tier": "enterprise",
                "billing_cycle": "yearly",
                "price": Decimal("1190.00"),
                "min_quantity": 10,
                "start_date": timezone.now().date(),
                "trial_days": 30,
                "status": "active",
                "is_featured": False,
                "sort_order": 8,
            }
        )
        plan4 = plan_daily
        plan5 = plan_weekly
        self.stdout.write("  [OK] Subscription Plans created (Daily, Weekly, Monthly, Yearly)")

        # 6. Customers
        customers_data = [
            ("Apex Health Systems", "Dr. Marcus Vance", "mvance@apexhealth.org", "+1-555-0192", "United States"),
            ("NovaTech Labs", "Elena Rostova", "elena@novatech.io", "+44-20-7946-0912", "United Kingdom"),
            ("Meridian Fintech", "Liam Gallagher", "lgallagher@meridianpay.com", "+1-415-555-2671", "United States"),
            ("CloudScale Corp", "Kenji Takahashi", "kenji@cloudscale.jp", "+81-3-5555-0143", "Japan"),
            ("Vertex Logistics", "Sofia Alvarez", "sofia@vertexlogistics.de", "+49-30-555-0188", "Germany"),
            ("BlueWave Solutions", "David Chen", "david.chen@bluewave.com", "+1-206-555-0129", "United States"),
            ("Aura Dynamics", "Rachel Green", "rachel@auradynamics.co", "+1-617-555-0174", "United States"),
            ("Starlight Interactive", "Priya Sharma", "priya@starlightgames.in", "+91-80-5555-0199", "India"),
        ]

        created_customers = []
        for company, name, email, phone, country in customers_data:
            c, _ = Customer.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": name,
                    "company_name": company,
                    "phone": phone,
                    "country": country,
                    "status": "active"
                }
            )
            created_customers.append(c)
        self.stdout.write("  [OK] Customers verified")

        # 7. Subscriptions
        today = timezone.now().date()
        subs_spec = [
            ("SUB-1001", created_customers[0], plan2, v1_pro, "active", plan2.price, today - timedelta(days=90), today + timedelta(days=30)),
            ("SUB-1002", created_customers[1], plan3, v1_ent, "active", plan3.price, today - timedelta(days=120), today + timedelta(days=245)),
            ("SUB-1003", created_customers[2], plan5, v3_pro, "active", plan5.price, today - timedelta(days=45), today + timedelta(days=15)),
            ("SUB-1004", created_customers[3], plan1, v1_std, "active", plan1.price, today - timedelta(days=20), today + timedelta(days=10)),
            ("SUB-1005", created_customers[4], plan5, v3_pro, "trialing", Decimal("0.00"), today - timedelta(days=5), today + timedelta(days=9)),
            ("SUB-1006", created_customers[5], plan2, v1_pro, "past_due", plan2.price, today - timedelta(days=60), today - timedelta(days=3)),
            ("SUB-1007", created_customers[6], plan4, None, "active", plan4.price, today - timedelta(days=15), today + timedelta(days=15)),
            ("SUB-1008", created_customers[7], plan1, v1_std, "canceled", plan1.price, today - timedelta(days=180), today - timedelta(days=60)),
        ]

        created_subs = []
        for sid, cust, pln, var, status, amt, s_date, n_date in subs_spec:
            sub, _ = Subscription.objects.get_or_create(
                subscription_id=sid,
                defaults={
                    "customer": cust,
                    "plan": pln,
                    "variant": var,
                    "status": status,
                    "billing_cycle": pln.billing_cycle,
                    "current_amount": amt if amt > 0 else pln.price,
                    "start_date": s_date,
                    "next_billing_date": n_date,
                    "auto_renew": status == "active",
                }
            )
            created_subs.append(sub)
        self.stdout.write("  [OK] Subscriptions verified")

        # 7b. Tax Rates
        tax_rates_spec = [
            ("Standard GST", Decimal("18.00"), "Standard 18% Goods & Services Tax", True),
            ("European Union VAT", Decimal("20.00"), "Standard EU cross-border value added tax", False),
            ("US State Sales Tax", Decimal("8.25"), "Standard US state & local nexus sales tax", False),
            ("Zero-Rated Export", Decimal("0.00"), "Tax-exempt international B2B digital export", False),
        ]
        created_taxes = {}
        for tname, trate, tdesc, tdef in tax_rates_spec:
            tr, _ = TaxRate.objects.get_or_create(
                name=tname,
                defaults={
                    "rate_percent": trate,
                    "description": tdesc,
                    "is_default": tdef,
                    "is_active": True,
                }
            )
            created_taxes[tname] = tr
        self.stdout.write("  [OK] Tax Rates configured")

        # 8. Invoices (Paid, Pending, and OVERDUE)
        default_tax = created_taxes.get("Standard GST")

        invoices_spec = [
            ("BL-INV-2026-001", created_customers[0], created_subs[0], Decimal("129.00"), "paid", today - timedelta(days=90), today - timedelta(days=60)),
            ("BL-INV-2026-002", created_customers[0], created_subs[0], Decimal("129.00"), "paid", today - timedelta(days=60), today - timedelta(days=30)),
            ("BL-INV-2026-003", created_customers[0], created_subs[0], Decimal("129.00"), "paid", today - timedelta(days=30), today),
            ("BL-INV-2026-004", created_customers[1], created_subs[1], Decimal("1190.00"), "paid", today - timedelta(days=120), today - timedelta(days=90)),
            ("BL-INV-2026-005", created_customers[2], created_subs[2], Decimal("99.00"), "paid", today - timedelta(days=45), today - timedelta(days=15)),
            ("BL-INV-2026-006", created_customers[2], created_subs[2], Decimal("99.00"), "paid", today - timedelta(days=15), today + timedelta(days=15)),
            ("BL-INV-2026-007", created_customers[3], created_subs[3], Decimal("49.00"), "paid", today - timedelta(days=20), today + timedelta(days=10)),
            ("BL-INV-2026-008", created_customers[6], created_subs[6], Decimal("29.00"), "paid", today - timedelta(days=15), today + timedelta(days=15)),
            # OVERDUE INVOICES (Explicitly past due)
            ("BL-INV-2026-009", created_customers[5], created_subs[5], Decimal("129.00"), "overdue", today - timedelta(days=40), today - timedelta(days=10)),
            ("BL-INV-2026-010", created_customers[7], created_subs[7], Decimal("147.00"), "overdue", today - timedelta(days=50), today - timedelta(days=20)),
            # PENDING INVOICE
            ("BL-INV-2026-011", created_customers[4], created_subs[4], Decimal("99.00"), "pending", today - timedelta(days=2), today + timedelta(days=12)),
        ]

        created_invoices = []
        for inv_num, cust, sub, amt, inv_status, idate, ddate in invoices_spec:
            tax = round(amt * Decimal('0.18'), 2)
            total = amt + tax
            inv, _ = Invoice.objects.get_or_create(
                invoice_number=inv_num,
                defaults={
                    "customer": cust,
                    "subscription": sub,
                    "amount": amt,
                    "tax_rate": default_tax,
                    "tax_amount": tax,
                    "total_amount": total,
                    "status": inv_status,
                    "issued_date": idate,
                    "due_date": ddate,
                    "paid_at": timezone.now() if inv_status == 'paid' else None,
                }
            )
            created_invoices.append(inv)
        self.stdout.write("  [OK] Invoices created (including Overdue & Pending)")

        # 9. Payments (Completed, Pending, Failed)
        payments_data = [
            ("PAY-1001", created_customers[0], created_invoices[0], Decimal("152.22"), "credit_card", "completed", "txn_stripe_9901", timezone.now() - timedelta(days=90)),
            ("PAY-1002", created_customers[0], created_invoices[1], Decimal("152.22"), "credit_card", "completed", "txn_stripe_9902", timezone.now() - timedelta(days=60)),
            ("PAY-1003", created_customers[1], created_invoices[3], Decimal("1404.20"), "bank_transfer", "completed", "wire_ref_44819", timezone.now() - timedelta(days=120)),
            ("PAY-1004", created_customers[2], created_invoices[4], Decimal("116.82"), "paypal", "completed", "pp_order_7718", timezone.now() - timedelta(days=45)),
            ("PAY-1005", created_customers[3], created_invoices[6], Decimal("57.82"), "credit_card", "completed", "txn_stripe_9905", timezone.now() - timedelta(days=20)),
            ("PAY-1006", created_customers[6], created_invoices[7], Decimal("34.22"), "credit_card", "completed", "txn_stripe_9906", timezone.now() - timedelta(days=15)),
            # PENDING PAYMENTS (Pending payment queue)
            ("PAY-1007", created_customers[4], created_invoices[10], Decimal("116.82"), "stripe", "pending", "auth_hold_8819", timezone.now() - timedelta(hours=6)),
            ("PAY-1008", created_customers[5], created_invoices[8], Decimal("152.22"), "bank_transfer", "pending", "pending_ach_001", timezone.now() - timedelta(hours=14)),
        ]

        for pid, cust, inv, amt, method, p_status, tx_ref, p_date in payments_data:
            Payment.objects.get_or_create(
                payment_id=pid,
                defaults={
                    "customer": cust,
                    "invoice": inv,
                    "amount": amt,
                    "payment_method": method,
                    "status": p_status,
                    "transaction_reference": tx_ref,
                    "payment_date": p_date,
                }
            )
        self.stdout.write("  [OK] Payments created (Completed and Pending)")

        # 10. Quotations
        quotations_data = [
            ("QT-2026-001", created_customers[0], plan3, Decimal("9500.00"), "sent", today + timedelta(days=14), "Enterprise multi-region discount applied."),
            ("QT-2026-002", created_customers[1], plan2, Decimal("1200.00"), "accepted", today + timedelta(days=5), "Custom SLA add-on included."),
            ("QT-2026-003", created_customers[2], plan5, Decimal("3500.00"), "draft", today + timedelta(days=30), "Annual AI seat bundle quotation."),
        ]
        for qnum, cust, pln, tot, q_status, v_until, notes in quotations_data:
            Quotation.objects.get_or_create(
                quotation_number=qnum,
                defaults={
                    "customer": cust,
                    "plan": pln,
                    "total_amount": tot,
                    "status": q_status,
                    "valid_until": v_until,
                    "notes": notes,
                }
            )
        self.stdout.write("  [OK] Quotations created")

        # 11. Discounts
        discounts_data = [
            ("LAUNCH20", "20% Off Launch Special", "percentage", Decimal("20.00"), today - timedelta(days=30), today + timedelta(days=60), True, 18),
            ("STARTUP50", "Startup Tier Fixed $50 Off", "fixed", Decimal("50.00"), today - timedelta(days=10), today + timedelta(days=90), True, 7),
            ("ANNUALPROMO", "15% Off Annual Commitment", "percentage", Decimal("15.00"), today - timedelta(days=60), today + timedelta(days=120), True, 24),
        ]
        for code, desc, dtype, val, vfrom, vuntil, act, used in discounts_data:
            Discount.objects.get_or_create(
                code=code,
                defaults={
                    "description": desc,
                    "discount_type": dtype,
                    "value": val,
                    "valid_from": vfrom,
                    "valid_until": vuntil,
                    "is_active": act,
                    "times_used": used,
                }
            )
        self.stdout.write("  [OK] Discounts created")

        # 12. Initial Audit Logs
        logs = [
            ("System Admin Alexander Pierce signed in to Executive Console", "system"),
            ("Processed automatic recurring billing run for 8 accounts", "setting"),
            ("Flagged 2 overdue invoices past net-30 terms", "setting"),
            ("Exported financial performance quarterly summary", "export"),
        ]
        for act, cat in logs:
            ActivityLog.objects.get_or_create(action=act, defaults={"category": cat})

        self.stdout.write(self.style.SUCCESS("Brightloop SaaS database successfully seeded with complete relational records!"))
