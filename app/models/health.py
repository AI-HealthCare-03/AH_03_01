from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.users import User


class RecordType(StrEnum):
    WEIGHT = "WEIGHT"
    WAIST = "WAIST"
    BLOOD_PRESSURE = "BLOOD_PRESSURE"
    BLOOD_GLUCOSE = "BLOOD_GLUCOSE"
    HBA1C = "HBA1C"
    ACTIVITY = "ACTIVITY"


class RecordSubType(StrEnum):
    HOME = "HOME"
    HOSPITAL = "HOSPITAL"
    FASTING = "FASTING"
    POSTMEAL = "POSTMEAL"


class RecordSource(StrEnum):
    MANUAL = "MANUAL"
    WEARABLE = "WEARABLE"
    OCR = "OCR"


class AlcoholIntake(StrEnum):
    NONE = "NONE"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


class PregnancyHistory(StrEnum):
    NONE = "NONE"
    PREGNANT = "PREGNANT"
    POSTPARTUM = "POSTPARTUM"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DiseaseType(StrEnum):
    DIABETES = "DIABETES"
    HYPERTENSION = "HYPERTENSION"
    CARDIOVASCULAR = "CARDIOVASCULAR"


class RiskLevel(StrEnum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    RISK = "RISK"
    HIGH_RISK = "HIGH_RISK"


class UserHealthInfo(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.OneToOneRelation["User"] = fields.OneToOneField(
        "models.User", related_name="health_info", on_delete=fields.CASCADE
    )
    height_cm = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    weight_kg = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    waist_cm = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    is_smoker = fields.BooleanField(default=False)
    alcohol_intake = fields.CharEnumField(enum_type=AlcoholIntake, default=AlcoholIntake.NONE)
    pregnancy_history = fields.CharEnumField(enum_type=PregnancyHistory, default=PregnancyHistory.NOT_APPLICABLE)
    has_diabetes_family_history = fields.BooleanField(default=False)
    has_hypertension_family_history = fields.BooleanField(default=False)
    is_chronic_patient = fields.BooleanField(default=False)
    diseases: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    medications: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_health_info"


class HealthRecord(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="health_records", on_delete=fields.CASCADE
    )
    record_type = fields.CharEnumField(enum_type=RecordType)
    sub_type = fields.CharEnumField(enum_type=RecordSubType, null=True)
    primary_value = fields.DecimalField(max_digits=8, decimal_places=2)
    secondary_value = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    unit = fields.CharField(max_length=16)
    measured_at = fields.DatetimeField()
    source = fields.CharEnumField(enum_type=RecordSource, default=RecordSource.MANUAL)
    note = fields.TextField(null=True)
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_records"
        indexes = [("user_id", "record_type", "measured_at")]


class HealthReference(models.Model):
    id = fields.BigIntField(primary_key=True)
    record_type = fields.CharEnumField(enum_type=RecordType)
    sub_type = fields.CharEnumField(enum_type=RecordSubType, null=True)
    gender = fields.CharField(max_length=10, null=True)
    age_group_min = fields.SmallIntField(null=True)
    age_group_max = fields.SmallIntField(null=True)
    normal_min = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    normal_max = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    caution_min = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    caution_max = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    danger_min = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    avg_value = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    source = fields.CharField(max_length=64, null=True)

    class Meta:
        table = "health_references"
        unique_together = (("record_type", "sub_type", "gender", "age_group_min", "age_group_max"),)


class DiseaseRiskGuideline(models.Model):
    id = fields.BigIntField(primary_key=True)
    disease_type = fields.CharEnumField(enum_type=DiseaseType)
    risk_level = fields.CharEnumField(enum_type=RiskLevel)
    level_label = fields.CharField(max_length=40)
    condition_desc = fields.TextField()
    recommendation = fields.TextField()
    lifestyle_tips: list[Any] = fields.JSONField(default=list)  # type: ignore[assignment]
    hospital_visit_recommended = fields.BooleanField(default=False)
    disclaimer = fields.TextField(default="본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다.")

    class Meta:
        table = "disease_risk_guidelines"
        unique_together = (("disease_type", "risk_level"),)


class DiseaseRisk(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="disease_risks", on_delete=fields.CASCADE
    )
    disease_type = fields.CharEnumField(enum_type=DiseaseType)
    risk_score = fields.DecimalField(max_digits=5, decimal_places=2)
    risk_level = fields.CharEnumField(enum_type=RiskLevel)
    contributing_factors: list[dict[str, Any]] = fields.JSONField(default=list)  # type: ignore[assignment]
    input_snapshot: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    model_version = fields.CharField(max_length=40, default="rule-v1")
    guideline: fields.ForeignKeyNullableRelation["DiseaseRiskGuideline"] = fields.ForeignKeyField(
        "models.DiseaseRiskGuideline",
        related_name="risk_results",
        null=True,
        on_delete=fields.SET_NULL,
    )
    guideline_id: int | None
    calculated_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "disease_risks"
        indexes = [("user_id", "disease_type", "calculated_at")]


class MonthlyReport(models.Model):
    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="monthly_reports", on_delete=fields.CASCADE
    )
    year_month = fields.CharField(max_length=7)
    disease_risk_summary: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    health_data_summary: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    challenge_summary: dict[str, Any] = fields.JSONField(default=dict)  # type: ignore[assignment]
    pdf_file_id = fields.BigIntField(null=True)
    generated_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "monthly_reports"
        unique_together = (("user", "year_month"),)
