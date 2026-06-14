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
    # ── 추가 문항 (혈당/BLOOD_SUGAR) ──────────────────────────────────────────
    {
        "category": "BLOOD_SUGAR",
        "question": "식후 2시간 혈당의 정상 기준은?",
        "option_a": "120 mg/dL 미만",
        "option_b": "140 mg/dL 미만",
        "option_c": "160 mg/dL 미만",
        "option_d": "180 mg/dL 미만",
        "correct_option": "B",
        "explanation": "대한당뇨병학회 기준으로 식후 2시간 혈당은 140 mg/dL 미만이 정상입니다. 140~199 mg/dL은 내당능장애(당뇨 전단계), 200 mg/dL 이상이면 당뇨병으로 진단합니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "당뇨 전단계(공복혈당장애)의 공복혈당 범위는?",
        "option_a": "70~99 mg/dL",
        "option_b": "100~125 mg/dL",
        "option_c": "126~139 mg/dL",
        "option_d": "140 mg/dL 이상",
        "correct_option": "B",
        "explanation": "공복혈당 100~125 mg/dL은 당뇨 전단계(공복혈당장애)로 분류됩니다. 이 단계에서 생활 습관을 개선하면 제2형 당뇨병 발병을 58%까지 예방할 수 있습니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "제1형 당뇨병의 주요 원인은?",
        "option_a": "비만과 신체 활동 부족",
        "option_b": "인슐린 분비 세포(베타세포)를 공격하는 자가면역 반응",
        "option_c": "과도한 탄수화물 섭취",
        "option_d": "스트레스 호르몬 과다 분비",
        "correct_option": "B",
        "explanation": "제1형 당뇨병은 면역 체계가 췌장 베타세포를 공격해 인슐린을 거의 생산하지 못하는 자가면역 질환입니다. 인슐린 투여가 필수이며, 제2형과 달리 생활 습관과 직접적인 관련이 낮습니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "당뇨병의 미세혈관 합병증에 해당하지 않는 것은?",
        "option_a": "당뇨병성 망막병증",
        "option_b": "당뇨병성 신증",
        "option_c": "당뇨병성 신경병증",
        "option_d": "관상동맥 질환",
        "correct_option": "D",
        "explanation": "관상동맥 질환은 대혈관(macrovascular) 합병증입니다. 미세혈관 합병증은 망막병증(실명 위험), 신증(신부전 위험), 신경병증(감각 이상·발 궤양)이 대표적입니다.",
    },
    {
        "category": "BLOOD_SUGAR",
        "question": "제2형 당뇨의 1차 치료 약물로 가장 널리 사용되는 것은?",
        "option_a": "인슐린 글라진",
        "option_b": "메트포르민",
        "option_c": "설포닐우레아",
        "option_d": "GLP-1 수용체 작용제",
        "correct_option": "B",
        "explanation": "메트포르민은 간에서 포도당 생성을 억제하고 인슐린 감수성을 높이는 기전으로 제2형 당뇨의 1차 표준 치료제입니다. 저혈당 위험이 낮고 체중 중립적인 장점이 있습니다.",
    },
    # ── 추가 문항 (고혈압/BLOOD_PRESSURE) ────────────────────────────────────
    {
        "category": "BLOOD_PRESSURE",
        "question": "가면고혈압(masked hypertension)이란?",
        "option_a": "병원에서는 혈압이 높고 일상에서는 정상인 경우",
        "option_b": "병원에서는 혈압이 정상이지만 일상에서는 고혈압인 경우",
        "option_c": "아침에만 혈압이 높은 경우",
        "option_d": "약을 복용해야만 혈압이 정상인 경우",
        "correct_option": "B",
        "explanation": "가면고혈압은 병원 측정에서는 정상이지만 일상이나 가정에서 혈압이 높은 상태입니다. 백의고혈압(병원에서만 높음)과 반대 개념으로, 가정 혈압 측정이 진단에 중요합니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "DASH 식이요법의 핵심 원칙으로 옳은 것은?",
        "option_a": "고단백·저탄수화물 식이 유지",
        "option_b": "채소·과일·저지방 유제품을 늘리고 나트륨·포화지방을 줄임",
        "option_c": "육류 완전 제한",
        "option_d": "하루 한 끼 간헐적 단식 적용",
        "correct_option": "B",
        "explanation": "DASH(Dietary Approaches to Stop Hypertension) 식이는 채소, 과일, 저지방 유제품, 통곡물, 견과류를 늘리고 나트륨·포화지방·가공식품을 줄이는 방식으로, 수축기 혈압을 8~14 mmHg 낮추는 효과가 임상 연구에서 입증되었습니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "ACE 억제제 계열 고혈압 약물의 대표적인 부작용은?",
        "option_a": "빠른 맥박(빈맥)",
        "option_b": "마른기침",
        "option_c": "저칼륨혈증",
        "option_d": "체중 증가",
        "correct_option": "B",
        "explanation": "ACE 억제제는 브라디키닌 분해를 억제해 기도에 브라디키닌이 축적되어 마른기침이 유발됩니다. 기침이 심하면 ARB(안지오텐신 수용체 차단제)로 교체하는 것이 일반적입니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "기립성(직립성) 저혈압의 정의로 옳은 것은?",
        "option_a": "안정 시 수축기 혈압이 90 mmHg 미만인 경우",
        "option_b": "앉거나 누웠다 일어설 때 수축기 혈압이 20 mmHg 이상 하강하는 경우",
        "option_c": "운동 중 혈압이 수축기 180 mmHg 이상 오르는 경우",
        "option_d": "야간 수면 중 혈압이 낮아지는 경우",
        "correct_option": "B",
        "explanation": "기립성 저혈압은 체위 변경 3분 이내에 수축기 혈압 20 mmHg 이상 또는 이완기 혈압 10 mmHg 이상 하강하는 상태입니다. 노인, 당뇨 환자, 이뇨제·혈압약 복용 시 흔하며 낙상 위험이 있습니다.",
    },
    {
        "category": "BLOOD_PRESSURE",
        "question": "정상 맥압(수축기 혈압 - 이완기 혈압)의 범위는?",
        "option_a": "10~20 mmHg",
        "option_b": "30~50 mmHg",
        "option_c": "60~80 mmHg",
        "option_d": "80~100 mmHg",
        "correct_option": "B",
        "explanation": "정상 맥압은 약 30~50 mmHg입니다. 맥압이 60 mmHg 이상으로 넓어지면 대동맥 경직도 증가를 의미하며 심혈관 위험이 높아집니다. 혈압 120/80 mmHg이라면 맥압은 40 mmHg입니다.",
    },
    # ── 추가 문항 (식이/DIET) ─────────────────────────────────────────────────
    {
        "category": "DIET",
        "question": "수용성 식이섬유가 풍부해 혈당·콜레스테롤 조절에 특히 효과적인 식품은?",
        "option_a": "흰 쌀밥",
        "option_b": "닭가슴살",
        "option_c": "귀리(오트밀)",
        "option_d": "달걀",
        "correct_option": "C",
        "explanation": "귀리에는 베타글루칸이라는 수용성 식이섬유가 풍부합니다. 베타글루칸은 장에서 젤을 형성해 포도당 흡수를 늦추고, LDL 콜레스테롤과 결합해 배출을 촉진합니다. 하루 3g 이상 섭취 시 LDL 감소 효과가 있습니다.",
    },
    {
        "category": "DIET",
        "question": "오메가-3 지방산(EPA·DHA)의 주요 효과가 아닌 것은?",
        "option_a": "혈중 중성지방 감소",
        "option_b": "혈소판 응집 억제",
        "option_c": "혈당 직접 감소",
        "option_d": "항염증 효과",
        "correct_option": "C",
        "explanation": "오메가-3(EPA·DHA)는 중성지방 감소, 혈소판 응집 억제, 항염증 작용으로 심혈관을 보호합니다. 혈당을 직접 낮추는 효과는 없습니다. 고등어, 연어, 청어, 참치가 풍부한 공급원입니다.",
    },
    {
        "category": "DIET",
        "question": "혈압을 낮추는 데 도움이 되는 칼륨이 풍부한 식품으로 옳은 것은?",
        "option_a": "흰 빵과 라면",
        "option_b": "바나나, 고구마, 아보카도",
        "option_c": "가공 치즈와 소시지",
        "option_d": "콜라와 에너지 드링크",
        "correct_option": "B",
        "explanation": "칼륨은 신장에서 나트륨 배설을 촉진해 혈압을 낮추는 효과가 있습니다. 바나나, 고구마, 아보카도, 시금치, 콩류가 대표적인 고칼륨 식품입니다. 단, 만성 신장 질환 환자는 칼륨 과다 섭취를 주의해야 합니다.",
    },
    {
        "category": "DIET",
        "question": "트랜스지방이 심혈관 건강에 미치는 영향으로 옳은 것은?",
        "option_a": "LDL(나쁜 콜레스테롤)을 낮추고 HDL(좋은 콜레스테롤)을 높인다",
        "option_b": "LDL을 높이고 HDL을 낮춰 심혈관 질환 위험을 증가시킨다",
        "option_c": "혈당에만 영향을 주고 콜레스테롤과는 무관하다",
        "option_d": "소량은 오히려 심혈관에 도움이 된다",
        "correct_option": "B",
        "explanation": "트랜스지방은 LDL 콜레스테롤을 높이고 HDL 콜레스테롤을 낮춰 심혈관 질환 위험을 증가시킵니다. 부분 수소화 식물성 기름, 마가린, 쇼트닝, 일부 튀긴 가공식품에 함유되어 있으며 섭취를 최소화해야 합니다.",
    },
    {
        "category": "DIET",
        "question": "정제 곡물보다 통곡물 섭취가 당뇨·심혈관 관리에 유리한 이유는?",
        "option_a": "칼로리가 더 낮아서",
        "option_b": "식이섬유·비타민·무기질이 풍부하고 혈당지수(GI)가 낮아서",
        "option_c": "단백질 함량이 훨씬 높아서",
        "option_d": "소화·흡수가 더 빨라 에너지 효율이 높아서",
        "correct_option": "B",
        "explanation": "통곡물은 정제 과정에서 제거되는 겨층과 배아를 포함해 식이섬유, B군 비타민, 마그네슘이 풍부합니다. 혈당지수(GI)가 낮아 혈당을 완만하게 올리며 심혈관 질환과 제2형 당뇨 위험 감소와 연관됩니다.",
    },
    # ── 추가 문항 (운동/EXERCISE) ─────────────────────────────────────────────
    {
        "category": "EXERCISE",
        "question": "유산소 운동을 규칙적으로 할 때 기대되는 혈압 변화는?",
        "option_a": "혈압 변화 없음",
        "option_b": "수축기 혈압 4~9 mmHg 감소 가능",
        "option_c": "이완기 혈압만 20 mmHg 이상 감소",
        "option_d": "혈압이 오히려 상승",
        "correct_option": "B",
        "explanation": "규칙적인 유산소 운동은 혈관 탄력성을 높이고 교감신경 활성을 낮춰 수축기 혈압을 평균 4~9 mmHg 낮출 수 있습니다. 고혈압 환자에게 주 5회, 30분 이상의 중강도 운동이 권장됩니다.",
    },
    {
        "category": "EXERCISE",
        "question": "당뇨 환자가 운동 전 혈당이 100 mg/dL 미만일 때 권장되는 조치는?",
        "option_a": "혈당이 낮으므로 즉시 운동을 시작한다",
        "option_b": "탄수화물 15~30 g을 섭취한 후 운동한다",
        "option_c": "인슐린을 추가 투여한다",
        "option_d": "운동을 당분간 중단한다",
        "correct_option": "B",
        "explanation": "혈당 100 mg/dL 미만에서 운동하면 저혈당 위험이 높아집니다. 탄수화물 15~30 g(과일 한 조각, 주스 반 컵 등)을 섭취하고 15분 후 혈당을 재확인한 뒤 운동하는 것이 안전합니다.",
    },
    {
        "category": "EXERCISE",
        "question": "운동 후 인슐린 감수성이 향상되는 지속 시간은?",
        "option_a": "운동 직후 1~2시간",
        "option_b": "24~48시간",
        "option_c": "1주일",
        "option_d": "운동 중에만 일시적으로 향상",
        "correct_option": "B",
        "explanation": "한 번의 운동 후 근육의 포도당 흡수 능력(인슐린 감수성)은 24~48시간 동안 향상됩니다. 이 때문에 매일 또는 이틀에 한 번씩 규칙적으로 운동하는 것이 혈당 조절에 가장 효과적입니다.",
    },
    {
        "category": "EXERCISE",
        "question": "유산소 운동과 저항성(근력) 운동을 병행할 때의 장점은?",
        "option_a": "어느 하나만 할 때보다 혈당·혈압·체중 관리 효과가 더 크다",
        "option_b": "운동 효과는 같지만 시간이 더 절약된다",
        "option_c": "근력 운동은 혈당을 높이므로 피해야 한다",
        "option_d": "유산소 운동만으로 충분하다",
        "correct_option": "A",
        "explanation": "유산소 운동은 심폐 기능과 인슐린 감수성을, 저항성 운동은 근육량 증가를 통한 기초 포도당 소비를 개선합니다. 두 가지를 병행하면 혈당·혈압·체중 조절 및 심혈관 위험 감소 효과가 각각 단독 운동보다 우수합니다.",
    },
    # ── 추가 문항 (일반/GENERAL) ──────────────────────────────────────────────
    {
        "category": "GENERAL",
        "question": "대한비만학회 기준 한국인의 비만 BMI 기준은?",
        "option_a": "BMI 23 이상",
        "option_b": "BMI 25 이상",
        "option_c": "BMI 27.5 이상",
        "option_d": "BMI 30 이상",
        "correct_option": "B",
        "explanation": "대한비만학회는 BMI 25 이상을 비만으로 정의합니다(WHO 기준 30 이상과 다름). BMI 23~24.9는 과체중(비만 전단계)에 해당합니다. 아시아인은 같은 BMI에서 서구인보다 체지방 비율이 높아 기준을 낮게 적용합니다.",
    },
    {
        "category": "GENERAL",
        "question": "만성 스트레스가 혈당에 미치는 영향은?",
        "option_a": "혈당을 낮춘다",
        "option_b": "혈당과 무관하다",
        "option_c": "코르티솔 분비를 통해 혈당을 높인다",
        "option_d": "인슐린 분비를 직접 증가시킨다",
        "correct_option": "C",
        "explanation": "스트레스 상황에서 분비되는 코르티솔과 에피네프린은 간에서 포도당 생성을 촉진하고 인슐린 저항성을 높여 혈당을 올립니다. 만성 스트레스는 당뇨 환자의 혈당 조절을 어렵게 만드는 주요 요인입니다.",
    },
    {
        "category": "GENERAL",
        "question": "알코올과 혈압의 관계로 옳은 것은?",
        "option_a": "알코올은 혈압에 영향을 주지 않는다",
        "option_b": "소량의 음주는 혈압을 크게 높인다",
        "option_c": "하루 2잔(남성 기준)을 초과하는 음주는 혈압 상승과 연관된다",
        "option_d": "음주 후 혈압은 항상 일시적으로만 올라간다",
        "correct_option": "C",
        "explanation": "하루 알코올 30 g(남성 기준 약 2잔) 초과 음주는 혈압 상승 및 고혈압 위험 증가와 연관됩니다. 알코올은 교감신경을 자극하고 혈관 수축을 유발합니다. 고혈압 환자에게는 절주 또는 금주가 권고됩니다.",
    },
    {
        "category": "GENERAL",
        "question": "금연 1년 후 나타나는 심혈관 건강 변화는?",
        "option_a": "심장 질환 위험이 비흡연자와 동일해진다",
        "option_b": "심장 질환 위험이 흡연자 대비 약 50% 감소한다",
        "option_c": "폐 기능만 개선되고 심혈관에는 변화가 없다",
        "option_d": "금연 효과는 5년 이후부터 나타난다",
        "correct_option": "B",
        "explanation": "금연 1년 후 관상동맥 질환 위험은 흡연자 대비 약 50% 감소합니다. 금연 20분 이내에 혈압과 심박수가 정상화되고, 5년 후 뇌졸중 위험이 감소하며, 15년 후에는 심혈관 위험이 비흡연자 수준에 근접합니다.",
    },
    {
        "category": "GENERAL",
        "question": "하루 충분한 수분 섭취(1.5~2L)가 만성질환 관리에 도움이 되는 이유는?",
        "option_a": "혈당을 직접적으로 낮추기 때문",
        "option_b": "신장의 老廢物 배출을 돕고 혈액 점도를 낮춰 혈압 부담을 줄이기 때문",
        "option_c": "칼로리를 공급해 체력을 유지하기 때문",
        "option_d": "수분은 혈압·혈당과 무관하다",
        "correct_option": "B",
        "explanation": "충분한 수분 섭취는 신장의 노폐물 배출을 돕고, 혈액 점도를 낮춰 심혈관 부담을 줄입니다. 당뇨 환자는 고혈당 시 소변으로 수분 손실이 많아 탈수 위험이 높으므로 특히 중요합니다. 단, 심장·신장 질환자는 전문의 지도 하에 수분량을 조절해야 합니다.",
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
