import datetime
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.core.money import money
from apps.timesheets.models import Timesheet
from .models import Invoice, InvoiceItem, InvoiceStatusHistory, Payment
from apps.notifications import events      

ZERO = Decimal("0")
PAYABLE = ("issued", "partially_paid", "overdue")
COUNTED = ("confirmed", "reconciled")          # payment statuses that reduce the balance

def _next_number(model, field, prefix):
    stem = f"{prefix}-{datetime.date.today().year}-"
    last = model.objects.filter(**{f"{field}__startswith": stem}).order_by(f"-{field}").first()
    n = int(getattr(last, field).split("-")[-1]) + 1 if last else 1
    return f"{stem}{n:05d}"

def _set_status(inv, new, user=None, reason=""):
    """Every invoice status change is tracked."""
    if inv.status != new:
        InvoiceStatusHistory.objects.create(invoice=inv, from_status=inv.status, to_status=new,
                                            changed_by=user, reason=reason)
        inv.status = new

# ---------- invoice building ----------

def build_items(inv, timesheet_ids, hourly_rate):
    ids = set(timesheet_ids)
    sheets = list(Timesheet.objects.select_for_update().filter(id__in=ids).select_related("task"))
    if len(sheets) != len(ids):
        raise ValidationError({"timesheet_ids": ["One or more timesheets do not exist."]})
    for s in sheets:
        if s.project_id != inv.project_id:
            raise ValidationError({"timesheet_ids": ["All timesheets must belong to the invoice's project."]})
        if s.status != "approved":
            raise ValidationError({"timesheet_ids": ["Only approved timesheets can be invoiced."]})
        if s.invoice_item_id:
            raise ValidationError({"timesheet_ids": ["A timesheet is already billed on another invoice."]})
    groups = defaultdict(list)
    for s in sheets:
        groups[s.task_id].append(s)
    for group in groups.values():
        hours = sum((s.hours for s in group), ZERO)
        item = InvoiceItem.objects.create(
            invoice=inv, description=f"{group[0].task.title} ({len(group)} approved timesheet entries)",
            quantity=hours, unit_price=hourly_rate, line_total=money(hours * hourly_rate))
        Timesheet.objects.filter(id__in=[s.id for s in group]).update(invoice_item=item)

def recalc_totals(inv):
    """All invoice totals are calculated server-side."""
    subtotal = money(sum((i.line_total for i in inv.items.all()), ZERO))
    if inv.discount > subtotal:
        raise ValidationError({"discount": ["Discount cannot exceed the subtotal."]})
    taxable = subtotal - inv.discount
    inv.subtotal = subtotal
    inv.tax = money(taxable * inv.tax_rate / Decimal("100"))
    inv.total = money(taxable + inv.tax)
    inv.amount_paid = ZERO
    inv.balance = inv.total
    inv.save()

@transaction.atomic
def create_invoice(user, timesheet_ids, hourly_rate, project, due_date, issue_date=None, **fields):
    inv = Invoice.objects.create(
        invoice_number=_next_number(Invoice, "invoice_number", "INV"),
        client=project.client, branch=project.branch, project=project,
        issue_date=issue_date or datetime.date.today(), due_date=due_date, created_by=user, **fields)
    build_items(inv, timesheet_ids, hourly_rate)
    recalc_totals(inv)
    InvoiceStatusHistory.objects.create(invoice=inv, from_status="", to_status="draft",
                                        changed_by=user, reason="Created")
    return inv

@transaction.atomic
def update_invoice(invoice, timesheet_ids=None, hourly_rate=None, **fields):
    inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status != "draft":
        raise ValidationError({"status": ["Only draft invoices can be edited."]})
    for k, v in fields.items():
        setattr(inv, k, v)
    inv.save()
    if timesheet_ids is not None:
        inv.items.all().delete()                 # SET_NULL frees the old timesheets
        build_items(inv, timesheet_ids, hourly_rate)
    recalc_totals(inv)
    return inv

# ---------- invoice lifecycle ----------

@transaction.atomic
def issue(invoice, user):
    inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status != "draft":
        raise ValidationError({"status": [f"Only draft invoices can be issued (current: {inv.status})."]})
    if not inv.items.exists() or inv.total <= 0:
        raise ValidationError({"items": ["An invoice needs billed work and a total above zero."]})
    if inv.due_date < inv.issue_date:
        raise ValidationError({"due_date": ["Due date cannot be before the issue date."]})
    _set_status(inv, "issued", user, "Issued")
    inv.amount_paid, inv.balance = ZERO, inv.total
    inv.save()
    events.invoice_issued(inv, user)
    return inv

@transaction.atomic
def cancel(invoice, user, reason):
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required to cancel an invoice."]})
    inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status in ("paid", "cancelled"):
        raise ValidationError({"status": [f"A {inv.status} invoice cannot be cancelled."]})
    if inv.payments.exclude(status="rejected").exists():
        raise ValidationError({"status": ["Reject the payments on this invoice before cancelling it."]})
    Timesheet.objects.filter(invoice_item__invoice=inv).update(invoice_item=None)   # work becomes billable again
    _set_status(inv, "cancelled", user, reason)
    inv.cancel_reason, inv.balance = reason, ZERO
    inv.save()
    return inv

def derive_status(inv):
    if inv.status in ("draft", "cancelled"):
        return inv.status
    if inv.balance <= 0:
        return "paid"
    if inv.due_date < datetime.date.today():
        return "overdue"
    return "partially_paid" if inv.amount_paid > 0 else "issued"

def recalc_invoice(inv, user=None, reason=""):
    """Balance and status come only from confirmed/reconciled payments."""
    paid = inv.payments.filter(status__in=COUNTED).aggregate(s=Sum("amount"))["s"] or ZERO
    inv.amount_paid = money(paid)
    inv.balance = max(money(inv.total - inv.amount_paid), ZERO)
    _set_status(inv, derive_status(inv), user, reason)
    inv.save()

def mark_overdue():
    """Called on invoice requests and by the `mark_overdue` command (run it daily from cron)."""
    due = Invoice.objects.filter(status__in=("issued", "partially_paid"),
                                 due_date__lt=datetime.date.today(), balance__gt=0)
    for inv in due:
        _set_status(inv, "overdue", None, "Past due date")
        inv.save()

# ---------- payments ----------

def _check_capacity(inv, amount, user, allow_overpayment):
    if amount > inv.balance and not (user.is_super_admin and allow_overpayment):
        raise ValidationError({"amount": [
            f"Amount exceeds the outstanding balance ({inv.balance}). Only a Super Admin can authorize an overpayment."]})

def _lock_payable(invoice):
    inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status not in PAYABLE:
        raise ValidationError({"invoice": ["Payments apply only to issued, partially paid or overdue invoices."]})
    return inv

@transaction.atomic
def record_payment(user, invoice, amount, method, reference, payment_date,
                   notes="", initial_status="confirmed", allow_overpayment=False):
    inv = _lock_payable(invoice)
    if Payment.objects.filter(invoice=inv, reference__iexact=reference).exclude(status="rejected").exists():
        raise ValidationError({"reference": ["This reference was already recorded on this invoice."]})
    _check_capacity(inv, amount, user, allow_overpayment)
    payment = Payment.objects.create(
        payment_number=_next_number(Payment, "payment_number", "PAY"), invoice=inv, client=inv.client,
        amount=money(amount), method=method, reference=reference, payment_date=payment_date,
        status=initial_status, notes=notes, recorded_by=user)
    if initial_status == "confirmed":
        recalc_invoice(inv, user, f"Payment {payment.payment_number} recorded")
    events.payment_recorded(payment, user)
    return payment

@transaction.atomic
def confirm_payment(payment, user, allow_overpayment=False):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != "pending":
        raise ValidationError({"status": ["Only pending payments can be confirmed."]})
    inv = _lock_payable(payment.invoice)
    _check_capacity(inv, payment.amount, user, allow_overpayment)
    payment.status = "confirmed"
    payment.save()
    recalc_invoice(inv, user, f"Payment {payment.payment_number} confirmed")
    return payment

@transaction.atomic
def reject_payment(payment, user, reason):
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required to reject a payment."]})
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status not in ("pending", "confirmed"):
        raise ValidationError({"status": [f"A {payment.status} payment cannot be rejected."]})
    inv = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
    payment.status, payment.reject_reason = "rejected", reason
    payment.save()
    recalc_invoice(inv, user, f"Payment {payment.payment_number} rejected: {reason}")
    return payment

@transaction.atomic
def reconcile_payment(payment, user):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != "confirmed":
        raise ValidationError({"status": ["Only confirmed payments can be reconciled."]})
    payment.status, payment.reconciled_by, payment.reconciled_at = "reconciled", user, timezone.now()
    payment.save()
    return payment