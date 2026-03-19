import logging

from rest_framework import filters, viewsets
from rest_framework.response import Response

from ..models import Message
from ..permissions import ReadOnlyAdminPermission
from ..serializers import MessageSerializer

logger = logging.getLogger(__name__)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.select_related("farm", "cow")
    serializer_class = MessageSerializer
    permission_classes = [ReadOnlyAdminPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["message_text", "message_type"]

    def get_queryset(self):
        queryset = Message.objects.select_related("farm", "cow")
        farm_id = self.request.query_params.get("farm_id", None)
        cow_id = self.request.query_params.get("cow_id", None)

        if cow_id and not farm_id:
            return Message.objects.none()

        if farm_id:
            queryset = queryset.filter(farm__farm_id=farm_id)
            if cow_id:
                queryset = queryset.filter(cow__cow_id=cow_id)

        return queryset
