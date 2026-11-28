from django.core.exceptions import ObjectDoesNotExist
from . import context
from .models import AuditLog

SKIP = {"id", "password", "last_login", "created_at", "updated_at"}   # passwords are never logged

def _val(v):
    return v if v is None or isinstance(v, (bool, int, float, str)) else str(v)

def snapshot(obj):
    return {f.name: _val(f.value_from_object(obj))
            for f in obj._meta.concrete_fields if f.name not in SKIP}

def branch_id_of(obj):
    if obj._meta.model_name == "branch":
        return obj.pk
    for path in (("branch_id",), ("project", "branch_id"), ("invoice", "branch_id")):
        cur = obj
        try:
            for part in path:
                cur = getattr(cur, part)
        except (AttributeError, ObjectDoesNotExist):
            continue
        if cur:
            return cur
    return None

def record(action, module, obj, old=None, new=None, user=None):
    ctx = context.current()
    AuditLog.objects.create(
        user=user or ctx["user"], action=action, module=module, record_type=obj._meta.model_name,
        record_id=str(obj.pk), record_repr=str(obj)[:255], branch_id=branch_id_of(obj),
        old_values=old, new_values=new, ip_address=ctx["ip"])