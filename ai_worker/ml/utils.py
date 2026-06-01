"""ai_worker/ml — 공통 유틸리티 함수.

metrics 계산, SHAP 중요도 추출, 시각화 함수를 모아둔다.
train_shap.py 에서 import해서 사용한다.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
import shap
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from ai_worker.ml.config import SHAP_N_FEATURES


# ──────────────────────────────────────────────────────────────────────────────
# 지표 계산
# ──────────────────────────────────────────────────────────────────────────────

def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    target: str,
    is_multi: bool = False,
) -> dict:
    """AUC / Accuracy / F1 / Precision / Recall 계산."""
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
    n_cls = y_prob.shape[1]
    labels = list(range(n_cls))
    try:
        if is_multi:
            auc = roc_auc_score(
                y_true, y_prob, multi_class="ovr", average="macro", labels=labels
            )
        else:
            auc = roc_auc_score(y_true, y_prob[:, 1])
    except ValueError as e:
        print(f"    ⚠ AUC 계산 실패 ({e}) — 0으로 대체")
        auc = 0.0
    return {
        "target": target,
        "AUC": round(auc, 4),
        "Accuracy": round(acc, 4),
        "F1_macro": round(f1, 4),
        "Precision": round(prec, 4),
        "Recall": round(rec, 4),
    }


# ──────────────────────────────────────────────────────────────────────────────
# SHAP 중요도
# ──────────────────────────────────────────────────────────────────────────────

def get_shap_importance(
    model: LGBMClassifier,
    X: np.ndarray,
    is_multi: bool,
    n_cls: int,  # noqa: ARG001
) -> np.ndarray:
    """SHAP TreeExplainer 로 피처별 평균 |SHAP| 값을 계산한다.

    Returns
    -------
    np.ndarray
        shape (n_features,)
    """
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X)

    if is_multi:
        if isinstance(shap_vals, list):
            mean_abs = np.mean([np.abs(sv).mean(axis=0) for sv in shap_vals], axis=0)
        else:
            mean_abs = np.abs(shap_vals).mean(axis=(0, 2))
    else:
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        mean_abs = np.abs(shap_vals).mean(axis=0)

    return mean_abs


# ──────────────────────────────────────────────────────────────────────────────
# 시각화
# ──────────────────────────────────────────────────────────────────────────────

def plot_shap_bar(
    shap_importance: np.ndarray,
    feature_names: list[str],
    title: str,
    save_path: str,
    top_n: int = 30,
) -> None:
    """SHAP 절댓값 평균 막대 그래프 (선택된 피처는 빨강으로 표시)."""
    imp_df = (
        pd.DataFrame({"feature": feature_names, "shap_mean_abs": shap_importance})
        .sort_values("shap_mean_abs", ascending=False)
        .head(top_n)
    )
    fig, ax = plt.subplots(figsize=(8, max(4, min(top_n, len(imp_df)) * 0.32)))
    colors = [
        "#FF6B6B" if i < SHAP_N_FEATURES else "#AED6F1" for i in range(len(imp_df))
    ]
    ax.barh(
        imp_df["feature"][::-1],
        imp_df["shap_mean_abs"][::-1],
        color=colors[::-1],
        edgecolor="white",
        height=0.7,
    )
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title(title, fontsize=11)
    if len(imp_df) >= SHAP_N_FEATURES:
        ax.axhline(
            len(imp_df) - SHAP_N_FEATURES - 0.5,
            color="red", linestyle="--", lw=1.2, alpha=0.7,
            label=f"Top {SHAP_N_FEATURES} 경계",
        )
        ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_shap_beeswarm(
    explainer: shap.TreeExplainer,
    X_sel: np.ndarray,
    feature_names: list[str],
    title: str,
    save_path: str,
    is_multi: bool = False,
    n_cls: int = 2,  # noqa: ARG001
) -> None:
    """SHAP Beeswarm (Summary Plot)."""
    shap_vals = explainer.shap_values(X_sel)
    plt.figure(figsize=(9, max(5, len(feature_names) * 0.35)))
    if is_multi and isinstance(shap_vals, list):
        shap.summary_plot(
            shap_vals[0], X_sel, feature_names=feature_names, show=False, plot_size=None
        )
        plt.title(f"{title} [Class 0]", fontsize=11)
    else:
        sv = shap_vals[1] if isinstance(shap_vals, list) else shap_vals
        shap.summary_plot(sv, X_sel, feature_names=feature_names, show=False, plot_size=None)
        plt.title(title, fontsize=11)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_shap_dependence(
    explainer: shap.TreeExplainer,
    X_sel: np.ndarray,
    feature_names: list[str],
    top_feat: str,
    title: str,
    save_path: str,
    is_multi: bool = False,  # noqa: ARG001
) -> None:
    """SHAP Dependence Plot — 상위 1개 피처."""
    shap_vals = explainer.shap_values(X_sel)
    sv = (
        shap_vals[1]
        if isinstance(shap_vals, list)
        else (
            shap_vals[:, :, 0]
            if len(np.array(shap_vals).shape) == 3  # noqa: PLR2004
            else shap_vals
        )
    )
    feat_idx = list(feature_names).index(top_feat)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(
        X_sel[:, feat_idx], sv[:, feat_idx],
        c=sv[:, feat_idx], cmap="coolwarm",
        alpha=0.4, s=10, edgecolors="none",
    )
    ax.set_xlabel(top_feat)
    ax.set_ylabel("SHAP value")
    ax.set_title(title, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray, title: str, save_path: str
) -> None:
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(max(4, len(cm)), max(3, len(cm) - 1)))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax, linewidths=0.5, linecolor="gray")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title, fontsize=11, pad=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_roc_curves(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_classes: int,
    title: str,
    save_path: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    if n_classes == 2:  # noqa: PLR2004
        fpr, tpr, _ = roc_curve(y_true, y_prob[:, 1])
        auc_val = roc_auc_score(y_true, y_prob[:, 1])
        ax.plot(fpr, tpr, lw=2, label=f"AUC = {auc_val:.4f}")
    else:
        from sklearn.preprocessing import label_binarize
        classes = list(range(n_classes))
        y_bin = label_binarize(y_true, classes=classes)
        colors = plt.cm.tab10(np.linspace(0, 1, n_classes))
        for i, color in zip(classes, colors):
            try:
                fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
                auc_val = roc_auc_score(y_bin[:, i], y_prob[:, i])
                ax.plot(fpr, tpr, lw=1.5, color=color, label=f"Class {i}  AUC={auc_val:.3f}")
            except Exception:  # noqa: BLE001
                pass
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_feature_importance(
    importances: np.ndarray,
    feature_names: list[str],
    title: str,
    save_path: str,
    top_n: int = 20,
) -> None:
    imp_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(top_n)
    )
    fig, ax = plt.subplots(figsize=(8, max(4, min(top_n, len(imp_df)) * 0.35)))
    ax.barh(
        imp_df["feature"][::-1], imp_df["importance"][::-1],
        color="steelblue", edgecolor="white", height=0.7,
    )
    ax.set_xlabel("Feature Importance")
    ax.set_title(title, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_summary_bar(
    summary_df: pd.DataFrame,
    model_name: str,
    fig_dir: str,
    target_kor: dict[str, str],
    sexes: list[str],
) -> None:
    """Meta 모델 성능 막대그래프 + Base 모델 히트맵 저장."""
    meta_test = summary_df[
        (summary_df["model_type"] == "meta") & (summary_df["split"] == "test")
    ].copy()
    meta_test["label"] = meta_test.apply(
        lambda r: f"{target_kor.get(r['target'], r['target'])}\n({'남' if r['sex'] == 'male' else '여'})",
        axis=1,
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, metric in zip(axes, ["AUC", "Accuracy", "F1_macro"]):
        colors = ["#1e88e5" if s == "male" else "#e53935" for s in meta_test["sex"]]
        x_pos = np.arange(len(meta_test))
        bars = ax.bar(x_pos, meta_test[metric], color=colors, edgecolor="white", width=0.55)
        ax.set_ylim(max(0, meta_test[metric].min() - 0.08), 1.02)
        ax.set_title(f"Meta 모델 — {metric} (Test)", fontsize=11, pad=8)
        ax.set_ylabel(metric, fontsize=10)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(meta_test["label"], fontsize=9, rotation=0, ha="center")
        for bar, val in zip(bars, meta_test[metric]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.006,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold",
            )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    legend_patches = [
        mpatches.Patch(color="#1e88e5", label="남성"),
        mpatches.Patch(color="#e53935", label="여성"),
    ]
    fig.legend(handles=legend_patches, loc="upper right", fontsize=10, bbox_to_anchor=(1.0, 1.0))
    plt.suptitle(f"Meta 모델 성능 요약 ({model_name})", fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(f"{fig_dir}/shap_meta_performance_summary.png", dpi=130, bbox_inches="tight")
    plt.close()

    base_test = summary_df[
        (summary_df["model_type"] == "base") & (summary_df["split"] == "test")
    ].copy()
    base_targets = summary_df[summary_df["model_type"] == "base"]["target"].unique().tolist()
    for sex in sexes:
        sub = base_test[base_test["sex"] == sex].set_index("target")[
            ["AUC", "Accuracy", "F1_macro"]
        ]
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(sub, annot=True, fmt=".4f", cmap="YlGnBu", linewidths=0.5, ax=ax, vmin=0.5, vmax=1.0)
        ax.set_title(f"[{sex}] Base 모델 성능 히트맵 (Test) — SHAP", fontsize=11)
        plt.tight_layout()
        plt.savefig(f"{fig_dir}/shap_base_{sex}_heatmap.png", dpi=130, bbox_inches="tight")
        plt.close()
