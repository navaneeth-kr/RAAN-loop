from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from products.models import Product, ProductCategory
from plans.models import SubscriptionPlan, PlanFeature
from plans.forms import SubscriptionPlanForm
from subscriptions.models import Customer, Subscription

class SubscriptionPlanManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin User
        self.admin = User.objects.create_superuser(
            username='admin_plan_tester',
            email='admin@brightloop.io',
            password='password123'
        )
        self.client.force_login(self.admin)

        # Regular Non-Staff User
        self.regular_user = User.objects.create_user(
            username='regular_plan_tester',
            email='regular@brightloop.io',
            password='password123'
        )

        # Base Product
        self.category = ProductCategory.objects.create(name="Business Suite")
        self.product = Product.objects.create(
            name="Software Package",
            sku="BL-TEST-PKG",
            product_type="software",
            category=self.category,
            selling_price=Decimal("500.00"),
            cost_price=Decimal("250.00")
        )

        # Base Plan with Monthly Frequency
        self.today = timezone.now().date()
        self.plan = SubscriptionPlan.objects.create(
            name="Software Package Standard Plan",
            code="PLAN-TEST-SW-01",
            product=self.product,
            billing_cycle="monthly",
            price=Decimal("500.00"),
            min_quantity=1,
            start_date=self.today,
            end_date=self.today + timedelta(days=365),
            auto_close=False,
            allow_early_cancellation=True,
            allow_pausing=True,
            allow_renewal=True,
            trial_days=14,
            status="active",
            description="Test plan for SaaS standard users."
        )

        # Customer & Subscription for Deletion Protection Testing
        self.customer = Customer.objects.create(
            full_name="Acme Corp",
            email="billing@acme.com",
            status="active"
        )

    # 1. PLAN CRUD & DETAILS
    def test_plan_list_view(self):
        """Admin can view plans with pricing cards and management table."""
        response = self.client.get(reverse('plan_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Software Package Standard Plan")
        self.assertContains(response, "PLAN-TEST-SW-01")
        self.assertContains(response, "planManagementTable")

    def test_plan_create_success(self):
        """Admin can create a new plan with all required fields."""
        post_data = {
            'name': 'Software Package Yearly Enterprise',
            'code': 'PLAN-TEST-YR-02',
            'product': self.product.id,
            'tier': 'enterprise',
            'billing_cycle': 'yearly',
            'price': '5000.00',
            'min_quantity': '5',
            'start_date': str(self.today),
            'end_date': str(self.today + timedelta(days=730)),
            'auto_close': True,
            'allow_early_cancellation': False,
            'allow_pausing': True,
            'allow_renewal': True,
            'trial_days': '30',
            'setup_fee': '0.00',
            'status': 'active',
            'sort_order': '1',
            'description': 'Yearly enterprise commitment with 5 minimum seats.'
        }
        response = self.client.post(reverse('plan_create'), post_data)
        self.assertEqual(response.status_code, 302)
        new_plan = SubscriptionPlan.objects.get(code='PLAN-TEST-YR-02')
        self.assertEqual(new_plan.billing_cycle, 'yearly')
        self.assertEqual(new_plan.min_quantity, 5)
        self.assertEqual(new_plan.price, Decimal('5000.00'))
        self.assertFalse(new_plan.allow_early_cancellation)
        self.assertTrue(new_plan.auto_close)

    def test_plan_update(self):
        """Admin can edit plan terms and settings."""
        post_data = {
            'name': 'Software Package Standard Plan - Revised',
            'code': self.plan.code,
            'product': self.product.id,
            'tier': 'starter',
            'billing_cycle': 'monthly',
            'price': '550.00',
            'min_quantity': '2',
            'start_date': str(self.today),
            'end_date': str(self.today + timedelta(days=365)),
            'auto_close': False,
            'allow_early_cancellation': True,
            'allow_pausing': True,
            'allow_renewal': True,
            'trial_days': '14',
            'setup_fee': '0.00',
            'status': 'active',
            'sort_order': '0',
            'description': 'Revised pricing terms.'
        }
        response = self.client.post(reverse('plan_update', kwargs={'pk': self.plan.pk}), post_data)
        self.assertEqual(response.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.name, 'Software Package Standard Plan - Revised')
        self.assertEqual(self.plan.price, Decimal('550.00'))
        self.assertEqual(self.plan.min_quantity, 2)

    # 2. SAFE DELETION & ACTIVE SUBSCRIPTION PROTECTION
    def test_prevent_deletion_when_active_subscriptions_exist(self):
        """
        PREVENT DELETION of plans that are already used by active subscriptions.
        """
        Subscription.objects.create(
            subscription_id="SUB-ACTIVE-TEST-01",
            customer=self.customer,
            plan=self.plan,
            status="active",
            billing_cycle="monthly",
            current_amount=Decimal("500.00"),
            start_date=self.today,
            next_billing_date=self.today + timedelta(days=30)
        )

        # Check model safety check directly
        can_delete, reason = self.plan.can_be_safely_deleted()
        self.assertFalse(can_delete)
        self.assertIn("active subscription", reason)

        # Attempting POST delete should be BLOCKED
        response = self.client.post(reverse('plan_delete', kwargs={'pk': self.plan.pk}))
        self.assertEqual(response.status_code, 302)
        # Plan MUST still exist
        self.assertTrue(SubscriptionPlan.objects.filter(pk=self.plan.pk).exists())

    def test_safe_deletion_when_zero_active_subscriptions(self):
        """
        Safe deletion succeeds when plan has 0 active subscriptions.
        """
        unused_plan = SubscriptionPlan.objects.create(
            name="Unused Plan To Delete",
            code="PLAN-UNUSED-01",
            product=self.product,
            price=Decimal("100.00"),
            min_quantity=1
        )
        can_delete, _ = unused_plan.can_be_safely_deleted()
        self.assertTrue(can_delete)

        response = self.client.post(reverse('plan_delete', kwargs={'pk': unused_plan.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SubscriptionPlan.objects.filter(pk=unused_plan.pk).exists())

    # 3. ACTIVATE OR DEACTIVATE PLANS
    def test_activate_and_deactivate_plan(self):
        """Admin can toggle status between active and inactive."""
        self.assertEqual(self.plan.status, "active")

        # Toggle to inactive
        self.client.post(reverse('plan_toggle_status', kwargs={'pk': self.plan.pk}))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, "inactive")

        # Toggle back to active
        self.client.post(reverse('plan_toggle_status', kwargs={'pk': self.plan.pk}))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, "active")

    # 4. QUANTITY-BASED PRICE CALCULATION
    def test_quantity_price_calculation(self):
        """Calculate total price based on quantity: Qty * Unit Price."""
        plan = SubscriptionPlan.objects.create(
            name="Seat Pack Plan",
            code="PLAN-SEAT-01",
            product=self.product,
            price=Decimal("50.00"),
            min_quantity=5
        )
        # Minimum quantity enforced (requesting 1 calculates for min_quantity 5)
        self.assertEqual(plan.calculate_price_for_quantity(1), Decimal("250.00"))
        # 10 seats * 50 = 500
        self.assertEqual(plan.calculate_price_for_quantity(10), Decimal("500.00"))
        # 25 seats * 50 = 1250
        self.assertEqual(plan.calculate_price_for_quantity(25), Decimal("1250.00"))

    def test_ajax_calculate_price_endpoint(self):
        """Verify JSON endpoint for real-time quantity pricing."""
        response = self.client.get(reverse('plan_calculate_price', kwargs={'pk': self.plan.pk}) + '?qty=8')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['unit_price'], 500.00)
        self.assertEqual(data['effective_quantity'], 8)
        self.assertEqual(data['total_price'], 4000.00)

    # 5. BILLING FREQUENCIES (Daily, Weekly, Monthly, Yearly)
    def test_billing_frequencies(self):
        """Verify plans support Daily, Weekly, Monthly, and Yearly frequencies."""
        for freq in ['daily', 'weekly', 'monthly', 'yearly']:
            p = SubscriptionPlan.objects.create(
                name=f"Plan {freq}",
                code=f"PLAN-FREQ-{freq.upper()}",
                product=self.product,
                billing_cycle=freq,
                price=Decimal("100.00")
            )
            self.assertEqual(p.billing_cycle, freq)

    # 6. DATE VALIDATIONS
    def test_date_validations(self):
        """End date cannot be earlier than start date; auto_close requires end date."""
        # 1. End Date before Start Date fails
        form_invalid_dates = SubscriptionPlanForm(data={
            'name': 'Invalid Date Plan',
            'code': 'PLAN-INV-DATE',
            'product': self.product.id,
            'billing_cycle': 'monthly',
            'price': '100.00',
            'min_quantity': '1',
            'start_date': str(self.today),
            'end_date': str(self.today - timedelta(days=5)),
        })
        self.assertFalse(form_invalid_dates.is_valid())
        self.assertIn('end_date', form_invalid_dates.errors)

        # 2. Auto-close without End Date fails
        form_auto_close_no_end = SubscriptionPlanForm(data={
            'name': 'Auto Close Without End Date',
            'code': 'PLAN-AUTO-NO-END',
            'product': self.product.id,
            'billing_cycle': 'monthly',
            'price': '100.00',
            'min_quantity': '1',
            'start_date': str(self.today),
            'end_date': '',
            'auto_close': True,
        })
        self.assertFalse(form_auto_close_no_end.is_valid())
        self.assertIn('end_date', form_auto_close_no_end.errors)

    # 7. SEARCH & FILTERING
    def test_search_and_filtering(self):
        """Search by name/code and filter by billing frequency."""
        # Search
        res_search = self.client.get(reverse('plan_list') + '?q=Standard Plan')
        self.assertContains(res_search, "PLAN-TEST-SW-01")

        # Filter by Frequency
        res_freq = self.client.get(reverse('plan_list') + '?billing_cycle=monthly')
        self.assertContains(res_freq, "PLAN-TEST-SW-01")

        res_wrong_freq = self.client.get(reverse('plan_list') + '?billing_cycle=daily')
        self.assertNotContains(res_wrong_freq, "PLAN-TEST-SW-01")

    # 8. SECURITY & AUTHORIZATION
    def test_unauthorized_access_blocked(self):
        """Non-admin and anonymous users are blocked from managing plans."""
        self.client.logout()
        resp_anon = self.client.get(reverse('plan_list'))
        self.assertEqual(resp_anon.status_code, 302)

        self.client.force_login(self.regular_user)
        resp_user = self.client.get(reverse('plan_list'))
        self.assertEqual(resp_user.status_code, 302)
