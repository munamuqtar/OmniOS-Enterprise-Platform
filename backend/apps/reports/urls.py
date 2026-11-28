from django.urls import path
from .views import (ExecutiveDashboard, HRDashboard, SalesDashboard, ProjectsDashboard, FinanceDashboard)

urlpatterns = [
    path("dashboard/executive/", ExecutiveDashboard.as_view()),
    path("dashboard/hr/", HRDashboard.as_view()),
    path("dashboard/sales/", SalesDashboard.as_view()),
    path("dashboard/projects/", ProjectsDashboard.as_view()),
    path("dashboard/finance/", FinanceDashboard.as_view()),
]