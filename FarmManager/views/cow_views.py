import logging

from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from FarmManager.constants import APIMessages, MessageTemplates, MessageTypes
from FarmManager.models import Cow, FarmerMedicalReport, GeneralHealthStatus, InseminationRecord, MastitisStatus, MedicalAssessment, Message, Reproduction, UdderHealthStatus
from FarmManager.permissions import AdminGetOnlyPermission
from FarmManager.serializers import CowCreateUpdateSerializer, CowSerializer, DoctorMedicalAssessmentSerializer, FarmerMedicalAssessmentSerializer, HeatSignRecordSerializer, MonitorBirthSerializer, MonitorHeatSignSerializer, MonitorPregnancySerializer
from FarmManager.services import HealthService, LoggingMixin, MessagingService, ResponseService, ValidationService
from FarmManager.notifications.services import NotificationService
from django.utils.timezone import now
class CowViewSet(viewsets.ModelViewSet, LoggingMixin):
    queryset = Cow.objects.select_related(
        "farm",
        "breed",
        "gynecological_status",
        "farm__type_of_housing",
        "farm__type_of_floor",
        "farm__inseminator",
        "farm__doctor",
    )
    serializer_class = CowSerializer
    permission_classes = [AdminGetOnlyPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["cow_id", "breed__name"]
    filterset_fields = ["farm_id"]

    def get_serializer_class(self):
        """Use different serializers for different operations"""
        if self.action in ["create", "update", "partial_update"]:
            return CowCreateUpdateSerializer
        return CowSerializer

    def create(self, request, *args, **kwargs):
        """Create a new cow with logging"""
        self.log_request_received("cow creation", request.data)
        try:
            response = super().create(request, *args, **kwargs)
            self.log_operation_success(
                "created cow", f"with ID: {response.data.get('cow_id')}"
            )
            return response
        except Exception as e:
            self.log_operation_error("creating cow", e)
            raise

    def update(self, request, *args, **kwargs):
        """Update a cow with logging"""
        cow_pk = kwargs.get("pk")
        self.log_request_received(f"cow update for cow {cow_pk}", request.data)
        try:
            response = super().update(request, *args, **kwargs)
            self.log_operation_success("updated cow", cow_pk)
            return response
        except Exception as e:
            self.log_operation_error(f"updating cow {cow_pk}", e)
            raise

    def destroy(self, request, *args, **kwargs):
        """Delete a cow with logging"""
        cow_pk = kwargs.get("pk")
        self.log_request_received(f"cow deletion for cow {cow_pk}")
        try:
            response = super().destroy(request, *args, **kwargs)
            self.log_operation_success("deleted cow", cow_pk)
            return response
        except Exception as e:
            self.log_operation_error(f"deleting cow {cow_pk}", e)
            raise

    @action(detail=False, methods=["GET"])
    def deleted(self, request):
        """List all soft-deleted cows"""
        self.log_request_received("list deleted cows")
        try:
            deleted_cows = Cow.objects.deleted().select_related(
                "farm", "breed", "gynecological_status"
            )
            farm_id = request.query_params.get("farm_id")
            if farm_id:
                deleted_cows = deleted_cows.filter(farm__farm_id=farm_id)

            serializer = CowSerializer(deleted_cows, many=True)
            self.log_operation_success(
                "retrieved", f"{len(serializer.data)} deleted cows"
            )
            return Response(
                {
                    "total_deleted": len(serializer.data),
                    "cows": serializer.data,
                }
            )
        except Exception as e:
            self.log_operation_error("listing deleted cows", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["POST"])
    def restore(self, request, pk=None):
        """Restore a soft-deleted cow"""
        self.log_request_received(f"restore cow {pk}")
        try:
            cow = Cow.objects.deleted().select_related("farm").get(pk=pk)
            cow.is_deleted = False
            cow.save()
            self.log_operation_success("restored cow", cow.cow_id)
            serializer = CowSerializer(cow)
            return Response(
                {
                    "message": f"Cow {cow.cow_id} restored successfully",
                    "cow": serializer.data,
                }
            )
        except Cow.DoesNotExist:
            return Response(
                {"error": f"No deleted cow found with ID {pk}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            self.log_operation_error(f"restoring cow {pk}", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["DELETE"])
    def hard_delete(self, request, pk=None):
        """Permanently delete a cow and all related records"""
        self.log_request_received(f"hard delete cow {pk}")
        try:
            cow = Cow.objects.all_with_deleted().select_related("farm").get(pk=pk)
            cow_id = cow.cow_id
            farm_id = cow.farm.farm_id

            with transaction.atomic():
                # Delete related records first
                Reproduction.objects.all_with_deleted().filter(cow=cow).delete()
                MedicalAssessment.objects.all_with_deleted().filter(cow=cow).delete()
                InseminationRecord.objects.all_with_deleted().filter(cow=cow).delete()
                Message.objects.all_with_deleted().filter(cow=cow).delete()
                FarmerMedicalReport.objects.all_with_deleted().filter(cow=cow).delete()

                # Hard delete the cow
                cow.hard_delete()

            self.log_operation_success(
                "permanently deleted cow",
                f"{cow_id} from farm {farm_id} and all related records",
            )
            return Response(
                {
                    "message": f"Cow {cow_id} and all related records permanently deleted",
                },
                status=status.HTTP_200_OK,
            )
        except Cow.DoesNotExist:
            return Response(
                {"error": f"No cow found with ID {pk}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            self.log_operation_error(f"hard deleting cow {pk}", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request, *args, **kwargs):
        """List cows with logging"""
        self.log_request_received("cow list", f"query params: {request.query_params}")
        try:
            response = super().list(request, *args, **kwargs)
            self.log_operation_success("retrieved", f"{len(response.data)} cows")
            return response
        except Exception as e:
            self.log_operation_error("listing cows", e)
            raise

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single cow with logging"""
        cow_pk = kwargs.get("pk")
        self.log_request_received(f"cow retrieve for cow {cow_pk}")
        try:
            response = super().retrieve(request, *args, **kwargs)
            self.log_operation_success("retrieved cow", cow_pk)
            return response
        except Exception as e:
            self.log_operation_error(f"retrieving cow {cow_pk}", e)
            raise

    @action(detail=False, methods=["GET"])
    def by_farm(self, request):
        """Get all cows for a specific farm with logging"""
        farm_id = request.query_params.get("farm_id")
        self.log_request_received(f"by_farm for farm {farm_id}")

        if not farm_id:
            self.get_logger().warning("by_farm request missing farm_id parameter")
            return Response(
                {"error": APIMessages.FARM_ID_REQUIRED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cows = self.get_queryset().filter(farm__farm_id=farm_id)
            serializer = self.get_serializer(cows, many=True)
            self.log_operation_success(
                "retrieved", f"{len(serializer.data)} cows for farm {farm_id}"
            )

            return Response(
                {
                    "farm_id": farm_id,
                    "total_cows": len(serializer.data),
                    "cows": serializer.data,
                }
            )
        except Exception as e:
            self.log_operation_error(f"retrieving cows for farm {farm_id}", e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Override perform_create to automatically create reproduction and medical assessment records"""
        try:
            with transaction.atomic():
                # Save the cow first
                cow = serializer.save()
                self.log_operation_success(
                    "created new cow", f"{cow.cow_id} for farm {cow.farm.farm_id}"
                )

                # Create related records
                self._create_reproduction_record(cow, serializer)
                self._create_medical_assessment_record(cow, serializer)

        except Exception as e:
            self.log_operation_error(
                "creating cow with reproduction and medical records", e
            )
            raise

    def perform_update(self, serializer):
        """Override perform_update to handle reproduction and medical side-effects"""
        try:
            with transaction.atomic():
                cow = serializer.save()
                self.log_operation_success(
                    "updated cow", f"{cow.cow_id} for farm {cow.farm.farm_id}"
                )

                # Check if reproduction fields were sent in the update
                reproduction_fields = serializer.context.get("reproduction_fields", {})
                heat_fields = serializer.context.get("heat_fields", {})

                if reproduction_fields or heat_fields:
                    self._update_reproduction_record(cow, serializer)

        except Exception as e:
            self.log_operation_error(
                "updating cow with side-effect records", e
            )
            raise

    def _update_reproduction_record(self, cow, serializer):
        """Update or create reproduction record during cow update"""
        reproduction_fields = serializer.context.get("reproduction_fields", {})
        heat_fields = serializer.context.get("heat_fields", {})

        # Get or create reproduction record for this cow
        reproduction, created = Reproduction.objects.get_or_create(
            cow=cow,
            farm=cow.farm,
            defaults={"is_cow_pregnant": False},
        )

        # Update pregnancy status if provided
        if "is_pregnant" in reproduction_fields:
            is_pregnant = ValidationService.convert_yes_no_to_boolean(
                reproduction_fields["is_pregnant"]
            )
            reproduction.is_cow_pregnant = is_pregnant

        # Update heat sign fields if provided
        if "heat_start_date" in heat_fields:
            reproduction.heat_sign_start = heat_fields["heat_start_date"]
        if "heat_end_date" in heat_fields:
            reproduction.heat_sign_end = heat_fields["heat_end_date"]
        if "heat_signs" in heat_fields:
            reproduction.heat_signs_seen = heat_fields["heat_signs"]

        reproduction.save()

        action = "created" if created else "updated"
        self.log_operation_success(
            f"{action} reproduction record", f"for cow {cow.cow_id}"
        )

    def _create_reproduction_record(self, cow, serializer):
        """Create reproduction record for the cow"""
        medical_fields = serializer.context.get("medical_fields", {})
        reproduction_fields = serializer.context.get("reproduction_fields", {})
        heat_fields = serializer.context.get("heat_fields", {})

        # Convert is_pregnant from yes/no to boolean if present
        is_pregnant = ValidationService.convert_yes_no_to_boolean(
            reproduction_fields.get("is_pregnant", False)
        )

        # Create reproduction record with data from the request
        Reproduction.objects.create(
            cow=cow,
            farm=cow.farm,
            is_cow_pregnant=is_pregnant,
            pregnancy_date=serializer.validated_data.get("last_date_insemination"),
            calving_date=serializer.validated_data.get("last_calving_date"),
            heat_sign_start=heat_fields.get("heat_start_date", None),
            heat_sign_end=heat_fields.get("heat_end_date", None),
            heat_signs_seen=heat_fields.get("heat_signs", None),
        )
        self.log_operation_success(
            "created reproduction record", f"for cow {cow.cow_id}"
        )

    def _create_medical_assessment_record(self, cow, serializer):
        """Create medical assessment record for the cow"""
        medical_fields = serializer.context.get("medical_fields", {})

        # Get a doctor for the assessment
        assessed_by = HealthService.get_doctor_for_assessment(cow.farm)
        if not assessed_by:
            self.get_logger().warning(
                "No doctors available in the system, skipping medical assessment creation"
            )
            return

        # Get default health status objects
        general_health, udder_health, mastitis = (
            HealthService.get_default_health_statuses()
        )

        # Convert medical field values using validation service
        has_lameness = ValidationService.convert_yes_no_to_boolean(
            medical_fields.get("has_lameness")
        )
        is_vaccinated = ValidationService.convert_yes_no_to_boolean(
            medical_fields.get("is_vaccinated")
        )

        # Handle deworming from multiple possible sources
        has_deworming = ValidationService.convert_yes_no_to_boolean(
            medical_fields.get("has_deworming")
            or serializer.validated_data.get("deworming")
        )

        # Create medical assessment with data from the request
        MedicalAssessment.objects.create(
            farm=cow.farm,
            cow=cow,
            assessed_by=assessed_by,
            is_cow_sick=False,
            general_health=general_health,
            udder_health=udder_health,
            mastitis=mastitis,
            has_lameness=has_lameness,
            body_condition_score=ValidationService.safe_int_conversion(cow.bcs),
            reproductive_health=medical_fields.get("reproductive_health", "Normal"),
            metabolic_disease=medical_fields.get("metabolic_disease", "Normal"),
            is_cow_vaccinated=is_vaccinated,
            vaccination_date=medical_fields.get("vaccination_date"),
            vaccination_type=medical_fields.get("vaccination_type", ""),
            has_deworming=has_deworming,
            deworming_date=medical_fields.get("deworming_date"),
            deworming_type=medical_fields.get("deworming_type", ""),
            diagnosis="",
            treatment="",
            prescription="",
        )
        self.log_operation_success(
            "created medical assessment", f"for cow {cow.cow_id}"
        )

    @action(detail=False, methods=["post"])
    def record_heat_sign(self, request):
        """Record heat sign for a cow and send notifications"""
        self.log_request_received("heat sign recording")
        self.get_logger().info(f"Raw request data: {request.data}")

        # Log the specific heat_start_time format being received
        if "heat_start_time" in request.data:
            self.get_logger().info(
                f"Heat start time received: '{request.data['heat_start_time']}' (type: {type(request.data['heat_start_time'])})"
            )

        serializer = HeatSignRecordSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("heat sign recording", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            cow = serializer.validated_data["cow"]
            heat_signs = serializer.validated_data["heat_signs"]
            heat_start_time = serializer.validated_data["heat_start_time"]
            heat_sign_recorded_at = serializer.validated_data["heat_sign_recorded_at"]

            self.log_operation_success(
                "recording heat sign",
                f"for cow {cow.cow_id} from farm {cow.farm.farm_id}",
            )

            # record heat sign
            reproduction = self._create_or_update_reproduction(
                cow, heat_signs, heat_start_time, heat_sign_recorded_at
            )

            # Send SMS notifications using messaging service
            notification_results = MessagingService.send_heat_sign_notifications(
                cow, heat_signs
            )

            # Send WebSocket notifications to inseminator
            if cow.farm.inseminator and cow.farm.inseminator.user_id:
                NotificationService.notify_heat_sign(
                    cow_id=cow.id,
                    cow_name=cow.cow_id,
                    farm_name=cow.farm.farm_id,
                    inseminator_ids=[cow.farm.inseminator.user_id],
                )

            self.log_operation_success(
                "recorded heat sign",
                f"for cow {cow.cow_id} from farm {cow.farm.farm_id}",
            )

            response_data = ResponseService.success_response(
                APIMessages.HEAT_SIGN_RECORDED,
                {
                    "cow_id": cow.cow_id,
                    "farm_id": cow.farm.farm_id,
                    "heat_sign_start": reproduction.heat_sign_start,
                    "heat_sign_recorded_at": reproduction.heat_sign_recorded_at,
                    "notifications_sent": notification_results,
                },
            )
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error(
                f"recording heat sign for cow {cow.cow_id} from farm {cow.farm.farm_id}",
                e,
            )
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_or_update_reproduction(
        self, cow, heat_signs, heat_start_time, heat_sign_recorded_at=None
    ):
        """Create or update reproduction record based on heat signs"""
        self.log_operation_success(
            "creating or updating reproduction record",
            f"for cow {cow.cow_id} from farm {cow.farm.farm_id}",
        )

        reproduction, created = Reproduction.objects.get_or_create(
            cow=cow,
            farm=cow.farm,
            defaults={
                "is_cow_pregnant": False,
                "heat_sign_start": heat_start_time,
                "heat_signs_seen": heat_signs,
                "heat_sign_recorded_at": heat_sign_recorded_at or now(),
            },
        )

        if not created:
            reproduction.heat_sign_start = heat_start_time
            reproduction.heat_signs_seen = heat_signs
            if heat_sign_recorded_at:
                reproduction.heat_sign_recorded_at = heat_sign_recorded_at
            reproduction.save()

        self.log_operation_success(
            "created or updated reproduction record",
            f"for cow {cow.cow_id} from farm {cow.farm.farm_id}",
        )
        return reproduction

    @action(detail=False, methods=["post"])
    def monitor_pregnancy(self, request):
        """Monitor pregnancy status of a cow"""
        self.log_request_received("pregnancy monitoring")
        self.get_logger().info(f"Raw request data: {request.data}")

        serializer = MonitorPregnancySerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("pregnancy monitoring", serializer.errors)
            self.get_logger().warning(
                f"Received data keys: {list(request.data.keys()) if hasattr(request.data, 'keys') else 'No keys method'}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                cow = validated_data["cow"]

                # Calculate expected calving date
                expected_calving_date = validated_data["pregnancy_date"]

                # Update or create reproduction record
                reproduction, created = Reproduction.objects.get_or_create(
                    cow=cow,
                    farm=cow.farm,
                    defaults={
                        "is_cow_pregnant": True,
                        "pregnancy_date": validated_data["pregnancy_date"],
                        "calving_date": expected_calving_date,
                    },
                )

                if not created:
                    reproduction.is_cow_pregnant = True
                    reproduction.pregnancy_date = validated_data["pregnancy_date"]
                    reproduction.calving_date = expected_calving_date
                    reproduction.save()

                # Update cow record
                cow.number_of_inseminations = validated_data["service_per_conception"]
                cow.lactation_number = validated_data["lactation_number"]
                cow.save()

                # Send notification using message template
                farmer_message = MessageTemplates.pregnancy_confirmation(
                    cow.cow_id,
                    validated_data["pregnancy_date"].strftime("%Y-%m-%d"),
                    expected_calving_date.strftime("%Y-%m-%d"),
                    validated_data["lactation_number"],
                )

                # Send SMS notification and create message record
                MessagingService.send_notification_with_message_record(
                    cow.farm.telephone_number,
                    farmer_message,
                    MessageTypes.PREGNANCY_UPDATE,
                    cow.farm,
                    cow,
                    f"Pregnancy confirmation for cow {cow.cow_id}:",
                )

                # Send WebSocket notification to farmer
                if cow.farm.user_id:
                    NotificationService.notify_pregnancy_confirmed(
                        cow_id=cow.id,
                        cow_name=cow.cow_id,
                        farm_name=cow.farm.farm_id,
                        farmer_user_ids=[cow.farm.user_id],
                    )

                self.log_operation_success(
                    "updated pregnancy status", f"for cow {cow.cow_id}"
                )

                response_data = ResponseService.success_response(
                    APIMessages.PREGNANCY_UPDATED,
                    {
                        "cow_id": cow.cow_id,
                        "farm_id": cow.farm.farm_id,
                        "pregnancy_date": validated_data["pregnancy_date"],
                        "expected_calving_date": expected_calving_date,
                        "service_per_conception": validated_data[
                            "service_per_conception"
                        ],
                        "lactation_number": validated_data["lactation_number"],
                    },
                )
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error("pregnancy monitoring", e)
            error_response, error_status = ResponseService.error_response(
                APIMessages.FAILED_TO_UPDATE_PREGNANCY
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["post"])
    def farmer_medical_assessment(self, request):
        """Record farmer's medical assessment"""
        self.log_request_received("farmer medical assessment")

        serializer = FarmerMedicalAssessmentSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("farmer medical assessment", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                cow = serializer.validated_data["cow"]
                sickness_description = serializer.validated_data["sickness_description"]

                # Create medical report
                report = FarmerMedicalReport.objects.create(
                    farm=cow.farm, cow=cow, sickness_description=sickness_description
                )

                # Notify farm's doctor using message template
                if cow.farm.doctor:
                    doctor_message = MessageTemplates.doctor_medical_report_alert(
                        cow.cow_id,
                        cow.farm.farm_id,
                        cow.farm.owner_name,
                        sickness_description,
                    )
                    MessagingService.send_notification_with_message_record(
                        cow.farm.doctor.phone_number,
                        doctor_message,
                        MessageTypes.HEALTH_ALERT,
                        cow.farm,
                        cow,
                        f"Doctor medical report alert for cow {cow.cow_id}:",
                    )

                    # Send WebSocket notification to doctor
                    if cow.farm.doctor.user_id:
                        NotificationService.notify_medical_report(
                            cow_id=cow.id,
                            cow_name=cow.cow_id,
                            farm_name=cow.farm.farm_id,
                            doctor_ids=[cow.farm.doctor.user_id],
                        )

                # Send confirmation to farmer using message template
                doctor_name = (
                    cow.farm.doctor.name if cow.farm.doctor else "the assigned doctor"
                )
                farmer_message = MessageTemplates.farmer_medical_report_confirmation(
                    cow.cow_id, sickness_description, doctor_name
                )
                MessagingService.send_notification_with_message_record(
                    cow.farm.telephone_number,
                    farmer_message,
                    MessageTypes.FARMER_ALERT,
                    cow.farm,
                    cow,
                    f"Farmer medical report confirmation for cow {cow.cow_id}:",
                )

                self.log_operation_success(
                    "created medical report", f"for cow {cow.cow_id}"
                )

                response_data = ResponseService.success_response(
                    APIMessages.MEDICAL_ASSESSMENT_SUBMITTED,
                    {
                        "report_id": report.id,
                        "farm_id": cow.farm.farm_id,
                        "cow_id": cow.cow_id,
                        "reported_date": report.reported_date,
                    },
                )
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error("farmer medical assessment", e)
            error_response, error_status = ResponseService.error_response(
                APIMessages.FAILED_TO_SUBMIT_MEDICAL_ASSESSMENT
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["post"])
    def doctor_assessment(self, request):
        """Record doctor's medical assessment"""
        self.log_request_received("doctor assessment")
        self.get_logger().info(f"Raw request data: {request.data}")

        serializer = DoctorMedicalAssessmentSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("doctor assessment", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                cow = validated_data["cow"]
                doctor = validated_data["doctor"]

                # Convert health status IDs to model instances
                health_status_fields = {}
                if "general_health" in validated_data:
                    health_status_fields["general_health"] = (
                        GeneralHealthStatus.objects.get(
                            id=validated_data["general_health"]
                        )
                    )
                if "udder_health" in validated_data:
                    health_status_fields["udder_health"] = (
                        UdderHealthStatus.objects.get(id=validated_data["udder_health"])
                    )
                if "mastitis" in validated_data:
                    health_status_fields["mastitis"] = MastitisStatus.objects.get(
                        id=validated_data["mastitis"]
                    )

                # Create medical assessment with model instances
                assessment_data = {
                    k: v
                    for k, v in validated_data.items()
                    if k
                    not in [
                        "cow",
                        "doctor",
                        "farm_id",
                        "cow_id",
                        "doctor_id",
                        "general_health",
                        "udder_health",
                        "mastitis",
                    ]
                }

                # Add the health status instances
                assessment_data.update(health_status_fields)

                assessment = MedicalAssessment.objects.create(
                    farm=cow.farm, cow=cow, assessed_by=doctor, **assessment_data
                )

                # Notify farmer using message template
                farmer_message = MessageTemplates.medical_assessment_complete(
                    cow.cow_id,
                    doctor.name,
                    validated_data["is_cow_sick"],
                    validated_data.get("has_lameness", False),
                    validated_data.get("notes"),
                )
                MessagingService.send_notification_with_message_record(
                    cow.farm.telephone_number,
                    farmer_message,
                    MessageTypes.HEALTH_ALERT,
                    cow.farm,
                    cow,
                    f"Medical assessment complete for cow {cow.cow_id}:",
                )

                # Send WebSocket notification to farmer
                if cow.farm.user_id:
                    NotificationService.notify_doctor_assessment(
                        cow_id=cow.id,
                        cow_name=cow.cow_id,
                        farm_name=cow.farm.farm_id,
                        farmer_user_ids=[cow.farm.user_id],
                    )

                # Send confirmation to doctor using message template
                doctor_confirmation = MessageTemplates.doctor_assessment_confirmation(
                    cow.farm.farm_id,
                    cow.farm.owner_name,
                    cow.cow_id,
                    validated_data["is_cow_sick"],
                )
                MessagingService.send_notification_with_message_record(
                    doctor.phone_number,
                    doctor_confirmation,
                    MessageTypes.DOCTOR_CONFIRMATION,
                    cow.farm,
                    cow,
                    f"Doctor assessment confirmation for cow {cow.cow_id}:",
                )

                self.log_operation_success(
                    "created medical assessment", f"for cow {cow.cow_id}"
                )

                response_data = ResponseService.success_response(
                    APIMessages.MEDICAL_ASSESSMENT_RECORDED,
                    {
                        "assessment_id": assessment.id,
                        "farm_id": cow.farm.farm_id,
                        "cow_id": cow.cow_id,
                    },
                )
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error("doctor assessment", e)
            error_response, error_status = ResponseService.error_response(
                APIMessages.FAILED_TO_RECORD_MEDICAL_ASSESSMENT
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["post"])
    def monitor_heat_sign(self, request):
        """Monitor heat signs and record insemination"""
        self.log_request_received("heat sign monitoring")
        self.get_logger().info(f"Raw request data: {request.data}")

        serializer = MonitorHeatSignSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("heat sign monitoring", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                cow = validated_data["cow"]

                # Create insemination record
                record = InseminationRecord.objects.create(
                    farm=cow.farm,
                    cow=cow,
                    inseminator=cow.farm.inseminator,
                    is_inseminated=validated_data["is_inseminated"],
                    date_of_insemination=validated_data.get("date_of_insemination"),
                    insemination_count=validated_data["insemination_count"],
                    lactation_number=validated_data["lactation_number"],
                )

                # Update reproduction record if cow is inseminated
                if validated_data["is_inseminated"]:
                    reproduction, _ = Reproduction.objects.get_or_create(
                        cow=cow,
                        farm=cow.farm,
                        defaults={
                            "is_cow_pregnant": False,
                        },
                    )
                    reproduction.pregnancy_date = validated_data["date_of_insemination"]
                    reproduction.save()

                # Format date for messages
                insemination_date = None
                if (
                    validated_data["is_inseminated"]
                    and "date_of_insemination" in validated_data
                ):
                    insemination_date = validated_data["date_of_insemination"].strftime(
                        "%Y-%m-%d"
                    )

                # Notify farmer using message template
                farmer_message = MessageTemplates.heat_monitoring_farmer(
                    cow.cow_id,
                    cow.farm.farm_id,
                    cow.farm.owner_name,
                    validated_data["is_inseminated"],
                    validated_data["insemination_count"],
                    insemination_date,
                )
                MessagingService.send_notification_with_message_record(
                    cow.farm.telephone_number,
                    farmer_message,
                    MessageTypes.HEAT_ALERT,
                    cow.farm,
                    cow,
                    f"Heat monitoring farmer alert for cow {cow.cow_id}:",
                )

                # Notify inseminator using message template
                inseminator_message = MessageTemplates.heat_monitoring_inseminator(
                    cow.farm.farm_id,
                    cow.cow_id,
                    validated_data["is_inseminated"],
                    validated_data["lactation_number"],
                    validated_data["insemination_count"],
                    insemination_date,
                )
                MessagingService.send_notification_with_message_record(
                    cow.farm.inseminator.phone_number,
                    inseminator_message,
                    MessageTypes.INSEMINATION_ALERT,
                    cow.farm,
                    cow,
                    f"Heat monitoring inseminator alert for cow {cow.cow_id}:",
                )

                # Send WebSocket notifications
                if validated_data["is_inseminated"]:
                    # Notify farmer about insemination
                    if cow.farm.user_id:
                        NotificationService.notify_insemination(
                            cow_id=cow.id,
                            cow_name=cow.cow_id,
                            farm_name=cow.farm.farm_id,
                            farmer_user_ids=[cow.farm.user_id],
                        )

                self.log_operation_success(
                    "recorded heat sign monitoring", f"for cow {cow.cow_id}"
                )

                response_data = ResponseService.success_response(
                    APIMessages.HEAT_SIGN_MONITORING_RECORDED,
                    {
                        "record_id": record.id,
                        "farm_id": cow.farm.farm_id,
                        "cow_id": cow.cow_id,
                    },
                )
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error("heat sign monitoring", e)
            error_response, error_status = ResponseService.error_response(
                APIMessages.FAILED_TO_RECORD_HEAT_MONITORING
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["post"])
    def monitor_birth(self, request):
        """Record birth event for a cow"""
        self.log_request_received("birth monitoring")
        self.get_logger().info(f"Raw request data: {request.data}")

        serializer = MonitorBirthSerializer(data=request.data)
        if not serializer.is_valid():
            self.log_validation_error("birth monitoring", serializer.errors)
            self.get_logger().warning(
                f"Received data keys: {list(request.data.keys()) if hasattr(request.data, 'keys') else 'No keys method'}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                cow = validated_data["cow"]

                # Check if there's an existing reproduction record
                reproduction = Reproduction.objects.filter(
                    cow=cow, is_cow_pregnant=True
                ).first()
                if reproduction:
                    # Update existing reproduction record
                    reproduction.is_cow_pregnant = False
                    reproduction.calving_date = validated_data["calving_date"]
                    reproduction.save()

                # Update cow record
                cow.parity += 1  # Increment number of births
                cow.last_calving_date = validated_data["last_calving_date"]
                cow.save()

                # Create message for farmer using template
                farmer_message = MessageTemplates.birth_event(
                    cow.cow_id,
                    validated_data["calving_date"],
                    validated_data["last_calving_date"],
                    validated_data["calf_sex"],
                )

                # Send notifications using messaging service
                MessagingService.send_notification_with_message_record(
                    cow.farm.telephone_number,
                    farmer_message,
                    MessageTypes.BIRTH_ALERT,
                    cow.farm,
                    cow,
                    f"Birth event notification for cow {cow.cow_id}:",
                )

                # Send WebSocket notifications to farmer and doctor
                farmer_ids = [cow.farm.user_id] if cow.farm.user_id else []
                doctor_ids = [cow.farm.doctor.user_id] if cow.farm.doctor and cow.farm.doctor.user_id else []
                all_user_ids = farmer_ids + doctor_ids
                if all_user_ids:
                    NotificationService.notify_calving(
                        cow_id=cow.id,
                        cow_name=cow.cow_id,
                        farm_name=cow.farm.farm_id,
                        farmer_user_ids=farmer_ids,
                        doctor_ids=doctor_ids,
                    )

                self.log_operation_success(
                    "recorded birth event", f"for cow {cow.cow_id}"
                )

                response_data = ResponseService.success_response(
                    APIMessages.BIRTH_EVENT_RECORDED,
                    {
                        "cow_id": cow.cow_id,
                        "farm_id": cow.farm.farm_id,
                        "calving_date": validated_data["calving_date"],
                        "last_calving_date": validated_data["last_calving_date"],
                        "calf_sex": validated_data["calf_sex"],
                        "parity": cow.parity,
                    },
                )
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            self.log_operation_error("birth monitoring", e)
            error_response, error_status = ResponseService.error_response(
                APIMessages.FAILED_TO_RECORD_BIRTH
            )
            return Response(error_response, status=error_status)

    @action(detail=False, methods=["get"])
    def pregnancy_records(self, request):
        """Get pregnancy monitoring records"""
        farm_id = request.query_params.get("farm_id")
        cow_id = request.query_params.get("cow_id")

        if not farm_id:
            return Response(
                {"error": "farm_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Reproduction.objects.filter(
            farm__farm_id=farm_id, is_cow_pregnant=True
        )

        if cow_id:
            queryset = queryset.filter(cow__cow_id=cow_id)

        data = []
        for record in queryset:
            data.append(
                {
                    "farm_id": record.farm.farm_id,
                    "cow_id": record.cow.cow_id,
                    "pregnancy_date": record.pregnancy_date,
                    "expected_calving_date": record.calving_date,
                    "service_per_conception": record.cow.number_of_inseminations,
                    "lactation_number": record.cow.lactation_number,
                }
            )

        return Response(data)

    @action(detail=False, methods=["get"])
    def birth_records(self, request):
        """Get birth monitoring records"""
        farm_id = request.query_params.get("farm_id")
        cow_id = request.query_params.get("cow_id")

        if not farm_id:
            return Response(
                {"error": "farm_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Reproduction.objects.filter(
            farm__farm_id=farm_id, calving_date__isnull=False
        )

        if cow_id:
            queryset = queryset.filter(cow__cow_id=cow_id)

        data = []
        for record in queryset:
            data.append(
                {
                    "farm_id": record.farm.farm_id,
                    "cow_id": record.cow.cow_id,
                    "calving_date": record.calving_date,
                    "last_calving_date": record.cow.last_calving_date,
                    "parity": record.cow.parity,
                }
            )

        return Response(data)

    @action(detail=False, methods=["get"])
    def heat_sign_records(self, request):
        """Get heat sign records from Reproduction or InseminationRecord"""
        farm_id = request.query_params.get("farm_id")
        cow_id = request.query_params.get("cow_id")
        record_type = request.query_params.get("record_type", "all")  # Default to all

        if not farm_id:
            return Response(
                {"error": "farm_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = []

        if record_type in ["reproduction", "all"]:
            reproduction_queryset = Reproduction.objects.filter(
                farm__farm_id=farm_id, is_cow_pregnant=False
            ).order_by("-heat_sign_recorded_at")
            if cow_id:
                reproduction_queryset = reproduction_queryset.filter(cow__cow_id=cow_id)
            for record in reproduction_queryset:
                data.append(
                    {
                        "type": "reproduction",
                        "farm_id": record.farm.farm_id,
                        "cow_id": record.cow.cow_id,
                        "heat_sign_start": record.heat_sign_start,
                        "heat_signs_seen": record.heat_signs_seen,
                        "heat_sign_recorded_at": record.heat_sign_recorded_at,
                    }
                )

        if record_type in ["insemination", "all"]:
            insemination_queryset = InseminationRecord.objects.filter(
                farm__farm_id=farm_id
            ).order_by("-recorded_date")
            if cow_id:
                insemination_queryset = insemination_queryset.filter(cow__cow_id=cow_id)
            for record in insemination_queryset:
                data.append(
                    {
                        "type": "insemination",
                        "farm_id": record.farm.farm_id,
                        "cow_id": record.cow.cow_id,
                        "insemination_time": record.insemination_time,
                        "recorded_date": record.recorded_date,
                    }
                )

        return Response(data)

    @action(detail=False, methods=["get"])
    def medical_records(self, request):
        """Get medical assessment records"""
        farm_id = request.query_params.get("farm_id")
        cow_id = request.query_params.get("cow_id")
        record_type = request.query_params.get(
            "type", "all"
        )  # 'farmer' or 'doctor' or 'all'

        if not farm_id:
            return Response(
                {"error": "farm_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = []

        # Get farmer medical reports if requested
        if record_type in ["farmer", "all"]:
            farmer_reports = FarmerMedicalReport.objects.filter(farm__farm_id=farm_id)
            if cow_id:
                farmer_reports = farmer_reports.filter(cow__cow_id=cow_id)

            for report in farmer_reports:
                data.append(
                    {
                        "type": "farmer_report",
                        "farm_id": report.farm.farm_id,
                        "cow_id": report.cow.cow_id,
                        "reported_date": report.reported_date,
                        "sickness_description": report.sickness_description,
                        "is_reviewed": report.is_reviewed,
                        "reviewed_by": (
                            report.reviewed_by.name if report.reviewed_by else None
                        ),
                        "review_date": report.review_date,
                    }
                )

        # Get doctor medical assessments if requested
        if record_type in ["doctor", "all"]:
            assessments = MedicalAssessment.objects.filter(farm__farm_id=farm_id)
            if cow_id:
                assessments = assessments.filter(cow__cow_id=cow_id)

            for assessment in assessments:
                data.append(
                    {
                        "type": "doctor_assessment",
                        "farm_id": assessment.farm.farm_id,
                        "cow_id": assessment.cow.cow_id,
                        "assessment_date": assessment.assessment_date,
                        "assessed_by": assessment.assessed_by.name,
                        "is_cow_sick": assessment.is_cow_sick,
                        "sickness_type": assessment.sickness_type,
                        "general_health": assessment.general_health.name,
                        "udder_health": assessment.udder_health.name,
                        "mastitis": assessment.mastitis.name,
                        "has_lameness": assessment.has_lameness,
                        "body_condition_score": assessment.body_condition_score,
                        "reproductive_health": assessment.reproductive_health,
                        "metabolic_disease": assessment.metabolic_disease,
                        "is_cow_vaccinated": assessment.is_cow_vaccinated,
                        "vaccination_date": assessment.vaccination_date,
                        "vaccination_type": assessment.vaccination_type,
                        "has_deworming": assessment.has_deworming,
                        "deworming_date": assessment.deworming_date,
                        "deworming_type": assessment.deworming_type,
                        "diagnosis": assessment.diagnosis,
                        "treatment": assessment.treatment,
                        "prescription": assessment.prescription,
                        "next_assessment_date": assessment.next_assessment_date,
                    }
                )

        return Response(data)


