from unittest import mock
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.accounts.throttles import LoginRateThrottle
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.organizations.models import Organization

ROLES = ["super_admin", "hr", "sales", "finance", "project_manager", "employee"]
ALL = set(ROLES)
ADMIN = {"super_admin"}
V = "/api/v1/"

# Roles allowed to READ each endpoint. Everyone else must get 403.
READ = {
    V + "organizations/": ADMIN,
    V + "branches/": ALL,
    V + "users/": ADMIN,
    V + "roles/": ADMIN,
    V + "permissions/": ADMIN,
    V + "employees/": ALL,
    V + "departments/": ALL,
    V + "vacancies/": {"super_admin", "hr"},
    V + "candidates/": {"super_admin", "hr"},
    V + "recruitment-applications/": {"super_admin", "hr"},
    V + "leads/": {"super_admin", "sales"},
    V + "opportunities/": {"super_admin", "sales"},
    V + "clients/": {"super_admin", "sales", "finance", "project_manager"},
    V + "quotes/": {"super_admin", "sales", "finance"},
    V + "projects/": {"super_admin", "project_manager", "sales", "finance", "employee"},
    V + "tasks/": {"super_admin", "project_manager", "sales", "employee"},
    V + "timesheets/": {"super_admin", "hr", "finance", "project_manager", "employee"},
    V + "invoices/": {"super_admin", "finance", "sales", "project_manager"},
    V + "payments/": {"super_admin", "finance"},
    V + "audit-logs/": {"super_admin", "hr", "finance", "project_manager"},
    V + "notifications/": ALL,
    V + "auth/me/": ALL,
    V + "dashboard/executive/": ADMIN,
    V + "dashboard/hr/": {"super_admin", "hr"},
    V + "dashboard/sales/": {"super_admin", "sales"},
    V + "dashboard/projects/": {"super_admin", "project_manager"},
    V + "dashboard/finance/": {"super_admin", "finance"},
}

# Roles allowed to CREATE records. Everyone else must get 403.
WRITE = {
    V + "organizations/": ADMIN,
    V + "branches/": ADMIN,
    V + "users/": ADMIN,
    V + "roles/": ADMIN,
    V + "employees/": {"super_admin", "hr"},
    V + "departments/": {"super_admin", "hr"},
    V + "vacancies/": {"super_admin", "hr"},
    V + "candidates/": {"super_admin", "hr"},
    V + "recruitment-applications/": {"super_admin", "hr"},
    V + "leads/": {"super_admin", "sales"},
    V + "clients/": {"super_admin", "sales"},
    V + "opportunities/": {"super_admin", "sales"},
    V + "quotes/": {"super_admin", "sales"},
    V + "projects/": {"super_admin", "project_manager"},
    V + "tasks/": {"super_admin", "project_manager"},
    V + "timesheets/": {"super_admin", "employee", "project_manager"},
    V + "invoices/": {"super_admin", "finance"},
    V + "payments/": {"super_admin", "finance"},
}

class PermissionMatrixTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.clients = {r: api_client(make_user(f"u_{r}", r, [] if r == "super_admin" else [self.a]))
                        for r in ROLES}

    def test_read_matrix_matches_the_spec(self):
        for url, allowed in READ.items():
            for role in ROLES:
                with self.subTest(url=url, role=role):
                    got = self.clients[role].get(url).status_code
                    self.assertEqual(got, 200 if role in allowed else 403, f"{role} GET {url} -> {got}")

    def test_write_matrix_matches_the_spec(self):
        """Allowed roles reach validation (400 on an empty body); everyone else is stopped with 403."""
        for url, allowed in WRITE.items():
            for role in ROLES:
                with self.subTest(url=url, role=role):
                    got = self.clients[role].post(url, {}, format="json").status_code
                    self.assertEqual(got, 400 if role in allowed else 403, f"{role} POST {url} -> {got}")

    def test_anonymous_users_are_rejected_everywhere(self):
        anon = APIClient()
        for url in READ:
            with self.subTest(url=url):
                self.assertIn(anon.get(url).status_code, (401, 403))
        for url in WRITE:
            with self.subTest(url=url):
                self.assertIn(anon.post(url, {}, format="json").status_code, (401, 403))

    def test_health_endpoint_is_public(self):
        self.assertEqual(APIClient().get("/api/v1/health/").status_code, 200)

class AuthSecurityTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.alice = make_user("alice", "sales", [self.a])

    def login(self, username="alice", password="Passw0rd!x1"):
        return APIClient().post("/api/v1/auth/login/", {"username": username, "password": password}, format="json")

    def bearer(self, token):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return c

    def test_passwords_are_stored_hashed(self):
        self.assertNotEqual(self.alice.password, "Passw0rd!x1")
        self.assertTrue(self.alice.check_password("Passw0rd!x1"))

    def test_logout_blacklists_the_refresh_token(self):
        tokens = self.login().data["data"]
        out = self.bearer(tokens["access"]).post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(out.status_code, 200)
        again = APIClient().post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_deactivated_user_loses_access_immediately(self):
        token = self.login().data["data"]["access"]
        self.assertEqual(self.bearer(token).get("/api/v1/auth/me/").status_code, 200)
        User.objects.filter(pk=self.alice.pk).update(is_active=False)
        self.assertEqual(self.bearer(token).get("/api/v1/auth/me/").status_code, 401)
        self.assertEqual(self.login().status_code, 401)

    def test_garbage_token_is_rejected(self):
        self.assertEqual(self.bearer("not-a-real-token").get("/api/v1/auth/me/").status_code, 401)

    def test_weak_password_is_rejected(self):
        admin = api_client(make_user("root", "super_admin", []))
        res = admin.post("/api/v1/users/", {"username": "weak", "email": "w@x.com", "password": "123",
                         "role_codes": ["sales"], "branch_ids": [str(self.a.id)]}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.data["errors"])

    def test_login_is_rate_limited(self):
        cache.clear()
        with mock.patch.object(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"}):
            c = APIClient()
            codes = [c.post("/api/v1/auth/login/", {"username": "nobody", "password": "x"},
                            format="json").status_code for _ in range(5)]
        cache.clear()
        self.assertEqual(codes, [401, 401, 401, 429, 429])

    def test_unknown_urls_return_json_not_html(self):
        res = self.client.get("/api/v1/does-not-exist/")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.json()["success"])