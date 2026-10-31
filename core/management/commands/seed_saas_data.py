from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import SystemSetting, ActivityLog
from products.models import ProductCategory, Product, ProductVariant
from plans.models import SubscriptionPlan, PlanFeature
from subscriptions.models import Customer, Subscription, Invoice

class Command(BaseCommand):
    help = "Seeds initial realistic SaaS records for Brightloop Software"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Brightloop SaaS database...")

        # 1. System Settings
        settings, _ = SystemSetting.objects.get_or_create(id=1)
        settings.company_name = "Brightloop Software"
        settings.support_email = "support@brightloop.io"
        settings.billing_email = "billing@brightloop.io"
        settings.currency_code = "USD"
        settings.currency_symbol = "$"
        settings.tax_rate = Decimal('18.00')
        settings.default_trial_days = 14
        settings.grace_period_days = 7
        settings.invoice_prefix = "BL-INV-"
        settings.save()
        self.stdout.write("  [OK] System Settings verified")

        # 2. Product Categories
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
        p1, _ = Product.objects.get_or_create(
            sku="BL-CSS-01",
            defaults={
                "name": "Cloud Sentinel Suite",
                "category": cat_sec,
                "tagline": "Realtime enterprise vulnerability scanning and multi-cloud perimeter security",
                "description": "Cloud Sentinel provides automated real-time compliance monitoring, vulnerability assessment, and threat neutralization across AWS, Azure, and Google Cloud environments.",
                "base_price": Decimal("49.00"),
                "status": "active",
                "is_featured": True,
            }
        )

        p2, _ = Product.objects.get_or_create(
            sku="BL-DTE-02",
            defaults={
                "name": "DataPulse Telemetry Engine",
                "category": cat_tel,
                "tagline": "Unified log ingestion, distributed tracing, and synthetic monitoring",
                "description": "High-performance telemetry engine capable of streaming up to 2 million events per second with instant anomaly detection and OpenTelemetry native integration.",
                "base_price": Decimal("29.00"),
                "status": "active",
                "is_featured": False,
            }
        )

        p3, _ = Product.objects.get_or_create(
            sku="BL-AIW-03",
            defaults={
                "name": "BrightAI Workspace",
                "category": cat_ai,
                "tagline": "Agentic AI assistants and autonomous business workflow agents",
                "description": "Empower your product and engineering teams with collaborative autonomous agents for code review, data synthesis, and customer operations.",
                "base_price": Decimal("79.00"),
                "status": "active",
                "is_featured": True,
            }
        )

        p4, _ = Product.objects.get_or_create(
            sku="BL-AGF-04",
            defaults={
                "name": "API Gateway Flow",
                "category": cat_api,
                "tagline": "Ultra-low-latency edge microservices proxy with built-in rate limiting",
                "description": "Sub-millisecond API proxy offering declarative route policies, OAuth2 token enforcement, mTLS termination, and dynamic request transformation.",
                "base_price": Decimal("19.00"),
                "status": "active",
                "is_featured": False,
            }
        )
        self.stdout.write("  [OK] Products created")

        # 4. Product Variants
        # Variants for Product 1 (Cloud Sentinel)
        v1_std, _ = ProductVariant.objects.get_or_create(
            sku="VAR-CSS-STD-MO",
            defaults={
                "product": p1,
                "name": "Standard Cloud (Monthly)",
                "tier": "standard",
                "billing_cycle": "monthly",
                "price": Decimal("49.00"),
                "max_users": 5,
                "storage_gb": 50,
                "api_rate_limit": 25000,
                "sla_support_level": "Standard Email (24h)",
                "description": "Ideal for startups and growing teams managing up to 10 cloud accounts.",
            }
        )
        v1_pro, _ = ProductVariant.objects.get_or_create(
            sku="VAR-CSS-PRO-MO",
            defaults={
                "product": p1,
                "name": "Professional Dedicated (Monthly)",
                "tier": "pro",
                "billing_cycle": "monthly",
                "price": Decimal("129.00"),
                "max_users": 20,
                "storage_gb": 250,
                "api_rate_limit": 100000,
                "sla_support_level": "Priority Slack & Phone (4h)",
                "description": "Dedicated threat detection workers, compliance reports, and audit trails.",
            }
        )
        v1_ent, _ = ProductVariant.objects.get_or_create(
            sku="VAR-CSS-ENT-YR",
            defaults={
                "product": p1,
                "name": "Enterprise Cluster (Annual)",
                "tier": "enterprise",
                "billing_cycle": "annual",
                "price": Decimal("1190.00"),
                "max_users": 100,
                "storage_gb": 1000,
                "api_rate_limit": 500000,
                "sla_support_level": "Dedicated Solutions Engineer (1h SLA)",
                "description": "Unlimited security scanning nodes with air-gapped on-premise connector option.",
            }
        )

        # Variants for Product 3 (BrightAI Workspace)
        v3_pro, _ = ProductVariant.objects.get_or_create(
            sku="VAR-AIW-PRO-MO",
            defaults={
                "product": p3,
                "name": "Pro Agent Pack (Monthly)",
                "tier": "pro",
                "billing_cycle": "monthly",
                "price": Decimal("99.00"),
                "max_users": 10,
                "storage_gb": 100,
                "api_rate_limit": 50000,
                "sla_support_level": "Priority Email & Chat",
            }
        )
        self.stdout.write("  [OK] Product Variants created")

        # 5. Subscription Plans
        plan1, _ = SubscriptionPlan.objects.get_or_create(
            code="PLAN-SENTINEL-STARTER",
            defaults={
                "product": p1,
                "variant": v1_std,
                "name": "Sentinel Starter",
                "tier": "starter",
                "billing_cycle": "monthly",
                "price": Decimal("49.00"),
                "trial_days": 14,
                "status": "active",
                "is_featured": False,
                "sort_order": 1,
                "description": "Essential multi-cloud security scanning and vulnerability alerts.",
            }
        )
        plan2, _ = SubscriptionPlan.objects.get_or_create(
            code="PLAN-SENTINEL-GROWTH",
            defaults={
                "product": p1,
                "variant": v1_pro,
                "name": "Sentinel Growth Pro",
                "tier": "growth",
                "billing_cycle": "monthly",
                "price": Decimal("129.00"),
                "trial_days": 14,
                "status": "active",
                "is_featured": True,
                "sort_order": 2,
                "description": "Automated compliance framework (SOC2, HIPAA, ISO27001) and fast remediation.",
            }
        )
        plan3, _ = SubscriptionPlan.objects.get_or_create(
            code="PLAN-SENTINEL-ENTERPRISE",
            defaults={
                "product": p1,
                "variant": v1_ent,
                "name": "Sentinel Enterprise",
                "tier": "enterprise",
                "billing_cycle": "annual",
                "price": Decimal("1190.00"),
                "trial_days": 30,
                "status": "active",
                "is_featured": False,
                "sort_order": 3,
                "description": "Custom security policies, SAML SSO, and dedicated technical account manager.",
            }
        )

        plan4, _ = SubscriptionPlan.objects.get_or_create(
            code="PLAN-DATAPULSE-DEV",
            defaults={
                "product": p2,
                "name": "DataPulse Developer",
                "tier": "starter",
                "billing_cycle": "monthly",
                "price": Decimal("29.00"),
                "trial_days": 7,
                "status": "active",
                "is_featured": False,
                "sort_order": 4,
                "description": "Up to 50 GB log ingestion per month with 7-day retention.",
            }
        )

        plan5, _ = SubscriptionPlan.objects.get_or_create(
            code="PLAN-BRIGHTAI-TEAM",
            defaults={
                "product": p3,
                "variant": v3_pro,
                "name": "BrightAI Workspace Pro",
                "tier": "growth",
                "billing_cycle": "monthly",
                "price": Decimal("99.00"),
                "trial_days": 14,
                "status": "active",
                "is_featured": True,
                "sort_order": 5,
                "description": "5 autonomous agents, unlimited model prompts, and custom knowledge base integration.",
            }
        )
        self.stdout.write("  [OK] Subscription Plans created")

        # 6. Plan Features
        features_data = [
            (plan1, "Multi-Cloud Security Scanning", "Up to 10 Accounts", True, 1),
            (plan1, "Weekly Vulnerability Reports", "Automated PDF", True, 2),
            (plan1, "SAML Single Sign-On (SSO)", "Not Included", False, 3),

            (plan2, "Multi-Cloud Security Scanning", "Up to 50 Accounts", True, 1),
            (plan2, "Automated Compliance Audits", "SOC2, HIPAA, ISO", True, 2),
            (plan2, "Real-time Slack & PagerDuty Alerts", "Unlimited", True, 3),
            (plan2, "SAML Single Sign-On (SSO)", "Included", True, 4),

            (plan3, "Multi-Cloud Security Scanning", "Unlimited Accounts", True, 1),
            (plan3, "Automated Compliance Audits", "Full Suite & Reports", True, 2),
            (plan3, "Dedicated Solutions Engineer", "1 Hour SLA", True, 3),
            (plan3, "Air-Gapped / Private VPC Deploy", "Included", True, 4),

            (plan5, "Autonomous AI Agents", "5 Active Agents", True, 1),
            (plan5, "Private Knowledge Base Vector Storage", "100 GB", True, 2),
            (plan5, "Custom Fine-Tuned Prompts", "Included", True, 3),
        ]

        for p, name, quota, inc, order in features_data:
            PlanFeature.objects.get_or_create(
                plan=p,
                name=name,
                defaults={"quota_value": quota, "is_included": inc, "sort_order": order}
            )
        self.stdout.write("  [OK] Plan Features created")

        # 7. Customers (Person 1 Alignment)
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

        # 8. Subscriptions (Person 3 Alignment)
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

        # 9. Invoices (Person 4 Alignment)
        invoices_spec = [
            ("BL-INV-2026-001", created_customers[0], created_subs[0], Decimal("129.00"), today - timedelta(days=90)),
            ("BL-INV-2026-002", created_customers[0], created_subs[0], Decimal("129.00"), today - timedelta(days=60)),
            ("BL-INV-2026-003", created_customers[0], created_subs[0], Decimal("129.00"), today - timedelta(days=30)),
            ("BL-INV-2026-004", created_customers[1], created_subs[1], Decimal("1190.00"), today - timedelta(days=120)),
            ("BL-INV-2026-005", created_customers[2], created_subs[2], Decimal("99.00"), today - timedelta(days=45)),
            ("BL-INV-2026-006", created_customers[2], created_subs[2], Decimal("99.00"), today - timedelta(days=15)),
            ("BL-INV-2026-007", created_customers[3], created_subs[3], Decimal("49.00"), today - timedelta(days=20)),
            ("BL-INV-2026-008", created_customers[6], created_subs[6], Decimal("29.00"), today - timedelta(days=15)),
        ]

        for inv_num, cust, sub, amt, idate in invoices_spec:
            tax = round(amt * Decimal('0.18'), 2)
            total = amt + tax
            Invoice.objects.get_or_create(
                invoice_number=inv_num,
                defaults={
                    "customer": cust,
                    "subscription": sub,
                    "amount": amt,
                    "tax_amount": tax,
                    "total_amount": total,
                    "status": "paid",
                    "issued_date": idate,
                    "paid_at": timezone.now(),
                }
            )
        self.stdout.write("  [OK] Invoices created")

        # 10. Initial Audit Logs
        logs = [
            ("Initialized Brightloop SaaS catalog and executive dashboard", "dashboard"),
            ("Configured Cloud Sentinel Suite base SKU and tiered variants", "product"),
            ("Published Sentinel Growth Pro subscription plan", "plan"),
            ("Updated system tax and currency configuration", "setting"),
            ("Generated monthly product performance export", "export"),
        ]
        for act, cat in logs:
            ActivityLog.objects.get_or_create(action=act, defaults={"category": cat})

        self.stdout.write(self.style.SUCCESS("Brightloop SaaS database successfully seeded with realistic records!"))
