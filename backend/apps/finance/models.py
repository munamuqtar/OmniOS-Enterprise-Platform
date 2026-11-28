import datetime
from decimal import Decimal
from django.db import models
from apps.organizations.models import TimeStampedModel

ZERO = Decimal("0")

class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="invoices")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="invoices")
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="invoices")
    issue_date = models.DateField(default=datetime.date.today)
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)   # amount
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)    # percent
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)
    cancel_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["due_date"])]

    def __str__(self):
        return self.invoice_number

class InvoiceItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)      # billed hours
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)    # hourly rate
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)

class InvoiceStatusHistory(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=14, blank=True)
    to_status = models.CharField(max_length=14)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        RECONCILED = "reconciled", "Reconciled"
        REJECTED = "rejected", "Rejected"

    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"
        CHEQUE = "cheque", "Cheque"

    payment_number = models.CharField(max_length=30, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=14, choices=Method.choices)
    reference = models.CharField(max_length=100)
    payment_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED)
    notes = models.TextField(blank=True)
    reject_reason = models.TextField(blank=True)
    recorded_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reconciled_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["invoice", "status"])]
        constraints = [models.UniqueConstraint(
            fields=["invoice", "reference"], condition=~models.Q(status="rejected"),
            name="uniq_active_payment_reference")]