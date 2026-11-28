from datetime import date
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.organizations.models import Organization
from .models import Employee


class EmployeeAccessTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.emp_a = Employee.objects.create(employee_number="E1", first_name="Ann", last_name="A",
                                             email="ann@x.com", branch=self.a, hire_date=date(2024, 1, 1))
        Employee.objects.create(employee_number="E2", first_name="Bob", last_name="B",
                                email="bob@x.com", branch=self.b, hire_date=date(2024, 1, 1))
        self.hr_a = make_user("hr_a", "hr", [self.a])

    def test_hr_sees_only_own_branch(self):
        res = api_client(self.hr_a).get("/api/v1/employees/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([e["employee_number"] for e in res.data["results"]], ["E1"])

    def test_hr_cannot_create_in_other_branch(self):
        res = api_client(self.hr_a).post("/api/v1/employees/", {
            "first_name": "X", "last_name": "Y", "email": "x@x.com",
            "branch": str(self.b.id), "hire_date": "2024-05-01"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_sales_can_read_but_not_write(self):
        sales = make_user("sales_a", "sales", [self.a])
        c = api_client(sales)
        self.assertEqual(c.get("/api/v1/employees/").status_code, 200)
        res = c.post("/api/v1/employees/", {}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_employee_role_sees_only_own_record(self):
        user = make_user("ann", "employee", [self.a])
        self.emp_a.user = user
        self.emp_a.save()
        res = api_client(user).get("/api/v1/employees/")
        self.assertEqual(len(res.data["results"]), 1)


class DepartmentDefaultsTests(TestCase):
    def setUp(self):
        self.hr = api_client(make_user("hr1", "hr", []))

    def test_department_uses_the_company_when_organization_is_omitted(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        res = self.hr.post("/api/v1/departments/", {"name": "Engineering", "code": "ENG"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(str(res.data["organization"]), str(org.id))

    def test_department_needs_a_company_first(self):
        res = self.hr.post("/api/v1/departments/", {"name": "Engineering", "code": "ENG"}, format="json")
        self.assertEqual(res.status_code, 400)