from django.test import TestCase, Client
from django.urls import reverse
from core.models import SystemSetting, ActivityLog
from core.utils import get_dashboard_metrics

class CoreDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.settings = SystemSetting.objects.create(
            company_name="Brightloop Software Test",
            currency_symbol="$",
            currency_code="USD"
        )

    def test_dashboard_view_status_code(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Executive Admin Dashboard")
        self.assertContains(response, "Monthly Recurring Revenue")

    def test_admin_settings_get_and_post(self):
        response = self.client.get(reverse('admin_settings'))
        self.assertEqual(response.status_code, 200)

        # POST update
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

    def test_export_center_view(self):
        response = self.client.get(reverse('export_center'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Export & Reporting Center")

    def test_export_download_csv_and_json(self):
        # CSV Export
        csv_resp = self.client.get(reverse('export_download') + '?entity=products&format=csv')
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp['Content-Type'], 'text/csv')

        # JSON Export
        json_resp = self.client.get(reverse('export_download') + '?entity=products&format=json')
        self.assertEqual(json_resp.status_code, 200)
        self.assertEqual(json_resp['Content-Type'], 'application/json')
