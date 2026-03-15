import logging

from django.db import transaction
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from ..models import (
    Cow, Reproduction, FarmerMedicalReport, MedicalAssessment, InseminationRecord,
    GeneralHealthStatus, UdderHealthStatus, MastitisStatus, Farm, Doctor
)
from ..serializers import (
    CowSerializer, CowCreateUpdateSerializer, ReproductionSerializer,
    FarmerMedicalReportSerializer, MedicalAssessmentSerializer,
    InseminationRecordSerializer, HeatSignRecordSerializer,
    MonitorPregnancySerializer, FarmerMedicalAssessmentSerializer,
    DoctorMedicalAssessmentSerializer, MonitorHeatSignSerializer,
    MonitorBirthSerializer
)
from ..constants import APIMessages, MessageTemplates, MessageTypes
from ..services import ValidationService, HealthService, MessagingService, ResponseService, LoggingMixin
from ..permissions import AdminGetOnlyPermission

logger = logging.getLogger(__name__)