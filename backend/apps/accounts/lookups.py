import uuid
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.core.responses import ok
from .models import User

LOOKUP_ROLES = {"sales", "project_manager"}


class UserLookupView(APIView):
    """People pickers: active users of one role, limited to the requester's branches."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        if not (u.is_super_admin or u.role_codes & {"sales", "project_manager", "hr", "finance"}):
            raise PermissionDenied("You do not have access to this lookup.")
        if request.query_params.get("unlinked"):
            if not (u.is_super_admin or "hr" in u.role_codes):
                raise PermissionDenied("Only HR can look up users without an employee profile.")
            qs = User.objects.filter(is_active=True, employee_profile__isnull=True)
        else:
            role = request.query_params.get("role")
            if role not in LOOKUP_ROLES:
                raise ValidationError({"role": [f"Role must be one of: {', '.join(sorted(LOOKUP_ROLES))}."]})
            qs = User.objects.filter(is_active=True, roles__code=role)
        qs = qs.distinct()
        if not u.is_super_admin:
            qs = qs.filter(branches__in=u.branch_ids()).distinct()
        branch = request.query_params.get("branch")
        if branch:
            try:
                qs = qs.filter(branches__id=uuid.UUID(branch)).distinct()
            except ValueError:
                raise ValidationError({"branch": ["Invalid branch id."]})
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        qs = qs.distinct().order_by("first_name", "username")[:50]
        return ok([{"id": x.id, "username": x.username,
                    "name": f"{x.first_name} {x.last_name}".strip() or x.username} for x in qs])