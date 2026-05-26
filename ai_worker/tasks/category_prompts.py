"""챌린지 카테고리·세부카테고리 → SigLIP2 zero-shot 프롬프트 매핑.

각 카테고리마다 "positive" 프롬프트 1~3개 + "negative" 프롬프트 ("unrelated photo")
형태로 묶어서 softmax 후 positive 의 최대 점수를 사용한다.
한국어/영어 프롬프트 혼용 OK (SigLIP2 다국어 지원).
"""

from __future__ import annotations

# 카테고리/서브카테고리 → 프롬프트 리스트.
# 각 항목 첫 번째는 "정답 라벨"(top_label 로 보고 시 사용), 마지막은 negative.
_CATEGORY_PROMPTS: dict[str, list[str]] = {
    "WATER": [
        "a photo of someone drinking water",
        "a glass of water",
        "a water bottle",
        "a clear cup of water",
    ],
    "DIET": [
        "a photo of a healthy meal",
        "a bowl of vegetables",
        "a plate of food",
        "a salad",
    ],
    "SLEEP": [
        "a photo of someone sleeping in bed",
        "a bedroom at night",
        "a person resting in bed",
    ],
    "NO_SMOKING": [
        "a nicotine patch on skin",
        "a no smoking sign",
        "a photo of stopping smoking",
        "a photo of a quit smoking aid",
    ],
    "NO_ALCOHOL": [
        "a photo of non-alcoholic drink",
        "a glass of water instead of alcohol",
        "a no alcohol sign",
    ],
    "DISEASE_CARE": [
        "a photo of taking medication",
        "a pill or tablet",
        "a blood pressure cuff",
        "a glucometer",
    ],
    "MEDITATION": [
        "a photo of meditation",
        "a person sitting cross-legged with eyes closed",
        "a yoga mat",
    ],
    # EXERCISE 는 sub_category 우선
    "EXERCISE": [
        "a photo of exercising",
        "a person working out",
        "fitness activity",
    ],
}

_EXERCISE_SUB_PROMPTS: dict[str, list[str]] = {
    "WALKING": [
        "a photo of someone walking outside",
        "walking shoes on a path",
        "a screenshot of a walking app",
        "step counter showing steps",
    ],
    "RUNNING": [
        "a photo of someone running",
        "a running track",
        "a screenshot of a running app",
        "running shoes on pavement",
    ],
    "STRENGTH": [
        "a photo of weight training",
        "a person lifting dumbbells",
        "a barbell on a gym floor",
    ],
    "CYCLING": [
        "a photo of cycling",
        "a person on a bicycle",
        "a road bike",
    ],
    "SWIMMING": [
        "a photo of swimming in a pool",
        "a swimmer doing freestyle",
        "a swimming lane",
    ],
    "OTHER": [
        "a photo of exercising",
        "a person doing sports",
    ],
}

# Negative 프롬프트 (전 카테고리 공통). softmax 분모에 포함되어 무관 사진의 점수를 낮춤.
_NEGATIVE_PROMPTS: list[str] = [
    "an unrelated photo",
    "a screenshot of an unrelated app",
    "a random object",
]

# 카테고리별 threshold override. 비어있으면 SIGLIP_APPROVE_THRESHOLD 사용.
# 더 엄격(↑) / 관대(↓) 가 필요한 카테고리만 명시.
_CATEGORY_THRESHOLDS: dict[str, float] = {
    # 사진 검증이 까다로운 카테고리 (지나치게 보편적 객체) 는 임계값 ↑
    "WATER": 0.25,
    "NO_ALCOHOL": 0.25,
    # 사진 다양성이 큰 카테고리는 임계값 ↓
    "DIET": 0.18,
    "EXERCISE": 0.18,
}


# 식단 종류별 프롬프트 (그룹 챌린지 diet_type)
_DIET_TYPE_PROMPTS: dict[str, list[str]] = {
    "MEDITERRANEAN": [
        "a photo of mediterranean diet meal with olive oil, fish, vegetables",
        "a plate with grilled fish, olives and salad",
    ],
    "LOW_CARB": [
        "a photo of a low-carb meal with meat and vegetables, no rice or bread",
        "a keto diet plate with steak and greens",
    ],
    "LOW_FAT": [
        "a photo of a low-fat meal with steamed vegetables and lean protein",
        "a healthy plate without fried food",
    ],
    "LOW_SODIUM": [
        "a photo of a low-sodium meal with fresh herbs and vegetables",
        "a bland looking healthy meal without seasoning",
    ],
    "LOW_SUGAR": [
        "a photo of a low-sugar meal without dessert or sweet sauces",
        "a savory meal without sweets",
    ],
}

# 체중 관리 모드별 프롬프트 (체중계/체중기록)
_WEIGHT_PROMPTS: list[str] = [
    "a photo of a body weight scale display showing a number",
    "a digital scale showing weight in kilograms",
    "a person standing on a bathroom scale",
]


def build_prompts_for(
    *,
    category: str,
    sub_category: str | None,
    goal_config: dict | None = None,
) -> list[str]:
    """zero-shot 분류에 넘길 프롬프트 배열 생성.

    positive 들 + negative 들. 첫 번째 positive 가 top_label 로 사용된다.
    goal_config 에 따라 카테고리별 세부 프롬프트가 동적으로 추가된다.
    """
    gc = goal_config or {}
    positives: list[str] = []

    # WEIGHT_MANAGEMENT 카테고리는 체중계 사진
    if category == "WEIGHT_MANAGEMENT":
        positives = list(_WEIGHT_PROMPTS)
    elif category == "EXERCISE" and sub_category:
        positives = list(_EXERCISE_SUB_PROMPTS.get(sub_category, []))
    elif category == "DIET":
        # 그룹 diet_type 우선
        diet_type = gc.get("diet_type")
        if diet_type and diet_type in _DIET_TYPE_PROMPTS:
            positives = list(_DIET_TYPE_PROMPTS[diet_type])
        # 개인 INCLUDE 모드: 사용자가 지정한 음식 (채소/과일/콩/생선 등) 동적 프롬프트
        elif gc.get("diet_mode") == "INCLUDE":
            targets = [t for t in (gc.get("diet_targets") or []) if isinstance(t, str)]
            if targets:
                positives = [f"a photo of a meal containing {t}" for t in targets[:3]]
                positives.append("a plate of healthy food")
        # 개인 AVOID 모드: 회피 음식이 보이지 않는 깨끗한 식사
        elif gc.get("diet_mode") == "AVOID":
            positives = [
                "a photo of a healthy home-cooked meal",
                "a plate of vegetables and rice without fried or processed food",
                "a balanced healthy meal",
            ]
        else:
            positives = list(_CATEGORY_PROMPTS.get(category, []))

    if not positives:
        positives = list(_CATEGORY_PROMPTS.get(category, []))
    if not positives:
        return []
    return positives + _NEGATIVE_PROMPTS


def positive_count(
    category: str,
    sub_category: str | None,
    goal_config: dict | None = None,
) -> int:
    """입력 카테고리에 매칭되는 positive 프롬프트 수 (top score 산정에 사용)"""
    # build_prompts_for 와 동일 분기를 다시 계산하지 않고 길이로 역산.
    prompts = build_prompts_for(category=category, sub_category=sub_category, goal_config=goal_config)
    return max(0, len(prompts) - len(_NEGATIVE_PROMPTS))


def threshold_for(category: str, default: float) -> float:
    """카테고리별 threshold override. 없으면 default."""
    return _CATEGORY_THRESHOLDS.get(category, default)
