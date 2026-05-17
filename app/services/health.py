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
from app.models.users import User
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


class HealthProfileService:
    def __init__(self) -> None:
        self.repo = HealthProfileRepository()

    async def get_or_init(self, user: User) -> UserHealthInfo:
        profile = await self.repo.get_by_user(user.id)
        if profile is None:
            profile = await self.repo.create(user.id, data={})
        return profile

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
        "hba1c": (RecordType.HBA1C, None),
        "activity": (RecordType.ACTIVITY, None),
    }

    @classmethod
    def parse_metric(cls, metric: str) -> tuple[RecordType, RecordSubType | None]:
        if metric not in cls._METRIC_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 metric: {metric}",
            )
        return cls._METRIC_MAP[metric]

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
        if sub_type_q in {RecordSubType.FASTING.value, RecordSubType.POSTMEAL.value}:
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
        if record_type == RecordType.HBA1C:
            value = float(record.primary_value)
            if value < 5.7:
                level = "normal"
            elif value < 6.5:
                level = "pre_diabetic"
            else:
                level = "diabetic"
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
            elif r.sub_type == RecordSubType.POSTMEAL:
                grouped[key]["postmeal"] = r.primary_value
        merged: list[StatisticsPoint] = []
        for day, values in sorted(grouped.items()):
            primary = values.get("fasting") or values.get("postmeal") or Decimal("0")
            secondary = values.get("postmeal") if "fasting" in values else None
            merged.append(
                StatisticsPoint(
                    measured_at=datetime.combine(day, datetime.min.time()),
                    primary_value=primary,
                    secondary_value=secondary,
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
        latest_postmeal = await self.record_repo.latest_value(user.id, RecordType.BLOOD_GLUCOSE, RecordSubType.POSTMEAL)
        latest_hba1c = await self.record_repo.latest_value(user.id, RecordType.HBA1C)
        latest_weight = await self.record_repo.latest_value(user.id, RecordType.WEIGHT)
        latest_waist = await self.record_repo.latest_value(user.id, RecordType.WAIST)

        weight = (latest_weight.primary_value if latest_weight else None) or (profile.weight_kg if profile else None)
        waist = (latest_waist.primary_value if latest_waist else None) or (profile.waist_cm if profile else None)

        payload = PredictionInput(
            disease_type=disease_type,
            age=HealthStatisticsService._age(user.birthday),
            gender=user.gender.value if user.gender else None,
            height_cm=profile.height_cm if profile else None,
            weight_kg=weight,
            waist_cm=waist,
            is_smoker=profile.is_smoker if profile else False,
            alcohol_intake=profile.alcohol_intake.value if profile else None,
            has_diabetes_family_history=profile.has_diabetes_family_history if profile else False,
            has_hypertension_family_history=profile.has_hypertension_family_history if profile else False,
            is_chronic_patient=profile.is_chronic_patient if profile else False,
            blood_pressure_systolic=latest_bp.primary_value if latest_bp else None,
            blood_pressure_diastolic=latest_bp.secondary_value if latest_bp else None,
            fasting_glucose=latest_fasting.primary_value if latest_fasting else None,
            postmeal_glucose=latest_postmeal.primary_value if latest_postmeal else None,
            hba1c=latest_hba1c.primary_value if latest_hba1c else None,
        )
        if snapshot_override:
            for key, value in snapshot_override.items():
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
