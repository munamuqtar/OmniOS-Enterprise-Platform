from django.db import models
from apps.organizations.models import TimeStampedModel
from apps.branches.models import Branch

class Project(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    project_code = models.CharField(max_length=30, unique=True, editable=False)
    name = models.CharField(max_length=200)
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="projects")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="projects")
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    manager = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="managed_projects")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["branch", "status"])]

    def __str__(self):
        return f"{self.project_code} - {self.name}"

class ProjectMember(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    employee = models.ForeignKey("hr.Employee", on_delete=models.PROTECT, related_name="project_memberships")
    role = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("project", "employee")

class Task(TimeStampedModel):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        REVIEW = "review", "Review"
        COMPLETED = "completed", "Completed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_employee = models.ForeignKey("hr.Employee", null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name="tasks")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["project", "status"]), models.Index(fields=["due_date"])]

    def __str__(self):
        return self.title