from django.test import TestCase
from apps.branches.models import Branch
from apps.core.testing import make_user, api_client
from apps.organizations.models import Organization
from .models import JobVacancy, Candidate, RecruitmentApplication


class PipelineTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Acme", company_code="ACME")
        self.a = Branch.objects.create(organization=org, name="A", branch_code="A")
        self.hr = make_user("hr_a", "hr", [self.a])
        v = JobVacancy.objects.create(title="Dev", branch=self.a, status="open")
        c = Candidate.objects.create(first_name="Sam", last_name="S", email="s@x.com", branch=self.a)
        self.app = RecruitmentApplication.objects.create(candidate=c, vacancy=v, branch=self.a)
        self.url = f"/api/v1/recruitment-applications/{self.app.id}/stage/"
        self.client_hr = api_client(self.hr)

    def test_cannot_skip_stages(self):
        res = self.client_hr.post(self.url, {"stage": "hired"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_rejection_requires_reason(self):
        res = self.client_hr.post(self.url, {"stage": "rejected"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_interview_requires_schedule(self):
        self.client_hr.post(self.url, {"stage": "screening"}, format="json")
        res = self.client_hr.post(self.url, {"stage": "interview"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_full_happy_path_and_history(self):
        self.client_hr.post(self.url, {"stage": "screening"}, format="json")
        self.client_hr.post(self.url, {"stage": "interview", "interview_at": "2026-12-01T10:00:00Z"}, format="json")
        self.client_hr.post(self.url, {"stage": "evaluation"}, format="json")
        self.client_hr.post(self.url, {"stage": "offered"}, format="json")
        res = self.client_hr.post(self.url, {"stage": "hired"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.app.history.count(), 5)

    def test_sales_forbidden(self):
        sales = make_user("sales_a", "sales", [self.a])
        res = api_client(sales).get("/api/v1/recruitment-applications/")
        self.assertEqual(res.status_code, 403)

    def test_applications_can_be_filtered_by_candidate(self):
        mine = self.client_hr.get(f"/api/v1/recruitment-applications/?candidate={self.app.candidate_id}")
        self.assertEqual(mine.data["count"], 1)
        idle = Candidate.objects.create(first_name="No", last_name="Apps", email="none@x.com", branch=self.a)
        other = self.client_hr.get(f"/api/v1/recruitment-applications/?candidate={idle.id}")
        self.assertEqual(other.data["count"], 0)