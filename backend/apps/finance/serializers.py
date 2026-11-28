import datetime
from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, InvoiceItem, InvoiceStatusHistory, Payment

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "description", "quantity", "unit_price", "line_total"]
        read_only_fields = fields

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.project_code", read_only=True)
    timesheet_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True,
                                          required=False, allow_empty=False)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True,
                                           required=False, min_value=Decimal("0.01"))

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "client", "client_name", "branch", "project", "project_name",
                  "project_code", "issue_date", "due_date", "currency", "items", "subtotal", "discount",
                  "tax_rate", "tax", "total", "amount_paid", "balance", "status", "cancel_reason",
                  "notes", "timesheet_ids", "hourly_rate", "created_at", "updated_at"]
        read_only_fields = ["id", "invoice_number", "client", "branch", "subtotal", "tax", "total",
                            "amount_paid", "balance", "status", "cancel_reason", "created_at", "updated_at"]

    def validate_discount(self, v):
        if v < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return v

    def validate_tax_rate(self, v):
        if not Decimal("0") <= v <= Decimal("100"):
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return v

    def validate(self, attrs):
        user = self.context["request"].user
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))
        project = get("project")
        if not user.is_super_admin and project.branch_id not in user.branch_ids():
            raise serializers.ValidationError({"project": ["You do not have access to this project's branch."]})
        if self.instance:
            if self.instance.status != "draft":
                raise serializers.ValidationError("Only draft invoices can be edited.")
            if project.id != self.instance.project_id:
                raise serializers.ValidationError({"project": ["The project cannot be changed."]})
            if ("timesheet_ids" in attrs) != ("hourly_rate" in attrs):
                raise serializers.ValidationError("Send timesheet_ids and hourly_rate together to change the billed work.")
        else:
            if not attrs.get("timesheet_ids"):
                raise serializers.ValidationError({"timesheet_ids": ["Select approved timesheets to bill."]})
            if "hourly_rate" not in attrs:
                raise serializers.ValidationError({"hourly_rate": ["Hourly rate is required."]})
        issue = get("issue_date") or datetime.date.today()
        if get("due_date") < issue:
            raise serializers.ValidationError({"due_date": ["Due date cannot be before the issue date."]})
        return attrs

class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField()

class InvoiceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceStatusHistory
        fields = ["from_status", "to_status", "reason", "changed_by", "created_at"]

class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    initial_status = serializers.ChoiceField(choices=["pending", "confirmed"], default="confirmed", write_only=True)
    allow_overpayment = serializers.BooleanField(default=False, write_only=True)
    currency = serializers.CharField(source="invoice.currency", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "payment_number", "invoice", "invoice_number", "client", "client_name", "amount",
                  "currency", "method", "reference", "payment_date", "status", "notes", "reject_reason",
                  "recorded_by", "reconciled_by", "reconciled_at", "initial_status", "allow_overpayment",
                  "created_at"]
        read_only_fields = ["id", "payment_number", "client", "status", "reject_reason", "recorded_by",
                            "reconciled_by", "reconciled_at", "created_at"]

    def validate_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return v

    def validate_reference(self, v):
        if not v.strip():
            raise serializers.ValidationError("A transaction reference is required.")
        return v.strip()

    def validate_payment_date(self, v):
        if v > datetime.date.today():
            raise serializers.ValidationError("Payment date cannot be in the future.")
        return v

    def validate_invoice(self, inv):
        user = self.context["request"].user
        if not user.is_super_admin and inv.branch_id not in user.branch_ids():
            raise serializers.ValidationError("You do not have access to this invoice's branch.")
        return inv