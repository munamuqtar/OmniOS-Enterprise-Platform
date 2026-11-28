import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Quote, QuoteItem, QuoteApproval
from apps.notifications import events  

TWO = Decimal("0.01")
EDITABLE = {"draft", "rejected"}

def money(x):
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)

def recalc(quote):
    """All totals are calculated server-side only."""
    items = list(quote.items.all())
    for it in items:
        it.line_total = money(it.quantity * it.unit_price)
        it.save(update_fields=["line_total"])
    subtotal = money(sum((i.line_total for i in items), Decimal("0")))
    if quote.discount > subtotal:
        raise ValidationError({"discount": ["Discount cannot exceed the subtotal."]})
    taxable = subtotal - quote.discount
    quote.subtotal = subtotal
    quote.tax = money(taxable * quote.tax_rate / Decimal("100"))
    quote.total = money(taxable + quote.tax)
    quote.save(update_fields=["subtotal", "tax", "total", "updated_at"])

def next_quote_number():
    year = datetime.date.today().year
    last = Quote.objects.filter(quote_number__startswith=f"QT-{year}-").order_by("-quote_number").first()
    n = int(last.quote_number.split("-")[-1]) + 1 if last else 1
    return f"QT-{year}-{n:05d}"

@transaction.atomic
def create_quote(user, items, **fields):
    quote = Quote(created_by=user, quote_number=next_quote_number(), **fields)
    quote.save()
    for it in items:
        QuoteItem.objects.create(quote=quote, **it)
    recalc(quote)
    return quote

@transaction.atomic
def update_quote(quote, items, **fields):
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status not in EDITABLE:
        raise ValidationError({"status": [f"A {quote.status} quote cannot be edited."]})
    for k, v in fields.items():
        setattr(quote, k, v)
    quote.save()
    if items is not None:
        quote.items.all().delete()
        for it in items:
            QuoteItem.objects.create(quote=quote, **it)
    recalc(quote)
    return quote

@transaction.atomic
def submit(quote, user):
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status not in EDITABLE:
        raise ValidationError({"status": [f"Only draft or rejected quotes can be submitted (current: {quote.status})."]})
    if not quote.items.exists():
        raise ValidationError({"items": ["Add at least one item before submitting."]})
    if quote.valid_until < datetime.date.today():
        raise ValidationError({"valid_until": ["Valid-until date is in the past."]})
    if quote.total <= 0:
        raise ValidationError({"total": ["Quote total must be greater than zero."]})
    if quote.status == "rejected":
        quote.revision += 1          # corrected resubmission = new revision, new approval
    QuoteApproval.objects.create(quote=quote, revision=quote.revision, decision="submitted", actor=user)
    quote.status = "pending_approval"
    quote.save()
    events.quote_submitted(quote, user)
    return quote

def _check_approver(quote, user):
    if quote.created_by_id == user.id:
        raise PermissionDenied("You cannot approve or reject your own quotation.")
    if user.is_super_admin:
        return
    is_branch_manager = quote.branch.manager_id == user.id
    if not ("sales" in user.role_codes and is_branch_manager):
        raise PermissionDenied("Only an authorized manager can approve quotations.")

@transaction.atomic
def approve(quote, user):
    quote = Quote.objects.select_for_update().select_related("branch").get(pk=quote.pk)
    if quote.status != "pending_approval":
        raise ValidationError({"status": ["Only quotes pending approval can be approved."]})
    _check_approver(quote, user)
    QuoteApproval.objects.create(quote=quote, revision=quote.revision, decision="approved", actor=user)
    quote.status = "approved"
    quote.save()
    events.quote_decided(quote, user, True)
    return quote

@transaction.atomic
def reject(quote, user, reason):
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required to reject a quotation."]})
    quote = Quote.objects.select_for_update().select_related("branch").get(pk=quote.pk)
    if quote.status != "pending_approval":
        raise ValidationError({"status": ["Only quotes pending approval can be rejected."]})
    _check_approver(quote, user)
    QuoteApproval.objects.create(quote=quote, revision=quote.revision, decision="rejected",
                                 actor=user, reason=reason)
    quote.status = "rejected"
    quote.save()
    events.quote_decided(quote, user, False, reason)
    return quote

@transaction.atomic
def revise(quote, user):
    """Approved quote revision requires new approval: reopen as draft, revision + 1."""
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    if quote.status != "approved":
        raise ValidationError({"status": ["Only approved quotes need to be reopened for revision."]})
    quote.status = "draft"
    quote.revision += 1
    quote.save()
    return quote

@transaction.atomic
def convert_to_project(quote, user, manager, name, start_date, end_date, description=""):
    from apps.projects.models import Project
    from apps.projects import services as project_services

    quote = Quote.objects.select_for_update().get(pk=quote.pk)     # no select_related: nullable FKs
    if quote.status != "approved":
        raise ValidationError({"status": ["Only approved quotes can be converted to a project."]})
    if quote.converted_project_id:
        raise ValidationError({"status": ["This quote has already been converted to a project."]})
    client = quote.client or (quote.lead.converted_client if quote.lead_id else None)
    if not client:
        raise ValidationError({"client": ["Convert the lead to a client first, then convert the quote."]})
    project_services.check_manager(manager, quote.branch)

    project = Project.objects.create(
        project_code=project_services.next_project_code(), name=name, client=client,
        branch=quote.branch, manager=manager, description=description,
        start_date=start_date, end_date=end_date, budget=quote.total, created_by=user)
    quote.converted_project = project
    if not quote.client_id:
        quote.client = client
    quote.save()
    events.project_manager_assigned(project, user) 
    return quote, project