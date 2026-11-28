from decimal import Decimal
from rest_framework import serializers
from apps.core.serializers import BranchValidationMixin
from .models import Quote, QuoteItem, QuoteApproval
from apps.accounts.models import User


class QuoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteItem
        fields = ["id", "description", "quantity", "unit_price", "line_total"]
        read_only_fields = ["id", "line_total"]

    def validate_quantity(self, v):
        if v <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return v

    def validate_unit_price(self, v):
        if v < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return v

class QuoteSerializer(BranchValidationMixin, serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Quote
        fields = ["id", "quote_number", "client", "client_name", "lead", "lead_name", "opportunity",
                  "branch", "currency", "items", "subtotal", "discount", "tax_rate", "tax", "total",
                  "status", "valid_until", "payment_terms", "notes", "revision",
                  "created_by", "created_by_name", "created_at", "updated_at"]
        read_only_fields = ["id", "quote_number", "subtotal", "tax", "total", "status", "revision",
                            "created_by", "created_at", "updated_at"]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items

    def validate_discount(self, v):
        if v < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return v

    def validate_tax_rate(self, v):
        if not Decimal("0") <= v <= Decimal("100"):
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return v

    def validate(self, attrs):
        client = attrs.get("client", getattr(self.instance, "client", None))
        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if not client and not lead:
            raise serializers.ValidationError("A quote needs a client or a lead.")
        for obj in (client, lead):
            if obj and branch and obj.branch_id != branch.id:
                raise serializers.ValidationError("Client/lead must belong to the same branch.")
        return attrs

class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField()

class ApprovalSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = QuoteApproval
        fields = ["revision", "decision", "actor_name", "reason", "created_at"]

class ConvertQuoteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    manager = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": ["End date cannot be before the start date."]})
        return attrs