"""ChallengeTemplate 초기 데이터 삽입 스크립트.

위험도 권고 그래프(RiskRecommendationGraph)의 챌린지 추천은 활성 ChallengeTemplate
풀에서 후보를 고른다. 테이블이 비어 있으면 추천이 0개가 되므로 기본 템플릿을 시드한다.

템플릿 정의는 챌린지 카탈로그 단일 출처(CHALLENGE_CATALOG)를 그대로 따른다:
`RAG/final docs/CHALLENGE_CATALOG_documentation.md` (CHALL_SEC_0004~0017).
카탈로그가 정의한 챌린지 종류·인증방식(사진/체크형)·목표 선택지를 반영한다.
질환·위험도 구간별 권고(저염/저당/지중해식 등)는 템플릿이 아니라 RAG + LLM 권고
(CHALL_SEC_0021/0021A)와 challenge_eligibility_filter 가 담당하므로 여기서 다루지 않는다.

운동 난이도는 challenge_eligibility_filter 의 심혈관 고위험 안전 제외 로직과 정합한다:
고강도(러닝·자전거·근력)는 LEVEL_3 → 심혈관 고위험 시 제외, 저~중강도(걷기·수영·기타)는
LEVEL_1~2 로 유지. (카탈로그 고혈관 고위험 권고 = 저염식·걷기·수영·금연·체중관리)

실행 방법 (로컬):
    docker cp scripts/seed_challenge_templates.py fastapi:/tmp/seed_challenge_templates.py
    docker exec -i fastapi uv run --no-sync python /tmp/seed_challenge_templates.py

실행 방법 (prod EC2 컨테이너):
    docker exec -i -w /app fastapi /app/.venv/bin/python /tmp/seed_challenge_templates.py

title 기준 get_or_create 로 멱등 실행 가능 (이미 있으면 건너뜀).
"""

import asyncio

from tortoise import Tortoise

from app.core.db.databases import TORTOISE_ORM
from app.models.challenge import (
    ChallengeCategory,
    ChallengeDifficulty,
    ExerciseSubType,
    GoalType,
    VerificationType,
)

# (category, sub_category, title, description, goal_type, goal_value_options,
#  default_unit, verification_type, difficulty)
# 출처: CHALLENGE_CATALOG_documentation.md — 카탈로그가 정의한 챌린지 종류 1:1 매핑.
TEMPLATES = [
    # ── 운동 (CHALL_SEC_0004~0009) ──
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.WALKING,
        "걷기 챌린지",
        "하루 목표 걷기 시간을 채우는 저강도 유산소 운동. 혈압·혈당·체중 관리에 도움이 됩니다.",
        GoalType.DURATION,
        [30, 60, 90, 120],
        "분",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_1,
    ),
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.RUNNING,
        "러닝 챌린지",
        "하루 목표 달리기 시간을 채우는 중·고강도 유산소 운동. 심폐 기능 강화에 도움이 됩니다.",
        GoalType.DURATION,
        [30, 60, 90, 120],
        "분",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_3,
    ),
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.CYCLING,
        "자전거 챌린지",
        "일주일 동안 목표 횟수만큼 자전거를 타는 유산소 운동입니다.",
        GoalType.COUNT,
        [1, 2, 3, 4, 5, 6, 7],
        "회",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_3,
    ),
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.STRENGTH,
        "근력 운동 챌린지",
        "하루 목표 근력 운동 시간을 채웁니다. 근육량 증가로 인슐린 저항성 개선에 도움이 됩니다.",
        GoalType.DURATION,
        [20, 30, 40, 60],
        "분",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_3,
    ),
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.SWIMMING,
        "수영 챌린지",
        "일주일 동안 목표 횟수만큼 수영하는 관절 부담이 적은 전신 유산소 운동입니다.",
        GoalType.COUNT,
        [1, 2, 3, 4, 5, 6, 7],
        "회",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_2,
    ),
    (
        ChallengeCategory.EXERCISE,
        ExerciseSubType.OTHER,
        "기타 운동 챌린지",
        "등산·요가·필라테스·홈트레이닝 등 원하는 운동을 일주일 목표 횟수만큼 실천합니다.",
        GoalType.COUNT,
        [1, 2, 3, 4, 5, 6, 7],
        "회",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_2,
    ),
    # ── 생활습관 (CHALL_SEC_0010~0013) ──
    (
        ChallengeCategory.WATER,
        None,
        "물 마시기 챌린지",
        "하루 목표 용량만큼 물을 마십니다. 충분한 수분 섭취는 혈당 희석·신장 보호에 도움이 됩니다.",
        GoalType.AMOUNT,
        [500, 1000, 1500, 2000],
        "mL",
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_1,
    ),
    (
        ChallengeCategory.SLEEP,
        None,
        "수면 챌린지",
        "취침 시간·수면 시간·기상 시간 중 목표를 정해 규칙적인 수면 습관을 만듭니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.CHECK,
        ChallengeDifficulty.LEVEL_1,
    ),
    (
        ChallengeCategory.DIET,
        None,
        "식단 챌린지",
        "권고에 따라 피해야 할 음식을 피하거나 권장 식품을 먹는 식단을 사진으로 인증합니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_1,
    ),
    (
        ChallengeCategory.WEIGHT_MANAGEMENT,
        None,
        "체중 관리 챌린지",
        "설정한 기간 동안 목표 체중(유지·감량)에 도달하도록 관리합니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_2,
    ),
    # ── 금연/금주 (CHALL_SEC_0014~0015) ──
    (
        ChallengeCategory.NO_SMOKING,
        None,
        "금연 챌린지",
        "매일 금연 실천 여부를 인증합니다. 금연은 혈압·심혈관 위험을 가장 빠르게 낮춥니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.PHOTO,
        ChallengeDifficulty.LEVEL_2,
    ),
    (
        ChallengeCategory.NO_ALCOHOL,
        None,
        "금주 챌린지",
        "매일 금주 여부를 체크합니다. 절주·금주는 혈압 조절과 간 건강에 중요합니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.CHECK,
        ChallengeDifficulty.LEVEL_2,
    ),
    # ── 정신건강 (CHALL_SEC_0016) ──
    (
        ChallengeCategory.MEDITATION,
        None,
        "명상 챌린지",
        "앱 내 명상 타이머로 하루 목표 시간만큼 명상합니다. 스트레스 완화에 도움이 됩니다.",
        GoalType.DURATION,
        [3, 5, 10, 20],
        "분",
        VerificationType.CHECK,
        ChallengeDifficulty.LEVEL_1,
    ),
    # ── 질환관리 (CHALL_SEC_0017) ──
    (
        ChallengeCategory.DISEASE_CARE,
        None,
        "당뇨발 관리 챌린지",
        "당뇨병 환자의 발 합병증 예방을 위해 매일 1회 발 자가 점검을 체크형으로 인증합니다.",
        GoalType.CHECK,
        [],
        None,
        VerificationType.CHECK,
        ChallengeDifficulty.LEVEL_1,
    ),
]


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    from app.models.challenge import ChallengeTemplate

    created = 0
    for (
        category,
        sub_category,
        title,
        description,
        goal_type,
        goal_value_options,
        default_unit,
        verification_type,
        difficulty,
    ) in TEMPLATES:
        _, was_created = await ChallengeTemplate.get_or_create(
            title=title,
            defaults=dict(
                category=category,
                sub_category=sub_category,
                description=description,
                goal_type=goal_type,
                goal_value_options=goal_value_options,
                default_unit=default_unit,
                verification_type=verification_type,
                difficulty=difficulty,
                is_active=True,
            ),
        )
        if was_created:
            created += 1

    await Tortoise.close_connections()
    print(f"완료 — ChallengeTemplate {created}개 신규 삽입 (전체 정의 {len(TEMPLATES)}개)")


if __name__ == "__main__":
    asyncio.run(main())
