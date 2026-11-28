import datetime
from decimal import Decimal
from django.test import TestCase
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.hr.models import Employee
from apps.notifications.models import Notification
from apps.organizations.models import Organization

TODAY = datetime.date.today()
TODAY_ISO = TODAY.isoformat()
FUTURE = (TODAY + datetime.timedelta(days=30)).isoformat()
QUAL = {"business_requirement": "ERP system", "budget": "10000", "customer_interest": "high",
        "expected_timeline": "3 months"}

def plain(res, code=200):          # standard DRF responses: the object itself
    assert res.status_code == code, (res.status_code, res.data)
    return res.data

def wrapped(res, code=200):        # action responses: {"success", "message", "data", "errors"}
    assert res.status_code == code, (res.status_code, res.data)
    return res.data["data"]

def kinds(user):
    return set(Notification.objects.filter(recipient=user).values_list("kind", flat=True))

class WorkflowTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.seller = make_user("seller", "sales", [self.a])
        self.manager = make_user("mgr", "sales", [self.a])
        self.a.manager = self.manager
        self.a.save()
        self.pm = make_user("pm", "project_manager", [self.a])
        self.emp_user = make_user("emp", "employee", [self.a])
        self.fin = make_user("fin", "finance", [self.a])
        self.admin = make_user("root", "super_admin", [])
        self.emp = Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                           email="eva@x.com", branch=self.a, hire_date=TODAY, user=self.emp_user)
        self.s, self.m, self.p = api_client(self.seller), api_client(self.manager), api_client(self.pm)
        self.e, self.f, self.root = api_client(self.emp_user), api_client(self.fin), api_client(self.admin)

    def test_lead_to_payment_end_to_end(self):
        s, m, p, e, f, root = self.s, self.m, self.p, self.e, self.f, self.root

        # 1-2. Lead captured and qualified
        lead = plain(s.post("/api/v1/leads/", {"name": "Sahan", "company_name": "Sahan Foods",
                     "email": "sahan@foods.test", "branch": str(self.a.id)}, format="json"), 201)
        lid = lead["id"]
        self.assertEqual(lead["status"], "new")
        self.assertEqual(wrapped(s.post(f"/api/v1/leads/{lid}/qualify/", QUAL, format="json"))["status"], "qualified")

        # 3. Quotation and approval (a seller cannot approve their own quote)
        quote = wrapped(s.post("/api/v1/quotes/", {"lead": lid, "branch": str(self.a.id), "valid_until": FUTURE,
                        "tax_rate": "10", "items": [{"description": "ERP rollout", "quantity": "100",
                        "unit_price": "50"}]}, format="json"), 201)
        qid = quote["id"]
        self.assertEqual(Decimal(quote["total"]), Decimal("5500.00"))
        self.assertEqual(wrapped(s.post(f"/api/v1/quotes/{qid}/submit/"))["status"], "pending_approval")
        self.assertEqual(s.post(f"/api/v1/quotes/{qid}/approve/").status_code, 403)
        self.assertEqual(wrapped(m.post(f"/api/v1/quotes/{qid}/approve/"))["status"], "approved")

        # 4. Client conversion
        converted = wrapped(s.post(f"/api/v1/leads/{lid}/convert/", {"address": "Mogadishu"}, format="json"), 201)
        cid = converted["client"]["id"]
        self.assertEqual(converted["lead"]["status"], "converted")

        # Opportunity walked to Won
        opp = plain(s.post("/api/v1/opportunities/", {"name": "ERP deal", "client": cid, "branch": str(self.a.id),
                    "value": "5500", "probability": 10, "expected_close_date": FUTURE}, format="json"), 201)
        for stage in ("qualification", "proposal", "negotiation", "won"):
            wrapped(s.post(f"/api/v1/opportunities/{opp['id']}/stage/", {"stage": stage}, format="json"))

        # 5. Approved quote becomes a project; PM staffs it and creates a task
        project = wrapped(s.post(f"/api/v1/quotes/{qid}/convert/", {"name": "ERP Rollout", "manager": str(self.pm.id),
                          "start_date": TODAY_ISO, "end_date": FUTURE}, format="json"), 201)["project"]
        pid = project["id"]
        self.assertEqual((project["status"], Decimal(project["budget"])), ("draft", Decimal("5500.00")))
        self.assertEqual(str(project["client"]), str(cid))
        wrapped(p.post(f"/api/v1/projects/{pid}/members/", {"employee": str(self.emp.id), "role": "Dev"},
                       format="json"), 201)
        for status in ("planned", "active"):
            wrapped(p.post(f"/api/v1/projects/{pid}/status/", {"status": status}, format="json"))
        task = plain(p.post("/api/v1/tasks/", {"project": pid, "title": "Build", "due_date": FUTURE,
                     "assigned_employee": str(self.emp.id)}, format="json"), 201)
        tid = task["id"]
        for status in ("in_progress", "review"):
            wrapped(e.post(f"/api/v1/tasks/{tid}/status/", {"status": status}, format="json"))
        self.assertEqual(e.post(f"/api/v1/tasks/{tid}/status/", {"status": "completed"}, format="json").status_code, 403)
        self.assertEqual(wrapped(p.post(f"/api/v1/tasks/{tid}/status/", {"status": "completed"}, format="json"))["status"], "completed")

        # 6. Timesheet submitted by the employee and approved by the project manager
        ts = plain(e.post("/api/v1/timesheets/", {"project": pid, "task": tid, "work_date": TODAY_ISO,
                   "hours": "8", "description": "Built it"}, format="json"), 201)
        wrapped(e.post(f"/api/v1/timesheets/{ts['id']}/submit/"))
        self.assertEqual(wrapped(p.post(f"/api/v1/timesheets/{ts['id']}/approve/"))["status"], "approved")

        # 7. Finance invoices the approved work (and cannot bill it twice)
        billable = wrapped(f.get(f"/api/v1/invoices/billable/?project={pid}"))
        self.assertEqual((billable["count"], Decimal(str(billable["total_hours"]))), (1, Decimal("8")))
        invoice = wrapped(f.post("/api/v1/invoices/", {"project": pid, "due_date": FUTURE, "tax_rate": "10",
                          "hourly_rate": "100.00", "timesheet_ids": [ts["id"]]}, format="json"), 201)
        iid = invoice["id"]
        self.assertEqual(Decimal(invoice["total"]), Decimal("880.00"))
        self.assertEqual(wrapped(f.get(f"/api/v1/invoices/billable/?project={pid}"))["count"], 0)
        self.assertEqual(wrapped(f.post(f"/api/v1/invoices/{iid}/issue/"))["status"], "issued")

        # 8. Payments recorded and reconciled
        pay1 = wrapped(f.post("/api/v1/payments/", {"invoice": iid, "amount": "400", "method": "bank_transfer",
                        "reference": "BT-1", "payment_date": TODAY_ISO}, format="json"), 201)
        self.assertEqual(plain(f.get(f"/api/v1/invoices/{iid}/"))["status"], "partially_paid")
        pay2 = wrapped(f.post("/api/v1/payments/", {"invoice": iid, "amount": "480", "method": "bank_transfer",
                        "reference": "BT-2", "payment_date": TODAY_ISO}, format="json"), 201)
        for pay in (pay1, pay2):
            wrapped(f.post(f"/api/v1/payments/{pay['id']}/reconcile/"))
        final = plain(f.get(f"/api/v1/invoices/{iid}/"))
        self.assertEqual((final["status"], Decimal(final["balance"])), ("paid", Decimal("0.00")))
        history = [h["to_status"] for h in wrapped(f.get(f"/api/v1/invoices/{iid}/history/"))]
        self.assertEqual(history, ["draft", "issued", "partially_paid", "paid"])

        # Dashboards reflect everything that just happened
        ex = wrapped(root.get("/api/v1/dashboard/executive/"))["kpis"]
        self.assertEqual((ex["total_clients"], ex["total_leads"], ex["active_projects"], ex["total_invoices"]), (1, 1, 1, 1))
        self.assertEqual(wrapped(f.get("/api/v1/dashboard/finance/"))["kpis"]["paid_invoices"], 1)
        self.assertEqual(wrapped(f.get("/api/v1/dashboard/finance/"))["reconciliation_status"]["reconciled"], 2)
        self.assertEqual(wrapped(s.get("/api/v1/dashboard/sales/"))["kpis"]["won_opportunities"], 1)
        pk = wrapped(p.get("/api/v1/dashboard/projects/"))["kpis"]
        self.assertEqual((pk["approved_timesheets"], Decimal(str(pk["approved_hours"]))), (1, Decimal("8")))

        # Notifications reached the right people
        self.assertIn("quote_submitted", kinds(self.manager))
        self.assertIn("quote_approved", kinds(self.seller))
        self.assertTrue({"project_assigned", "timesheet_submitted"} <= kinds(self.pm))
        self.assertTrue({"project_assigned", "task_assigned", "timesheet_approved"} <= kinds(self.emp_user))

        # Audit trail captured the money movements
        self.assertGreaterEqual(AuditLog.objects.filter(record_type="invoice", action="status_change").count(), 3)
        self.assertEqual(AuditLog.objects.filter(record_type="payment", action="create").count(), 2)

        # Branch isolation: another branch sees none of it
        sales_b = api_client(make_user("sales_b", "sales", [self.b]))
        fin_b = api_client(make_user("fin_b", "finance", [self.b]))
        self.assertEqual(sales_b.get(f"/api/v1/leads/{lid}/").status_code, 404)
        self.assertEqual(fin_b.get(f"/api/v1/invoices/{iid}/").status_code, 404)
        self.assertEqual(wrapped(fin_b.get("/api/v1/dashboard/finance/"))["kpis"]["total_invoices"], 0)