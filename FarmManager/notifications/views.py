from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from FarmManager.pagination import StandardResultsSetPagination

from .models import Notification
from .serializers import (
    NotificationMarkReadSerializer,
    NotificationSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = []

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @action(detail=False, methods=["get"])
    def unread(self, request):
        queryset = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MarkNotificationReadView(APIView):
    permission_classes = []

    def post(self, request, notification_id):
        serializer = NotificationMarkReadSerializer(
            data={"notification_id": notification_id},
            context={"request": request},
        )
        if serializer.is_valid():
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user,
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
            return Response(
                {"message": "Notification marked as read"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkAllNotificationsReadView(APIView):
    permission_classes = []

    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response(
            {"message": f"{updated} notifications marked as read"},
            status=status.HTTP_200_OK,
        )
