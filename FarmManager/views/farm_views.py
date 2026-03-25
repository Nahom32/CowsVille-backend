import logging

from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from FarmManager.models import Cow, FarmerMedicalReport, InseminationRecord, MedicalAssessment, Message, Reproduction

from ..models import Farm, Inseminator, Doctor
from ..serializers import FarmSerializer, InseminatorAssignmentSerializer, DoctorAssignmentSerializer
from ..constants import APIMessages, MessageTypes
from ..services import MessagingService, LoggingMixin, ResponseService
from FarmManager.notifications.services import NotificationService
from ..permissions import AdminGetOnlyPermission

logger = logging.getLogger(__name__)

class FarmViewSet(viewsets.ModelViewSet, LoggingMixin):
    queryset = Farm.objects.select_related(
        "type_of_housing",
        "type_of_floor",
        "source_of_water",
        "rate_of_cow_feeding",
        "rate_of_water_giving",
        "inseminator",
        "doctor",
    )
    serializer_class = FarmSerializer
    permission_classes = [AdminGetOnlyPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "farm_id",
        "owner_name",
        "is_deleted",
        "cluster_number",
    ]  # For exact matches
    search_fields = [
        "farm_id",
        "owner_name",
        "address",
        "cluster_number",
    ]  # For partial matches

    def create(self, request, *args, **kwargs):
        """Create a new farm with logging"""
        self.log_request_received("farm creation", request.data)
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                self.log_validation_error("farm creation", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            farm = serializer.save()
            self.log_operation_success("created farm", f"with ID: {farm.farm_id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            self.log_operation_error("creating farm", e)
            error_response, error_status = ResponseService.error_response(
                f"{APIMessages.FAILED_TO_CREATE_FARM}: {str(e)}"
            )
            return Response(error_response, status=error_status)

    def update(self, request, *args, **kwargs):
        """Update a farm with logging"""
        farm_pk = kwargs.get("pk")
        self.log_request_received(f"farm update for farm {farm_pk}", request.data)
        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )
            if not serializer.is_valid():
                self.log_validation_error("farm update", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            farm = serializer.save()
            self.log_operation_success("updated farm", farm.farm_id)
            return Response(serializer.data)

        except Exception as e:
            self.log_operation_error(f"updating farm {farm_pk}", e)
            error_response, error_status = ResponseService.error_response(
                f"{APIMessages.FAILED_TO_UPDATE_FARM}: {str(e)}"
            )
            return Response(error_response, status=error_status)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single farm with logging"""
        farm_pk = kwargs.get("pk")
        self.log_request_received(f"farm retrieve for farm {farm_pk}")
        try:
            response = super().retrieve(request, *args, **kwargs)
            self.log_operation_success("retrieved farm", farm_pk)
            return response

        except Exception as e:
            self.log_operation_error(f"retrieving farm {farm_pk}", e)
            error_response, error_status = ResponseService.error_response(
                f"{APIMessages.FAILED_TO_RETRIEVE_FARM}: {str(e)}"
            )
            return Response(error_response, status=error_status)

    def destroy(self, request, *args, **kwargs):
        """Delete a farm with logging"""
        farm_pk = kwargs.get("pk")
        self.log_request_received(f"farm deletion for farm {farm_pk}")
        try:
            instance = self.get_object()
            farm_id = instance.farm_id
            response = super().destroy(request, *args, **kwargs)
            self.log_operation_success("deleted farm", farm_id)
            return response

        except Exception as e:
            self.log_operation_error(f"deleting farm {farm_pk}", e)
            error_response, error_status = ResponseService.error_response(
                f"{APIMessages.FAILED_TO_DELETE_FARM}: {str(e)}"
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["GET"])
    def deleted(self, request):
        """List all soft-deleted farms"""
        self.log_request_received("list deleted farms")
        try:
            deleted_farms = Farm.objects.deleted().select_related(
                "type_of_housing", "type_of_floor", "source_of_water",
                "rate_of_cow_feeding", "rate_of_water_giving",
                "inseminator", "doctor",
            )
            serializer = FarmSerializer(deleted_farms, many=True)
            self.log_operation_success(
                "retrieved", f"{len(serializer.data)} deleted farms"
            )
            return Response(
                {
                    "total_deleted": len(serializer.data),
                    "farms": serializer.data,
                }
            )
        except Exception as e:
            self.log_operation_error("listing deleted farms", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["POST"])
    def restore(self, request, pk=None):
        """Restore a soft-deleted farm"""
        self.log_request_received(f"restore farm {pk}")
        try:
            farm = Farm.objects.deleted().get(pk=pk)
            farm.is_deleted = False
            farm.save()
            self.log_operation_success("restored farm", farm.farm_id)
            serializer = FarmSerializer(farm)
            return Response(
                {
                    "message": f"Farm {farm.farm_id} restored successfully",
                    "farm": serializer.data,
                }
            )
        except Farm.DoesNotExist:
            return Response(
                {"error": f"No deleted farm found with ID {pk}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            self.log_operation_error(f"restoring farm {pk}", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["DELETE"])
    def hard_delete(self, request, pk=None):
        """Permanently delete a farm and all related records"""
        self.log_request_received(f"hard delete farm {pk}")
        try:
            farm = Farm.objects.all_with_deleted().get(pk=pk)
            farm_id = farm.farm_id

            with transaction.atomic():
                # Get all cows in this farm (including deleted)
                cows = Cow.objects.all_with_deleted().filter(farm=farm)

                # Delete all related records for each cow
                for cow in cows:
                    Reproduction.objects.all_with_deleted().filter(cow=cow).delete()
                    MedicalAssessment.objects.all_with_deleted().filter(cow=cow).delete()
                    InseminationRecord.objects.all_with_deleted().filter(cow=cow).delete()
                    Message.objects.all_with_deleted().filter(cow=cow).delete()
                    FarmerMedicalReport.objects.all_with_deleted().filter(cow=cow).delete()

                # Delete all cows
                cows.delete()

                # Hard delete the farm
                farm.hard_delete()

            self.log_operation_success(
                "permanently deleted farm",
                f"{farm_id} and all related records",
            )
            return Response(
                {
                    "message": f"Farm {farm_id} and all related records permanently deleted",
                },
                status=status.HTTP_200_OK,
            )
        except Farm.DoesNotExist:
            return Response(
                {"error": f"No farm found with ID {pk}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            self.log_operation_error(f"hard deleting farm {pk}", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def change_inseminator(self, request, pk=None):
        """Change inseminator for a farm"""
        farm = self.get_object()
        logger.info(f"Request to change inseminator for farm {farm.farm_id}")

        serializer = InseminatorAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("inseminator change", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Validated inseminator change request for farm {farm.farm_id}")
        return self._change_staff(
            request,
            "inseminator",
            serializer.validated_data["inseminator_id"],
            MessageTypes.INSEMINATOR_ASSIGNMENT,
        )

    @action(detail=True, methods=["post"])
    def change_doctor(self, request, pk=None):
        """Change doctor for a farm"""
        farm = self.get_object()
        logger.info(f"Request to change doctor for farm {farm.farm_id}")

        serializer = DoctorAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("doctor change", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Validated doctor change request for farm {farm.farm_id}")
        return self._change_staff(
            request,
            "doctor",
            serializer.validated_data["doctor_id"],
            MessageTypes.DOCTOR_ASSIGNMENT,
        )

    def _change_staff(self, request, staff_type, staff_id, message_type):
        """Common method to handle staff changes"""
        farm = self.get_object()
        logger.info(
            f"Attempting to change {staff_type} for farm {farm.farm_id} to staff ID {staff_id}"
        )

        try:
            with transaction.atomic():
                # Get staff models and current assignments
                if staff_type == "inseminator":
                    StaffModel = Inseminator
                    old_staff = farm.inseminator
                else:
                    StaffModel = Doctor
                    old_staff = farm.doctor

                try:
                    new_staff = StaffModel.objects.get(id=staff_id)
                except StaffModel.DoesNotExist:
                    error_msg = (
                        f"{staff_type.capitalize()} with ID {staff_id} not found"
                    )
                    logger.error(error_msg)
                    return Response(
                        {"error": error_msg}, status=status.HTTP_404_NOT_FOUND
                    )

                logger.info(
                    f"Found new {staff_type}: {new_staff.name} (ID: {new_staff.id})"
                )

                # Update assignments
                if old_staff:
                    logger.info(
                        f"Replacing {staff_type}: {old_staff.name} (ID: {old_staff.id}) with {new_staff.name}"
                    )
                    old_staff.is_active = False
                else:
                    logger.info(f"No existing {staff_type} to replace")

                # Update farm with new staff
                setattr(farm, staff_type, new_staff)
                farm.save(update_fields=[staff_type])
                logger.info(
                    f"Successfully updated farm {farm.farm_id} with new {staff_type}"
                )

                # Send notifications using the messaging service
                notification_results = MessagingService.send_staff_change_notifications(
                    farm, staff_type, old_staff, new_staff, message_type
                )

                # Send WebSocket notifications to affected staff
                affected_user_ids = []
                if old_staff and old_staff.user_id:
                    affected_user_ids.append(old_staff.user_id)
                if new_staff.user_id:
                    affected_user_ids.append(new_staff.user_id)
                if affected_user_ids:
                    NotificationService.notify_staff_changed(
                        farm_name=farm.farm_id,
                        staff_type=staff_type,
                        affected_user_ids=affected_user_ids,
                    )

                logger.info(
                    f"Successfully completed the {staff_type} change process for farm {farm.farm_id}"
                )

                response_data = ResponseService.success_response(
                    f"{staff_type} changed successfully",
                    {
                        "farm_id": farm.farm_id,
                        "new_staff_id": new_staff.id,
                        "old_staff_id": old_staff.id if old_staff else None,
                        "notifications_sent": notification_results,
                    },
                )
                return Response(response_data)

        except Exception as e:
            logger.error(
                f"An error occurred while changing {staff_type} for farm {farm.farm_id}: {str(e)}"
            )
            error_response, error_status = ResponseService.error_response(
                f"Failed to change {staff_type} for farm {farm.farm_id}: Unexpected error"
            )
            return Response(error_response, status=error_status)