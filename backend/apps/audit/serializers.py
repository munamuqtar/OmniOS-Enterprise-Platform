from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "user", "user_name", "action", "module", "record_type", "record_id",
                  "record_repr", "branch", "old_values", "new_values", "ip_address", "created_at"]
        read_only_fields = fields