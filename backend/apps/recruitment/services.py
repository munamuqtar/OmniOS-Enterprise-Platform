from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import RecruitmentApplication, ApplicationStageHistory

ALLOWED = {
    "applied":    {"screening", "rejected"},
    "screening":  {"interview", "rejected"},
    "interview":  {"evaluation", "rejected"},
    "evaluation": {"offered", "rejected"},
    "offered":    {"hired", "rejected"},
    "hired":      set(),
    "rejected":   set(),
}

@transaction.atomic
def change_stage(application, new_stage, user, reason="", interview_at=None, interview_location=""):
    app = RecruitmentApplication.objects.select_for_update().get(pk=application.pk)
    old = app.stage
    if new_stage not in ALLOWED[old]:
        raise ValidationError({"stage": [f"Cannot move from '{old}' to '{new_stage}'."]})
    if new_stage == "rejected" and not reason.strip():
        raise ValidationError({"reason": ["Rejection requires a reason."]})
    if new_stage == "interview":
        if not interview_at:
            raise ValidationError({"interview_at": ["Interview date/time is required."]})
        app.interview_at = interview_at
        app.interview_location = interview_location
    if new_stage == "rejected":
        app.rejection_reason = reason
    app.stage = new_stage
    app.save()
    ApplicationStageHistory.objects.create(
        application=app, from_stage=old, to_stage=new_stage, changed_by=user, reason=reason)
    return app