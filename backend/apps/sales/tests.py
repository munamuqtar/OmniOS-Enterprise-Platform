import datetime
from decimal import Decimal
from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.crm.models import Client
from apps.organizations.models import Organization
from .models import Quote

FUTURE = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

class QuoteTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.b = Branch.objects.create(organization=org, name="B", branch_code="B")
        self.seller = make_user("seller", "sales", [self.a])
        self.manager = make_user("mgr", "sales", [self.a])
        self.a.manager = self.manager
        self.a.save()
        self.client_rec = Client.objects.create(name="Cli", email="c@x.com", branch=self.a)
        self.s = api_client(self.seller)
        self.m = api_client(self.manager)

    def _payload(self, **over):
        p = {"client": str(self.client_rec.id), "branch": str(self.a.id), "currency": "USD",
             "valid_until": FUTURE, "discount": "10.00", "tax_rate": "10.00",
             "items": [{"description": "Dev", "quantity": "2", "unit_price": "100.00"},
                       {"description": "Support", "quantity": "1", "unit_price": "50.00"}]}
        p.update(over)
        return p

    def _create(self, **over):
        return self.s.post("/api/v1/quotes/", self._payload(**over), format="json")

    def test_server_side_totals(self):
        res = self._create()
        self.assertEqual(res.status_code, 201)
        d = res.data["data"]
        # subtotal 250, minus 10 discount = 240, tax 10% = 24, total 264
        self.assertEqual(Decimal(d["subtotal"]), Decimal("250.00"))
        self.assertEqual(Decimal(d["tax"]), Decimal("24.00"))
        self.assertEqual(Decimal(d["total"]), Decimal("264.00"))
        self.assertTrue(d["quote_number"].startswith("QT-"))

    def test_client_cannot_inject_total(self):
        res = self._create(total="1.00", subtotal="1.00")
        self.assertEqual(Decimal(res.data["data"]["total"]), Decimal("264.00"))


    def test_discount_cannot_exceed_subtotal(self):
        self.assertEqual(self._create(discount="999.00").status_code, 400)

    def test_requires_items_and_quantity_positive(self):
        self.assertEqual(self._create(items=[]).status_code, 400)
        bad = [{"description": "x", "quantity": "0", "unit_price": "5"}]
        self.assertEqual(self._create(items=bad).status_code, 400)

    def test_cannot_create_in_other_branch(self):
        self.assertEqual(self._create(branch=str(self.b.id)).status_code, 400)

    def test_sales_cannot_approve_own_quote(self):
        qid = self._create().data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        res = self.s.post(f"/api/v1/quotes/{qid}/approve/")
        self.assertEqual(res.status_code, 403)

    def test_non_manager_sales_cannot_approve(self):
        other = api_client(make_user("other", "sales", [self.a]))
        qid = self._create().data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        self.assertEqual(other.post(f"/api/v1/quotes/{qid}/approve/").status_code, 403)

    def test_manager_approves_and_history_recorded(self):
        qid = self._create().data["data"]["id"]
        self.assertEqual(self.s.post(f"/api/v1/quotes/{qid}/submit/").status_code, 200)
        res = self.m.post(f"/api/v1/quotes/{qid}/approve/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["status"], "approved")
        hist = self.m.get(f"/api/v1/quotes/{qid}/approvals/")
        self.assertEqual(len(hist.data["data"]), 2)   # submitted + approved

    def test_reject_needs_reason_then_fix_and_resubmit(self):
        qid = self._create().data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        self.assertEqual(self.m.post(f"/api/v1/quotes/{qid}/reject/", {}, format="json").status_code, 400)
        self.assertEqual(self.m.post(f"/api/v1/quotes/{qid}/reject/", {"reason": "Too high"},
                                     format="json").status_code, 200)
        self.assertEqual(self.s.put(f"/api/v1/quotes/{qid}/", self._payload(discount="20.00"),
                                    format="json").status_code, 200)
        self.assertEqual(self.s.post(f"/api/v1/quotes/{qid}/submit/").status_code, 200)
        self.assertEqual(Quote.objects.get(pk=qid).revision, 2)

    def test_cannot_edit_pending_or_approved_quote(self):
        qid = self._create().data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        self.assertEqual(self.s.put(f"/api/v1/quotes/{qid}/", self._payload(), format="json").status_code, 400)

    def test_approved_revision_needs_new_approval(self):
        qid = self._create().data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        self.m.post(f"/api/v1/quotes/{qid}/approve/")
        self.assertEqual(self.s.post(f"/api/v1/quotes/{qid}/revise/").status_code, 200)
        q = Quote.objects.get(pk=qid)
        self.assertEqual((q.status, q.revision), ("draft", 2))

    def test_finance_read_only_hr_blocked(self):
        self._create()
        fin = api_client(make_user("fin", "finance", [self.a]))
        self.assertEqual(fin.get("/api/v1/quotes/").status_code, 200)
        self.assertEqual(fin.post("/api/v1/quotes/", self._payload(), format="json").status_code, 403)
        hr = api_client(make_user("hr1", "hr", [self.a]))
        self.assertEqual(hr.get("/api/v1/quotes/").status_code, 403)

    def _approved_quote(self, **over):
        qid = self._create(**over).data["data"]["id"]
        self.s.post(f"/api/v1/quotes/{qid}/submit/")
        self.m.post(f"/api/v1/quotes/{qid}/approve/")
        return qid

    def _convert_body(self):
        pm = make_user("pm1", "project_manager", [self.a])
        end = (datetime.date.today() + datetime.timedelta(days=90)).isoformat()
        return {"name": "Website build", "manager": str(pm.id),
                "start_date": datetime.date.today().isoformat(), "end_date": end}

    def test_convert_approved_quote_creates_project(self):
        qid = self._approved_quote()
        res = self.s.post(f"/api/v1/quotes/{qid}/convert/", self._convert_body(), format="json")
        self.assertEqual(res.status_code, 201)
        project = res.data["data"]["project"]
        self.assertEqual(project["status"], "draft")
        self.assertEqual(Decimal(project["budget"]), Decimal("264.00"))
        self.assertIsNotNone(Quote.objects.get(pk=qid).converted_project)

    def test_cannot_convert_unapproved_quote(self):
        qid = self._create().data["data"]["id"]
        res = self.s.post(f"/api/v1/quotes/{qid}/convert/", self._convert_body(), format="json")
        self.assertEqual(res.status_code, 400)

    def test_cannot_convert_twice(self):
        qid = self._approved_quote()
        body = self._convert_body()
        self.s.post(f"/api/v1/quotes/{qid}/convert/", body, format="json")
        self.assertEqual(self.s.post(f"/api/v1/quotes/{qid}/convert/", body, format="json").status_code, 400)

    def test_lead_only_quote_needs_client_first(self):
        from apps.crm.models import Lead
        lead = Lead.objects.create(name="L", email="l@x.com", branch=self.a)
        qid = self._approved_quote(client=None, lead=str(lead.id))
        res = self.s.post(f"/api/v1/quotes/{qid}/convert/", self._convert_body(), format="json")
        self.assertEqual(res.status_code, 400)