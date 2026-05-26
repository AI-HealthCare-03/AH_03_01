"""
CRAG 파이프라인 테스트
"""
from crag_pipeline import build_crag_graph, CRAGState

TEST_CASES = [
    ("당뇨병 환자의 혈당 조절 목표가 어떻게 돼?", None),
    ("고혈압 환자는 혈압을 얼마나 낮춰야 해?",    None),
    ("챌린지 인증 실패하면 어떻게 해?",           None),
    ("나한테 맞는 챌린지 추천해줘", {
        "diabetes":       62.3,
        "hypertension":   44.1,
        "cardiovascular": 38.7,
    }),
]

if __name__ == "__main__":
    print("=" * 60)
    print("  CRAG + LangGraph 파이프라인 테스트")
    print("=" * 60)

    crag = build_crag_graph()

    for question, prediction in TEST_CASES:
        print(f"\n{'=' * 60}")
        print(f"  ❓ 질문: {question}")
        if prediction:
            print(f"  📊 ML 예측: {prediction}")
        print(f"{'=' * 60}")

        initial_state: CRAGState = {
            "question":             question,
            "prediction_result":    prediction,
            "retrieved_context":    [],
            "web_results":          [],
            "final_recommendation": "",
            "rewrite_count":        0,
        }

        for step in crag.stream(initial_state):
            pass

    print(f"\n{'=' * 60}")
    print("  ✅ CRAG 테스트 완료!")
    print("=" * 60)