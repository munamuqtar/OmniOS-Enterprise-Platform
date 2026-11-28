import django_filters
from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from apps.core.mixins import BranchScopedMixin
from .models import AuditLog
from .serializers import AuditLogSerializer

# "Limited" access from the spec: each role sees only its own modules, in its own branches.
LIMITED = {"hr": {"hr", "recruitment"}, "finance": {"finance"}, "project_manager": {"projects", "timesheets"}}

class AuditPermission(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (u.is_super_admin or bool(u.role_codes & set(LIMITED)))

class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = AuditLog
        fields = ["module", "action", "user", "branch", "record_type", "record_id"]

class AuditLogViewSet(BranchScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").order_by("-created_at")
    serializer_class = AuditLogSerializer
    permission_classes = [AuditPermission]
    filterset_class = AuditLogFilter
    search_fields = ["record_repr", "record_id", "user__username"]

    def get_queryset(self):
        qs = super().get_queryset()            # non-admins: own branches only (rows with no branch are hidden)
        u = self.request.user
        if u.is_super_admin:
            return qs
        modules = set().union(*(LIMITED[r] for r in u.role_codes if r in LIMITED))
        return qs.filter(module__in=modules)