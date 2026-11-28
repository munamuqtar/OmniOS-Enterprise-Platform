class BranchScopedMixin:
    """Filters every queryset by the user's assigned branches. Super Admin sees all."""
    branch_field = "branch_id"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_super_admin:
            return qs
        return qs.filter(**{f"{self.branch_field}__in": user.branch_ids()})