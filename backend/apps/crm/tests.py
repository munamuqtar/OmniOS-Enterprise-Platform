from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.organizations.models import Organization
from .models import Lead, Client
from .models import Opportunity
from apps.crm.models import Client

QUAL = {"business_requirement": "ERP", "budget": "5000.00",
        "customer_interest": "high", "expected_timeline": "3 months"}

class LeadWorkflowTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.sales = make_user("sales_a", "sales", [self.a])
        self.c = api_client(self.sales)

    def _lead(self, email="l@x.com", branch=None):
        res = self.c.post("/api/v1/leads/", {"name": "Lee", "company_name": "LeeCo",
                          "email": email, "branch": str(branch or self.a.id)}, format="json")
        return res

    def test_create_lead_defaults(self):
        res = self._lead()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "new")
        self.assertEqual(Lead.objects.get().owner, self.sales)

    def test_cannot_create_in_other_branch(self):
        self.assertEqual(self._lead(branch=self.b.id).status_code, 400)

    def test_branch_isolation_on_list(self):
        self._lead()
        Lead.objects.create(name="Other", email="o@x.com", branch=self.b)
        res = self.c.get("/api/v1/leads/")
        self.assertEqual(len(res.data["results"]), 1)

    def test_unqualify_requires_reason(self):
        lid = self._lead().data["id"]
        self.assertEqual(self.c.post(f"/api/v1/leads/{lid}/unqualify/", {}, format="json").status_code, 400)
        res = self.c.post(f"/api/v1/leads/{lid}/unqualify/", {"reason": "No budget"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_qualify_requires_all_fields(self):
        lid = self._lead().data["id"]
        res = self.c.post(f"/api/v1/leads/{lid}/qualify/", {"budget": "10"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cannot_convert_unqualified_lead(self):
        lid = self._lead().data["id"]
        res = self.c.post(f"/api/v1/leads/{lid}/convert/", {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_convert_happy_path_and_history(self):
        lid = self._lead().data["id"]
        self.c.post(f"/api/v1/leads/{lid}/qualify/", QUAL, format="json")
        res = self.c.post(f"/api/v1/leads/{lid}/convert/", {"address": "Mogadishu"}, format="json")
        self.assertEqual(res.status_code, 201)
        lead = Lead.objects.get(pk=lid)
        self.assertEqual(lead.status, "converted")
        self.assertEqual(lead.converted_client.email, "l@x.com")
        self.assertEqual(lead.history.count(), 2)   # qualified, converted

    def test_duplicate_client_blocks_conversion(self):
        Client.objects.create(name="Old", email="L@x.com", branch=self.a)
        lid = self._lead().data["id"]
        self.c.post(f"/api/v1/leads/{lid}/qualify/", QUAL, format="json")
        res = self.c.post(f"/api/v1/leads/{lid}/convert/", {}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Lead.objects.get(pk=lid).status, "qualified")   # rolled back, nothing changed

    def test_cannot_convert_twice(self):
        lid = self._lead().data["id"]
        self.c.post(f"/api/v1/leads/{lid}/qualify/", QUAL, format="json")
        self.c.post(f"/api/v1/leads/{lid}/convert/", {}, format="json")
        self.assertEqual(self.c.post(f"/api/v1/leads/{lid}/convert/", {}, format="json").status_code, 400)

    def test_plain_put_cannot_change_status(self):
        lid = self._lead().data["id"]
        self.c.put(f"/api/v1/leads/{lid}/", {"name": "Lee", "email": "l@x.com",
                   "branch": str(self.a.id), "status": "qualified"}, format="json")
        self.assertEqual(Lead.objects.get(pk=lid).status, "new")

    def test_hr_and_employee_forbidden(self):
        for role in ("hr", "employee"):
            u = make_user(f"{role}_a", role, [self.a])
            self.assertEqual(api_client(u).get("/api/v1/leads/").status_code, 403)

    def test_finance_can_read_clients_not_write(self):
        fin = api_client(make_user("fin_a", "finance", [self.a]))
        self.assertEqual(fin.get("/api/v1/clients/").status_code, 200)
        self.assertEqual(fin.post("/api/v1/clients/", {}, format="json").status_code, 403)



class OpportunityTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.cl = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.c = api_client(make_user("sales_a", "sales", [self.a]))
        res = self.c.post("/api/v1/opportunities/", {
            "name": "Deal", "client": str(self.cl.id), "branch": str(self.a.id),
            "value": "5000", "probability": 10, "expected_close_date": "2027-01-31"}, format="json")
        self.oid = res.data["id"]
        self.url = f"/api/v1/opportunities/{self.oid}/stage/"

    def test_cannot_skip_stage(self):
        self.assertEqual(self.c.post(self.url, {"stage": "negotiation"}, format="json").status_code, 400)

    def test_lost_needs_reason(self):
        self.assertEqual(self.c.post(self.url, {"stage": "lost"}, format="json").status_code, 400)
        self.assertEqual(self.c.post(self.url, {"stage": "lost", "reason": "Budget"}, format="json").status_code, 200)

    def test_closed_cannot_change(self):
        self.c.post(self.url, {"stage": "lost", "reason": "x"}, format="json")
        self.assertEqual(self.c.post(self.url, {"stage": "qualification"}, format="json").status_code, 400)

    def test_won_path(self):
        for st in ("qualification", "proposal", "negotiation", "won"):
            self.assertEqual(self.c.post(self.url, {"stage": st}, format="json").status_code, 200)
        self.assertEqual(Opportunity.objects.get(pk=self.oid).probability, 100)

    def test_needs_lead_or_client(self):
        res = self.c.post("/api/v1/opportunities/", {"name": "X", "branch": str(self.a.id),
                          "value": "1", "expected_close_date": "2027-01-31"}, format="json")
        self.assertEqual(res.status_code, 400)