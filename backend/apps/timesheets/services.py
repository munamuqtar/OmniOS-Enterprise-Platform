from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Timesheet, TimesheetApproval
from apps.notifications import events   

def _log(ts, decision, user, reason=""):
    TimesheetApproval.objects.create(timesheet=ts, decision=decision, actor=user, reason=reason)

@transaction.atomic
def submit(ts, user):
    ts = Timesheet.objects.select_for_update().get(pk=ts.pk)
    if ts.employee.user_id != user.id:
        raise PermissionDenied("You can only submit your own timesheets.")
    if ts.status not in ("draft", "rejected"):
        raise ValidationError({"status": [f"A {ts.status} timesheet cannot be submitted."]})
    if ts.project.status != "active":
        raise ValidationError({"project": [f"Project is '{ts.project.status}', not active."]})
    ts.status = "submitted"
    ts.rejection_reason = ""
    ts.save(update_fields=["status", "rejection_reason", "updated_at"])
    _log(ts, "submitted", user)
    events.timesheet_submitted(ts, user)
    return ts

def _check_reviewer(ts, user):
    if ts.employee.user_id == user.id:
        raise PermissionDenied("You cannot review your own timesheet.")
    if user.is_super_admin:
        return
    if ts.project.manager_id != user.id:
        raise PermissionDenied("Only the project's manager can review this timesheet.")

@transaction.atomic
def approve(ts, user):
    ts = Timesheet.objects.select_for_update().get(pk=ts.pk)
    if ts.status != "submitted":
        raise ValidationError({"status": ["Only submitted timesheets can be approved."]})
    _check_reviewer(ts, user)
    ts.status, ts.reviewed_by, ts.reviewed_at = "approved", user, timezone.now()
    ts.save()
    _log(ts, "approved", user)
    events.timesheet_reviewed(ts, user, True)
    return ts

@transaction.atomic
def reject(ts, user, reason):
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required to reject a timesheet."]})
    ts = Timesheet.objects.select_for_update().get(pk=ts.pk)
    if ts.status != "submitted":
        raise ValidationError({"status": ["Only submitted timesheets can be rejected."]})
    _check_reviewer(ts, user)
    ts.status, ts.reviewed_by, ts.reviewed_at = "rejected", user, timezone.now()
    ts.rejection_reason = reason
    ts.save()
    _log(ts, "rejected", user, reason)
    events.timesheet_reviewed(ts, user, False, reason)
    return ts