from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole, UserBranch
from apps.access_control.models import Role

def make_user(username, role_code, branches=()):
    role, _ = Role.objects.get_or_create(code=role_code, defaults={"name": role_code})
    user = User.objects.create_user(username=username, email=f"{username}@test.com", password="Passw0rd!x1")
    UserRole.objects.create(user=user, role=role)
    for b in branches:
        UserBranch.objects.create(user=user, branch=b)
    return user

def api_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client