from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Q
from .models import Product, ProductVariant, ProductCategory
from .forms import ProductForm, ProductVariantForm, ProductCategoryForm
from core.models import ActivityLog
from core.utils import paginate_queryset

class ProductListView(View):
    """List products with multi-criteria search, filters, sorting, and pagination."""
    template_name = 'products/product_list.html'

    def get(self, request):
        queryset = Product.objects.select_related('category').prefetch_related('variants', 'plans').all()
        categories = ProductCategory.objects.filter(is_active=True)

        # Search Query
        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(tagline__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Category Filter
        category_id = request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Status Filter
        status = request.GET.get('status')
        if status in ['active', 'draft', 'archived']:
            queryset = queryset.filter(status=status)

        # Sorting
        sort_by = request.GET.get('sort', '-created_at')
        valid_sorts = {
            'name_asc': 'name',
            'name_desc': '-name',
            'price_asc': 'base_price',
            'price_desc': '-base_price',
            'date_asc': 'created_at',
            'date_desc': '-created_at',
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, '-created_at'))

        page_obj = paginate_queryset(request, queryset, per_page=9)

        context = {
            'page_obj': page_obj,
            'products': page_obj.object_list,
            'categories': categories,
            'search_query': search_query,
            'selected_category': category_id,
            'selected_status': status,
            'selected_sort': sort_by,
            'total_count': queryset.count(),
            'page_title': 'Product Catalog Management',
        }
        return render(request, self.template_name, context)


class ProductDetailView(View):
    """Detailed overview of a single product with variants and plans."""
    template_name = 'products/product_detail.html'

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related('category').prefetch_related('variants', 'plans'), pk=pk)
        variants = product.variants.all()
        plans = product.plans.all()

        context = {
            'product': product,
            'variants': variants,
            'plans': plans,
            'page_title': f"{product.name} — Product Details",
        }
        return render(request, self.template_name, context)


class ProductCreateView(View):
    """Create a new SaaS product."""
    template_name = 'products/product_form.html'

    def get(self, request):
        form = ProductForm()
        context = {'form': form, 'page_title': 'Add New SaaS Product', 'action': 'Create'}
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                action=f"Created product '{product.name}' ({product.sku})",
                category="product",
                user=request.user if request.user.is_authenticated else None,
                details=f"Base Price: ${product.base_price}, Status: {product.status}"
            )
            messages.success(request, f"Product '{product.name}' was created successfully!")
            return redirect('product_detail', pk=product.pk)
        
        context = {'form': form, 'page_title': 'Add New SaaS Product', 'action': 'Create'}
        return render(request, self.template_name, context)


class ProductUpdateView(View):
    """Edit existing SaaS product."""
    template_name = 'products/product_form.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=product)
        context = {'form': form, 'product': product, 'page_title': f"Edit {product.name}", 'action': 'Update'}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated product '{product.name}'",
                category="product",
                user=request.user if request.user.is_authenticated else None,
                details=f"Status: {product.status}, Price: ${product.base_price}"
            )
            messages.success(request, f"Product '{product.name}' has been updated.")
            return redirect('product_detail', pk=product.pk)
        
        context = {'form': form, 'product': product, 'page_title': f"Edit {product.name}", 'action': 'Update'}
        return render(request, self.template_name, context)


class ProductDeleteView(View):
    """Delete or archive product."""
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
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Product '{name}' was permanently removed.")
        return redirect('product_list')


# ===================== PRODUCT VARIANTS =====================

class VariantListView(View):
    """List variants with filtering by tier, cycle, product, and pagination."""
    template_name = 'products/variant_list.html'

    def get(self, request):
        queryset = ProductVariant.objects.select_related('product').all()
        products = Product.objects.filter(status='active')

        # Filters
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

        billing_cycle = request.GET.get('billing_cycle')
        if billing_cycle:
            queryset = queryset.filter(billing_cycle=billing_cycle)

        sort_by = request.GET.get('sort', 'price')
        if sort_by in ['price', '-price', 'name', '-name', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort_by)

        page_obj = paginate_queryset(request, queryset, per_page=10)

        context = {
            'page_obj': page_obj,
            'variants': page_obj.object_list,
            'products': products,
            'search_query': search_query,
            'selected_product': product_id,
            'selected_tier': tier,
            'selected_cycle': billing_cycle,
            'selected_sort': sort_by,
            'total_count': queryset.count(),
            'page_title': 'Product Variants Matrix',
        }
        return render(request, self.template_name, context)


class VariantCreateView(View):
    """Create a new product variant."""
    template_name = 'products/variant_form.html'

    def get(self, request):
        initial = {}
        product_id = request.GET.get('product')
        if product_id:
            initial['product'] = product_id

        form = ProductVariantForm(initial=initial)
        context = {'form': form, 'page_title': 'Add Product Variant', 'action': 'Create'}
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save()
            ActivityLog.objects.create(
                action=f"Created variant '{variant.name}' for '{variant.product.name}'",
                category="variant",
                user=request.user if request.user.is_authenticated else None,
                details=f"Tier: {variant.tier}, Price: ${variant.price}/{variant.billing_cycle}"
            )
            messages.success(request, f"Variant '{variant.name}' created successfully!")
            return redirect('product_detail', pk=variant.product.pk)

        context = {'form': form, 'page_title': 'Add Product Variant', 'action': 'Create'}
        return render(request, self.template_name, context)


class VariantUpdateView(View):
    """Edit existing product variant."""
    template_name = 'products/variant_form.html'

    def get(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        form = ProductVariantForm(instance=variant)
        context = {'form': form, 'variant': variant, 'page_title': f"Edit Variant: {variant.name}", 'action': 'Update'}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated variant '{variant.name}' ({variant.sku})",
                category="variant",
                user=request.user if request.user.is_authenticated else None
            )
            messages.success(request, f"Variant '{variant.name}' was updated.")
            return redirect('variant_list')

        context = {'form': form, 'variant': variant, 'page_title': f"Edit Variant: {variant.name}", 'action': 'Update'}
        return render(request, self.template_name, context)


class VariantDeleteView(View):
    """Delete product variant."""
    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        product_pk = variant.product.pk
        name = variant.name
        variant.delete()
        ActivityLog.objects.create(
            action=f"Deleted variant '{name}'",
            category="variant",
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Variant '{name}' was deleted.")
        return redirect('product_detail', pk=product_pk)
