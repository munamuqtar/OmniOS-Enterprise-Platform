from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.core.responses import ok, fail
from .serializers import MeSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from apps.audit import services as audit_services
from rest_framework import viewsets
from apps.core.permissions import HasRole
from .models import User
from .serializers import MeSerializer, UserSerializer
from .throttles import LoginRateThrottle

class LoginView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle] 
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        audit_services.record("login", "auth", serializer.user, user=serializer.user)
        return ok(serializer.validated_data, "Login successful")

class RefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return ok(response.data, "Token refreshed")

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
        except TokenError:
            return fail({"refresh": ["Invalid or expired token."]}, "Logout failed")
        return ok(message="Logged out")

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return ok(MeSerializer(request.user).data)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("roles", "branches").order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasRole.of("super_admin")]
    http_method_names = ["get", "post", "put", "head", "options"]
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["is_active", "roles__code", "branches"]