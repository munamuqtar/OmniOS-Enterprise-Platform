import datetime
import uuid
from decimal import Decimal
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client
from apps.hr.models import Employee
from apps.organizations.models import Organization
from apps.projects.models import Project, Task
from apps.timesheets.models import Timesheet

TODAY = datetime.date.today()

def days(n):
    return TODAY + datetime.timedelta(days=n)

class FinanceTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.fin = make_user("fin", "finance", [self.a])
        self.f = api_client(self.fin)
        self.pm = make_user("pm", "project_manager", [self.a])
        self.pm2 = make_user("pm2", "project_manager", [self.a])
        self.admin = make_user("root", "super_admin", [])
        self.client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.project = self._project("P1", self.pm)
        self.project2 = self._project("P2", self.pm2)
        self.emp = Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                           email="e1@x.com", branch=self.a, hire_date=TODAY)
        self.task1 = Task.objects.create(project=self.project, title="Design", due_date=TODAY)
        self.task2 = Task.objects.create(project=self.project, title="Build", due_date=TODAY)
        self.task_p2 = Task.objects.create(project=self.project2, title="Other", due_date=TODAY)
        self.ts1 = self._ts(self.project, self.task1, "8")
        self.ts2 = self._ts(self.project, self.task1, "2")
        self.ts3 = self._ts(self.project, self.task2, "5")
        self.ts_pending = self._ts(self.project, self.task2, "1", status="submitted")
        self.ts_p2 = self._ts(self.project2, self.task_p2, "4")

    # ---- helpers ----
    def _project(self, code, manager):
        return Project.objects.create(
            project_code=code, name=f"Proj {code}", client=self.client_rec, branch=self.a, manager=manager,
            start_date=days(-30), end_date=days(60), status="active")

    def _ts(self, project, task, hours, status="approved"):
        return Timesheet.objects.create(employee=self.emp, project=project, task=task, work_date=TODAY,
                                        hours=Decimal(hours), description="Work", status=status)

    def inv_payload(self, **over):
        p = {"project": str(self.project.id), "due_date": days(30).isoformat(), "currency": "USD",
             "discount": "0", "tax_rate": "10", "hourly_rate": "50.00",
             "timesheet_ids": [str(self.ts1.id), str(self.ts2.id), str(self.ts3.id)]}
        p.update(over)
        return p

    def create_invoice(self, client=None, **over):
        return (client or self.f).post("/api/v1/invoices/", self.inv_payload(**over), format="json")

    def make_invoice(self, issue=True, **over):
        res = self.create_invoice(**over)
        self.assertEqual(res.status_code, 201, res.data)
        iid = res.data["data"]["id"]
        if issue:
            self.assertEqual(self.f.post(f"/api/v1/invoices/{iid}/issue/").status_code, 200)
        return iid

    def pay(self, iid, amount, client=None, **over):
        body = {"invoice": iid, "amount": str(amount), "method": "bank_transfer",
                "reference": uuid.uuid4().hex[:10], "payment_date": TODAY.isoformat()}
        body.update(over)
        return (client or self.f).post("/api/v1/payments/", body, format="json")

    def invoice(self, iid):
        return self.f.get(f"/api/v1/invoices/{iid}/").data

    # ---- invoice building ----
    def test_totals_and_items_server_side(self):
        res = self.create_invoice()
        self.assertEqual(res.status_code, 201)
        d = res.data["data"]
        # 10h design + 5h build at 50 = 750, tax 10% = 75, total 825
        self.assertEqual(Decimal(d["subtotal"]), Decimal("750.00"))
        self.assertEqual(Decimal(d["tax"]), Decimal("75.00"))
        self.assertEqual(Decimal(d["total"]), Decimal("825.00"))
        self.assertEqual(sorted(Decimal(i["line_total"]) for i in d["items"]),
                         [Decimal("250.00"), Decimal("500.00")])
        self.assertEqual(d["status"], "draft")
        self.assertTrue(d["invoice_number"].startswith("INV-"))
        self.assertEqual(Timesheet.objects.filter(invoice_item__isnull=False).count(), 3)

    def test_client_cannot_inject_totals(self):
        d = self.create_invoice(total="1.00", subtotal="1.00", balance="0").data["data"]
        self.assertEqual(Decimal(d["total"]), Decimal("825.00"))

    def test_only_approved_timesheets(self):
        res = self.create_invoice(timesheet_ids=[str(self.ts_pending.id)])
        self.assertEqual(res.status_code, 400)

    def test_timesheet_from_other_project_rejected(self):
        res = self.create_invoice(timesheet_ids=[str(self.ts1.id), str(self.ts_p2.id)])
        self.assertEqual(res.status_code, 400)

    def test_timesheet_cannot_be_billed_twice(self):
        self.make_invoice(issue=False)
        self.assertEqual(self.create_invoice(timesheet_ids=[str(self.ts1.id)]).status_code, 400)

    def test_issue_flow(self):
        iid = self.make_invoice()
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("issued", Decimal("825.00")))
        self.assertEqual(self.f.post(f"/api/v1/invoices/{iid}/issue/").status_code, 400)

    def test_only_drafts_can_be_edited(self):
        iid = self.make_invoice(issue=False)
        body = {"project": str(self.project.id), "due_date": days(30).isoformat(),
                "discount": "25", "tax_rate": "10"}
        res = self.f.put(f"/api/v1/invoices/{iid}/", body, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        # 750 - 25 = 725, tax 72.50, total 797.50
        self.assertEqual(Decimal(res.data["data"]["total"]), Decimal("797.50"))
        self.f.post(f"/api/v1/invoices/{iid}/issue/")
        self.assertEqual(self.f.put(f"/api/v1/invoices/{iid}/", body, format="json").status_code, 400)

    # ---- payments ----
    def test_partial_then_full_payment(self):
        iid = self.make_invoice()
        res = self.pay(iid, 300)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["data"]["payment_number"].startswith("PAY-"))
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("partially_paid", Decimal("525.00")))
        self.assertEqual(self.pay(iid, 525).status_code, 201)
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("paid", Decimal("0.00")))

    def test_overpayment_needs_super_admin_authorization(self):
        iid = self.make_invoice()
        self.assertEqual(self.pay(iid, 900).status_code, 400)
        self.assertEqual(self.pay(iid, 900, allow_overpayment=True).status_code, 400)   # finance cannot authorize
        res = self.pay(iid, 900, client=api_client(self.admin), allow_overpayment=True)
        self.assertEqual(res.status_code, 201, res.data)
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("paid", Decimal("0.00")))

    def test_payment_validation(self):
        iid = self.make_invoice()
        self.assertEqual(self.pay(iid, 0).status_code, 400)
        self.assertEqual(self.pay(iid, 10, reference="").status_code, 400)
        self.assertEqual(self.pay(iid, 10, payment_date=days(1).isoformat()).status_code, 400)
        self.assertEqual(self.pay(iid, 10, reference="DUP1").status_code, 201)
        self.assertEqual(self.pay(iid, 10, reference="DUP1").status_code, 400)
        extra = self._ts(self.project, self.task1, "3")
        draft = self.make_invoice(issue=False, timesheet_ids=[str(extra.id)])
        self.assertEqual(self.pay(draft, 5).status_code, 400)     # draft invoices take no payments

    def test_rejecting_a_payment_reopens_the_balance(self):
        iid = self.make_invoice()
        pid = self.pay(iid, 825).data["data"]["id"]
        self.assertEqual(self.invoice(iid)["status"], "paid")
        self.assertEqual(self.f.post(f"/api/v1/payments/{pid}/reject/", {}, format="json").status_code, 400)
        res = self.f.post(f"/api/v1/payments/{pid}/reject/", {"reason": "Bounced"}, format="json")
        self.assertEqual(res.status_code, 200)
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("issued", Decimal("825.00")))

    def test_reconcile_rules(self):
        iid = self.make_invoice()
        pid = self.pay(iid, 100).data["data"]["id"]
        res = self.f.post(f"/api/v1/payments/{pid}/reconcile/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["status"], "reconciled")
        self.assertEqual(self.f.post(f"/api/v1/payments/{pid}/reconcile/").status_code, 400)
        self.assertEqual(self.f.post(f"/api/v1/payments/{pid}/reject/", {"reason": "x"},
                                     format="json").status_code, 400)

    def test_pending_payment_does_not_count_until_confirmed(self):
        iid = self.make_invoice()
        pid = self.pay(iid, 300, initial_status="pending").data["data"]["id"]
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["amount_paid"])), ("issued", Decimal("0.00")))
        self.assertEqual(self.f.post(f"/api/v1/payments/{pid}/confirm/").status_code, 200)
        d = self.invoice(iid)
        self.assertEqual((d["status"], Decimal(d["balance"])), ("partially_paid", Decimal("525.00")))

    # ---- cancel and overdue ----
    def test_cancel_needs_reason_and_frees_timesheets(self):
        iid = self.make_invoice(issue=False)
        self.assertEqual(self.f.post(f"/api/v1/invoices/{iid}/cancel/", {}, format="json").status_code, 400)
        res = self.f.post(f"/api/v1/invoices/{iid}/cancel/", {"reason": "Wrong rate"}, format="json")
        self.assertEqual(res.status_code, 200)
        billable = self.f.get(f"/api/v1/invoices/billable/?project={self.project.id}")
        self.assertEqual(billable.data["data"]["count"], 3)

    def test_cannot_cancel_invoice_with_payments(self):
        iid = self.make_invoice()
        self.pay(iid, 100)
        res = self.f.post(f"/api/v1/invoices/{iid}/cancel/", {"reason": "Oops"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_overdue_status_and_payoff(self):
        iid = self.make_invoice(issue_date=days(-10).isoformat(), due_date=days(-1).isoformat())
        self.assertEqual(self.invoice(iid)["status"], "overdue")
        self.pay(iid, 100)
        self.assertEqual(self.invoice(iid)["status"], "overdue")    # still late after a partial payment
        self.pay(iid, 725)
        self.assertEqual(self.invoice(iid)["status"], "paid")

    # ---- access control ----
    def test_role_scopes(self):
        mine = self.make_invoice()
        other = self.make_invoice(project=str(self.project2.id), timesheet_ids=[str(self.ts_p2.id)])
        pm = api_client(self.pm)
        self.assertEqual([i["id"] for i in pm.get("/api/v1/invoices/").data["results"]], [mine])
        sales = api_client(make_user("sales1", "sales", [self.a]))
        self.assertEqual(len(sales.get("/api/v1/invoices/").data["results"]), 2)
        self.assertEqual(sales.post("/api/v1/invoices/", self.inv_payload(), format="json").status_code, 403)
        self.assertEqual(sales.get("/api/v1/payments/").status_code, 403)
        self.assertEqual(pm.get("/api/v1/payments/").status_code, 403)
        for role in ("hr", "employee"):
            self.assertEqual(api_client(make_user(f"{role}1", role, [self.a])).get("/api/v1/invoices/").status_code, 403)

    def test_branch_isolation(self):
        iid = self.make_invoice()
        fin_b = api_client(make_user("finb", "finance", [self.b]))
        self.assertEqual(len(fin_b.get("/api/v1/invoices/").data["results"]), 0)
        self.assertEqual(fin_b.get(f"/api/v1/invoices/{iid}/").status_code, 404)
        self.assertEqual(self.pay(iid, 10, client=fin_b).status_code, 400)

    # ---- billable work and history ----
    def test_billable_endpoint(self):
        url = f"/api/v1/invoices/billable/?project={self.project.id}"
        self.assertEqual(self.f.get(url).data["data"]["count"], 3)        # pending timesheet excluded
        self.make_invoice(issue=False)
        self.assertEqual(self.f.get(url).data["data"]["count"], 0)
        self.assertEqual(self.f.get("/api/v1/invoices/billable/").status_code, 400)
        sales = api_client(make_user("sales2", "sales", [self.a]))
        self.assertEqual(sales.get(url).status_code, 403)

    def test_status_history_is_tracked(self):
        iid = self.make_invoice()
        self.pay(iid, 825)
        hist = self.f.get(f"/api/v1/invoices/{iid}/history/").data["data"]
        self.assertEqual([h["to_status"] for h in hist], ["draft", "issued", "paid"])

    def test_payments_expose_their_currency(self):
        iid = self.make_invoice()
        res = self.pay(iid, 100)
        self.assertEqual(res.data["data"]["currency"], "USD")