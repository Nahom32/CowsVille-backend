from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationViewSet,
)

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("mark-read/<int:notification_id>/", MarkNotificationReadView.as_view(), name="mark-notification-read"),
    path("mark-all-read/", MarkAllNotificationsReadView.as_view(), name="mark-all-notifications-read"),
    path("", include(router.urls)),
]
