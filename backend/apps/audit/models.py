from django.db import models
from apps.organizations.models import TimeStampedModel

class AuditLog(TimeStampedModel):
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=20)            # create, update, status_change, delete, login
    module = models.CharField(max_length=30)            # crm, sales, finance, ...
    record_type = models.CharField(max_length=60)
    record_id = models.CharField(max_length=64)
    record_repr = models.CharField(max_length=255, blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["module", "created_at"]),
                   models.Index(fields=["branch", "created_at"]),
                   models.Index(fields=["record_type", "record_id"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit logs are immutable.")
        super().save(*args, **kwargs)