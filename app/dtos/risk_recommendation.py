"""DTO — POST /api/v1/risk-recommendations 요청·응답.

설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 2단계.

요청 body 는 없음(사용자 ID 만 JWT 에서 추출, 입력 데이터는 DB 자동 fetch).
응답에 위험도 예측 결과 (3 질환) + LLM 권고·챌린지 추천 본문 + sources + 메타.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContributingFactorItem(BaseModel):
    """위험도 산출에 기여한 요인 단위. RiskPredictor 출력 그대로."""

    model_config = ConfigDict(extra="ignore")

    factor: str
    weight: float
    description: str | None = None
    name_kor: str | None = None  # 한글명 (ML 경로; 룰 폴백은 None → UI 는 factor/description 사용)
    direction: str | None = None  # "위험 증가↑"/"위험 감소↓"


class RiskPredictionItem(BaseModel):
    """질환별 위험도 예측 결과."""

    disease_type: str = Field(description='"DIABETES" / "HYPERTENSION" / "CARDIOVASCULAR"')
    risk_score: float = Field(description="0~100 위험도 점수")
    risk_level: str = Field(description='"NORMAL"/"CAUTION"/"RISK"/"HIGH_RISK"')
    contributing_factors: list[ContributingFactorItem] = Field(default_factory=list)


class RecommendationSourceItem(BaseModel):
    """답변 생성에 사용된 RAG 청크 출처 (frontend 표시용)."""

    title: str | None = None
    document_id: int | None = None
    snippet: str | None = None
    source: str | None = None  # 예: "KSLA2022" / "CHALLENGE_CATALOG"


class RecommendedChallengeItem(BaseModel):
    """추천 챌린지 카드 (프론트가 바로 렌더). LLM 선정 + 카탈로그 메타 조인 결과."""

    model_config = ConfigDict(extra="ignore")

    template_id: int = Field(description="챌린지 템플릿 id (참여 등록 시 사용)")
    title: str = Field(description="챌린지 제목")
    category: str = Field(description="카테고리 (예: DIET/EXERCISE/...)")
    difficulty: str = Field(description="난이도 (예: LEVEL_1~LEVEL_4)")
    reason: str = Field(default="", description="추천 이유 한 줄 (LLM 생성)")
    priority: str | None = Field(
        default=None,
        description='"TOP"/"RECOMMENDED"/"OPTIONAL" (LLM 미지정 시 null)',
    )


class RiskRecommendationResponse(BaseModel):
    """`POST /api/v1/risk-recommendations` 응답.

    필드 매트릭스:
      - has_required_data=false → predictions=[], answer=MISSING_INFO, missing_fields 채움
      - has_required_data=true + is_fallback=false → 정상 답변
      - has_required_data=true + is_fallback=true  → fallback 메시지
    """

    answer: str = Field(description="LLM 생성 권고·챌린지 추천 본문")
    predictions: list[RiskPredictionItem] = Field(default_factory=list)
    sources: list[RecommendationSourceItem] = Field(default_factory=list)
    recommended_tips: list[str] = Field(
        default_factory=list,
        description="생활습관 권고 칩 (LLM 구조화 출력, 본문 요약)",
    )
    recommended_diet: list[str] = Field(
        default_factory=list,
        description="끼니별 식단 제안 칩 (아침/점심/저녁)",
    )
    recommended_challenges: list[RecommendedChallengeItem] = Field(
        default_factory=list,
        description="구조화 추천 챌린지 카드 (프론트가 카드로 렌더; LLM 미선정·eligible 없음이면 빈 배열)",
    )
    has_required_data: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    action_hint: str | None = Field(
        default=None,
        description='has_required_data=false 일 때 "navigate_to_health_info"',
    )
    is_fallback: bool = False
    eval_revision_count: int | None = None
    disclaimer: str = "본 결과는 의학적 진단이 아닌 참고용 위험도 지표입니다."
    model_version: str = "risk-graph-v1"

    # extra dict (디버깅·확장용 — 운영에선 사용 안 함)
    extra: dict[str, Any] = Field(default_factory=dict)
