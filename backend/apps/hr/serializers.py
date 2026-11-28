import uuid
from rest_framework import serializers
from apps.core.serializers import BranchValidationMixin
from .models import Department, Employee

from apps.core.serializers import BranchValidationMixin, DefaultOrganizationMixin

class DepartmentSerializer(DefaultOrganizationMixin, serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"organization": {"required": False}}

class EmployeeSerializer(BranchValidationMixin, serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"employee_number": {"required": False}}

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None
    
    def validate(self, attrs):
        dept = attrs.get("department", getattr(self.instance, "department", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if dept and branch and dept.organization_id != branch.organization_id:
            raise serializers.ValidationError({"department": ["Department belongs to a different organization."]})
        return attrs

    def create(self, validated):
        if not validated.get("employee_number"):
            validated["employee_number"] = "EMP-" + uuid.uuid4().hex[:6].upper()
        return super().create(validated)