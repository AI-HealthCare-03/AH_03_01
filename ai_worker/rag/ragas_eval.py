"""
RAGAS 평가 파이프라인
======================================
평가 지표:
    Faithfulness      ← 답변이 검색 문서에 근거하는가? (목표 0.85 이상)
    Context Precision ← 검색된 문서가 정확한가?
    Context Recall    ← 필요한 정보를 잘 가져왔는가?
    Answer Relevancy  ← [RAGAS 원본, 참고용] 한국어 역질문 매칭 한계
    KO Answer Relevancy ← [커스텀] 한국어 전용 직접 평가 (신뢰도 높음)

데이터셋:
    eval_dataset.json 에서 관리 — 질문 추가/수정은 해당 파일만 편집하세요.
    schema: [{ category, question, ground_truth, prediction_result }, ...]
"""

import os
import json
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage

from crag_pipeline import build_crag_graph, CRAGState

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE              = Path(__file__).parent
EVAL_DATASET_PATH = BASE / "eval_dataset.json"

# ─────────────────────────────────────────────
# 데이터셋 로드 (eval_dataset.json)
# ─────────────────────────────────────────────
def load_eval_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"평가 데이터셋 파일을 찾을 수 없습니다: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  데이터셋 로드 완료: {len(data)}개 ({path.name})")
    return data

EVAL_DATASET = load_eval_dataset(EVAL_DATASET_PATH)

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
# CRAG 파이프라인으로 답변 및 컨텍스트 수집
# ─────────────────────────────────────────────
def collect_answers(eval_dataset: list[dict]) -> dict:
    crag = build_crag_graph()

    questions     = []
    answers       = []
    contexts      = []
    ground_truths = []

    print("=" * 60)
    print(f"  RAGAS 평가용 답변 수집 중... (총 {len(eval_dataset)}개)")
    print("=" * 60)

    for i, item in enumerate(eval_dataset):
        question     = item["question"]
        ground_truth = item["ground_truth"]
        prediction   = item.get("prediction_result")

        print(f"\n  [{i+1}/{len(eval_dataset)}] {question}")

        initial_state: CRAGState = {
            "question":             question,
            "original_question":    question,
            "prediction_result":    prediction,
            "retrieved_context":    [],
            "web_results":          [],
            "final_recommendation": "",
            "eval_verdict":         "",
            "eval_feedback":        "",
            "retry_count":          0,
            "rewrite_count":        0,
        }

        try:
            result    = crag.invoke(initial_state)
            answer    = result.get("final_recommendation", "")
            ctx_docs  = result.get("retrieved_context", [])
            ctx_texts = [doc["content"] for doc in ctx_docs]
            ctx_texts += result.get("web_results", [])  # 웹 검색 결과도 포함
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            answer    = ""
            ctx_texts = []

        questions.append(question)
        answers.append(answer)
        contexts.append(ctx_texts)
        ground_truths.append(ground_truth)

        print(f"    ✅ 완료 (컨텍스트 {len(ctx_texts)}개)")

    return {
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths,
    }


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
    """한국어 전용 Answer Relevancy 계산 (RAGAS 대체)"""
    scores = []
    for q, a in zip(questions, answers):
        if not a.strip():
            scores.append(0.0)
            continue
        try:
            response = llm.invoke([
                HumanMessage(content=KO_AR_PROMPT.format(question=q, answer=a[:600]))
            ])
            score = float(response.content.strip())
            scores.append(min(max(score, 0.0), 1.0))
        except Exception:
            scores.append(0.5)
    return scores


# ─────────────────────────────────────────────
# RAGAS 평가 실행
# ─────────────────────────────────────────────
def run_ragas_evaluation(data: dict) -> tuple[dict, list[float]]:
    import asyncio
    import numpy as np

    print("\n" + "=" * 60)
    print("  RAGAS 평가 실행 중...")
    print("=" * 60)

    ragas_llm        = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    ragas_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-3-small")
    )
    ko_ar_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    dataset = Dataset.from_dict(data)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ragas_result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,   # 참고용 (한국어 한계)
            context_precision,
            context_recall,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    # 커스텀 한국어 AR 점수 계산
    print("\n  한국어 Answer Relevancy 계산 중...")
    ko_ar_scores = compute_korean_answer_relevancy(
        data["question"], data["answer"], ko_ar_llm
    )
    print(f"  KO Answer Relevancy: {float(np.mean(ko_ar_scores)):.4f}")

    return ragas_result, ko_ar_scores


# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────
def print_results(ragas_result, ko_ar_scores: list[float]):
    import numpy as np

    print("\n" + "=" * 60)
    print("  📊 RAGAS 평가 결과")
    print("=" * 60)

    def safe_float(val) -> float:
        try:
            return float(val) if hasattr(val, "__float__") else float(np.mean(val))
        except Exception:
            return 0.0

    scores = {
        "Faithfulness":         safe_float(ragas_result["faithfulness"]),
        "Context Precision":    safe_float(ragas_result["context_precision"]),
        "Context Recall":       safe_float(ragas_result["context_recall"]),
        "Answer Relevancy(EN)": safe_float(ragas_result["answer_relevancy"]),
        "KO Answer Relevancy":  float(np.mean(ko_ar_scores)),
    }

    TARGET = 0.85
    for metric, score in scores.items():
        if metric == "Answer Relevancy(EN)":
            note = " ⚠ (한국어 역질문 한계, 참고용)"
        elif metric == "KO Answer Relevancy":
            note = " ✨ (한국어 전용 직접 평가)"
        else:
            note = ""
        status = "✅" if score >= TARGET else "⚠️ "
        bar    = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {status} {metric:25s} {bar} {score:.4f}{note}")

    print()
    faith_score = scores["Faithfulness"]
    print(f"  목표: Faithfulness ≥ {TARGET}")
    if faith_score >= TARGET:
        print(f"  ✅ Faithfulness 목표 달성! ({faith_score:.4f})")
    else:
        gap = TARGET - faith_score
        print(f"  ⚠️  Faithfulness 목표 미달 ({faith_score:.4f}, {gap:.4f} 부족)")
    print("=" * 60)

    output_path = BASE / "output" / "ragas_result.json"
    output_data = {
        "summary": {k: float(v) for k, v in scores.items()},
        "ko_ar_per_question": [
            {"question": item["question"], "ko_ar_score": s}
            for item, s in zip(EVAL_DATASET, ko_ar_scores)
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n  결과 저장: {output_path}")


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    data          = collect_answers(EVAL_DATASET)
    result, ko_ar = run_ragas_evaluation(data)
    print_results(result, ko_ar)