"""ChatRAGGraph — LangGraph 기반 동기 챗봇 RAG 그래프.

API 계약: `RAG/LangGraph_API계약_chat_v1.md` 의 1단계 (mode=rag).
설계 문서: `RAG/LangGraph_마이그레이션_계획.md` 5장 1단계.

노드 흐름:
    classify_intent
        ├── intent=medical_inquiry/service_guide/general
        └── needs_health_data 분류
    decide_after_classify
        ├── needs_health_data=true → fetch_health_data
        └── 그 외                  → retrieve (일반)
    fetch_health_data — DB 조회: UserHealthInfo + 최근 HealthRecord + 최근 DiseaseRisk
    decide_after_fetch_health
        ├── has_data=true  → retrieve (개인화: health snapshot 을 generate 컨텍스트에 주입)
        └── has_data=false → final_missing_info (입력 페이지 이동 안내)
    retrieve → generate → evaluate (2-stage: 1차 Rule → 2차 LLM, 3-way 분류 + 카운트 게이트)
        ├── pass                                            → final_ok            (케이스 1)
        ├── generation_problem + revision_count<MAX         → generate            (케이스 2: 재생성)
        ├── retrieval_problem  + revision_count<MAX         → rewrite_query       (케이스 3: 재검색)
        └── revision_count >= MAX                           → final_fallback      (케이스 4)
    rewrite_query
        └── 원 질문 + 이전 평가 피드백 → 새 검색 쿼리 → retrieve 재진입

evaluate 내부 (한 노드, 2단계):
    1차 Rule-based (결정적, LLM 호출 없음)
        R1. 검색 결과 없음           → retrieval_problem
        R2. 답변 길이 < 30자          → generation_problem
        R3. 단정/약물 직접 권고 표현  → generation_problem
        R4. medical_inquiry 인데 의사 상담 권고 누락 → generation_problem
    1차 fail → 즉시 분류 종료, LLM 평가 스킵.
    1차 pass → 2차 LLM-based (6가지 기준):
        1) 질문 직접 답변  2) 근거 충실성  3) 수치 해석 정확성
        4) 위험도 과장 여부  5) 권고 구체성  6) 금기/주의 문구 필요성

상태: `ChatState` TypedDict — user_id/thread_id/original_question/intent/
    needs_health_data/missing_fields/health_data/retrieval_query/retrieved_docs/
    draft_answer/eval_result/eval_stage/eval_revision_count/eval_feedback/
    final_answer/sources/is_fallback/action_hint/disclaimer.
"""

from __future__ import annotations

import functools
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.core import config
from app.models.health import (
    DiseaseRisk,
    DiseaseType,
    HealthRecord,
    RecordType,
    UserHealthInfo,
)
from app.services.ml.retrieval import RetrievedChunk, SourceType, retrieve

_logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 상수 / 정책
# ─────────────────────────────────────────────
MAX_REVISIONS = 2  # 재검색·재생성 합산 상한 (API 계약 eval_revision_count 0~2)
RETRIEVE_TOP_K = 5  # 일반/서비스 기본
# medical_inquiry 는 생활요법·약물·추적·위험도 4측면이 한 번에 잡혀야 답변 완전성↑.
# top_k 를 5→8 로 확장 (broader context). RRF 후보 풀도 자동으로 늘어남.
RETRIEVE_TOP_K_MEDICAL = 8
MIN_ANSWER_LEN = 30  # 1차 Rule R2: 답변 최소 글자 수

MEDICAL_DISCLAIMER = "본 답변은 의학적 진단을 대체하지 않습니다."
SERVICE_DISCLAIMER = ""
GENERAL_DISCLAIMER = MEDICAL_DISCLAIMER

MISSING_INFO_MESSAGE = "개인화된 답변을 드리려면 건강 정보가 필요해요. 건강 정보 입력 페이지로 이동하시겠습니까?"
# 인사 즉시 응답 — retrieve/generate/evaluate 전부 스킵하여 0.5초 이내 응답.
GREETING_REPLY = (
    "안녕하세요! 무엇을 도와드릴까요? 건강 관련 질문이나 챗봇·챌린지 사용법이 궁금하시면 편하게 말씀해 주세요."
)
# intent 별 fallback 메시지 — 서비스 가이드 답변에 의료 면책이 끼면 어색하므로 분기.
FALLBACK_MEDICAL = (
    "현재 해당 질문에 대해 신뢰할 수 있는 답변을 생성하기 어려워요. "
    "구체적인 의료 사항은 담당 의사 또는 약사와 상담하시기를 권장합니다."
)
FALLBACK_SERVICE = (
    "찾으시는 기능 안내를 정확히 드리기 어려워요. 잠시 후 다시 시도하시거나 고객 지원/도움말 페이지에서 확인해 주세요."
)
# 호환: 기존 import 경로 (`from app.graphs.chat_rag_graph import FALLBACK_MESSAGE`) 유지.
FALLBACK_MESSAGE = FALLBACK_MEDICAL

# 1차 Rule R3 — 단정적 진단 표현(수치/상태) 정규식.
# "정상이에요"/"위험해요"/"비정상이네요" 같은 다양한 한국어 어미 변형을 한 번에 잡되,
# "정상 범위" 처럼 평가가 아닌 표현은 일부러 제외 (false positive 회피).
_DIAGNOSTIC_ASSERTION_PATTERN = re.compile(
    r"(정상이|비정상이|위험하|안전하|확진(하|되|이))"
    r"(다|에요|네요|어요|군요|시네요|시군요|시다|었|시었|니까|시니까)"
    r"|확진입니다|당신은 환자|단언"
)

# 1차 Rule R3 — 약물 직접 권고 패턴 (특정 약/용법을 직접 권유). 일반적 한국어 변형 다수 커버.
_DRUG_DIRECT_RECOMMENDATIONS = (
    "을 드세요",
    "를 드세요",
    "을 복용하세요",
    "를 복용하세요",
    "복용을 권합니다",
    "복용을 권장합니다",
    "처방받으세요",
    "처방을 받으세요",
    "약을 추천",
)

# 1차 Rule R4 — 의료 답변에 있어야 하는 권고 키워드 (하나라도 있으면 OK)
_MEDICAL_REQUIRED_PHRASES = ("의사", "전문의", "전문가", "상담", "병원")

# 1차 Rule R4 — intent=general 로 (오)분류돼도 답변에 의료 토픽이 등장하면 권고를 강제.
# classify_intent 의 single point of failure 를 방어한다.
_MEDICAL_TOPIC_KEYWORDS = (
    "당뇨",
    "고혈압",
    "혈압",
    "혈당",
    "HbA1c",
    "당화혈색소",
    "콜레스테롤",
    "LDL",
    "HDL",
    "중성지방",
    "이상지질혈증",
    "심혈관",
    "약물",
    "복용",
    "처방",
    "인슐린",
    "스타틴",
)

# classify_intent prefilter — 명백한 인사/단답에서 LLM 호출 생략용 보수적 패턴.
# 매치 조건이 모두 만족할 때만 prefilter 적용 (의료/서비스 키워드 하나라도 있으면 LLM 으로 fallthrough).
# `좋은\s*아침` 처럼 띄어쓰기 변형까지 커버. 어미 변형(`~이야`/`~이에요`/`~예요`)은
# 뒤쪽 `[\s가-힣\w!?.,~]*` 가 흡수.
_GREETING_PATTERN = re.compile(
    r"^(안녕|안뇽|하이|hi|hello|반가|반갑|"
    r"좋은\s*(아침|오후|저녁|밤|하루)|"
    r"잘\s*(지내|있|있어|있나|있었)|오랜만|처음\s*뵙|"
    r"고마|감사|땡큐|thanks?|thank|"
    r"잘가|잘자|굿\s*모닝|굿\s*나잇|"
    r"수고|수고하|좋은\s*하루)"
    r"[\s가-힣\w!?.,~^]*[?.!~^]?$",
    re.IGNORECASE,
)
# prefilter 활성 글자 수 상한 — 길어지면 의도 모호해지므로 LLM 으로.
# 30자: "좋은 아침이에요 오늘도 잘 부탁드려요" 정도까지 커버.
_PREFILTER_MAX_LEN = 30

# 본인 상태 평가 요청 강제 가드 — classify LLM 이 needs_health_data=False 로 잘못
# 분류해도 명백한 1인칭 상태 질문이면 강제로 true 로 끌어올림 (2차 검수 N1 보호 가드).
# 예: "나 어때?", "내 상태 어때?", "나는?", "나 괜찮아?", "저는 어때요" — 정규식 매치 시 true.
#
# false positive 방지 (보안 리뷰 H-1):
#   - 단독 명사("건강"/"상태"/"컨디션")는 일반 의료 질문과 구분 안 돼 매치하지 않음.
#     ("내 건강식단" / "나 건강검진" / "저 건강관리법" 등 일반 질문 false positive 차단)
#   - 평가 동사/형용사(어때/괜찮/평가/봐줘) 결합 케이스만 본인 상태 평가로 인정.
_PERSONAL_STATUS_PATTERN = re.compile(
    r"^(나|저|내|제)\s*(는|도|만)?\s*"
    # 평가 동사·형용사만 허용 — 단독 "건강/상태/컨디션" 명사는 제거
    r"(어때|어떤가|어떻|괜찮|괜찮은가)"
    r"[\s가-힣\w!?.,~]*[?.!~]?$"
)
# "내/제/나의/저의 + 상태/건강/컨디션 + 평가 동사" — 동사 결합 필수.
_PERSONAL_STATUS_NOUN_PATTERN = re.compile(
    r"^(내|제|나의|저의)\s*(상태|건강|건강\s*상태|컨디션)\s+"
    r"(어때|어떤가|어떻|괜찮|평가|봐줘|봐주세요)"
    r"[\s가-힣\w!?.,~]*[?.!~]?$"
)
# 단독 1인칭 의문문 — "나는?", "저는?", "내가?" (2글자 이상 1인칭만, M-2: "나?"/"저?" 1글자는 제외).
_PERSONAL_BARE_PATTERN = re.compile(r"^(나는|저는|내가|제가)\s*\?\s*$")


def _looks_like_personal_status_question(text: str) -> bool:
    """LLM 분류 보강 — 명백한 본인 상태 평가 요청 여부 (휴리스틱)."""
    stripped = text.strip()
    if len(stripped) > 20:  # 너무 길면 의도 다른 키워드 섞일 가능성 → LLM 신뢰
        return False
    return bool(
        _PERSONAL_STATUS_PATTERN.match(stripped)
        or _PERSONAL_STATUS_NOUN_PATTERN.match(stripped)
        or _PERSONAL_BARE_PATTERN.match(stripped)
    )


IntentLiteral = Literal["medical_inquiry", "service_guide", "general"]
EvalResultLiteral = Literal["pass", "generation_problem", "retrieval_problem"]
EvalStageLiteral = Literal["rule", "llm"]
# classify_intent 가 분류해 retrieve.disease 필터로 전달하는 질환 키.
DiseaseLiteral = Literal["diabetes", "hypertension", "dyslipidemia", "general"]


# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────
class ChatState(TypedDict, total=False):
    """ChatRAGGraph 의 노드 간 공유 상태."""

    # 입력
    # user_id 는 프로젝트 User PK 의 int → UUID 전환 잔여 도메인에 걸쳐 있어 Any.
    # Tortoise filter 가 실제 컬럼 타입에 맞춰 처리한다.
    user_id: Any
    thread_id: str
    original_question: str

    # classify_intent
    intent: IntentLiteral
    # diseases — multi-disease 라우팅 지원. 1개면 단일 질환, 2개면 OR 매치.
    # 예: "당뇨병 환자의 이상지질혈증" → ["diabetes", "dyslipidemia"]
    diseases: list[DiseaseLiteral]
    needs_health_data: bool
    needs_challenge_catalog: bool  # 챌린지 카탈로그를 함께 검색 (medical+service 혼합)
    missing_fields: list[str]
    action_hint: str | None
    is_greeting: bool  # prefilter hit 신호 — retrieve/generate 모두 스킵하고 final_greeting 으로

    # fetch_health_data
    health_data: dict[str, Any] | None
    # needs_health_data 와 별개: 사용자가 DB 에 의미 있는 건강 데이터를 갖고 있는지.
    # 분기 매트릭스: needs=true & has=false → MISSING_INFO, needs=true & has=true → 개인화,
    # needs=false → 일반 RAG (has 무관).
    has_health_data: bool

    # retrieve
    retrieval_query: str
    retrieved_docs: list[RetrievedChunk]

    # generate / evaluate 루프
    draft_answer: str
    eval_result: EvalResultLiteral
    eval_stage: EvalStageLiteral  # 어느 단계(rule/llm)에서 결정됐는지 (디버깅·감사)
    eval_revision_count: int
    eval_feedback: str

    # final
    final_answer: str
    sources: list[RetrievedChunk]
    is_fallback: bool
    disclaimer: str
    model_version: str
    confidence: float

    error: str | None


# ─────────────────────────────────────────────
# 결과 타입 (그래프 외부 반환용)
# ─────────────────────────────────────────────
@dataclass(slots=True)
class ChatRAGResult:
    answer: str
    sources: list[RetrievedChunk] = field(default_factory=list)
    intent: IntentLiteral = "general"
    needs_health_data: bool = False
    has_health_data: bool = False  # 사용자가 DB 에 의미 있는 건강 데이터를 갖고 있는지
    missing_fields: list[str] = field(default_factory=list)
    action_hint: str | None = None
    is_fallback: bool = False
    eval_revision_count: int | None = None
    disclaimer: str = MEDICAL_DISCLAIMER
    confidence: float = 0.0
    model_version: str = "chatragraph-v1"


# ─────────────────────────────────────────────
# OpenAI 클라이언트
# ─────────────────────────────────────────────
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 비어 있어 ChatRAGGraph 를 실행할 수 없습니다.")
        # 운영 안정성: SDK 기본 timeout 600s 는 OpenAI stall 시 FastAPI 워커를 분 단위로
        # 점유. config 의 짧은 timeout + 짧은 retry 로 그래프가 fallback 노드로 빠지게 함.
        _client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_REQUEST_TIMEOUT,
            max_retries=config.OPENAI_MAX_RETRIES,
        )
    return _client


def _safe_err_repr(e: BaseException) -> str:
    head = str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {head[:160]}"


def _timed_node(func: Callable[[ChatState], Awaitable[dict[str, Any]]]) -> Any:
    """노드 함수 데코레이터 — 시작/종료 시각 + 소요 ms 를 INFO 로 기록.

    REPL/로컬 디버깅 시 logging level INFO 이상이면 노드별 소요 시간이 가시화된다.
    운영에서는 로깅 레벨로 끄면 그대로 비활성.

    return Any: LangGraph `StateGraph.add_node` 의 광범위한 generic union 시그니처와
    호환되게 하기 위해 wrapper 타입을 Any 로 노출 (정확한 타입 매칭은 라이브러리 내부에서).
    """

    @functools.wraps(func)
    async def wrapper(state: ChatState) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            return await func(state)
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            _logger.info("[node:%s] %.0fms", func.__name__, elapsed_ms)

    return wrapper


# ─────────────────────────────────────────────
# 노드 1: classify_intent
# ─────────────────────────────────────────────
_CLASSIFY_PROMPT = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 생활습관 관리 챗봇의 라우터입니다.
사용자의 질문을 분석해 아래 JSON 형식으로만 응답하세요. JSON 외 텍스트는 절대 포함하지 마세요.

{{
  "intent": "medical_inquiry" | "service_guide" | "general",
  "diseases": ["diabetes" | "hypertension" | "dyslipidemia"],
  "needs_health_data": true | false,
  "needs_challenge_catalog": true | false,
  "missing_fields": [],
  "rationale": "한 줄 설명"
}}

== intent ==
- "medical_inquiry": 의학 정보 질문 (증상·진단 기준·약물·식이·운동·합병증·검사 등)
- "service_guide": 앱 사용법·챌린지·포인트·인증·로그인 등 기능 안내 질문
- "general": 위 둘에 명확히 안 맞거나 인사·잡담
- 둘 다 관련된 혼합형(예: "내 상태에 맞는 식단·챌린지")은 medical_inquiry 우선.

== needs_challenge_catalog ==
질문이 **챌린지/운동 프로그램/생활습관 챌린지 추천**을 요구하는지.
- true: "어떤 챌린지", "챌린지 추천", "운동 프로그램 추천", "식단·챌린지", "생활습관 챌린지" 등
- false: 챌린지와 무관한 일반 의학 질문 / 서비스 사용법 질문
true 면 retrieve 가 의료 진료지침과 함께 CHALLENGE_CATALOG 도 함께 검색해 답변 근거로 사용.

== diseases (list) ==
질문이 관련된 질환들을 list 로 (1개 또는 여러 개). 빈 list 면 질환 비특화 / 서비스 질문.
- "diabetes": 당뇨·혈당·HbA1c·당화혈색소·인슐린·당뇨병 합병증
- "hypertension": 고혈압·혈압 (수축기/이완기)·DASH 식단
- "dyslipidemia": 이상지질혈증·콜레스테롤·LDL·HDL·중성지방·스타틴·동맥경화
예시:
- "당뇨병 진단 기준" → ["diabetes"]
- "당뇨병 환자의 이상지질혈증 관리" → ["diabetes", "dyslipidemia"] (multi-disease 라우팅)
- "운동 권고" → [] (질환 비특화)
- "챌린지 인증 방법" → [] (서비스 질문)

== needs_health_data ==
다음 조건 중 하나라도 해당하면 **true** (보수적으로 풀게 분류 — 본인 상태 의심되면 true):
- (a) 1인칭 표현 + 본인 상태/수치 평가: "내", "제", "나는", "나에게", "본인", "나의", "내가"
  등이 본인의 건강 상태/측정값/위험도/추천에 결부됨
- (b) 본인 데이터 해석/판단 요청: "내가 위험한지", "나에게 맞는 ~", "내 수치 어때"
- (c) 본인 측정값을 보고 답해야 하는 질문: "내 혈압이 정상?", "내 BMI 어때?"
- (d) **짧고 모호한 1인칭 상태 질문도 true** — "나 어때?", "내 상태?", "나는?",
  "나 괜찮아?", "어떤가요 저는?", "지금 저 어때?" 같이 본인 데이터를 전제로 한
  포괄적 평가 요청. 의도가 모호해도 **본인 평가/추천을 묻는 뉘앙스면 true**.

다음은 **false**:
- 일반 의학 정보 질문 ("DASH 식단이란?", "당뇨병 진단 기준은?", "고혈압 약 부작용은?")
- 일반 권고 질문 ("고혈압 환자는 어떤 운동?") — 본인이 명시되지 않음
- 인사/잡담 ("안녕", "고마워")

같은 주제도 1인칭이 붙으면 true 로 전환:
- "고혈압 식단" → false / "내 고혈압 식단" → true
- "당뇨 위험" → false / "내가 당뇨 위험군인지" → true
- "건강 상태 평가법" → false / "나 어때" → **true** (본인 평가 요청)

== missing_fields ==
needs_health_data=true 일 때 필요한 데이터 필드명을 한국어 키워드 또는 표준 영문 키 중 알아보기 쉬운 쪽으로:
- 혈압 관련: ["blood_pressure"]
- 혈당 관련: ["blood_glucose"] (HbA1c 면 ["hba1c"])
- 체중/BMI: ["weight_kg", "height_cm"]
- 콜레스테롤: ["cholesterol"]
- 종합/추천형: ["profile"] 또는 위 필드 조합
needs_health_data=false 면 missing_fields=[].

질문: {question}
"""


def _heuristic_prefilter(question: str) -> dict[str, Any] | None:
    """LLM 호출 없이 즉시 결정 가능한 매우 보수적 케이스만 prefilter.

    적용 조건 (모두 만족):
      1. 메시지 길이 ≤ _PREFILTER_MAX_LEN 자
      2. 의료 토픽 키워드 / 서비스(챌린지·포인트·인증·로그인 등) 키워드 미포함
      3. 인사·감사·작별 표현 정규식과 매치

    매치되면 intent=general / needs_health_data=false 로 즉시 반환.
    불일치하면 None 을 돌려 LLM 으로 위임.

    목적: 단답·인사로 인한 불필요한 LLM 비용·지연 제거 (정확도 손실 거의 없음).
    """
    stripped = question.strip()
    if len(stripped) > _PREFILTER_MAX_LEN:
        return None

    # 의료/서비스 토픽 단어가 하나라도 있으면 LLM 분류로 위임.
    lowered = stripped.lower()
    for kw in _MEDICAL_TOPIC_KEYWORDS:
        if kw.lower() in lowered:
            return None
    # 서비스 의심 키워드 — 일부만 (포인트/챌린지/인증/로그인/회원). 명백한 service_guide
    # 판단도 LLM 에 맡겨 보수적으로 처리.
    for kw in ("챌린지", "포인트", "인증", "로그인", "회원", "알림", "예측"):
        if kw in stripped:
            return None

    if not _GREETING_PATTERN.match(stripped):
        return None

    return {
        "intent": "general",
        "disease": None,
        "needs_health_data": False,
        "missing_fields": [],
        "action_hint": None,
    }


async def classify_intent(state: ChatState) -> dict[str, Any]:
    # 보수적 휴리스틱으로 명백한 인사·단답은 LLM 호출 없이 즉시 결정.
    # is_greeting=True 면 decide_after_classify 가 final_greeting 로 곧장 분기해 retrieve/generate 모두 스킵.
    prefilter = _heuristic_prefilter(state["original_question"])
    if prefilter is not None:
        _logger.info("classify_intent prefilter hit (skip LLM, skip retrieve/generate)")
        return {**prefilter, "is_greeting": True}

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "한국어로 분류만 수행하는 JSON 응답기."},
                {"role": "user", "content": _CLASSIFY_PROMPT.format(question=state["original_question"])},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:  # noqa: BLE001
        _logger.warning("classify_intent 실패, general 폴백: %s", _safe_err_repr(e))
        return {
            "intent": "general",
            "disease": None,
            "needs_health_data": False,
            "missing_fields": [],
            "action_hint": None,
        }

    intent = data.get("intent")
    if intent not in ("medical_inquiry", "service_guide", "general"):
        intent = "general"

    # diseases — list 로 수신. 단일 문자열로 들어오는 백워드 케이스도 흡수.
    raw_diseases = data.get("diseases")
    if raw_diseases is None:
        # 옛 single-field 케이스 대비
        legacy_disease = data.get("disease")
        raw_diseases = [legacy_disease] if legacy_disease else []
    if not isinstance(raw_diseases, list):
        raw_diseases = [raw_diseases]
    diseases = [str(d) for d in raw_diseases if d in ("diabetes", "hypertension", "dyslipidemia")][:3]

    needs = bool(data.get("needs_health_data", False))
    needs_challenge = bool(data.get("needs_challenge_catalog", False))
    missing = data.get("missing_fields") or []
    if not isinstance(missing, list):
        missing = []
    missing = [str(x) for x in missing][:8]

    # N1 가드: 명백한 본인 상태 평가 요청("나 어때?", "내 상태")은 LLM 결과가 false 여도
    # 강제 true 로 끌어올려 fetch_health_data 경로로. intent 도 medical_inquiry 로 정규화.
    if not needs and _looks_like_personal_status_question(state["original_question"]):
        _logger.info("classify_intent N1 guard hit — 본인 상태 질문 강제 분류")
        needs = True
        intent = "medical_inquiry"
        if not missing:
            missing = ["profile"]

    return {
        "intent": intent,
        "diseases": diseases,
        "needs_health_data": needs,
        "needs_challenge_catalog": needs_challenge,
        "missing_fields": missing if needs else [],
        "action_hint": "navigate_to_health_info" if needs else None,
    }


def decide_after_classify(state: ChatState) -> Literal["final_greeting", "fetch_health_data", "retrieve"]:
    if state.get("is_greeting"):
        return "final_greeting"
    return "fetch_health_data" if state.get("needs_health_data") else "retrieve"


async def final_greeting(state: ChatState) -> dict[str, Any]:
    """인사/단답 즉시 응답 노드 — retrieve/generate/evaluate 전부 스킵.

    classify_intent prefilter hit 케이스에서만 진입한다. LLM 호출 0회 + DB 조회 0회 →
    응답 시간 < 0.5초.
    """
    return {
        "final_answer": GREETING_REPLY,
        "sources": [],
        "is_fallback": False,
        "disclaimer": "",  # 인사 답변엔 의료 면책 불필요
        "confidence": 1.0,
        "model_version": "chatragraph-v1",
    }


# ─────────────────────────────────────────────
# 노드: fetch_health_data
# ─────────────────────────────────────────────
async def _fetch_user_health_snapshot(user_id: Any) -> dict[str, Any] | None:
    """사용자의 정적 프로필 + 측정값 type 별 최신 1건 + 질환별 최신 위험도를 일괄 조회.

    Returns:
        None: 사용자가 건강 정보를 **한 번도 의미 있게 입력하지 않음** (UserHealthInfo row 가 없거나,
              row 는 있어도 핵심 필드가 비어 있고 HealthRecord 도 전혀 없는 상태)
        dict: profile/recent_records/disease_risks 키를 갖는 스냅샷
    """
    profile = await UserHealthInfo.filter(user_id=user_id).first()

    recent_records: dict[str, dict[str, Any]] = {}
    for rt in RecordType:
        rec = (
            await HealthRecord.filter(user_id=user_id, record_type=rt, is_deleted=False)
            .order_by("-measured_at")
            .first()
        )
        if rec is None:
            continue
        recent_records[rt.value] = {
            "primary_value": float(rec.primary_value),
            "secondary_value": float(rec.secondary_value) if rec.secondary_value is not None else None,
            "unit": rec.unit,
            "sub_type": str(rec.sub_type) if rec.sub_type else None,
            "measured_at": rec.measured_at.isoformat(),
        }

    risks: dict[str, dict[str, Any]] = {}
    for dt in DiseaseType:
        r = await DiseaseRisk.filter(user_id=user_id, disease_type=dt).order_by("-calculated_at").first()
        if r is None:
            continue
        risks[dt.value] = {
            "risk_score": float(r.risk_score),
            "risk_level": str(r.risk_level),
            "calculated_at": r.calculated_at.isoformat(),
        }

    # has_data 판단: 핵심 프로필 필드(키·체중·허리) 또는 측정값(HealthRecord) 중 하나라도 있어야 인정
    has_profile_core = profile is not None and (
        profile.height_cm is not None or profile.weight_kg is not None or profile.waist_cm is not None
    )
    has_data = has_profile_core or len(recent_records) > 0

    if not has_data:
        return None

    snapshot: dict[str, Any] = {
        "profile": (
            {
                "height_cm": float(profile.height_cm) if profile and profile.height_cm is not None else None,
                "weight_kg": float(profile.weight_kg) if profile and profile.weight_kg is not None else None,
                "waist_cm": float(profile.waist_cm) if profile and profile.waist_cm is not None else None,
                "is_smoker": bool(profile.is_smoker) if profile else False,
                "alcohol_intake": str(profile.alcohol_intake) if profile else None,
                "has_diabetes_family_history": bool(profile.has_diabetes_family_history) if profile else False,
                "has_hypertension_family_history": (
                    bool(profile.has_hypertension_family_history) if profile else False
                ),
                "is_chronic_patient": bool(profile.is_chronic_patient) if profile else False,
                "diseases": list(profile.diseases) if profile else [],
                "medications": list(profile.medications) if profile else [],
            }
            if profile is not None
            else {}
        ),
        "recent_records": recent_records,
        "disease_risks": risks,
    }
    return snapshot


async def fetch_health_data(state: ChatState) -> dict[str, Any]:
    """사용자 건강 정보 조회 — has_health_data 플래그를 채워 분기 매트릭스의 한 축을 결정.

    needs_health_data(질문이 요구하는지) 는 classify 결과 그대로 보존.
    프론트는 (needs && !has) 일 때만 CTA 를 표시하면 된다.
    missing_fields/action_hint 는 데이터 부재 시에만 활성 (개인화 답변엔 비움).
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"health_data": None, "has_health_data": False}
    try:
        snapshot = await _fetch_user_health_snapshot(user_id)
    except Exception as e:  # noqa: BLE001
        _logger.warning("fetch_health_data 실패, 미입력으로 처리: %s", _safe_err_repr(e))
        return {"health_data": None, "has_health_data": False, "error": _safe_err_repr(e)}

    if snapshot is not None:
        # 데이터 보유 → 개인화 답변 경로. needs_health_data 는 분류 결과 그대로 유지.
        # missing_fields/action_hint 는 비움 (CTA 표시 안 함).
        return {
            "health_data": snapshot,
            "has_health_data": True,
            "missing_fields": [],
            "action_hint": None,
        }
    # 데이터 부재 — needs_health_data 와 결합되면 final_missing_info 로.
    return {"health_data": None, "has_health_data": False}


def decide_after_fetch_health(state: ChatState) -> Literal["retrieve", "final_missing_info"]:
    # has_health_data 가 명시적 플래그 — health_data dict 존재 여부와 동치이나 의미를 명확히 함.
    return "retrieve" if state.get("has_health_data") else "final_missing_info"


async def final_missing_info(state: ChatState) -> dict[str, Any]:
    return {
        "final_answer": MISSING_INFO_MESSAGE,
        "sources": [],
        "is_fallback": False,
        "disclaimer": MEDICAL_DISCLAIMER,
        "confidence": 0.0,
        "model_version": "chatragraph-v1",
    }


# ─────────────────────────────────────────────
# 노드: retrieve
# ─────────────────────────────────────────────
def _intent_to_source_type(intent: IntentLiteral) -> SourceType:
    if intent == "medical_inquiry":
        return "medical"
    if intent == "service_guide":
        return "service"
    return "all"


async def retrieve_node(state: ChatState) -> dict[str, Any]:
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    source_type = _intent_to_source_type(intent)
    # multi-disease 라우팅. ChatState 의 diseases: list[DiseaseLiteral] 을 retrieve 의
    # `disease: str | list[str] | None` 시그니처와 맞추기 위해 list[str] 로 좁힘.
    diseases: list[str] = [str(d) for d in (state.get("diseases") or [])]
    query = state.get("retrieval_query") or state["original_question"]
    needs_challenge = bool(state.get("needs_challenge_catalog"))

    # medical 인데 챌린지 추천이 필요하면 source_type=all 로 확장해 진료지침 + CHALLENGE_CATALOG
    # 둘 다 검색. 단일 source 만 잡혀 우리 서비스에 없는 챌린지를 LLM 이 생성하는 할루시 방지.
    if source_type == "medical" and needs_challenge:
        source_type = "all"

    # medical 영역은 4측면(목표·생활요법·약물·추적) 동시 커버를 위해 broader top_k.
    top_k = RETRIEVE_TOP_K_MEDICAL if intent == "medical_inquiry" else RETRIEVE_TOP_K

    try:
        result = await retrieve(
            query=query,
            top_k=top_k,
            source_type=source_type,
            disease=diseases if diseases else None,
        )
    except Exception as e:  # noqa: BLE001
        _logger.warning("retrieve 실패, 빈 결과로 진행: %s", _safe_err_repr(e))
        return {"retrieved_docs": [], "retrieval_query": query, "error": _safe_err_repr(e)}

    return {"retrieved_docs": result.chunks, "retrieval_query": query}


# ─────────────────────────────────────────────
# 노드: generate (health_data 컨텍스트 주입)
# ─────────────────────────────────────────────
_MEDICAL_SYSTEM = """당신은 만성질환(고혈압·당뇨·이상지질혈증) 환자의 생활습관 관리를 돕는 한국어 의료 챗봇입니다.

규칙:
1. 제공된 컨텍스트(진료지침)에 근거해서만 답하고, 컨텍스트에 없는 사실은 추측하지 마세요.
2. **수치·정량 정보는 반드시 본문에 인용하세요** (의료 답변의 완전성 핵심):
   - 진단·관리 목표: 구체 수치 (예: "LDL-C 100 mg/dL 미만, 위험인자 동반 시 70 mg/dL 미만",
     "가정혈압 135/85 mmHg 미만").
   - 생활요법: 정량 권고 (예: "나트륨 하루 2,400 mg 미만 / 소금 6 g 미만", "유산소 운동 주 5~7회,
     하루 30분 이상 중강도", "절주 — 남성 2잔/일, 여성 1잔/일 이하").
   - 추적 검사 주기 (예: "당뇨 환자 지질 검사 진단 시 + 매년 1회 이상").
   - "관리가 중요합니다" 같은 모호한 일반론 금지. 컨텍스트에 수치가 있으면 그 수치를 인용.
3. **의료 질문의 4가지 측면을 모두 다루세요** (해당 컨텍스트 있으면):
   - (a) 관리 목표 (target — 수치·범위)
   - (b) 생활요법 (식사·운동·체중·금연·절주 — 정량 권고)
   - (c) 약물치료 (필요 시점·일반 원칙. 특정 약 직접 권고는 금지)
   - (d) 추적 관리 (검사 주기·재평가 시점)
4. [사용자 건강 정보] 블록이 제공되면 **반드시** 그 데이터의 수치를 답변 본문에 명시 인용하고
   진료지침과 비교한 **일반적인 경향**을 설명하세요.
   - 예: "사용자의 최근 혈압 130/85 mmHg 는 진료지침 정상 범위(120/80 미만)를 다소 벗어나는 경향입니다."
   - 절대 단정적 진단/위험 등급 부여 금지 ("당신은 당뇨입니다", "정상입니다", "위험합니다" 같은 표현 금지).
   - "정상 범위", "권고 범위 안/밖" 표현은 사용 가능. "정상이다 / 비정상이다" 단정은 금지.
   - 약물 복용 결정·용량·특정 약 직접 권고 절대 금지.
5. 답변 끝에 반드시 "정확한 평가와 처방은 담당 의사 또는 약사와 상담하세요" 권고 포함.
6. [사용자 건강 정보] 블록이 **없으면** 일반 의학 정보로만 답하고, 본인 데이터에 대한 가정·추측 금지.
7. [챌린지 카탈로그] 자료가 제공된 경우 그 안에 정의된 챌린지(걷기/러닝/식단/물 마시기 등) 만
   추천하고, 사용자 상태(가족력·위험도·측정값) 와 매핑된 **구체 목표 예시**(예: "주 5일, 하루 30분 걷기")
   를 포함하세요. 카탈로그에 없는 챌린지(예: 임의 "30일 챌린지") 절대 생성 금지.
8. 답변은 명확하고 간결하게. 불릿/문단 구성으로 읽기 좋게. 출처는 본문에 넣지 말고 사실만 전달."""

_SERVICE_SYSTEM = """당신은 만성질환 생활습관 관리 서비스의 사용 안내 챗봇입니다.

규칙:
1. 제공된 서비스 가이드 컨텍스트에 근거해서만 답하세요.
2. 의료 정보·진단 관련 질문이면 정중히 거절하고 의료 챗봇 모드로 이동하라고 안내.
3. 답변은 단계별 절차나 기능 설명으로 명확하게.
4. 의료 면책 문구는 포함하지 않습니다."""


def _format_context(docs: list[RetrievedChunk]) -> str:
    if not docs:
        return "(검색된 컨텍스트가 없습니다.)"
    parts: list[str] = []
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        title = d.title or meta.get("section_title") or d.source
        pages = meta.get("source_pages")
        header = f"[자료 {i}] 출처: {d.source}" + (f" / p.{pages}" if pages else "") + f" — {title}"
        parts.append(header + "\n" + d.chunk_text)
    return "\n\n".join(parts)


def _format_profile_block(profile: dict[str, Any]) -> list[str]:  # noqa: C901 — 필드 합치는 평면 흐름
    """UserHealthInfo 정적 프로필 직렬화."""
    lines: list[str] = []
    h = profile.get("height_cm")
    w = profile.get("weight_kg")
    if h and w:
        bmi = float(w) / ((float(h) / 100) ** 2)
        lines.append(f"- 키 {h}cm, 몸무게 {w}kg, BMI {bmi:.1f}")
    elif h:
        lines.append(f"- 키 {h}cm")
    elif w:
        lines.append(f"- 몸무게 {w}kg")
    if profile.get("waist_cm"):
        lines.append(f"- 허리둘레 {profile['waist_cm']}cm")
    if profile.get("is_smoker"):
        lines.append("- 흡연자")
    alcohol = profile.get("alcohol_intake")
    if alcohol and alcohol != "NONE":
        lines.append(f"- 음주: {alcohol}")
    fam: list[str] = []
    if profile.get("has_diabetes_family_history"):
        fam.append("당뇨")
    if profile.get("has_hypertension_family_history"):
        fam.append("고혈압")
    if fam:
        lines.append(f"- 가족력: {', '.join(fam)}")
    if profile.get("is_chronic_patient"):
        lines.append("- 만성질환 환자")
    diseases = profile.get("diseases") or []
    if diseases:
        lines.append(f"- 진단받은 질환: {', '.join(str(d) for d in diseases)}")
    medications = profile.get("medications") or []
    if medications:
        lines.append(f"- 복용 약물: {', '.join(str(m) for m in medications)}")
    return lines


def _format_records_block(records: dict[str, dict[str, Any]]) -> list[str]:
    """HealthRecord type 별 최근 측정값 직렬화."""
    lines: list[str] = []
    for rt, rec in records.items():
        v = rec["primary_value"]
        v2 = rec.get("secondary_value")
        unit = rec["unit"]
        sub = rec.get("sub_type")
        ts = rec["measured_at"][:10]
        val = f"{v}/{v2}" if v2 is not None else f"{v}"
        sub_str = f" ({sub})" if sub else ""
        lines.append(f"- 최근 {rt}{sub_str}: {val} {unit} ({ts})")
    return lines


def _format_risks_block(risks: dict[str, dict[str, Any]]) -> list[str]:
    """DiseaseRisk 질환별 최근 위험도 직렬화."""
    return [
        f"- 최근 {dt} 위험도: {r['risk_level']} (점수 {r['risk_score']:.1f}, {r['calculated_at'][:10]})"
        for dt, r in risks.items()
    ]


def _format_health_snapshot(snap: dict[str, Any] | None) -> str:
    """ChatState.health_data 를 LLM 컨텍스트용 텍스트 블록으로 직렬화.

    진단·단정 표현 없이 raw 수치와 정적 프로필만 노출. 진료지침과 대조한 "경향" 표현은
    system prompt 가 강제한다. 필드별 분리 헬퍼(_format_*_block)로 구성 (L-1).
    """
    if not snap:
        return ""

    lines: list[str] = ["[사용자 건강 정보 — 진단 아님, 참고용]"]
    lines.extend(_format_profile_block(snap.get("profile") or {}))
    lines.extend(_format_records_block(snap.get("recent_records") or {}))
    lines.extend(_format_risks_block(snap.get("disease_risks") or {}))
    return "\n".join(lines) + "\n\n"


async def generate_node(state: ChatState) -> dict[str, Any]:
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    docs = state.get("retrieved_docs", [])
    system = _SERVICE_SYSTEM if intent == "service_guide" else _MEDICAL_SYSTEM
    context = _format_context(docs)
    health_block = _format_health_snapshot(state.get("health_data"))

    feedback = state.get("eval_feedback", "")
    feedback_hint = f"\n\n[Evaluator 피드백] 이전 답변에서 보완할 점: {feedback}" if feedback else ""

    user_prompt = (
        f"질문: {state['original_question']}\n\n"
        f"{health_block}"
        f"컨텍스트:\n{context}\n\n"
        f"위 정보(사용자 건강 정보가 있다면 그것 포함)를 사용해 한국어로 답변하세요. "
        f"컨텍스트에 답이 없으면 솔직히 모른다고 말하고 의료 전문가와 상담을 권하세요."
        f"{feedback_hint}"
    )

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        draft = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        _logger.warning("generate 실패: %s", _safe_err_repr(e))
        return {"draft_answer": "", "error": _safe_err_repr(e)}

    return {"draft_answer": draft}


# ─────────────────────────────────────────────
# 노드: evaluate (2-stage)
# ─────────────────────────────────────────────
def _rule_evaluate(state: ChatState) -> tuple[EvalResultLiteral, str]:
    """1차 결정적 평가. (eval_result, feedback) 반환. pass 면 feedback="".

    실패 조건 (하나라도 걸리면 즉시 분류):
      R1. retrieved_docs == [] → retrieval_problem
      R2. draft 길이 < MIN_ANSWER_LEN → generation_problem
      R3. 금지 표현(단정/약물 직접 권고) 포함 → generation_problem
      R4. medical_inquiry 인데 의사 상담 권고 키워드 모두 누락 → generation_problem
    """
    draft = state.get("draft_answer", "")
    docs = state.get("retrieved_docs", [])
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]

    # R1: 문서 없음
    if not docs:
        return (
            "retrieval_problem",
            "[Rule R1] 검색 결과가 비어 있음. 핵심 키워드/동의어로 쿼리 재작성 필요.",
        )

    # R2: 답변 길이 부족 (generate 가 빈 답을 돌려준 경우 포함)
    stripped = draft.strip()
    if len(stripped) < MIN_ANSWER_LEN:
        return (
            "generation_problem",
            f"[Rule R2] 답변이 너무 짧음 ({len(stripped)}자). "
            f"컨텍스트를 인용해 단계별로 다시 작성하고 의사 상담 권고 포함.",
        )

    # R3: 단정적 진단 표현 (정규식 — 한국어 어미 변형 커버)
    diag_match = _DIAGNOSTIC_ASSERTION_PATTERN.search(draft)
    if diag_match:
        return (
            "generation_problem",
            f"[Rule R3] 단정적 진단 표현 '{diag_match.group(0)}' 사용 금지. "
            f"'경향/범위' 표현으로 바꾸고 의사 상담 권고 추가하여 재작성.",
        )
    # R3: 약물 직접 권고
    for phrase in _DRUG_DIRECT_RECOMMENDATIONS:
        if phrase in draft:
            return (
                "generation_problem",
                f"[Rule R3] 약물 직접 권고 '{phrase}' 금지. 일반 정보 안내 + '담당 의사·약사 상담' 권고로 재작성.",
            )

    # R4: 의료 답변에 의사 상담 권고 필수.
    # medical_inquiry 또는 intent=general 인데 본문에 의료 토픽이 등장하면 권고를 강제
    # (classify_intent 오분류 방어).
    needs_advice = intent == "medical_inquiry" or (
        intent == "general" and any(k in draft for k in _MEDICAL_TOPIC_KEYWORDS)
    )
    if needs_advice and not any(p in draft for p in _MEDICAL_REQUIRED_PHRASES):
        return (
            "generation_problem",
            "[Rule R4] 의료 답변에 '의사/전문의/전문가/상담/병원' 권고 누락. 답변 끝에 의사 상담 권고 추가하여 재작성.",
        )

    # R5: 사용자 건강 데이터가 제공됐는데 답변이 본인 실제 수치를 인용하지 않으면 일반론
    # 으로 전락한 것으로 간주 (검수 P7 + 보안 리뷰 M-1).
    # 단순 "숫자 1개라도 있으면 OK" 는 챕터 번호/일반 임계값(120/80)이 우연히 들어와도
    # 통과시켜 약함 → 사용자 스냅샷의 실제 측정값 중 하나라도 답변에 인용됐는지 검사.
    if state.get("has_health_data"):
        snap = state.get("health_data") or {}
        user_numbers = _extract_user_numbers(snap)
        if user_numbers and not any(n in draft for n in user_numbers):
            return (
                "generation_problem",
                "[Rule R5] 사용자 본인 데이터의 실제 수치(예: 혈압 130/85, 체중 70 kg, "
                "BMI 22.5) 가 답변에 인용되지 않음. 사용자 데이터를 본문에 그대로 인용하여 재작성.",
            )

    return ("pass", "")


def _extract_user_numbers(snap: dict[str, Any]) -> set[str]:
    """사용자 health snapshot 에서 실제 수치 토큰을 추출 (답변 인용 여부 검사용).

    프로필 키(height_cm/weight_kg/waist_cm) + 측정값(primary_value/secondary_value).
    숫자는 `f"{v:g}"` 로 정수·소수 둘 다 자연스러운 표기로.
    """
    numbers: set[str] = set()
    profile = snap.get("profile") or {}
    for key in ("height_cm", "weight_kg", "waist_cm"):
        v = profile.get(key)
        if v is not None:
            numbers.add(f"{float(v):g}")
    for rec in (snap.get("recent_records") or {}).values():
        for key in ("primary_value", "secondary_value"):
            v = rec.get(key)
            if v is not None:
                numbers.add(f"{float(v):g}")
    return numbers


_LLM_EVAL_PROMPT = """당신은 의료/서비스 RAG 답변 품질 평가자입니다. 질문·컨텍스트·답변(필요 시 사용자 건강 정보 포함)을 검토하고 6가지 기준으로 진단하세요.

JSON 만 응답하세요:
{{
  "result": "pass" | "generation_problem" | "retrieval_problem",
  "criteria": {{
    "answers_question": true | false,
    "grounded_in_context": true | false,
    "numeric_interpretation_correct": true | false | null,
    "no_risk_exaggeration": true | false,
    "recommendations_specific": true | false,
    "warnings_appropriate": true | false
  }},
  "reason": "한 줄 평가",
  "feedback": "result≠pass 일 때 다음 단계 보강 지시. pass 면 빈 문자열."
}}

평가 기준:
1. answers_question: 질문에 직접 답했는가? (질문과 무관한 일반론만 늘어놓진 않았는가)
2. grounded_in_context: 컨텍스트 근거 안에서 답했는가? (환각·근거 외 사실 인용 없음)
3. numeric_interpretation_correct: 사용자 건강 수치가 제공된 경우 정확히 해석했는가? 건강정보 미제공이면 null.
4. no_risk_exaggeration: 위험도/심각도를 과장하지 않았는가? (불필요한 공포 조장 없음)
5. recommendations_specific (의료 답변 핵심 — 엄격하게 판단):
   - **컨텍스트에 수치·임계값·정량 권고가 있는데 답변이 모호한 일반론만 담고 있으면 false.**
   - 예시: 컨텍스트에 "LDL-C 100 mg/dL 미만" 또는 "유산소 운동 주 5~7회 30분 이상" 같은 정량
     정보가 있는데 답변엔 "콜레스테롤 관리가 중요" / "운동을 늘리세요" 정도만 있으면 false.
   - 의료 답변의 4측면(관리 목표·생활요법·약물·추적 관리) 중 컨텍스트에 있는데 누락된 측면이
     있으면 false (특히 "관리 목표 수치" 누락은 의료 도메인에서 치명적).
   - 컨텍스트 자체가 수치를 안 가지면 true (답변이 일반론이어도 retrieval_problem).
6. warnings_appropriate: 금기/주의 문구가 필요한 상황(약물·임신·증상 등)에서 포함됐는가? 불필요하면 true 처리.

분류 매핑:
- 1·5번이 false → generation_problem (재생성으로 보강 — 5번이면 feedback 에 누락된 수치/측면을 명시)
- 2번이 false 이고 답변이 컨텍스트와 완전히 동떨어졌으면 → retrieval_problem (재검색 필요)
- 2번이 false 이지만 환각만 있고 컨텍스트는 관련 있음 → generation_problem
- 3·4·6번이 false → generation_problem
- 전부 true (또는 3번 null) → pass

feedback 은 한국어로 명확히 어떤 항목이 어떻게 보강돼야 하는지 적으세요. 특히 5번 fail 의 경우
"컨텍스트에 ~ 수치가 있으니 답변에 인용 필요" 형태로 구체적으로 지시.

질문: {question}
{health_block}컨텍스트:
{context}

답변:
{answer}
"""


async def _llm_evaluate(state: ChatState) -> tuple[EvalResultLiteral, str]:
    """2차 LLM 평가. 1차 통과 시에만 호출."""
    docs = state.get("retrieved_docs", [])
    draft = state.get("draft_answer", "")
    health_block = _format_health_snapshot(state.get("health_data"))

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "JSON 으로만 답하는 RAG 평가자."},
                {
                    "role": "user",
                    "content": _LLM_EVAL_PROMPT.format(
                        question=state["original_question"],
                        health_block=health_block,
                        context=_format_context(docs),
                        answer=draft,
                    ),
                },
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:  # noqa: BLE001
        _logger.warning("llm_evaluate 실패, 통과로 간주: %s", _safe_err_repr(e))
        return ("pass", "")

    result = data.get("result")
    if result not in ("pass", "generation_problem", "retrieval_problem"):
        result = "pass"  # 분류 실패 시 보수적으로 통과 (불필요 루프 회피)

    feedback = str(data.get("feedback") or "")
    return (result, feedback)


async def evaluate_node(state: ChatState) -> dict[str, Any]:
    revision_count = int(state.get("eval_revision_count", 0))

    # 1차: Rule
    rule_result, rule_feedback = _rule_evaluate(state)
    if rule_result != "pass":
        return {
            "eval_result": rule_result,
            "eval_stage": "rule",
            "eval_revision_count": revision_count + 1,
            "eval_feedback": rule_feedback,
        }

    # 서비스 가이드 답변은 의료 가드(수치 해석·위험도 과장·금기 문구) 가 무관하므로
    # 6기준 LLM 평가를 생략한다. 1차 Rule 만으로 통과 → 속도·과민 fail 모두 개선.
    # medical_inquiry / general 만 LLM 평가를 거친다.
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    if intent == "service_guide":
        return {
            "eval_result": "pass",
            "eval_stage": "rule",
            "eval_revision_count": revision_count,
            "eval_feedback": "",
        }

    # 2차: LLM (medical_inquiry / general)
    llm_result, llm_feedback = await _llm_evaluate(state)
    return {
        "eval_result": llm_result,
        "eval_stage": "llm",
        "eval_revision_count": revision_count + (0 if llm_result == "pass" else 1),
        "eval_feedback": llm_feedback,
    }


def decide_after_evaluate(
    state: ChatState,
) -> Literal["final_ok", "generate", "rewrite_query", "final_fallback"]:
    eval_result: EvalResultLiteral = state.get("eval_result", "pass")  # type: ignore[assignment]
    revision_count = int(state.get("eval_revision_count", 0))

    # 케이스 1: 통과
    if eval_result == "pass":
        return "final_ok"
    # 케이스 4: 카운트 상한 → fallback
    if revision_count >= MAX_REVISIONS:
        return "final_fallback"
    # 케이스 2: 답변 생성만 문제 → 같은 컨텍스트로 재생성
    if eval_result == "generation_problem":
        return "generate"
    # 케이스 3: 검색이 잘못됨 → 쿼리 재작성 후 재검색
    return "rewrite_query"


# ─────────────────────────────────────────────
# 노드: rewrite_query
# ─────────────────────────────────────────────
_REWRITE_PROMPT = """당신은 한국어 의료/서비스 RAG 검색 쿼리 재작성기입니다.

원 사용자 질문과 이전 검색 결과 평가 피드백을 보고, **새 검색 쿼리** 를 한 줄로만 출력하세요.
- 핵심 의학/서비스 키워드 우선, 동의어·약어 포함 가능
- 불필요한 조사/구어체 제거
- 따옴표·접두어("질의:", "Q:" 등) 없이 쿼리 본문만 출력

원 질문: {question}
이전 평가 피드백: {feedback}
새 검색 쿼리:
"""


async def rewrite_query_node(state: ChatState) -> dict[str, Any]:
    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "검색 쿼리 한 줄만 출력. 다른 텍스트 금지."},
                {
                    "role": "user",
                    "content": _REWRITE_PROMPT.format(
                        question=state["original_question"],
                        feedback=state.get("eval_feedback", ""),
                    ),
                },
            ],
            temperature=0.0,
        )
        new_query = (resp.choices[0].message.content or "").strip().split("\n")[0]
    except Exception as e:  # noqa: BLE001
        _logger.warning("rewrite_query 실패, 원문 재사용: %s", _safe_err_repr(e))
        new_query = state["original_question"]

    if not new_query:
        new_query = state["original_question"]

    return {"retrieval_query": new_query}


# ─────────────────────────────────────────────
# 노드: final_ok / final_fallback
# ─────────────────────────────────────────────
def _disclaimer_for(intent: IntentLiteral) -> str:
    if intent == "service_guide":
        return SERVICE_DISCLAIMER
    if intent == "medical_inquiry":
        return MEDICAL_DISCLAIMER
    return GENERAL_DISCLAIMER


def _confidence_for(docs: list[RetrievedChunk], revision_count: int) -> float:
    """검색 결과 강도와 재시도 횟수로 거친 신뢰도.

    top-3 청크의 dense_similarity 평균 (Dense 미스 시 0 으로 간주) 을 베이스로 사용.
    1위만 보면 Sparse-only hit 케이스에서 일률적인 0.4 가 나오는 문제를 완화 (L-3).
    """
    if not docs:
        return 0.2
    sims = [(d.dense_similarity or 0.0) for d in docs[:3]]
    avg = sum(sims) / len(sims) if sims else 0.0
    base = min(0.95, max(0.4, float(avg)))
    return max(0.0, base - 0.1 * revision_count)


async def final_ok(state: ChatState) -> dict[str, Any]:
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    docs = state.get("retrieved_docs", [])
    revision_count = int(state.get("eval_revision_count", 0))
    return {
        "final_answer": state.get("draft_answer", ""),
        "sources": docs,
        "is_fallback": False,
        "disclaimer": _disclaimer_for(intent),
        "confidence": _confidence_for(docs, revision_count),
        "model_version": "chatragraph-v1",
    }


async def final_fallback(state: ChatState) -> dict[str, Any]:
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    message = FALLBACK_SERVICE if intent == "service_guide" else FALLBACK_MEDICAL
    return {
        "final_answer": message,
        "sources": [],
        "is_fallback": True,
        "disclaimer": _disclaimer_for(intent),
        "confidence": 0.0,
        "model_version": "chatragraph-v1",
    }


# ─────────────────────────────────────────────
# 그래프 컴파일 (프로세스 1회)
# ─────────────────────────────────────────────
def _build_graph() -> Any:
    g: StateGraph[ChatState] = StateGraph(ChatState)
    # 각 노드를 _timed_node 로 감싸 노드 소요 시간을 INFO 로그로 가시화 (디버깅·튜닝용).
    g.add_node("classify_intent", _timed_node(classify_intent))
    g.add_node("final_greeting", _timed_node(final_greeting))
    g.add_node("fetch_health_data", _timed_node(fetch_health_data))
    g.add_node("final_missing_info", _timed_node(final_missing_info))
    g.add_node("retrieve", _timed_node(retrieve_node))
    g.add_node("generate", _timed_node(generate_node))
    g.add_node("evaluate", _timed_node(evaluate_node))
    g.add_node("rewrite_query", _timed_node(rewrite_query_node))
    g.add_node("final_ok", _timed_node(final_ok))
    g.add_node("final_fallback", _timed_node(final_fallback))

    g.add_edge(START, "classify_intent")
    g.add_conditional_edges(
        "classify_intent",
        decide_after_classify,
        {
            "final_greeting": "final_greeting",
            "fetch_health_data": "fetch_health_data",
            "retrieve": "retrieve",
        },
    )
    g.add_edge("final_greeting", END)
    g.add_conditional_edges(
        "fetch_health_data",
        decide_after_fetch_health,
        {"retrieve": "retrieve", "final_missing_info": "final_missing_info"},
    )
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "evaluate")
    g.add_conditional_edges(
        "evaluate",
        decide_after_evaluate,
        {
            "final_ok": "final_ok",
            "generate": "generate",
            "rewrite_query": "rewrite_query",
            "final_fallback": "final_fallback",
        },
    )
    g.add_edge("rewrite_query", "retrieve")
    g.add_edge("final_missing_info", END)
    g.add_edge("final_ok", END)
    g.add_edge("final_fallback", END)

    return g.compile()


_compiled_graph: Any | None = None


def ChatRAGGraph() -> Any:  # noqa: N802 — API 계약 문서 명칭 보존
    """컴파일된 그래프 (lazy singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ─────────────────────────────────────────────
# 공개 진입점 — ChatbotRAG.answer() 가 호출
# ─────────────────────────────────────────────
async def run_chat_rag(
    question: str,
    user_id: Any,
    thread_id: str,
) -> ChatRAGResult:
    """ChatRAGGraph 1회 실행 → ChatRAGResult."""
    if not question.strip():
        return ChatRAGResult(
            answer=FALLBACK_MESSAGE,
            is_fallback=True,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    graph = ChatRAGGraph()
    initial: ChatState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "original_question": question,
        "eval_revision_count": 0,
    }

    try:
        final_state: ChatState = await graph.ainvoke(initial)
    except Exception as e:  # noqa: BLE001 — 그래프 자체 예외는 안전 fallback
        _logger.error("ChatRAGGraph 실행 실패: %s", _safe_err_repr(e))
        return ChatRAGResult(
            answer=FALLBACK_MESSAGE,
            is_fallback=True,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    intent: IntentLiteral = final_state.get("intent", "general")  # type: ignore[assignment]
    return ChatRAGResult(
        answer=final_state.get("final_answer", FALLBACK_MESSAGE),
        sources=final_state.get("sources", []),
        intent=intent,
        needs_health_data=bool(final_state.get("needs_health_data", False)),
        has_health_data=bool(final_state.get("has_health_data", False)),
        missing_fields=list(final_state.get("missing_fields", [])),
        action_hint=final_state.get("action_hint"),
        is_fallback=bool(final_state.get("is_fallback", False)),
        eval_revision_count=int(final_state.get("eval_revision_count", 0)),
        disclaimer=final_state.get("disclaimer", _disclaimer_for(intent)),
        confidence=float(final_state.get("confidence", 0.0)),
        model_version=final_state.get("model_version", "chatragraph-v1"),
    )
