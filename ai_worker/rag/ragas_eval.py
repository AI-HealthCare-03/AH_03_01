"""
RAGAS 평가 파이프라인
======================================
평가 지표:
    Faithfulness        ← 답변이 검색 문서에 근거하는가? (목표 0.85 이상)
    Context Precision   ← 검색된 문서가 정확한가? (ground_truth=answer 기반)
    Context Recall      ← 필요한 정보를 잘 가져왔는가? (eval_metrics 포함 항목만)
    Answer Relevancy    ← [RAGAS 원본, 참고용] 한국어 역질문 매칭 한계
    KO Answer Relevancy ← [커스텀] 한국어 전용 직접 평가 (신뢰도 높음)
    Reference Hit Rate  ← [커스텀] reference_context_ids 기반 정답 섹션 검색 적중률

데이터셋:
    rag_eval_qa_dataset_v4.jsonl — 질문 추가/수정은 해당 파일만 편집하세요.
    schema: {id, category, sub_topic, difficulty, question, answer, disclaimer,
             reference_context_ids, question_type, source_document,
             safety_level, is_adversarial, eval_metrics}
    ※ ground_truth 필드 없음 → answer 필드를 대신 사용

변경 이력:
    v1: crag_pipeline(CRAG) → ChatRAGGraph(chat_rag_graph) 기반으로 전환
    v2: per-item eval_metrics 존중 (challenge_rec context_recall 제외)
        reference_context_ids 기반 Reference Hit Rate 지표 추가
        카테고리 비율 유지 층화 샘플링 적용
        eval_type 필터(dead code) → category 기반으로 교체
        _collect_single 미사용 graph 파라미터 제거
        KO_AR 답변 절단 600자 → 1200자
        카테고리별 KO_AR 세분화 출력
        per-item 상세 결과 JSON 저장
"""

import asyncio
import json
import math
import os
import random
from collections import defaultdict
from pathlib import Path

# nest_asyncio를 가장 먼저 패치 — ragas 내부 event loop 충돌 방지
import nest_asyncio

nest_asyncio.apply()

from datasets import Dataset  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent
EVAL_DATASET_PATH = BASE / "rag_eval_qa_dataset_v6.jsonl"
EVAL_SAMPLE_SIZE = 50  # legacy — stratified 샘플링으로 대체됨, 현재 미사용
EVAL_SAMPLE_PER_CATEGORY = 10  # category당 최대 샘플 수; 이하면 전수 포함

# 평가에서 제외할 카테고리 (v3의 eval_type="out_of_scope" 대체)
_EXCLUDE_CATEGORIES: set[str] = {"out_of_scope"}


# ─────────────────────────────────────────────
# 데이터셋 로드
# ─────────────────────────────────────────────
def load_eval_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"평가 데이터셋 파일을 찾을 수 없습니다: {path}")
    with open(path, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
    print(f"  데이터셋 로드 완료: {len(data)}개 ({path.name})")
    return data


# ─────────────────────────────────────────────
# 환경변수 로드
# ─────────────────────────────────────────────
def load_env(base: Path):
    env_path = base.parent.parent / "envs" / ".local.env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


load_env(BASE)


# ─────────────────────────────────────────────
# 층화 샘플링 (카테고리 비율 유지)
# ─────────────────────────────────────────────
def stratified_sample(data: list[dict], total: int, seed: int | None = None) -> list[dict]:
    """카테고리별 비율을 유지하며 total개를 샘플링."""
    if seed is not None:
        random.seed(seed)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in data:
        by_category[item.get("category", "unknown")].append(item)

    n = len(data)
    sampled: list[dict] = []
    for items in by_category.values():
        quota = max(1, math.floor(len(items) / n * total))
        sampled.extend(random.sample(items, min(quota, len(items))))

    # 반올림 오차로 total 미만이면 나머지에서 무작위 보충
    chosen_ids = {id(item) for item in sampled}
    remaining = [item for item in data if id(item) not in chosen_ids]
    if len(sampled) < total and remaining:
        sampled.extend(random.sample(remaining, min(total - len(sampled), len(remaining))))

    random.shuffle(sampled)
    return sampled[:total]


# ─────────────────────────────────────────────
# ChatRAGGraph 로 답변 및 컨텍스트 수집
# ─────────────────────────────────────────────
async def _collect_single(
    question: str,
    idx: int,
    total: int,
) -> tuple[str, list[str], list[str]]:
    """단일 질문에 대해 ChatRAGGraph를 실행하고 (answer, ctx_texts, ctx_ids) 반환.

    실제 서비스의 run_chat_rag() 와 동일한 파이프라인을 거친다:
      classify_intent → retrieve(PGVector+BM25) → generate(LLM) → evaluate → final_ok/fallback
    단, eval_mode=True 로 fetch_health_data(DB 개인 건강 데이터 조회) 노드를 건너뜀.

    인라인 수치 질문(예: "수축기 혈압 145 mmHg이고 LDL 140 mg/dL인데 어떤 챌린지가 맞아?")은
    classify_intent 의 N3 가드가 needs_health_data=False 로 자동 처리하므로 별도 모킹 불필요.
    LLM 은 question 문자열 내 수치를 컨텍스트로 직접 사용한다.
    """
    print(f"\n  [{idx}/{total}] {question}")
    try:
        from app.graphs.chat_rag_graph import ChatRAGGraph, _build_initial_state, _state_to_result

        graph = ChatRAGGraph()
        # run_chat_rag() 와 동일한 초기 state + eval_mode=True:
        # _build_initial_state 가 바뀌어도 평가 파이프라인이 자동으로 동기화된다.
        initial = {
            **_build_initial_state(question, user_id=None, thread_id=f"ragas-eval-{idx}"),
            "eval_mode": True,
        }
        final_state = await graph.ainvoke(initial)
        result = _state_to_result(final_state)
        answer = result.answer or ""
        sources = [chunk for chunk in (result.sources or []) if chunk.chunk_text]
        ctx_texts: list[str] = [chunk.chunk_text for chunk in sources]
        ctx_ids: list[str] = [chunk.metadata.get("section_id") or str(chunk.document_id) for chunk in sources]
    except Exception as e:
        print(f"    ❌ 오류: {e}")
        answer = ""
        ctx_texts = []
        ctx_ids = []

    print(f"    ✅ 완료 (컨텍스트 {len(ctx_texts)}개)")
    return answer, ctx_texts, ctx_ids


async def _collect_all(eval_dataset: list[dict]) -> dict:
    from tortoise import Tortoise

    from app.core.db.databases import TORTOISE_ORM

    # Tortoise ORM 초기화 — RAG 검색(PGVector dense SQL + BM25 RAGDocument 로드) 전용.
    # 실제 유저 건강 데이터(fetch_health_data 노드)는 eval_mode=True 로 완전히 건너뜀.
    await Tortoise.init(config=TORTOISE_ORM)

    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    context_ids: list[list[str]] = []
    ground_truths: list[str] = []
    eval_metrics_list: list[list[str]] = []
    reference_context_ids_list: list[list[str]] = []
    categories: list[str] = []
    total = len(eval_dataset)

    print("=" * 60)
    print(f"  RAGAS 평가용 답변 수집 중... (총 {total}개)")
    print("=" * 60)

    try:
        for i, item in enumerate(eval_dataset, start=1):
            question = item["question"]
            # v4: ground_truth 필드 없음 → answer 필드를 대신 사용
            ground_truth = item.get("ground_truth") or item.get("answer", "")
            answer, ctx_texts, ctx_ids = await _collect_single(question, i, total)
            questions.append(question)
            answers.append(answer)
            contexts.append(ctx_texts)
            context_ids.append(ctx_ids)
            ground_truths.append(ground_truth)
            eval_metrics_list.append(item.get("eval_metrics", ["faithfulness", "answer_relevance", "context_recall"]))
            reference_context_ids_list.append(item.get("reference_context_ids") or [])
            categories.append(item.get("category", "unknown"))
    finally:
        await Tortoise.close_connections()

    return {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "context_ids": context_ids,
        "ground_truth": ground_truths,
        "eval_metrics": eval_metrics_list,
        "reference_context_ids": reference_context_ids_list,
        "category": categories,
    }


def collect_answers(eval_dataset: list[dict], seed: int | None = None) -> dict:
    # v4에는 eval_type 필드가 없으므로 category 기반으로만 필터링
    filtered = [item for item in eval_dataset if item.get("category") not in _EXCLUDE_CATEGORIES]

    sampled = stratified_sample(filtered, EVAL_SAMPLE_SIZE, seed=seed)

    from collections import Counter

    # RAGAS 평가용 필터링 — out_of_scope 제외
    CORE_EVAL_EXCLUDE = {"out_of_scope"}
    filtered = [
        item
        for item in eval_dataset
        if item.get("category") not in CORE_EVAL_EXCLUDE and item.get("eval_type") not in ("out_of_scope",)
    ]

    # category별 stratified 샘플링: EVAL_SAMPLE_PER_CATEGORY 이하면 전수, 초과면 N개만
    from collections import defaultdict

    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in filtered:
        by_category[item.get("category", "unknown")].append(item)

    if seed is not None:
        random.seed(seed)

    sampled = []
    for cat, items in sorted(by_category.items()):
        if len(items) <= EVAL_SAMPLE_PER_CATEGORY:
            sampled.extend(items)
        else:
            sampled.extend(random.sample(items, EVAL_SAMPLE_PER_CATEGORY))

    category_summary = {cat: min(len(items), EVAL_SAMPLE_PER_CATEGORY) for cat, items in sorted(by_category.items())}
    print(
        f"  샘플링: {len(eval_dataset)}개 중 필터링 후 {len(filtered)}개 → {len(sampled)}개 선택 "
        f"(stratified N={EVAL_SAMPLE_PER_CATEGORY}, seed={seed if seed else '랜덤'})"
    )
    print(f"  category별: {category_summary}")
    return asyncio.run(_collect_all(sampled))


# ─────────────────────────────────────────────
# 커스텀 한국어 Answer Relevancy 평가
# ─────────────────────────────────────────────
# RAGAS 기본 Answer Relevancy: 내부적으로 영어 역질문 생성 → 한국어 매칭 실패 (0.35 수준)
# 해결: 한국어 전용 직접 평가 방식 구현
KO_AR_PROMPT = """다음 답변이 질문에 얼마나 관련 있고 충분한지 0~1 사이의 점수로 평가하세요.

[질문]
{question}

[답변]
{answer}

평가 기준:
- 1.0: 질문에 직접적으로 정확하게 답변
- 0.7~0.9: 대부분 관련 있으나 일부 부족
- 0.4~0.6: 부분적으로 관련 있음
- 0.0~0.3: 관련 없거나 엉뚱한 답변

숫자만 출력하세요 (예: 0.85)"""


def compute_korean_answer_relevancy(
    questions: list[str],
    answers: list[str],
    llm: ChatOpenAI,
) -> list[float]:
    """한국어 전용 Answer Relevancy 계산 (RAGAS 대체)."""
    scores = []
    for q, a in zip(questions, answers, strict=False):
        if not a.strip():
            scores.append(0.0)
            continue
        try:
            # 600자 → 1200자: hard 난이도 긴 의료 답변 절단 방지
            response = llm.invoke([HumanMessage(content=KO_AR_PROMPT.format(question=q, answer=a[:1200]))])
            score = float(response.content.strip())
            scores.append(min(max(score, 0.0), 1.0))
        except Exception:
            scores.append(0.5)
    return scores


# ─────────────────────────────────────────────
# Reference Context Hit Rate
# ─────────────────────────────────────────────
def compute_reference_context_hit_rate(
    context_ids: list[list[str]],
    reference_ids: list[list[str]],
) -> list[float | None]:
    """
    reference_context_ids 기반 정답 섹션 검색 적중률.
    context_ids: 각 질문에서 실제 검색된 청크의 section_id 리스트.
    reference_ids가 비어 있으면 None(해당 항목 미적용).
    """
    scores = []
    for retrieved_ids, ref_ids in zip(context_ids, reference_ids, strict=False):
        if not ref_ids:
            scores.append(None)
            continue
        if not retrieved_ids:
            scores.append(0.0)
            continue
        retrieved_set = set(retrieved_ids)
        hit = sum(1 for ref_id in ref_ids if ref_id in retrieved_set)
        scores.append(hit / len(ref_ids))
    return scores


# ─────────────────────────────────────────────
# RAGAS 평가 실행
# ─────────────────────────────────────────────
def run_ragas_evaluation(data: dict) -> tuple[dict, list[float], list[float | None]]:
    import numpy as np

    print("\n" + "=" * 60)
    print("  RAGAS 평가 실행 중...")
    print("=" * 60)

    ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
    ko_ar_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # eval_metrics에 context_recall이 없는 항목(challenge_rec 등)은 contexts를 비워
    # ragas가 contexts=[] 이면 context_recall=NaN 처리하여 해당 항목 제외
    adjusted_contexts = [
        ctx if "context_recall" in metrics else []
        for ctx, metrics in zip(data["contexts"], data["eval_metrics"], strict=False)
    ]

    ragas_data = {
        "question": data["question"],
        "answer": data["answer"],
        "contexts": adjusted_contexts,
        "ground_truth": data["ground_truth"],
    }
    dataset = Dataset.from_dict(ragas_data)

    # RAGAS 자체가 내부에서 asyncio loop를 관리하므로 별도 loop 생성 불필요
    ragas_result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,  # 참고용 (한국어 한계)
            context_precision,
            context_recall,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    print("\n  한국어 Answer Relevancy 계산 중...")
    ko_ar_scores = compute_korean_answer_relevancy(data["question"], data["answer"], ko_ar_llm)
    print(f"  KO Answer Relevancy: {float(np.mean(ko_ar_scores)):.4f}")

    print("\n  Reference Context Hit Rate 계산 중...")
    ref_hit_scores = compute_reference_context_hit_rate(data["context_ids"], data["reference_context_ids"])
    valid_hits = [s for s in ref_hit_scores if s is not None]
    if valid_hits:
        print(f"  Reference Hit Rate: {float(np.mean(valid_hits)):.4f}")

    return ragas_result, ko_ar_scores, ref_hit_scores


# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────
def print_results(ragas_result, ko_ar_scores: list[float], ref_hit_scores: list[float | None], data: dict, output_filename: str = "ragas_result.json"):
    import numpy as np

    print("\n" + "=" * 60)
    print("  📊 RAGAS 평가 결과")
    print("=" * 60)

    def safe_float(val) -> float:
        try:
            return float(val) if hasattr(val, "__float__") else float(np.mean(val))
        except Exception:
            return 0.0

    scores: dict[str, float] = {
        "Faithfulness": safe_float(ragas_result["faithfulness"]),
        "Context Precision": safe_float(ragas_result["context_precision"]),
        "Context Recall": safe_float(ragas_result["context_recall"]),
        "Answer Relevancy(EN)": safe_float(ragas_result["answer_relevancy"]),
        "KO Answer Relevancy": float(np.mean(ko_ar_scores)),
    }
    valid_hits = [s for s in ref_hit_scores if s is not None]
    if valid_hits:
        scores["Reference Hit Rate"] = float(np.mean(valid_hits))

    target = 0.85
    notes = {
        "Answer Relevancy(EN)": " ⚠ (한국어 역질문 한계, 참고용)",
        "KO Answer Relevancy": " ✨ (한국어 전용 직접 평가)",
        "Reference Hit Rate": " 🎯 (정답 섹션 검색 적중률)",
    }
    for metric, score in scores.items():
        status = "✅" if score >= target else "⚠️ "
        score_for_bar = 0.0 if score != score else score  # NaN 체크
        bar = "█" * int(score_for_bar * 20) + "░" * (20 - int(score_for_bar * 20))
        print(f"  {status} {metric:25s} {bar} {score:.4f}{notes.get(metric, '')}")

    # 카테고리별 KO_AR 세분화
    categories = data.get("category", [])
    if categories:
        print("\n  📂 카테고리별 KO Answer Relevancy")
        cat_scores: dict[str, list[float]] = defaultdict(list)
        for cat, score in zip(categories, ko_ar_scores, strict=False):
            cat_scores[cat].append(score)
        for cat, sc in sorted(cat_scores.items()):
            avg = float(np.mean(sc))
            status = "✅" if avg >= target else "⚠️ "
            print(f"    {status} {cat:30s} {avg:.4f} (n={len(sc)})")

    print()
    faith_score = scores["Faithfulness"]
    print(f"  목표: Faithfulness ≥ {target}")
    if faith_score >= target:
        print(f"  ✅ Faithfulness 목표 달성! ({faith_score:.4f})")
    else:
        gap = target - faith_score
        print(f"  ⚠️  Faithfulness 목표 미달 ({faith_score:.4f}, {gap:.4f} 부족)")
    print("=" * 60)

    output_path = BASE / "output" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "summary": {k: float(v) for k, v in scores.items()},
        "per_question": [
            {
                "question": q,
                "category": cat,
                "ko_ar_score": s,
                "ref_hit_score": rh,
            }
            for q, cat, s, rh in zip(
                data["question"],
                data.get("category", [""] * len(data["question"])),
                ko_ar_scores,
                ref_hit_scores,
                strict=False,
            )
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n  결과 저장: {output_path}")


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAGAS 평가 실행")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="샘플링 시드 (기본값: 42). 다른 값으로 다른 질문셋 평가 가능.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 파일명 (output/ 하위). 기본값: ragas_result_seed{seed}.json",
    )
    args = parser.parse_args()

    seed = args.seed
    output_filename = args.output or f"ragas_result_seed{seed}.json"

    dataset = load_eval_dataset(EVAL_DATASET_PATH)
    data = collect_answers(dataset, seed=seed)
    result, ko_ar, ref_hits = run_ragas_evaluation(data)
    print_results(result, ko_ar, ref_hits, data, output_filename=output_filename)
