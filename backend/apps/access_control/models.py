from django.db import models
from apps.organizations.models import TimeStampedModel

class Permission(TimeStampedModel):
    codename = models.CharField(max_length=100, unique=True)   # e.g. "leads.create"
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.codename

class Role(TimeStampedModel):
    class Code(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        HR = "hr", "HR"
        SALES = "sales", "Sales"
        FINANCE = "finance", "Finance"
        PROJECT_MANAGER = "project_manager", "Project Manager"
        EMPLOYEE = "employee", "Employee"

    code = models.CharField(max_length=30, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    def __str__(self):
        return self.name