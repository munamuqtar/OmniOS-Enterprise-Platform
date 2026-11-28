from django.db import models
from apps.organizations.models import TimeStampedModel

class Timesheet(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey("hr.Employee", on_delete=models.PROTECT, related_name="timesheets")
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="timesheets")
    task = models.ForeignKey("projects.Task", on_delete=models.PROTECT, related_name="timesheets")
    work_date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    invoice_item = models.ForeignKey("finance.InvoiceItem", null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="timesheets")

    class Meta:
        indexes = [models.Index(fields=["employee", "work_date"]),
                   models.Index(fields=["project", "status"])]

    def __str__(self):
        return f"{self.employee_id} {self.work_date} {self.hours}h"

class TimesheetApproval(TimeStampedModel):
    class Decision(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="approvals")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    actor = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)