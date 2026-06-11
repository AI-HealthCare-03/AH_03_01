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
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.core import config
from app.graphs._shared.medical_evaluator import (
    _MEDICAL_TOPIC_KEYWORDS,
    EvalInput,
    EvalResultLiteral,
    EvalStageLiteral,
    extract_user_numbers,  # noqa: F401 — 외부 호환 (옛 위치 import 보존)
)
from app.graphs._shared.medical_evaluator import (
    evaluate as run_evaluator,
)
from app.graphs._shared.medical_evaluator import (
    format_context as _format_context,
)
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
MAX_REVISIONS = 1  # 재검색·재생성 합산 상한 (API 계약 eval_revision_count 0~2)
RETRIEVE_TOP_K = 5  # 일반/서비스 기본
# medical_inquiry 는 생활요법·약물·추적·위험도 4측면이 한 번에 잡혀야 답변 완전성↑.
# top_k 를 5→8 로 확장 (broader context). RRF 후보 풀도 자동으로 늘어남.
RETRIEVE_TOP_K_MEDICAL = 8
# MIN_ANSWER_LEN 등 evaluator Rule 상수는 app/graphs/_shared/medical_evaluator.py 로 이동.

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

# 1차 Rule (R1~R5) 상수·정규식·약물 권고 패턴은 모두 app/graphs/_shared/medical_evaluator.py 로 이동.

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

# N2 가드: 약품명·의약품 보관/용법 / 병원·진료 안내 → 무조건 medical_inquiry 강제.
# LLM이 diseases=[] 를 근거로 service_guide 로 오분류하는 케이스를 차단.
_DRUG_KEYWORD_PATTERN = re.compile(
    r"인슐린|스타틴|와파린|메트포르민|티카그렐러|아스피린|"
    r"혈압약|당뇨약|고지혈증약|이뇨제|베타차단제|"
    r"보관\s*(방법|온도|기간|법)|용법|용량|복용\s*(방법|법)|처방전",
    re.IGNORECASE,
)
_HOSPITAL_KEYWORD_PATTERN = re.compile(
    r"어느\s*(병원|과|진료과)|병원\s*(가야|추천|선택)|진료\s*(과|받을|예약)|처방\s*(받을|전)",
)

# N3 가드: 쿼리 내 인라인 수치 감지 → needs_health_data 강제 False.
# LLM이 수치가 포함된 쿼리를 "본인 DB 데이터 필요"로 오분류하면
# fetch_health_data → has_health_data=False → final_missing_info 로 빠지는 문제 차단.
# 패턴: 의료 수치 단위 또는 위험도 점수 형태 (소수점 포함)
# 예: "공복혈당 145", "HbA1c 7.8%", "위험도 0.12", "혈압 142/91", "LDL 95 mg/dL"
_INLINE_NUMERIC_PATTERN = re.compile(
    r"\d+\.?\d*\s*%"  # 퍼센트 수치 (HbA1c 7.8%, 위험도 12%)
    r"|\d+\.?\d*\s*(mg/dL|mmHg|kg|cm|kcal)"  # 단위 포함 수치
    r"|위험도\s*\d+\.?\d*"  # 위험도 점수 (0.12, 0.35 등)
    r"|혈압\s*\d+/\d+"  # 혈압 수치 (130/85)
    r"|(공복혈당|혈당|LDL|HDL|중성지방|HbA1c|당화혈색소|콜레스테롤)\s*\d+",  # 검사 항목 + 수치
)


# prefilter 확장: 명확한 서비스 질문 패턴 — 길이 무관, 의료 키워드 없으면 LLM 스킵
# 비밀번호/로그인/회원가입/탈퇴 등 앱 기능 관련 질문
_SERVICE_PREFILTER_PATTERN = re.compile(
    r"비밀번호\s*(변경|찾기|재설정|초기화|설정|잊|까먹)"
    r"|로그인\s*(방법|이?\s*안|못|문제|오류|에러|안\s*되)"
    r"|회원\s*(가입|탈퇴|정보\s*수정|등록)"
    r"|아이디\s*(찾기|변경|잊)"
    r"|앱\s*(설치|다운|업데이트|오류|버그|삭제)"
    r"|알림\s*(설정|끄기|켜기|받기|안\s*와)"
    r"|탈퇴\s*(방법|하고\s*싶|하려)",
    re.IGNORECASE,
)

# N4 가드 패턴: 약물 일반 정보 질문 (부작용·효능·작용기전·복약법 등)
# 본인 수치·데이터 없이 답할 수 있는 질문 → needs_health_data 강제 False
_DRUG_GENERAL_INFO_PATTERN = re.compile(
    r"부작용|이상반응|근육통|근육통증|횡문근융해|두통|어지럼"
    r"|약\s*(끊|중단|바꿔|바꾸|그냥\s*먹|먹어도\s*되)"
    r"|효과|효능|작용|기전|원리"
    r"|언제\s*먹|어떻게\s*먹|같이\s*먹|함께\s*먹",
    re.IGNORECASE,
)

# 소아 관련 질문 감지 패턴 — is_pediatric=True 로 설정해 pediatric_only 섹션 포함 검색
_PEDIATRIC_PATTERN = re.compile(
    r"소아|어린이|아이(?!디)|청소년|소년|소녀"
    r"|\d{1,2}\s*세\s*(?:아이|아동|어린|소아|청소년|남아|여아)",
    re.IGNORECASE,
)

# prefilter 확장: 명백한 개인정보 질문 — 범위 외로 즉시 처리
_PERSONAL_INFO_PREFILTER_PATTERN = re.compile(
    r"^(내|제|나의|저의)?\s*(이름|나이|생년월일|전화번호|주소|성별)\s*(이\s*뭐야|이\s*뭐에요|뭐야|뭐에요|알아요?\??|알려줘|뭔가요\??|뭐예요\??)\s*\??$",
    re.IGNORECASE,
)

# ── 코드 기반 분류 패턴 (LLM 판단 대체) ───────────────────────────────────
# 1인칭 건강 질문 감지 — needs_health_data=True 결정에 사용.
# "내일"·"내용"·"내과" 등 오탐 방지: (내|제) 뒤에 조사·공백만 허용.
_FIRST_PERSON_PATTERN = re.compile(
    r"(나|저)(는|도|의|가|에게|한테|를|을|\s)"
    r"|(내|제)(가|는|도|의|\s)"
    r"|본인"
)

# 챌린지 추천 감지 — needs_challenge_catalog=True 결정에 사용.
_CHALLENGE_CATALOG_PATTERN = re.compile(
    r"(챌린지|운동\s*프로그램|생활습관\s*프로그램).{0,20}(추천|맞는|적합|좋은|어떤|골라|알려)"
    r"|(추천|맞는|적합|어떤).{0,20}(챌린지|운동\s*프로그램)"
    r"|챌린지\s*(추천|맞는|골라|알려줘|알려주)"
)

# 질환 감지 — diseases 결정에 사용.
_DISEASE_PATTERNS: dict[str, re.Pattern[str]] = {
    "diabetes": re.compile(
        r"당뇨|혈당|HbA1c|당화혈색소|인슐린|저혈당|고혈당|공복혈당|식후혈당"
    ),
    "hypertension": re.compile(
        r"고혈압|혈압|수축기|이완기|DASH\s*식단"
    ),
    "dyslipidemia": re.compile(
        r"이상지질혈증|고지혈증|콜레스테롤|LDL|HDL|중성지방|TG\b|스타틴|동맥경화"
    ),
}

# 토픽 감지 — topics 결정에 사용. 순서 무관, 모두 매칭.
_TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "medication": re.compile(
        r"약|복용|처방|부작용|이상반응|보관|용법|용량|인슐린|스타틴|와파린|메트포르민"
        r"|티카그렐러|아스피린|이뇨제|베타차단제|혈압약|당뇨약|고지혈증약"
    ),
    "exercise": re.compile(r"운동|신체활동|유산소|근력|걷기|달리기|조깅|스트레칭"),
    "diet": re.compile(r"식단|식이|식사|영양|저염|저지방|저당|음식|먹|섭취|칼로리|DASH"),
    "weight": re.compile(r"체중|비만|BMI|살|다이어트|허리둘레|과체중"),
    "smoking": re.compile(r"금연|흡연|담배"),
    "alcohol": re.compile(r"음주|절주|술"),
    "complication": re.compile(
        r"합병증|신장|망막|신경병증|알부민뇨|단백뇨|뇌졸중|심근경색|심부전|말초혈관"
    ),
    "risk": re.compile(r"위험도|위험인자|위험군|심혈관\s*위험|위험\s*평가|위험\s*분석"),
    "monitoring": re.compile(
        r"측정|모니터링|목표\s*수치|추적|자가\s*측정|혈압\s*재|혈당\s*재|관리\s*목표"
    ),
    "diagnosis": re.compile(r"진단|기준|분류|선별|검사|수치\s*해석|정상\s*범위"),
    "lifestyle": re.compile(r"생활습관|수면|스트레스|자기관리|일상|관리\s*(방법|전략|개선|지침)"),
    "challenge": re.compile(r"챌린지|챌린지\s*참여|챌린지\s*인증"),
    "service": re.compile(
        r"사용법|기능|포인트|인증|로그인|회원|알림|앱|서비스\s*안내|이용\s*방법"
        r"|비밀번호|아이디|패스워드|탈퇴|가입"
    ),
}


def _detect_diseases(question: str) -> list[str]:
    """질문에서 관련 질환을 코드로 감지."""
    return [d for d, pat in _DISEASE_PATTERNS.items() if pat.search(question)]


def _detect_topics(question: str, intent: str) -> list[str]:
    """질문에서 관련 토픽을 코드로 감지."""
    if intent == "general":
        return []
    return [t for t, pat in _TOPIC_PATTERNS.items() if pat.search(question)]


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
# EvalResultLiteral / EvalStageLiteral 은 _shared.medical_evaluator 에서 re-export.
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
    topics: list[str]  # classify_intent 가 추출한 topic 목록 (retrieve 필터용)
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
    # 평가 모드 플래그 — True 시 fetch_health_data(DB 조회) 를 건너뛰고 retrieve 로 직행.
    # ragas_eval.py 에서 ainvoke 호출 시 주입한다.
    eval_mode: bool
    # 소아 관련 질문 여부 — True 시 retrieve 에서 pediatric_only 섹션 포함 검색.
    is_pediatric: bool


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
  "rationale": "한 줄 설명"
}}

== intent ==
- "medical_inquiry": 의학 정보 질문 (증상·진단 기준·약물·식이·운동·합병증·검사 등)
- "service_guide": 앱 사용법·챌린지·포인트·인증·로그인 등 기능 안내 질문. AI 위험도 예측 기능·결과 의미·예측 대상 질환·예측 방식 등 서비스 AI 기능 설명도 포함. 이름·나이·전화번호·주소·생년월일·성별 등 본인 개인정보를 챗봇에 직접 묻는 질문도 포함 (예: "내 이름이 뭐야?", "내 전화번호 알려줘", "나이 몇살이야?", "내 정보 보여줘").
- "general": 위 둘에 명확히 안 맞거나 인사·잡담
- 둘 다 관련된 혼합형(예: "내 상태에 맞는 식단·챌린지")은 medical_inquiry 우선.

== intent 혼동 방지 ==
다음은 반드시 medical_inquiry (service_guide 아님):
- 약품명·의약품이 포함된 보관/용법/복용 질문: "인슐린", "스타틴", "와파린", "메트포르민" 등
- 병원·진료·처방 안내 질문: "어느 병원", "진료과", "처방"
- 증상·진단·합병증 질문 (service_guide 로 분류 절대 금지)

질문: {question}
"""


def _heuristic_prefilter(question: str) -> dict[str, Any] | None:
    """LLM 호출 없이 즉시 결정 가능한 케이스를 처리.

    3가지 경로:
      A. 명확한 서비스 기능 질문 (비밀번호/로그인/회원 등) → service_guide 즉시 반환
      B. 명백한 개인정보 질문 (이름/나이 등) → general(범위 외) 즉시 반환
      C. 인사·감사·작별 (30자 이내, 의료/서비스 키워드 없음) → general 즉시 반환

    불일치하면 None 을 돌려 LLM 으로 위임.
    """
    stripped = question.strip()

    # A. 명확한 서비스 기능 질문 → LLM 없이 service_guide 즉시 반환
    # 의료 키워드가 없을 때만 (예: "당뇨 환자 비밀번호" 같은 엣지케이스 방지)
    if _SERVICE_PREFILTER_PATTERN.search(stripped):
        has_medical = any(kw.lower() in stripped.lower() for kw in _MEDICAL_TOPIC_KEYWORDS)
        if not has_medical:
            _logger.info("classify_intent prefilter SERVICE hit: %s", stripped[:30])
            return {
                "intent": "service_guide",
                "diseases": [],
                "topics": ["service"],
                "needs_health_data": False,
                "needs_challenge_catalog": False,
                "missing_fields": [],
                "action_hint": None,
            }

    # B. 명백한 개인정보 질문은 classify_intent 에서 직접 처리 (is_greeting=False 필요)
    # → _heuristic_prefilter 에서 None 을 반환해 LLM 위임처럼 동작하지만,
    #   classify_intent 에서 별도 분기로 service_guide 즉시 반환.
    # (이 함수에서는 None 반환 — classify_intent 에서 잡음)

    # C. 인사·감사·작별 (기존 로직 유지)
    if len(stripped) > _PREFILTER_MAX_LEN:
        return None
    lowered = stripped.lower()
    for kw in _MEDICAL_TOPIC_KEYWORDS:
        if kw.lower() in lowered:
            return None
    for kw in ("챌린지", "포인트", "인증", "로그인", "회원", "알림", "예측"):
        if kw in stripped:
            return None
    if not _GREETING_PATTERN.match(stripped):
        return None

    return {
        "intent": "general",
        "diseases": [],
        "topics": [],
        "needs_health_data": False,
        "needs_challenge_catalog": False,
        "missing_fields": [],
        "action_hint": None,
    }


async def classify_intent(state: ChatState) -> dict[str, Any]:  # noqa: C901
    # 개인정보 질문 (이름/나이 등) → service_guide 로 라우팅해 service_system.txt 규칙 5 적용.
    # is_greeting=False 이므로 retrieve/generate 흐름을 타게 됨.
    if _PERSONAL_INFO_PREFILTER_PATTERN.match(state["original_question"].strip()):
        _logger.info("classify_intent prefilter PERSONAL_INFO hit: %s", state["original_question"][:30])
        return {
            "intent": "service_guide",
            "diseases": [],
            "topics": ["service"],
            "needs_health_data": False,
            "needs_challenge_catalog": False,
            "missing_fields": [],
            "action_hint": None,
            "is_greeting": False,
        }

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

    # N2 가드: 약품명/보관/용법/병원 키워드 → 무조건 medical_inquiry 강제.
    # LLM 이 diseases=[] 를 근거로 service_guide 로 오분류하는 케이스 사후 교정.
    # (예: "인슐린 펜 보관 방법", "고혈압인데 어느 병원 가야 하나요")
    if intent != "medical_inquiry" and (
        _DRUG_KEYWORD_PATTERN.search(state["original_question"])
        or _HOSPITAL_KEYWORD_PATTERN.search(state["original_question"])
    ):
        _logger.info("classify_intent N2 guard hit — 약품/병원 질문 강제 medical_inquiry")
        intent = "medical_inquiry"

    # 코드 기반: needs_challenge_catalog — 챌린지/운동 프로그램 추천 키워드로 결정.
    needs_challenge = bool(_CHALLENGE_CATALOG_PATTERN.search(state["original_question"]))

    # 1인칭 + 챌린지 추천 조합 → 반드시 medical_inquiry.
    # LLM 이 "챌린지 = 서비스 기능" 으로 service_guide 분류하는 오류를 코드로 보정.
    if needs_challenge and bool(_FIRST_PERSON_PATTERN.search(state["original_question"])):
        intent = "medical_inquiry"

    # 코드 기반: needs_health_data — intent=medical_inquiry + 1인칭 표현 조합으로 결정.
    # LLM 판단 대신 코드로 결정하여 비결정성 제거.
    needs = intent == "medical_inquiry" and bool(_FIRST_PERSON_PATTERN.search(state["original_question"]))
    missing = ["profile"] if needs else []

    # 코드 기반: diseases · topics — 키워드 패턴으로 결정.
    diseases = _detect_diseases(state["original_question"])
    topics = _detect_topics(state["original_question"], intent)

    is_pediatric = bool(_PEDIATRIC_PATTERN.search(state["original_question"]))

    return {
        "intent": intent,
        "diseases": diseases,
        "topics": topics,
        "needs_health_data": needs,
        "needs_challenge_catalog": needs_challenge,
        "missing_fields": missing if needs else [],
        "action_hint": "navigate_to_health_info" if needs else None,
        "is_pediatric": is_pediatric,
    }


def decide_after_classify(state: ChatState) -> Literal["final_greeting", "fetch_health_data", "retrieve"]:
    if state.get("is_greeting"):
        return "final_greeting"
    # eval_mode 시 fetch_health_data(DB 조회) 를 건너뛰고 retrieve 로 직행.
    # needs_health_data=True 여도 평가 환경에선 유저 DB 가 없어 final_missing_info 로
    # 빠져 컨텍스트 0개가 되는 문제를 방지한다.
    if state.get("eval_mode"):
        return "retrieve"
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
                "current_smoker": (
                    int(profile.current_smoker) if profile and profile.current_smoker is not None else None
                ),
                "alcohol_freq_y": (
                    int(profile.alcohol_freq_y) if profile and profile.alcohol_freq_y is not None else None
                ),
                "family_dm": int(profile.family_dm) if profile and profile.family_dm is not None else None,
                "family_hp": int(profile.family_hp) if profile and profile.family_hp is not None else None,
                "family_hl": int(profile.family_hl) if profile and profile.family_hl is not None else None,
                "chronic_diseases": list(profile.chronic_diseases) if profile else [],
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


# ── Query Decomposition: 약물+식품 조합 질문 분해 ──────────────────────────
# "OO약 복용 중인데 OO 먹어도 되나요?" 패턴 감지
# 약물+식품 또는 질환+식품 조합 질문 패턴
_DRUG_FOOD_PATTERN = re.compile(
    r"(복용|투약|먹고\s*있|사용\s*중|처방).{0,20}(먹어도|섭취|마셔도|먹을\s*수|괜찮|안전)"
    r"|(당뇨|고혈압|이상지질혈증|당뇨병).{0,10}(환자|있는데|있는\s*사람).{0,20}(먹어도|섭취|마셔도|먹을\s*수|괜찮|안전)",
    re.DOTALL,
)

# Multi-hop 복합 질문 패턴 — 두 가지 이상의 주제가 결합된 질문
_MULTI_HOP_PATTERN = re.compile(
    r"(노인|고령|70대|80대).{0,30}(당뇨|혈당|고혈압|혈압|콜레스테롤)"
    r"|(당뇨|고혈압|이상지질혈증).{0,20}(합병증|신장|망막|신경|알부민뇨)"
    r"|(SGLT|메트포르민|인슐린|스타틴).{0,30}(신장|간|심장|안전)"
    r"|(혈압|혈당|콜레스테롤).{0,20}목표.{0,20}(약|치료|선택)",
    re.DOTALL,
)

_DECOMPOSE_PROMPT = """다음 질문을 RAG 검색에 최적화된 2개의 독립적인 검색 쿼리로 분해하세요.
JSON 배열로만 응답하세요. 다른 텍스트 절대 포함 금지.

질문: {question}
유형: {query_type}

규칙 (유형별):
[drug_food] 약물+식품 또는 질환+식품 조합:
- 쿼리 1: 약물 카테고리 주의사항 또는 질환 관리 원칙
- 쿼리 2: 질환별 식이 권고 또는 영양소 관련 원칙

[multi_hop] 복합/심층 질문:
- 쿼리 1: 첫 번째 핵심 주제 (질환·상황·대상)
- 쿼리 2: 두 번째 핵심 주제 (치료·목표·합병증)

각 쿼리는 20자 이내 핵심 키워드로.

예시:
"인슐린 복용 중 바나나 먹어도 되나요?" [drug_food]
→ ["인슐린 혈당 식이 주의사항", "당뇨 과일 혈당 식이요법"]

"노인 당뇨 환자 혈당 목표는 어떻게 다른가요?" [multi_hop]
→ ["노인 당뇨 혈당조절 목표", "고령 당뇨 저혈당 위험"]

"알부민뇨 발견 시 혈압 목표와 약제 선택" [multi_hop]
→ ["당뇨 신장질환 혈압 목표", "만성콩팥병 항고혈압제 선택"]"""


async def _decompose_query(question: str, query_type: str = "drug_food") -> list[str]:
    """질문을 2개 검색 쿼리로 분해. 실패 시 원본 질문 단일 리스트 반환."""
    try:
        response = await _get_client().chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": _DECOMPOSE_PROMPT.format(question=question, query_type=query_type)}],
            temperature=0,
            max_tokens=100,
        )
        text = (response.choices[0].message.content or "").strip()
        # LLM이 코드펜스나 앞뒤 텍스트를 붙여도 JSON 배열 부분만 추출
        text = re.sub(r"```json|```", "", text).strip()
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        text = match.group(0) if match else text
        queries = json.loads(text)
        if isinstance(queries, list) and len(queries) >= 2:
            _logger.info("query decomposition[%s] 성공: %s → %s", query_type, question[:30], queries)
            return queries[:2]
    except Exception as e:  # noqa: BLE001
        _logger.warning("query decomposition 실패, 원본 쿼리 사용: %s", _safe_err_repr(e))
    return [question]


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

    # ── Query Decomposition: 약물+식품 / 복합 질문 감지 시 쿼리 분해 후 병합 ──
    original = state["original_question"]
    is_drug_food = bool(_DRUG_FOOD_PATTERN.search(original))
    is_multi_hop = bool(_MULTI_HOP_PATTERN.search(original)) and not is_drug_food

    is_pediatric = bool(state.get("is_pediatric"))

    try:
        if is_drug_food or is_multi_hop:
            query_type = "drug_food" if is_drug_food else "multi_hop"
            sub_queries = await _decompose_query(original, query_type)
            all_chunks: list[Any] = []
            seen_ids: set[str] = set()
            for sub_query in sub_queries:
                result = await retrieve(
                    query=sub_query,
                    top_k=top_k // 2,
                    source_type=source_type,
                    disease=diseases if diseases else None,
                    topics=state.get("topics") or None,
                    include_pediatric=is_pediatric,
                )
                for chunk in result.chunks:
                    chunk_id = chunk.metadata.get("section_id") or str(chunk.document_id)
                    if chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        all_chunks.append(chunk)
            return {"retrieved_docs": all_chunks, "retrieval_query": query}
        else:
            result = await retrieve(
                query=query,
                source_type=source_type,
                disease=diseases if diseases else None,
                topics=state.get("topics") or None,
                include_pediatric=is_pediatric,
            )
            # RRF 후 동일 section_id 중복 제거: 점수 높은 첫 번째 청크만 유지
            seen_ids = set()
            deduped_chunks: list[Any] = []
            for chunk in result.chunks:
                chunk_id = chunk.metadata.get("section_id") or str(chunk.document_id)
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    deduped_chunks.append(chunk)
            return {"retrieved_docs": deduped_chunks, "retrieval_query": query}

    except Exception as e:  # noqa: BLE001
        _logger.warning("retrieve 실패, 빈 결과로 진행: %s", _safe_err_repr(e))
        return {"retrieved_docs": [], "retrieval_query": query, "error": _safe_err_repr(e)}


# ─────────────────────────────────────────────
# 노드: generate (health_data 컨텍스트 주입)
# ─────────────────────────────────────────────
def _load_prompt(filename: str) -> str:
    """app/graphs/prompts/ 에서 프롬프트 텍스트를 로드한다.

    프롬프트 수정은 이 파일이 아닌 prompts/*.txt 만 편집하면 된다.
    git 에서도 프롬프트 변경 이력을 코드와 분리해 추적할 수 있다.
    """
    prompt_path = Path(__file__).parent / "prompts" / filename
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}\napp/graphs/prompts/{filename} 파일이 있는지 확인하세요."
        )
    return prompt_path.read_text(encoding="utf-8").strip()


_MEDICAL_SYSTEM = _load_prompt("medical_system.txt")
_SERVICE_SYSTEM = _load_prompt("service_system.txt")


# _format_context 는 _shared.medical_evaluator 에서 import (위 import 블록 참조).


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
    if profile.get("current_smoker") == 1:
        lines.append("- 흡연자")
    alcohol_freq = profile.get("alcohol_freq_y")
    # BD1_11: 1=거의매일 … 7=전혀안함, -1=모름 → 사람이 읽을 표현으로 변환(raw 코드 노출 금지)
    if alcohol_freq is not None and alcohol_freq not in (7, -1):
        if 1 <= alcohol_freq <= 3:
            lines.append("- 음주: 잦음(주 1회 이상)")
        else:
            lines.append("- 음주: 가끔")
    fam: list[str] = []
    if profile.get("family_dm") == 1:
        fam.append("당뇨")
    if profile.get("family_hp") == 1:
        fam.append("고혈압")
    if profile.get("family_hl") == 1:
        fam.append("고지혈증")
    if fam:
        lines.append(f"- 가족력: {', '.join(fam)}")
    diseases = profile.get("chronic_diseases") or []
    if diseases:
        lines.append(f"- 진단받은 만성질환: {', '.join(str(d) for d in diseases)}")
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
    # H-5: 빈 컨텍스트로 LLM 호출하면 hallucination + 무의미 토큰 비용. evaluator R1
    # (retrieval_problem) 이 다음 노드에서 라우팅을 잡아주므로 빈 draft 만 반환.
    # 단, service_guide 는 개인정보 질문 등 컨텍스트 없이 시스템 프롬프트 규칙만으로 답하는 경우가 있음.
    if not docs and intent != "service_guide":
        _logger.info("generate skip — retrieved_docs 비어있음 (evaluator R1 위임)")
        return {"draft_answer": ""}
    system = _SERVICE_SYSTEM if intent == "service_guide" else _MEDICAL_SYSTEM
    context = _format_context(docs)
    health_block = _format_health_snapshot(state.get("health_data"))

    feedback = state.get("eval_feedback", "")
    feedback_hint = f"\n\n[Evaluator 피드백] 이전 답변에서 보완할 점: {feedback}" if feedback else ""

    no_context_hint = "컨텍스트에 답이 없으면 솔직히 모른다고 말하세요."
    if intent == "medical_inquiry":
        no_context_hint += " 의료 전문가와 상담을 권하세요."
    user_prompt = (
        f"질문: {state['original_question']}\n\n"
        f"{health_block}"
        f"컨텍스트:\n{context}\n\n"
        f"위 정보(사용자 건강 정보가 있다면 그것 포함)를 사용해 한국어로 답변하세요. "
        f"{no_context_hint}"
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
# 노드: evaluate (2-stage) — 의료 가드 다층 구조는 _shared.medical_evaluator 로 추출됨.
# 본 노드는 ChatState → EvalInput 변환 + 결과 → ChatState 업데이트만 담당.
# ─────────────────────────────────────────────
async def evaluate_node(state: ChatState) -> dict[str, Any]:
    intent: IntentLiteral = state.get("intent", "general")  # type: ignore[assignment]
    inp = EvalInput(
        question=state["original_question"],
        draft=state.get("draft_answer", ""),
        docs=state.get("retrieved_docs", []),
        intent=intent,
        has_health_data=bool(state.get("has_health_data", False)),
        health_data=state.get("health_data"),
        revision_count=int(state.get("eval_revision_count", 0)),
    )
    out = await run_evaluator(inp)
    if out.eval_result != "pass":
        _logger.info(
            "evaluate fail — stage=%s result=%s rev=%d",
            out.eval_stage,
            out.eval_result,
            out.eval_revision_count,
        )
        _logger.debug("evaluate fail — feedback=%s", out.eval_feedback)
    return {
        "eval_result": out.eval_result,
        "eval_stage": out.eval_stage,
        "eval_revision_count": out.eval_revision_count,
        "eval_feedback": out.eval_feedback,
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


# 모듈 임포트 시점에 미리 빌드 — 첫 요청 콜드스타트 방지.
# 서버 기동 시 그래프가 초기화되어 첫 질문도 빠르게 응답 가능.
_compiled_graph: Any = _build_graph()


def ChatRAGGraph() -> Any:  # noqa: N802 — API 계약 문서 명칭 보존
    """컴파일된 그래프 (eager singleton)."""
    return _compiled_graph


# ─────────────────────────────────────────────
# 공개 진입점용 공통 헬퍼 (run_chat_rag / run_chat_rag_stream 공유)
# ─────────────────────────────────────────────
def _build_initial_state(question: str, user_id: Any, thread_id: str) -> ChatState:
    """그래프 초기 state 구성 — 동기/스트리밍 진입점이 공유."""
    return {
        "user_id": user_id,
        "thread_id": thread_id,
        "original_question": question,
        "eval_revision_count": 0,
    }


def _state_to_result(final_state: ChatState) -> ChatRAGResult:
    """누적된 최종 ChatState → ChatRAGResult 매핑 (run_chat_rag 와 동일 규칙)."""
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


# 그래프 노드명 → 사용자에게 보여줄 진행 단계 문구 (백엔드가 canonical 소유).
# 종료 노드(final_*) 는 의도적으로 매핑에서 제외 — 스트리밍은 token/done 으로 전이한다.
# 매핑에 없는 노드는 stage 미발행(스킵).
STAGE_LABELS: dict[str, str] = {
    "classify_intent": "질문을 분석하고 있어요...",
    "fetch_health_data": "건강 정보를 확인하고 있어요...",
    "retrieve": "관련 자료를 검색하고 있어요...",
    "generate": "답변을 작성하고 있어요...",
    "rewrite_query": "검색어를 다시 다듬고 있어요...",
    "evaluate": "정확한 답변을 제공해 드리기 위해 검토중이에요. 조금만 기다려 주세요!",
}


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
    initial = _build_initial_state(question, user_id, thread_id)

    try:
        final_state: ChatState = await graph.ainvoke(initial)
    except Exception as e:  # noqa: BLE001 — 그래프 자체 예외는 안전 fallback
        _logger.error("ChatRAGGraph 실행 실패: %s", _safe_err_repr(e))
        return ChatRAGResult(
            answer=FALLBACK_MESSAGE,
            is_fallback=True,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    return _state_to_result(final_state)


# ─────────────────────────────────────────────
# 스트리밍 진입점 — ChatbotConversationService.handle_message_stream() 이 소비
# ─────────────────────────────────────────────
# yield 이벤트 형태:
#   ("stage", <node_name: str>)  — 그래프 노드 진입 시점 (진행 중 의미). 라우터/서비스가
#                                  STAGE_LABELS 로 한국어 라벨 매핑.
#   ("result", ChatRAGResult)    — 마지막 1회. 그래프 완료(또는 fallback) 후 최종 결과.
async def run_chat_rag_stream(
    question: str,
    user_id: Any,
    thread_id: str,
) -> AsyncIterator[tuple[str, Any]]:
    """ChatRAGGraph 를 스트리밍 실행하며 단계 이벤트를 yield, 마지막에 최종 결과 yield.

    스트리밍 방식: `astream_events(version="v2")` 의 `on_chain_start` 이벤트에서
    노드명이 우리 노드셋에 속할 때 ("stage", node) 를 발행한다. on_chain_start 는 노드
    **진입** 시점이므로 "지금 ~하고 있어요" 진행 의미와 정확히 맞는다 (노드 완료 delta 인
    stream_mode="updates" 보다 의미가 자연스러움). 최종 ChatRAGResult 는 루트 그래프 실행
    (parent_ids == []) 의 on_chain_end 출력(누적 state) 에서 run_chat_rag 와 동일 매핑으로 구성.

    빈 질문/그래프 예외 시 run_chat_rag 와 동일한 fallback 결과를 ("result", ...) 로 yield
    (stage 없이). 호출 측은 항상 정확히 1개의 ("result", ...) 를 마지막에 받는다.
    """
    if not question.strip():
        yield (
            "result",
            ChatRAGResult(answer=FALLBACK_MESSAGE, is_fallback=True, disclaimer=MEDICAL_DISCLAIMER),
        )
        return

    graph = ChatRAGGraph()
    initial = _build_initial_state(question, user_id, thread_id)

    root_run_id: Any = None
    final_state: ChatState | None = None

    try:
        async for ev in graph.astream_events(initial, version="v2"):
            event_type = ev["event"]
            # 루트 그래프 실행 식별 — parent_ids 가 빈 리스트인 on_chain_start 가 최상위.
            if event_type == "on_chain_start" and ev.get("parent_ids") == []:
                root_run_id = ev["run_id"]
                continue
            # 노드 진입 → stage 발행 (STAGE_LABELS 에 있는 노드만; 종료 노드는 스킵).
            if event_type == "on_chain_start" and ev["name"] in STAGE_LABELS:
                yield ("stage", ev["name"])
                continue
            # 루트 그래프 종료 → 누적 최종 state 확보.
            if event_type == "on_chain_end" and ev["run_id"] == root_run_id:
                output = ev["data"].get("output")
                if isinstance(output, dict):
                    final_state = output  # type: ignore[assignment]
    except Exception as e:  # noqa: BLE001 — 그래프 자체 예외는 안전 fallback
        _logger.error("ChatRAGGraph 스트리밍 실행 실패: %s", _safe_err_repr(e))
        yield (
            "result",
            ChatRAGResult(answer=FALLBACK_MESSAGE, is_fallback=True, disclaimer=MEDICAL_DISCLAIMER),
        )
        return

    if final_state is None:
        # on_chain_end 를 못 잡은 비정상 케이스 — fallback.
        _logger.error("ChatRAGGraph 스트리밍: 최종 state 미확보, fallback")
        yield (
            "result",
            ChatRAGResult(answer=FALLBACK_MESSAGE, is_fallback=True, disclaimer=MEDICAL_DISCLAIMER),
        )
        return

    yield ("result", _state_to_result(final_state))
