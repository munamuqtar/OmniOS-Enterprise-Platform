import django_filters
from django.db.models import Count, Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from apps.core.responses import ok
from .models import Timesheet
from .serializers import TimesheetSerializer, RejectSerializer, ApprovalSerializer
from . import services

class TimesheetFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="work_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="work_date", lookup_expr="lte")

    class Meta:
        model = Timesheet
        fields = ["status", "project", "task", "employee"]

class TimesheetPermission(BasePermission):
    """Read: HR, Finance, PM, Employee. Write own: Employee, PM. Review: PM. Super Admin: all. Sales: none."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_super_admin:
            return True
        roles = u.role_codes
        if request.method in SAFE_METHODS:
            return bool(roles & {"hr", "finance", "project_manager", "employee"})
        if view.action in ("approve", "reject"):
            return "project_manager" in roles
        return bool(roles & {"employee", "project_manager"})

class TimesheetViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    branch_field = "project__branch_id"
    queryset = Timesheet.objects.select_related("employee", "project", "task").order_by("-work_date", "-created_at")
    serializer_class = TimesheetSerializer
    permission_classes = [TimesheetPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    filterset_class = TimesheetFilter
    search_fields = ["description", "employee__first_name", "employee__last_name",
                     "project__name", "task__title"]

    def get_queryset(self):
        qs = super().get_queryset()                    # branch isolation first
        u = self.request.user
        if u.is_super_admin:
            return qs
        roles = u.role_codes
        q = Q(employee__user=u)                         # everyone sees their own
        if "project_manager" in roles:
            q |= Q(project__manager=u) & ~Q(status="draft")   # projects they manage, never other people's drafts
        if "hr" in roles:
            q |= ~Q(status="draft")                     # HR: read-only, no drafts
        if "finance" in roles:
            q |= Q(status="approved")                   # Finance: approved work only
        return qs.filter(q)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        ts = services.submit(self.get_object(), request.user)
        return ok(self.get_serializer(ts).data, "Timesheet submitted")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        ts = services.approve(self.get_object(), request.user)
        return ok(self.get_serializer(ts).data, "Timesheet approved")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        s = RejectSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ts = services.reject(self.get_object(), request.user, s.validated_data["reason"])
        return ok(self.get_serializer(ts).data, "Timesheet rejected")

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return ok(ApprovalSerializer(self.get_object().approvals.select_related("actor"), many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Hours reporting. Supports the same filters as the list (project, employee, date_from, date_to, status)."""
        qs = self.filter_queryset(self.get_queryset()).order_by()
        by_status = qs.values("status").annotate(hours=Sum("hours"), entries=Count("id"))
        by_project = qs.values("project", "project__project_code", "project__name") \
                       .annotate(hours=Sum("hours"), entries=Count("id"))
        by_employee = qs.values("employee", "employee__employee_number") \
                        .annotate(hours=Sum("hours"), entries=Count("id"))
        return ok({"by_status": list(by_status), "by_project": list(by_project),
                   "by_employee": list(by_employee)})

    @action(detail=False, methods=["get"], url_path="approved-work")
    def approved_work(self, request):
        """Approved hours per project. This is the pool Finance invoices from (Phase 8)."""
        qs = self.filter_queryset(self.get_queryset()).filter(status="approved", invoice_item__isnull=True).order_by()
        rows = qs.values("project", "project__project_code", "project__name") \
                 .annotate(hours=Sum("hours"), entries=Count("id"))
        return ok(list(rows))