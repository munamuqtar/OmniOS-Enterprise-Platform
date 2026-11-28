from django.db import models
from apps.organizations.models import TimeStampedModel
from apps.branches.models import Branch

class Client(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="clients")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["email"])]

    def __str__(self):
        return self.name

class Lead(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        PENDING = "pending", "Pending"
        QUALIFIED = "qualified", "Qualified"
        UNQUALIFIED = "unqualified", "Unqualified"
        CONVERTED = "converted", "Converted"

    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=100, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="leads")
    owner = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="leads")
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)

    # qualification info
    business_requirement = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    customer_interest = models.CharField(max_length=200, blank=True)
    expected_timeline = models.CharField(max_length=200, blank=True)
    unqualified_reason = models.TextField(blank=True)

    converted_client = models.OneToOneField(Client, null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name="source_lead")
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["owner"])]

    def __str__(self):
        return self.name

class LeadStatusHistory(TimeStampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=12)
    to_status = models.CharField(max_length=12)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)

class LeadActivity(TimeStampedModel):
    class Kind(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        NOTE = "note", "Note"
        FOLLOW_UP = "follow_up", "Follow Up"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    description = models.TextField()
    activity_date = models.DateTimeField()
    next_follow_up = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

class Opportunity(TimeStampedModel):
    class Stage(models.TextChoices):
        PROSPECTING = "prospecting", "Prospecting"
        QUALIFICATION = "qualification", "Qualification"
        PROPOSAL = "proposal", "Proposal"
        NEGOTIATION = "negotiation", "Negotiation"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    name = models.CharField(max_length=200)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.PROTECT, related_name="opportunities")
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.PROTECT, related_name="opportunities")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="opportunities")
    owner = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="opportunities")
    value = models.DecimalField(max_digits=14, decimal_places=2)
    probability = models.PositiveSmallIntegerField(default=10)   # 0-100
    expected_close_date = models.DateField()
    stage = models.CharField(max_length=14, choices=Stage.choices, default=Stage.PROSPECTING)
    lost_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["branch", "stage"])]

    def __str__(self):
        return self.name

class OpportunityStageHistory(TimeStampedModel):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="history")
    from_stage = models.CharField(max_length=14)
    to_stage = models.CharField(max_length=14)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField(blank=True)