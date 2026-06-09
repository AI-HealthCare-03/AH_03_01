"""
ml_risk_predictor_draft.py
==========================
ML 모델 기반 위험도 예측기

현재 risk_predictor.py 의 RuleBasedRiskCalculator 를 교체할 코드.
risk_predictor.py 의 RiskPredictor.predict() 에서 MLRiskPredictor.calculate() 를 호출.

모델 구조:
  preprocess.py → STEP1 Base(지질4종) → STEP2 Meta(이상지질혈증)
                                       → STEP3 Direct(고혈압/당뇨)
  저장 형식: PlattCalibrator(TripleEnsemble(ResidualEnsemble(M1,M2), CatBoost))
  남성 Base: OrdinalClassifier (K-1 누적 이진 분류기)

출력:
  - risk_score    : 0-100 (val+test percentile 기반)
  - risk_level    : 매우낮음/낮음/보통/높음/매우높음
  - top_5_features: SHAP 기반 기여 피처 상위 5개
"""
from __future__ import annotations

import json
import pickle
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

# ──────────────────────────────────────────────────────────────
# 모델 아티팩트 경로 (Docker 볼륨 마운트 경로)
# ── 전처리 파일(preprocess.py/config/kde)도 이 폴더에 포함됨 ──
# 노트북 Section 6-3에서 자동 복사, Section 7에서 Drive 백업
# Docker: docker-compose volumes 로 /app/models/ 마운트 필요
# ──────────────────────────────────────────────────────────────
MODEL_ARTIFACT_DIR = Path("/app/models/rb3_a4_cal_cb_ordm_aha_fF80_mM80_0609")


# ──────────────────────────────────────────────────────────────
# pkl 역직렬화용 앙상블 클래스 정의
# (lgbm_model.pkl 로드 시 이 클래스들이 필요)
# ──────────────────────────────────────────────────────────────
class ResidualEnsemble:
    """LGBM M1 × 0.6 + M2 × 0.4 앙상블"""
    def __init__(self, m1, m2, alpha: float = 0.4):
        self.m1 = m1
        self.m2 = m2
        self.alpha = alpha

    def predict_proba(self, X):
        return (1 - self.alpha) * self.m1.predict_proba(X) + \
               self.alpha * self.m2.predict_proba(X)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


class TripleEnsemble:
    """ResidualEnsemble × 0.7 + CatBoost × 0.3 앙상블"""
    def __init__(self, lgbm_model, cb_model, cb_alpha: float = 0.3):
        self.lgbm_model = lgbm_model
        self.cb_model = cb_model
        self.cb_alpha = cb_alpha

    def predict_proba(self, X):
        return (1 - self.cb_alpha) * self.lgbm_model.predict_proba(X) + \
               self.cb_alpha * self.cb_model.predict_proba(X)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


class OrdinalClassifier:
    """남성 Base 모델 전용 — K-1 누적 이진 분류기 (pkl 역직렬화용)"""
    def __init__(self, params, n_cls):
        self.params = params
        self.n_cls = n_cls
        self.clfs_ = []

    def predict_proba(self, X):
        K = self.n_cls - 1
        cum = np.stack([c.predict_proba(X)[:, 1] for c in self.clfs_], axis=1)
        for k in range(1, K):
            cum[:, k] = np.minimum(cum[:, k], cum[:, k - 1])
        n = len(X) if hasattr(X, "__len__") else X.shape[0]
        probs = np.empty((n, self.n_cls))
        probs[:, 0] = 1 - cum[:, 0]
        probs[:, -1] = cum[:, -1]
        for k in range(1, K):
            probs[:, k] = cum[:, k - 1] - cum[:, k]
        probs = np.clip(probs, 0, 1)
        probs /= probs.sum(axis=1, keepdims=True)
        return probs

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


class PlattCalibrator:
    """Platt / Temperature Scaling 확률 보정 래퍼"""
    def __init__(self, base_model):
        self.base_model = base_model
        self._lr = None
        self._T = 1.0
        self._n_cls = None

    def predict_proba(self, X):
        from scipy.special import softmax
        raw = self.base_model.predict_proba(X)
        if self._n_cls == 2 and self._lr is not None:
            cal = self._lr.predict_proba(raw[:, 1].reshape(-1, 1))[:, 1]
            return np.column_stack([1 - cal, cal])
        logits = np.log(np.clip(raw, 1e-10, 1))
        return softmax(logits / self._T, axis=1)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


# ──────────────────────────────────────────────────────────────
# 위험 확률 계산 (AHA/ACC + 대한고혈압학회 기준)
# ──────────────────────────────────────────────────────────────
def _risk_prob_for_score(proba: np.ndarray, n_cls: int) -> float:
    """다중클래스 모델의 대표 위험 확률 계산.

    가중치 기준:
    - HE_HP(4): AHA/ACC 2017 + 대한고혈압학회 2022 — 단계별 심혈관 상대위험도
      정상(0) / 주의혈압(0.25) / 고혈압1기(0.60) / 고혈압2기(1.0)
    - HE_DM(3): ADA 2023 + 대한당뇨병학회 2023 — DPP 10년 진행률 ~50%
      정상(0) / 전당뇨(0.50) / 당뇨(1.0)
    - binary(2): 양성 확률 직접 사용 (이상지질혈증)
    """
    if n_cls == 2:
        return float(proba[1])
    elif n_cls == 4:
        # 고혈압: AHA/ACC 2017 + 대한고혈압학회 가이드라인 가중치
        return float(0.25 * proba[1] + 0.60 * proba[2] + 1.00 * proba[3])
    elif n_cls == 3:
        # 당뇨: ADA + 대한당뇨병학회 가이드라인 가중치
        return float(0.50 * proba[1] + 1.00 * proba[2])
    else:
        return float(proba[-1])


# ──────────────────────────────────────────────────────────────
# Percentile 기반 Risk Score (0-100)
# ──────────────────────────────────────────────────────────────
_SCORE_REFERENCE: dict | None = None  # 앱 시작 시 1회 로드


def _load_score_reference(artifact_dir: Path) -> dict:
    global _SCORE_REFERENCE
    if _SCORE_REFERENCE is None:
        ref_path = artifact_dir / "risk_score_reference.json"
        if ref_path.exists():
            with open(ref_path, encoding="utf-8") as f:
                _SCORE_REFERENCE = json.load(f)
        else:
            _SCORE_REFERENCE = {}
    return _SCORE_REFERENCE


def _prob_to_score(
    artifact_dir: Path,
    sex_str: str,
    model_key: str,   # e.g. "meta_DI2_dg", "direct_HE_HP"
    risk_prob: float,
) -> int:
    """확률 → 0-100 위험 점수 (val+test percentile 기반, fallback: 직접 변환)"""
    ref = _load_score_reference(artifact_dir)
    pcts = ref.get(sex_str, {}).get(model_key, {}).get("percentile_probs")
    if pcts is None:
        return int(round(min(risk_prob * 100, 100)))
    score = int(np.searchsorted(pcts, risk_prob, side="right"))
    return min(score, 100)


def _score_to_level(score: int) -> str:
    if score <= 20:   return "매우 낮음"
    elif score <= 40: return "낮음"
    elif score <= 60: return "보통"
    elif score <= 80: return "높음"
    else:             return "매우 높음"


# ──────────────────────────────────────────────────────────────
# SHAP Top-5 기여 피처
# ──────────────────────────────────────────────────────────────

# 피처 한국어 이름 매핑 (54개 전체, 중복 없음)
FEAT_KOR = {
    # 신체 계측
    "age": "나이", "height_cm": "키", "weight_kg": "체중",
    "waist_cm": "허리둘레", "BMI": "체질량지수(BMI)",
    "WHtR": "허리-키 비율", "WHtR_risk": "허리-키 위험",
    "bmi_age_index": "BMI-나이 복합 지수",
    "age_male_peak": "남성 최고 위험 연령대",
    "age_whtr_inter": "나이-허리키비율 상호작용",
    # 혈압
    "systolic_bp": "수축기혈압", "diastolic_bp": "이완기혈압",
    "bp_cat": "혈압 구간",
    # 혈당
    "fasting_blood_sugar": "공복혈당",
    "fpg_risk_continuous": "공복혈당 위험",
    "HbA1c_proxy_home": "당화혈색소 추정치",
    "HbA1c_proxy_home_v2": "당화혈색소 추정치(v2)",
    "glucose_age_interaction": "혈당-나이 상호작용",
    "glucose_adiposity_interaction": "혈당-비만 상호작용",
    "glucose_sodium_interaction": "혈당-나트륨 상호작용",
    # 지질 추정치
    "TG_proxy_mgdl": "중성지방 추정치", "HDL_proxy_mgdl": "HDL 추정치",
    "LDL_proxy": "LDL 추정치", "TC_residual_risk": "총콜레스테롤 위험",
    "HDL_LOW_RISK_PROXY": "HDL 저하 위험 추정치",
    "HDL_male_risk": "남성 HDL 위험",
    "TG_male_risk": "남성 중성지방 위험",
    "TG_female_risk": "여성 중성지방 위험",
    # 지질 메타 피처 — TG
    "prob_tg_cat_0": "중성지방(정상)", "prob_tg_cat_1": "중성지방(경계)",
    "prob_tg_cat_2": "중성지방(높음)",
    # 지질 메타 피처 — HDL
    "prob_hdl_cat_0": "HDL(낮음)", "prob_hdl_cat_1": "HDL(정상)",
    "prob_hdl_cat_2": "HDL(높음)", "prob_hdl_cat_pos": "HDL 저하 위험",
    # 지질 메타 피처 — TC
    "prob_chol_cat_0": "총콜레스테롤(정상)", "prob_chol_cat_1": "총콜레스테롤(경계)",
    "prob_chol_cat_2": "총콜레스테롤(높음)", "prob_chol_cat_pos": "총콜레스테롤 위험",
    # 지질 메타 피처 — LDL
    "prob_ldl_cat_0": "LDL(최적)", "prob_ldl_cat_1": "LDL(정상)",
    "prob_ldl_cat_2": "LDL(경계)", "prob_ldl_cat_3": "LDL(높음)",
    "prob_ldl_cat_4": "LDL(매우높음)", "prob_ldl_cat_pos": "LDL 위험",
    # 복합 지수
    "metabolic_age": "기능적 연령", "GLYCEMIC_BURDEN_PROXY": "혈당 부담 지수",
    "lipid_hidden_risk_proxy": "숨은 지질 위험", "body_metabolic_score": "대사 건강 점수",
    # 생활습관
    "FAMILY_HP": "고혈압 가족력", "DRINK_RISK": "음주 위험",
    "walk_day": "걷기 일수", "SLEEP_AVG": "평균 수면시간",
    "SLEEP_WEEKDAY": "주중 수면시간", "SLEEP_WEEKEND": "주말 수면시간",
    "SLEEP_IMBALANCE": "수면 불균형",
    "alcohol_freq_y": "음주 빈도",
    "breakfast_freq": "아침식사 빈도", "fruit_freq": "과일 섭취 빈도",
    "out_meal_freq": "외식 빈도",
    "water_count": "하루 물 섭취량", "water_ml_per_kg": "체중 대비 물 섭취량",
    "anemia": "빈혈 여부",
    # KDE 백분위
    "tg_proxy_kde_pct": "중성지방 분포 위치",
    "hdl_proxy_kde_pct": "HDL 분포 위치",
    "tc_proxy_kde_pct": "총콜레스테롤 분포 위치",
    "ldl_proxy_kde_pct": "LDL 분포 위치",
    "gbp_kde_pct": "혈당 부담 분포 위치",
    "whtr_kde_pct_v2": "허리-키 비율 분포 위치",
    "meta_age_kde_pct": "기능적 연령 분포 위치",
    "wt_bmi_idx_pct": "체중-BMI 분포 위치",
}


def _unwrap_lgbm(model, max_depth: int = 10):
    """래퍼 클래스를 재귀적으로 벗겨 SHAP 이 지원하는 LGBMClassifier 를 반환한다.
    PlattCalibrator 이중 래핑(PlattCalibrator → PlattCalibrator → ...)도 처리."""
    for _ in range(max_depth):
        if isinstance(model, PlattCalibrator):
            model = model.base_model
        elif isinstance(model, TripleEnsemble):
            model = model.lgbm_model
        elif isinstance(model, ResidualEnsemble):
            model = model.m1
        else:
            break
    return model


def _get_top5_features(
    model, feature_cols: list[str], X_in, predicted_class: int, n: int = 5
) -> list[dict[str, Any]]:
    """SHAP 기반 Top-N 기여 피처 반환 (실패 시 빈 리스트)"""
    try:
        import shap
        # OrdinalClassifier는 SHAP 불가 → 빈 리스트
        if isinstance(model, OrdinalClassifier):
            return []
        # 래퍼 클래스 언래핑 → 실제 LGBMClassifier
        lgbm_model = _unwrap_lgbm(model)
        # 언래핑 후에도 OrdinalClassifier면 SHAP 불가
        if isinstance(lgbm_model, OrdinalClassifier):
            return []
        explainer = shap.TreeExplainer(lgbm_model)
        shap_vals = explainer.shap_values(X_in)
        # 항상 위험 클래스(마지막) 기준으로 SHAP 계산
        # → positive = 위험 증가↑, negative = 위험 감소↓ 로 일관된 해석
        if isinstance(shap_vals, list):
            risk_cls_idx = len(shap_vals) - 1
            sv = np.array(shap_vals[risk_cls_idx]).flatten()[:len(feature_cols)]
        elif isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
            risk_cls_idx = shap_vals.shape[2] - 1
            sv = shap_vals[0, :, risk_cls_idx]
        else:
            sv = np.array(shap_vals).flatten()[:len(feature_cols)]

        top_idx = np.argsort(np.abs(sv))[-n:][::-1]
        result = []
        for i in top_idx:
            fname = feature_cols[i] if i < len(feature_cols) else f"feat_{i}"
            contribution = float(sv[i])
            result.append({
                "feature":           fname,
                "name_kor":          FEAT_KOR.get(fname, fname),
                "shap_contribution": round(contribution, 4),
                "direction":         "위험 증가↑" if contribution > 0 else "위험 감소↓",
            })
        return result
    except Exception as e:
        import logging, traceback
        logging.getLogger(__name__).error(
            f"[SHAP] 실패: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        )
        return []


# ──────────────────────────────────────────────────────────────
# 예측 클래스 → RiskLevel 매핑
# ──────────────────────────────────────────────────────────────
from app.models.health import RiskLevel  # noqa: E402

CLASS_TO_RISK_LEVEL = {
    "HE_HP": {
        0: RiskLevel.NORMAL,
        1: RiskLevel.CAUTION,
        2: RiskLevel.RISK,
        3: RiskLevel.HIGH_RISK,
    },
    "HE_DM_HbA1c": {
        0: RiskLevel.NORMAL,
        1: RiskLevel.CAUTION,
        2: RiskLevel.RISK,
    },
    "DI2_dg": {
        0: RiskLevel.NORMAL,
        1: RiskLevel.RISK,
    },
}

LIPID_BASE_TARGETS = [
    ("tg_cat",   3),
    ("hdl_cat",  3),
    ("chol_cat", 3),
    ("ldl_cat",  5),
]


# ──────────────────────────────────────────────────────────────
# Colab pkl 역직렬화 — 클래스 경로 재매핑
# Colab에서 저장된 pkl은 클래스가 __mp_main__ / __main__ 에 등록됨
# FastAPI 환경에서는 app.services.ml.ml_risk_predictor_draft 로 매핑 필요
# ──────────────────────────────────────────────────────────────
_THIS_MODULE = "app.services.ml.ml_risk_predictor_draft"
_COLAB_CLASS_NAMES = {
    "PlattCalibrator", "ResidualEnsemble", "TripleEnsemble", "OrdinalClassifier",
}


class _ColabUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if name in _COLAB_CLASS_NAMES and module in ("__mp_main__", "__main__"):
            module = _THIS_MODULE
        return super().find_class(module, name)


def _pkl_load(path: Path):
    """Colab pkl 안전 로드 (클래스 경로 재매핑 포함)"""
    with open(path, "rb") as f:
        return _ColabUnpickler(f).load()


# ──────────────────────────────────────────────────────────────
# 모델 로더
# ──────────────────────────────────────────────────────────────
def _load_model(
    artifact_dir: Path, sex: str, layer: str, target: str
) -> tuple:
    """pkl 로드 → (model, feature_cols, threshold) 반환"""
    d = artifact_dir / sex / f"{layer}_{target}"
    with open(d / "lgbm_model.pkl", "rb") as f:
        data = _ColabUnpickler(f).load()
    feat = json.loads((d / "feature_columns.json").read_text(encoding="utf-8"))
    cols = [x["name"] for x in sorted(feat["features"], key=lambda x: x["order_index"])]
    thr  = json.loads((d / "threshold_config.json").read_text(encoding="utf-8"))["threshold"]
    return data["model"], cols, thr


# ──────────────────────────────────────────────────────────────
# 핵심 추론 함수
# ──────────────────────────────────────────────────────────────
def _get_sex_str(gender: str | int | None) -> str:
    if gender is None:
        return "male"
    if isinstance(gender, int):
        return "female" if gender == 2 else "male"
    if str(gender).lower() in ("female", "f", "여", "2"):
        return "female"
    return "male"


def predict_disease(
    raw_input: dict[str, Any],
    target: str,
    preprocess_module,
    preprocess_config: dict,
    kde_reference,
    artifact_dir: Path = MODEL_ARTIFACT_DIR,
) -> dict[str, Any]:
    """
    raw_input → preprocess → predict_proba → Risk Score + Top5 Features

    Returns
    -------
    {
        "class_probabilities": dict,
        "risk_signal_probability": float,
        "risk_score": int,            # 0-100 (percentile 기반)
        "risk_level": str,            # 매우낮음/낮음/보통/높음/매우높음
        "risk_level_enum": RiskLevel,
        "predicted_class": int,
        "threshold": float,
        "top_5_features": list[dict],
    }
    """
    import pandas as pd

    sex_str  = _get_sex_str(raw_input.get("sex") or raw_input.get("gender"))
    sex_code = 2 if sex_str == "female" else 1

    # ── 1. 전처리 ──────────────────────────────────────────────
    df_input = pd.DataFrame([raw_input])
    df_feat  = preprocess_module.preprocess(df_input, preprocess_config, kde_reference)
    df_feat["sex"] = sex_code

    # ── 2. 지질 Base 모델 (DI2_dg 전용) ───────────────────────
    meta_features: dict[str, float] = {}
    if target == "DI2_dg":
        for bt, n_cls in LIPID_BASE_TARGETS:
            bmodel, bcols, _ = _load_model(artifact_dir, sex_str, "base", bt)
            X_b   = df_feat.reindex(columns=bcols, fill_value=0).values
            bprob = bmodel.predict_proba(X_b)
            if n_cls == 2:
                meta_features[f"prob_{bt}_pos"] = float(bprob[0, 1])
            else:
                for c in range(n_cls):
                    meta_features[f"prob_{bt}_{c}"] = float(bprob[0, c])

    # ── 3. 대상 모델 추론 ──────────────────────────────────────
    if target == "DI2_dg":
        layer = "meta"
        X_in  = pd.DataFrame([meta_features])
    else:
        layer = "direct"
        X_in  = df_feat

    model, feat_cols, threshold = _load_model(artifact_dir, sex_str, layer, target)
    X_arr = X_in.reindex(columns=feat_cols, fill_value=0).values
    proba = model.predict_proba(X_arr)[0]
    n_cls = len(proba)

    # ── 4. 예측 클래스 결정 ────────────────────────────────────
    if n_cls == 2:
        pred_class = int(proba[1] >= threshold)
    else:
        pred_class = int(np.argmax(proba))

    # ── 5. Risk Score (0-100, percentile 기반) ─────────────────
    model_key  = f"{layer}_{target}"
    risk_prob  = _risk_prob_for_score(proba, n_cls)
    risk_score = _prob_to_score(artifact_dir, sex_str, model_key, risk_prob)
    level_str  = _score_to_level(risk_score)

    # ── 6. SHAP Top5 기여 피처 ─────────────────────────────────
    top5 = _get_top5_features(model, feat_cols, X_arr, pred_class)

    # ── 7. 출력 구성 ───────────────────────────────────────────
    label_keys = {
        "HE_HP":        ["normal", "elevated", "stage1", "stage2"],
        "HE_DM_HbA1c":  ["normal", "prediabetes", "diabetes"],
        "DI2_dg":        ["normal", "dyslipidemia"],
    }
    keys       = label_keys.get(target, [str(i) for i in range(n_cls)])
    class_probs = {k: round(float(p), 4) for k, p in zip(keys, proba)}
    risk_signal = round(float(1.0 - proba[0]), 4)
    risk_level  = CLASS_TO_RISK_LEVEL[target].get(pred_class, RiskLevel.NORMAL)

    return {
        "class_probabilities":   class_probs,
        "risk_signal_probability": risk_signal,
        "risk_score":            risk_score,
        "risk_level":            level_str,
        "risk_level_enum":       risk_level,
        "predicted_class":       pred_class,
        "threshold":             threshold,
        "top_5_features":        top5,
    }


# ──────────────────────────────────────────────────────────────
# MLRiskPredictor — RuleBasedRiskCalculator 교체용 클래스
# risk_predictor.py 의 RiskPredictor.predict() 에서 호출
# ──────────────────────────────────────────────────────────────
class MLRiskPredictor:
    """
    학습된 ML 모델 기반 위험도 계산기.
    기존 PredictionInput / PredictionOutput 인터페이스 유지.
    서버 시작 시 _lazy_load() 로 모델을 1회만 로드.
    """

    def __init__(self, artifact_dir: Path = MODEL_ARTIFACT_DIR) -> None:
        self.artifact_dir = artifact_dir
        self._preprocess  = None
        self._cfg         = None
        self._kde         = None
        self._loaded      = False

    def _lazy_load(self) -> None:
        """최초 호출 시 preprocess 모듈 + 설정 로드.

        전처리 파일(preprocess.py / preprocess_config.json / kde_reference.pkl)은
        노트북 Section 6-3에서 artifact_dir 에 자동 복사됨.
        Docker 배포 시 /app/models/ 볼륨 마운트만 하면 됨.
        """
        if self._loaded:
            return
        import importlib.util

        preprocess_py = self.artifact_dir / "preprocess.py"
        spec = importlib.util.spec_from_file_location("preprocess", preprocess_py)
        self._preprocess = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self._preprocess)
        self._cfg = json.loads(
            (self.artifact_dir / "preprocess_config.json").read_text(encoding="utf-8")
        )
        with open(self.artifact_dir / "kde_reference.pkl", "rb") as f:
            self._kde = pickle.load(f)
        self._loaded = True

    def calculate(self, payload: Any) -> Any:
        """PredictionInput → PredictionOutput (기존 인터페이스 호환)"""
        from app.services.ml.risk_predictor import PredictionOutput, RiskFactor
        from app.models.health import DiseaseType

        self._lazy_load()

        TARGET_MAP = {
            DiseaseType.HYPERTENSION:   "HE_HP",
            DiseaseType.DIABETES:       "HE_DM_HbA1c",
            DiseaseType.CARDIOVASCULAR: "DI2_dg",
        }
        target = TARGET_MAP[payload.disease_type]

        raw = {
            "age":                 payload.age,
            "sex":                 2 if (payload.gender or "").lower() in ("female", "f", "여") else 1,
            "height_cm":           float(payload.height_cm)              if payload.height_cm else None,
            "weight_kg":           float(payload.weight_kg)              if payload.weight_kg else None,
            "waist_cm":            float(payload.waist_cm)               if payload.waist_cm else None,
            "systolic_bp":         float(payload.blood_pressure_systolic) if payload.blood_pressure_systolic else None,
            "diastolic_bp":        float(payload.blood_pressure_diastolic) if payload.blood_pressure_diastolic else None,
            "fasting_blood_sugar": float(payload.fasting_glucose)         if payload.fasting_glucose else None,
            **payload.extra,
        }

        result = predict_disease(
            raw_input=raw,
            target=target,
            preprocess_module=self._preprocess,
            preprocess_config=self._cfg,
            kde_reference=self._kde,
            artifact_dir=self.artifact_dir,
        )

        # SHAP top5 → RiskFactor 변환
        # weight: 부호 유지 (양수=위험 증가↑, 음수=위험 감소↓)
        # UI에서 weight > 0 → 빨간 막대, weight < 0 → 파란 막대
        contributing = [
            RiskFactor(
                factor=f["feature"],
                weight=f["shap_contribution"],  # 부호 그대로 저장
                description=f"{f['name_kor']}  {f['direction']}",
            )
            for f in result["top_5_features"]
        ]

        return PredictionOutput(
            disease_type=payload.disease_type,
            risk_score=Decimal(str(result["risk_score"])),
            risk_level=result["risk_level_enum"],
            contributing_factors=contributing,
            model_version="ml-v2.0-aha",
        )
