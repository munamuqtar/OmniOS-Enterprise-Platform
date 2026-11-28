from django.apps import apps
from django.db.models.signals import pre_save, post_save, post_delete
from .services import snapshot, record

AUDITED = {
    "organizations.Organization": "organizations", "branches.Branch": "branches",
    "accounts.User": "accounts", "accounts.UserRole": "accounts", "accounts.UserBranch": "accounts",
    "hr.Department": "hr", "hr.Employee": "hr",
    "recruitment.JobVacancy": "recruitment", "recruitment.Candidate": "recruitment",
    "recruitment.RecruitmentApplication": "recruitment",
    "crm.Lead": "crm", "crm.Client": "crm", "crm.Opportunity": "crm",
    "sales.Quote": "sales",
    "projects.Project": "projects", "projects.ProjectMember": "projects", "projects.Task": "projects",
    "timesheets.Timesheet": "timesheets",
    "finance.Invoice": "finance", "finance.Payment": "finance",
}
LOG_DELETE = {"accounts.UserRole", "accounts.UserBranch", "projects.ProjectMember"}

def _pre_save(sender, instance, raw=False, **kwargs):
    instance._audit_before = None
    if raw or instance._state.adding:
        return
    old = sender._base_manager.filter(pk=instance.pk).first()
    instance._audit_before = snapshot(old) if old else None

def _post_save(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    module = AUDITED[sender._meta.label]
    after = snapshot(instance)
    if created:
        record("create", module, instance, None, after)
        return
    before = getattr(instance, "_audit_before", None) or {}
    changed = [k for k, v in after.items() if before.get(k) != v]
    if not changed:
        return
    action = "status_change" if {"status", "stage"} & set(changed) else "update"
    record(action, module, instance, {k: before.get(k) for k in changed}, {k: after[k] for k in changed})

def _post_delete(sender, instance, **kwargs):
    record("delete", AUDITED[sender._meta.label], instance, snapshot(instance), None)

def connect():
    for label in AUDITED:
        model = apps.get_model(label)
        pre_save.connect(_pre_save, sender=model, dispatch_uid=f"audit-pre-{label}")
        post_save.connect(_post_save, sender=model, dispatch_uid=f"audit-post-{label}")
        if label in LOG_DELETE:
            post_delete.connect(_post_delete, sender=model, dispatch_uid=f"audit-del-{label}")