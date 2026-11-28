import datetime
from django.test import TestCase
from rest_framework.test import APIClient
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.hr.models import Employee
from apps.organizations.models import Organization
from .models import User


class UserLookupTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.seller = make_user("seller", "sales", [self.a])
        make_user("colleague", "sales", [self.a])
        make_user("faraway", "sales", [self.b])
        make_user("pm", "project_manager", [self.a])
        gone = make_user("gone", "sales", [self.a])
        gone.is_active = False
        gone.save()
        self.c = api_client(self.seller)

    def names(self, client, **params):
        res = client.get("/api/v1/lookups/users/", params)
        self.assertEqual(res.status_code, 200, res.data)
        return {u["username"] for u in res.data["data"]}

    def test_only_active_users_of_my_branches(self):
        self.assertEqual(self.names(self.c, role="sales"), {"seller", "colleague"})
        self.assertEqual(self.names(self.c, role="project_manager"), {"pm"})

    def test_super_admin_sees_every_branch(self):
        admin = api_client(make_user("root", "super_admin", []))
        self.assertEqual(self.names(admin, role="sales"), {"seller", "colleague", "faraway"})
        self.assertEqual(self.names(admin, role="sales", branch=str(self.b.id)), {"faraway"})

    def test_search_narrows_results(self):
        self.assertEqual(self.names(self.c, role="sales", search="coll"), {"colleague"})

    def test_only_whitelisted_roles_can_be_looked_up(self):
        self.assertEqual(self.c.get("/api/v1/lookups/users/", {"role": "finance"}).status_code, 400)
        self.assertEqual(self.c.get("/api/v1/lookups/users/").status_code, 400)
        admin = api_client(make_user("root", "super_admin", []))
        self.assertEqual(admin.get("/api/v1/lookups/users/", {"role": "sales", "branch": "nope"}).status_code, 400)

    def test_employees_and_anonymous_are_blocked(self):
        emp = api_client(make_user("emp", "employee", [self.a]))
        self.assertEqual(emp.get("/api/v1/lookups/users/", {"role": "sales"}).status_code, 403)
        self.assertIn(APIClient().get("/api/v1/lookups/users/", {"role": "sales"}).status_code, (401, 403))

    def test_hr_can_find_users_without_an_employee_profile(self):
        colleague = User.objects.get(username="colleague")
        Employee.objects.create(employee_number="E1", first_name="Co", last_name="Worker", email="co@x.com",
                                branch=self.a, hire_date=datetime.date.today(), user=colleague)
        hr = api_client(make_user("hr1", "hr", [self.a]))
        # linked (colleague), inactive (gone) and other-branch (faraway) users are excluded
        self.assertEqual(self.names(hr, unlinked="1"), {"seller", "pm", "hr1"})

    def test_unlinked_lookup_is_for_hr_and_admin_only(self):
        self.assertEqual(self.c.get("/api/v1/lookups/users/", {"unlinked": "1"}).status_code, 403)
        admin = api_client(make_user("root", "super_admin", []))
        self.assertEqual(admin.get("/api/v1/lookups/users/", {"unlinked": "1"}).status_code, 200)