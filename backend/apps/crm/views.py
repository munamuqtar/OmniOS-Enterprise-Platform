from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from apps.core.permissions import HasRole
from apps.core.responses import ok
from .models import Client, Lead
from . import services
from apps.notifications import events      # adjust to wherever `events` actually lives
from .serializers import (ClientSerializer, LeadSerializer, QualifySerializer, UnqualifySerializer,
                          StatusSerializer, ConvertSerializer, ActivitySerializer, HistorySerializer)
from . import services
from django.db.models import Sum, Count
from .models import Opportunity
from .serializers import OpportunitySerializer, OppStageSerializer

SALES = [IsAuthenticated, HasRole.of("sales")]   # Super Admin always passes

class LeadViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Lead.objects.select_related("owner", "branch", "converted_client").order_by("-created_at")
    serializer_class = LeadSerializer
    permission_classes = SALES
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "company_name", "email", "phone"]
    filterset_fields = ["status", "branch", "owner", "source"]

    def perform_create(self, serializer):
        user = self.request.user
        lead = serializer.save(created_by=user, owner=serializer.validated_data.get("owner") or user)
        events.lead_assigned(lead, user)          # <-- new line

    def perform_update(self, serializer):         # <-- new method
        old_owner = serializer.instance.owner_id
        lead = serializer.save()
        if lead.owner_id and lead.owner_id != old_owner:
            events.lead_assigned(lead, self.request.user)

    @action(detail=True, methods=["post"])
    def qualify(self, request, pk=None):
        s = QualifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lead = services.qualify(self.get_object(), request.user, s.validated_data)
        return ok(LeadSerializer(lead, context={"request": request}).data, "Lead qualified")

    @action(detail=True, methods=["post"])
    def unqualify(self, request, pk=None):
        s = UnqualifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lead = services.mark_unqualified(self.get_object(), request.user, s.validated_data["reason"])
        return ok(LeadSerializer(lead, context={"request": request}).data, "Lead marked unqualified")

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        s = StatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lead = services.change_status(self.get_object(), s.validated_data["status"],
                                      request.user, s.validated_data["reason"])
        return ok(LeadSerializer(lead, context={"request": request}).data, "Status updated")

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        s = ConvertSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lead, client = services.convert_to_client(self.get_object(), request.user, **s.validated_data)
        return ok({"lead": LeadSerializer(lead, context={"request": request}).data,
                   "client": ClientSerializer(client, context={"request": request}).data},
                  "Lead converted to client", status=201)

    @action(detail=True, methods=["get", "post"])
    def activities(self, request, pk=None):
        lead = self.get_object()
        if request.method == "POST":
            s = ActivitySerializer(data=request.data)
            s.is_valid(raise_exception=True)
            s.save(lead=lead, created_by=request.user)
            return ok(s.data, "Activity added", status=201)
        return ok(ActivitySerializer(lead.activities.select_related("created_by"), many=True).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return ok(HistorySerializer(self.get_object().history.all(), many=True).data)

class ClientPermission(BasePermission):
    """Sales and Super Admin write. Finance and Project Manager can read (needed for invoices/projects)."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_super_admin or "sales" in u.role_codes:
            return True
        return request.method in SAFE_METHODS and bool(u.role_codes & {"finance", "project_manager"})

class ClientViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Client.objects.select_related("branch").order_by("-created_at")
    serializer_class = ClientSerializer
    permission_classes = [ClientPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "company_name", "email", "phone"]
    filterset_fields = ["status", "branch"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Client history. Quotes/projects/invoices are added to this in later phases."""
        client = self.get_object()
        lead = getattr(client, "source_lead", None)
        return ok({"client": ClientSerializer(client, context={"request": request}).data,
                   "source_lead": str(lead.id) if lead else None,
                   "lead_history": HistorySerializer(lead.history.all(), many=True).data if lead else []})



class OpportunityViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Opportunity.objects.select_related("lead", "client", "owner", "branch").order_by("-created_at")
    serializer_class = OpportunitySerializer
    permission_classes = SALES
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "client__name", "lead__name"]
    filterset_fields = ["stage", "branch", "owner", "client"]

    def perform_create(self, serializer):
        u = self.request.user
        serializer.save(created_by=u, owner=serializer.validated_data.get("owner") or u)

    @action(detail=True, methods=["post"])
    def stage(self, request, pk=None):
        s = OppStageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        opp = services.change_opp_stage(self.get_object(), s.validated_data["stage"],
                                        request.user, s.validated_data["reason"])
        return ok(OpportunitySerializer(opp, context={"request": request}).data, "Stage updated")

    @action(detail=False, methods=["get"])
    def pipeline(self, request):
        """Sales pipeline: count and value per stage (branch-scoped)."""
        qs = self.filter_queryset(self.get_queryset()).order_by()
        rows = {r["stage"]: r for r in qs.values("stage").annotate(n=Count("id"), total=Sum("value"))}
        return ok([{"stage": s, "count": rows.get(s, {}).get("n", 0),
                    "value": rows.get(s, {}).get("total") or 0} for s, _ in Opportunity.Stage.choices])