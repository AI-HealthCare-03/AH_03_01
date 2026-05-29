"""`POST /api/v1/risk-recommendations` 라우터.

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 2단계.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.responses import ORJSONResponse as Response
from app.dependencies.security import get_request_user
from app.dtos.risk_recommendation import RiskRecommendationResponse
from app.models.users import User
from app.services.risk_recommendation import RiskRecommendationService

risk_recommendations_router = APIRouter(prefix="/risk-recommendations", tags=["risk-recommendations"])


@risk_recommendations_router.post(
    "",
    response_model=RiskRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def create_risk_recommendation(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[RiskRecommendationService, Depends(RiskRecommendationService)],
) -> Response:
    """위험도 예측 + 맞춤 권고 + 챌린지 추천을 한 응답에 묶어 반환.

    - 사용자 건강 정보는 DB 에서 자동 조회 (저장 직후 트리거 가정).
    - 필수 데이터(키·몸무게) 누락 시 has_required_data=false + action_hint 로 응답.
    - 위험도 예측은 룰 stub (P1). ml_inference_requests 에 이력 기록.
    - DiseaseRisk 테이블에 시계열 누적 저장 — 이후 ChatRAGGraph 가 자동 컨텍스트로 활용.
    """
    result = await service.recommend(user_id=user.id)
    return Response(content=result.model_dump())
