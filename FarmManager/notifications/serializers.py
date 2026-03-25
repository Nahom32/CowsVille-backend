from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "event_type",
            "title",
            "message",
            "priority",
            "data",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationMarkReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField()

    def validate_notification_id(self, value):
        request = self.context.get("request")
        if request and request.user:
            if not Notification.objects.filter(id=value, user=request.user).exists():
                raise serializers.ValidationError("Notification not found.")
        return value
