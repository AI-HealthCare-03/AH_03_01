from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.dtos.health import (
    HealthProfileUpsertRequest,
    HealthRecordCreateRequest,
    HealthRecordUpdateRequest,
    ProfileCompleteness,
    ReferenceRange,
    StatisticsPoint,
    StatisticsResponse,
)
from app.models.health import (
    DiseaseRisk,
    DiseaseType,
    HealthRecord,
    RecordSource,
    RecordSubType,
    RecordType,
    UserHealthInfo,
)
from app.models.users import Gender, User
from app.repositories.health_repository import (
    DiseaseRiskGuidelineRepository,
    DiseaseRiskRepository,
    HealthProfileRepository,
    HealthRecordRepository,
    HealthReferenceRepository,
    MonthlyReportRepository,
)
from app.services.ml import PredictionInput, RiskPredictor

HOME_BP_CORRECTION = Decimal("5")  # 가정 측정치 보정 (+5/+5)

# input_snapshot override 로 덮어쓸 수 없는 서버측 신뢰 필드 (요청 파라미터·User 에서 도출)
_SNAPSHOT_OVERRIDE_PROTECTED = frozenset({"disease_type", "age", "gender", "extra"})

# 위험도 예측 모델입력 필수 필드셋 (완성도 계산 + 예측 게이트 공용).
# "채워짐" = 값이 None 이 아님 (가족력 -1=모름도 채워진 것으로 인정).
# HealthProfileUpsertRequest / PredictionInput.snapshot() 의 모델입력 키와 정합.
# chronic_diseases/medications/pregnancy_status/bp_measure_env 는 모델입력이 아니므로 제외.
# age/gender 는 User(가입 시 존재)라 게이트 대상이 아님.
REQUIRED_PROFILE_FIELDS = (
    "height_cm",
    "weight_kg",
    "waist_cm",
    "systolic_bp",
    "diastolic_bp",
    "fasting_blood_sugar",
    "sleep_weekday",
    "sleep_weekend",
    "moderate_exercise_hour",
    "smoking_risk",
    "current_smoker",
    "mid_act_day",
    "walk_day",
    "water_count",
    "family_dm",
    "family_hp",
    "family_hl",
    "alcohol_freq_y",
    "alcohol_cup",
    "fruit_freq",
    "veg_freq_1",
    "out_meal_freq",
    "breakfast_freq",
    "anemia",
)
# user.gender == FEMALE 일 때만 필수에 포함. 남성/비해당이면 total·missing 에서 제외.
FEMALE_ONLY_PROFILE_FIELDS = (
    "is_menopause",
    "ocp_total_months",
)
# profile 값이 비어도 최신 일별 레코드로 충족 가능한 필드 (DiseaseRiskService._build_input 의
# 레코드→profile 폴백과 동일). 완성도 판정 시 profile OR 최신 레코드 둘 중 하나면 "채워짐".
RECORD_FALLBACK_FIELDS = frozenset({"weight_kg", "waist_cm", "systolic_bp", "diastolic_bp", "fasting_blood_sugar"})


class HealthProfileService:
    def __init__(self) -> None:
        self.repo = HealthProfileRepository()
        self.record_repo = HealthRecordRepository()

    async def get_or_init(self, user: User) -> UserHealthInfo:
        profile = await self.repo.get_by_user(user.id)
        if profile is None:
            profile = await self.repo.create(user.id, data={})
        return profile

    @staticmethod
    def required_fields_for(user: User) -> tuple[str, ...]:
        """성별 조건을 반영한 필수 필드셋."""
        if user.gender == Gender.FEMALE:
            return REQUIRED_PROFILE_FIELDS + FEMALE_ONLY_PROFILE_FIELDS
        return REQUIRED_PROFILE_FIELDS

    async def _record_satisfied_fields(self, user: User) -> set[str]:
        """profile 이 비어도 최신 일별 레코드로 충족되는 필드 집합.

        DiseaseRiskService._build_input 의 레코드→profile 폴백과 동일한 소스를 본다.
        """
        satisfied: set[str] = set()
        latest_weight = await self.record_repo.latest_value(user.id, RecordType.WEIGHT)
        if latest_weight and latest_weight.primary_value is not None:
            satisfied.add("weight_kg")
        latest_waist = await self.record_repo.latest_value(user.id, RecordType.WAIST)
        if latest_waist and latest_waist.primary_value is not None:
            satisfied.add("waist_cm")
        latest_bp = await self.record_repo.latest_value(user.id, RecordType.BLOOD_PRESSURE)
        if latest_bp and latest_bp.primary_value is not None:
            satisfied.add("systolic_bp")
        if latest_bp and latest_bp.secondary_value is not None:
            satisfied.add("diastolic_bp")
        latest_fasting = await self.record_repo.latest_value(user.id, RecordType.BLOOD_GLUCOSE, RecordSubType.FASTING)
        if latest_fasting and latest_fasting.primary_value is not None:
            satisfied.add("fasting_blood_sugar")
        return satisfied

    async def compute_completeness(self, profile: UserHealthInfo | None, user: User) -> ProfileCompleteness:
        """위험도 예측 모델입력 필드 기준 완성도 계산.

        - "채워짐" = profile 값이 None 이 아님 (가족력 -1=모름도 인정).
        - 단 RECORD_FALLBACK_FIELDS(혈압·혈당·체중·허리)는 최신 일별 레코드가 있으면 채워진 것으로 인정.
        - 여성은 is_menopause/ocp_total_months 를 필수에 포함, 남성/비해당은 제외.
        - profile 이 None 이어도 레코드로 일부 충족될 수 있어 레코드를 함께 조회한다.
        """
        required = self.required_fields_for(user)
        total = len(required)
        record_satisfied = await self._record_satisfied_fields(user)
        missing = []
        for field_name in required:
            profile_filled = profile is not None and getattr(profile, field_name, None) is not None
            if profile_filled or (field_name in RECORD_FALLBACK_FIELDS and field_name in record_satisfied):
                continue
            missing.append(field_name)
        filled = total - len(missing)
        percent = round(filled / total * 100) if total else 100
        return ProfileCompleteness(
            percent=percent,
            filled=filled,
            total=total,
            missing_fields=missing,
            complete=not missing,
        )

    async def upsert(self, user: User, data: HealthProfileUpsertRequest) -> UserHealthInfo:
        profile = await self.repo.get_by_user(user.id)
        payload = data.model_dump(exclude_unset=True)
        async with in_transaction():
            if profile is None:
                profile = await self.repo.create(user.id, payload)
            else:
                profile = await self.repo.update_instance(profile, payload)
        # Decimal 컬럼은 DB 정규화 결과(예: 175 → 175.0)를 반영해 응답하도록 refresh.
        await profile.refresh_from_db()
        return profile


class HealthRecordService:
    def __init__(self) -> None:
        self.repo = HealthRecordRepository()

    async def create(self, user: User, data: HealthRecordCreateRequest) -> HealthRecord:
        payload = data.model_dump()
        if (
            payload["record_type"] == RecordType.BLOOD_PRESSURE
            and payload.get("sub_type") == RecordSubType.HOME
            and payload.get("source") == RecordSource.MANUAL
        ):
            payload["primary_value"] = Decimal(str(payload["primary_value"])) + HOME_BP_CORRECTION
            payload["secondary_value"] = (
                Decimal(str(payload["secondary_value"])) + HOME_BP_CORRECTION
                if payload.get("secondary_value") is not None
                else None
            )
        async with in_transaction():
            record = await self.repo.create(user.id, payload)
        # 주간 활동량 EXP 적립 (HEALTH_INPUT, 1일 1회). best-effort.
        try:
            from app.models.experience import XpKind
            from app.services.experience import ExperienceService

            await ExperienceService().award(user_id=user.id, kind=XpKind.HEALTH_INPUT)
        except Exception:
            pass
        return record

    async def get_owned(self, user: User, record_id: int) -> HealthRecord:
        record = await self.repo.get_owned(record_id, user.id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="건강 기록을 찾을 수 없습니다.")
        return record

    async def list_records(
        self,
        user: User,
        record_type: RecordType | None,
        sub_type: RecordSubType | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        size: int,
    ) -> tuple[list[HealthRecord], int]:
        return await self.repo.list_records(
            user_id=user.id,
            record_type=record_type,
            sub_type=sub_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            size=size,
        )

    async def update(self, user: User, record_id: int, data: HealthRecordUpdateRequest) -> HealthRecord:
        record = await self.get_owned(user, record_id)
        async with in_transaction():
            return await self.repo.update_instance(record, data.model_dump(exclude_unset=True))

    async def delete(self, user: User, record_id: int) -> None:
        record = await self.get_owned(user, record_id)
        await self.repo.soft_delete(record)


class HealthStatisticsService:
    def __init__(self) -> None:
        self.record_repo = HealthRecordRepository()
        self.reference_repo = HealthReferenceRepository()

    _METRIC_MAP = {
        "weight": (RecordType.WEIGHT, None),
        "waist": (RecordType.WAIST, None),
        "blood_pressure": (RecordType.BLOOD_PRESSURE, None),
        "blood_glucose": (RecordType.BLOOD_GLUCOSE, None),
        "activity": (RecordType.ACTIVITY, None),
    }

    @classmethod
    def parse_metric(cls, metric: str) -> tuple[RecordType, RecordSubType | None]:
        key = (metric or "").lower()
        if key not in cls._METRIC_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 metric: {metric}",
            )
        return cls._METRIC_MAP[key]

    @staticmethod
    def _period_to_dates(period: str | None) -> tuple[date | None, date | None]:
        if period is None:
            return None, None
        today = datetime.now().date()
        mapping = {
            "weekly": 7,
            "1w": 7,
            "monthly": 30,
            "1m": 30,
            "3m": 90,
            "6m": 180,
        }
        days = mapping.get(period)
        if days is None:
            return None, None
        return today.fromordinal(today.toordinal() - days), today

    async def get_statistics(
        self,
        user: User,
        metric: str,
        period: str | None,
        sub_type_q: str | None,
        date_from: date | None,
        date_to: date | None,
        limit: int | None,
        include_reference: bool,
    ) -> StatisticsResponse:
        record_type, _ = self.parse_metric(metric)
        sub_type: RecordSubType | None = None
        if sub_type_q == RecordSubType.FASTING.value:
            sub_type = RecordSubType(sub_type_q)

        if date_from is None and date_to is None and period:
            date_from, date_to = self._period_to_dates(period)

        records = await self.record_repo.for_statistics(
            user_id=user.id,
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            sub_type=sub_type,
            limit=limit,
        )
        records.sort(key=lambda r: r.measured_at)

        if record_type == RecordType.BLOOD_GLUCOSE and sub_type_q == "both":
            series = self._merge_glucose(records)
        else:
            series = [self._point(record_type, r) for r in records]

        reference = None
        peer_avg = None
        if include_reference:
            ref = await self.reference_repo.lookup(
                record_type=record_type,
                sub_type=sub_type,
                gender=user.gender.value if user.gender else None,
                age=self._age(user.birthday),
            )
            if ref is not None:
                reference = ReferenceRange(
                    normal={"min": ref.normal_min, "max": ref.normal_max},
                    caution={"min": ref.caution_min, "max": ref.caution_max},
                    danger={"min": ref.danger_min, "max": None},
                    avg_value=ref.avg_value,
                    source=ref.source,
                )
                peer_avg = ref.avg_value

        insufficient = record_type == RecordType.BLOOD_PRESSURE and len(records) < 3

        return StatisticsResponse(
            metric=metric,
            period=period,
            sub_type=sub_type_q,
            data_count=len(records),
            insufficient_data=insufficient,
            series=series,
            reference_range=reference,
            peer_average=peer_avg,
        )

    @staticmethod
    def _point(record_type: RecordType, record: HealthRecord) -> StatisticsPoint:
        level = None
        return StatisticsPoint(
            measured_at=record.measured_at,
            primary_value=record.primary_value,
            secondary_value=record.secondary_value,
            sub_type=record.sub_type,
            level=level,
        )

    @staticmethod
    def _merge_glucose(records: list[HealthRecord]) -> list[StatisticsPoint]:
        grouped: dict[date, dict[str, Decimal]] = defaultdict(dict)
        for r in records:
            key = r.measured_at.date()
            if r.sub_type == RecordSubType.FASTING:
                grouped[key]["fasting"] = r.primary_value
        merged: list[StatisticsPoint] = []
        for day, values in sorted(grouped.items()):
            primary = values.get("fasting") or Decimal("0")
            merged.append(
                StatisticsPoint(
                    measured_at=datetime.combine(day, datetime.min.time()),
                    primary_value=primary,
                    secondary_value=None,
                )
            )
        return merged

    @staticmethod
    def _age(birthday: date | None) -> int | None:
        if birthday is None:
            return None
        today = datetime.now().date()
        years = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            years -= 1
        return years


class DiseaseRiskService:
    def __init__(self) -> None:
        self.repo = DiseaseRiskRepository()
        self.guideline_repo = DiseaseRiskGuidelineRepository()
        self.profile_repo = HealthProfileRepository()
        self.record_repo = HealthRecordRepository()
        self.predictor = RiskPredictor()

    async def create(
        self,
        user: User,
        disease_type: DiseaseType,
        snapshot_override: dict[str, Any] | None,
    ) -> DiseaseRisk:
        payload = await self._build_input(user, disease_type, snapshot_override)
        result = await self.predictor.predict(payload)
        guideline = await self.guideline_repo.get(disease_type, result.risk_level.value)

        async with in_transaction():
            risk = await self.repo.create(
                user_id=user.id,
                data={
                    "disease_type": disease_type,
                    "risk_score": result.risk_score,
                    "risk_level": result.risk_level,
                    "contributing_factors": [f.to_dict() for f in result.contributing_factors],
                    "input_snapshot": payload.snapshot(),
                    "model_version": result.model_version,
                    "guideline_id": guideline.id if guideline else None,
                },
            )
        return risk

    async def list_for_user(
        self,
        user: User,
        disease_type: DiseaseType | None,
        date_from: date | None,
        date_to: date | None,
        latest_only: bool,
    ) -> list[DiseaseRisk]:
        return await self.repo.list_for_user(
            user_id=user.id,
            disease_type=disease_type,
            date_from=date_from,
            date_to=date_to,
            latest_only=latest_only,
        )

    async def get_owned(self, user: User, prediction_id: int) -> DiseaseRisk:
        risk = await self.repo.get_owned(prediction_id, user.id)
        if risk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
        return risk

    async def _build_input(
        self,
        user: User,
        disease_type: DiseaseType,
        snapshot_override: dict[str, Any] | None,
    ) -> PredictionInput:
        profile = await self.profile_repo.get_by_user(user.id)
        latest_bp = await self.record_repo.latest_value(user.id, RecordType.BLOOD_PRESSURE)
        latest_fasting = await self.record_repo.latest_value(user.id, RecordType.BLOOD_GLUCOSE, RecordSubType.FASTING)
        latest_weight = await self.record_repo.latest_value(user.id, RecordType.WEIGHT)
        latest_waist = await self.record_repo.latest_value(user.id, RecordType.WAIST)

        weight = (latest_weight.primary_value if latest_weight else None) or (profile.weight_kg if profile else None)
        waist = (latest_waist.primary_value if latest_waist else None) or (profile.waist_cm if profile else None)
        systolic = (latest_bp.primary_value if latest_bp else None) or (profile.systolic_bp if profile else None)
        diastolic = (latest_bp.secondary_value if latest_bp else None) or (profile.diastolic_bp if profile else None)
        fasting_blood_sugar = (latest_fasting.primary_value if latest_fasting else None) or (
            profile.fasting_blood_sugar if profile else None
        )

        payload = PredictionInput(
            disease_type=disease_type,
            age=HealthStatisticsService._age(user.birthday),
            gender=user.gender.value if user.gender else None,
            height_cm=profile.height_cm if profile else None,
            weight_kg=weight,
            waist_cm=waist,
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            fasting_blood_sugar=fasting_blood_sugar,
            sleep_weekday=profile.sleep_weekday if profile else None,
            sleep_weekend=profile.sleep_weekend if profile else None,
            moderate_exercise_hour=profile.moderate_exercise_hour if profile else None,
            mid_act_day=profile.mid_act_day if profile else None,
            walk_day=profile.walk_day if profile else None,
            water_count=profile.water_count if profile else None,
            family_dm=profile.family_dm if profile else None,
            family_hp=profile.family_hp if profile else None,
            family_hl=profile.family_hl if profile else None,
            current_smoker=profile.current_smoker if profile else None,
            smoking_risk=profile.smoking_risk if profile else None,
            alcohol_freq_y=profile.alcohol_freq_y if profile else None,
            alcohol_cup=profile.alcohol_cup if profile else None,
            fruit_freq=profile.fruit_freq if profile else None,
            veg_freq_1=profile.veg_freq_1 if profile else None,
            out_meal_freq=profile.out_meal_freq if profile else None,
            breakfast_freq=profile.breakfast_freq if profile else None,
            is_menopause=profile.is_menopause if profile else None,
            ocp_total_months=profile.ocp_total_months if profile else None,
            anemia=profile.anemia if profile else None,
        )
        if snapshot_override:
            for key, value in snapshot_override.items():
                # disease_type/age/gender 는 서버측(요청 파라미터·User)에서 도출한 신뢰값이므로
                # 클라이언트 input_snapshot 으로 덮어쓰지 못하게 한다. (점수 조작 방지)
                if key in _SNAPSHOT_OVERRIDE_PROTECTED:
                    continue
                if hasattr(payload, key):
                    setattr(payload, key, value)
                else:
                    payload.extra[key] = value
        return payload


class MonthlyReportService:
    def __init__(self) -> None:
        self.repo = MonthlyReportRepository()
        self.record_repo = HealthRecordRepository()
        self.risk_repo = DiseaseRiskRepository()

    async def get_or_build(self, user: User, year_month: str) -> dict[str, Any]:
        try:
            year, month = year_month.split("-")
            year_int = int(year)
            month_int = int(month)
            if not 1 <= month_int <= 12:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month 형식은 YYYY-MM 이어야 합니다.",
            ) from exc

        start = date(year_int, month_int, 1)
        next_month_year = year_int + (1 if month_int == 12 else 0)
        next_month = 1 if month_int == 12 else month_int + 1
        end = date(next_month_year, next_month, 1).fromordinal(date(next_month_year, next_month, 1).toordinal() - 1)

        records = await self.record_repo.list_records(
            user_id=user.id,
            date_from=start,
            date_to=end,
            page=1,
            size=1000,
        )
        risks = await self.risk_repo.list_for_user(
            user_id=user.id,
            date_from=start,
            date_to=end,
            latest_only=False,
        )

        summary = self._summarize_records(records[0])
        risk_summary = self._summarize_risks(risks)
        report = await self.repo.upsert(
            user.id,
            year_month,
            data={
                "disease_risk_summary": risk_summary,
                "health_data_summary": summary,
                "challenge_summary": {},
                "pdf_file_id": None,
            },
        )
        return {
            "year_month": report.year_month,
            "disease_risk_summary": report.disease_risk_summary,
            "health_data_summary": report.health_data_summary,
            "challenge_summary": report.challenge_summary,
            "pdf_url": None,
            "generated_at": report.generated_at,
        }

    @staticmethod
    def _summarize_records(records: list[HealthRecord]) -> dict[str, Any]:
        grouped: dict[str, list[float]] = defaultdict(list)
        for r in records:
            grouped[r.record_type.value].append(float(r.primary_value))
        summary: dict[str, Any] = {}
        for record_type, values in grouped.items():
            summary[record_type] = {
                "count": len(values),
                "avg": round(sum(values) / len(values), 2) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        return summary

    @staticmethod
    def _summarize_risks(risks: list[DiseaseRisk]) -> dict[str, Any]:
        latest_by_type: dict[str, dict[str, Any]] = {}
        for r in risks:
            existing = latest_by_type.get(r.disease_type.value)
            if existing is None or r.calculated_at > existing["calculated_at"]:
                latest_by_type[r.disease_type.value] = {
                    "risk_score": float(r.risk_score),
                    "risk_level": r.risk_level.value,
                    "calculated_at": r.calculated_at,
                }
        for value in latest_by_type.values():
            value["calculated_at"] = value["calculated_at"].isoformat()
        return latest_by_type


def safe_int_or_400(value: str, field_name: str, *, default: int | None = None, min_value: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        if default is not None:
            return default
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} 값이 잘못되었습니다.",
        ) from exc
    if parsed < min_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} 값은 {min_value} 이상이어야 합니다.",
        )
    return parsed


def total_pages(total: int, size: int) -> int:
    if size <= 0:
        return 0
    return math.ceil(total / size)
