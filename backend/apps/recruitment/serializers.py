from rest_framework import serializers
from apps.core.serializers import BranchValidationMixin
from .models import (JobVacancy, Candidate, RecruitmentApplication,
                     RecruitmentNote, ApplicationStageHistory)

class VacancySerializer(BranchValidationMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = JobVacancy
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None


class CandidateSerializer(BranchValidationMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Candidate
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    vacancy_title = serializers.CharField(source="vacancy.title", read_only=True)

    class Meta:
        model = RecruitmentApplication
        fields = ["id", "candidate", "candidate_name", "vacancy", "vacancy_title", "branch",
                  "stage", "rejection_reason", "interview_at", "interview_location", "created_at"]
        read_only_fields = ["id", "branch", "stage", "rejection_reason",
                            "interview_at", "interview_location", "created_at"]

    def get_candidate_name(self, obj):
        return str(obj.candidate)

    def validate(self, attrs):
        candidate, vacancy = attrs["candidate"], attrs["vacancy"]
        user = self.context["request"].user
        if candidate.branch_id != vacancy.branch_id:
            raise serializers.ValidationError("Candidate and vacancy must belong to the same branch.")
        if not user.is_super_admin and vacancy.branch_id not in user.branch_ids():
            raise serializers.ValidationError("You do not have access to this branch.")
        if vacancy.status != JobVacancy.Status.OPEN:
            raise serializers.ValidationError({"vacancy": ["This vacancy is not open."]})
        return attrs

    def create(self, validated):
        validated["branch"] = validated["vacancy"].branch
        return super().create(validated)

class StageChangeSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=RecruitmentApplication.Stage.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    interview_at = serializers.DateTimeField(required=False)
    interview_location = serializers.CharField(required=False, allow_blank=True, default="")

class NoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = RecruitmentNote
        fields = ["id", "note", "author_name", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStageHistory
        fields = ["from_stage", "to_stage", "reason", "changed_by", "created_at"]