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
    ACTIVITY = "ACTIVITY"
    SLEEP = "SLEEP"
    WATER = "WATER"


class RecordSubType(StrEnum):
    HOME = "HOME"
    HOSPITAL = "HOSPITAL"
    FASTING = "FASTING"


class RecordSource(StrEnum):
    MANUAL = "MANUAL"
    WEARABLE = "WEARABLE"
    OCR = "OCR"


class PregnancyStatus(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PREGNANT = "PREGNANT"
    POSTPARTUM = "POSTPARTUM"


class BpMeasureEnv(StrEnum):
    HOME = "HOME"
    HOSPITAL = "HOSPITAL"


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
    """유저당 1행 프로필 (최신값 upsert).

    수치형 컬럼은 시계열(HealthRecord)과 병행 유지한다 — 예측 서비스는 이 행에서 직접 읽는다.
    카테고리/파생 컬럼은 이 행에만 존재한다.

    KNHANES 예측 모델 CORE_INPUT_VARS 컬럼→키 매핑 (snake_case DB → 예측 서비스 키):
        height_cm           → height_cm
        weight_kg           → weight_kg
        waist_cm            → waist_cm
        systolic_bp         → systolic_bp
        diastolic_bp        → diastolic_bp
        fasting_blood_sugar → fasting_blood_sugar
        family_dm           → FAMILY_DM
        family_hp           → FAMILY_HP
        family_hl           → FAMILY_HL
        current_smoker      → CURRENT_SMOKER
        smoking_risk        → smoking_risk
        alcohol_freq_y      → alcohol_freq_y
        alcohol_cup         → alcohol_cup
        sleep_weekday       → SLEEP_WEEKDAY
        sleep_weekend       → SLEEP_WEEKEND
        mid_act_day         → mid_act_day
        moderate_exercise_hour → MODERATE_EXERCISE_HOUR
        walk_day            → walk_day
        fruit_freq          → fruit_freq
        veg_freq_1          → veg_freq_1
        out_meal_freq       → out_meal_freq
        breakfast_freq      → breakfast_freq
        water_count         → water_count
        is_menopause        → is_menopause
        ocp_total_months    → ocp_total_months
        anemia              → anemia
        (age / sex 는 User 테이블에서 직접 조회)
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.OneToOneRelation["User"] = fields.OneToOneField(
        "models.User", related_name="health_info", on_delete=fields.CASCADE
    )

    # ── 수치형 (시계열 HealthRecord와 병행) ──────────────────────────────────
    height_cm = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    weight_kg = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    waist_cm = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    systolic_bp = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    diastolic_bp = fields.DecimalField(max_digits=5, decimal_places=1, null=True)
    fasting_blood_sugar = fields.DecimalField(max_digits=6, decimal_places=1, null=True)
    sleep_weekday = fields.DecimalField(max_digits=4, decimal_places=2, null=True)  # 시간 단위 (예: 6.50)
    sleep_weekend = fields.DecimalField(max_digits=4, decimal_places=2, null=True)
    moderate_exercise_hour = fields.DecimalField(max_digits=4, decimal_places=2, null=True)  # 1회 운동시간(h)
    mid_act_day = fields.SmallIntField(null=True)  # 주당 중강도 운동 일수 (KNHANES BE3_86)
    walk_day = fields.SmallIntField(null=True)  # 주당 걷기 일수 (KNHANES BE3_31, 단위: 일)
    water_count = fields.SmallIntField(null=True)  # 하루 물 섭취 컵 수 (KNHANES N_WAT_C)

    # ── 가족력: 1=있음 / 0=없음 / -1=모름 ────────────────────────────────────
    family_dm = fields.SmallIntField(null=True)  # 당뇨 가족력 → FAMILY_DM
    family_hp = fields.SmallIntField(null=True)  # 고혈압 가족력 → FAMILY_HP
    family_hl = fields.SmallIntField(null=True)  # 고지혈증 가족력 → FAMILY_HL

    # ── 흡연 ─────────────────────────────────────────────────────────────────
    # current_smoker: 현재흡연=1 / 비흡연=0  → CURRENT_SMOKER
    # smoking_risk: 현재흡연=1.0 / 과거흡연=0.5 / 무경험=0.0  → smoking_risk
    current_smoker = fields.SmallIntField(null=True)
    smoking_risk = fields.DecimalField(max_digits=3, decimal_places=1, null=True)

    # ── 음주 (KNHANES 코드 그대로 저장) ─────────────────────────────────────
    # alcohol_freq_y: 연간 음주 빈도 코드 (BD1_11: 1=거의매일 … 7=전혀안함, -1=모름)
    # alcohol_cup: 1회 평균 음주량 잔 수 (BD2_1)
    alcohol_freq_y = fields.SmallIntField(null=True)
    alcohol_cup = fields.SmallIntField(null=True)

    # ── 식습관 (KNHANES 코드 그대로 저장) ───────────────────────────────────
    # fruit_freq / veg_freq_1 / out_meal_freq / breakfast_freq: KNHANES 빈도 코드
    fruit_freq = fields.SmallIntField(null=True)
    veg_freq_1 = fields.SmallIntField(null=True)
    out_meal_freq = fields.SmallIntField(null=True)
    breakfast_freq = fields.SmallIntField(null=True)

    # ── 폐경 / 호르몬 ────────────────────────────────────────────────────────
    # is_menopause: 폐경=1 / 비폐경(여성)=0 / 남성/비해당=-1  → is_menopause
    # ocp_total_months: 경구피임약 총 복용 개월 수  → ocp_total_months
    is_menopause = fields.SmallIntField(null=True)
    ocp_total_months = fields.SmallIntField(null=True)

    # ── 기타 건강 지표 ────────────────────────────────────────────────────────
    anemia = fields.SmallIntField(null=True)  # 빈혈: 1=있음 / 0=없음  → anemia

    # ── 예측 미사용 · 권고/챗봇용 프로필 ─────────────────────────────────────
    chronic_diseases: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    medications: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    pregnancy_status = fields.CharEnumField(
        enum_type=PregnancyStatus, default=PregnancyStatus.NOT_APPLICABLE, null=True
    )
    bp_measure_env = fields.CharEnumField(enum_type=BpMeasureEnv, null=True)  # 혈압측정환경

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
