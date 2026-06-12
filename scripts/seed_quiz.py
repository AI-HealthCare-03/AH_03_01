"""건강 퀴즈 시드 데이터 삽입 스크립트.

실행 방법:
    docker cp scripts/seed_quiz.py fastapi:/tmp/seed_quiz.py
    docker exec -i fastapi uv run --no-sync python /tmp/seed_quiz.py

이미 존재하는 question 은 건너뜁니다 (멱등 실행 가능).
추후 데이터 추가 및 수정 필요함.
"""

import asyncio
import os

import asyncpg

# ── DB 접속 정보 (환경변수에서 읽음; docker-compose 내부 기본값 사용) ──────────
DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER", "ozcoding"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_health"),
)

# ── 퀴즈 데이터 ─────────────────────────────────────────────────────────────────
QUIZZES = [
    # ── 당뇨 (BLOOD_SUGAR) ────────────────────────────────────────────────────
    {
        "category": "BLOOD_SUGAR",
        "question": "한국인 공복혈당의 정상 범위는?",
        "option_a": "60~80 mg/dL",
        "option_b": "70~99 mg/dL",
        "option_c": "100~125 mg/dL",
        "option_d": "80~140 mg/dL",
        "correct_option": "B",
        "explanation": "공복혈당 정상 범위는 70~99 mg/dL입니다. 100~125 mg/dL은 공복혈당장애(당뇨 전단계), 126 mg/dL 이상이 두 번 측정되면 당뇨병으로 진단합니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "당화혈색소(HbA1c) 정상 기준은?",
        "option_a": "4% 미만",
        "option_b": "5.7% 미만",
        "option_c": "6.5% 미만",
        "option_d": "7.0% 미만",
        "correct_option": "B",
        "explanation": "HbA1c 5.7% 미만이 정상입니다. 5.7~6.4%는 당뇨 전단계, 6.5% 이상이면 당뇨병으로 진단합니다. 최근 2~3개월 평균 혈당을 반영합니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "제2형 당뇨병의 가장 큰 위험 인자는?",
        "option_a": "바이러스 감염",
        "option_b": "과도한 운동",
        "option_c": "복부비만과 신체 활동 부족",
        "option_d": "수면 과다",
        "correct_option": "C",
        "explanation": "제2형 당뇨는 인슐린 저항성이 주요 원인입니다. 복부비만, 신체 활동 부족, 고칼로리 식이가 복합적으로 위험을 높입니다. 체중 5~10% 감량만으로도 발병을 늦출 수 있습니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "저혈당 증상으로 옳지 않은 것은?",
        "option_a": "식은땀, 손 떨림",
        "option_b": "가슴 두근거림",
        "option_c": "얼굴이 붉어지고 두통",
        "option_d": "심한 공복감과 어지러움",
        "correct_option": "C",
        "explanation": "얼굴이 붉어지고 두통이 오는 것은 고혈압 증상에 가깝습니다. 저혈당(혈당 70 mg/dL 미만)은 식은땀, 손 떨림, 심박 증가, 극심한 공복감, 어지러움이 특징입니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "당뇨 환자에게 권장되는 하루 유산소 운동량은?",
        "option_a": "주 1회, 60분 이상",
        "option_b": "주 3~5회, 회당 30분 이상 (총 150분 이상)",
        "option_c": "매일 10분 미만의 가벼운 스트레칭",
        "option_d": "주 7회, 회당 90분 이상",
        "correct_option": "B",
        "explanation": "대한당뇨병학회는 주 3~5회, 회당 30분 이상, 총 150분 이상의 중강도 유산소 운동을 권장합니다. 운동은 인슐린 감수성을 높이고 혈당 조절에 직접적인 도움을 줍니다.",
    },
    # ── 고혈압 (BLOOD_PRESSURE) ───────────────────────────────────────────────
    {
        "category": "BLOOD_PRESSURE",
        "question": "고혈압의 진단 기준(수축기/이완기)은?",
        "option_a": "120/80 mmHg 이상",
        "option_b": "130/85 mmHg 이상",
        "option_c": "140/90 mmHg 이상",
        "option_d": "150/95 mmHg 이상",
        "correct_option": "C",
        "explanation": "두 번 이상 측정 시 수축기 140 mmHg 이상 또는 이완기 90 mmHg 이상이면 고혈압으로 진단합니다. 130~139/80~89는 고혈압 전단계(주의혈압)입니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "혈압을 높이는 생활 습관으로 옳은 것은?",
        "option_a": "하루 나트륨 섭취 2,000 mg 이하 유지",
        "option_b": "규칙적인 유산소 운동",
        "option_c": "과도한 음주와 흡연",
        "option_d": "충분한 수면과 스트레스 관리",
        "correct_option": "C",
        "explanation": "과도한 음주와 흡연은 혈관을 수축시키고 심박수를 높여 혈압을 올립니다. 반면 나트륨 제한, 규칙적 운동, 충분한 수면은 혈압 조절에 도움이 됩니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "고혈압 환자가 하루 나트륨 섭취 목표량은?",
        "option_a": "1,000 mg 이하",
        "option_b": "2,000 mg 이하",
        "option_c": "3,500 mg 이하",
        "option_d": "제한 없음",
        "correct_option": "B",
        "explanation": "고혈압 환자의 나트륨 섭취 목표는 하루 2,000 mg(소금 5 g) 이하입니다. 나트륨 1,000 mg 감소 시 수축기 혈압이 약 2~4 mmHg 낮아질 수 있습니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "혈압 측정 시 올바른 방법이 아닌 것은?",
        "option_a": "5분 이상 안정 후 측정",
        "option_b": "측정 30분 전 카페인·흡연 금지",
        "option_c": "운동 직후 바로 측정",
        "option_d": "양쪽 팔을 번갈아 측정 후 높은 값 기준",
        "correct_option": "C",
        "explanation": "운동 직후에는 일시적으로 혈압이 높아지므로 최소 30분 휴식 후 측정해야 정확합니다. 측정 전 카페인, 흡연, 식사도 피하고 5분 이상 안정을 취해야 합니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "고혈압 합병증으로 가장 거리가 먼 것은?",
        "option_a": "뇌졸중",
        "option_b": "심근경색",
        "option_c": "골다공증",
        "option_d": "만성 신장 질환",
        "correct_option": "C",
        "explanation": "고혈압의 주요 합병증은 뇌졸중, 심근경색, 심부전, 만성 신장 질환, 망막 손상 등입니다. 골다공증은 고혈압과 직접적인 인과관계가 없습니다.",
    },
    # ── 식이 (DIET) ───────────────────────────────────────────────────────────
    {
        "category": "DIET",
        "question": "만성질환 예방에 도움이 되는 식사 패턴은?",
        "option_a": "고단백·저탄수화물 극단 식이",
        "option_b": "채소·통곡물·생선 위주의 지중해식 식단",
        "option_c": "하루 1식 간헐적 단식",
        "option_d": "가공식품 위주의 편의 식단",
        "correct_option": "B",
        "explanation": "지중해식 식단은 심혈관 질환, 당뇨, 고혈압 위험을 낮추는 것으로 다수의 임상 연구에서 입증되었습니다. 채소, 통곡물, 올리브오일, 생선, 콩류를 중심으로 합니다.",
    },
    {
        "category": "DIET",
        "question": "혈당 지수(GI)가 낮은 식품은?",
        "option_a": "흰 쌀밥",
        "option_b": "감자",
        "option_c": "렌틸콩",
        "option_d": "식빵",
        "correct_option": "C",
        "explanation": "렌틸콩의 GI는 약 29로 낮습니다. 흰 쌀밥(GI 72), 감자(GI 78), 식빵(GI 70)은 모두 고GI 식품입니다. 저GI 식품은 혈당을 천천히 올려 당뇨 관리에 유리합니다.",
    },
    # ── 운동 (EXERCISE) ───────────────────────────────────────────────────────
    {
        "category": "EXERCISE",
        "question": "근력 운동이 혈당 조절에 도움이 되는 이유는?",
        "option_a": "근육이 포도당을 소비하는 주요 기관이기 때문",
        "option_b": "땀을 통해 당을 배출하기 때문",
        "option_c": "심박수를 낮춰 인슐린을 억제하기 때문",
        "option_d": "지방세포를 근육세포로 전환하기 때문",
        "correct_option": "A",
        "explanation": "근육은 포도당 소비의 약 80%를 담당하는 주요 기관입니다. 근육량이 증가하면 인슐린 감수성이 높아져 혈당 조절 능력이 개선됩니다. 저항 운동을 유산소 운동과 병행하는 것이 효과적입니다.",
    },
    # ── 일반 (GENERAL) ────────────────────────────────────────────────────────
    {
        "category": "GENERAL",
        "question": "만성질환 자가 관리에서 가장 중요한 것은?",
        "option_a": "증상이 없으면 약을 중단한다",
        "option_b": "꾸준한 모니터링과 생활 습관 유지",
        "option_c": "민간요법으로 대체한다",
        "option_d": "병원 방문을 최소화한다",
        "correct_option": "B",
        "explanation": "만성질환은 증상이 없어도 지속적인 관리가 필수입니다. 정기적인 혈압·혈당 측정, 복약 순응, 건강한 식이와 운동 습관이 합병증 예방의 핵심입니다.",
    },
    {
        "category": "GENERAL",
        "question": "수면이 혈당·혈압에 미치는 영향으로 옳은 것은?",
        "option_a": "수면 시간은 혈당·혈압과 무관하다",
        "option_b": "수면 부족(6시간 미만)은 인슐린 저항성과 혈압을 높일 수 있다",
        "option_c": "10시간 이상 자면 혈압이 낮아진다",
        "option_d": "낮잠은 야간 수면 부족을 완전히 보완한다",
        "correct_option": "B",
        "explanation": "수면 부족은 코르티솔·카테콜아민 분비를 증가시켜 인슐린 저항성을 높이고 혈압을 올립니다. 성인 권장 수면 시간은 7~9시간이며, 수면의 질도 중요합니다.",
    },
]


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    inserted = 0
    skipped = 0

    for q in QUIZZES:
        exists = await conn.fetchval('SELECT id FROM "health_quizzes" WHERE "question" = $1', q["question"])
        if exists:
            skipped += 1
            continue

        await conn.execute(
            """
            INSERT INTO "health_quizzes"
                ("question", "option_a", "option_b", "option_c", "option_d",
                 "correct_option", "explanation", "category", "is_active")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
            """,
            q["question"],
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"],
            q["correct_option"],
            q["explanation"],
            q["category"],
        )
        inserted += 1

    await conn.close()
    print(f"완료 — 삽입: {inserted}개 / 스킵(중복): {skipped}개")


if __name__ == "__main__":
    asyncio.run(main())
