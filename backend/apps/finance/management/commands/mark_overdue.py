from django.core.management.base import BaseCommand
from apps.finance.services import mark_overdue

class Command(BaseCommand):
    help = "Mark issued/partially paid invoices past their due date as overdue"

    def handle(self, *args, **opts):
        mark_overdue()
        self.stdout.write(self.style.SUCCESS("Overdue invoices updated"))