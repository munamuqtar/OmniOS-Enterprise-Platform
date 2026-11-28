from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from apps.core.responses import ok
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Everyone sees only their own notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_read", "kind"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        n = self.get_object()
        if not n.is_read:
            n.is_read, n.read_at = True, timezone.now()
            n.save(update_fields=["is_read", "read_at", "updated_at"])
        return ok(self.get_serializer(n).data, "Marked as read")

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        n = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return ok({"updated": n}, "All notifications marked as read")

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return ok({"unread": self.get_queryset().filter(is_read=False).count()})