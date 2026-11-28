from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from apps.core.responses import ok
from .models import Quote
from .serializers import QuoteSerializer, RejectSerializer, ApprovalSerializer
from . import services
from .serializers import ConvertQuoteSerializer
from apps.projects.serializers import ProjectSerializer

class QuotePermission(BasePermission):
    """Sales and Super Admin: full. Finance: read only (needed for invoicing)."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_super_admin or "sales" in u.role_codes:
            return True
        return request.method in SAFE_METHODS and "finance" in u.role_codes

class QuoteViewSet(BranchScopedMixin, viewsets.ModelViewSet):

    queryset = Quote.objects.select_related("client", "lead", "branch", "created_by") \
                            .prefetch_related("items").order_by("-created_at")
    serializer_class = QuoteSerializer
    permission_classes = [QuotePermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["quote_number", "client__name", "lead__name"]
    filterset_fields = ["status", "branch", "client", "created_by", "currency"]

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        items = data.pop("items")
        quote = services.create_quote(request.user, items, **data)
        return ok(self.get_serializer(quote).data, "Quotation created", status=201)

    def update(self, request, *args, **kwargs):
        quote = self.get_object()
        s = self.get_serializer(quote, data=request.data, partial=kwargs.get("partial", False))
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        items = data.pop("items", None)
        quote = services.update_quote(quote, items, **data)
        return ok(self.get_serializer(quote).data, "Quotation updated")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return ok(self.get_serializer(services.submit(self.get_object(), request.user)).data,
                  "Submitted for approval")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return ok(self.get_serializer(services.approve(self.get_object(), request.user)).data,
                  "Quotation approved")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        s = RejectSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        quote = services.reject(self.get_object(), request.user, s.validated_data["reason"])
        return ok(self.get_serializer(quote).data, "Quotation rejected")

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        return ok(self.get_serializer(services.revise(self.get_object(), request.user)).data,
                  "Quotation reopened for revision")

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        s = ConvertQuoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        quote, project = services.convert_to_project(self.get_object(), request.user, **s.validated_data)
        return ok({"quote": self.get_serializer(quote).data,
                   "project": ProjectSerializer(project, context={"request": request}).data},
                  "Quotation converted to project", status=201)

    @action(detail=True, methods=["get"])
    def approvals(self, request, pk=None):
        return ok(ApprovalSerializer(self.get_object().approvals.select_related("actor"), many=True).data)

    @action(detail=False, methods=["get"], url_path="pending-approval")
    def pending_approval(self, request):
        qs = self.filter_queryset(self.get_queryset()).filter(status="pending_approval")
        return ok(self.get_serializer(qs, many=True).data)