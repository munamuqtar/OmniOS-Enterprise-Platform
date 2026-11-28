from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import BranchScopedMixin
from apps.core.permissions import HasRole
from apps.core.responses import ok
from .models import JobVacancy, Candidate, RecruitmentApplication
from .serializers import (VacancySerializer, CandidateSerializer, ApplicationSerializer,
                          StageChangeSerializer, NoteSerializer, HistorySerializer)
from .services import change_stage

HR_ONLY = [IsAuthenticated, HasRole.of("hr")]   # Super Admin always passes HasRole

class VacancyViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = JobVacancy.objects.select_related("department", "branch").order_by("-created_at")
    serializer_class = VacancySerializer
    permission_classes = HR_ONLY
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["title", "description"]
    filterset_fields = ["status", "branch", "department"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CandidateViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Candidate.objects.order_by("-created_at")
    serializer_class = CandidateSerializer
    permission_classes = HR_ONLY
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    filterset_fields = ["branch", "source"]

class ApplicationViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = RecruitmentApplication.objects.select_related("candidate", "vacancy").order_by("-created_at")
    serializer_class = ApplicationSerializer
    permission_classes = HR_ONLY
    http_method_names = ["get", "post", "head", "options"]
    search_fields = ["candidate__first_name", "candidate__last_name", "vacancy__title"]
    filterset_fields = ["stage", "branch", "vacancy", "candidate"]

    @action(detail=True, methods=["post"])
    def stage(self, request, pk=None):
        app = self.get_object()
        s = StageChangeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        app = change_stage(app, d["stage"], request.user, d["reason"],
                           d.get("interview_at"), d["interview_location"])
        return ok(ApplicationSerializer(app).data, "Stage updated")

    @action(detail=True, methods=["get", "post"])
    def notes(self, request, pk=None):
        app = self.get_object()
        if request.method == "POST":
            s = NoteSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            s.save(application=app, author=request.user)
            return ok(s.data, "Note added", status=201)
        return ok(NoteSerializer(app.notes.select_related("author"), many=True).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return ok(HistorySerializer(self.get_object().history.all(), many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset()).order_by()
        counts = dict(qs.values_list("stage").annotate(n=Count("id")))
        return ok({stage: counts.get(stage, 0) for stage, _ in RecruitmentApplication.Stage.choices})