from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.health import (
    ExplanationResponse,
    HealthProfileResponse,
    HealthProfileUpsertRequest,
    HealthRecordCreateRequest,
    HealthRecordListResponse,
    HealthRecordResponse,
    HealthRecordUpdateRequest,
    MonthlyReportResponse,
    PredictionCreateRequest,
    PredictionListResponse,
    PredictionResponse,
    RiskRecommendationItem,
    RiskRecommendationResponse,
    StatisticsResponse,
)
from app.models.health import DiseaseType, RecordSubType, RecordType
from app.models.users import User
from app.services.health import (
    DiseaseRiskService,
    HealthProfileService,
    HealthRecordService,
    HealthStatisticsService,
    MonthlyReportService,
    total_pages,
)
from app.services.ml.risk_predictor import MLUnavailableError

health_records_router = APIRouter(prefix="/health-records", tags=["health-records"])
health_reports_router = APIRouter(prefix="/health-reports", tags=["health-reports"])
predictions_router = APIRouter(prefix="/predictions", tags=["predictions"])


async def _award_health_view(user_id) -> None:  # type: ignore[no-untyped-def]  # user_id: UUID
    """건강 데이터 확인 활동량 EXP 적립 (1일 1회). best-effort."""
    try:
        from app.models.experience import XpKind
        from app.services.experience import ExperienceService

        await ExperienceService().award(user_id=user_id, kind=XpKind.HEALTH_VIEW)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /health-records (profile + daily records unified via recordType)
# ---------------------------------------------------------------------------


@health_records_router.get("", status_code=status.HTTP_200_OK)
async def list_health_records(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthRecordService, Depends(HealthRecordService)],
    profile_service: Annotated[HealthProfileService, Depends(HealthProfileService)],
    record_type: Annotated[
        str | None,
        Query(alias="recordType", description="profile|daily|weight|waist|blood_pressure|blood_glucose|hba1c|activity"),
    ] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    sub_type: Annotated[RecordSubType | None, Query(alias="subType")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Response:
    if record_type == "profile":
        profile = await profile_service.get_or_init(user)
        completeness = await profile_service.compute_completeness(profile, user)
        profile_payload = HealthProfileResponse.model_validate(profile).model_copy(
            update={"completeness": completeness}
        )
        return Response(
            profile_payload.model_dump(),
            status_code=status.HTTP_200_OK,
        )

    rt = _parse_record_type(record_type) if record_type and record_type != "daily" else None
    items, total = await service.list_records(
        user=user,
        record_type=rt,
        sub_type=sub_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    payload = HealthRecordListResponse(
        page=page,
        size=size,
        total_elements=total,
        total_pages=total_pages(total, size),
        items=[HealthRecordResponse.model_validate(r) for r in items],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@health_records_router.post("", status_code=status.HTTP_201_CREATED)
async def create_health_record(
    request: Request,
    user: Annotated[User, Depends(get_request_user)],
    record_service: Annotated[HealthRecordService, Depends(HealthRecordService)],
    profile_service: Annotated[HealthProfileService, Depends(HealthProfileService)],
    record_type: Annotated[
        str | None,
        Query(alias="recordType", description="profile|daily|<record_type>"),
    ] = None,
) -> Response:
    # recordType 으로 dispatch 되는 두 body 타입을 동일 엔드포인트에서 받기 위해
    # 수동으로 raw JSON 을 파싱한 뒤 적절한 DTO 로 검증한다.
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="본문 형식이 잘못되었습니다.")

    try:
        if record_type == "profile":
            profile_body = HealthProfileUpsertRequest.model_validate(body)
            profile = await profile_service.upsert(user, profile_body)
            return Response(
                HealthProfileResponse.model_validate(profile).model_dump(mode="json"),
                status_code=status.HTTP_201_CREATED,
            )
        record_body = HealthRecordCreateRequest.model_validate(body)
    except ValidationError as exc:
        raise RequestValidationError(errors=exc.errors()) from exc
    record = await record_service.create(user, record_body)
    return Response(
        HealthRecordResponse.model_validate(record).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@health_records_router.get("/statistics", response_model=StatisticsResponse, status_code=status.HTTP_200_OK)
async def get_health_statistics(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthStatisticsService, Depends(HealthStatisticsService)],
    metric: Annotated[str, Query()],
    period: Annotated[str | None, Query()] = None,
    sub_type: Annotated[str | None, Query(alias="subType")] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    include_reference: Annotated[bool, Query(alias="includeReference")] = True,
) -> Response:
    payload = await service.get_statistics(
        user=user,
        metric=metric,
        period=period,
        sub_type_q=sub_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        include_reference=include_reference,
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@health_records_router.get("/{record_id}", response_model=HealthRecordResponse, status_code=status.HTTP_200_OK)
async def get_health_record(
    record_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthRecordService, Depends(HealthRecordService)],
) -> Response:
    record = await service.get_owned(user, record_id)
    return Response(
        HealthRecordResponse.model_validate(record).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@health_records_router.patch("/{record_id}", response_model=HealthRecordResponse, status_code=status.HTTP_200_OK)
async def update_health_record(
    record_id: int,
    update_data: HealthRecordUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthRecordService, Depends(HealthRecordService)],
) -> Response:
    record = await service.update(user, record_id, update_data)
    return Response(
        HealthRecordResponse.model_validate(record).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@health_records_router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_record(
    record_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthRecordService, Depends(HealthRecordService)],
) -> Response:
    await service.delete(user, record_id)
    return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# /health-reports
# ---------------------------------------------------------------------------


@health_reports_router.get("", response_model=MonthlyReportResponse, status_code=status.HTTP_200_OK)
async def get_health_report(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MonthlyReportService, Depends(MonthlyReportService)],
    period: Annotated[str, Query()] = "monthly",
    month: Annotated[str | None, Query()] = None,
    output_format: Annotated[str, Query(alias="format")] = "json",
) -> Response:
    if period != "monthly":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재는 monthly 만 지원합니다.")
    if month is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month 쿼리(YYYY-MM)가 필요합니다.")
    if output_format not in {"json", "pdf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format 은 json 또는 pdf 입니다.")
    payload = await service.get_or_build(user, month)
    if output_format == "pdf":
        # PDF 생성 파이프라인은 별도 작업(FILE_UPLOAD/렌더러)이라 현 단계에서 미지원.
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="PDF 다운로드는 추후 지원 예정입니다.")
    await _award_health_view(user.id)
    return Response(payload, status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# /predictions
# ---------------------------------------------------------------------------


@predictions_router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[DiseaseRiskService, Depends(DiseaseRiskService)],
    profile_service: Annotated[HealthProfileService, Depends(HealthProfileService)],
    disease_type: Annotated[DiseaseType, Query(alias="diseaseType")],
    body: PredictionCreateRequest | None = None,
    mode: Annotated[str, Query()] = "sync",
) -> Response:
    if mode not in {"sync", "stream"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode 는 sync|stream 입니다.")
    if mode == "stream":
        # SSE 는 추후 지원
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="stream 모드는 추후 지원 예정입니다.")
    # 예측 게이트: 모델입력 필드가 모두 채워져야 예측 가능. 미충족이면 422 + 누락 항목 안내.
    profile = await profile_service.repo.get_by_user(user.id)
    completeness = await profile_service.compute_completeness(profile, user)
    if not completeness.complete:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "건강 데이터를 모두 입력해야 위험도 예측을 이용할 수 있습니다.",
                "missing_fields": completeness.missing_fields,
            },
        )
    snapshot = body.input_snapshot if body and body.input_snapshot else None
    try:
        risk = await service.create(user, disease_type, snapshot)
    except MLUnavailableError as e:
        # RISK_REQUIRE_ML=True 에서 ML 로드/추론 실패 — 룰로 가리지 않고 503 으로 드러낸다.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "위험도 예측 모델을 일시적으로 사용할 수 없습니다.", "code": "ML_UNAVAILABLE"},
        ) from e
    return Response(
        PredictionResponse.model_validate(risk).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@predictions_router.get("", response_model=PredictionListResponse, status_code=status.HTTP_200_OK)
async def list_predictions(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[DiseaseRiskService, Depends(DiseaseRiskService)],
    disease_type: Annotated[DiseaseType | None, Query(alias="diseaseType")] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    latest: Annotated[bool, Query()] = False,
) -> Response:
    risks = await service.list_for_user(
        user=user,
        disease_type=disease_type,
        date_from=date_from,
        date_to=date_to,
        latest_only=latest,
    )
    payload = PredictionListResponse(items=[PredictionResponse.model_validate(r) for r in risks])
    await _award_health_view(user.id)
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@predictions_router.get(
    "/{prediction_id}/risk-recommendations",
    response_model=RiskRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_risk_recommendation(
    prediction_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[DiseaseRiskService, Depends(DiseaseRiskService)],
) -> Response:
    risk = await service.get_owned(user, prediction_id)
    guideline = None
    if risk.guideline_id is not None:
        from app.models.health import DiseaseRiskGuideline as _DiseaseRiskGuideline

        guideline = await _DiseaseRiskGuideline.get_or_none(id=risk.guideline_id)
    if guideline is None:
        recommendations = [
            RiskRecommendationItem(category="general", content="규칙적인 운동과 균형 잡힌 식단을 권장합니다.")
        ]
        condition_desc = "현재 등록된 가이드라인이 없어 일반 권고만 제공됩니다."
        level_label = risk.risk_level.value
        hospital_visit = False
        disclaimer = "본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다."
    else:
        tips = guideline.lifestyle_tips or []
        recommendations = [
            RiskRecommendationItem(category=t.get("category", "lifestyle"), content=t.get("content", ""))
            if isinstance(t, dict)
            else RiskRecommendationItem(category="lifestyle", content=str(t))
            for t in tips
        ]
        if not recommendations:
            recommendations = [RiskRecommendationItem(category="lifestyle", content=guideline.recommendation)]
        condition_desc = guideline.condition_desc
        level_label = guideline.level_label
        hospital_visit = guideline.hospital_visit_recommended
        disclaimer = guideline.disclaimer

    payload = RiskRecommendationResponse(
        prediction_id=risk.id,
        disease_type=risk.disease_type,
        risk_level=risk.risk_level,
        level_label=level_label,
        condition_desc=condition_desc,
        recommendations=recommendations,
        hospital_visit_recommended=hospital_visit,
        disclaimer=disclaimer,
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


@predictions_router.get(
    "/{prediction_id}/explanations",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_prediction_explanation(
    prediction_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[DiseaseRiskService, Depends(DiseaseRiskService)],
    visualization: Annotated[str, Query()] = "feature",
) -> Response:
    if visualization not in {"feature", "shap", "chart"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="visualization 은 feature|shap|chart 입니다.",
        )
    risk = await service.get_owned(user, prediction_id)
    factors_data: list[dict[str, Any]] = list(risk.contributing_factors or [])
    risk_factors = [
        {
            "factor": f.get("factor", ""),
            "weight": float(f.get("weight", 0.0)),
            "description": f.get("description"),
        }
        for f in factors_data
    ]
    charts: list[dict[str, Any]] = []
    if visualization in {"feature", "chart"}:
        charts.append(
            {
                "type": "feature_contribution",
                "data": risk_factors,
            }
        )
    if visualization == "shap":
        # SHAP 시각화는 실제 ML 모델 연결 시 제공
        charts.append({"type": "shap", "data": [], "status": "pending_model_integration"})
    payload = ExplanationResponse(
        prediction_id=risk.id,
        disease_type=risk.disease_type,
        visualization=visualization,
        risk_factors=risk_factors,  # type: ignore[arg-type]
        charts=charts,
        recommendations=[
            RiskRecommendationItem(category="lifestyle", content="규칙적인 식사와 운동을 권장합니다."),
        ],
    )
    return Response(payload.model_dump(), status_code=status.HTTP_200_OK)


def _parse_record_type(value: str) -> RecordType:
    try:
        return RecordType(value.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 recordType: {value}",
        ) from exc
