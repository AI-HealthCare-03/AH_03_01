"""의료 답변 품질 평가 모듈 — ChatRAGGraph / RiskRecommendationGraph 공용.

1단계에서 ChatRAGGraph 안에 만들었던 2-stage evaluator(1차 Rule R1~R5 + 2차 LLM 6기준)를
**state 비결합**으로 추출. 각 그래프는 자기 State 에서 필요한 값만 뽑아 `EvalInput`
dataclass 로 넘기고, 본 모듈이 동일한 의료 가드 다층 구조를 적용한다.

배경 — 위험도 그래프(RiskRecommendationGraph)도 위험도 결과 + 권고를 LLM 으로 생성
하므로 동일한 의료 안전 가드(단정 표현 금지·약물 직접 권고 금지·수치 인용 필수·
4측면 가이드)가 적용돼야 한다. evaluate 로직을 한 곳에 두어 회귀 위험을 줄인다.

가드 다층 구조 (양 그래프 동일):
1. 시스템 프롬프트 (generate 노드 안에서 그래프별로 정의 — 본 모듈 외부)
2. 1차 Rule (결정적, LLM 호출 없음)
   - R1 retrieved_docs 비어 있음        → retrieval_problem
   - R2 답변 길이 < MIN_ANSWER_LEN      → generation_problem
   - R3 단정/약물 직접 권고 표현        → generation_problem
   - R4 의료 답변에 "의사·전문가·상담" 권고 누락 → generation_problem
   - R5 has_health_data=true 인데 사용자 실제 수치 미인용 → generation_problem
3. 2차 LLM (medical_inquiry / general 만 — service_guide 는 skip)
   - 6기준: answers_question / grounded_in_context / numeric_interpretation_correct /
     no_risk_exaggeration / recommendations_specific / warnings_appropriate
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from openai import AsyncOpenAI

from app.core import config
from app.services.ml.retrieval import RetrievedChunk

_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────
MIN_ANSWER_LEN = 30  # R2: 답변 최소 글자 수

# R3 단정적 진단 표현 정규식 — 한국어 어미 변형 커버, "정상 범위" 같은 평가 아닌 표현은 제외.
_DIAGNOSTIC_ASSERTION_PATTERN = re.compile(
    r"(정상이|비정상이|위험하|안전하|확진(하|되|이))"
    r"(다|에요|네요|어요|군요|시네요|시군요|시다|었|시었|니까|시니까)"
    r"|확진입니다|당신은 환자|단언"
)

# R3 약물 직접 권고 — 특정 약/용법 권유. 한국어 변형 다수 커버.
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

# R4 의료 답변에 필수 권고 키워드 (하나라도 있으면 OK)
_MEDICAL_REQUIRED_PHRASES = ("의사", "전문의", "전문가", "상담", "병원")

# R4 보강 — intent=general 로 (오)분류돼도 본문에 의료 토픽이 등장하면 권고 강제.
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


EvalResultLiteral = Literal["pass", "generation_problem", "retrieval_problem"]
EvalStageLiteral = Literal["rule", "llm"]
# evaluator 호출 측이 intent 를 어떻게 표현하든 본 모듈은 세 가지 영역만 본다.
EvalIntentLiteral = Literal["medical_inquiry", "service_guide", "general"]


# ─────────────────────────────────────────────
# 호출 인터페이스 (state 비결합)
# ─────────────────────────────────────────────
@dataclass(slots=True)
class EvalInput:
    """evaluator 입력 — 그래프 State 와 결합 끊기 위한 명시적 dataclass.

    호출 측은 자기 State 에서 필요한 값만 뽑아 인스턴스화한다.
    """

    question: str
    draft: str
    docs: list[RetrievedChunk]
    intent: EvalIntentLiteral
    has_health_data: bool = False
    health_data: dict[str, Any] | None = None
    revision_count: int = 0


@dataclass(slots=True)
class EvalOutput:
    """evaluator 결과 — 호출 측이 그래프 State 업데이트에 사용."""

    eval_result: EvalResultLiteral
    eval_stage: EvalStageLiteral
    eval_revision_count: int
    eval_feedback: str = ""
    criteria: dict[str, Any] = field(default_factory=dict)  # LLM 평가의 6기준 세부 (디버깅용)


# ─────────────────────────────────────────────
# OpenAI 클라이언트 (모듈 싱글톤)
# ─────────────────────────────────────────────
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 비어 있어 evaluator 를 실행할 수 없습니다.")
        _client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.OPENAI_REQUEST_TIMEOUT,
            max_retries=config.OPENAI_MAX_RETRIES,
        )
    return _client


def _safe_err_repr(e: BaseException) -> str:
    head = str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {head[:160]}"


# ─────────────────────────────────────────────
# 헬퍼 — 사용자 실제 수치 추출 (R5 인용 검사)
# ─────────────────────────────────────────────
def extract_user_numbers(snap: dict[str, Any] | None) -> set[str]:
    """사용자 health snapshot 에서 실제 수치 토큰을 추출 (답변 인용 여부 검사용).

    프로필 키(height_cm/weight_kg/waist_cm) + 측정값(primary_value/secondary_value).
    숫자는 `f"{v:g}"` 로 정수·소수 둘 다 자연스러운 표기.
    """
    if not snap:
        return set()
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


# ─────────────────────────────────────────────
# 헬퍼 — 컨텍스트·health snapshot 포맷 (LLM 평가 입력용)
# ─────────────────────────────────────────────
def format_context(docs: list[RetrievedChunk]) -> str:
    """retrieved 청크 list 를 LLM 입력용 텍스트로. ChatRAGGraph 의 동일 헬퍼 추출."""
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


# ─────────────────────────────────────────────
# 1차 Rule
# ─────────────────────────────────────────────
def rule_evaluate(inp: EvalInput) -> tuple[EvalResultLiteral, str]:  # noqa: C901 — 평면 Rule 분기
    """1차 결정적 평가. (eval_result, feedback) 반환. pass 면 feedback="".

    R1~R5 중 하나라도 fail 이면 즉시 분류 종료, LLM 호출 없음.
    """
    # R1: 문서 없음
    if not inp.docs:
        return (
            "retrieval_problem",
            "[Rule R1] 검색 결과가 비어 있음. 핵심 키워드/동의어로 쿼리 재작성 필요.",
        )

    # R2: 답변 길이 부족
    stripped = inp.draft.strip()
    if len(stripped) < MIN_ANSWER_LEN:
        return (
            "generation_problem",
            f"[Rule R2] 답변이 너무 짧음 ({len(stripped)}자). "
            f"컨텍스트를 인용해 단계별로 다시 작성하고 의사 상담 권고 포함.",
        )

    # R3: 단정적 진단 표현
    diag_match = _DIAGNOSTIC_ASSERTION_PATTERN.search(inp.draft)
    if diag_match:
        return (
            "generation_problem",
            f"[Rule R3] 단정적 진단 표현 '{diag_match.group(0)}' 사용 금지. "
            f"'경향/범위' 표현으로 바꾸고 의사 상담 권고 추가하여 재작성.",
        )

    # R3: 약물 직접 권고
    for phrase in _DRUG_DIRECT_RECOMMENDATIONS:
        if phrase in inp.draft:
            return (
                "generation_problem",
                f"[Rule R3] 약물 직접 권고 '{phrase}' 금지. 일반 정보 안내 + '담당 의사·약사 상담' 권고로 재작성.",
            )

    # R4: 의료 답변에 의사 상담 권고 필수
    needs_advice = inp.intent == "medical_inquiry" or (
        inp.intent == "general" and any(k in inp.draft for k in _MEDICAL_TOPIC_KEYWORDS)
    )
    if needs_advice and not any(p in inp.draft for p in _MEDICAL_REQUIRED_PHRASES):
        return (
            "generation_problem",
            "[Rule R4] 의료 답변에 '의사/전문의/전문가/상담/병원' 권고 누락. 답변 끝에 의사 상담 권고 추가하여 재작성.",
        )

    # R5: 사용자 본인 데이터 실제 수치 인용 여부
    if inp.has_health_data:
        user_numbers = extract_user_numbers(inp.health_data)
        if user_numbers and not any(n in inp.draft for n in user_numbers):
            return (
                "generation_problem",
                "[Rule R5] 사용자 본인 데이터의 실제 수치(예: 혈압 130/85, 체중 70 kg, "
                "BMI 22.5) 가 답변에 인용되지 않음. 사용자 데이터를 본문에 그대로 인용하여 재작성.",
            )

    return ("pass", "")


# ─────────────────────────────────────────────
# 2차 LLM (6기준)
# ─────────────────────────────────────────────
def _format_health_block_for_eval(snap: dict[str, Any] | None) -> str:
    """LLM 평가 프롬프트의 [사용자 건강 정보] 블록.

    snapshot 미제공이면 빈 문자열 (평가자가 numeric_interpretation_correct=null 처리).
    제공되면 raw json 으로 (이미 generate 단계에서 포맷된 텍스트를 다시 만들지 않고
    LLM 이 자체 해석 — 평가 일관성 위해).
    """
    if not snap:
        return ""
    return f"[사용자 건강 정보 (raw)]\n{json.dumps(snap, ensure_ascii=False, indent=2)}\n\n"


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


async def llm_evaluate(inp: EvalInput) -> tuple[EvalResultLiteral, str, dict[str, Any]]:
    """2차 LLM 평가 — 1차 통과 시에만 호출.

    Returns: (result, feedback, criteria_dict)
    """
    health_block = _format_health_block_for_eval(inp.health_data)

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "JSON 으로만 답하는 RAG 평가자."},
                {
                    "role": "user",
                    "content": _LLM_EVAL_PROMPT.format(
                        question=inp.question,
                        health_block=health_block,
                        context=format_context(inp.docs),
                        answer=inp.draft,
                    ),
                },
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:  # noqa: BLE001
        _logger.warning("llm_evaluate 실패, 통과로 간주: %s", _safe_err_repr(e))
        return ("pass", "", {})

    result = data.get("result")
    if result not in ("pass", "generation_problem", "retrieval_problem"):
        result = "pass"  # 분류 실패 시 보수적으로 통과 (불필요 루프 회피)

    feedback = str(data.get("feedback") or "")
    criteria = data.get("criteria") or {}
    if not isinstance(criteria, dict):
        criteria = {}
    return (result, feedback, criteria)


# ─────────────────────────────────────────────
# 약물+식품 조합 질문 패턴 (evaluator LLM 평가 스킵용)
# ─────────────────────────────────────────────
_DRUG_FOOD_EVAL_PATTERN = re.compile(
    r"(복용|투약|먹고\s*있|사용\s*중|처방).{0,20}(먹어도|섭취|마셔도|먹을\s*수|괜찮|안전)"
    r"|(당뇨|고혈압|이상지질혈증|당뇨병).{0,10}(환자|있는데|있는\s*사람).{0,20}(먹어도|섭취|마셔도|먹을\s*수|괜찮|안전)",
    re.DOTALL,
)


# ─────────────────────────────────────────────
# 통합 evaluate — 그래프 노드가 직접 호출하는 단일 진입점
# ─────────────────────────────────────────────
async def evaluate(inp: EvalInput) -> EvalOutput:
    """2-stage evaluator 단일 진입점.

    - 1차 Rule fail → 즉시 분류 종료
    - 1차 pass + service_guide → LLM 평가 skip (의료 가드 불필요)
    - 1차 pass + 약물+식품 조합 질문 → LLM 평가 skip
      (직접 조합 MD 없어 5번 기준 탈락 방지 — Query Decomposition 으로 관련 원칙 기반 답변)
    - 1차 pass + medical/general → LLM 6기준 평가
    """
    # 1차: Rule
    rule_result, rule_feedback = rule_evaluate(inp)
    if rule_result != "pass":
        return EvalOutput(
            eval_result=rule_result,
            eval_stage="rule",
            eval_revision_count=inp.revision_count + 1,
            eval_feedback=rule_feedback,
        )

    # 서비스 가이드는 의료 가드 불필요 → LLM 평가 skip (속도·과민 fail 회피)
    if inp.intent == "service_guide":
        return EvalOutput(
            eval_result="pass",
            eval_stage="rule",
            eval_revision_count=inp.revision_count,
            eval_feedback="",
        )

    # 약물+식품 조합 질문 → LLM 평가 skip
    # MD에 특정 약물+식품 직접 조합이 없어 LLM 평가 5번(recommendations_specific)에서
    # 과민 탈락하는 문제 방지. 1차 Rule 통과 시 pass 처리.
    if _DRUG_FOOD_EVAL_PATTERN.search(inp.question):
        return EvalOutput(
            eval_result="pass",
            eval_stage="rule",
            eval_revision_count=inp.revision_count,
            eval_feedback="",
        )

    # 2차: LLM (medical/general)
    llm_result, llm_feedback, criteria = await llm_evaluate(inp)
    return EvalOutput(
        eval_result=llm_result,
        eval_stage="llm",
        eval_revision_count=inp.revision_count + (0 if llm_result == "pass" else 1),
        eval_feedback=llm_feedback,
        criteria=criteria,
    )
