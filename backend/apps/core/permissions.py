from rest_framework.permissions import BasePermission

class HasRole(BasePermission):
    """Use: permission_classes = [IsAuthenticated, HasRole.of("hr", "super_admin")]"""
    allowed_roles = ()

    @classmethod
    def of(cls, *roles):
        return type("HasRoleDynamic", (cls,), {"allowed_roles": set(roles)})

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_super_admin or bool(user.role_codes & self.allowed_roles)