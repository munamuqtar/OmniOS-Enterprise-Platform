from django.db import models
from apps.organizations.models import TimeStampedModel, Organization

class Branch(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="branches")
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=30, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey("accounts.User", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="managed_branches")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name_plural = "branches"
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"{self.branch_code} - {self.name}"