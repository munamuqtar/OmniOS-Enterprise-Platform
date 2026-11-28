from django.test import TestCase
from apps.core.testing import make_user, api_client
from apps.organizations.models import Organization

class BranchDefaultsTests(TestCase):
    def setUp(self):
        self.admin = api_client(make_user("root", "super_admin", []))

    def test_branch_uses_the_company_when_organization_is_omitted(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        res = self.admin.post("/api/v1/branches/", {"name": "East", "branch_code": "EAST"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(str(res.data["organization"]), str(org.id))

    def test_branch_needs_a_company_first(self):
        res = self.admin.post("/api/v1/branches/", {"name": "East", "branch_code": "EAST"}, format="json")
        self.assertEqual(res.status_code, 400)