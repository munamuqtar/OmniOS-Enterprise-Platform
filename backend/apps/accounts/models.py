from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from apps.organizations.models import TimeStampedModel

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(username=username, email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    roles = models.ManyToManyField("access_control.Role", through="UserRole", related_name="users")
    branches = models.ManyToManyField("branches.Branch", through="UserBranch", related_name="users")

    objects = UserManager()
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    @property
    def role_codes(self):
        return set(self.roles.values_list("code", flat=True))

    @property
    def is_super_admin(self):
        return "super_admin" in self.role_codes

    def branch_ids(self):
        return list(self.branches.values_list("id", flat=True))

class UserRole(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey("access_control.Role", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "role")

class UserBranch(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "branch")