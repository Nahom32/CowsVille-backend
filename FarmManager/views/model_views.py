from rest_framework import filters, viewsets

from ..models import FarmerMedicalReport, InseminationRecord, MedicalAssessment, Reproduction
from ..permissions import AdminGetOnlyPermission
from ..serializers import (
    FarmerMedicalReportSerializer, InseminationRecordSerializer,
    MedicalAssessmentSerializer, ReproductionSerializer
)


class FarmerMedicalReportViewSet(viewsets.ModelViewSet):
    queryset = FarmerMedicalReport.objects.select_related("farm", "cow", "reviewed_by")
    serializer_class = FarmerMedicalReportSerializer
    permission_classes = [AdminGetOnlyPermission]

    def get_queryset(self):
        queryset = FarmerMedicalReport.objects.select_related(
            "farm", "cow", "reviewed_by"
        )
        farm_id = self.request.query_params.get("farm_id", None)
        cow_id = self.request.query_params.get("cow_id", None)
        is_reviewed = self.request.query_params.get("is_reviewed", None)

        if farm_id:
            queryset = queryset.filter(farm__farm_id=farm_id)
        if cow_id:
            queryset = queryset.filter(cow__cow_id=cow_id)
        if is_reviewed is not None:
            queryset = queryset.filter(is_reviewed=is_reviewed)

        return queryset


class MedicalAssessmentViewSet(viewsets.ModelViewSet):
    queryset = MedicalAssessment.objects.select_related(
        "farm", "cow", "assessed_by", "general_health", "udder_health", "mastitis"
    )
    serializer_class = MedicalAssessmentSerializer
    permission_classes = [AdminGetOnlyPermission]

    def get_queryset(self):
        queryset = MedicalAssessment.objects.select_related(
            "farm", "cow", "assessed_by", "general_health", "udder_health", "mastitis"
        )
        farm_id = self.request.query_params.get("farm_id", None)
        cow_id = self.request.query_params.get("cow_id", None)
        doctor_id = self.request.query_params.get("doctor_id", None)
        is_cow_sick = self.request.query_params.get("is_cow_sick", None)

        if farm_id:
            queryset = queryset.filter(farm__farm_id=farm_id)
        if cow_id:
            queryset = queryset.filter(cow__cow_id=cow_id)
        if doctor_id:
            queryset = queryset.filter(assessed_by_id=doctor_id)
        if is_cow_sick is not None:
            queryset = queryset.filter(is_cow_sick=is_cow_sick)

        return queryset


class InseminationRecordViewSet(viewsets.ModelViewSet):
    queryset = InseminationRecord.objects.select_related("farm", "cow", "inseminator")
    serializer_class = InseminationRecordSerializer
    permission_classes = [AdminGetOnlyPermission]

    def get_queryset(self):
        queryset = InseminationRecord.objects.select_related(
            "farm", "cow", "inseminator"
        )
        farm_id = self.request.query_params.get("farm_id", None)
        cow_id = self.request.query_params.get("cow_id", None)
        inseminator_id = self.request.query_params.get("inseminator_id", None)
        is_inseminated = self.request.query_params.get("is_inseminated", None)

        if farm_id:
            queryset = queryset.filter(farm__farm_id=farm_id)
        if cow_id:
            queryset = queryset.filter(cow__cow_id=cow_id)
        if inseminator_id:
            queryset = queryset.filter(inseminator_id=inseminator_id)
        if is_inseminated is not None:
            queryset = queryset.filter(is_inseminated=is_inseminated)

        return queryset


class ReproductionViewSet(viewsets.ModelViewSet):
    queryset = Reproduction.objects.select_related("cow", "farm")
    serializer_class = ReproductionSerializer
    permission_classes = [AdminGetOnlyPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["cow__cow_id", "farm__farm_id"]

    def get_queryset(self):
        queryset = Reproduction.objects.select_related("cow", "farm")
        farm_id = self.request.query_params.get("farm_id", None)
        cow_id = self.request.query_params.get("cow_id", None)
        is_pregnant = self.request.query_params.get("is_pregnant", None)

        if farm_id:
            queryset = queryset.filter(farm__farm_id=farm_id)
        if cow_id and farm_id:
            queryset = queryset.filter(cow__cow_id=cow_id)
        if is_pregnant is not None:
            queryset = queryset.filter(is_cow_pregnant=is_pregnant.lower() == "true")

        return queryset
