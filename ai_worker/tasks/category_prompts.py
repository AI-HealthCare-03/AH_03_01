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


def build_prompts_for(*, category: str, sub_category: str | None) -> list[str]:
    """zero-shot 분류에 넘길 프롬프트 배열 생성.

    positive 들 + negative 들. 첫 번째 positive 가 top_label 로 사용된다.
    """
    positives: list[str] = []
    if category == "EXERCISE" and sub_category:
        positives = list(_EXERCISE_SUB_PROMPTS.get(sub_category, []))
    if not positives:
        positives = list(_CATEGORY_PROMPTS.get(category, []))
    if not positives:
        return []
    return positives + _NEGATIVE_PROMPTS


def positive_count(category: str, sub_category: str | None) -> int:
    """입력 카테고리에 매칭되는 positive 프롬프트 수 (top score 산정에 사용)"""
    if category == "EXERCISE" and sub_category:
        return len(_EXERCISE_SUB_PROMPTS.get(sub_category, []))
    return len(_CATEGORY_PROMPTS.get(category, []))
