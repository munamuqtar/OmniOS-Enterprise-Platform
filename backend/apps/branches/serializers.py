from rest_framework import serializers
from apps.core.serializers import DefaultOrganizationMixin
from .models import Branch

class BranchSerializer(DefaultOrganizationMixin, serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"organization": {"required": False}}

    def get_manager_name(self, obj):
        m = obj.manager
        return (f"{m.first_name} {m.last_name}".strip() or m.username) if m else None