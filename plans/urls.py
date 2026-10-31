from django.urls import path
from . import views

urlpatterns = [
    path('', views.PlanListView.as_view(), name='plan_list'),
    path('new/', views.PlanCreateView.as_view(), name='plan_create'),
    path('compare/', views.PlanComparisonMatrixView.as_view(), name='plan_comparison'),
    path('<int:pk>/', views.PlanDetailView.as_view(), name='plan_detail'),
    path('<int:pk>/edit/', views.PlanUpdateView.as_view(), name='plan_update'),
    path('<int:pk>/delete/', views.PlanDeleteView.as_view(), name='plan_delete'),
    path('<int:pk>/toggle-status/', views.PlanToggleStatusView.as_view(), name='plan_toggle_status'),
    path('<int:pk>/calculate-price/', views.PlanCalculatePriceView.as_view(), name='plan_calculate_price'),
    path('<int:plan_pk>/features/new/', views.PlanFeatureCreateView.as_view(), name='plan_feature_create'),
    path('features/<int:pk>/delete/', views.PlanFeatureDeleteView.as_view(), name='plan_feature_delete'),
]
