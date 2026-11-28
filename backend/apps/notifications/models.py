from django.db import models
from apps.organizations.models import TimeStampedModel

class Notification(TimeStampedModel):
    class Kind(models.TextChoices):
        LEAD_ASSIGNED = "lead_assigned", "New lead assignment"
        QUOTE_SUBMITTED = "quote_submitted", "Quotation submitted"
        QUOTE_APPROVED = "quote_approved", "Quotation approved"
        QUOTE_REJECTED = "quote_rejected", "Quotation rejected"
        PROJECT_ASSIGNED = "project_assigned", "Project assignment"
        TASK_ASSIGNED = "task_assigned", "Task assignment"
        TIMESHEET_SUBMITTED = "timesheet_submitted", "Timesheet submitted"
        TIMESHEET_APPROVED = "timesheet_approved", "Timesheet approved"
        TIMESHEET_REJECTED = "timesheet_rejected", "Timesheet rejected"
        INVOICE_ISSUED = "invoice_issued", "Invoice issued"
        PAYMENT_RECORDED = "payment_recorded", "Payment recorded"

    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")
    related_type = models.CharField(max_length=60, blank=True)
    related_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]