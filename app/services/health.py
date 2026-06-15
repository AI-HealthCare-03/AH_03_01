from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.core import config
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
        # 건강 프로필 변경 → 위험도 feature_snapshot 입력이 바뀌므로 Redis 캐시 무효화 (best-effort).
        from app.services.risk_recommendation_cache import invalidate_risk_cache

        await invalidate_risk_cache(user.id)
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
        # 일별 레코드 생성 → 위험도 feature_snapshot(레코드 폴백 포함) 입력이 바뀌므로 캐시 무효화 (best-effort).
        from app.services.risk_recommendation_cache import invalidate_risk_cache

        await invalidate_risk_cache(user.id)
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
            updated = await self.repo.update_instance(record, data.model_dump(exclude_unset=True))
        # 레코드 수정 → 위험도 feature_snapshot(최신 레코드 폴백) 입력이 바뀌므로 캐시 무효화 (best-effort).
        from app.services.risk_recommendation_cache import invalidate_risk_cache

        await invalidate_risk_cache(user.id)
        return updated

    async def delete(self, user: User, record_id: int) -> None:
        record = await self.get_owned(user, record_id)
        await self.repo.soft_delete(record)
        # 레코드 삭제 → 직전 레코드가 "최신"으로 노출되어 snapshot 입력이 바뀌므로 캐시 무효화 (best-effort).
        from app.services.risk_recommendation_cache import invalidate_risk_cache

        await invalidate_risk_cache(user.id)


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
    # 추이 노출 대상 지표 (참고 디자인: 혈압 / 혈당(공복) / 체중. HbA1c 는 미수집이라 제외)
    _TREND_SPECS: tuple[tuple[str, RecordType, RecordSubType | None, str], ...] = (
        ("blood_pressure", RecordType.BLOOD_PRESSURE, None, "mmHg"),
        ("blood_glucose", RecordType.BLOOD_GLUCOSE, RecordSubType.FASTING, "mg/dL"),
        ("weight", RecordType.WEIGHT, None, "kg"),
    )
    # 위험도 판단근거 상위 N
    _TOP_FACTORS = 5

    def __init__(self) -> None:
        self.repo = MonthlyReportRepository()
        self.record_repo = HealthRecordRepository()
        self.risk_repo = DiseaseRiskRepository()
        self.profile_repo = HealthProfileRepository()

    # 임의 기간(custom) 리포트 최대 조회 범위. 너무 긴 범위의 풀스캔/레코드 폭주 방지.
    _MAX_RANGE_DAYS = 366

    async def _aggregate(self, user: User, start: date, end: date) -> dict[str, Any]:
        """기간(start~end, 양끝 포함) 집계 — 캐싱/영속 없이 구조화 섹션 dict 산출 (월/임의기간 공용).

        ⚠️ records 는 size=1000 으로 제한 — 매우 긴 기간(_MAX_RANGE_DAYS 근처)에서 일 다건 기록이
        쌓이면 상한에 걸려 잘릴 수 있다(월 단위에선 사실상 미발생). 필요 시 페이지네이션으로 확장.
        """
        records, _ = await self.record_repo.list_records(
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
        profile = await self.profile_repo.get_by_user(user.id)

        # ── 구조화 섹션 집계 ──────────────────────────────────────────────────
        header = self._build_header(records, profile)
        disease_risks = self._build_disease_risks(risks)
        trends = self._build_trends(records)
        challenges = await self._build_challenges(user.id, start, end)
        good_habits = self._build_good_habits(records, challenges, profile)

        # ── 레거시 dict 섹션 (호환 유지) ─────────────────────────────────────
        summary = self._summarize_records(records)
        risk_summary = self._summarize_risks(risks)
        return {
            "disease_risk_summary": risk_summary,
            "health_data_summary": summary,
            "header_stats": header,
            "disease_risks": disease_risks,
            "trends": trends,
            "challenges": challenges,
            "good_habits": good_habits,
        }

    @staticmethod
    def _payload(
        *,
        sections: dict[str, Any],
        year_month: str,
        period: str,
        start: date,
        end: date,
        generated_at: datetime,
    ) -> dict[str, Any]:
        """집계 섹션 → 응답 payload(MonthlyReportResponse shape). 월/임의기간 공용."""
        return {
            "year_month": year_month,
            "period": period,
            "date_from": start,
            "date_to": end,
            "disease_risk_summary": sections["disease_risk_summary"],
            "health_data_summary": sections["health_data_summary"],
            "challenge_summary": {
                "header_stats": sections["header_stats"],
                "disease_risks": sections["disease_risks"],
                "trends": sections["trends"],
                "challenges": sections["challenges"],
                "good_habits": sections["good_habits"],
            },
            "header_stats": sections["header_stats"],
            "disease_risks": sections["disease_risks"],
            "trends": sections["trends"],
            "challenges": sections["challenges"],
            "good_habits": sections["good_habits"],
            "pdf_url": None,
            "generated_at": generated_at,
        }

    async def get_or_build(self, user: User, year_month: str) -> dict[str, Any]:
        """월 단위 리포트 — YYYY-MM. 결과를 MonthlyReport 에 upsert(캐싱·영속)."""
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

        sections = await self._aggregate(user, start, end)
        report = await self.repo.upsert(
            user.id,
            year_month,
            data={
                "disease_risk_summary": sections["disease_risk_summary"],
                "health_data_summary": sections["health_data_summary"],
                # 구조화 섹션을 challenge_summary JSONB 에 함께 영속 (마이그레이션 불요).
                "challenge_summary": {
                    "header_stats": sections["header_stats"],
                    "disease_risks": sections["disease_risks"],
                    "trends": sections["trends"],
                    "challenges": sections["challenges"],
                    "good_habits": sections["good_habits"],
                },
                "pdf_file_id": None,
            },
        )
        return self._payload(
            sections=sections,
            year_month=report.year_month,
            period="monthly",
            start=start,
            end=end,
            generated_at=report.generated_at,
        )

    async def build_for_range(self, user: User, date_from: str, date_to: str) -> dict[str, Any]:
        """임의 기간 리포트 — date_from~date_to(YYYY-MM-DD, 양끝 포함). 캐싱/영속 없이 매번 산출."""
        try:
            start = date.fromisoformat(date_from)
            end = date.fromisoformat(date_to)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from/date_to 형식은 YYYY-MM-DD 이어야 합니다.",
            ) from exc
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from 은 date_to 보다 이후일 수 없습니다.",
            )
        if (end - start).days > self._MAX_RANGE_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"조회 기간은 최대 {self._MAX_RANGE_DAYS}일까지 가능합니다.",
            )

        sections = await self._aggregate(user, start, end)
        return self._payload(
            sections=sections,
            year_month=f"{start.isoformat()}~{end.isoformat()}",
            period="custom",
            start=start,
            end=end,
            generated_at=datetime.now(config.TIMEZONE),
        )

    # ── 헤더 통계 ────────────────────────────────────────────────────────────
    @staticmethod
    def _build_header(records: list[HealthRecord], profile: UserHealthInfo | None) -> dict[str, Any]:
        recorded_days = {r.measured_at.astimezone(config.TIMEZONE).date() for r in records}
        sleep_vals = [float(r.primary_value) for r in records if r.record_type == RecordType.SLEEP]
        step_vals = [float(r.primary_value) for r in records if r.record_type == RecordType.ACTIVITY]
        avg_sleep: float | None = None
        if sleep_vals:
            avg_sleep = round(sum(sleep_vals) / len(sleep_vals), 2)
        elif recorded_days and profile is not None and profile.sleep_weekday is not None:
            avg_sleep = round(float(profile.sleep_weekday), 2)
        avg_steps = round(sum(step_vals) / len(step_vals), 1) if step_vals else None
        return {
            "recorded_days": len(recorded_days),
            "avg_sleep_hours": avg_sleep,
            "avg_steps": avg_steps,
        }

    # ── 위험도 + 판단근거 TOP5 ──────────────────────────────────────────────
    @classmethod
    def _build_disease_risks(cls, risks: list[DiseaseRisk]) -> list[dict[str, Any]]:
        latest_by_type: dict[DiseaseType, DiseaseRisk] = {}
        for r in risks:
            existing = latest_by_type.get(r.disease_type)
            if existing is None or r.calculated_at > existing.calculated_at:
                latest_by_type[r.disease_type] = r
        result: list[dict[str, Any]] = []
        for disease_type in DiseaseType:  # 질환 3종 모두 노출 (예측 없으면 has_prediction=False)
            latest = latest_by_type.get(disease_type)
            if latest is None:
                result.append(
                    {
                        "disease_type": disease_type.value,
                        "risk_score": None,
                        "risk_level": None,
                        "risk_level_label": None,
                        "calculated_at": None,
                        "has_prediction": False,
                        "top_factors": [],
                    }
                )
                continue
            factors = sorted(
                (latest.contributing_factors or []),
                key=lambda f: abs(float(f.get("weight", 0.0))),
                reverse=True,
            )[: cls._TOP_FACTORS]
            top_factors = [
                {
                    "factor": f.get("factor", ""),
                    "weight": float(f.get("weight", 0.0)),
                    "name_kor": f.get("name_kor"),
                    "direction": f.get("direction"),
                    "description": f.get("description"),
                }
                for f in factors
            ]
            result.append(
                {
                    "disease_type": disease_type.value,
                    "risk_score": float(latest.risk_score),
                    "risk_level": latest.risk_level.value,
                    "risk_level_label": latest.risk_level_label,
                    "calculated_at": latest.calculated_at.isoformat(),
                    "has_prediction": True,
                    "top_factors": top_factors,
                }
            )
        return result

    # ── 건강지표 추이 ────────────────────────────────────────────────────────
    @classmethod
    def _build_trends(cls, records: list[HealthRecord]) -> list[dict[str, Any]]:
        trends: list[dict[str, Any]] = []
        for metric, record_type, sub_type, unit in cls._TREND_SPECS:
            matched = [
                r
                for r in records
                if r.record_type == record_type and (sub_type is None or r.sub_type == sub_type)
            ]
            matched.sort(key=lambda r: r.measured_at)
            series = [
                {
                    "date": r.measured_at.astimezone(config.TIMEZONE).date().isoformat(),
                    "value": float(r.primary_value),
                    "secondary_value": (float(r.secondary_value) if r.secondary_value is not None else None),
                }
                for r in matched
            ]
            primary_vals = [float(r.primary_value) for r in matched]
            secondary_vals = [float(r.secondary_value) for r in matched if r.secondary_value is not None]
            trends.append(
                {
                    "metric": metric,
                    "unit": unit,
                    "series": series,
                    "avg": round(sum(primary_vals) / len(primary_vals), 2) if primary_vals else None,
                    "latest": primary_vals[-1] if primary_vals else None,
                    "secondary_avg": (
                        round(sum(secondary_vals) / len(secondary_vals), 2) if secondary_vals else None
                    ),
                    # secondary_vals[-1] 사용: 마지막 레코드의 secondary 가 None 이어도(혈압 일부 누락)
                    # 마지막 '유효' 이완기값을 안전하게 반환 (matched[-1].secondary_value 직접 캐스트 시 None→TypeError).
                    "secondary_latest": (secondary_vals[-1] if secondary_vals else None),
                }
            )
        return trends

    # ── 챌린지 수행 내역 ─────────────────────────────────────────────────────
    async def _build_challenges(self, user_id: Any, start: date, end: date) -> list[dict[str, Any]]:
        """해당 월에 기간이 겹치는, 사용자가 참여(LEFT 제외)한 챌린지별 인증 집계."""
        from app.models.challenge import (
            Challenge,
            ChallengeParticipant,
            ChallengeVerification,
            ParticipantStatus,
            VerificationStatus,
        )

        participants = await ChallengeParticipant.filter(
            user_id=user_id,
            status__in=[ParticipantStatus.APPROVED, ParticipantStatus.PENDING],
        ).prefetch_related("challenge")
        result: list[dict[str, Any]] = []
        for participant in participants:
            challenge: Challenge = participant.challenge
            if challenge is None or challenge.is_deleted:
                continue
            # 챌린지 기간이 해당 월과 겹치는지 (start_date <= end and end_date >= start)
            if challenge.start_date > end or challenge.end_date < start:
                continue
            goal_days = (challenge.end_date - challenge.start_date).days + 1
            success_days = await ChallengeVerification.filter(
                challenge_id=challenge.id,
                user_id=user_id,
                status=VerificationStatus.APPROVED,
                is_deleted=False,
            ).count()
            progress = round(success_days / goal_days * 100) if goal_days > 0 else 0
            progress = max(0, min(100, progress))
            today = datetime.now(config.TIMEZONE).date()
            if success_days >= goal_days and goal_days > 0:
                state = "success"
            elif challenge.end_date < today:
                state = "success" if progress >= 100 else "failed"
            else:
                state = "in_progress"
            result.append(
                {
                    "challenge_id": challenge.id,
                    "title": challenge.title,
                    "category": challenge.category.value,
                    "status": state,
                    "progress_percent": progress,
                    "success_days": success_days,
                    "goal_days": goal_days,
                }
            )
        result.sort(key=lambda c: c["challenge_id"])
        return result

    # ── 좋은 습관 (파생, 중립 톤) ───────────────────────────────────────────
    @classmethod
    def _build_good_habits(
        cls,
        records: list[HealthRecord],
        challenges: list[dict[str, Any]],
        profile: UserHealthInfo | None,
    ) -> list[dict[str, Any]]:
        """수집 데이터로 '잘 지킨 습관'을 보수적으로 도출. 의학적 단정 금지(근거 수치만 제시)."""
        habits: list[dict[str, Any]] = []

        # 걷기: 일평균 걸음 8000 이상이면 '꾸준한 걷기'
        step_vals = [float(r.primary_value) for r in records if r.record_type == RecordType.ACTIVITY]
        if step_vals:
            avg_steps = sum(step_vals) / len(step_vals)
            if avg_steps >= 8000:
                habits.append(
                    {
                        "key": "walking",
                        "label": "꾸준한 걷기",
                        "evidence": f"이번 달 평균 {round(avg_steps):,}걸음을 기록했어요.",
                    }
                )

        # 수분: 하루 물 섭취 8컵 이상(프로필 water_count)
        if profile is not None and profile.water_count is not None and profile.water_count >= 8:
            habits.append(
                {
                    "key": "hydration",
                    "label": "충분한 수분 섭취",
                    "evidence": f"하루 평균 물 {profile.water_count}컵을 섭취하고 있어요.",
                }
            )

        # 수면: 평균 수면 7시간 이상 (SLEEP 레코드 우선, 없으면 프로필 sleep_weekday)
        sleep_vals = [float(r.primary_value) for r in records if r.record_type == RecordType.SLEEP]
        avg_sleep: float | None = None
        if sleep_vals:
            avg_sleep = sum(sleep_vals) / len(sleep_vals)
        elif profile is not None and profile.sleep_weekday is not None:
            avg_sleep = float(profile.sleep_weekday)
        if avg_sleep is not None and avg_sleep >= 7:
            habits.append(
                {
                    "key": "sleep",
                    "label": "규칙적인 수면",
                    "evidence": f"평균 수면 시간이 {round(avg_sleep, 1)}시간이에요.",
                }
            )

        # 운동: 주당 중강도 운동 3일 이상(프로필 mid_act_day)
        if profile is not None and profile.mid_act_day is not None and profile.mid_act_day >= 3:
            habits.append(
                {
                    "key": "exercise",
                    "label": "꾸준한 운동",
                    "evidence": f"주 {profile.mid_act_day}일 중강도 운동을 실천하고 있어요.",
                }
            )

        # 챌린지: 진행률 100% 달성(성공) 챌린지가 있으면 '챌린지 완수'
        completed = [c for c in challenges if c["status"] == "success"]
        if completed:
            habits.append(
                {
                    "key": "challenge",
                    "label": "챌린지 완수",
                    "evidence": f"이번 달 {len(completed)}개 챌린지를 성공적으로 마쳤어요.",
                }
            )

        return habits

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
