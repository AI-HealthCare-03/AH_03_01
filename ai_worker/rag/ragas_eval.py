"""
RAGAS 평가 파이프라인
======================================
평가 지표:
    Faithfulness     ← 답변이 검색 문서에 근거하는가? (목표 0.85 이상)
    Answer Relevancy ← 답변이 질문과 관련 있는가?
    Context Precision ← 검색된 문서가 정확한가?
    Context Recall   ← 필요한 정보를 잘 가져왔는가?
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

from crag_pipeline import build_crag_graph, CRAGState, hybrid_search

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent

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
# RAGAS 평가 데이터셋
# ground_truth: 우리가 기대하는 정답 (Context Recall 평가용)
# ─────────────────────────────────────────────
EVAL_DATASET = [
    {
        "question": "당뇨병 환자의 혈당 조절 목표가 어떻게 돼?",
        "ground_truth": "2형당뇨병 성인의 일반적인 혈당 조절 목표는 당화혈색소 6.5% 미만이며, 1형당뇨병 성인은 7.0% 미만이다. 혈당 조절 목표는 환자의 신체적, 정신적, 사회적 여건에 따라 개별화해야 한다.",
        "prediction_result": None,
    },
    {
        "question": "고혈압 환자는 혈압을 얼마나 낮춰야 해?",
        "ground_truth": "고혈압 환자의 일반적인 목표 혈압은 140/90 mmHg 미만이며, 당뇨병을 동반한 경우 130/80 mmHg 미만으로 조절하는 것이 권고된다.",
        "prediction_result": None,
    },
    {
        "question": "챌린지 인증 실패하면 어떻게 해?",
        "ground_truth": "AI가 사진을 분석하여 챌린지와 관련된 활동임을 확인할 수 없는 경우 실패 처리된다. 활동을 명확히 확인할 수 있는 사진을 다시 업로드하거나, 실패 방지권을 사용하여 해당 날짜를 인증 완료 상태로 변경할 수 있다.",
        "prediction_result": None,
    },
    {
        "question": "이상지질혈증 환자의 LDL 콜레스테롤 목표는?",
        "ground_truth": "심혈관 위험도에 따라 LDL 콜레스테롤 목표가 다르다. 초고위험군은 70 mg/dL 미만, 고위험군은 100 mg/dL 미만, 중등도위험군은 130 mg/dL 미만, 저위험군은 160 mg/dL 미만을 목표로 한다.",
        "prediction_result": None,
    },
    {
        "question": "당뇨병 환자에게 운동은 얼마나 해야 해?",
        "ground_truth": "당뇨병 환자는 주 150분 이상 중강도 유산소운동을 권고한다. 운동의 종류, 빈도, 시간, 강도는 나이, 신체능력, 동반질환 등에 따라 개별화해야 하며, 가급적 운동전문가에게 운동처방을 의뢰하는 것이 좋다.",
        "prediction_result": None,
    },
]


# ─────────────────────────────────────────────
# CRAG 파이프라인으로 답변 및 컨텍스트 수집
# ─────────────────────────────────────────────
def collect_answers(eval_dataset: list[dict]) -> dict:
    """
    각 질문에 대해 CRAG 파이프라인 실행 후
    RAGAS 평가용 데이터 수집
    """
    crag = build_crag_graph()

    questions    = []
    answers      = []
    contexts     = []
    ground_truths = []

    print("=" * 60)
    print("  RAGAS 평가용 답변 수집 중...")
    print("=" * 60)

    for i, item in enumerate(eval_dataset):
        question       = item["question"]
        ground_truth   = item["ground_truth"]
        prediction     = item.get("prediction_result")

        print(f"\n  [{i+1}/{len(eval_dataset)}] {question}")

        initial_state: CRAGState = {
            "question":             question,
            "prediction_result":    prediction,
            "retrieved_context":    [],
            "web_results":          [],
            "final_recommendation": "",
            "eval_feedback":        "",
            "retry_count":          0,
        }

        # CRAG 실행
        final_state = None
        for step in crag.stream(initial_state):
            node_name   = list(step.keys())[0]
            final_state = step[node_name]

        # 마지막 상태에서 답변과 컨텍스트 추출
        # stream()은 각 노드의 업데이트만 반환하므로 전체 실행 후 invoke()로 재실행
        result = crag.invoke(initial_state)

        answer       = result.get("final_recommendation", "")
        ctx_docs     = result.get("retrieved_context", [])
        ctx_texts    = [doc["content"] for doc in ctx_docs]

        questions.append(question)
        answers.append(answer)
        contexts.append(ctx_texts)
        ground_truths.append(ground_truth)

        print(f"    ✅ 답변 수집 완료 (컨텍스트 {len(ctx_texts)}개)")

    return {
        "question":    questions,
        "answer":      answers,
        "contexts":    contexts,
        "ground_truth": ground_truths,
    }


# ─────────────────────────────────────────────
# RAGAS 평가 실행
# ─────────────────────────────────────────────
def run_ragas_evaluation(data: dict) -> dict:
    import asyncio
    
    print("\n" + "=" * 60)
    print("  RAGAS 평가 실행 중...")
    print("=" * 60)

    ragas_llm        = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    dataset = Dataset.from_dict(data)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    return result


# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────
def print_results(result):
    print("\n" + "=" * 60)
    print("  📊 RAGAS 평가 결과")
    print("=" * 60)

    # ragas 0.2.x 결과 형식 처리
    scores = {}
    try:
        scores = {
            "Faithfulness":      float(result["faithfulness"]) if hasattr(result["faithfulness"], '__float__') else float(result["faithfulness"][0]),
            "Answer Relevancy":  float(result["answer_relevancy"]) if hasattr(result["answer_relevancy"], '__float__') else float(result["answer_relevancy"][0]),
            "Context Precision": float(result["context_precision"]) if hasattr(result["context_precision"], '__float__') else float(result["context_precision"][0]),
            "Context Recall":    float(result["context_recall"]) if hasattr(result["context_recall"], '__float__') else float(result["context_recall"][0]),
        }
    except Exception:
        # 평균값으로 계산
        import numpy as np
        scores = {
            "Faithfulness":      float(np.mean(result["faithfulness"])),
            "Answer Relevancy":  float(np.mean(result["answer_relevancy"])),
            "Context Precision": float(np.mean(result["context_precision"])),
            "Context Recall":    float(np.mean(result["context_recall"])),
        }

    TARGET = 0.85

    for metric, score in scores.items():
        status = "✅" if score >= TARGET else "⚠️ "
        bar    = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {status} {metric:20s} {bar} {score:.4f}")

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
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({k: float(v) for k, v in scores.items()}, f, ensure_ascii=False, indent=2)
    print(f"\n  결과 저장: {output_path}")


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # 1. 답변 수집
    data = collect_answers(EVAL_DATASET)

    # 2. RAGAS 평가
    result = run_ragas_evaluation(data)

    # 3. 결과 출력
    print_results(result)
