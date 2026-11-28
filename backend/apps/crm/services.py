from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from .models import Lead, Client, LeadStatusHistory
from .models import Opportunity, OpportunityStageHistory

# which transitions are allowed by the manual status flow
TRANSITIONS = {
    "new": {"contacted", "pending", "qualified", "unqualified"},
    "contacted": {"pending", "qualified", "unqualified"},
    "pending": {"contacted", "qualified", "unqualified"},
    "qualified": {"unqualified"},
    "unqualified": {"contacted", "pending"},   # re-open
    "converted": set(),
}

def _record(lead, new_status, user, reason=""):
    LeadStatusHistory.objects.create(lead=lead, from_status=lead.status,
                                     to_status=new_status, changed_by=user, reason=reason)

@transaction.atomic
def change_status(lead, new_status, user, reason=""):
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    if new_status not in TRANSITIONS[lead.status]:
        raise ValidationError({"status": [f"Cannot change from '{lead.status}' to '{new_status}'."]})
    _record(lead, new_status, user, reason)
    lead.status = new_status
    lead.save(update_fields=["status", "updated_at"])
    return lead

@transaction.atomic
def qualify(lead, user, data):
    """data: business_requirement, budget, customer_interest, expected_timeline, notes"""
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    if lead.status == "converted":
        raise ValidationError({"status": ["Lead is already converted."]})
    for f in ("business_requirement", "budget", "customer_interest", "expected_timeline"):
        if data.get(f) in (None, ""):
            raise ValidationError({f: ["Required to qualify a lead."]})
        setattr(lead, f, data[f])
    if data.get("notes"):
        lead.notes = data["notes"]
    if "qualified" not in TRANSITIONS[lead.status] and lead.status != "qualified":
        raise ValidationError({"status": [f"Cannot qualify a lead that is '{lead.status}'."]})
    if lead.status != "qualified":
        _record(lead, "qualified", user)
    lead.status = "qualified"
    lead.unqualified_reason = ""
    lead.save()
    return lead

@transaction.atomic
def mark_unqualified(lead, user, reason):
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required to mark a lead unqualified."]})
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    if "unqualified" not in TRANSITIONS[lead.status]:
        raise ValidationError({"status": [f"Cannot mark '{lead.status}' lead as unqualified."]})
    _record(lead, "unqualified", user, reason)
    lead.status = "unqualified"
    lead.unqualified_reason = reason
    lead.save()
    return lead

@transaction.atomic
def convert_to_client(lead, user, address="", contact_person=""):
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    if lead.status == "converted":
        raise ValidationError({"status": ["Lead is already converted."]})
    if lead.status != "qualified":
        raise ValidationError({"status": ["Only qualified leads can be converted."]})
    if not lead.email:
        raise ValidationError({"email": ["Lead needs an email to be converted."]})

    # duplicate check: same email or same name+company in the same branch
    dup = Client.objects.filter(branch=lead.branch).filter(
        Q(email__iexact=lead.email) |
        Q(name__iexact=lead.name, company_name__iexact=lead.company_name)).first()
    if dup:
        raise ValidationError({"client": [f"A client already exists: '{dup.name}' ({dup.email})."]})

    client = Client.objects.create(
        name=lead.name, company_name=lead.company_name, contact_person=contact_person or lead.name,
        email=lead.email, phone=lead.phone, address=address, branch=lead.branch, created_by=user)
    _record(lead, "converted", user, f"Converted to client {client.id}")
    lead.status = "converted"
    lead.converted_client = client
    lead.save()
    return lead, client

OPP_ORDER = ["prospecting", "qualification", "proposal", "negotiation"]
DEFAULT_PROB = {"prospecting": 10, "qualification": 25, "proposal": 50, "negotiation": 75, "won": 100, "lost": 0}

@transaction.atomic
def change_opp_stage(opp, new_stage, user, reason=""):
    opp = Opportunity.objects.select_for_update().get(pk=opp.pk)
    old = opp.stage
    if old in ("won", "lost"):
        raise ValidationError({"stage": [f"A {old} opportunity cannot change stage."]})
    if new_stage == old:
        raise ValidationError({"stage": ["Opportunity is already in this stage."]})
    if new_stage == "lost":
        if not (reason or "").strip():
            raise ValidationError({"reason": ["A reason is required when marking an opportunity lost."]})
        opp.lost_reason = reason
    elif new_stage == "won":
        if old != "negotiation":
            raise ValidationError({"stage": ["Only opportunities in negotiation can be marked won."]})
        if not opp.client_id:
            raise ValidationError({"client": ["Link a client before marking the opportunity won."]})
    elif OPP_ORDER.index(new_stage) < OPP_ORDER.index(old):
        pass   # moving backwards is allowed
    elif OPP_ORDER.index(new_stage) - OPP_ORDER.index(old) > 1:
        raise ValidationError({"stage": ["Stages cannot be skipped."]})
    opp.stage = new_stage
    opp.probability = DEFAULT_PROB[new_stage]
    opp.save()
    OpportunityStageHistory.objects.create(opportunity=opp, from_stage=old, to_stage=new_stage,
                                           changed_by=user, reason=reason)
    return opp