from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from core.views import AdminRequiredMixin
from core.models import ActivityLog
from core.utils import paginate_queryset
from products.models import Product, ProductVariant
from .models import SubscriptionPlan, PlanFeature
from .forms import SubscriptionPlanForm, PlanFeatureForm

class PlanListView(AdminRequiredMixin, View):
    """
    Subscription Plan Management Overview:
    - Renders both professional SaaS Pricing Cards AND a comprehensive Management Table
    - Admin features: Add, View, Edit, Activate/Deactivate, and Delete when safe
    - Multi-field search and filters by Product, Billing Frequency, Tier, and Status
    """
    template_name = 'plans/plan_list.html'

    def get(self, request):
        queryset = SubscriptionPlan.objects.select_related('product', 'variant').prefetch_related('features', 'subscriptions').all()
        products = Product.objects.all()

        # 1. Search Query
        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(product__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # 2. Filter by Product
        product_id = request.GET.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # 3. Filter by Billing Frequency (Daily, Weekly, Monthly, Yearly)
        billing_cycle = request.GET.get('billing_cycle')
        if billing_cycle:
            if billing_cycle in ['yearly', 'annual']:
                queryset = queryset.filter(billing_cycle__in=['yearly', 'annual'])
            else:
                queryset = queryset.filter(billing_cycle=billing_cycle)

        # 4. Filter by Tier
        tier = request.GET.get('tier')
        if tier:
            queryset = queryset.filter(tier=tier)

        # 5. Filter by Status
        status = request.GET.get('status')
        if status in ['active', 'inactive', 'archived']:
            queryset = queryset.filter(status=status)

        # 6. Sorting
        sort_by = request.GET.get('sort', 'sort_order')
        valid_sorts = {
            'order': 'sort_order',
            'price_asc': 'price',
            'price_desc': '-price',
            'name_asc': 'name',
            'name_desc': '-name',
            'date_desc': '-created_at',
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, 'sort_order'))

        # Metrics for dashboard strip
        total_plans = queryset.count()
        active_plans = SubscriptionPlan.objects.filter(status='active').count()

        page_obj = paginate_queryset(request, queryset, per_page=12)

        context = {
            'page_obj': page_obj,
            'plans': page_obj.object_list,
            'products': products,
            'search_query': search_query,
            'selected_product': product_id,
            'selected_cycle': billing_cycle,
            'selected_tier': tier,
            'selected_status': status,
            'selected_sort': sort_by,
            'total_plans': total_plans,
            'active_plans': active_plans,
            'page_title': 'Subscription Plan Management',
        }
        return render(request, self.template_name, context)


class PlanDetailView(AdminRequiredMixin, View):
    """View plan details, associated subscriptions, policy flags, and feature quotas."""
    template_name = 'plans/plan_detail.html'

    def get(self, request, pk):
        plan = get_object_or_404(
            SubscriptionPlan.objects.select_related('product', 'variant').prefetch_related('features', 'subscriptions'),
            pk=pk
        )
        feature_form = PlanFeatureForm()
        subscriptions = plan.subscriptions.select_related('customer')[:10]

        # Generate sample quantity price tiers for display
        quantity_samples = []
        for qty in [1, 5, 10, 25, 50, 100]:
            if qty >= plan.min_quantity:
                quantity_samples.append({
                    'quantity': qty,
                    'total_price': plan.calculate_price_for_quantity(qty),
                    'unit_price': plan.price,
                })

        can_delete, delete_block_reason = plan.can_be_safely_deleted()

        context = {
            'plan': plan,
            'features': plan.features.all(),
            'feature_form': feature_form,
            'recent_subscriptions': subscriptions,
            'quantity_samples': quantity_samples,
            'can_delete': can_delete,
            'delete_block_reason': delete_block_reason,
            'page_title': f"{plan.name} — Subscription Plan",
        }
        return render(request, self.template_name, context)


class PlanCreateView(AdminRequiredMixin, View):
    """Create a new subscription plan with date validation and quantity rules."""
    template_name = 'plans/plan_form.html'

    def get(self, request):
        initial = {}
        product_id = request.GET.get('product')
        if product_id:
            initial['product'] = product_id

        form = SubscriptionPlanForm(initial=initial)
        context = {
            'form': form,
            'page_title': 'Create Subscription Plan',
            'action': 'Create',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            ActivityLog.objects.create(
                action=f"Created subscription plan '{plan.name}' ({plan.code})",
                category="plan",
                user=request.user,
                details=f"Product: {plan.product.name}, Price: ₹{plan.price}/{plan.get_billing_cycle_display()}, Min Qty: {plan.min_quantity}"
            )
            messages.success(request, f"Subscription plan '{plan.name}' created successfully!")
            return redirect('plan_detail', pk=plan.pk)

        context = {
            'form': form,
            'page_title': 'Create Subscription Plan',
            'action': 'Create',
        }
        return render(request, self.template_name, context)


class PlanUpdateView(AdminRequiredMixin, View):
    """Update existing subscription plan."""
    template_name = 'plans/plan_form.html'

    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        form = SubscriptionPlanForm(instance=plan)
        context = {
            'form': form,
            'plan': plan,
            'page_title': f"Edit Plan: {plan.name}",
            'action': 'Update',
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated plan '{plan.name}'",
                category="plan",
                user=request.user,
                details=f"Price: ₹{plan.price}, Status: {plan.status}, Min Qty: {plan.min_quantity}"
            )
            messages.success(request, f"Plan '{plan.name}' has been updated.")
            return redirect('plan_detail', pk=plan.pk)

        context = {
            'form': form,
            'plan': plan,
            'page_title': f"Edit Plan: {plan.name}",
            'action': 'Update',
        }
        return render(request, self.template_name, context)


class PlanDeleteView(AdminRequiredMixin, View):
    """
    Delete plans when safe.
    PREVENTS DELETION of plans that are currently in use by active subscriptions.
    """
    template_name = 'plans/plan_confirm_delete.html'

    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        can_delete, reason = plan.can_be_safely_deleted()
        context = {
            'plan': plan,
            'can_delete': can_delete,
            'block_reason': reason,
            'active_subscribers': plan.active_subscriptions_count,
            'page_title': f"Delete Plan: {plan.name}",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        can_delete, reason = plan.can_be_safely_deleted()

        if not can_delete:
            messages.error(request, reason)
            return redirect('plan_detail', pk=plan.pk)

        name = plan.name
        code = plan.code
        plan.delete()
        ActivityLog.objects.create(
            action=f"Deleted subscription plan '{name}' ({code})",
            category="plan",
            user=request.user
        )
        messages.success(request, f"Subscription plan '{name}' was safely deleted.")
        return redirect('plan_list')


class PlanToggleStatusView(AdminRequiredMixin, View):
    """One-click activate or deactivate plan toggle."""
    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        new_status = 'inactive' if plan.status == 'active' else 'active'
        plan.status = new_status
        plan.save(update_fields=['status'])
        ActivityLog.objects.create(
            action=f"Changed plan '{plan.name}' status to {new_status.upper()}",
            category="plan",
            user=request.user
        )
        messages.info(request, f"Plan '{plan.name}' is now {new_status.title()}.")
        return redirect('plan_list')


class PlanCalculatePriceView(AdminRequiredMixin, View):
    """AJAX endpoint to calculate total price based on plan and quantity."""
    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        try:
            quantity = int(request.GET.get('qty', 1))
        except (ValueError, TypeError):
            quantity = 1

        effective_qty = max(quantity, plan.min_quantity)
        total_price = plan.calculate_price_for_quantity(effective_qty)

        return JsonResponse({
            'plan_id': plan.id,
            'plan_name': plan.name,
            'unit_price': float(plan.price),
            'min_quantity': plan.min_quantity,
            'requested_quantity': quantity,
            'effective_quantity': effective_qty,
            'total_price': float(total_price),
            'billing_cycle': plan.get_billing_cycle_display(),
        })


class PlanComparisonMatrixView(AdminRequiredMixin, View):
    """Interactive side-by-side plan comparison matrix."""
    template_name = 'plans/plan_comparison.html'

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(status='active').select_related('product', 'variant').prefetch_related('features').order_by('price')
        all_feature_names = list(PlanFeature.objects.filter(plan__in=plans).values_list('name', flat=True).distinct())

        context = {
            'plans': plans,
            'feature_names': all_feature_names,
            'page_title': 'Subscription Plans Comparison Matrix',
        }
        return render(request, self.template_name, context)


class PlanFeatureCreateView(AdminRequiredMixin, View):
    """Add a feature to a subscription plan."""
    def post(self, request, plan_pk):
        plan = get_object_or_404(SubscriptionPlan, pk=plan_pk)
        form = PlanFeatureForm(request.POST)
        if form.is_valid():
            feature = form.save(commit=False)
            feature.plan = plan
            feature.save()
            messages.success(request, f"Feature '{feature.name}' added to plan.")
        else:
            messages.error(request, "Failed to add feature. Please check inputs.")
        return redirect('plan_detail', pk=plan.pk)


class PlanFeatureDeleteView(AdminRequiredMixin, View):
    """Remove a feature from a subscription plan."""
    def post(self, request, pk):
        feature = get_object_or_404(PlanFeature, pk=pk)
        plan_pk = feature.plan.pk
        name = feature.name
        feature.delete()
        messages.success(request, f"Feature '{name}' removed.")
        return redirect('plan_detail', pk=plan_pk)


def index(request):
    """Subscription tiers and pricing plans view."""
    plans = [
        {
            'name': 'Starter Plan',
            'product': 'Brightloop Core',
            'price': '$29',
            'interval': 'Monthly',
            'popular': False,
            'features': ['Up to 5 Users', 'Basic Analytics', 'Standard Support'],
        },
        {
            'name': 'Pro Business',
            'product': 'Brightloop Core + Growth',
            'price': '$99',
            'interval': 'Monthly',
            'popular': True,
            'features': ['Up to 25 Users', 'Advanced BI & Exports', '24/7 Priority Support'],
        },
        {
            'name': 'Enterprise Suite',
            'product': 'Complete SaaS Suite',
            'price': '$299',
            'interval': 'Monthly',
            'popular': False,
            'features': ['Unlimited Users', 'Dedicated SLA', 'Custom Integrations'],
        },
    ]
    return render(request, 'plans/index.html', {
        'page_title': 'Plans & Pricing',
        'active_tab': 'plans',
        'plans': plans,
    })
