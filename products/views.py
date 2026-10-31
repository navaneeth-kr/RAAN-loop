from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from core.views import AdminRequiredMixin
from core.models import ActivityLog
from core.utils import paginate_queryset
from .models import Product, ProductVariant, ProductCategory
from .forms import ProductForm, ProductVariantForm, ProductCategoryForm

class ProductListView(AdminRequiredMixin, View):
    """
    Admin Table View for Products with Search, Filtering, and Actions:
    1. Add new products
    2. View all products
    3. Edit products
    4. Delete products
    5. Search products
    6. Filter products
    """
    template_name = 'products/product_list.html'

    def get(self, request):
        queryset = Product.objects.select_related('category').prefetch_related('variants', 'plans').all()
        categories = ProductCategory.objects.filter(is_active=True)

        # 1. Search Query
        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(product_type__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(notes__icontains=search_query)
            )

        # 2. Filter by Product Type
        product_type = request.GET.get('product_type')
        if product_type:
            queryset = queryset.filter(product_type=product_type)

        # 3. Filter by Category
        category_id = request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # 4. Filter by Status
        status = request.GET.get('status')
        if status in ['active', 'draft', 'archived']:
            queryset = queryset.filter(status=status)

        # 5. Sorting
        sort_by = request.GET.get('sort', '-created_at')
        valid_sorts = {
            'name_asc': 'name',
            'name_desc': '-name',
            'selling_asc': 'selling_price',
            'selling_desc': '-selling_price',
            'cost_asc': 'cost_price',
            'cost_desc': '-cost_price',
            'date_asc': 'created_at',
            'date_desc': '-created_at',
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, '-created_at'))

        page_obj = paginate_queryset(request, queryset, per_page=10)

        context = {
            'page_obj': page_obj,
            'products': page_obj.object_list,
            'categories': categories,
            'product_types': Product.PRODUCT_TYPE_CHOICES,
            'search_query': search_query,
            'selected_type': product_type,
            'selected_category': category_id,
            'selected_status': status,
            'selected_sort': sort_by,
            'total_count': queryset.count(),
            'page_title': 'Product Management',
        }
        return render(request, self.template_name, context)


class ProductDetailView(AdminRequiredMixin, View):
    """View product specifications, internal notes, variants, and final calculated prices."""
    template_name = 'products/product_detail.html'

    def get(self, request, pk):
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('variants', 'plans'),
            pk=pk
        )
        variants = product.variants.all()
        plans = product.plans.all()

        context = {
            'product': product,
            'variants': variants,
            'plans': plans,
            'page_title': f"{product.name} — Details",
        }
        return render(request, self.template_name, context)


class ProductCreateView(AdminRequiredMixin, View):
    """Create a new product with validated selling and cost prices."""
    template_name = 'products/product_form.html'

    def get(self, request):
        form = ProductForm()
        context = {'form': form, 'page_title': 'Add New Product', 'action': 'Create'}
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                action=f"Created product '{product.name}' ({product.sku})",
                category="product",
                user=request.user,
                details=f"Type: {product.get_product_type_display()}, Selling: ${product.selling_price}, Cost: ${product.cost_price}"
            )
            messages.success(request, f"Product '{product.name}' was created successfully!")
            return redirect('product_detail', pk=product.pk)
        
        context = {'form': form, 'page_title': 'Add New Product', 'action': 'Create'}
        return render(request, self.template_name, context)


class ProductUpdateView(AdminRequiredMixin, View):
    """Edit existing product."""
    template_name = 'products/product_form.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=product)
        context = {'form': form, 'product': product, 'page_title': f"Edit Product: {product.name}", 'action': 'Update'}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated product '{product.name}'",
                category="product",
                user=request.user,
                details=f"Selling: ${product.selling_price}, Cost: ${product.cost_price}"
            )
            messages.success(request, f"Product '{product.name}' has been updated.")
            return redirect('product_detail', pk=product.pk)
        
        context = {'form': form, 'product': product, 'page_title': f"Edit Product: {product.name}", 'action': 'Update'}
        return render(request, self.template_name, context)


class ProductDeleteView(AdminRequiredMixin, View):
    """Delete a product."""
    template_name = 'products/product_confirm_delete.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        context = {'product': product, 'page_title': f"Confirm Delete: {product.name}"}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        sku = product.sku
        product.delete()
        ActivityLog.objects.create(
            action=f"Deleted product '{name}' ({sku})",
            category="product",
            user=request.user
        )
        messages.success(request, f"Product '{name}' was deleted.")
        return redirect('product_list')


# ===================== PRODUCT VARIANTS =====================

class VariantListView(AdminRequiredMixin, View):
    """List variants with auto-calculated final prices."""
    template_name = 'products/variant_list.html'

    def get(self, request):
        queryset = ProductVariant.objects.select_related('product').all()
        products = Product.objects.all()

        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(product__name__icontains=search_query)
            )

        product_id = request.GET.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        tier = request.GET.get('tier')
        if tier:
            queryset = queryset.filter(tier=tier)

        page_obj = paginate_queryset(request, queryset, per_page=10)

        context = {
            'page_obj': page_obj,
            'variants': page_obj.object_list,
            'products': products,
            'search_query': search_query,
            'selected_product': product_id,
            'selected_tier': tier,
            'total_count': queryset.count(),
            'page_title': 'Product Variants Matrix',
        }
        return render(request, self.template_name, context)


class VariantCreateView(AdminRequiredMixin, View):
    """Create a new product variant with auto price calculation."""
    template_name = 'products/variant_form.html'

    def _get_products_map(self):
        return {
            str(p.id): {
                'name': p.name,
                'selling_price': float(p.selling_price),
                'currency': '₹'
            }
            for p in Product.objects.all()
        }

    def get(self, request):
        initial = {}
        product_id = request.GET.get('product')
        if product_id:
            initial['product'] = product_id

        form = ProductVariantForm(initial=initial)
        context = {
            'form': form,
            'page_title': 'Add Product Variant',
            'action': 'Create',
            'products_map': self._get_products_map(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save()
            ActivityLog.objects.create(
                action=f"Created variant '{variant.name}' for '{variant.product.name}'",
                category="variant",
                user=request.user,
                details=f"Base: ${variant.base_price} + Extra: ${variant.additional_charge} = Final: ${variant.final_price}"
            )
            messages.success(request, f"Variant '{variant.name}' created! Final Price: ${variant.final_price}")
            return redirect('product_detail', pk=variant.product.pk)

        context = {
            'form': form,
            'page_title': 'Add Product Variant',
            'action': 'Create',
            'products_map': self._get_products_map(),
        }
        return render(request, self.template_name, context)


class VariantUpdateView(AdminRequiredMixin, View):
    """Edit existing product variant."""
    template_name = 'products/variant_form.html'

    def _get_products_map(self):
        return {
            str(p.id): {
                'name': p.name,
                'selling_price': float(p.selling_price),
                'currency': '₹'
            }
            for p in Product.objects.all()
        }

    def get(self, request, pk):
        variant = get_object_or_404(ProductVariant.objects.select_related('product'), pk=pk)
        form = ProductVariantForm(instance=variant)
        context = {
            'form': form,
            'variant': variant,
            'page_title': f"Edit Variant: {variant.name}",
            'action': 'Update',
            'products_map': self._get_products_map(),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated variant '{variant.name}' ({variant.sku})",
                category="variant",
                user=request.user,
                details=f"Final Price: ${variant.final_price}"
            )
            messages.success(request, f"Variant '{variant.name}' updated! Final Price: ${variant.final_price}")
            return redirect('product_detail', pk=variant.product.pk)

        context = {
            'form': form,
            'variant': variant,
            'page_title': f"Edit Variant: {variant.name}",
            'action': 'Update',
            'products_map': self._get_products_map(),
        }
        return render(request, self.template_name, context)


class VariantDeleteView(AdminRequiredMixin, View):
    """Delete product variant."""
    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        product_pk = variant.product.pk
        name = variant.name
        variant.delete()
        ActivityLog.objects.create(
            action=f"Deleted variant '{name}'",
            category="variant",
            user=request.user
        )
        messages.success(request, f"Variant '{name}' was deleted.")
        return redirect('product_detail', pk=product_pk)


def index(request):
    """SaaS products catalog foundation view."""
    products = [
        {'code': 'PRD-CLOUD', 'name': 'Brightloop Cloud Platform', 'category': 'Infrastructure', 'plans_count': 3, 'status': 'Active'},
        {'code': 'PRD-ANALYTICS', 'name': 'Brightloop Analytics Suite', 'category': 'Data & BI', 'plans_count': 2, 'status': 'Active'},
        {'code': 'PRD-SECURITY', 'name': 'Brightloop Secure Shield', 'category': 'Cybersecurity', 'plans_count': 3, 'status': 'Active'},
    ]
    return render(request, 'products/index.html', {
        'page_title': 'Products Catalog',
        'active_tab': 'products',
        'products': products,
    })
