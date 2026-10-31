from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from products.models import Product
from plans.models import SubscriptionPlan, PlanFeature

class SubscriptionPlanTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(name="AI Suite", sku="AI-001", base_price=Decimal("50.00"))
        self.plan = SubscriptionPlan.objects.create(
            name="Pro Plan",
            code="PLAN-AI-PRO",
            product=self.product,
            price=Decimal("99.00"),
            status="active"
        )
        self.feature = PlanFeature.objects.create(
            plan=self.plan,
            name="Unlimited Tokens",
            quota_value="Unlimited",
            is_included=True
        )

    def test_plan_list_view(self):
        response = self.client.get(reverse('plan_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PLAN-AI-PRO")

    def test_plan_toggle_status(self):
        self.assertEqual(self.plan.status, "active")
        resp = self.client.post(reverse('plan_toggle_status', kwargs={'pk': self.plan.pk}))
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, "inactive")

    def test_plan_comparison_matrix_view(self):
        # activate plan for matrix view
        self.plan.status = "active"
        self.plan.save()
        response = self.client.get(reverse('plan_comparison'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unlimited Tokens")
