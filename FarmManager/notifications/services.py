import json
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from .constants import NotificationEventType, NotificationPriority
from .models import Notification

User = get_user_model()
channel_layer = get_channel_layer()


class NotificationService:
    @staticmethod
    def _serialize_notification(notification: Notification) -> dict:
        return {
            "id": notification.id,
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority,
            "data": notification.data,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }

    @staticmethod
    def _send_to_user_group(user_id: int, notification: Notification):
        if channel_layer:
            from asgiref.sync import async_to_sync

            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "notification_message",
                    "notification": NotificationService._serialize_notification(notification),
                },
            )

    @classmethod
    def notify_user(
        cls,
        user_id: int,
        event_type: str,
        title: str,
        message: str,
        priority: str = NotificationPriority.NORMAL,
        data: dict = None,
    ) -> Notification:
        notification = Notification.objects.create(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            priority=priority,
            data=data or {},
        )
        cls._send_to_user_group(user_id, notification)
        return notification

    @classmethod
    def notify_users(
        cls,
        user_ids: list[int],
        event_type: str,
        title: str,
        message: str,
        priority: str = NotificationPriority.NORMAL,
        data: dict = None,
    ) -> list[Notification]:
        notifications = []
        valid_user_ids = [uid for uid in user_ids if uid]
        if not valid_user_ids:
            return notifications
        for user_id in valid_user_ids:
            notification = cls.notify_user(
                user_id=user_id,
                event_type=event_type,
                title=title,
                message=message,
                priority=priority,
                data=data,
            )
            notifications.append(notification)
        return notifications

    @classmethod
    def notify_heat_sign(cls, cow_id, cow_name: str, farm_name: str, inseminator_ids: list[int]):
        title = "Heat Sign Detected"
        message = f"Cow '{cow_name}' at {farm_name} is showing heat signs. Please schedule insemination."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        return cls.notify_users(
            user_ids=inseminator_ids,
            event_type=NotificationEventType.HEAT_SIGN,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            data=data,
        )

    @classmethod
    def notify_pregnancy_confirmed(cls, cow_id, cow_name: str, farm_name: str, farmer_user_ids: list[int]):
        title = "Pregnancy Confirmed"
        message = f"Cow '{cow_name}' at {farm_name} has been confirmed pregnant."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        return cls.notify_users(
            user_ids=farmer_user_ids,
            event_type=NotificationEventType.PREGNANCY_CONFIRMED,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data=data,
        )

    @classmethod
    def notify_medical_report(
        cls, cow_id: int, cow_name: str, farm_name: str, doctor_ids: list[int]
    ):
        title = "New Medical Report"
        message = f"A new medical report has been submitted for cow '{cow_name}' at {farm_name}. Please review."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        return cls.notify_users(
            user_ids=doctor_ids,
            event_type=NotificationEventType.MEDICAL_REPORT,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            data=data,
        )

    @classmethod
    def notify_doctor_assessment(
        cls, cow_id, cow_name: str, farm_name: str, farmer_user_ids: list[int]
    ):
        title = "Doctor Assessment Completed"
        message = f"A doctor has completed the assessment for cow '{cow_name}' at {farm_name}."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        return cls.notify_users(
            user_ids=farmer_user_ids,
            event_type=NotificationEventType.DOCTOR_ASSESSMENT,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data=data,
        )

    @classmethod
    def notify_insemination(
        cls, cow_id, cow_name: str, farm_name: str, farmer_user_ids: list[int]
    ):
        title = "Insemination Recorded"
        message = f"Insemination has been recorded for cow '{cow_name}' at {farm_name}."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        return cls.notify_users(
            user_ids=farmer_user_ids,
            event_type=NotificationEventType.INSEMINATION,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data=data,
        )

    @classmethod
    def notify_calving(
        cls, cow_id, cow_name: str, farm_name: str, farmer_user_ids: list[int], doctor_ids: list[int]
    ):
        title = "Calving/Birth Recorded"
        message = f"A calving event has been recorded for cow '{cow_name}' at {farm_name}."
        data = {"cow_id": cow_id, "farm_name": farm_name}
        all_user_ids = list(set(farmer_user_ids + doctor_ids))
        return cls.notify_users(
            user_ids=all_user_ids,
            event_type=NotificationEventType.CALVING_BIRTH,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            data=data,
        )

    @classmethod
    def notify_staff_changed(
        cls, farm_name: str, staff_type: str, affected_user_ids: list[int]
    ):
        title = "Staff Assignment Changed"
        message = f"A new {staff_type} has been assigned to {farm_name}."
        data = {"farm_name": farm_name, "staff_type": staff_type}
        return cls.notify_users(
            user_ids=affected_user_ids,
            event_type=NotificationEventType.STAFF_CHANGED,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data=data,
        )
