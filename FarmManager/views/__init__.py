from .choice_views import (
    BreedTypeViewSet,
    FeedingFrequencyViewSet,
    FloorTypeViewSet,
    GeneralHealthStatusViewSet,
    GynecologicalStatusViewSet,
    HousingTypeViewSet,
    MastitisStatusViewSet,
    UdderHealthStatusViewSet,
    WaterSourceViewSet,
)
from .cow_views import CowViewSet
from .farm_views import FarmViewSet
from .message_views import MessageViewSet
from .model_views import (
    FarmerMedicalReportViewSet,
    InseminationRecordViewSet,
    MedicalAssessmentViewSet,
    ReproductionViewSet,
)
from .staff_views import DoctorViewSet, InseminatorViewSet

__all__ = [
    "FarmViewSet",
    "CowViewSet",
    "MessageViewSet",
    "InseminatorViewSet",
    "DoctorViewSet",
    "ReproductionViewSet",
    "BreedTypeViewSet",
    "HousingTypeViewSet",
    "FloorTypeViewSet",
    "FeedingFrequencyViewSet",
    "WaterSourceViewSet",
    "GynecologicalStatusViewSet",
    "UdderHealthStatusViewSet",
    "MastitisStatusViewSet",
    "GeneralHealthStatusViewSet",
    "FarmerMedicalReportViewSet",
    "MedicalAssessmentViewSet",
    "InseminationRecordViewSet",
]
