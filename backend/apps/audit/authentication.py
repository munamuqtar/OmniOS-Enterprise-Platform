from rest_framework_simplejwt.authentication import JWTAuthentication
from . import context

class AuditJWTAuthentication(JWTAuthentication):
    """Same as JWT auth, but remembers who the user is so audit rows can name them."""
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            context.set_user(result[0])
        return result