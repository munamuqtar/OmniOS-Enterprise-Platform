import uuid
from decimal import Decimal
from django.db.models import Count, Q, Sum
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.core.permissions import HasRole
from apps.core.responses import ok
from apps.crm.models import Client, Lead, Opportunity
from apps.finance import services as finance_services
from apps.finance.models import Invoice, Payment
from apps.hr.models import Employee
from apps.projects.models import Project, Task
from apps.recruitment.models import RecruitmentApplication
from apps.sales.models import Quote
from apps.timesheets.models import Timesheet

ZERO = Decimal("0")
OPEN_INVOICE = ("issued", "partially_paid", "overdue")
COUNTED = ("confirmed", "reconciled")

def branch_ids(request):
    """None means 'all branches' (Super Admin only). Otherwise the branches the user may see."""
    u = request.user
    wanted = request.query_params.get("branch")
    if wanted:
        try:
            wanted = uuid.UUID(wanted)
        except ValueError:
            raise ValidationError({"branch": ["Invalid branch id."]})
    if u.is_super_admin:
        return [wanted] if wanted else None
    allowed = u.branch_ids()
    if wanted:
        if wanted not in allowed:
            raise PermissionDenied("You do not have access to this branch.")
        return [wanted]
    return allowed

def scope(qs, field, ids):
    return qs if ids is None else qs.filter(**{f"{field}__in": ids})

def counts_by(qs, field):
    return {r[field]: r["n"] for r in qs.values(field).annotate(n=Count("id")).order_by()}

def fill(counts, choices):
    return {key: counts.get(key, 0) for key, _ in choices}

def sum_by_currency(qs, amount_field, currency_field="currency"):
    rows = qs.values(currency_field).annotate(t=Sum(amount_field)).order_by(currency_field)
    return [{"currency": r[currency_field], "amount": r["t"] or ZERO} for r in rows]

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return ok(self.build(request, branch_ids(request)))

class ExecutiveDashboard(DashboardView):
    permission_classes = [IsAuthenticated, HasRole.of()]       # Super Admin only

    def build(self, request, ids):
        finance_services.mark_overdue()
        branches = Branch.objects.all() if ids is None else Branch.objects.filter(id__in=ids)
        projects = scope(Project.objects.all(), "branch_id", ids)
        quotes = scope(Quote.objects.all(), "branch_id", ids)
        invoices = scope(Invoice.objects.all(), "branch_id", ids)
        payments = scope(Payment.objects.all(), "invoice__branch_id", ids)
        timesheets = scope(Timesheet.objects.all(), "project__branch_id", ids)
        logs = scope(AuditLog.objects.select_related("user"), "branch_id", ids)[:10]
        return {
            "kpis": {
                "total_employees": scope(Employee.objects.all(), "branch_id", ids).count(),
                "total_branches": branches.count(),
                "total_clients": scope(Client.objects.all(), "branch_id", ids).count(),
                "total_leads": scope(Lead.objects.all(), "branch_id", ids).count(),
                "total_opportunities": scope(Opportunity.objects.all(), "branch_id", ids).count(),
                "active_projects": projects.filter(status="active").count(),
                "pending_quotations": quotes.filter(status="pending_approval").count(),
                "total_invoices": invoices.exclude(status="cancelled").count(),
                "outstanding_balance": sum_by_currency(invoices.filter(status__in=OPEN_INVOICE), "balance"),
                "payments_received": sum_by_currency(payments.filter(status__in=COUNTED), "amount", "invoice__currency"),
            },
            "projects_by_status": fill(counts_by(projects, "status"), Project.Status.choices),
            "invoices_by_status": fill(counts_by(invoices, "status"), Invoice.Status.choices),
            "payments_by_status": fill(counts_by(payments, "status"), Payment.Status.choices),
            "pending_approvals": {"quotations": quotes.filter(status="pending_approval").count(),
                                  "timesheets": timesheets.filter(status="submitted").count()},
            "recent_activity": [{"user": l.user.username if l.user else "system", "action": l.action,
                                 "module": l.module, "record": l.record_repr, "at": l.created_at} for l in logs],
        }

class HRDashboard(DashboardView):
    permission_classes = [IsAuthenticated, HasRole.of("hr")]

    def build(self, request, ids):
        employees = scope(Employee.objects.all(), "branch_id", ids)
        apps_qs = scope(RecruitmentApplication.objects.all(), "branch_id", ids)
        by_branch = employees.values("branch__name").annotate(n=Count("id")).order_by("branch__name")
        return {
            "kpis": {
                "total_employees": employees.count(),
                "active_employees": employees.filter(status="active").count(),
                "recruitment_applications": apps_qs.count(),
                "hired_candidates": apps_qs.filter(stage="hired").count(),
            },
            "interview_pipeline": fill(counts_by(apps_qs, "stage"), RecruitmentApplication.Stage.choices),
            "employees_by_branch": [{"branch": r["branch__name"], "count": r["n"]} for r in by_branch],
        }

class SalesDashboard(DashboardView):
    permission_classes = [IsAuthenticated, HasRole.of("sales")]

    def build(self, request, ids):
        leads = scope(Lead.objects.all(), "branch_id", ids)
        opps = scope(Opportunity.objects.all(), "branch_id", ids)
        quotes = scope(Quote.objects.all(), "branch_id", ids)
        open_opps = opps.exclude(stage__in=("won", "lost"))
        by_stage = {r["stage"]: r["t"] or ZERO for r in opps.values("stage").annotate(t=Sum("value")).order_by()}
        return {
            "kpis": {
                "leads": leads.count(),
                "qualified_leads": leads.filter(status="qualified").count(),
                "opportunities": opps.count(),
                "quotations": quotes.count(),
                "pending_approvals": quotes.filter(status="pending_approval").count(),
                "won_opportunities": opps.filter(stage="won").count(),
                "lost_opportunities": opps.filter(stage="lost").count(),
                "pipeline_value": open_opps.aggregate(t=Sum("value"))["t"] or ZERO,
            },
            "leads_by_status": fill(counts_by(leads, "status"), Lead.Status.choices),
            "opportunities_by_stage": fill(counts_by(opps, "stage"), Opportunity.Stage.choices),
            "pipeline_value_by_stage": {s: by_stage.get(s, ZERO) for s, _ in Opportunity.Stage.choices},
        }

class ProjectsDashboard(DashboardView):
    permission_classes = [IsAuthenticated, HasRole.of("project_manager")]

    def build(self, request, ids):
        import datetime
        projects = scope(Project.objects.all(), "branch_id", ids)
        if not request.user.is_super_admin:
            projects = projects.filter(manager=request.user)       # PM: only projects they manage
        tasks = Task.objects.filter(project__in=projects)
        sheets = Timesheet.objects.filter(project__in=projects)
        active = projects.filter(status="active").annotate(
            n=Count("tasks", distinct=True),
            done=Count("tasks", filter=Q(tasks__status="completed"), distinct=True)).order_by("-created_at")[:10]
        return {
            "kpis": {
                "active_projects": projects.filter(status="active").count(),
                "completed_projects": projects.filter(status="completed").count(),
                "total_tasks": tasks.count(),
                "overdue_tasks": tasks.exclude(status="completed").filter(due_date__lt=datetime.date.today()).count(),
                "pending_timesheets": sheets.filter(status="submitted").count(),
                "approved_timesheets": sheets.filter(status="approved").count(),
                "approved_hours": sheets.filter(status="approved").aggregate(t=Sum("hours"))["t"] or ZERO,
            },
            "projects_by_status": fill(counts_by(projects, "status"), Project.Status.choices),
            "tasks_by_status": fill(counts_by(tasks, "status"), Task.Status.choices),
            "project_progress": [{"id": p.id, "project_code": p.project_code, "name": p.name,
                                  "progress": round(100 * p.done / p.n) if p.n else 0} for p in active],
        }

class FinanceDashboard(DashboardView):
    permission_classes = [IsAuthenticated, HasRole.of("finance")]

    def build(self, request, ids):
        finance_services.mark_overdue()
        invoices = scope(Invoice.objects.all(), "branch_id", ids)
        payments = scope(Payment.objects.all(), "invoice__branch_id", ids)
        by_pay = payments.values("status", "invoice__currency").annotate(count=Count("id"), total=Sum("amount")).order_by()
        return {
            "kpis": {
                "total_invoices": invoices.exclude(status="cancelled").count(),
                "paid_invoices": invoices.filter(status="paid").count(),
                "partially_paid_invoices": invoices.filter(status="partially_paid").count(),
                "overdue_invoices": invoices.filter(status="overdue").count(),
                "outstanding_balance": sum_by_currency(invoices.filter(status__in=OPEN_INVOICE), "balance"),
                "overdue_balance": sum_by_currency(invoices.filter(status="overdue"), "balance"),
                "payments_received": sum_by_currency(payments.filter(status__in=COUNTED), "amount", "invoice__currency"),
            },
            "invoices_by_status": fill(counts_by(invoices, "status"), Invoice.Status.choices),
            "payments": [{"status": r["status"], "currency": r["invoice__currency"],
                          "count": r["count"], "total": r["total"]} for r in by_pay],
            "reconciliation_status": fill(counts_by(payments, "status"), Payment.Status.choices),
        }