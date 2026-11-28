from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import HasRole
from .models import Organization
from .serializers import OrganizationSerializer

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, HasRole.of("super_admin")]
    http_method_names = ["get", "post", "put", "head", "options"]   # spec: GET, POST, PUT only
    search_fields = ["name", "company_code"]