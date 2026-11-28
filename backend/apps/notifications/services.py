from .models import Notification

def notify(recipients, kind, title, message="", actor=None, obj=None, branch_id=None):
    """Create one notification per distinct, active recipient. The person who did the action is skipped."""
    seen = set()
    for user in recipients:
        if user is None or not user.is_active or user.pk in seen:
            continue
        if actor is not None and user.pk == actor.pk:
            continue
        seen.add(user.pk)
        Notification.objects.create(
            recipient=user, kind=kind, title=title, message=message, branch_id=branch_id,
            related_type=obj._meta.model_name if obj is not None else "",
            related_id=obj.pk if obj is not None else None)