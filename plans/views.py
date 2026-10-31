from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Q, Count
from .models import SubscriptionPlan, PlanFeature
from .forms import SubscriptionPlanForm, PlanFeatureForm
from products.models import Product
from core.models import ActivityLog
from core.utils import paginate_queryset

class PlanListView(View):
    """List subscription plans with search, multi-filters, and pagination."""
    template_name = 'plans/plan_list.html'

    def get(self, request):
        queryset = SubscriptionPlan.objects.select_related('product', 'variant').prefetch_related('features').all()
        products = Product.objects.filter(status='active')

        # Search Query
        search_query = request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(product__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Product Filter
        product_id = request.GET.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Tier Filter
        tier = request.GET.get('tier')
        if tier:
            queryset = queryset.filter(tier=tier)

        # Billing Cycle Filter
        billing_cycle = request.GET.get('billing_cycle')
        if billing_cycle:
            queryset = queryset.filter(billing_cycle=billing_cycle)

        # Status Filter
        status = request.GET.get('status')
        if status in ['active', 'inactive', 'archived']:
            queryset = queryset.filter(status=status)

        # Sorting
        sort_by = request.GET.get('sort', 'sort_order')
        valid_sorts = {
            'order': 'sort_order',
            'price_asc': 'price',
            'price_desc': '-price',
            'name_asc': 'name',
            'name_desc': '-name',
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, 'sort_order'))

        page_obj = paginate_queryset(request, queryset, per_page=9)

        context = {
            'page_obj': page_obj,
            'plans': page_obj.object_list,
            'products': products,
            'search_query': search_query,
            'selected_product': product_id,
            'selected_tier': tier,
            'selected_cycle': billing_cycle,
            'selected_status': status,
            'selected_sort': sort_by,
            'total_count': queryset.count(),
            'page_title': 'Subscription Plan Management',
        }
        return render(request, self.template_name, context)


class PlanDetailView(View):
    """View plan details, associated subscriptions, and features."""
    template_name = 'plans/plan_detail.html'

    def get(self, request, pk):
        plan = get_object_or_404(
            SubscriptionPlan.objects.select_related('product', 'variant').prefetch_related('features', 'subscriptions'),
            pk=pk
        )
        feature_form = PlanFeatureForm()
        subscriptions = plan.subscriptions.select_related('customer')[:10]

        context = {
            'plan': plan,
            'features': plan.features.all(),
            'feature_form': feature_form,
            'recent_subscriptions': subscriptions,
            'page_title': f"{plan.name} — Subscription Plan",
        }
        return render(request, self.template_name, context)


class PlanCreateView(View):
    """Create a new subscription plan."""
    template_name = 'plans/plan_form.html'

    def get(self, request):
        initial = {}
        product_id = request.GET.get('product')
        if product_id:
            initial['product'] = product_id
            
        form = SubscriptionPlanForm(initial=initial)
        context = {'form': form, 'page_title': 'Create Subscription Plan', 'action': 'Create'}
        return render(request, self.template_name, context)

    def post(self, request):
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            ActivityLog.objects.create(
                action=f"Created subscription plan '{plan.name}' ({plan.code})",
                category="plan",
                user=request.user if request.user.is_authenticated else None,
                details=f"Product: {plan.product.name}, Price: ${plan.price}/{plan.billing_cycle}"
            )
            messages.success(request, f"Subscription plan '{plan.name}' created successfully!")
            return redirect('plan_detail', pk=plan.pk)

        context = {'form': form, 'page_title': 'Create Subscription Plan', 'action': 'Create'}
        return render(request, self.template_name, context)


class PlanUpdateView(View):
    """Update existing subscription plan."""
    template_name = 'plans/plan_form.html'

    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        form = SubscriptionPlanForm(instance=plan)
        context = {'form': form, 'plan': plan, 'page_title': f"Edit Plan: {plan.name}", 'action': 'Update'}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action=f"Updated plan '{plan.name}'",
                category="plan",
                user=request.user if request.user.is_authenticated else None,
                details=f"Price: ${plan.price}, Status: {plan.status}"
            )
            messages.success(request, f"Plan '{plan.name}' has been updated.")
            return redirect('plan_detail', pk=plan.pk)

        context = {'form': form, 'plan': plan, 'page_title': f"Edit Plan: {plan.name}", 'action': 'Update'}
        return render(request, self.template_name, context)


class PlanDeleteView(View):
    """Delete a subscription plan."""
    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        name = plan.name
        product_pk = plan.product.pk
        plan.delete()
        ActivityLog.objects.create(
            action=f"Deleted plan '{name}'",
            category="plan",
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Plan '{name}' was deleted.")
        return redirect('plan_list')


class PlanToggleStatusView(View):
    """One-click toggle between active and inactive plan status."""
    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        new_status = 'inactive' if plan.status == 'active' else 'active'
        plan.status = new_status
        plan.save(update_fields=['status'])
        ActivityLog.objects.create(
            action=f"Changed plan '{plan.name}' status to {new_status.upper()}",
            category="plan",
            user=request.user if request.user.is_authenticated else None
        )
        messages.info(request, f"Plan '{plan.name}' status changed to {new_status.title()}.")
        return redirect('plan_list')


class PlanComparisonMatrixView(View):
    """Interactive side-by-side plan comparison matrix."""
    template_name = 'plans/plan_comparison.html'

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(status='active').select_related('product', 'variant').prefetch_related('features').order_by('price')
        
        # Collect distinct feature names across active plans
        all_feature_names = list(PlanFeature.objects.filter(plan__in=plans).values_list('name', flat=True).distinct())

        context = {
            'plans': plans,
            'feature_names': all_feature_names,
            'page_title': 'Subscription Plans Comparison Matrix',
        }
        return render(request, self.template_name, context)


class PlanFeatureCreateView(View):
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


class PlanFeatureDeleteView(View):
    """Remove a feature from a subscription plan."""
    def post(self, request, pk):
        feature = get_object_or_404(PlanFeature, pk=pk)
        plan_pk = feature.plan.pk
        name = feature.name
        feature.delete()
        messages.success(request, f"Feature '{name}' removed.")
        return redirect('plan_detail', pk=plan_pk)
