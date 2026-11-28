import uuid
from decimal import Decimal
from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from apps.core.responses import ok
from apps.timesheets.models import Timesheet
from .models import Invoice, Payment
from .serializers import (InvoiceSerializer, CancelSerializer, InvoiceHistorySerializer, PaymentSerializer)
from . import services

def is_finance(u):
    return u.is_super_admin or "finance" in u.role_codes

class FinanceOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_finance(request.user)

class InvoicePermission(BasePermission):
    """Finance and Super Admin: full. Sales and Project Manager: read only (limited scope)."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if is_finance(u):
            return True
        return request.method in SAFE_METHODS and bool(u.role_codes & {"sales", "project_manager"})

class InvoiceViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("client", "project", "branch") \
                              .prefetch_related("items").order_by("-created_at")
    serializer_class = InvoiceSerializer
    permission_classes = [InvoicePermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["invoice_number", "client__name", "project__name", "project__project_code"]
    filterset_fields = ["status", "branch", "client", "project", "currency"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        services.mark_overdue()

    def get_queryset(self):
        qs = super().get_queryset()                       # branch isolation first
        u = self.request.user
        if is_finance(u) or "sales" in u.role_codes:
            return qs
        return qs.filter(project__manager=u)              # Project Manager: only projects they manage

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        ids, rate = data.pop("timesheet_ids"), data.pop("hourly_rate")
        inv = services.create_invoice(request.user, ids, rate, **data)
        return ok(self.get_serializer(inv).data, "Invoice created", status=201)

    def update(self, request, *args, **kwargs):
        inv = self.get_object()
        s = self.get_serializer(inv, data=request.data, partial=kwargs.get("partial", False))
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        ids, rate = data.pop("timesheet_ids", None), data.pop("hourly_rate", None)
        inv = services.update_invoice(inv, ids, rate, **data)
        return ok(self.get_serializer(inv).data, "Invoice updated")

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        return ok(self.get_serializer(services.issue(self.get_object(), request.user)).data, "Invoice issued")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        s = CancelSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        inv = services.cancel(self.get_object(), request.user, s.validated_data["reason"])
        return ok(self.get_serializer(inv).data, "Invoice cancelled")

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return ok(InvoiceHistorySerializer(self.get_object().history.all(), many=True).data)

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        qs = self.get_object().payments.select_related("invoice", "client").order_by("created_at")
        return ok(PaymentSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], permission_classes=[FinanceOnly])
    def billable(self, request):
        """Approved timesheets of a project that are not billed yet. This is what Finance picks from."""
        try:
            pid = uuid.UUID(str(request.query_params.get("project", "")))
        except ValueError:
            raise ValidationError({"project": ["A valid project id is required."]})
        qs = Timesheet.objects.filter(project_id=pid, status="approved", invoice_item__isnull=True) \
                              .select_related("employee", "task").order_by("work_date")
        if not request.user.is_super_admin:
            qs = qs.filter(project__branch_id__in=request.user.branch_ids())
        rows = [{"id": t.id, "work_date": t.work_date, "hours": t.hours, "task_id": t.task_id,
                 "task": t.task.title, "employee": f"{t.employee.first_name} {t.employee.last_name}"} for t in qs]
        return ok({"count": len(rows), "total_hours": sum((r["hours"] for r in rows), Decimal("0")),
                   "timesheets": rows})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Financial report. Grouped by currency because amounts in different currencies cannot be added."""
        qs = self.filter_queryset(self.get_queryset()).order_by()
        rows = qs.values("currency", "status").annotate(
            count=Count("id"), total=Sum("total"), paid=Sum("amount_paid"), balance=Sum("balance"))
        return ok(list(rows))

class PaymentViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    branch_field = "invoice__branch_id"
    queryset = Payment.objects.select_related("invoice", "client").order_by("-created_at")
    serializer_class = PaymentSerializer
    permission_classes = [FinanceOnly]
    http_method_names = ["get", "post", "head", "options"]
    search_fields = ["payment_number", "reference", "invoice__invoice_number", "client__name"]
    filterset_fields = ["status", "invoice", "client", "method"]

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        payment = services.record_payment(request.user, data.pop("invoice"), **data)
        return ok(self.get_serializer(payment).data, "Payment recorded", status=201)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        p = services.confirm_payment(self.get_object(), request.user,
                                     allow_overpayment=request.data.get("allow_overpayment") is True)
        return ok(self.get_serializer(p).data, "Payment confirmed")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        s = CancelSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        p = services.reject_payment(self.get_object(), request.user, s.validated_data["reason"])
        return ok(self.get_serializer(p).data, "Payment rejected")

    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        p = services.reconcile_payment(self.get_object(), request.user)
        return ok(self.get_serializer(p).data, "Payment reconciled")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Reconciliation status: how many payments and how much money sit in each status."""
        qs = self.filter_queryset(self.get_queryset()).order_by()
        return ok(list(qs.values("status", "invoice__currency").annotate(count=Count("id"), total=Sum("amount"))))