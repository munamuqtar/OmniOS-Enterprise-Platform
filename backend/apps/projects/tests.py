import datetime
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client
from apps.hr.models import Employee
from apps.organizations.models import Organization

TODAY = datetime.date.today()
START = TODAY.isoformat()
END = (TODAY + datetime.timedelta(days=60)).isoformat()
DUE = (TODAY + datetime.timedelta(days=14)).isoformat()

class ProjectBase(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.pm = make_user("pm", "project_manager", [self.a])
        self.pmc = api_client(self.pm)
        self.client_a = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.client_b = Client.objects.create(name="CliB", email="cb@x.com", branch=self.b)
        self.emp_user = make_user("emp1", "employee", [self.a])
        self.emp1 = Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                            email="e1@x.com", branch=self.a, hire_date=TODAY, user=self.emp_user)
        self.emp2 = Employee.objects.create(employee_number="E2", first_name="Eli", last_name="Two",
                                            email="e2@x.com", branch=self.a, hire_date=TODAY)
        self.emp_b = Employee.objects.create(employee_number="E3", first_name="Bo", last_name="Three",
                                             email="e3@x.com", branch=self.b, hire_date=TODAY)
        self.empc = api_client(self.emp_user)

    def payload(self, **over):
        p = {"name": "Website", "client": str(self.client_a.id), "branch": str(self.a.id),
             "manager": str(self.pm.id), "start_date": START, "end_date": END}
        p.update(over)
        return p

    def make_project(self, **over):
        res = self.pmc.post("/api/v1/projects/", self.payload(**over), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    def add_member(self, pid, emp):
        res = self.pmc.post(f"/api/v1/projects/{pid}/members/", {"employee": str(emp.id)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)

    def set_project_status(self, pid, *states):
        for s in states:
            res = self.pmc.post(f"/api/v1/projects/{pid}/status/", {"status": s}, format="json")
            self.assertEqual(res.status_code, 200, res.data)

    def make_task(self, pid, emp=None, title="Task"):
        body = {"project": pid, "title": title, "due_date": DUE}
        if emp:
            body["assigned_employee"] = str(emp.id)
        res = self.pmc.post("/api/v1/tasks/", body, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    def task_status(self, client, tid, status):
        return client.post(f"/api/v1/tasks/{tid}/status/", {"status": status}, format="json")

class ProjectTests(ProjectBase):
    def test_create_project_defaults(self):
        res = self.pmc.post("/api/v1/projects/", self.payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["project_code"].startswith("PRJ-"))
        self.assertEqual(res.data["status"], "draft")

    def test_cannot_create_in_other_branch(self):
        res = self.pmc.post("/api/v1/projects/", self.payload(
            branch=str(self.b.id), client=str(self.client_b.id)), format="json")
        self.assertEqual(res.status_code, 400)

    def test_client_must_match_branch(self):
        res = self.pmc.post("/api/v1/projects/", self.payload(client=str(self.client_b.id)), format="json")
        self.assertEqual(res.status_code, 400)

    def test_end_date_before_start(self):
        res = self.pmc.post("/api/v1/projects/", self.payload(end_date="2000-01-01"), format="json")
        self.assertEqual(res.status_code, 400)

    def test_manager_must_be_project_manager(self):
        res = self.pmc.post("/api/v1/projects/", self.payload(manager=str(self.emp_user.id)), format="json")
        self.assertEqual(res.status_code, 400)

    def test_employee_and_hr_cannot_create_or_hr_read(self):
        self.assertEqual(self.empc.post("/api/v1/projects/", self.payload(), format="json").status_code, 403)
        hr = api_client(make_user("hr1", "hr", [self.a]))
        self.assertEqual(hr.get("/api/v1/projects/").status_code, 403)

    def test_members_rules(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        dup = self.pmc.post(f"/api/v1/projects/{pid}/members/", {"employee": str(self.emp1.id)}, format="json")
        self.assertEqual(dup.status_code, 400)
        other = self.pmc.post(f"/api/v1/projects/{pid}/members/", {"employee": str(self.emp_b.id)}, format="json")
        self.assertEqual(other.status_code, 400)

    def test_employee_sees_only_assigned_projects(self):
        p1 = self.make_project(name="Mine")
        self.make_project(name="Not mine")
        self.add_member(p1, self.emp1)
        res = self.empc.get("/api/v1/projects/")
        self.assertEqual([p["name"] for p in res.data["results"]], ["Mine"])

    def test_cannot_complete_project_with_open_tasks(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        tid = self.make_task(pid, self.emp1)
        self.set_project_status(pid, "planned", "active")
        self.assertEqual(self.pmc.post(f"/api/v1/projects/{pid}/status/", {"status": "completed"},
                                       format="json").status_code, 400)
        for st in ("in_progress", "review", "completed"):
            self.assertEqual(self.task_status(self.pmc, tid, st).status_code, 200)
        self.set_project_status(pid, "completed")

    def test_invalid_project_transition(self):
        pid = self.make_project()
        res = self.pmc.post(f"/api/v1/projects/{pid}/status/", {"status": "active"}, format="json")
        self.assertEqual(res.status_code, 400)   # draft cannot jump to active

    def test_progress_and_report(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        t1 = self.make_task(pid, self.emp1, "One")
        self.make_task(pid, self.emp1, "Two")
        self.set_project_status(pid, "planned", "active")
        for st in ("in_progress", "review", "completed"):
            self.task_status(self.pmc, t1, st)
        self.assertEqual(self.pmc.get(f"/api/v1/projects/{pid}/").data["progress"], 50)
        report = self.pmc.get(f"/api/v1/projects/{pid}/report/").data["data"]
        self.assertEqual((report["tasks_total"], report["progress"]), (2, 50))

class TaskTests(ProjectBase):
    def test_task_requires_project_member(self):
        pid = self.make_project()
        body = {"project": pid, "title": "T", "due_date": DUE, "assigned_employee": str(self.emp1.id)}
        self.assertEqual(self.pmc.post("/api/v1/tasks/", body, format="json").status_code, 400)
        self.add_member(pid, self.emp1)
        self.assertEqual(self.pmc.post("/api/v1/tasks/", body, format="json").status_code, 201)

    def test_employee_status_rules(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        tid = self.make_task(pid, self.emp1)
        self.set_project_status(pid, "planned")
        self.assertEqual(self.task_status(self.empc, tid, "in_progress").status_code, 200)
        self.assertEqual(self.task_status(self.empc, tid, "review").status_code, 200)
        self.assertEqual(self.task_status(self.empc, tid, "completed").status_code, 403)   # PM only
        self.assertEqual(self.task_status(self.pmc, tid, "completed").status_code, 200)

    def test_cannot_skip_task_status(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        tid = self.make_task(pid, self.emp1)
        self.set_project_status(pid, "planned")
        self.assertEqual(self.task_status(self.pmc, tid, "completed").status_code, 400)

    def test_cannot_work_tasks_in_draft_project(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        tid = self.make_task(pid, self.emp1)
        self.assertEqual(self.task_status(self.empc, tid, "in_progress").status_code, 400)

    def test_employee_sees_and_edits_only_own_tasks(self):
        pid = self.make_project()
        self.add_member(pid, self.emp1)
        self.add_member(pid, self.emp2)
        mine = self.make_task(pid, self.emp1, "Mine")
        theirs = self.make_task(pid, self.emp2, "Theirs")
        self.set_project_status(pid, "planned")
        res = self.empc.get("/api/v1/tasks/")
        self.assertEqual([t["title"] for t in res.data["results"]], ["Mine"])
        self.assertEqual(self.task_status(self.empc, theirs, "in_progress").status_code, 404)
        put = self.empc.put(f"/api/v1/tasks/{mine}/", {"project": pid, "title": "x", "due_date": DUE}, format="json")
        self.assertEqual(put.status_code, 403)   # employees can change status only