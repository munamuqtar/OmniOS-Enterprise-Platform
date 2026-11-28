import datetime
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from apps.core.responses import ok
from apps.notifications import events
from .models import Project, Task
from .serializers import (ProjectSerializer, MemberSerializer, AddMemberSerializer, RemoveMemberSerializer,
                          StatusSerializer, TaskSerializer)
from . import services

BROAD_READ = {"project_manager", "sales", "finance"}

def is_manager(u):
    return u.is_super_admin or "project_manager" in u.role_codes

class ProjectPermission(BasePermission):
    """Super Admin and Project Manager: full. Sales, Finance, Employee: read only. HR: none."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if is_manager(u):
            return True
        return request.method in SAFE_METHODS and bool(u.role_codes & {"sales", "finance", "employee"})

class ProjectViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related("client", "branch", "manager").annotate(
        task_count=Count("tasks", distinct=True),
        completed_count=Count("tasks", filter=Q(tasks__status="completed"), distinct=True),
    ).order_by("-created_at")
    serializer_class = ProjectSerializer
    permission_classes = [ProjectPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "project_code", "client__name"]
    filterset_fields = ["status", "branch", "client", "manager"]

    def get_queryset(self):
        qs = super().get_queryset()                     # branch isolation first
        u = self.request.user
        if u.is_super_admin or (u.role_codes & BROAD_READ):
            return qs
        return qs.filter(members__employee__user=u)     # Employee: assigned projects only

    def perform_create(self, serializer):
        project = serializer.save(project_code=services.next_project_code(), created_by=self.request.user)
        events.project_manager_assigned(project, self.request.user)

    def perform_update(self, serializer):
        old_manager = serializer.instance.manager_id
        project = serializer.save()
        if project.manager_id != old_manager:
            events.project_manager_assigned(project, self.request.user)

 

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        s = StatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        project = services.change_project_status(self.get_object(), s.validated_data["status"], request.user)
        return ok(ProjectSerializer(project, context={"request": request}).data, "Project status updated")

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        project = self.get_object()
        if request.method == "POST":
            s = AddMemberSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            m = services.add_member(project, s.validated_data["employee"], s.validated_data["role"])
            events.project_member_added(project, s.validated_data["employee"], request.user)
            return ok(MemberSerializer(m).data, "Member added", status=201)
        return ok(MemberSerializer(project.members.select_related("employee"), many=True).data)

    @action(detail=True, methods=["post"], url_path="members/remove")
    def remove_member(self, request, pk=None):
        s = RemoveMemberSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.remove_member(self.get_object(), s.validated_data["employee"])
        return ok(message="Member removed")

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        project = self.get_object()
        tasks = project.tasks.all()
        today = datetime.date.today()
        by_status = dict(tasks.values_list("status").annotate(n=Count("id")))
        total = tasks.count()
        done = by_status.get("completed", 0)
        return ok({
            "project": project.project_code, "status": project.status,
            "members": project.members.count(), "tasks_total": total,
            "tasks_by_status": {s: by_status.get(s, 0) for s, _ in Task.Status.choices},
            "overdue_tasks": tasks.exclude(status="completed").filter(due_date__lt=today).count(),
            "progress": round(100 * done / total) if total else 0,
        })

class TaskPermission(BasePermission):
    """Super Admin and PM: full. Sales: read. Employee: read own tasks and update status on them."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if is_manager(u):
            return True
        if request.method in SAFE_METHODS:
            return bool(u.role_codes & {"sales", "employee"})
        return view.action == "set_status" and "employee" in u.role_codes

class TaskViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    branch_field = "project__branch_id"
    queryset = Task.objects.select_related("project", "assigned_employee").order_by("due_date")
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["title", "description", "project__name"]
    filterset_fields = ["status", "priority", "project", "assigned_employee"]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if is_manager(u) or "sales" in u.role_codes:
            return qs
        return qs.filter(assigned_employee__user=u)     # Employee: own tasks only

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        events.task_assigned(task, self.request.user)

    def perform_update(self, serializer):
        old = serializer.instance.assigned_employee_id
        task = serializer.save()
        if task.assigned_employee_id and task.assigned_employee_id != old:
            events.task_assigned(task, self.request.user)

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        new = request.data.get("status")
        if new not in dict(Task.Status.choices):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": ["Invalid status."]})
        task = services.change_task_status(self.get_object(), new, request.user)
        return ok(TaskSerializer(task, context={"request": request}).data, "Task status updated")

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        qs = self.filter_queryset(self.get_queryset()).exclude(status="completed") \
                 .filter(due_date__lt=datetime.date.today())
        return ok(TaskSerializer(qs, many=True, context={"request": request}).data)