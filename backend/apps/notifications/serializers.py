from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "message", "related_type", "related_id",
                  "branch", "is_read", "read_at", "created_at"]
        read_only_fields = fields