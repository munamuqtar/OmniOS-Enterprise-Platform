import datetime
from decimal import Decimal
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from apps.hr.models import Employee
from .models import Timesheet, TimesheetApproval

class TimesheetSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.name", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Timesheet
        fields = ["id", "employee", "employee_name", "project", "project_name", "task", "task_title",
                  "work_date", "hours", "description", "status", "is_mine", "rejection_reason",
                  "reviewed_by", "reviewed_at", "invoice_item", "created_at", "updated_at"]
        read_only_fields = ["id", "employee", "status", "rejection_reason", "reviewed_by",
                            "reviewed_at", "invoice_item", "created_at", "updated_at"]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.employee.user_id == request.user.id)

    # validate_hours, validate, RejectSerializer and ApprovalSerializer stay exactly as they are
    def validate_hours(self, v):
        if v <= 0 or v > 24:
            raise serializers.ValidationError("Hours must be greater than 0 and at most 24.")
        return v

    def validate(self, attrs):
        user = self.context["request"].user
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))

        if self.instance:
            if self.instance.employee.user_id != user.id:
                raise PermissionDenied("You can only edit your own timesheets.")
            if self.instance.status not in ("draft", "rejected"):
                raise serializers.ValidationError(f"A {self.instance.status} timesheet cannot be edited.")
            employee = self.instance.employee
        else:
            employee = Employee.objects.filter(user=user).first()
            if not employee:
                raise serializers.ValidationError("Your account has no employee profile, so you cannot log time.")

        project, task, work_date, hours = get("project"), get("task"), get("work_date"), get("hours")
        if project.status != "active":
            raise serializers.ValidationError({"project": [f"Project is '{project.status}', not active."]})
        if not project.members.filter(employee=employee).exists():
            raise serializers.ValidationError({"project": ["You are not a member of this project."]})
        if task.project_id != project.id:
            raise serializers.ValidationError({"task": ["Task does not belong to this project."]})
        if work_date > datetime.date.today():
            raise serializers.ValidationError({"work_date": ["Work date cannot be in the future."]})
        if work_date < project.start_date:
            raise serializers.ValidationError({"work_date": ["Work date is before the project start date."]})

        others = Timesheet.objects.filter(employee=employee, work_date=work_date).exclude(status="rejected")
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        total = (others.aggregate(t=Sum("hours"))["t"] or Decimal("0")) + hours
        if total > 24:
            raise serializers.ValidationError({"hours": [f"Total for {work_date} would be {total}h (max 24)."]})

        if not self.instance:
            attrs["employee"] = employee        # always the logged-in user, never client-supplied
        return attrs

class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField()

class ApprovalSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = TimesheetApproval
        fields = ["decision", "actor_name", "reason", "created_at"]