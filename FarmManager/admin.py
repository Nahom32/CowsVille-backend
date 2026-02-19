from django.contrib import admin

from .models import (BreedType, Cow, Doctor, Farm, FarmerMedicalReport,
                     FeedingFrequency, FloorType, GeneralHealthStatus,
                     GynecologicalStatus, HousingType, InseminationRecord,
                     Inseminator, MastitisStatus, MedicalAssessment, Message,
                     Reproduction, UdderHealthStatus, WaterSource)

# from unfold.admin import ModelAdmin


# --- Base Admin for Soft Delete Models ---
class SoftDeleteAdmin(admin.ModelAdmin):
    """Base admin class for models using SoftDeleteModel.
    Shows all records (including soft-deleted), adds is_deleted to display/filter,
    and provides bulk hard-delete and restore actions.
    """
    select_related_fields = []

    def get_queryset(self, request):
        """Show all records including soft-deleted ones"""
        return self.model.objects.all_with_deleted().select_related(
            *self.select_related_fields
        )

    def get_list_display(self, request):
        """Append is_deleted to list_display"""
        base = list(super().get_list_display(request))
        if "is_deleted" not in base:
            base.append("is_deleted")
        return base

    def get_list_filter(self, request):
        """Append is_deleted to list_filter"""
        base = list(super().get_list_filter(request))
        if "is_deleted" not in base:
            base.append("is_deleted")
        return base

    @admin.action(description="Hard delete selected (permanent)")
    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        for obj in queryset:
            obj.hard_delete()
        self.message_user(request, f"Permanently deleted {count} record(s).")

    @admin.action(description="Restore selected (undo soft delete)")
    def restore_selected(self, request, queryset):
        count = queryset.filter(is_deleted=True).update(is_deleted=False)
        self.message_user(request, f"Restored {count} record(s).")

    actions = ["hard_delete_selected", "restore_selected"]


@admin.register(Farm)
class FarmAdmin(SoftDeleteAdmin):
    list_display = (
        "farm_id",
        "owner_name",
        "telephone_number",
        "doctor",
        "inseminator",
    )
    search_fields = ("farm_id", "owner_name", "address")
    list_filter = ("type_of_housing", "type_of_floor", "source_of_water")
    select_related_fields = [
        "doctor", "inseminator", "type_of_housing",
        "type_of_floor", "source_of_water",
    ]


@admin.register(Cow)
class CowAdmin(SoftDeleteAdmin):
    list_display = ("cow_id", "farm", "breed", "date_of_birth", "sex")
    search_fields = ("cow_id", "farm__farm_id")
    list_filter = ("breed", "sex", "gynecological_status")
    select_related_fields = ["farm", "breed", "gynecological_status"]


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "is_active", "license_number")
    search_fields = ("name", "phone_number", "license_number")
    list_filter = ("is_active",)


@admin.register(Inseminator)
class InseminatorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "is_active")
    search_fields = ("name", "phone_number")
    list_filter = ("is_active",)


@admin.register(Message)
class MessageAdmin(SoftDeleteAdmin):
    list_display = ("farm", "cow", "message_type", "sent_date", "is_sent")
    search_fields = ("farm__farm_id", "cow__cow_id", "message_text")
    list_filter = ("message_type", "is_sent", "sent_date")
    select_related_fields = ["farm", "cow"]


@admin.register(MedicalAssessment)
class MedicalAssessmentAdmin(SoftDeleteAdmin):
    list_display = ("farm", "cow", "assessed_by", "assessment_date", "is_cow_sick")
    search_fields = ("farm__farm_id", "cow__cow_id", "assessed_by__name")
    list_filter = ("is_cow_sick", "sickness_type", "is_cow_vaccinated", "has_deworming")
    date_hierarchy = "assessment_date"
    select_related_fields = [
        "farm", "cow", "assessed_by", "general_health", "udder_health", "mastitis",
    ]


@admin.register(InseminationRecord)
class InseminationRecordAdmin(SoftDeleteAdmin):
    list_display = ("farm", "cow", "inseminator", "is_inseminated", "recorded_date")
    search_fields = ("farm__farm_id", "cow__cow_id", "inseminator__name")
    list_filter = ("is_inseminated",)
    date_hierarchy = "recorded_date"
    select_related_fields = ["farm", "cow", "inseminator"]


@admin.register(FarmerMedicalReport)
class FarmerMedicalReportAdmin(SoftDeleteAdmin):
    list_display = ("farm", "cow", "reported_date", "is_reviewed")
    search_fields = ("farm__farm_id", "cow__cow_id", "sickness_description")
    list_filter = ("is_reviewed",)
    date_hierarchy = "reported_date"
    select_related_fields = ["farm", "cow", "reviewed_by"]


@admin.register(Reproduction)
class ReproductionAdmin(SoftDeleteAdmin):
    list_display = (
        "cow",
        "farm",
        "is_cow_pregnant",
        "pregnancy_date",
        "calving_date",
        "heat_sign_recorded_at",
    )
    search_fields = ("cow__cow_id", "farm__farm_id")
    list_filter = ("is_cow_pregnant", "calving_date")
    select_related_fields = ["farm", "cow"]


# Register choice models
admin.site.register(BreedType)
admin.site.register(HousingType)
admin.site.register(FloorType)
admin.site.register(FeedingFrequency)
admin.site.register(WaterSource)
admin.site.register(GynecologicalStatus)
admin.site.register(UdderHealthStatus)
admin.site.register(MastitisStatus)
admin.site.register(GeneralHealthStatus)
