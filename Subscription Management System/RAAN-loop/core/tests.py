from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from core.models import SystemSetting, ActivityLog, StaffProfile
from core.utils import get_dashboard_metrics
from products.models import Product
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription, Invoice, Payment, Quotation, Discount

class CoreDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_tester",
            email="admin@brightloop.io",
            password="adminpassword"
        )
        self.settings = SystemSetting.objects.create(
            company_name="Brightloop Software Test",
            currency_symbol="$",
            currency_code="USD"
        )
        self.customer = Customer.objects.create(
            full_name="Test Enterprise Corp",
            email="test@enterprise.com"
        )
        self.product = Product.objects.create(
            name="Security Cloud",
            sku="SKU-SEC-01",
            base_price=Decimal("100.00")
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Enterprise Annual",
            code="PLAN-ENT-01",
            product=self.product,
            price=Decimal("1200.00")
        )
        self.subscription = Subscription.objects.create(
            subscription_id="SUB-TEST-001",
            customer=self.customer,
            plan=self.plan,
            current_amount=Decimal("1200.00"),
            next_billing_date="2026-12-31"
        )
        self.invoice = Invoice.objects.create(
            invoice_number="INV-TEST-01",
            customer=self.customer,
            subscription=self.subscription,
            amount=Decimal("1200.00"),
            total_amount=Decimal("1416.00"),
            status="paid"
        )
        self.overdue_invoice = Invoice.objects.create(
            invoice_number="INV-OVERDUE-01",
            customer=self.customer,
            subscription=self.subscription,
            amount=Decimal("500.00"),
            total_amount=Decimal("590.00"),
            status="overdue",
            due_date="2026-01-01"
        )
        self.payment = Payment.objects.create(
            payment_id="PAY-TEST-01",
            customer=self.customer,
            invoice=self.invoice,
            amount=Decimal("1416.00"),
            status="completed"
        )
        self.pending_payment = Payment.objects.create(
            payment_id="PAY-PENDING-01",
            customer=self.customer,
            amount=Decimal("590.00"),
            status="pending"
        )

    def test_admin_restriction_redirects_anonymous(self):
        # Anonymous user must be redirected to login
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_dashboard_metrics_and_view_for_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Executive Admin Dashboard")
        self.assertContains(response, "Total Customers")
        self.assertContains(response, "Total Products")
        self.assertContains(response, "Active Subscriptions")
        self.assertContains(response, "Total Revenue")
        self.assertContains(response, "Pending Payments")
        self.assertContains(response, "Overdue Invoices")

    def test_all_sidebar_links_connected_and_accessible(self):
        """Verify that every single sidebar link connects to its respective working page."""
        self.client.force_login(self.admin_user)
        links = [
            'dashboard',
            'customer_list',
            'staff_list',
            'product_list',
            'plan_list',
            'subscription_list',
            'quotation_list',
            'invoice_list',
            'discount_list',
            'payment_list',
            'reports',
            'admin_settings',
        ]
        for url_name in links:
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 200, f"Sidebar link {url_name} failed to return HTTP 200")

    def test_admin_settings_get_and_post(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_settings'))
        self.assertEqual(response.status_code, 200)

        post_data = {
            'company_name': 'Brightloop Updated Inc',
            'support_email': 'support@brightloop.io',
            'billing_email': 'billing@brightloop.io',
            'currency_code': 'EUR',
            'currency_symbol': '€',
            'tax_rate': 20.00,
            'default_trial_days': 21,
            'grace_period_days': 10,
            'invoice_prefix': 'INV-TEST-',
            'allow_self_signup': True,
        }
        post_response = self.client.post(reverse('admin_settings'), post_data)
        self.assertEqual(post_response.status_code, 302)
        
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.company_name, 'Brightloop Updated Inc')
        self.assertEqual(self.settings.currency_symbol, '€')
