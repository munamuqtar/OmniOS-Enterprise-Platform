from rest_framework import viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.mixins import BranchScopedMixin
from .models import Department, Employee
from .serializers import DepartmentSerializer, EmployeeSerializer

DIRECTORY_ROLES = {"super_admin", "hr", "sales", "finance", "project_manager"}

class DirectoryPermission(BasePermission):
    """Any role can read; only HR and Super Admin can write."""
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated or not u.role_codes:
            return False
        if request.method in SAFE_METHODS:
            return True
        return u.is_super_admin or "hr" in u.role_codes

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [DirectoryPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["name", "code"]

class EmployeeViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("department", "branch", "user").order_by("employee_number")
    serializer_class = EmployeeSerializer
    permission_classes = [DirectoryPermission]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["employee_number", "first_name", "last_name", "email", "position"]
    filterset_fields = ["status", "department", "branch", "position"]

    def get_queryset(self):
        qs = super().get_queryset()          # branch isolation first
        u = self.request.user
        if not (u.role_codes & DIRECTORY_ROLES):   # plain Employee role: own record only
            return qs.filter(user=u)
        return qs