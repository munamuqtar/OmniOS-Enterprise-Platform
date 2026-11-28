from rest_framework import serializers
from apps.core.serializers import BranchValidationMixin
from apps.hr.models import Employee
from .models import Project, ProjectMember, Task
from . import services

class ProjectSerializer(BranchValidationMixin, serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    manager_name = serializers.CharField(source="manager.username", read_only=True)
    task_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "project_code", "name", "client", "client_name", "branch", "description",
                  "start_date", "end_date", "budget", "manager", "manager_name", "status",
                  "task_count", "completed_count", "progress", "created_at", "updated_at"]
        read_only_fields = ["id", "project_code", "status", "created_at", "updated_at"]

    def _counts(self, obj):
        if hasattr(obj, "task_count"):                      # annotated in the list queryset
            return obj.task_count, obj.completed_count
        qs = obj.tasks.all()
        return qs.count(), qs.filter(status="completed").count()

    def get_task_count(self, obj):
        return self._counts(obj)[0]

    def get_completed_count(self, obj):
        return self._counts(obj)[1]

    def get_progress(self, obj):
        total, done = self._counts(obj)
        return round(100 * done / total) if total else 0

    def validate_budget(self, v):
        if v is not None and v < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return v

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))
        if self.instance and self.instance.status in services.CLOSED:
            raise serializers.ValidationError(f"A {self.instance.status} project cannot be edited.")
        if get("end_date") < get("start_date"):
            raise serializers.ValidationError({"end_date": ["End date cannot be before the start date."]})
        if get("client").branch_id != get("branch").id:
            raise serializers.ValidationError({"client": ["Client belongs to a different branch."]})
        services.check_manager(get("manager"), get("branch"))
        return attrs

class MemberSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_number = serializers.CharField(source="employee.employee_number", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["id", "employee", "employee_name", "employee_number", "role", "created_at"]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

class AddMemberSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    role = serializers.CharField(required=False, allow_blank=True, default="")

class RemoveMemberSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Project.Status.choices)

class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    assignee_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "project", "project_name", "title", "description", "assigned_employee",
                  "assignee_name", "start_date", "due_date", "priority", "status", "is_overdue",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_assignee_name(self, obj):
        e = obj.assigned_employee
        return f"{e.first_name} {e.last_name}" if e else None

    def get_is_overdue(self, obj):
        import datetime
        return obj.status != "completed" and obj.due_date < datetime.date.today()

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))
        user = self.context["request"].user
        project = get("project")
        if self.instance and project.id != self.instance.project_id:
            raise serializers.ValidationError({"project": ["A task cannot be moved to another project."]})
        if not user.is_super_admin and project.branch_id not in user.branch_ids():
            raise serializers.ValidationError({"project": ["You do not have access to this project's branch."]})
        if project.status in services.CLOSED:
            raise serializers.ValidationError({"project": [f"Project is {project.status}."]})
        start, due = get("start_date"), get("due_date")
        if start and due < start:
            raise serializers.ValidationError({"due_date": ["Due date cannot be before the start date."]})
        emp = get("assigned_employee")
        if emp and not project.members.filter(employee=emp).exists():
            raise serializers.ValidationError({"assigned_employee": ["Employee is not a member of this project."]})
        return attrs