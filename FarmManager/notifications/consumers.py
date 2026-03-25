import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.warning("[WS] WebSocket connect attempt")
        logger.warning(f"[WS] Scope: {self.scope}")

        self.user = self.scope.get("user")
        session = self.scope.get("session")
        headers = dict(self.scope.get("headers", []))

        logger.warning(f"[WS] User from scope: {self.user}")
        logger.warning(f"[WS] User is_authenticated: {getattr(self.user, 'is_authenticated', 'N/A')}")
        logger.warning(f"[WS] Session: {session}")
        logger.warning(f"[WS] Headers: {headers}")

        if self.user and getattr(self.user, 'is_authenticated', False):
            self.user_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.accept()
            await self.send(
                text_data=json.dumps({
                    "type": "connection_established",
                    "message": "Connected to notification server",
                })
            )
            logger.warning(f"[WS] Connection ACCEPTED for user {self.user.id}")
        else:
            logger.warning("[WS] Connection REJECTED - no authenticated user")
            await self.close(code=4001)

    async def disconnect(self, close_code):
        logger.warning(f"[WS] Disconnecting with code: {close_code}")
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "ping":
                await self.send(
                    text_data=json.dumps({"type": "pong"})
                )
            elif message_type == "mark_read":
                notification_id = data.get("notification_id")
                if notification_id:
                    from asgiref.sync import sync_to_async

                    def mark_read():
                        from .models import Notification
                        notification = Notification.objects.filter(
                            id=notification_id,
                            user=self.user
                        ).first()
                        if notification:
                            notification.mark_as_read()
                            return True
                        return False

                    marked = await sync_to_async(mark_read)()
                    await self.send(
                        text_data=json.dumps({
                            "type": "mark_read_response",
                            "notification_id": notification_id,
                            "success": marked,
                        })
                    )
        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        notification = event["notification"]
        await self.send(
            text_data=json.dumps({
                "type": "notification",
                "notification": notification,
            })
        )
