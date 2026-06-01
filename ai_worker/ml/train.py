"""KNHANES 9기 — 2단계 스태킹 앙상블 학습 파이프라인 (SHAP 기반 피처 선택).

구조:
    [Base 6종 × 성별 2] → OOF 예측 → [Meta 3종 × 성별 2] → 최종 예측

차원 축소:
    SHAP 기반 피처 선택 (상위 SHAP_N_FEATURES개)

출력:
    models/shap_base_{sex}_{target}.pkl  (12개)
    models/shap_meta_{sex}_{target}.pkl  (6개)
    models/performance_summary.csv
    figures/*.png

사용법:
    python -m ai_worker.ml.train
    python -m ai_worker.ml.train --data-dir ./datasets --model-dir ./models --fig-dir ./figures
"""

from __future__ import annotations

import argparse
import pickle
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.model_selection import StratifiedKFold

from ai_worker.ml.config import (
    BASE_TARGETS,
    BIN_TARGETS,
    LGBM_PARAMS,
    META_TARGETS,
    MODEL_NAME,
    MULTI_TARGETS,
    N_CLASSES,
    N_FOLDS,
    RAND_SEED,
    SEXES,
    SHAP_N_FEATURES,
    SHAP_PRETRAIN_PARAMS,
    TARGET_KOR,
)
from ai_worker.ml.utils import (
    compute_metrics,
    get_shap_importance,
    plot_confusion_matrix,
    plot_feature_importance,
    plot_roc_curves,
    plot_shap_bar,
    plot_shap_beeswarm,
    plot_shap_dependence,
    plot_summary_bar,
)

warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────────────────────────────────────
# 1. 데이터 로드
# ──────────────────────────────────────────────────────────────────────────────

def load_data(data_dir: Path) -> dict:
    """datasets/{male,female}/ 의 CSV 파일을 모두 로드한다."""
    data: dict = {}
    print("=" * 70)
    print("데이터 로드")
    print("=" * 70)
    for sex in SEXES:
        d = data_dir / sex
        data[sex] = {
            "X_train":      pd.read_csv(d / "X_train.csv",      index_col=0),
            "X_val":        pd.read_csv(d / "X_val.csv",        index_col=0),
            "X_test":       pd.read_csv(d / "X_test.csv",       index_col=0),
            "Y_base_train": pd.read_csv(d / "Y_base_train.csv", index_col=0),
            "Y_base_val":   pd.read_csv(d / "Y_base_val.csv",   index_col=0),
            "Y_base_test":  pd.read_csv(d / "Y_base_test.csv",  index_col=0),
            "Y_meta_train": pd.read_csv(d / "Y_meta_train.csv", index_col=0),
            "Y_meta_val":   pd.read_csv(d / "Y_meta_val.csv",   index_col=0),
            "Y_meta_test":  pd.read_csv(d / "Y_meta_test.csv",  index_col=0),
        }
        print(
            f"  [{sex}] X_train: {data[sex]['X_train'].shape}  "
            f"X_val: {data[sex]['X_val'].shape}  "
            f"X_test: {data[sex]['X_test'].shape}"
        )
    return data


# ──────────────────────────────────────────────────────────────────────────────
# 2. Base 모델 학습
# ──────────────────────────────────────────────────────────────────────────────

def train_base_models(
    data: dict,
    model_dir: Path,
    fig_dir: Path,
) -> tuple[dict, dict, dict, dict, dict, dict, list]:
    """SHAP 피처 선택 → OOF 학습 → Base 모델 저장.

    Returns
    -------
    (base_models, base_preprocessors, base_selected_feats,
     oof_predictions, val_predictions, test_predictions, all_metrics)
    """
    print("\n" + "=" * 70)
    print(f"Base 모델 학습 (LightGBM + SHAP 피처 선택 Top {SHAP_N_FEATURES})")
    print("=" * 70)

    base_models: dict = {}
    base_preprocessors: dict = {}
    base_selected_feats: dict = {}
    shap_importance_store: dict = {}
    oof_predictions: dict = {}
    val_predictions: dict = {}
    test_predictions: dict = {}
    all_metrics: list = []

    kf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RAND_SEED)

    for sex in SEXES:
        base_models[sex] = {}
        base_preprocessors[sex] = {}
        base_selected_feats[sex] = {}
        shap_importance_store[sex] = {}
        oof_predictions[sex] = {}
        val_predictions[sex] = {}
        test_predictions[sex] = {}

        X_tr = data[sex]["X_train"].copy()
        X_vl = data[sex]["X_val"].copy()
        X_te = data[sex]["X_test"].copy()
        Y_tr = data[sex]["Y_base_train"]
        Y_vl = data[sex]["Y_base_val"]
        Y_te = data[sex]["Y_base_test"]
        n_tr = len(X_tr)
        feat_names = X_tr.columns.tolist()

        print(f"\n{'─' * 60}")
        print(f"  성별: {sex.upper()}  (train={n_tr}, val={len(X_vl)}, test={len(X_te)})")
        print(f"{'─' * 60}")

        for target in BASE_TARGETS:
            t0 = time.time()
            is_multi = target in MULTI_TARGETS
            n_cls = N_CLASSES[target]
            y_tr = Y_tr[target].values.astype(int)
            y_vl = Y_vl[target].values.astype(int)
            y_te = Y_te[target].values.astype(int)

            print(f"\n  ▶ [{sex}] {target}  ({'다중' if is_multi else '이진'}분류, {n_cls}클래스)")

            # Step 1: SHAP 사전 학습
            print("    SHAP 사전 학습 중...")
            pretrain_model = LGBMClassifier(**SHAP_PRETRAIN_PARAMS)
            pretrain_model.fit(X_tr.values, y_tr)

            # Step 2: SHAP 중요도 계산 → 상위 N개 선택
            print("    SHAP 값 계산 중...")
            shap_imp = get_shap_importance(pretrain_model, X_tr.values, is_multi, n_cls)
            shap_importance_store[sex][target] = dict(zip(feat_names, shap_imp))

            top_idx = np.argsort(shap_imp)[::-1][:SHAP_N_FEATURES]
            sel_feats = [feat_names[i] for i in sorted(top_idx)]
            base_selected_feats[sex][target] = sel_feats

            ranked = sorted(zip(feat_names, shap_imp), key=lambda x: -x[1])
            print(f"    SHAP 피처 선택: {len(feat_names)}개 → {len(sel_feats)}개")
            print("    선택된 피처 (SHAP 중요도 순):")
            for rank_i, (f, v) in enumerate(ranked[:SHAP_N_FEATURES], 1):
                print(f"      {rank_i:2d}. {f:<45s}  SHAP={v:.5f}")

            X_tr_sel = X_tr[sel_feats].values
            X_vl_sel = X_vl[sel_feats].values
            X_te_sel = X_te[sel_feats].values

            base_preprocessors[sex][target] = {
                "pretrain_model":    pretrain_model,
                "shap_importance":   dict(zip(feat_names, shap_imp)),
                "selected_features": sel_feats,
                "feature_names":     feat_names,
            }

            # Step 3: SHAP 시각화
            fig_pref = str(fig_dir / f"shap_base_{sex}_{target}")
            plot_shap_bar(
                shap_imp, feat_names,
                f"[{sex}] {target} — SHAP 중요도 (Top30, 빨강=선택됨)",
                fig_pref + "_shap_bar.png", top_n=30,
            )
            explainer_sel = shap.TreeExplainer(pretrain_model)
            try:
                plot_shap_beeswarm(
                    explainer_sel, X_tr[sel_feats].values, sel_feats,
                    f"[{sex}] {target} — SHAP Beeswarm (선택 {SHAP_N_FEATURES}개)",
                    fig_pref + "_shap_beeswarm.png", is_multi=is_multi, n_cls=n_cls,
                )
            except Exception as e:  # noqa: BLE001
                print(f"    ⚠ Beeswarm 생략: {e}")
            top_feat = ranked[0][0]
            if top_feat in sel_feats:
                try:
                    plot_shap_dependence(
                        explainer_sel, X_tr[sel_feats].values, sel_feats, top_feat,
                        f"[{sex}] {target} — SHAP Dependence ({top_feat})",
                        fig_pref + "_shap_dep.png", is_multi=is_multi,
                    )
                except Exception as e:  # noqa: BLE001
                    print(f"    ⚠ Dependence Plot 생략: {e}")

            # Step 4: OOF 학습
            oof_prob = np.zeros((n_tr, n_cls))
            fold_aucs = []
            for fold, (tr_idx, val_idx) in enumerate(kf.split(X_tr_sel, y_tr)):  # noqa: B007
                model_f = LGBMClassifier(**LGBM_PARAMS)
                model_f.fit(
                    X_tr_sel[tr_idx], y_tr[tr_idx],
                    eval_set=[(X_tr_sel[val_idx], y_tr[val_idx])],
                    callbacks=[
                        lgb.early_stopping(50, verbose=False),
                        lgb.log_evaluation(-1),
                    ],
                )
                oof_prob[val_idx] = model_f.predict_proba(X_tr_sel[val_idx])
                try:
                    from sklearn.metrics import roc_auc_score as _auc_fn
                    if is_multi:
                        _auc = _auc_fn(
                            y_tr[val_idx], oof_prob[val_idx],
                            multi_class="ovr", average="macro",
                            labels=list(range(n_cls)),
                        )
                    else:
                        _auc = _auc_fn(y_tr[val_idx], oof_prob[val_idx][:, 1])
                    fold_aucs.append(_auc)
                except Exception:  # noqa: BLE001
                    pass

            print(
                f"    OOF AUC — 평균: {np.mean(fold_aucs):.4f}  "
                f"std: {np.std(fold_aucs):.4f}  "
                f"[{', '.join(f'{v:.3f}' for v in fold_aucs)}]"
            )

            # Step 5: 최종 모델 (전체 train)
            final_model = LGBMClassifier(**LGBM_PARAMS)
            final_model.fit(X_tr_sel, y_tr)

            val_prob  = final_model.predict_proba(X_vl_sel)
            test_prob = final_model.predict_proba(X_te_sel)
            val_pred  = final_model.predict(X_vl_sel)
            test_pred = final_model.predict(X_te_sel)

            oof_predictions[sex][target]  = oof_prob
            val_predictions[sex][target]  = val_prob
            test_predictions[sex][target] = test_prob
            base_models[sex][target]      = final_model

            # Step 6: 지표
            val_m  = compute_metrics(y_vl, val_pred, val_prob, f"{sex}_{target}_val",  is_multi)
            test_m = compute_metrics(y_te, test_pred, test_prob, f"{sex}_{target}_test", is_multi)
            val_m.update({"sex": sex, "model_type": "base", "split": "val",  "model_name": MODEL_NAME})
            test_m.update({"sex": sex, "model_type": "base", "split": "test", "model_name": MODEL_NAME})
            all_metrics.extend([val_m, test_m])

            print(
                f"    Val  — AUC: {val_m['AUC']:.4f}  Acc: {val_m['Accuracy']:.4f}  F1: {val_m['F1_macro']:.4f}\n"
                f"    Test — AUC: {test_m['AUC']:.4f}  Acc: {test_m['Accuracy']:.4f}  F1: {test_m['F1_macro']:.4f}"
            )

            # Step 7: 추가 시각화
            plot_feature_importance(
                final_model.feature_importances_, sel_feats,
                f"[{sex}] {target} — 변수 중요도 (SHAP 선택 {SHAP_N_FEATURES}개)",
                fig_pref + "_lgbm_importance.png",
            )
            plot_roc_curves(y_te, test_prob, n_cls,
                f"[{sex}] {target} — ROC (Test)", fig_pref + "_roc.png")
            plot_confusion_matrix(y_te, test_pred,
                f"[{sex}] {target} — Confusion Matrix (Test)", fig_pref + "_cm.png")

            # Step 8: 저장
            save_path = model_dir / f"shap_base_{sex}_{target}.pkl"
            with open(save_path, "wb") as fh:
                pickle.dump({
                    "model":        final_model,
                    "preprocessor": base_preprocessors[sex][target],
                    "oof_prob":     oof_prob,
                    "metrics_val":  val_m,
                    "metrics_test": test_m,
                }, fh)
            print(f"    완료 ({time.time() - t0:.1f}s)  저장: {save_path.name}")

    # SHAP 피처 종합 요약
    _print_shap_summary(data, base_selected_feats, shap_importance_store, fig_dir)

    return (
        base_models, base_preprocessors, base_selected_feats,
        oof_predictions, val_predictions, test_predictions, all_metrics,
    )


def _print_shap_summary(
    data: dict,
    base_selected_feats: dict,
    shap_importance_store: dict,
    fig_dir: Path,
) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    print("\n" + "=" * 70 + "\nSHAP 피처 선택 종합 요약\n" + "=" * 70)
    rows = []
    for sex in SEXES:
        for target in BASE_TARGETS:
            sel = base_selected_feats[sex][target]
            s_imp = shap_importance_store[sex][target]
            rows.append({
                "sex": sex, "target": target,
                "n_original": len(data[sex]["X_train"].columns),
                "n_selected": len(sel),
                "top1_feature": sorted(s_imp, key=lambda k: -s_imp[k])[0],
            })
    print(pd.DataFrame(rows).to_string(index=False))

    for sex in SEXES:
        all_feats = sorted({f for tgt in BASE_TARGETS for f in base_selected_feats[sex][tgt]})
        hmap = pd.DataFrame(0, index=all_feats, columns=BASE_TARGETS, dtype=float)
        for target in BASE_TARGETS:
            s_imp = shap_importance_store[sex][target]
            sel = set(base_selected_feats[sex][target])
            for f in all_feats:
                hmap.loc[f, target] = s_imp.get(f, 0) if f in sel else 0
        hmap = hmap.loc[hmap.sum(axis=1).sort_values(ascending=False).index]
        fig, ax = plt.subplots(figsize=(len(BASE_TARGETS) * 1.5, max(8, len(all_feats) * 0.32)))
        sns.heatmap(hmap, annot=True, fmt=".4f", cmap="YlOrRd",
                    linewidths=0.3, linecolor="lightgray", ax=ax,
                    cbar_kws={"label": "Mean |SHAP|"})
        ax.set_title(f"[{sex}] 타겟별 SHAP 선택 피처 중요도 히트맵", fontsize=12, pad=10)
        ax.set_xticklabels(BASE_TARGETS, rotation=20, ha="right", fontsize=9)
        ax.set_yticklabels(ax.get_yticklabels(), fontsize=7)
        plt.tight_layout()
        plt.savefig(str(fig_dir / f"shap_{sex}_selection_heatmap.png"), dpi=120, bbox_inches="tight")
        plt.close()


# ──────────────────────────────────────────────────────────────────────────────
# 3. Meta 피처 구성
# ──────────────────────────────────────────────────────────────────────────────

def build_meta_features(
    data: dict,
    oof_predictions: dict,
    val_predictions: dict,
    test_predictions: dict,
) -> dict:
    """Base 모델 OOF/Val/Test 확률을 연결해 Meta 입력 피처를 구성한다."""
    print("\n" + "=" * 70 + "\nMeta 피처 구성 (OOF 예측 확률 연결)\n" + "=" * 70)

    meta_X: dict = {}
    for sex in SEXES:
        tr_parts, vl_parts, te_parts, col_names = [], [], [], []
        for target in BASE_TARGETS:
            n_cls = N_CLASSES[target]
            oof_p = oof_predictions[sex][target]
            vl_p  = val_predictions[sex][target]
            te_p  = test_predictions[sex][target]
            if n_cls == 2:  # noqa: PLR2004
                tr_parts.append(oof_p[:, 1:2])
                vl_parts.append(vl_p[:, 1:2])
                te_parts.append(te_p[:, 1:2])
                col_names.append(f"prob_{target}_1")
            else:
                tr_parts.append(oof_p)
                vl_parts.append(vl_p)
                te_parts.append(te_p)
                for c in range(n_cls):
                    col_names.append(f"prob_{target}_{c}")

        meta_X[sex] = {
            "train": pd.DataFrame(np.hstack(tr_parts), index=data[sex]["X_train"].index, columns=col_names),
            "val":   pd.DataFrame(np.hstack(vl_parts), index=data[sex]["X_val"].index,   columns=col_names),
            "test":  pd.DataFrame(np.hstack(te_parts), index=data[sex]["X_test"].index,  columns=col_names),
        }
        print(
            f"  [{sex}] Meta X — train: {meta_X[sex]['train'].shape}  "
            f"val: {meta_X[sex]['val'].shape}  test: {meta_X[sex]['test'].shape}"
        )
    return meta_X


# ──────────────────────────────────────────────────────────────────────────────
# 4. Meta 모델 학습
# ──────────────────────────────────────────────────────────────────────────────

def train_meta_models(
    data: dict,
    meta_X: dict,
    model_dir: Path,
    fig_dir: Path,
    all_metrics: list,
) -> dict:
    """Meta 모델 학습 및 저장."""
    print("\n" + "=" * 70 + "\nMeta 모델 학습\n" + "=" * 70)

    meta_models: dict = {}
    for sex in SEXES:
        meta_models[sex] = {}
        mX_tr  = meta_X[sex]["train"].values
        mX_vl  = meta_X[sex]["val"].values
        mX_te  = meta_X[sex]["test"].values
        Y_m_tr = data[sex]["Y_meta_train"]
        Y_m_vl = data[sex]["Y_meta_val"]
        Y_m_te = data[sex]["Y_meta_test"]

        print(f"\n{'─' * 60}\n  성별: {sex.upper()}\n{'─' * 60}")

        for target in META_TARGETS:
            t0   = time.time()
            y_tr = Y_m_tr[target].values.astype(int)
            y_vl = Y_m_vl[target].values.astype(int)
            y_te = Y_m_te[target].values.astype(int)

            print(f"\n  ▶ [{sex}] Meta — {target}")

            meta_model = LGBMClassifier(**LGBM_PARAMS)
            meta_model.fit(mX_tr, y_tr)

            vl_prob = meta_model.predict_proba(mX_vl)
            te_prob = meta_model.predict_proba(mX_te)
            vl_pred = meta_model.predict(mX_vl)
            te_pred = meta_model.predict(mX_te)
            meta_models[sex][target] = meta_model

            val_m  = compute_metrics(y_vl, vl_pred, vl_prob, f"{sex}_meta_{target}_val",  False)
            test_m = compute_metrics(y_te, te_pred, te_prob, f"{sex}_meta_{target}_test", False)
            val_m.update({"sex": sex, "model_type": "meta", "split": "val",  "model_name": MODEL_NAME})
            test_m.update({"sex": sex, "model_type": "meta", "split": "test", "model_name": MODEL_NAME})
            all_metrics.extend([val_m, test_m])

            print(
                f"    Val  — AUC: {val_m['AUC']:.4f}  Acc: {val_m['Accuracy']:.4f}  F1: {val_m['F1_macro']:.4f}\n"
                f"    Test — AUC: {test_m['AUC']:.4f}  Acc: {test_m['Accuracy']:.4f}  F1: {test_m['F1_macro']:.4f}"
            )

            fig_pref = str(fig_dir / f"shap_meta_{sex}_{target}")
            plot_roc_curves(y_te, te_prob, 2,
                f"[{sex}] Meta {target} — ROC (Test)", fig_pref + "_roc.png")
            plot_confusion_matrix(y_te, te_pred,
                f"[{sex}] Meta {target} — Confusion Matrix (Test)", fig_pref + "_cm.png")
            plot_feature_importance(
                meta_model.feature_importances_,
                meta_X[sex]["train"].columns.tolist(),
                f"[{sex}] Meta {target} — 피처 중요도",
                fig_pref + "_importance.png",
                top_n=len(meta_X[sex]["train"].columns),
            )
            try:
                import matplotlib.pyplot as plt
                meta_exp  = shap.TreeExplainer(meta_model)
                meta_shap = meta_exp.shap_values(mX_te)
                sv = meta_shap[1] if isinstance(meta_shap, list) else meta_shap
                plt.figure(figsize=(8, 4))
                shap.summary_plot(sv, mX_te,
                    feature_names=meta_X[sex]["train"].columns.tolist(),
                    show=False, plot_size=None)
                plt.title(f"[{sex}] Meta {target} — SHAP (Test)", fontsize=11)
                plt.tight_layout()
                plt.savefig(fig_pref + "_shap_beeswarm.png", dpi=120, bbox_inches="tight")
                plt.close()
            except Exception as e:  # noqa: BLE001
                print(f"    ⚠ Meta SHAP 생략: {e}")

            save_path = model_dir / f"shap_meta_{sex}_{target}.pkl"
            with open(save_path, "wb") as fh:
                pickle.dump({
                    "model":             meta_model,
                    "meta_feature_cols": meta_X[sex]["train"].columns.tolist(),
                    "metrics_val":       val_m,
                    "metrics_test":      test_m,
                }, fh)
            print(f"    완료 ({time.time() - t0:.1f}s)  저장: {save_path.name}")

    return meta_models


# ──────────────────────────────────────────────────────────────────────────────
# 5. 성능 요약 저장 및 시각화
# ──────────────────────────────────────────────────────────────────────────────

def save_and_visualize_summary(all_metrics: list, model_dir: Path, fig_dir: Path) -> None:
    print("\n" + "=" * 70 + "\n성능 요약 테이블\n" + "=" * 70)

    summary_df = (
        pd.DataFrame(all_metrics)
        [["model_name", "model_type", "sex", "target", "split",
          "AUC", "Accuracy", "F1_macro", "Precision", "Recall"]]
        .sort_values(["model_type", "sex", "target", "split"])
        .reset_index(drop=True)
    )
    print(summary_df.to_string(index=False))

    summary_path = model_dir / "performance_summary.csv"
    if summary_path.exists():
        existing = pd.read_csv(summary_path)
        existing = existing[existing["model_name"] != MODEL_NAME]
        combined = pd.concat([existing, summary_df], ignore_index=True)
        combined.to_csv(summary_path, index=False)
        print(f"\n기존 요약에 추가 저장: {summary_path}  (총 {len(combined)}행)")
    else:
        summary_df.to_csv(summary_path, index=False)
        print(f"\n성능 요약 저장: {summary_path}  ({len(summary_df)}행)")

    plot_summary_bar(summary_df, MODEL_NAME, str(fig_dir), TARGET_KOR, SEXES)

    # 모델 간 비교 (2개 이상 모델 있을 때)
    if summary_path.exists():
        import matplotlib.pyplot as plt
        all_perf = pd.read_csv(summary_path)
        model_names = all_perf["model_name"].unique()
        if len(model_names) >= 2:  # noqa: PLR2004
            compare = all_perf[
                (all_perf["model_type"] == "meta") & (all_perf["split"] == "test")
            ].copy()
            compare["label"] = compare["sex"] + " | " + compare["target"]
            for metric in ["AUC", "F1_macro"]:
                pivot = compare.pivot_table(index="label", columns="model_name", values=metric)
                fig, ax = plt.subplots(
                    figsize=(max(8, len(pivot) * 1.2), max(4, len(model_names) * 1.5))
                )
                pivot.plot(kind="bar", ax=ax, edgecolor="white", width=0.7)
                ax.set_title(f"모델 비교 — Meta {metric} (Test)", fontsize=12)
                ax.set_ylabel(metric); ax.set_xlabel("")
                ax.set_xticklabels(ax.get_xticklabels(), rotation=25, ha="right")
                ax.legend(title="모델", fontsize=9)
                ax.set_ylim(max(0, compare[metric].min() - 0.05), 1.02)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                plt.savefig(str(fig_dir / f"model_comparison_{metric}.png"), dpi=130, bbox_inches="tight")
                plt.close()


# ──────────────────────────────────────────────────────────────────────────────
# 엔트리포인트
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="KNHANES SHAP 기반 스태킹 앙상블 학습")
    parser.add_argument("--data-dir",  type=Path, default=Path("./datasets"))
    parser.add_argument("--model-dir", type=Path, default=Path("./models"))
    parser.add_argument("--fig-dir",   type=Path, default=Path("./figures"))
    args = parser.parse_args()

    args.model_dir.mkdir(parents=True, exist_ok=True)
    args.fig_dir.mkdir(parents=True, exist_ok=True)

    data = load_data(args.data_dir)

    (base_models, base_preprocessors, base_selected_feats,
     oof_predictions, val_predictions, test_predictions, all_metrics) = \
        train_base_models(data, args.model_dir, args.fig_dir)

    meta_X = build_meta_features(data, oof_predictions, val_predictions, test_predictions)

    train_meta_models(data, meta_X, args.model_dir, args.fig_dir, all_metrics)

    save_and_visualize_summary(all_metrics, args.model_dir, args.fig_dir)

    print(f"\n전체 파이프라인 완료 (SHAP 피처 선택)\n"
          f"  모델 저장: {args.model_dir}\n"
          f"  성능 요약: {args.model_dir / 'performance_summary.csv'}\n"
          f"  그래프  : {args.fig_dir}")


if __name__ == "__main__":
    main()
