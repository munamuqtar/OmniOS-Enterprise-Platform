from django.db import models
from apps.organizations.models import TimeStampedModel, Organization
from apps.branches.models import Branch

class Department(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self):
        return self.name

class Employee(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On Leave"
        SUSPENDED = "suspended", "Suspended"
        TERMINATED = "terminated", "Terminated"

    user = models.OneToOneField("accounts.User", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="employee_profile")
    employee_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    department = models.ForeignKey(Department, null=True, blank=True,
                                   on_delete=models.PROTECT, related_name="employees")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="employees")
    position = models.CharField(max_length=150, blank=True)
    hire_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        indexes = [models.Index(fields=["branch", "status"])]

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name}"