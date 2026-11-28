from django.core.management.base import BaseCommand
from apps.access_control.models import Role

ROLES = [
    ("super_admin", "Super Admin", "Full system access"),
    ("hr", "HR", "Employees and recruitment"),
    ("sales", "Sales", "Leads, opportunities, quotations"),
    ("finance", "Finance", "Invoices and payments"),
    ("project_manager", "Project Manager", "Projects, tasks, timesheet review"),
    ("employee", "Employee", "Own work and profile"),
]

class Command(BaseCommand):
    help = "Seed the 6 official roles"

    def handle(self, *args, **opts):
        for code, name, desc in ROLES:
            Role.objects.update_or_create(code=code, defaults={"name": name, "description": desc})
        self.stdout.write(self.style.SUCCESS("Roles seeded"))