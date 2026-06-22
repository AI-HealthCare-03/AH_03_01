"""`POST /api/v1/risk-recommendations` 라우터.

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 2단계.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

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


@risk_recommendations_router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
)
async def stream_risk_recommendation(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[RiskRecommendationService, Depends(RiskRecommendationService)],
) -> StreamingResponse:
    """위험도 예측 + 맞춤 권고 SSE 스트리밍 — meta → stage* → token* → done (실패 시 error).

    비스트림 POST /risk-recommendations 와 동일한 캐시·저장 계약을 따르되, 그래프 진행 단계
    (건강정보 확인 → 위험도 예측 → 자료 검색 → 권고 작성 → 검토)를 실시간으로 흘려보낸다.
    done 이벤트 본문 shape 은 비스트림 응답과 동일.

    헤더 X-Accel-Buffering=no 로 nginx 버퍼링 무력화를 시도하나, 운영 nginx 의 해당 location
    proxy_buffering off 설정이 함께 필요할 수 있다 (챗봇 스트림과 동일 주의).
    """
    generator: AsyncGenerator[str, None] = service.recommend_stream(user_id=user.id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
