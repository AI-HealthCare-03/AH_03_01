from datetime import date, datetime
from typing import Any

from tortoise.expressions import Q

from app.models.health import (
    DiseaseRisk,
    DiseaseRiskGuideline,
    DiseaseType,
    HealthRecord,
    HealthReference,
    MonthlyReport,
    RecordSubType,
    RecordType,
    UserHealthInfo,
)


class HealthProfileRepository:
    def __init__(self) -> None:
        self._model = UserHealthInfo

    async def get_by_user(self, user_id: int) -> UserHealthInfo | None:
        return await self._model.get_or_none(user_id=user_id)

    async def create(self, user_id: int, data: dict[str, Any]) -> UserHealthInfo:
        return await self._model.create(user_id=user_id, **data)

    async def update_instance(self, profile: UserHealthInfo, data: dict[str, Any]) -> UserHealthInfo:
        update_fields = []
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
                update_fields.append(key)
        if update_fields:
            await profile.save(update_fields=update_fields)
        return profile


class HealthRecordRepository:
    def __init__(self) -> None:
        self._model = HealthRecord

    async def create(self, user_id: int, data: dict[str, Any]) -> HealthRecord:
        return await self._model.create(user_id=user_id, **data)

    async def get_owned(self, record_id: int, user_id: int) -> HealthRecord | None:
        return await self._model.get_or_none(id=record_id, user_id=user_id, is_deleted=False)

    async def list_records(
        self,
        user_id: int,
        record_type: RecordType | None = None,
        sub_type: RecordSubType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[HealthRecord], int]:
        qs = self._model.filter(user_id=user_id, is_deleted=False)
        if record_type is not None:
            qs = qs.filter(record_type=record_type)
        if sub_type is not None:
            qs = qs.filter(sub_type=sub_type)
        if date_from is not None:
            qs = qs.filter(measured_at__gte=datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            qs = qs.filter(measured_at__lte=datetime.combine(date_to, datetime.max.time()))
        total = await qs.count()
        items = await qs.order_by("-measured_at").offset((page - 1) * size).limit(size)
        return items, total

    async def update_instance(self, record: HealthRecord, data: dict[str, Any]) -> HealthRecord:
        update_fields = []
        for key, value in data.items():
            if value is not None:
                setattr(record, key, value)
                update_fields.append(key)
        if update_fields:
            await record.save(update_fields=update_fields)
        return record

    async def soft_delete(self, record: HealthRecord) -> None:
        record.is_deleted = True
        await record.save(update_fields=["is_deleted"])

    async def for_statistics(
        self,
        user_id: int,
        record_type: RecordType,
        date_from: date | None = None,
        date_to: date | None = None,
        sub_type: RecordSubType | None = None,
        limit: int | None = None,
    ) -> list[HealthRecord]:
        qs = self._model.filter(user_id=user_id, record_type=record_type, is_deleted=False)
        if sub_type is not None:
            qs = qs.filter(Q(sub_type=sub_type) | Q(sub_type__isnull=True))
        if date_from is not None:
            qs = qs.filter(measured_at__gte=datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            qs = qs.filter(measured_at__lte=datetime.combine(date_to, datetime.max.time()))
        qs = qs.order_by("-measured_at")
        if limit is not None:
            qs = qs.limit(limit)
        return list(await qs)

    async def latest_value(
        self, user_id: int, record_type: RecordType, sub_type: RecordSubType | None = None
    ) -> HealthRecord | None:
        qs = self._model.filter(user_id=user_id, record_type=record_type, is_deleted=False)
        if sub_type is not None:
            qs = qs.filter(sub_type=sub_type)
        return await qs.order_by("-measured_at").first()


class HealthReferenceRepository:
    def __init__(self) -> None:
        self._model = HealthReference

    async def lookup(
        self,
        record_type: RecordType,
        sub_type: RecordSubType | None = None,
        gender: str | None = None,
        age: int | None = None,
    ) -> HealthReference | None:
        qs = self._model.filter(record_type=record_type)
        if sub_type is not None:
            qs = qs.filter(Q(sub_type=sub_type) | Q(sub_type__isnull=True))
        if gender is not None:
            qs = qs.filter(Q(gender=gender) | Q(gender__isnull=True))
        if age is not None:
            qs = qs.filter(
                Q(age_group_min__isnull=True) | Q(age_group_min__lte=age),
            ).filter(
                Q(age_group_max__isnull=True) | Q(age_group_max__gte=age),
            )
        return await qs.order_by("-gender", "-age_group_min").first()


class DiseaseRiskRepository:
    def __init__(self) -> None:
        self._model = DiseaseRisk

    async def create(self, user_id: int, data: dict[str, Any]) -> DiseaseRisk:
        return await self._model.create(user_id=user_id, **data)

    async def get_owned(self, prediction_id: int, user_id: int) -> DiseaseRisk | None:
        return await self._model.get_or_none(id=prediction_id, user_id=user_id).select_related("guideline")

    async def list_for_user(
        self,
        user_id: int,
        disease_type: DiseaseType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        latest_only: bool = False,
    ) -> list[DiseaseRisk]:
        qs = self._model.filter(user_id=user_id)
        if disease_type is not None:
            qs = qs.filter(disease_type=disease_type)
        if date_from is not None:
            qs = qs.filter(calculated_at__gte=datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            qs = qs.filter(calculated_at__lte=datetime.combine(date_to, datetime.max.time()))
        qs = qs.order_by("-calculated_at")
        if latest_only:
            if disease_type is not None:
                latest = await qs.first()
                return [latest] if latest is not None else []
            seen: dict[DiseaseType, DiseaseRisk] = {}
            for risk in await qs:
                if risk.disease_type not in seen:
                    seen[risk.disease_type] = risk
            return list(seen.values())
        return list(await qs)


class DiseaseRiskGuidelineRepository:
    def __init__(self) -> None:
        self._model = DiseaseRiskGuideline

    async def get(self, disease_type: DiseaseType, risk_level: str) -> DiseaseRiskGuideline | None:
        return await self._model.get_or_none(disease_type=disease_type, risk_level=risk_level)


class MonthlyReportRepository:
    def __init__(self) -> None:
        self._model = MonthlyReport

    async def get(self, user_id: int, year_month: str) -> MonthlyReport | None:
        return await self._model.get_or_none(user_id=user_id, year_month=year_month)

    async def upsert(self, user_id: int, year_month: str, data: dict[str, Any]) -> MonthlyReport:
        existing = await self.get(user_id, year_month)
        if existing is None:
            return await self._model.create(user_id=user_id, year_month=year_month, **data)
        for key, value in data.items():
            setattr(existing, key, value)
        await existing.save()
        return existing
