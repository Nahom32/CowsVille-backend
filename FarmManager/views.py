"""
FarmManager Views - Decoupled module

This module re-exports all ViewSets from the views package for backward compatibility.
ViewSets are organized into:
- farm_views: FarmViewSet
- cow_views: CowViewSet
- message_views: MessageViewSet
- staff_views: InseminatorViewSet, DoctorViewSet
- choice_views: Choice model ViewSets
- model_views: FarmerMedicalReport, MedicalAssessment, InseminationRecord, Reproduction ViewSets
"""

from .views import (
    BreedTypeViewSet,
    CowViewSet,
    DoctorViewSet,
    FarmerMedicalReportViewSet,
    FarmViewSet,
    FeedingFrequencyViewSet,
    FloorTypeViewSet,
    GeneralHealthStatusViewSet,
    GynecologicalStatusViewSet,
    HousingTypeViewSet,
    InseminationRecordViewSet,
    InseminatorViewSet,
    MastitisStatusViewSet,
    MedicalAssessmentViewSet,
    MessageViewSet,
    ReproductionViewSet,
    UdderHealthStatusViewSet,
    WaterSourceViewSet,
)

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
