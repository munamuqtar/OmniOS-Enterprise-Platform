from apps.accounts.models import User
from .services import notify

def _super_admins():
    return User.objects.filter(is_active=True, roles__code="super_admin").distinct()

def _finance_users(branch_id):
    return User.objects.filter(is_active=True, roles__code="finance", branches__id=branch_id).distinct()

def lead_assigned(lead, actor):
    notify([lead.owner], "lead_assigned", "New lead assigned to you",
           f"Lead '{lead.name}' was assigned to you.", actor, lead, lead.branch_id)

def quote_submitted(quote, actor):
    notify([quote.branch.manager, *_super_admins()], "quote_submitted",
           f"Quotation {quote.quote_number} needs approval",
           f"Total {quote.total} {quote.currency}.", actor, quote, quote.branch_id)

def quote_decided(quote, actor, approved, reason=""):
    kind = "quote_approved" if approved else "quote_rejected"
    msg = "Your quotation was approved." if approved else f"Your quotation was rejected: {reason}"
    notify([quote.created_by], kind, f"Quotation {quote.quote_number} {'approved' if approved else 'rejected'}",
           msg, actor, quote, quote.branch_id)

def project_manager_assigned(project, actor):
    notify([project.manager], "project_assigned", f"You manage project {project.project_code}",
           f"{project.name} was assigned to you as project manager.", actor, project, project.branch_id)

def project_member_added(project, employee, actor):
    notify([employee.user], "project_assigned", f"You were added to project {project.project_code}",
           f"You are now a member of {project.name}.", actor, project, project.branch_id)

def task_assigned(task, actor):
    if task.assigned_employee:
        notify([task.assigned_employee.user], "task_assigned", f"New task: {task.title}",
               f"Due {task.due_date} on project {task.project.project_code}.", actor, task, task.project.branch_id)

def timesheet_submitted(ts, actor):
    notify([ts.project.manager], "timesheet_submitted", "Timesheet waiting for review",
           f"{ts.employee.first_name} {ts.employee.last_name} submitted {ts.hours}h for {ts.work_date}.",
           actor, ts, ts.project.branch_id)

def timesheet_reviewed(ts, actor, approved, reason=""):
    kind = "timesheet_approved" if approved else "timesheet_rejected"
    msg = f"Your timesheet for {ts.work_date} was approved." if approved else \
          f"Your timesheet for {ts.work_date} was rejected: {reason}"
    notify([ts.employee.user], kind, f"Timesheet {'approved' if approved else 'rejected'}",
           msg, actor, ts, ts.project.branch_id)

def invoice_issued(inv, actor):
    notify([inv.project.manager, inv.created_by], "invoice_issued", f"Invoice {inv.invoice_number} issued",
           f"Total {inv.total} {inv.currency}, due {inv.due_date}.", actor, inv, inv.branch_id)

def payment_recorded(payment, actor):
    inv = payment.invoice
    notify([inv.created_by, *_finance_users(inv.branch_id)], "payment_recorded",
           f"Payment {payment.payment_number} recorded",
           f"{payment.amount} {inv.currency} on invoice {inv.invoice_number}.", actor, payment, inv.branch_id)