import datetime
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Project, ProjectMember, Task

PROJECT_TRANSITIONS = {
    "draft": {"planned", "cancelled"},
    "planned": {"active", "on_hold", "cancelled"},
    "active": {"on_hold", "completed", "cancelled"},
    "on_hold": {"active", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
TASK_TRANSITIONS = {
    "todo": {"in_progress"},
    "in_progress": {"todo", "review"},
    "review": {"in_progress", "completed"},
    "completed": {"in_progress"},
}
CLOSED = ("completed", "cancelled")

def next_project_code():
    year = datetime.date.today().year
    last = Project.objects.filter(project_code__startswith=f"PRJ-{year}-").order_by("-project_code").first()
    n = int(last.project_code.split("-")[-1]) + 1 if last else 1
    return f"PRJ-{year}-{n:05d}"

def check_manager(manager, branch):
    if not (manager.is_super_admin or "project_manager" in manager.role_codes):
        raise ValidationError({"manager": ["Manager must have the Project Manager role."]})
    if not manager.is_super_admin and branch.id not in manager.branch_ids():
        raise ValidationError({"manager": ["Manager has no access to this branch."]})

@transaction.atomic
def change_project_status(project, new_status, user):
    project = Project.objects.select_for_update().get(pk=project.pk)
    if new_status not in PROJECT_TRANSITIONS[project.status]:
        raise ValidationError({"status": [f"Cannot change from '{project.status}' to '{new_status}'."]})
    if new_status == "completed":
        open_tasks = project.tasks.exclude(status="completed").count()
        if open_tasks:
            raise ValidationError({"status": [f"{open_tasks} task(s) are not completed yet."]})
    project.status = new_status
    project.save(update_fields=["status", "updated_at"])
    return project

@transaction.atomic
def add_member(project, employee, role=""):
    if project.status in CLOSED:
        raise ValidationError({"project": [f"Cannot change members of a {project.status} project."]})
    if employee.branch_id != project.branch_id:
        raise ValidationError({"employee": ["Employee belongs to a different branch."]})
    if employee.status != "active":
        raise ValidationError({"employee": ["Only active employees can be assigned."]})
    if ProjectMember.objects.filter(project=project, employee=employee).exists():
        raise ValidationError({"employee": ["Employee is already a project member."]})
    return ProjectMember.objects.create(project=project, employee=employee, role=role)

@transaction.atomic
def remove_member(project, employee):
    member = ProjectMember.objects.filter(project=project, employee=employee).first()
    if not member:
        raise ValidationError({"employee": ["Employee is not a member of this project."]})
    if Task.objects.filter(project=project, assigned_employee=employee).exclude(status="completed").exists():
        raise ValidationError({"employee": ["Reassign this employee's open tasks first."]})
    member.delete()

@transaction.atomic
def change_task_status(task, new_status, user):
    task = Task.objects.select_for_update().get(pk=task.pk)
    project = task.project
    if project.status not in ("planned", "active"):
        raise ValidationError({"status": [f"Tasks cannot be worked on while the project is '{project.status}'."]})
    if new_status not in TASK_TRANSITIONS[task.status]:
        raise ValidationError({"status": [f"Cannot change from '{task.status}' to '{new_status}'."]})
    is_manager = user.is_super_admin or "project_manager" in user.role_codes
    if not is_manager:
        own = task.assigned_employee_id and task.assigned_employee.user_id == user.id
        if not own:
            raise PermissionDenied("You can only update your own tasks.")
        if "completed" in (new_status, task.status):
            raise PermissionDenied("Only a project manager can complete or reopen a task.")
    task.status = new_status
    task.save(update_fields=["status", "updated_at"])
    return task