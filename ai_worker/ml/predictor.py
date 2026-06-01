"""SHAP 스태킹 앙상블 모델 추론 클래스.

train_shap.py 로 학습·저장된 pkl 파일을 로드해 위험도를 예측한다.
worker.py 의 _run_inference() 에서 이 클래스를 호출한다.

pkl 파일 레이아웃 (train_shap.py 출력 기준):
    models/
        shap_base_{sex}_{target}.pkl    # 2성별 × 6타겟 = 12개
        shap_meta_{sex}_{target}.pkl    # 2성별 × 3타겟 = 6개

각 pkl 내부 구조:
    base pkl  → {'model', 'preprocessor', 'oof_prob', 'metrics_val', 'metrics_test'}
    meta pkl  → {'model', 'meta_feature_cols', 'metrics_val', 'metrics_test'}
"""

from __future__ import annotations

import logging
import pickle
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from app.models.health import DiseaseType, RiskLevel
from app.services.ml.risk_predictor import (
    PredictionInput,
    PredictionOutput,
    RiskFactor,
    RuleBasedRiskCalculator,
)
from ai_worker.ml.config import (
    BASE_TARGETS,
    META_TARGETS,
    MODEL_VERSION,
    N_CLASSES,
)

logger = logging.getLogger("ai_worker.ml.predictor")


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _bmi(height_cm: Decimal | None, weight_kg: Decimal | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    h = float(height_cm) / 100.0
    return float(weight_kg) / (h * h) if h > 0 else None


def _risk_score_to_level(prob: float) -> RiskLevel:
    """Meta 모델 양성 클래스 확률 → RiskLevel."""
    if prob >= 0.70:
        return RiskLevel.HIGH_RISK
    if prob >= 0.45:
        return RiskLevel.RISK
    if prob >= 0.20:
        return RiskLevel.CAUTION
    return RiskLevel.NORMAL


# ──────────────────────────────────────────────────────────────────────────────
# MLRiskPredictor
# ──────────────────────────────────────────────────────────────────────────────

class MLRiskPredictor:
    """학습된 SHAP 스태킹 앙상블 모델로 만성질환 위험도를 예측한다.

    Parameters
    ----------
    model_dir:
        shap_base_*.pkl / shap_meta_*.pkl 이 저장된 디렉토리.
    fallback_on_error:
        모델 로드 실패 또는 추론 오류 시 RuleBasedRiskCalculator 로 자동 폴백.
    """

    def __init__(
        self,
        model_dir: Path | str = Path("./models"),
        fallback_on_error: bool = True,
    ) -> None:
        self._model_dir = Path(model_dir)
        self._fallback_on_error = fallback_on_error
        self._fallback = RuleBasedRiskCalculator()
        self._base: dict[str, dict[str, Any]] = {}   # [sex][target]
        self._meta: dict[str, dict[str, Any]] = {}   # [sex][target]
        self._loaded = False

    # ── 로드 ──────────────────────────────────────────────────────────────────

    def load(self) -> None:
        """pkl 파일 전체 로드. 워커 시작 시 1회 호출."""
        missing: list[str] = []
        for sex in ("male", "female"):
            self._base[sex] = {}
            self._meta[sex] = {}
            for target in BASE_TARGETS:
                path = self._model_dir / f"shap_base_{sex}_{target}.pkl"
                if not path.exists():
                    missing.append(str(path)); continue
                with open(path, "rb") as fh:
                    self._base[sex][target] = pickle.load(fh)  # noqa: S301
            for target in META_TARGETS:
                path = self._model_dir / f"shap_meta_{sex}_{target}.pkl"
                if not path.exists():
                    missing.append(str(path)); continue
                with open(path, "rb") as fh:
                    self._meta[sex][target] = pickle.load(fh)  # noqa: S301

        if missing:
            msg = (
                f"모델 파일 누락 ({len(missing)}개): "
                f"{missing[:3]}{'...' if len(missing) > 3 else ''}"
            )
            if self._fallback_on_error:
                logger.warning("%s — 룰 폴백 사용", msg)
            else:
                raise FileNotFoundError(msg)
        else:
            self._loaded = True
            logger.info("MLRiskPredictor 로드 완료 (model_dir=%s)", self._model_dir)

    # ── 피처 변환 ─────────────────────────────────────────────────────────────

    def _build_feature_row(
        self, payload: PredictionInput, feature_names: list[str]
    ) -> np.ndarray:
        """PredictionInput → 모델 입력 벡터.

        feature_names 는 학습 시 X_train 의 전체 원본 컬럼 목록이다.
        매핑되지 않는 피처는 0으로 채운다.
        """
        bmi = _bmi(payload.height_cm, payload.weight_kg)
        raw: dict[str, float] = {
            "age":            float(payload.age) if payload.age is not None else 0.0,
            "sex":            1.0 if payload.gender == "male" else 2.0,  # KNHANES 코딩: 남=1, 여=2
            "HE_ht":          _as_float(payload.height_cm) or 0.0,
            "HE_wt":          _as_float(payload.weight_kg) or 0.0,
            "HE_wc":          _as_float(payload.waist_cm) or 0.0,
            "HE_BMI":         bmi or 0.0,
            "HE_sbp":         _as_float(payload.blood_pressure_systolic) or 0.0,
            "HE_dbp":         _as_float(payload.blood_pressure_diastolic) or 0.0,
            "HE_glu":         _as_float(payload.fasting_glucose) or 0.0,
            "HE_HbA1c":       _as_float(payload.hba1c) or 0.0,
            "sm_now":         1.0 if payload.is_smoker else 0.0,
            "alcohol":        {None: 0.0, "NONE": 0.0, "LIGHT": 1.0, "MODERATE": 2.0, "HEAVY": 3.0}.get(
                              payload.alcohol_intake, 0.0),
            "FAMILY_DM":      1.0 if payload.has_diabetes_family_history else 0.0,
            "FAMILY_HP":      1.0 if payload.has_hypertension_family_history else 0.0,
            "is_chronic":     1.0 if payload.is_chronic_patient else 0.0,
        }
        return np.array([raw.get(f, 0.0) for f in feature_names], dtype=np.float32).reshape(1, -1)

    # ── 스태킹 추론 ───────────────────────────────────────────────────────────

    def _infer_sex_key(self, payload: PredictionInput) -> str:
        return "female" if payload.gender == "female" else "male"

    def _predict_proba_stacking(
        self, payload: PredictionInput, sex: str
    ) -> dict[str, np.ndarray]:
        """Base 6종 → Meta 피처 구성 → Meta 3종 예측 확률 반환."""
        base_probs: dict[str, np.ndarray] = {}
        for target in BASE_TARGETS:
            bundle = self._base[sex].get(target)
            if bundle is None:
                n_cls = N_CLASSES[target]
                base_probs[target] = np.full((1, n_cls), 1.0 / n_cls)
                continue
            preproc = bundle["preprocessor"]
            sel_feats: list[str] = preproc["selected_features"]
            all_feats: list[str] = preproc["feature_names"]
            X_full = self._build_feature_row(payload, all_feats)
            feat_idx = [all_feats.index(f) for f in sel_feats if f in all_feats]
            base_probs[target] = bundle["model"].predict_proba(X_full[:, feat_idx])

        # Meta 피처 구성 (train_shap.py build_meta_features 와 동일 순서)
        meta_parts: list[np.ndarray] = []
        for target in BASE_TARGETS:
            n_cls = N_CLASSES[target]
            prob = base_probs[target]
            if n_cls == 2:  # noqa: PLR2004
                meta_parts.append(prob[:, 1:2])
            else:
                meta_parts.append(prob)
        meta_X = np.hstack(meta_parts)

        meta_probs: dict[str, np.ndarray] = {}
        for target in META_TARGETS:
            bundle = self._meta[sex].get(target)
            meta_probs[target] = (
                bundle["model"].predict_proba(meta_X) if bundle else np.array([[0.5, 0.5]])
            )
        return meta_probs

    # ── 공개 인터페이스 ───────────────────────────────────────────────────────

    def predict(self, payload: PredictionInput) -> PredictionOutput:
        """PredictionInput → PredictionOutput.

        fallback_on_error=True 이면 미로드·오류 시 룰 기반 결과를 반환한다.
        """
        if not self._loaded:
            if self._fallback_on_error:
                logger.warning("모델 미로드 — 룰 폴백")
                return self._fallback.calculate(payload)
            raise RuntimeError("MLRiskPredictor.load() 가 호출되지 않음")
        try:
            return self._predict(payload)
        except Exception:  # noqa: BLE001
            logger.exception("ML 추론 실패 — 룰 폴백")
            if self._fallback_on_error:
                return self._fallback.calculate(payload)
            raise

    def _predict(self, payload: PredictionInput) -> PredictionOutput:
        sex = self._infer_sex_key(payload)
        meta_probs = self._predict_proba_stacking(payload, sex)

        main_target = (
            "HE_HP" if payload.disease_type == DiseaseType.HYPERTENSION else "HE_DM_HbA1c"
        )
        prob_positive = float(meta_probs[main_target][0, 1])
        risk_score = Decimal(str(round(prob_positive * 100, 2)))
        risk_level = _risk_score_to_level(prob_positive)

        # 기여 인자: SHAP 중요도 상위 3개 피처
        factor_scores: list[tuple[str, float]] = []
        for target in BASE_TARGETS:
            if not self._base[sex].get(target):
                continue
            shap_imp: dict[str, float] = self._base[sex][target]["preprocessor"].get(
                "shap_importance", {}
            )
            top_feat = max(shap_imp, key=lambda k: shap_imp[k]) if shap_imp else target
            factor_scores.append((top_feat, shap_imp.get(top_feat, 0.0)))

        factor_scores.sort(key=lambda x: -x[1])
        contributing_factors = [
            RiskFactor(factor=f, weight=round(w, 4)) for f, w in factor_scores[:3]
        ]

        return PredictionOutput(
            disease_type=payload.disease_type,
            risk_score=risk_score,
            risk_level=risk_level,
            contributing_factors=contributing_factors,
            model_version=MODEL_VERSION,
        )
