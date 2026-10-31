from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from products.models import ProductCategory, Product, ProductVariant

class ProductManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ProductCategory.objects.create(name="Enterprise Security")
        self.product = Product.objects.create(
            name="Cloud Sentinel",
            sku="BL-TEST-01",
            category=self.category,
            base_price=Decimal("49.00"),
            status="active"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Pro Tier",
            sku="VAR-TEST-PRO",
            price=Decimal("99.00"),
            tier="pro"
        )

    def test_product_list_view(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cloud Sentinel")

    def test_product_search_and_filter(self):
        # Search by SKU
        response = self.client.get(reverse('product_list') + '?q=BL-TEST-01')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cloud Sentinel")

        # Search non-existent
        response_none = self.client.get(reverse('product_list') + '?q=NON_EXISTENT_QUERY')
        self.assertNotContains(response_none, "BL-TEST-01")

    def test_product_create_and_delete(self):
        post_data = {
            'name': 'API Flow Master',
            'sku': 'BL-TEST-02',
            'category': self.category.id,
            'base_price': '39.00',
            'description': 'Test description for API tool.',
            'status': 'active'
        }
        resp = self.client.post(reverse('product_create'), post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Product.objects.filter(sku='BL-TEST-02').exists())

    def test_variant_list_view(self):
        response = self.client.get(reverse('variant_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VAR-TEST-PRO")
