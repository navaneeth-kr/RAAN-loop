from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import SystemSetting
from products.models import Product
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription, Invoice, Payment, Discount, TaxRate
from subscriptions.forms import InvoiceForm, DiscountForm, PaymentForm, TaxRateForm

class Person4InvoiceManagementTests(TestCase):
    """Tests for Person 4: Invoice Management module."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin_p4",
            email="p4@brightloop.io",
            password="testpassword"
        )
        self.setting = SystemSetting.objects.create(
            company_name="Brightloop Test Suite",
            tax_rate=Decimal("18.00"),
            currency_symbol="₹",
            currency_code="INR"
        )
        self.customer = Customer.objects.create(
            full_name="Acme Global Corporation",
            email="billing@acmeglobal.com",
            country="India"
        )
        self.product = Product.objects.create(
            name="Cloud Sentinel",
            sku="SKU-SENTINEL-P4",
            selling_price=Decimal("1000.00")
        )
        self.plan = SubscriptionPlan.objects.create(
            code="PLAN-SENTINEL-P4",
            name="Sentinel Enterprise",
            product=self.product,
            price=Decimal("1000.00"),
            billing_cycle="monthly"
        )
        self.subscription = Subscription.objects.create(
            subscription_id="SUB-P4-001",
            customer=self.customer,
            plan=self.plan,
            current_amount=Decimal("1000.00"),
            next_billing_date=timezone.now().date() + timedelta(days=30)
        )
        self.tax_18 = TaxRate.objects.create(
            name="GST 18%",
            rate_percent=Decimal("18.00"),
            is_default=True,
            is_active=True
        )
        self.discount_20 = Discount.objects.create(
            code="SAVE20P4",
            description="20% Off Promotion",
            discount_type="percentage",
            value=Decimal("20.00"),
            valid_from=timezone.now().date() - timedelta(days=5),
            valid_until=timezone.now().date() + timedelta(days=30),
            is_active=True
        )

    def test_invoice_creation_with_tax_and_discount(self):
        """Verifies invoice creation, automated number generation, discount, and tax calculation."""
        form_data = {
            'customer': self.customer.pk,
            'subscription': self.subscription.pk,
            'amount': '1000.00',
            'tax_rate': self.tax_18.pk,
            'discount': self.discount_20.pk,
            'issued_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': (timezone.now().date() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'status': 'pending',
            'notes': 'Net 15 enterprise terms apply.',
        }
        form = InvoiceForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        invoice = form.save()

        # Subtotal: 1000.00
        # Discount 20%: 200.00
        # Taxable Base: 800.00
        # Tax 18%: 144.00
        # Total: 944.00
        self.assertTrue('INV' in invoice.invoice_number)
        self.assertEqual(invoice.amount, Decimal('1000.00'))
        self.assertEqual(invoice.discount_amount, Decimal('200.00'))
        self.assertEqual(invoice.tax_amount, Decimal('144.00'))
        self.assertEqual(invoice.total_amount, Decimal('944.00'))
        self.assertEqual(invoice.status, 'pending')

    def test_invoice_due_date_validation(self):
        """Validates that due date cannot precede the issue date."""
        form_data = {
            'customer': self.customer.pk,
            'amount': '500.00',
            'issued_date': '2026-10-15',
            'due_date': '2026-10-10',  # Invalid: earlier than issued date
            'status': 'pending',
        }
        form = InvoiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)

    def test_invoice_list_and_kpis(self):
        """Verifies invoice list view loads, displays KPI summaries, and supports status filtering."""
        self.client.force_login(self.admin)
        inv = Invoice.objects.create(
            invoice_number="INV-TEST-001",
            customer=self.customer,
            amount=Decimal("500.00"),
            tax_amount=Decimal("90.00"),
            total_amount=Decimal("590.00"),
            status="overdue",
            issued_date=timezone.now().date() - timedelta(days=40),
            due_date=timezone.now().date() - timedelta(days=10)
        )
        response = self.client.get(reverse('invoice_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoices &amp; Billing")
        self.assertContains(response, "INV-TEST-001")
        self.assertContains(response, "Overdue")

        # Test status filter
        filter_resp = self.client.get(reverse('invoice_list') + '?status=overdue')
        self.assertEqual(filter_resp.status_code, 200)
        self.assertContains(filter_resp, "INV-TEST-001")

    def test_invoice_detail_view(self):
        """Verifies printable invoice view with customer, tax, and company information."""
        self.client.force_login(self.admin)
        inv = Invoice.objects.create(
            invoice_number="INV-DETAIL-001",
            customer=self.customer,
            amount=Decimal("1200.00"),
            tax_amount=Decimal("216.00"),
            total_amount=Decimal("1416.00"),
            status="pending"
        )
        response = self.client.get(reverse('invoice_detail', kwargs={'pk': inv.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoice #INV-DETAIL-001")
        self.assertContains(response, "Acme Global Corporation")
        self.assertContains(response, "1416.00")

    def test_invoice_mark_as_paid(self):
        """Verifies 1-click action to mark invoice as paid, which auto-creates completed payment."""
        self.client.force_login(self.admin)
        inv = Invoice.objects.create(
            invoice_number="INV-PAID-001",
            customer=self.customer,
            amount=Decimal("800.00"),
            tax_amount=Decimal("144.00"),
            total_amount=Decimal("944.00"),
            status="pending"
        )
        response = self.client.post(reverse('invoice_mark_paid', kwargs={'pk': inv.pk}))
        self.assertEqual(response.status_code, 302)

        inv.refresh_from_db()
        self.assertEqual(inv.status, 'paid')
        self.assertIsNotNone(inv.paid_at)

        # Check completed payment auto-created
        payment = Payment.objects.filter(invoice=inv, status='completed').first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('944.00'))


class Person4DiscountManagementTests(TestCase):
    """Tests for Person 4: Discount Management module."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username="admin_disc", email="d@b.io", password="p")

    def test_discount_creation_and_calculations(self):
        """Tests creating percentage and fixed discounts and their calculation methods."""
        disc_pct = Discount.objects.create(
            code="FESTIVE25",
            description="25% Off",
            discount_type="percentage",
            value=Decimal("25.00"),
            valid_from=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        # 25% of 800 = 200
        self.assertEqual(disc_pct.calculate_discount(Decimal("800.00")), Decimal("200.00"))

        disc_fixed = Discount.objects.create(
            code="CREDIT50",
            description="Fixed 50 credit",
            discount_type="fixed",
            value=Decimal("50.00"),
            valid_from=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        # Fixed 50 off 200 = 50
        self.assertEqual(disc_fixed.calculate_discount(Decimal("200.00")), Decimal("50.00"))
        # Fixed 50 off 30 = 30 (cannot exceed subtotal)
        self.assertEqual(disc_fixed.calculate_discount(Decimal("30.00")), Decimal("30.00"))

    def test_discount_validation_rules(self):
        """Verifies percentage cannot exceed 100% and dates must be ordered."""
        form_invalid_pct = DiscountForm(data={
            'code': 'INVALID150',
            'discount_type': 'percentage',
            'value': '150.00',  # Invalid: > 100%
            'valid_from': timezone.now().date(),
            'valid_until': timezone.now().date() + timedelta(days=10),
            'is_active': True
        })
        self.assertFalse(form_invalid_pct.is_valid())
        self.assertIn('value', form_invalid_pct.errors)

        form_invalid_dates = DiscountForm(data={
            'code': 'DATEFAIL',
            'discount_type': 'fixed',
            'value': '10.00',
            'valid_from': '2026-10-20',
            'valid_until': '2026-10-10',  # Invalid: before valid_from
            'is_active': True
        })
        self.assertFalse(form_invalid_dates.is_valid())
        self.assertIn('valid_until', form_invalid_dates.errors)

    def test_discount_toggle_status(self):
        """Tests 1-click active/inactive toggle."""
        self.client.force_login(self.admin)
        disc = Discount.objects.create(
            code="TOGGLE10",
            discount_type="percentage",
            value=Decimal("10.00"),
            valid_from=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=10),
            is_active=True
        )
        resp = self.client.post(reverse('discount_toggle_status', kwargs={'pk': disc.pk}))
        self.assertEqual(resp.status_code, 302)
        disc.refresh_from_db()
        self.assertFalse(disc.is_active)

        resp2 = self.client.post(reverse('discount_toggle_status', kwargs={'pk': disc.pk}))
        self.assertEqual(resp2.status_code, 302)
        disc.refresh_from_db()
        self.assertTrue(disc.is_active)


class Person4PaymentManagementTests(TestCase):
    """Tests for Person 4: Payment Management module."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username="admin_pay", email="p@b.io", password="p")
        self.customer = Customer.objects.create(full_name="Payment Client Corp", email="pay@corp.com")
        self.invoice = Invoice.objects.create(
            invoice_number="INV-PAY-TEST",
            customer=self.customer,
            amount=Decimal("500.00"),
            tax_amount=Decimal("90.00"),
            total_amount=Decimal("590.00"),
            status="pending"
        )

    def test_payment_creation_auto_settles_invoice(self):
        """Verifies that recording a completed payment auto-marks invoice as paid."""
        self.client.force_login(self.admin)
        form_data = {
            'customer': self.customer.pk,
            'invoice': self.invoice.pk,
            'amount': '590.00',
            'payment_method': 'stripe',
            'transaction_reference': 'txn_stripe_999888',
            'payment_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'status': 'completed',
        }
        form = PaymentForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        payment = form.save()

        self.assertTrue(payment.payment_id.startswith('PAY-'))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')
        self.assertIsNotNone(self.invoice.paid_at)

    def test_payment_refund_flow(self):
        """Verifies refund action updates payment to refunded and invoice to refunded."""
        self.client.force_login(self.admin)
        payment = Payment.objects.create(
            payment_id="PAY-REFUND-001",
            customer=self.customer,
            invoice=self.invoice,
            amount=Decimal("590.00"),
            payment_method="credit_card",
            status="completed"
        )
        self.invoice.status = 'paid'
        self.invoice.save()

        response = self.client.post(reverse('payment_refund', kwargs={'pk': payment.pk}))
        self.assertEqual(response.status_code, 302)

        payment.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')
        self.assertEqual(self.invoice.status, 'refunded')


class Person4TaxConfigurationTests(TestCase):
    """Tests for Person 4: Tax Configuration module."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username="admin_tax", email="t@b.io", password="p")
        self.setting = SystemSetting.objects.create(tax_rate=Decimal("18.00"))

    def test_tax_rate_creation_and_default_toggle(self):
        """Tests creating a tax rule and setting it as default."""
        self.client.force_login(self.admin)
        tr1 = TaxRate.objects.create(name="India GST", rate_percent=Decimal("18.00"), is_default=True)
        tr2 = TaxRate.objects.create(name="EU VAT", rate_percent=Decimal("20.00"), is_default=False)

        # Make EU VAT the default
        resp = self.client.post(reverse('tax_set_default', kwargs={'pk': tr2.pk}))
        self.assertEqual(resp.status_code, 302)

        tr1.refresh_from_db()
        tr2.refresh_from_db()
        self.assertFalse(tr1.is_default)
        self.assertTrue(tr2.is_default)

        # Syncs with SystemSetting
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.tax_rate, Decimal("20.00"))

    def test_tax_rate_range_validation(self):
        """Validates that tax rate percentage must be between 0% and 100%."""
        form = TaxRateForm(data={
            'name': 'Negative Tax',
            'rate_percent': '-5.00',
            'is_active': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rate_percent', form.errors)

        form_excess = TaxRateForm(data={
            'name': 'Excess Tax',
            'rate_percent': '105.00',
            'is_active': True
        })
        self.assertFalse(form_excess.is_valid())
        self.assertIn('rate_percent', form_excess.errors)


class Person4IntegrationTests(TestCase):
    """Integration tests verifying Person 4 live API and UI endpoints."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username="admin_int", email="i@b.io", password="p")
        self.tax = TaxRate.objects.create(name="GST", rate_percent=Decimal("18.00"), is_default=True)
        self.disc = Discount.objects.create(
            code="INT10",
            discount_type="percentage",
            value=Decimal("10.00"),
            valid_from=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=10)
        )

    def test_live_calculation_preview_api(self):
        """Tests the client-side calculator preview endpoint."""
        self.client.force_login(self.admin)
        url = reverse('invoice_calculate_preview') + f"?amount=1000.00&tax_rate_id={self.tax.id}&discount_id={self.disc.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 1000 - 100 (10%) = 900 taxable
        # 18% of 900 = 162 tax
        # Total = 1062
        self.assertEqual(data['subtotal'], 1000.0)
        self.assertEqual(data['discount_amount'], 100.0)
        self.assertEqual(data['taxable_amount'], 900.0)
        self.assertEqual(data['tax_amount'], 162.0)
        self.assertEqual(data['total_amount'], 1062.0)
