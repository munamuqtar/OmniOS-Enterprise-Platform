import datetime
from decimal import Decimal
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.access_control.models import Role
from apps.accounts.models import User, UserRole, UserBranch
from apps.branches.models import Branch
from apps.crm import services as crm
from apps.crm.models import Lead, Opportunity
from apps.finance import services as fin
from apps.hr.models import Department, Employee
from apps.organizations.models import Organization
from apps.projects import services as proj
from apps.projects.models import Project, Task
from apps.recruitment import services as rec
from apps.recruitment.models import Candidate, JobVacancy, RecruitmentApplication
from apps.sales import services as sales
from apps.timesheets import services as tsv
from apps.timesheets.models import Timesheet

TODAY = datetime.date.today()

def d(n):
    return TODAY + datetime.timedelta(days=n)

class Command(BaseCommand):
    help = "Create fictional demo data and one login per role (development and demo servers only)"

    def add_arguments(self, parser):
        parser.add_argument("--password", default="OmniOS#Demo2026")
        parser.add_argument("--force", action="store_true", help="allow running when DEBUG is False")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to create demo accounts while DEBUG is False. Use --force on a demo server only.")
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Demo data already exists. Use a fresh database to seed again.")
            return
        call_command("seed_roles")
        pw = opts["password"]

        org = Organization.objects.create(name="Horizon Group Ltd", company_code="HZN",
                                          email="info@horizon.example", phone="+000 111 2222",
                                          address="1 Example Street, Sample City")
        hq = Branch.objects.create(organization=org, name="Head Office", branch_code="HQ", email="hq@horizon.example")
        east = Branch.objects.create(organization=org, name="East Branch", branch_code="EAST", email="east@horizon.example")

        def mk(username, role, branches, first, last):
            u = User.objects.create_user(username=username, email=f"{username}@omnios.test", password=pw,
                                         first_name=first, last_name=last)
            UserRole.objects.create(user=u, role=Role.objects.get(code=role))
            for b in branches:
                UserBranch.objects.create(user=u, branch=b)
            return u

        admin = mk("admin", "super_admin", [], "Amina", "Admin")
        hr = mk("hr", "hr", [hq], "Hodan", "Hassan")
        seller = mk("sales", "sales", [hq], "Samir", "Sales")
        manager = mk("sales_manager", "sales", [hq], "Mariam", "Manager")
        finance = mk("finance", "finance", [hq], "Farah", "Finance")
        pm = mk("pm", "project_manager", [hq], "Pavel", "Project")
        employee = mk("employee", "employee", [hq], "Eman", "Employee")
        sales_east = mk("sales_east", "sales", [east], "Ebo", "East")
        hq.manager = manager
        hq.save()

        # ---- HR ----
        eng = Department.objects.create(organization=org, name="Engineering", code="ENG")
        hrd = Department.objects.create(organization=org, name="Human Resources", code="HR")
        Department.objects.create(organization=org, name="Sales", code="SAL")
        Department.objects.create(organization=org, name="Finance", code="FIN")
        staff = [(hr, hrd, "HR Officer"), (seller, None, "Account Executive"), (manager, None, "Sales Manager"),
                 (finance, None, "Accountant"), (pm, eng, "Project Manager"), (employee, eng, "Developer")]
        emps = {}
        for i, (u, dept, position) in enumerate(staff, start=1):
            emps[u.username] = Employee.objects.create(
                employee_number=f"EMP-{i:03d}", first_name=u.first_name, last_name=u.last_name, email=u.email,
                department=dept, branch=hq, position=position, hire_date=d(-400 + i * 10), user=u)
        dev2 = Employee.objects.create(employee_number="EMP-007", first_name="Dev", last_name="Two",
                                       email="dev2@omnios.test", department=eng, branch=hq, position="Developer", hire_date=d(-200))
        Employee.objects.create(employee_number="EMP-008", first_name="Eli", last_name="East",
                                email="eli@omnios.test", branch=east, position="Clerk", hire_date=d(-100))

        vacancy = JobVacancy.objects.create(title="Backend Developer", department=eng, branch=hq, status="open",
                                            description="Django and PostgreSQL", openings=2, created_by=hr)
        stages = [("Ayaan", "Ali", ["screening", "interview"]), ("Bilal", "Bare", ["screening"]), ("Cadey", "Cumar", [])]
        for first, last, path in stages:
            cand = Candidate.objects.create(first_name=first, last_name=last, email=f"{first.lower()}@cand.test", branch=hq, source="Website")
            app = RecruitmentApplication.objects.create(candidate=cand, vacancy=vacancy, branch=hq)
            for stage in path:
                extra = {"interview_at": timezone.now() + datetime.timedelta(days=3)} if stage == "interview" else {}
                rec.change_stage(app, stage, hr, **extra)

        # ---- CRM ----
        def lead(name, company, owner=seller, branch=hq):
            return Lead.objects.create(name=name, company_name=company, email=f"{name.lower().replace(' ', '.')}@lead.test",
                                       phone="+000 555 0100", source="Website", branch=branch, owner=owner, created_by=owner)
        lead("Nur Omar", "Nur Trading")
        crm.change_status(lead("Bashir Jama", "Bashir Logistics"), "contacted", seller)
        crm.mark_unqualified(lead("Oday Said", "Oday Imports"), seller, "Budget too low")
        lead("Ebo Guled", "East Traders", owner=sales_east, branch=east)
        qual = {"business_requirement": "Business system", "budget": Decimal("12000"),
                "customer_interest": "high", "expected_timeline": "2 months"}
        clients = []
        for name, company in (("Sahan Yusuf", "Sahan Foods"), ("Dalmar Nur", "Dalmar Energy")):
            ld = lead(name, company)
            crm.qualify(ld, seller, qual)
            clients.append(crm.convert_to_client(ld, seller, address="12 Market Road")[1])
        client_a, client_b = clients
        for name, client, stage, value in (("Foods ERP", client_a, "proposal", "8000"), ("Energy portal", client_b, "negotiation", "20000"),
                                           ("Pilot", client_a, "won", "1500"), ("Old bid", client_b, "lost", "700")):
            Opportunity.objects.create(name=name, client=client, branch=hq, owner=seller, created_by=seller, value=Decimal(value),
                                       probability={"proposal": 50, "negotiation": 75, "won": 100, "lost": 0}[stage],
                                       expected_close_date=d(30), stage=stage)

        # ---- Quotations (draft, pending approval, approved then converted to a project) ----
        def quote(client, items):
            return sales.create_quote(seller, [{"description": t, "quantity": Decimal(q), "unit_price": Decimal(p)} for t, q, p in items],
                                      client=client, branch=hq, valid_until=d(30), currency="USD", tax_rate=Decimal("5"))
        quote(client_a, [("Discovery workshop", "2", "800")])
        pending = quote(client_b, [("Portal build", "1", "9000")])
        sales.submit(pending, seller)
        approved = quote(client_a, [("ERP rollout", "100", "50"), ("Training", "10", "120")])
        sales.submit(approved, seller)
        sales.approve(approved, manager)
        _, project = sales.convert_to_project(approved, seller, pm, "ERP Rollout", d(-30), d(60))

        # ---- Projects, tasks, timesheets ----
        for u in (employee,):
            proj.add_member(project, emps[u.username], "Developer")
        proj.add_member(project, dev2, "Developer")
        project = proj.change_project_status(project, "planned", pm)
        project = proj.change_project_status(project, "active", pm)
        Project.objects.create(project_code=proj.next_project_code(), name="Mobile App", client=client_b, branch=hq,
                               manager=pm, start_date=d(10), end_date=d(120), status="planned", created_by=pm)
        mine = emps["employee"]
        tasks = [Task.objects.create(project=project, title=t, assigned_employee=a, start_date=d(-25), due_date=due,
                                     priority=pri, created_by=pm)
                 for t, a, due, pri in (("Requirements workshop", mine, d(-5), "high"), ("Data migration", mine, d(20), "medium"),
                                        ("Configuration", dev2, d(10), "medium"), ("User training", dev2, d(40), "low"))]
        proj.change_task_status(tasks[1], "in_progress", employee)
        for status in ("in_progress", "review", "completed"):
            proj.change_task_status(tasks[2], status, pm)
        for status in ("in_progress", "review"):
            proj.change_task_status(tasks[3], status, dev2.user or pm)

        sheets = [Timesheet.objects.create(employee=mine, project=project, task=tasks[2 if i < 4 else 1],
                                           work_date=d(-i), hours=Decimal("8"), description=f"Work day {i}")
                  for i in range(1, 8)]
        for ts in sheets[:5]:
            tsv.submit(ts, employee)
            tsv.approve(ts, pm)
        tsv.submit(sheets[5], employee)           # waiting for review
        #                                           sheets[6] stays a draft

        # ---- Finance ----
        inv1 = fin.create_invoice(finance, [sheets[0].id, sheets[1].id, sheets[2].id], Decimal("60.00"), project=project,
                                  due_date=d(20), currency="USD", tax_rate=Decimal("5"), notes="Phase 1 delivery")
        fin.issue(inv1, finance)
        paid = fin.record_payment(finance, inv1, Decimal("400"), "bank_transfer", "BT-1001", d(-1))
        fin.reconcile_payment(paid, finance)
        fin.record_payment(finance, inv1, Decimal("100"), "mobile_money", "MM-77", d(0), initial_status="pending")
        inv2 = fin.create_invoice(finance, [sheets[3].id, sheets[4].id], Decimal("60.00"), project=project,
                                  issue_date=d(-45), due_date=d(-15), currency="USD", notes="Overdue example")
        fin.issue(inv2, finance)
        fin.mark_overdue()

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"\nPassword for every account: {pw}\n")
        for u in (admin, hr, seller, manager, finance, pm, employee, sales_east):
            roles = ", ".join(sorted(u.role_codes))
            self.stdout.write(f"  {u.username:<14} {roles}")