from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import HasRole
from .models import Role, Permission
from .serializers import RoleSerializer, PermissionSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRole.of("super_admin")]
    http_method_names = ["get", "post", "head", "options"]

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasRole.of("super_admin")]