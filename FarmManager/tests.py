import uuid

import pytest
import pytest_asyncio
from asgiref.sync import sync_to_async
from channels.auth import AuthMiddlewareStack
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from FarmManager.notifications.consumers import NotificationConsumer
from FarmManager.notifications.routing import websocket_urlpatterns

User = get_user_model()


@pytest_asyncio.fixture
async def test_user(db):
    return await sync_to_async(User.objects.create_user)(
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        email="test@example.com",
        password="testpass123",
    )


@pytest_asyncio.fixture
async def other_user(db):
    return await sync_to_async(User.objects.create_user)(
        username=f"otheruser_{uuid.uuid4().hex[:8]}",
        email="other@example.com",
        password="testpass123",
    )


@pytest.fixture
def ws_application():
    return AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


@pytest.mark.asyncio
async def test_websocket_connection_authenticated(ws_application, test_user):
    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    connected, subprotocol = await communicator.connect()
    assert connected

    response = await communicator.receive_json_from()
    assert response["type"] == "connection_established"
    assert response["message"] == "Connected to notification server"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_connection_unauthenticated(ws_application):
    class AnonymousUser:
        is_authenticated = False

    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = AnonymousUser()

    connected, subprotocol = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
async def test_websocket_ping_pong(ws_application, test_user):
    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    await communicator.connect()
    await communicator.receive_json_from()

    await communicator.send_json_to({"type": "ping"})
    response = await communicator.receive_json_from()
    assert response["type"] == "pong"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_receive_notification(ws_application, test_user):
    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    await communicator.connect()
    await communicator.receive_json_from()

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"user_{test_user.id}",
        {
            "type": "notification_message",
            "notification": {
                "id": 1,
                "event_type": "heat_sign",
                "title": "Heat Sign Detected",
                "message": "Cow 'COW001' is showing heat signs.",
                "priority": "high",
                "data": {"cow_id": 1},
                "is_read": False,
                "created_at": "2026-03-26T10:00:00Z",
            },
        },
    )

    response = await communicator.receive_json_from()
    assert response["type"] == "notification"
    assert response["notification"]["title"] == "Heat Sign Detected"
    assert response["notification"]["event_type"] == "heat_sign"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_notification_isolation_between_users(ws_application, test_user, other_user):
    user1_communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    user1_communicator.scope["user"] = test_user

    user2_communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    user2_communicator.scope["user"] = other_user

    await user1_communicator.connect()
    await user1_communicator.receive_json_from()

    await user2_communicator.connect()
    await user2_communicator.receive_json_from()

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"user_{test_user.id}",
        {
            "type": "notification_message",
            "notification": {
                "id": 1,
                "event_type": "heat_sign",
                "title": "Heat Sign Detected",
                "message": "Cow 'COW001' is showing heat signs.",
                "priority": "high",
                "data": {"cow_id": 1},
                "is_read": False,
                "created_at": "2026-03-26T10:00:00Z",
            },
        },
    )

    response1 = await user1_communicator.receive_json_from()
    assert response1["type"] == "notification"

    import asyncio
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(user2_communicator.receive_json_from(), timeout=0.5)

    await user1_communicator.disconnect()
    await user2_communicator.disconnect()


@pytest.mark.asyncio
async def test_mark_notification_as_read(ws_application, test_user, db):
    from FarmManager.notifications.models import Notification

    notification = await sync_to_async(Notification.objects.create)(
        user=test_user,
        event_type="heat_sign",
        title="Test Notification",
        message="Test message",
    )

    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    await communicator.connect()
    await communicator.receive_json_from()

    await communicator.send_json_to({
        "type": "mark_read",
        "notification_id": notification.id,
    })

    response = await communicator.receive_json_from()
    assert response["type"] == "mark_read_response"
    assert response["success"] is True
    assert response["notification_id"] == notification.id

    await sync_to_async(notification.refresh_from_db)()
    assert notification.is_read

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_mark_notification_as_read_not_found(ws_application, test_user):
    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    await communicator.connect()
    await communicator.receive_json_from()

    await communicator.send_json_to({
        "type": "mark_read",
        "notification_id": 99999,
    })

    response = await communicator.receive_json_from()
    assert response["type"] == "mark_read_response"
    assert response["success"] is False

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_notification_service_sends_to_websocket(ws_application, test_user, db):
    from FarmManager.notifications.services import NotificationService

    communicator = WebsocketCommunicator(ws_application, "/ws/notifications/")
    communicator.scope["user"] = test_user

    await communicator.connect()
    await communicator.receive_json_from()

    await sync_to_async(NotificationService.notify_user)(
        user_id=test_user.id,
        event_type="heat_sign",
        title="Heat Sign Test",
        message="Test message from service",
        priority="high",
    )

    response = await communicator.receive_json_from()
    assert response["type"] == "notification"
    assert response["notification"]["title"] == "Heat Sign Test"
    assert response["notification"]["event_type"] == "heat_sign"

    await communicator.disconnect()
