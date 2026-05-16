from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.dtos.base import BaseSerializerModel
from app.models.health import (
    AlcoholIntake,
    DiseaseType,
    PregnancyHistory,
    RecordSource,
    RecordSubType,
    RecordType,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Health profile (USER_HEALTH_INFO)
# ---------------------------------------------------------------------------


class HealthProfileUpsertRequest(BaseModel):
    height_cm: Annotated[Decimal | None, Field(None, ge=50, le=250)]
    weight_kg: Annotated[Decimal | None, Field(None, ge=20, le=300)]
    waist_cm: Annotated[Decimal | None, Field(None, ge=30, le=200)]
    is_smoker: bool | None = None
    alcohol_intake: AlcoholIntake | None = None
    pregnancy_history: PregnancyHistory | None = None
    has_diabetes_family_history: bool | None = None
    has_hypertension_family_history: bool | None = None
    is_chronic_patient: bool | None = None
    diseases: list[str] | None = None
    medications: list[str] | None = None


class HealthProfileResponse(BaseSerializerModel):
    height_cm: Decimal | None
    weight_kg: Decimal | None
    waist_cm: Decimal | None
    is_smoker: bool
    alcohol_intake: AlcoholIntake
    pregnancy_history: PregnancyHistory
    has_diabetes_family_history: bool
    has_hypertension_family_history: bool
    is_chronic_patient: bool
    diseases: list[str]
    medications: list[str]
    updated_at: datetime


# ---------------------------------------------------------------------------
# Health record (HEALTH_RECORD)
# ---------------------------------------------------------------------------


class HealthRecordCreateRequest(BaseModel):
    record_type: RecordType
    sub_type: RecordSubType | None = None
    primary_value: Annotated[Decimal, Field(ge=0)]
    secondary_value: Annotated[Decimal | None, Field(None, ge=0)]
    unit: Annotated[str, Field(min_length=1, max_length=16)]
    measured_at: datetime
    source: RecordSource = RecordSource.MANUAL
    note: Annotated[str | None, Field(None, max_length=500)]

    @model_validator(mode="after")
    def _validate_subtype(self) -> "HealthRecordCreateRequest":
        if self.record_type == RecordType.BLOOD_PRESSURE:
            if self.secondary_value is None:
                raise ValueError("혈압 기록은 이완기(secondary_value)가 필요합니다.")
            if self.sub_type not in (RecordSubType.HOME, RecordSubType.HOSPITAL, None):
                raise ValueError("혈압의 sub_type 은 HOME 또는 HOSPITAL 이어야 합니다.")
        if self.record_type == RecordType.BLOOD_GLUCOSE and self.sub_type not in (
            RecordSubType.FASTING,
            RecordSubType.POSTMEAL,
            None,
        ):
            raise ValueError("혈당의 sub_type 은 FASTING 또는 POSTMEAL 이어야 합니다.")
        return self


class HealthRecordUpdateRequest(BaseModel):
    sub_type: RecordSubType | None = None
    primary_value: Annotated[Decimal | None, Field(None, ge=0)]
    secondary_value: Annotated[Decimal | None, Field(None, ge=0)]
    unit: Annotated[str | None, Field(None, min_length=1, max_length=16)]
    measured_at: datetime | None = None
    note: Annotated[str | None, Field(None, max_length=500)]


class HealthRecordResponse(BaseSerializerModel):
    id: int
    record_type: RecordType
    sub_type: RecordSubType | None
    primary_value: Decimal
    secondary_value: Decimal | None
    unit: str
    measured_at: datetime
    source: RecordSource
    note: str | None
    created_at: datetime
    updated_at: datetime


class HealthRecordListResponse(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    items: list[HealthRecordResponse]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class StatisticsPoint(BaseModel):
    measured_at: datetime
    primary_value: Decimal
    secondary_value: Decimal | None = None
    sub_type: RecordSubType | None = None
    level: str | None = None


class ReferenceRange(BaseModel):
    normal: dict[str, Decimal | None] | None = None
    caution: dict[str, Decimal | None] | None = None
    danger: dict[str, Decimal | None] | None = None
    avg_value: Decimal | None = None
    source: str | None = None


class StatisticsResponse(BaseModel):
    metric: str
    period: str | None = None
    sub_type: str | None = None
    data_count: int
    insufficient_data: bool = False
    series: list[StatisticsPoint]
    reference_range: ReferenceRange | None = None
    peer_average: Decimal | None = None


# ---------------------------------------------------------------------------
# Monthly report
# ---------------------------------------------------------------------------


class MonthlyReportResponse(BaseModel):
    year_month: str
    disease_risk_summary: dict[str, Any]
    health_data_summary: dict[str, Any]
    challenge_summary: dict[str, Any]
    pdf_url: str | None = None
    generated_at: datetime


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------


class PredictionCreateRequest(BaseModel):
    health_record_id: int | None = None
    input_snapshot: dict[str, Any] | None = None


class ContributingFactor(BaseModel):
    factor: str
    weight: float
    description: str | None = None


class PredictionResponse(BaseSerializerModel):
    id: int
    disease_type: DiseaseType
    risk_score: Decimal
    risk_level: RiskLevel
    contributing_factors: list[ContributingFactor]
    model_version: str
    calculated_at: datetime
    disclaimer: str = "본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다."


class PredictionListResponse(BaseModel):
    items: list[PredictionResponse]


class RiskRecommendationItem(BaseModel):
    category: str
    content: str
    evidence: str | None = None


class RiskRecommendationResponse(BaseModel):
    prediction_id: int
    disease_type: DiseaseType
    risk_level: RiskLevel
    level_label: str
    condition_desc: str
    recommendations: list[RiskRecommendationItem]
    hospital_visit_recommended: bool
    disclaimer: str


class ExplanationResponse(BaseModel):
    prediction_id: int
    disease_type: DiseaseType
    visualization: str
    risk_factors: list[ContributingFactor]
    charts: list[dict[str, Any]]
    recommendations: list[RiskRecommendationItem]
    disclaimer: str = "본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다."
