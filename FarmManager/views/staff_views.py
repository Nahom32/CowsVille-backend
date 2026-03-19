import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from AlertSystem.sendMesage import send_alert
from ..models import Doctor, Farm, Inseminator
from ..permissions import AdminGetOnlyPermission
from ..serializers import DoctorSerializer, InseminatorSerializer
from ..services import LoggingMixin

logger = logging.getLogger(__name__)


class InseminatorViewSet(viewsets.ModelViewSet):
    queryset = Inseminator.objects.all()
    serializer_class = InseminatorSerializer
    permission_classes = [AdminGetOnlyPermission]

    @action(detail=True, methods=["post"])
    def replace_inseminator(self, request, pk=None):
        try:
            old_inseminator = self.get_object()
            new_phone = request.data.get("phone_number")
            new_name = request.data.get("name")
            new_address = request.data.get("address")

            if not all([new_phone, new_name, new_address]):
                return Response(
                    {"error": "phone_number, name, and address are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            old_inseminator.phone_number = new_phone
            old_inseminator.name = new_name
            old_inseminator.address = new_address
            old_inseminator.save()

            affected_farms = Farm.objects.filter(inseminator=old_inseminator)

            for farm in affected_farms:
                message = (
                    f"Notice: Your inseminator's details have been updated:\n"
                    f"Name: {new_name}\n"
                    f"Phone: {new_phone}\n"
                    f"Address: {new_address}"
                )
                send_alert(farm.telephone_number, message)

            return Response(
                {
                    "message": "Inseminator details updated successfully",
                    "affected_farms_count": affected_farms.count(),
                    "new_details": {
                        "name": new_name,
                        "phone": new_phone,
                        "address": new_address,
                    },
                }
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DoctorViewSet(viewsets.ModelViewSet, LoggingMixin):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [AdminGetOnlyPermission]

    def perform_create(self, serializer):
        doctor = serializer.save()
        self.log_operation_success(
            "created new doctor", f"{doctor.name} (ID: {doctor.id})"
        )

    def perform_update(self, serializer):
        doctor = serializer.save()
        self.log_operation_success("updated doctor", f"{doctor.name} (ID: {doctor.id})")
