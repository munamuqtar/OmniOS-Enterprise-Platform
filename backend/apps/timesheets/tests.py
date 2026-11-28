import datetime
from decimal import Decimal
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client
from apps.hr.models import Employee
from apps.organizations.models import Organization
from apps.projects.models import Project, ProjectMember, Task

TODAY = datetime.date.today()

class TimesheetTests(TestCase):

    def test_is_mine_flag_tells_the_ui_who_owns_a_row(self):
        tid = self.create().data["id"]
        self.submit(tid)
        self.assertTrue(self.e.get(f"/api/v1/timesheets/{tid}/").data["is_mine"])
        self.assertFalse(self.p.get(f"/api/v1/timesheets/{tid}/").data["is_mine"])
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.pm = make_user("pm", "project_manager", [self.a])
        self.emp_user = make_user("emp1", "employee", [self.a])
        self.emp1 = Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                            email="e1@x.com", branch=self.a, hire_date=TODAY, user=self.emp_user)
        self.emp2_user = make_user("emp2", "employee", [self.a])
        self.emp2 = Employee.objects.create(employee_number="E2", first_name="Eli", last_name="Two",
                                            email="e2@x.com", branch=self.a, hire_date=TODAY, user=self.emp2_user)
        self.client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.project = self._project("P1", "active", self.pm)
        self.project2 = self._project("P2", "active", self.pm)
        self.draft_project = self._project("P3", "draft", self.pm)
        self.task = Task.objects.create(project=self.project, title="T1", due_date=TODAY)
        self.task2 = Task.objects.create(project=self.project2, title="T2", due_date=TODAY)
        self.draft_task = Task.objects.create(project=self.draft_project, title="T3", due_date=TODAY)
        for p in (self.project, self.project2, self.draft_project):
            ProjectMember.objects.create(project=p, employee=self.emp1)
        self.e = api_client(self.emp_user)
        self.p = api_client(self.pm)

    def _project(self, code, status, manager):
        return Project.objects.create(
            project_code=code, name=f"Proj {code}", client=self.client_rec, branch=self.a, manager=manager,
            start_date=TODAY - datetime.timedelta(days=30), end_date=TODAY + datetime.timedelta(days=60),
            status=status)

    def payload(self, **over):
        p = {"project": str(self.project.id), "task": str(self.task.id),
             "work_date": TODAY.isoformat(), "hours": "7.50", "description": "Worked"}
        p.update(over)
        return p

    def create(self, client=None, **over):
        return (client or self.e).post("/api/v1/timesheets/", self.payload(**over), format="json")

    def submit(self, tid, client=None):
        return (client or self.e).post(f"/api/v1/timesheets/{tid}/submit/")

    def approved(self, hours="7.50", day=None):
        tid = self.create(hours=hours, work_date=(day or TODAY).isoformat()).data["id"]
        self.submit(tid)
        self.p.post(f"/api/v1/timesheets/{tid}/approve/")
        return tid

    def test_create_defaults(self):
        res = self.create()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "draft")
        self.assertEqual(res.data["employee"], self.emp1.id)

    def test_cannot_spoof_employee(self):
        res = self.create(employee=str(self.emp2.id))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["employee"], self.emp1.id)

    def test_invalid_hours(self):
        self.assertEqual(self.create(hours="0").status_code, 400)
        self.assertEqual(self.create(hours="25").status_code, 400)

    def test_daily_total_cannot_exceed_24(self):
        self.assertEqual(self.create(hours="20").status_code, 201)
        self.assertEqual(self.create(hours="5").status_code, 400)

    def test_future_date_rejected(self):
        future = (TODAY + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.create(work_date=future).status_code, 400)

    def test_must_be_project_member(self):
        res = self.create(client=api_client(self.emp2_user))
        self.assertEqual(res.status_code, 400)

    def test_project_must_be_active(self):
        res = self.create(project=str(self.draft_project.id), task=str(self.draft_task.id))
        self.assertEqual(res.status_code, 400)

    def test_task_must_belong_to_project(self):
        self.assertEqual(self.create(task=str(self.task2.id)).status_code, 400)

    def test_submitted_timesheet_is_locked(self):
        tid = self.create().data["id"]
        self.assertEqual(self.submit(tid).status_code, 200)
        res = self.e.put(f"/api/v1/timesheets/{tid}/", self.payload(hours="5"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.submit(tid).status_code, 400)

    def test_approve_and_history(self):
        tid = self.create().data["id"]
        self.submit(tid)
        res = self.p.post(f"/api/v1/timesheets/{tid}/approve/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["status"], "approved")
        hist = self.p.get(f"/api/v1/timesheets/{tid}/history/")
        self.assertEqual(len(hist.data["data"]), 2)    # submitted, approved

    def test_reject_needs_reason_then_correct_and_resubmit(self):
        tid = self.create().data["id"]
        self.submit(tid)
        url = f"/api/v1/timesheets/{tid}/reject/"
        self.assertEqual(self.p.post(url, {}, format="json").status_code, 400)
        self.assertEqual(self.p.post(url, {"reason": "Wrong task"}, format="json").status_code, 200)
        fix = self.e.put(f"/api/v1/timesheets/{tid}/", self.payload(hours="6"), format="json")
        self.assertEqual(fix.status_code, 200)
        self.assertEqual(self.submit(tid).data["data"]["status"], "submitted")
        hist = self.p.get(f"/api/v1/timesheets/{tid}/history/")
        self.assertEqual(len(hist.data["data"]), 3)    # submitted, rejected, submitted

    def test_only_the_projects_manager_reviews(self):
        other_pm = api_client(make_user("pm2", "project_manager", [self.a]))
        tid = self.create().data["id"]
        self.submit(tid)
        self.assertEqual(other_pm.post(f"/api/v1/timesheets/{tid}/approve/").status_code, 404)  # cannot even see it
        self.assertEqual(self.e.post(f"/api/v1/timesheets/{tid}/approve/").status_code, 403)

    def test_cannot_review_own_timesheet(self):
        boss = make_user("pm3", "project_manager", [self.a])
        emp3 = Employee.objects.create(employee_number="E9", first_name="Pm", last_name="Self",
                                       email="pm3@x.com", branch=self.a, hire_date=TODAY, user=boss)
        proj = self._project("P9", "active", boss)
        ProjectMember.objects.create(project=proj, employee=emp3)
        task = Task.objects.create(project=proj, title="Own", due_date=TODAY)
        c = api_client(boss)
        tid = c.post("/api/v1/timesheets/", self.payload(project=str(proj.id), task=str(task.id)),
                     format="json").data["id"]
        c.post(f"/api/v1/timesheets/{tid}/submit/")
        self.assertEqual(c.post(f"/api/v1/timesheets/{tid}/approve/").status_code, 403)

    def test_visibility_rules(self):
        tid = self.create().data["id"]
        self.assertEqual(len(self.e.get("/api/v1/timesheets/").data["results"]), 1)
        self.assertEqual(len(api_client(self.emp2_user).get("/api/v1/timesheets/").data["results"]), 0)
        self.assertEqual(len(self.p.get("/api/v1/timesheets/").data["results"]), 0)     # draft hidden from PM
        self.submit(tid)
        self.assertEqual(len(self.p.get("/api/v1/timesheets/").data["results"]), 1)
        sales = api_client(make_user("sales1", "sales", [self.a]))
        self.assertEqual(sales.get("/api/v1/timesheets/").status_code, 403)

    def test_finance_sees_only_approved_and_hr_is_read_only(self):
        approved_id = self.approved(day=TODAY - datetime.timedelta(days=1))
        pending_id = self.create().data["id"]
        self.submit(pending_id)
        fin = api_client(make_user("fin1", "finance", [self.a]))
        res = fin.get("/api/v1/timesheets/")
        self.assertEqual([t["id"] for t in res.data["results"]], [approved_id])
        hr = api_client(make_user("hr1", "hr", [self.a]))
        self.assertEqual(len(hr.get("/api/v1/timesheets/").data["results"]), 2)
        self.assertEqual(hr.post("/api/v1/timesheets/", self.payload(), format="json").status_code, 403)

    def test_approved_work_totals(self):
        self.approved("7.50")
        self.approved("2.00")
        fin = api_client(make_user("fin2", "finance", [self.a]))
        rows = fin.get("/api/v1/timesheets/approved-work/").data["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(Decimal(str(rows[0]["hours"])), Decimal("9.50"))