from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.permissions import BasePermission
from apps.core.permissions import HasRole
from .models import Branch
from .serializers import BranchSerializer

class BranchPermission(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return u.is_super_admin   # HR "Limited" refinement can come later

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.select_related("organization", "manager")
    serializer_class = BranchSerializer
    permission_classes = [BranchPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "branch_code"]
    filterset_fields = ["status", "organization"]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        return qs if u.is_super_admin else qs.filter(id__in=u.branch_ids())