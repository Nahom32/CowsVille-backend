class NotificationEventType:
    HEAT_SIGN = "heat_sign"
    PREGNANCY_CONFIRMED = "pregnancy_confirmed"
    MEDICAL_REPORT = "medical_report"
    DOCTOR_ASSESSMENT = "doctor_assessment"
    INSEMINATION = "insemination"
    CALVING_BIRTH = "calving_birth"
    STAFF_CHANGED = "staff_changed"
    ALERT = "alert"

    CHOICES = [
        (HEAT_SIGN, "Heat Sign Detected"),
        (PREGNANCY_CONFIRMED, "Pregnancy Confirmed"),
        (MEDICAL_REPORT, "Medical Report Created"),
        (DOCTOR_ASSESSMENT, "Doctor Assessment Completed"),
        (INSEMINATION, "Insemination Recorded"),
        (CALVING_BIRTH, "Calving/Birth"),
        (STAFF_CHANGED, "Staff Changed"),
        (ALERT, "General Alert"),
    ]


class NotificationPriority:
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    CHOICES = [
        (LOW, "Low"),
        (NORMAL, "Normal"),
        (HIGH, "High"),
        (URGENT, "Urgent"),
    ]
