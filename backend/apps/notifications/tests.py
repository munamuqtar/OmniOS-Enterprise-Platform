import datetime
from decimal import Decimal
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client
from apps.finance import services as fin
from apps.finance.models import Invoice, InvoiceItem
from apps.hr.models import Employee
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectMember, Task
from .models import Notification

TODAY = datetime.date.today()
FUTURE = (TODAY + datetime.timedelta(days=30)).isoformat()

def kinds(user):
    return list(Notification.objects.filter(recipient=user).values_list("kind", flat=True))

class SalesNotificationTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.seller = make_user("seller", "sales", [self.a])
        self.manager = make_user("mgr", "sales", [self.a])
        self.a.manager = self.manager
        self.a.save()
        self.s, self.m = api_client(self.seller), api_client(self.manager)
        self.client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)

    def new_quote(self):
        res = self.s.post("/api/v1/quotes/", {
            "client": str(self.client_rec.id), "branch": str(self.a.id), "valid_until": FUTURE,
            "items": [{"description": "x", "quantity": "1", "unit_price": "100"}]}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["data"]["id"]

    def test_lead_assignment_notifies_owner_but_not_the_actor(self):
        res = self.s.post("/api/v1/leads/", {"name": "L", "email": "l@x.com", "branch": str(self.a.id),
                                             "owner": str(self.manager.id)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(kinds(self.manager), ["lead_assigned"])
        self.s.post("/api/v1/leads/", {"name": "M", "email": "m@x.com", "branch": str(self.a.id)}, format="json")
        self.assertEqual(kinds(self.seller), [])          # assigned to themselves: no notification

    def test_quotation_flow_notifications(self):
        q1 = self.new_quote()
        self.s.post(f"/api/v1/quotes/{q1}/submit/")
        self.assertEqual(kinds(self.manager), ["quote_submitted"])
        self.m.post(f"/api/v1/quotes/{q1}/approve/")
        self.assertEqual(kinds(self.seller), ["quote_approved"])
        q2 = self.new_quote()
        self.s.post(f"/api/v1/quotes/{q2}/submit/")
        self.m.post(f"/api/v1/quotes/{q2}/reject/", {"reason": "Too expensive"}, format="json")
        rejected = Notification.objects.get(recipient=self.seller, kind="quote_rejected")
        self.assertIn("Too expensive", rejected.message)

    def test_notification_endpoints(self):
        mine = [Notification.objects.create(recipient=self.seller, kind="lead_assigned", title=f"n{i}") for i in range(2)]
        theirs = Notification.objects.create(recipient=self.manager, kind="lead_assigned", title="not mine")
        self.assertEqual(len(self.s.get("/api/v1/notifications/").data["results"]), 2)
        self.assertEqual(self.s.get("/api/v1/notifications/unread-count/").data["data"]["unread"], 2)
        self.assertEqual(self.s.post(f"/api/v1/notifications/{mine[0].id}/read/").status_code, 200)
        self.assertEqual(self.s.get("/api/v1/notifications/unread-count/").data["data"]["unread"], 1)
        self.assertEqual(self.s.post(f"/api/v1/notifications/{theirs.id}/read/").status_code, 404)
        self.s.post("/api/v1/notifications/read-all/")
        self.assertEqual(self.s.get("/api/v1/notifications/unread-count/").data["data"]["unread"], 0)

class WorkNotificationTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.pm = make_user("pm", "project_manager", [self.a])
        self.emp_user = make_user("emp1", "employee", [self.a])
        self.emp = Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                           email="e1@x.com", branch=self.a, hire_date=TODAY, user=self.emp_user)
        self.client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.project = Project.objects.create(
            project_code="P1", name="Proj", client=self.client_rec, branch=self.a, manager=self.pm,
            start_date=TODAY - datetime.timedelta(days=10), end_date=TODAY + datetime.timedelta(days=60),
            status="active")
        self.task = Task.objects.create(project=self.project, title="T", due_date=TODAY)
        self.pmc, self.ec = api_client(self.pm), api_client(self.emp_user)

    def test_project_and_task_assignment(self):
        res = self.pmc.post(f"/api/v1/projects/{self.project.id}/members/", {"employee": str(self.emp.id)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(kinds(self.emp_user), ["project_assigned"])
        res = self.pmc.post("/api/v1/tasks/", {"project": str(self.project.id), "title": "New", "due_date": FUTURE,
                                               "assigned_employee": str(self.emp.id)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertCountEqual(kinds(self.emp_user), ["project_assigned", "task_assigned"])

    def test_timesheet_notifications(self):
        ProjectMember.objects.create(project=self.project, employee=self.emp)
        res = self.ec.post("/api/v1/timesheets/", {"project": str(self.project.id), "task": str(self.task.id),
                           "work_date": TODAY.isoformat(), "hours": "4", "description": "x"}, format="json")
        tid = res.data["id"]
        self.ec.post(f"/api/v1/timesheets/{tid}/submit/")
        self.assertEqual(kinds(self.pm), ["timesheet_submitted"])
        self.pmc.post(f"/api/v1/timesheets/{tid}/reject/", {"reason": "Wrong task"}, format="json")
        self.assertEqual(kinds(self.emp_user), ["timesheet_rejected"])

    def test_invoice_and_payment_notifications(self):
        fin1 = make_user("fin1", "finance", [self.a])
        fin2 = make_user("fin2", "finance", [self.a])
        inv = Invoice.objects.create(invoice_number="INV-T-1", client=self.client_rec, branch=self.a,
                                     project=self.project, due_date=TODAY + datetime.timedelta(days=30),
                                     subtotal=Decimal("100"), total=Decimal("100"), balance=Decimal("100"),
                                     created_by=fin1)
        InvoiceItem.objects.create(invoice=inv, description="x", quantity=1, unit_price=100, line_total=100)
        fin.issue(inv, fin1)
        self.assertEqual(kinds(self.pm), ["invoice_issued"])
        fin.record_payment(fin1, inv, Decimal("40"), "cash", "R1", TODAY)
        self.assertEqual(kinds(fin2), ["payment_recorded"])
        self.assertEqual(kinds(fin1), [])                 # the person who recorded it is not notified