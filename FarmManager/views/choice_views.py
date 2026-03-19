from rest_framework import filters, viewsets
from rest_framework.response import Response

from ..models import (
    BreedType, FeedingFrequency, FloorType, GeneralHealthStatus,
    GynecologicalStatus, HousingType, MastitisStatus,
    UdderHealthStatus, WaterSource
)
from ..permissions import ReadOnlyAdminPermission
from ..serializers import (
    BreedTypeSerializer, FeedingFrequencySerializer, FloorTypeSerializer,
    GeneralHealthStatusSerializer, GynecologicalStatusSerializer,
    HousingTypeSerializer, MastitisStatusSerializer,
    UdderHealthStatusSerializer, WaterSourceSerializer
)


class BreedTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BreedType.objects.all()
    serializer_class = BreedTypeSerializer
    permission_classes = [ReadOnlyAdminPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "display_name"]


class HousingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HousingType.objects.all()
    serializer_class = HousingTypeSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class FloorTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FloorType.objects.all()
    serializer_class = FloorTypeSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class FeedingFrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeedingFrequency.objects.all()
    serializer_class = FeedingFrequencySerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class WaterSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WaterSource.objects.all()
    serializer_class = WaterSourceSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class GynecologicalStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GynecologicalStatus.objects.all()
    serializer_class = GynecologicalStatusSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class UdderHealthStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UdderHealthStatus.objects.all()
    serializer_class = UdderHealthStatusSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class MastitisStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MastitisStatus.objects.all()
    serializer_class = MastitisStatusSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]


class GeneralHealthStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeneralHealthStatus.objects.all()
    serializer_class = GeneralHealthStatusSerializer
    permission_classes = [ReadOnlyAdminPermission]
    search_fields = ["name", "display_name"]
