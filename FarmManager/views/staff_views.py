import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Inseminator, Doctor, Farm
from ..serializers import InseminatorSerializer, DoctorSerializer
from ..services import LoggingMixin
from ..permissions import AdminGetOnlyPermission
from AlertSystem.sendMesage import send_alert   # Note: this external import remains

logger = logging.getLogger(__name__)