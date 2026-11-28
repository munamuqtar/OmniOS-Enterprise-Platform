import datetime
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client, Lead, Opportunity
from apps.finance.models import Invoice, Payment
from apps.hr.models import Employee
from apps.organizations.models import Organization
from apps.projects.models import Project, Task
from apps.recruitment.models import Candidate, JobVacancy, RecruitmentApplication
from apps.sales.models import Quote
from apps.timesheets.models import Timesheet

TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)

def data(res):
    assert res.status_code == 200, (res.status_code, res.data)
    return res.data["data"]

class DashboardTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.admin = api_client(make_user("root", "super_admin", []))
        self.hr_a = api_client(make_user("hr_a", "hr", [self.a]))
        self.hr_b = api_client(make_user("hr_b", "hr", [self.b]))
        self.sales = api_client(make_user("sales1", "sales", [self.a]))
        self.pm_user = make_user("pm", "project_manager", [self.a])
        self.pm = api_client(self.pm_user)
        pm2_user = make_user("pm2", "project_manager", [self.a])
        self.pm2 = api_client(pm2_user)
        self.fin = api_client(make_user("fin", "finance", [self.a]))
        self.emp_user = api_client(make_user("emp9", "employee", [self.a]))

        e1 = Employee.objects.create(employee_number="E1", first_name="A", last_name="One", email="1@x.com", branch=self.a, hire_date=TODAY)
        Employee.objects.create(employee_number="E2", first_name="B", last_name="Two", email="2@x.com", branch=self.a, hire_date=TODAY, status="terminated")
        Employee.objects.create(employee_number="E3", first_name="C", last_name="Three", email="3@x.com", branch=self.b, hire_date=TODAY)
        client_a = Client.objects.create(name="CliA", email="a@x.com", branch=self.a)
        Client.objects.create(name="CliB", email="b@x.com", branch=self.b)
        Lead.objects.create(name="L1", email="l1@x.com", branch=self.a)
        Lead.objects.create(name="L2", email="l2@x.com", branch=self.a, status="qualified")
        Lead.objects.create(name="L3", email="l3@x.com", branch=self.b)
        for name, stage, value in (("Open", "prospecting", "1000"), ("Won", "won", "500"), ("Lost", "lost", "200")):
            Opportunity.objects.create(name=name, client=client_a, branch=self.a, value=Decimal(value),
                                       expected_close_date=TODAY, stage=stage)
        Quote.objects.create(quote_number="QT-1", client=client_a, branch=self.a, valid_until=TODAY, status="pending_approval")
        vacancy = JobVacancy.objects.create(title="Dev", branch=self.a, status="open")
        cand = Candidate.objects.create(first_name="Sam", last_name="S", email="s@x.com", branch=self.a)
        RecruitmentApplication.objects.create(candidate=cand, vacancy=vacancy, branch=self.a, stage="interview")

        self.p1 = Project.objects.create(project_code="P1", name="One", client=client_a, branch=self.a,
                                         manager=self.pm_user, start_date=YESTERDAY, end_date=TODAY, status="active")
        Project.objects.create(project_code="P2", name="Two", client=client_a, branch=self.a,
                               manager=pm2_user, start_date=YESTERDAY, end_date=TODAY, status="completed")
        t1 = Task.objects.create(project=self.p1, title="Late", due_date=YESTERDAY, status="todo")
        Task.objects.create(project=self.p1, title="Done", due_date=TODAY, status="completed")
        for status, hours in (("submitted", "3"), ("approved", "5")):
            Timesheet.objects.create(employee=e1, project=self.p1, task=t1, work_date=TODAY,
                                     hours=Decimal(hours), description="x", status=status)
        Invoice.objects.create(invoice_number="INV-1", client=client_a, branch=self.a, project=self.p1,
                               due_date=YESTERDAY, total=Decimal("100"), balance=Decimal("100"), status="issued")
        paid = Invoice.objects.create(invoice_number="INV-2", client=client_a, branch=self.a, project=self.p1,
                                      due_date=TODAY, total=Decimal("50"), amount_paid=Decimal("50"),
                                      balance=Decimal("0"), status="paid")
        Payment.objects.create(payment_number="PAY-1", invoice=paid, client=client_a, amount=Decimal("50"),
                               method="cash", reference="R1", payment_date=TODAY, status="confirmed")

    def test_executive_dashboard_reflects_live_data(self):
        d = data(self.admin.get("/api/v1/dashboard/executive/"))
        k = d["kpis"]
        self.assertEqual((k["total_employees"], k["total_branches"], k["total_clients"], k["total_leads"]), (3, 2, 2, 3))
        self.assertEqual((k["active_projects"], k["pending_quotations"], k["total_invoices"]), (1, 1, 2))
        money = lambda rows: {r["currency"]: Decimal(str(r["amount"])) for r in rows}
        self.assertEqual(money(k["outstanding_balance"]), {"USD": Decimal("100.00")})
        self.assertEqual(money(k["payments_received"]), {"USD": Decimal("50.00")})
        self.assertEqual(d["pending_approvals"], {"quotations": 1, "timesheets": 1})
        self.assertTrue(len(d["recent_activity"]) > 0)

    def test_executive_dashboard_is_super_admin_only(self):
        for c in (self.hr_a, self.sales, self.pm, self.fin, self.emp_user):
            self.assertEqual(c.get("/api/v1/dashboard/executive/").status_code, 403)

    def test_hr_dashboard_and_branch_isolation(self):
        d = data(self.hr_a.get("/api/v1/dashboard/hr/"))
        self.assertEqual((d["kpis"]["total_employees"], d["kpis"]["active_employees"]), (2, 1))
        self.assertEqual((d["kpis"]["recruitment_applications"], d["interview_pipeline"]["interview"]), (1, 1))
        self.assertEqual(d["employees_by_branch"], [{"branch": "A", "count": 2}])
        self.assertEqual(data(self.hr_b.get("/api/v1/dashboard/hr/"))["kpis"]["total_employees"], 1)
        self.assertEqual(self.sales.get("/api/v1/dashboard/hr/").status_code, 403)

    def test_sales_dashboard(self):
        k = data(self.sales.get("/api/v1/dashboard/sales/"))["kpis"]
        self.assertEqual((k["leads"], k["qualified_leads"], k["opportunities"]), (2, 1, 3))
        self.assertEqual((k["won_opportunities"], k["lost_opportunities"]), (1, 1))
        self.assertEqual(Decimal(str(k["pipeline_value"])), Decimal("1000"))
        self.assertEqual((k["quotations"], k["pending_approvals"]), (1, 1))

    def test_projects_dashboard_is_limited_to_managed_projects(self):
        d = data(self.pm.get("/api/v1/dashboard/projects/"))
        k = d["kpis"]
        self.assertEqual((k["active_projects"], k["completed_projects"]), (1, 0))      # P2 belongs to pm2
        self.assertEqual((k["overdue_tasks"], k["pending_timesheets"], k["approved_timesheets"]), (1, 1, 1))
        self.assertEqual(Decimal(str(k["approved_hours"])), Decimal("5"))
        self.assertEqual(d["project_progress"][0]["progress"], 50)
        self.assertEqual(data(self.pm2.get("/api/v1/dashboard/projects/"))["kpis"]["completed_projects"], 1)
        self.assertEqual(data(self.admin.get("/api/v1/dashboard/projects/"))["kpis"]["active_projects"], 1)

    def test_finance_dashboard_marks_overdue_and_reports_reconciliation(self):
        d = data(self.fin.get("/api/v1/dashboard/finance/"))
        k = d["kpis"]
        self.assertEqual((k["total_invoices"], k["paid_invoices"], k["overdue_invoices"]), (2, 1, 1))
        self.assertEqual([Decimal(str(r["amount"])) for r in k["outstanding_balance"]], [Decimal("100.00")])
        self.assertEqual(d["reconciliation_status"]["confirmed"], 1)
        self.assertEqual(self.sales.get("/api/v1/dashboard/finance/").status_code, 403)

    def test_branch_filter_parameter(self):
        d = data(self.admin.get(f"/api/v1/dashboard/executive/?branch={self.b.id}"))
        self.assertEqual((d["kpis"]["total_employees"], d["kpis"]["total_leads"]), (1, 1))
        self.assertEqual(self.hr_b.get(f"/api/v1/dashboard/hr/?branch={self.a.id}").status_code, 403)
        self.assertEqual(self.admin.get("/api/v1/dashboard/executive/?branch=nope").status_code, 400)

    def test_employee_and_anonymous_are_denied(self):
        for name in ("executive", "hr", "sales", "projects", "finance"):
            self.assertEqual(self.emp_user.get(f"/api/v1/dashboard/{name}/").status_code, 403)
            self.assertIn(APIClient().get(f"/api/v1/dashboard/{name}/").status_code, (401, 403))