from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from products.models import ProductCategory, Product, ProductVariant
from products.forms import ProductForm, ProductVariantForm

class ProductManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='admin_test',
            email='admin@brightloop.io',
            password='password123'
        )
        self.client.force_login(self.admin)

        # Standard non-admin user
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@brightloop.io',
            password='password123'
        )

        # Base category
        self.category = ProductCategory.objects.create(
            name="Enterprise Software",
            icon="bi-building-gear"
        )

        # Flagship product matching user specification
        self.product = Product.objects.create(
            name="Software Package",
            sku="BL-SW-PKG-01",
            product_type="software",
            category=self.category,
            selling_price=Decimal("500.00"),
            cost_price=Decimal("250.00"),
            description="Enterprise modular business software suite.",
            notes="Standard base price is ₹500 with tiered variant surcharges.",
            status="active",
            is_featured=True
        )

        # Variants matching user specification:
        # 1. Standard: ₹0 additional charge -> ₹500
        self.variant_std = ProductVariant.objects.create(
            product=self.product,
            name="Standard",
            sku="VAR-SW-STD-01",
            tier="standard",
            billing_cycle="monthly",
            additional_charge=Decimal("0.00"),
            max_users=5,
            storage_gb=50
        )

        # 2. Odoo: ₹560 additional charge -> ₹1,060
        self.variant_odoo = ProductVariant.objects.create(
            product=self.product,
            name="Odoo",
            sku="VAR-SW-ODOO-02",
            tier="odoo",
            billing_cycle="monthly",
            additional_charge=Decimal("560.00"),
            max_users=15,
            storage_gb=150
        )

        # 3. Premium: ₹1,000 additional charge -> ₹1,500
        self.variant_prem = ProductVariant.objects.create(
            product=self.product,
            name="Premium",
            sku="VAR-SW-PREM-03",
            tier="premium",
            billing_cycle="monthly",
            additional_charge=Decimal("1000.00"),
            max_users=50,
            storage_gb=500
        )

    # 1. AUTOMATIC PRICE CALCULATION TESTS
    def test_automatic_variant_price_calculation(self):
        """Verify automatic final price calculation: Base Price + Additional Surcharge."""
        # Standard: 500 + 0 = 500
        self.assertEqual(self.variant_std.final_price, Decimal("500.00"))
        self.assertEqual(self.variant_std.price, Decimal("500.00"))

        # Odoo: 500 + 560 = 1060
        self.assertEqual(self.variant_odoo.final_price, Decimal("1060.00"))
        self.assertEqual(self.variant_odoo.price, Decimal("1060.00"))

        # Premium: 500 + 1000 = 1500
        self.assertEqual(self.variant_prem.final_price, Decimal("1500.00"))
        self.assertEqual(self.variant_prem.price, Decimal("1500.00"))

    def test_product_gross_profit_and_margin(self):
        """Verify product gross profit and profit margin percentage."""
        # Selling: 500, Cost: 250 -> Profit: 250, Margin: 50.0%
        self.assertEqual(self.product.gross_profit, Decimal("250.00"))
        self.assertEqual(self.product.profit_margin_percent, 50.0)

    # 2. PRODUCT CRUD OPERATIONS
    def test_product_list_view(self):
        """Admin can view the product management table."""
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product Management")
        self.assertContains(response, "Software Package")
        self.assertContains(response, "BL-SW-PKG-01")
        self.assertContains(response, "productManagementTable")

    def test_product_create_view_success(self):
        """Admin can create a new product with all required fields."""
        post_data = {
            'name': 'Cloud Telemetry Engine',
            'product_type': 'saas',
            'sku': 'BL-TEL-01',
            'category': self.category.id,
            'selling_price': '300.00',
            'cost_price': '100.00',
            'tagline': 'High throughput metrics pipeline',
            'description': 'Real-time telemetry and streaming metrics engine.',
            'notes': 'Internal cloud microservice node.',
            'status': 'active',
        }
        response = self.client.post(reverse('product_create'), post_data)
        self.assertEqual(response.status_code, 302)
        new_prod = Product.objects.get(sku='BL-TEL-01')
        self.assertEqual(new_prod.name, 'Cloud Telemetry Engine')
        self.assertEqual(new_prod.selling_price, Decimal('300.00'))
        self.assertEqual(new_prod.cost_price, Decimal('100.00'))
        self.assertEqual(new_prod.product_type, 'saas')
        self.assertEqual(new_prod.gross_profit, Decimal('200.00'))

    def test_product_detail_view(self):
        """Admin can view product specifications, notes, and variants table."""
        response = self.client.get(reverse('product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Software Package")
        self.assertContains(response, "Standard")
        self.assertContains(response, "Odoo")
        self.assertContains(response, "Premium")
        # Final calculated prices
        self.assertContains(response, "1060.00")
        self.assertContains(response, "1500.00")

    def test_product_update_view(self):
        """Admin can edit an existing product."""
        post_data = {
            'name': 'Software Package Enterprise Edition',
            'product_type': 'software',
            'sku': 'BL-SW-PKG-01',
            'category': self.category.id,
            'selling_price': '600.00',
            'cost_price': '250.00',
            'description': 'Updated enterprise software description.',
            'notes': 'Adjusted base price to ₹600.',
            'status': 'active',
        }
        response = self.client.post(reverse('product_update', kwargs={'pk': self.product.pk}), post_data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Software Package Enterprise Edition')
        self.assertEqual(self.product.selling_price, Decimal('600.00'))
        # Automatic recalculation on variant: 600 + 560 = 1160
        self.variant_odoo.refresh_from_db()
        self.assertEqual(self.variant_odoo.final_price, Decimal('1160.00'))

    def test_product_delete_view(self):
        """Admin can delete a product."""
        prod_to_delete = Product.objects.create(
            name="Temporary Product",
            sku="BL-TEMP-01",
            selling_price=Decimal("100.00"),
            cost_price=Decimal("50.00"),
            description="To be deleted"
        )
        response = self.client.post(reverse('product_delete', kwargs={'pk': prod_to_delete.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(sku="BL-TEMP-01").exists())

    # 3. SEARCH & FILTERING TESTS
    def test_product_search(self):
        """Search products by name, SKU, or notes."""
        # By Name
        res1 = self.client.get(reverse('product_list') + '?q=Software Package')
        self.assertContains(res1, "BL-SW-PKG-01")

        # By SKU
        res2 = self.client.get(reverse('product_list') + '?q=BL-SW-PKG-01')
        self.assertContains(res2, "Software Package")

        # By Notes
        res3 = self.client.get(reverse('product_list') + '?q=surcharges')
        self.assertContains(res3, "Software Package")

        # Non-matching
        res_none = self.client.get(reverse('product_list') + '?q=NonExistentQueryXYZ')
        self.assertNotContains(res_none, "BL-SW-PKG-01")

    def test_product_filter_by_type_and_status(self):
        """Filter products by product_type and status."""
        res_type = self.client.get(reverse('product_list') + '?product_type=software')
        self.assertContains(res_type, "Software Package")

        res_wrong_type = self.client.get(reverse('product_list') + '?product_type=hardware')
        self.assertNotContains(res_wrong_type, "BL-SW-PKG-01")

        res_status = self.client.get(reverse('product_list') + '?status=active')
        self.assertContains(res_status, "Software Package")

    # 4. PRICE VALIDATION TESTS
    def test_product_price_validation_rules(self):
        """Validate price constraints: selling > 0, cost >= 0, cost <= selling."""
        # Zero selling price should fail
        form1 = ProductForm(data={
            'name': 'Invalid Price Item',
            'product_type': 'software',
            'sku': 'BL-INV-01',
            'selling_price': '0.00',
            'cost_price': '0.00',
            'description': 'Valid desc'
        })
        self.assertFalse(form1.is_valid())
        self.assertIn('selling_price', form1.errors)

        # Negative cost price should fail
        form2 = ProductForm(data={
            'name': 'Negative Cost Item',
            'product_type': 'software',
            'sku': 'BL-INV-02',
            'selling_price': '100.00',
            'cost_price': '-20.00',
            'description': 'Valid desc'
        })
        self.assertFalse(form2.is_valid())
        self.assertIn('cost_price', form2.errors)

        # Cost price exceeding selling price should fail cross-field check
        form3 = ProductForm(data={
            'name': 'Negative Margin Item',
            'product_type': 'software',
            'sku': 'BL-INV-03',
            'selling_price': '50.00',
            'cost_price': '100.00',
            'description': 'Valid desc'
        })
        self.assertFalse(form3.is_valid())
        self.assertIn('cost_price', form3.errors)

    def test_variant_additional_charge_validation(self):
        """Validate variant additional charge cannot be negative."""
        form = ProductVariantForm(data={
            'product': self.product.id,
            'name': 'Discount Variant',
            'sku': 'VAR-DISC-01',
            'additional_charge': '-100.00'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('additional_charge', form.errors)

    # 5. SECURITY & ACCESS CONTROL
    def test_unauthorized_user_blocked(self):
        """Regular users and anonymous visitors cannot access product management."""
        # Anonymous
        self.client.logout()
        resp_anon = self.client.get(reverse('product_list'))
        self.assertEqual(resp_anon.status_code, 302)

        # Regular non-staff user
        self.client.force_login(self.regular_user)
        resp_user = self.client.get(reverse('product_list'))
        # AdminRequiredMixin redirects unauthorized users
        self.assertEqual(resp_user.status_code, 302)
