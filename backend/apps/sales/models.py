from decimal import Decimal
from django.db import models
from apps.organizations.models import TimeStampedModel
from apps.branches.models import Branch

class Quote(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    quote_number = models.CharField(max_length=30, unique=True, editable=False)
    client = models.ForeignKey("crm.Client", null=True, blank=True, on_delete=models.PROTECT, related_name="quotes")
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.PROTECT, related_name="quotes")
    opportunity = models.ForeignKey("crm.Opportunity", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="quotes")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="quotes")
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))   # amount
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))    # percent
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    valid_until = models.DateField()
    payment_terms = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="quotes_created")
    converted_project = models.ForeignKey("projects.Project", null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name="source_quotes")

    class Meta:
        indexes = [models.Index(fields=["branch", "status"])]

    def __str__(self):
        return self.quote_number

class QuoteItem(TimeStampedModel):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

class QuoteApproval(TimeStampedModel):
    class Decision(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="approvals")
    revision = models.PositiveIntegerField()
    decision = models.CharField(max_length=10, choices=Decision.choices)
    actor = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)