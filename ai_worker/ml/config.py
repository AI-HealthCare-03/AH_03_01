"""ai_worker/ml — 학습 설정 상수 모음.

train_shap.py / predictor.py 가 공통으로 참조하는 값들을 한 곳에 관리한다.
하이퍼파라미터 변경 시 이 파일만 수정하면 된다.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# 타겟 정의
# ──────────────────────────────────────────────────────────────────────────────

# Base 모델 타겟 6종 (train_shap.py 학습 순서와 반드시 일치)
BASE_TARGETS: list[str] = [
    "tg_cat",       # 중성지방  (4-class)
    "hdl_cat",      # HDL 콜레스테롤  (3-class)
    "chol_cat",     # 총콜레스테롤  (3-class)
    "ldl_cat",      # LDL 콜레스테롤  (5-class)
    "HE_HP",        # 고혈압  (binary)
    "HE_DM_HbA1c",  # 당뇨  (binary)
]

# Meta 모델 타겟 3종
META_TARGETS: list[str] = [
    "DI2_dg",       # 이상지질혈증 최종 진단  (binary)
    "HE_HP",        # 고혈압  (binary)
    "HE_DM_HbA1c",  # 당뇨  (binary)
]

# 다중분류 / 이진분류 구분
MULTI_TARGETS: list[str] = ["tg_cat", "hdl_cat", "chol_cat", "ldl_cat"]
BIN_TARGETS: list[str] = ["HE_HP", "HE_DM_HbA1c"]

# 타겟별 클래스 수
N_CLASSES: dict[str, int] = {
    "tg_cat": 4,
    "hdl_cat": 3,
    "chol_cat": 3,
    "ldl_cat": 5,
    "HE_HP": 2,
    "HE_DM_HbA1c": 2,
}

# ──────────────────────────────────────────────────────────────────────────────
# 성별
# ──────────────────────────────────────────────────────────────────────────────

SEXES: list[str] = ["male", "female"]

# ──────────────────────────────────────────────────────────────────────────────
# 학습 하이퍼파라미터
# ──────────────────────────────────────────────────────────────────────────────

RAND_SEED: int = 42
N_FOLDS: int = 5
SHAP_N_FEATURES: int = 15  # SHAP 기반 선택 피처 수

# SHAP 중요도 계산용 경량 사전 학습 모델
SHAP_PRETRAIN_PARAMS: dict = dict(
    n_estimators=200,
    learning_rate=0.05,
    num_leaves=63,
    max_depth=6,
    min_child_samples=30,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=RAND_SEED,
    n_jobs=-1,
    verbose=-1,
)

# 최종 학습 모델 (Base · Meta 공통)
LGBM_PARAMS: dict = dict(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=63,
    max_depth=6,
    min_child_samples=30,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=RAND_SEED,
    n_jobs=-1,
    verbose=-1,
)

# ──────────────────────────────────────────────────────────────────────────────
# 모델 메타
# ──────────────────────────────────────────────────────────────────────────────

MODEL_NAME: str = f"LightGBM_SHAP{SHAP_N_FEATURES}"
MODEL_VERSION: str = "shap-lgbm-v1"

# ──────────────────────────────────────────────────────────────────────────────
# 한국어 레이블 (시각화용)
# ──────────────────────────────────────────────────────────────────────────────

TARGET_KOR: dict[str, str] = {
    "tg_cat": "TG",
    "hdl_cat": "HDL",
    "chol_cat": "Chol",
    "ldl_cat": "LDL",
    "HE_HP": "고혈압",
    "HE_DM_HbA1c": "당뇨",
    "DI2_dg": "이상지질",
}
