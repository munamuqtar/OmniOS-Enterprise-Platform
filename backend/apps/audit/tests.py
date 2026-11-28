import datetime
import json
from django.test import TestCase
from rest_framework.test import APIClient
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client, Lead
from apps.hr.models import Employee
from apps.organizations.models import Organization
from apps.projects.models import Project
from .models import AuditLog

TODAY = datetime.date.today()

def login(username):
    c = APIClient()
    res = c.post("/api/v1/auth/login/", {"username": username, "password": "Passw0rd!x1"}, format="json")
    assert res.status_code == 200, res.data
    c.credentials(HTTP_AUTHORIZATION="Bearer " + res.data["data"]["access"])
    return c

class AuditTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.sales = make_user("sales1", "sales", [self.a])
        self.body = {"name": "L", "email": "l@x.com", "branch": str(self.a.id)}

    def test_create_is_logged_with_user_branch_and_ip(self):
        res = login("sales1").post("/api/v1/leads/", self.body, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        log = AuditLog.objects.get(record_type="lead", action="create")
        self.assertEqual((log.user, log.module, log.branch), (self.sales, "crm", self.a))
        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.new_values["name"], "L")

    def test_update_logs_only_changed_fields(self):
        c = login("sales1")
        lid = c.post("/api/v1/leads/", self.body, format="json").data["id"]
        c.put(f"/api/v1/leads/{lid}/", {**self.body, "name": "New"}, format="json")
        log = AuditLog.objects.get(record_type="lead", action="update")
        self.assertEqual(log.old_values, {"name": "L"})
        self.assertEqual(log.new_values, {"name": "New"})

    def test_status_change_is_labelled(self):
        c = login("sales1")
        lid = c.post("/api/v1/leads/", self.body, format="json").data["id"]
        c.post(f"/api/v1/leads/{lid}/qualify/", {"business_requirement": "ERP", "budget": "100",
               "customer_interest": "high", "expected_timeline": "1 month"}, format="json")
        log = AuditLog.objects.get(record_type="lead", action="status_change")
        self.assertEqual((log.old_values["status"], log.new_values["status"]), ("new", "qualified"))

    def test_passwords_are_never_logged(self):
        make_user("root", "super_admin", [])
        secret = "Str0ngPass!word1"
        res = login("root").post("/api/v1/users/", {"username": "newbie", "email": "n@x.com", "password": secret,
                                 "role_codes": ["sales"], "branch_ids": [str(self.a.id)]}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        log = AuditLog.objects.get(record_type="user", action="create", record_repr="newbie")
        self.assertNotIn("password", log.new_values)
        self.assertNotIn(secret, json.dumps(log.new_values))

    def test_visibility_is_limited_by_role_module_and_branch(self):
        client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        Lead.objects.create(name="L", email="l@x.com", branch=self.a)
        Employee.objects.create(employee_number="E1", first_name="Eva", last_name="One",
                                email="e1@x.com", branch=self.a, hire_date=TODAY)
        pm = make_user("pm", "project_manager", [self.a])
        Project.objects.create(project_code="P1", name="P", client=client_rec, branch=self.a, manager=pm,
                               start_date=TODAY, end_date=TODAY, status="active")
        modules = lambda c: {r["module"] for r in c.get("/api/v1/audit-logs/").data["results"]}
        self.assertEqual(modules(api_client(make_user("hr_a", "hr", [self.a]))), {"hr"})
        self.assertEqual(modules(api_client(pm)), {"projects"})
        self.assertEqual(modules(api_client(make_user("hr_b", "hr", [self.b]))), set())   # other branch
        for role in ("sales", "employee"):
            self.assertEqual(api_client(make_user(f"{role}9", role, [self.a])).get("/api/v1/audit-logs/").status_code, 403)
        admin = api_client(make_user("root", "super_admin", []))
        for module in ("crm", "hr", "projects"):
            self.assertGreaterEqual(len(admin.get(f"/api/v1/audit-logs/?module={module}").data["results"]), 1)

    def test_audit_log_is_read_only(self):
        admin = api_client(make_user("root", "super_admin", []))
        self.assertEqual(admin.post("/api/v1/audit-logs/", {}, format="json").status_code, 405)

    def test_login_is_logged(self):
        login("sales1")
        self.assertTrue(AuditLog.objects.filter(action="login", user=self.sales, module="auth").exists())