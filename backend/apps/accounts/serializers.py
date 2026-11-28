from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password
from apps.access_control.models import Role
from apps.branches.models import Branch
from .models import UserRole, UserBranch
from django.contrib.auth.password_validation import validate_password
from apps.access_control.models import Role
from apps.branches.models import Branch
from .models import User, UserRole, UserBranch

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role_codes = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    branch_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    roles = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active",
                  "password", "role_codes", "branch_ids", "roles", "branches", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_roles(self, obj):
        return sorted(obj.role_codes)

    def get_branches(self, obj):
        return [{"id": str(b.id), "name": b.name} for b in obj.branches.all()]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role_codes(self, codes):
        found = set(Role.objects.filter(code__in=codes).values_list("code", flat=True))
        missing = set(codes) - found
        if missing:
            raise serializers.ValidationError(f"Unknown roles: {sorted(missing)}")
        return codes

    def validate_branch_ids(self, ids):
        if Branch.objects.filter(id__in=ids).count() != len(set(ids)):
            raise serializers.ValidationError("One or more branches do not exist.")
        return ids

    def create(self, validated):
        password = validated.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": ["Password is required."]})
        role_codes = validated.pop("role_codes", [])
        branch_ids = validated.pop("branch_ids", [])
        user = User.objects.create_user(password=password, **validated)
        self._assign(user, role_codes, branch_ids)
        return user

    def update(self, instance, validated):
        password = validated.pop("password", None)
        role_codes = validated.pop("role_codes", None)
        branch_ids = validated.pop("branch_ids", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if role_codes is not None:
            UserRole.objects.filter(user=instance).delete()
            self._assign(instance, role_codes, [])
        if branch_ids is not None:
            UserBranch.objects.filter(user=instance).delete()
            self._assign(instance, [], branch_ids)
        return instance

    def _assign(self, user, role_codes, branch_ids):
        for role in Role.objects.filter(code__in=role_codes):
            UserRole.objects.get_or_create(user=user, role=role)
        for bid in branch_ids:
            UserBranch.objects.get_or_create(user=user, branch_id=bid)

class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "roles", "branches"]

    def get_roles(self, obj):
        return sorted(obj.role_codes)

    def get_branches(self, obj):
        return [{"id": str(b.id), "name": b.name} for b in obj.branches.all()]

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role_codes = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    branch_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    roles = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active",
                  "password", "role_codes", "branch_ids", "roles", "branches", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_roles(self, obj):
        return sorted(obj.role_codes)

    def get_branches(self, obj):
        return [{"id": str(b.id), "name": b.name} for b in obj.branches.all()]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role_codes(self, codes):
        found = set(Role.objects.filter(code__in=codes).values_list("code", flat=True))
        missing = set(codes) - found
        if missing:
            raise serializers.ValidationError(f"Unknown roles: {sorted(missing)}")
        return codes

    def validate_branch_ids(self, ids):
        if Branch.objects.filter(id__in=ids).count() != len(set(ids)):
            raise serializers.ValidationError("One or more branches do not exist.")
        return ids

    def create(self, validated):
        password = validated.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": ["Password is required."]})
        role_codes = validated.pop("role_codes", [])
        branch_ids = validated.pop("branch_ids", [])
        user = User.objects.create_user(password=password, **validated)
        self._assign(user, role_codes, branch_ids)
        return user

    def update(self, instance, validated):
        password = validated.pop("password", None)
        role_codes = validated.pop("role_codes", None)
        branch_ids = validated.pop("branch_ids", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if role_codes is not None:
            UserRole.objects.filter(user=instance).delete()
        if branch_ids is not None:
            UserBranch.objects.filter(user=instance).delete()
        self._assign(instance, role_codes or [], branch_ids or [])
        return instance

    def _assign(self, user, role_codes, branch_ids):
        for role in Role.objects.filter(code__in=role_codes):
            UserRole.objects.get_or_create(user=user, role=role)
        for bid in branch_ids:
            UserBranch.objects.get_or_create(user=user, branch_id=bid)