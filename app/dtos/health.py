from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.dtos.base import BaseSerializerModel
from app.models.health import (
    BpMeasureEnv,
    DiseaseType,
    PregnancyStatus,
    RecordSource,
    RecordSubType,
    RecordType,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Health profile (USER_HEALTH_INFO)
# ---------------------------------------------------------------------------


class HealthProfileUpsertRequest(BaseModel):
    # 수치형
    height_cm: Annotated[Decimal | None, Field(None, ge=50, le=250)]
    weight_kg: Annotated[Decimal | None, Field(None, ge=20, le=300)]
    waist_cm: Annotated[Decimal | None, Field(None, ge=30, le=200)]
    systolic_bp: Annotated[Decimal | None, Field(None, ge=50, le=300)]
    diastolic_bp: Annotated[Decimal | None, Field(None, ge=30, le=200)]
    fasting_blood_sugar: Annotated[Decimal | None, Field(None, ge=20, le=600)]
    sleep_weekday: Annotated[Decimal | None, Field(None, ge=0, le=24)]
    sleep_weekend: Annotated[Decimal | None, Field(None, ge=0, le=24)]
    moderate_exercise_hour: Annotated[Decimal | None, Field(None, ge=0, le=24)]
    smoking_risk: Annotated[Decimal | None, Field(None, ge=0, le=1)]
    # 정수형 (활동/식습관/물)
    mid_act_day: Annotated[int | None, Field(None, ge=0, le=7)]
    walk_day: Annotated[int | None, Field(None, ge=0, le=7)]
    water_count: Annotated[int | None, Field(None, ge=0, le=50)]
    # 가족력: 1=있음 / 0=없음 / -1=모름
    family_dm: Annotated[int | None, Field(None, ge=-1, le=1)]
    family_hp: Annotated[int | None, Field(None, ge=-1, le=1)]
    family_hl: Annotated[int | None, Field(None, ge=-1, le=1)]
    # 흡연: 현재흡연 1 / 비흡연 0
    current_smoker: Annotated[int | None, Field(None, ge=0, le=1)]
    # 음주 (KNHANES 코드)
    alcohol_freq_y: Annotated[int | None, Field(None, ge=-1, le=7)]
    alcohol_cup: Annotated[int | None, Field(None, ge=0, le=100)]
    # 식습관 (KNHANES 빈도 코드)
    fruit_freq: Annotated[int | None, Field(None, ge=0, le=99)]
    veg_freq_1: Annotated[int | None, Field(None, ge=0, le=99)]
    out_meal_freq: Annotated[int | None, Field(None, ge=0, le=99)]
    breakfast_freq: Annotated[int | None, Field(None, ge=0, le=99)]
    # 폐경 / 호르몬: 폐경 1 / 비폐경여성 0 / 남성·비해당 -1
    is_menopause: Annotated[int | None, Field(None, ge=-1, le=1)]
    ocp_total_months: Annotated[int | None, Field(None, ge=0, le=1200)]
    # 빈혈: 1=있음 / 0=없음 / -1=모름 (가족력·폐경과 동일하게 모름 허용)
    anemia: Annotated[int | None, Field(None, ge=-1, le=1)]
    # 예측 미사용 · 권고/챗봇용 프로필
    chronic_diseases: list[str] | None = None
    medications: list[str] | None = None
    pregnancy_status: PregnancyStatus | None = None
    bp_measure_env: BpMeasureEnv | None = None


class ProfileCompleteness(BaseModel):
    percent: int
    filled: int
    total: int
    missing_fields: list[str]
    complete: bool


class HealthProfileResponse(BaseSerializerModel):
    height_cm: Decimal | None
    weight_kg: Decimal | None
    waist_cm: Decimal | None
    systolic_bp: Decimal | None
    diastolic_bp: Decimal | None
    fasting_blood_sugar: Decimal | None
    sleep_weekday: Decimal | None
    sleep_weekend: Decimal | None
    moderate_exercise_hour: Decimal | None
    smoking_risk: Decimal | None
    mid_act_day: int | None
    walk_day: int | None
    water_count: int | None
    family_dm: int | None
    family_hp: int | None
    family_hl: int | None
    current_smoker: int | None
    alcohol_freq_y: int | None
    alcohol_cup: int | None
    fruit_freq: int | None
    veg_freq_1: int | None
    out_meal_freq: int | None
    breakfast_freq: int | None
    is_menopause: int | None
    ocp_total_months: int | None
    anemia: int | None
    chronic_diseases: list[str]
    medications: list[str]
    pregnancy_status: PregnancyStatus | None
    bp_measure_env: BpMeasureEnv | None
    updated_at: datetime
    completeness: ProfileCompleteness | None = None


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
            None,
        ):
            raise ValueError("혈당의 sub_type 은 FASTING 이어야 합니다.")
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


class MonthlyReportHeaderStats(BaseModel):
    """리포트 상단 요약 통계 (해당 월). 수집 불가 항목은 null."""

    recorded_days: int  # 해당 월 건강기록이 1건 이상 존재하는 distinct 날짜 수
    avg_sleep_hours: float | None = None  # 평균 수면시간(h). SLEEP 레코드 평균 → 없으면 프로필 sleep_weekday
    avg_steps: float | None = None  # 평균 걸음 수. ACTIVITY 레코드 평균 → 없으면 null


class MonthlyReportRiskFactor(BaseModel):
    """위험도 판단근거 1건 (DiseaseRisk.contributing_factors 의 한 항목)."""

    factor: str
    weight: float
    name_kor: str | None = None  # ML 한글명 (없으면 factor 로 폴백 표기 권장)
    direction: str | None = None  # "위험 증가↑" / "위험 감소↓"
    description: str | None = None


class MonthlyReportDiseaseRisk(BaseModel):
    """질환별 최신 위험도 + 판단근거 TOP5."""

    disease_type: DiseaseType
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    risk_level_label: str | None = None  # 5단계 한글 라벨
    calculated_at: datetime | None = None
    has_prediction: bool = False  # 해당 월 예측 존재 여부 (없으면 위 필드 모두 null)
    top_factors: list[MonthlyReportRiskFactor] = Field(default_factory=list)


class MonthlyReportTrendPoint(BaseModel):
    """추이 시계열 1점."""

    date: date  # 측정일 (Asia/Seoul 기준)
    value: float
    secondary_value: float | None = None  # 혈압 이완기 등


class MonthlyReportTrend(BaseModel):
    """건강지표 추이 (해당 월 일자별)."""

    metric: str  # blood_pressure | blood_glucose | weight
    unit: str | None = None
    series: list[MonthlyReportTrendPoint] = Field(default_factory=list)
    avg: float | None = None  # primary_value 평균
    latest: float | None = None  # 최근값(primary)
    secondary_avg: float | None = None  # 혈압 이완기 평균
    secondary_latest: float | None = None


class MonthlyReportChallenge(BaseModel):
    """챌린지 수행 내역 1건 (해당 월 참여 기준)."""

    challenge_id: int
    title: str
    category: str
    status: str  # success | in_progress | failed
    progress_percent: int  # 0~100
    success_days: int  # 인증 성공 일수
    goal_days: int  # 목표 일수(챌린지 기간 일수, 0 가능)


class MonthlyReportGoodHabit(BaseModel):
    """데이터로 도출한 '잘 지킨 습관' (중립 톤, 근거 수치 포함)."""

    key: str  # walking | hydration | sleep | diet | exercise ...
    label: str  # 한글 표기
    evidence: str  # 근거 문구(수치 포함)


class MonthlyReportResponse(BaseModel):
    year_month: str  # monthly: "YYYY-MM" / custom: "YYYY-MM-DD~YYYY-MM-DD" (표시용 라벨)
    period: str = "monthly"  # "monthly" | "custom" (임의 기간)
    date_from: date | None = None  # 집계 기간 시작(양끝 포함). 두 모드 모두 채움
    date_to: date | None = None  # 집계 기간 끝(양끝 포함)
    disease_risk_summary: dict[str, Any]
    health_data_summary: dict[str, Any]
    challenge_summary: dict[str, Any]
    # ── 참고 디자인 적응 구조화 섹션 (Phase 1 백엔드 데이터) ──────────────────
    header_stats: MonthlyReportHeaderStats | None = None
    disease_risks: list[MonthlyReportDiseaseRisk] = Field(default_factory=list)
    trends: list[MonthlyReportTrend] = Field(default_factory=list)
    challenges: list[MonthlyReportChallenge] = Field(default_factory=list)
    good_habits: list[MonthlyReportGoodHabit] = Field(default_factory=list)
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
    name_kor: str | None = None  # 한글명 (ML 경로; 룰 폴백은 None → UI 는 description 사용)
    direction: str | None = None  # "위험 증가↑"/"위험 감소↓"


class PredictionResponse(BaseSerializerModel):
    id: int
    disease_type: DiseaseType
    risk_score: Decimal
    risk_level: RiskLevel
    risk_level_label: str  # risk_score 기반 5단계 한글 라벨 (DiseaseRisk.risk_level_label @property 파생)
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
