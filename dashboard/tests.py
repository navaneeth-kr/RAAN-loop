from django.test import TestCase, Client
from django.urls import reverse

class ProjectFoundationTests(TestCase):
    """
    Automated integration tests verifying the foundation of
    Brightloop Software's Subscription Management System.
    """
    def setUp(self):
        self.client = Client()

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Brightloop')
        self.assertContains(response, 'Executive Dashboard')

    def test_accounts_view(self):
        response = self.client.get(reverse('accounts:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer Accounts')

    def test_products_view(self):
        response = self.client.get(reverse('products:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Products Catalog')

    def test_plans_view(self):
        response = self.client.get(reverse('plans:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Plans & Pricing Tiers')

    def test_subscriptions_view(self):
        response = self.client.get(reverse('subscriptions:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscriptions Management')

    def test_billing_view(self):
        response = self.client.get(reverse('billing:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Billing & Invoices')

    def test_payments_view(self):
        response = self.client.get(reverse('payments:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payments & Gateway Transactions')
