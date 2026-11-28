from rest_framework import serializers
from apps.organizations.models import Organization

class BranchValidationMixin:
    def validate_branch(self, branch):
        user = self.context["request"].user
        if not user.is_super_admin and branch.id not in user.branch_ids():
            raise serializers.ValidationError("You do not have access to this branch.")
        return branch


class DefaultOrganizationMixin:
    """This is a single-company system. If a client omits the organization, use the company."""
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not self.instance and "organization" not in value:
            org = Organization.objects.order_by("created_at").first()
            if org is None:
                raise serializers.ValidationError({"organization": ["Create the organization first."]})
            value["organization"] = org
        return value