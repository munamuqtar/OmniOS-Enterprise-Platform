from rest_framework import serializers
from apps.core.serializers import BranchValidationMixin
from .models import Client, Lead, LeadActivity, LeadStatusHistory
from .models import Opportunity

class ClientSerializer(BranchValidationMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_email(self, value):
        qs = Client.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A client with this email already exists.")
        return value

class LeadSerializer(BranchValidationMixin, serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = ["id", "status", "unqualified_reason", "converted_client",
                            "business_requirement", "budget", "customer_interest",
                            "expected_timeline", "created_by", "created_at", "updated_at"]

    def validate_owner(self, owner):
        branch = self.initial_data.get("branch") or getattr(self.instance, "branch_id", None)
        if owner and branch and not owner.is_super_admin and str(branch) not in map(str, owner.branch_ids()):
            raise serializers.ValidationError("Assigned salesperson has no access to this branch.")
        return owner

    def validate(self, attrs):
        if self.instance and self.instance.status == "converted":
            raise serializers.ValidationError("Converted leads cannot be edited.")
        return attrs

class QualifySerializer(serializers.Serializer):
    business_requirement = serializers.CharField()
    budget = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    customer_interest = serializers.CharField()
    expected_timeline = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)

class UnqualifySerializer(serializers.Serializer):
    reason = serializers.CharField()

class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["contacted", "pending"])   # follow-up states only
    reason = serializers.CharField(required=False, allow_blank=True, default="")

class ConvertSerializer(serializers.Serializer):
    address = serializers.CharField(required=False, allow_blank=True, default="")
    contact_person = serializers.CharField(required=False, allow_blank=True, default="")

class ActivitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = LeadActivity
        fields = ["id", "kind", "description", "activity_date", "next_follow_up",
                  "created_by_name", "created_at"]
        read_only_fields = ["id", "created_by_name", "created_at"]

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatusHistory
        fields = ["from_status", "to_status", "reason", "changed_by", "created_at"]




class OpportunitySerializer(BranchValidationMixin, serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = ["id", "stage", "lost_reason", "created_by", "created_at", "updated_at"]

    def validate_value(self, v):
        if v < 0:
            raise serializers.ValidationError("Value cannot be negative.")
        return v

    def validate_probability(self, p):
        if not 0 <= p <= 100:
            raise serializers.ValidationError("Probability must be between 0 and 100.")
        return p

    def validate(self, attrs):
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        client = attrs.get("client", getattr(self.instance, "client", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if not lead and not client:
            raise serializers.ValidationError("An opportunity needs a lead or a client.")
        for obj in (lead, client):
            if obj and branch and obj.branch_id != branch.id:
                raise serializers.ValidationError("Lead/client must belong to the same branch.")
        if self.instance and self.instance.stage in ("won", "lost"):
            raise serializers.ValidationError("Closed opportunities cannot be edited.")
        return attrs

class OppStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Opportunity.Stage.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")