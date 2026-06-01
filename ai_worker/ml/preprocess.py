"""KNHANES 9기 — ML 전처리 파이프라인.

원시 CSV(knhanes_modify_update_data.csv) → datasets/{male,female}/ CSV 생성.

사용법:
    python -m ai_worker.ml.preprocess --input knhanes_modify_update_data.csv
    python -m ai_worker.ml.preprocess \\
        --input ./data/knhanes_modify_update_data.csv \\
        --output ./ai_worker/ml/datasets
"""

from __future__ import annotations

import argparse
import os
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# 타겟 정의
# ──────────────────────────────────────────────────────────────────────────────
BASE_TARGETS = ["tg_cat", "hdl_cat", "chol_cat", "ldl_cat", "HE_HP", "HE_DM_HbA1c"]
BASE_TARGETS_BIN = ["tg_cat_bin", "hdl_cat_bin", "chol_cat_bin", "ldl_cat_bin", "HE_HP", "HE_DM_HbA1c"]
META_TARGETS = ["DI2_dg", "HE_HP", "HE_DM_HbA1c"]
ALL_TARGETS_FULL = list(set(BASE_TARGETS + BASE_TARGETS_BIN + META_TARGETS))


# ──────────────────────────────────────────────────────────────────────────────
# Step 1. 원시 데이터 로드 + 특수값 처리
# ──────────────────────────────────────────────────────────────────────────────

def load_raw(path: Path) -> pd.DataFrame:
    df_raw = pd.read_csv(path)
    print(f"[로드] {df_raw.shape[0]:,}행 × {df_raw.shape[1]}열")
    return df_raw


def apply_special_value_rules(df: pd.DataFrame) -> pd.DataFrame:
    """8/88/9/99 계열 특수값 → NaN 또는 유효값으로 변환."""
    df = df.copy()

    # G1: 8/88/888/8888, 9/99/999/9999 → NaN
    _G1 = [
        "HE_ht","HE_wt","HE_BMI","HE_wc",
        "HE_sbp","HE_dbp","HE_glu","HE_HbA1c",
        "HE_chol","HE_TG","HE_HDL_st2","HE_LDL_drct",
        "HE_obe","HE_DM_HbA1c","HE_HP","HE_anem",
        "DI2_dg","DI4_dg",
        "BS1_1","BS3_1","BS3_2","BS12_47","BS12_47_1","BS12_2",
        "BD1_11","BD2_1","BD2_31",
        "BE3_75","BE3_85","BE3_31","BE5_1",
        "BO1_1","BO1_2","BO1_3",
        "BP16_11","BP16_12","BP16_13","BP16_14",
        "BP16_21","BP16_22","BP16_23","BP16_24",
        "LW_pr","LW_oc","LW_wh","LW_wh_a","LW_wh_dur",
        "LW_wh_yy","LW_wh_mm","LW_ms","HE_prg",
    ]
    for c in _G1:
        if c in df.columns:
            df[c] = df[c].replace([8, 88, 888, 8888, 9, 99, 999, 9999], np.nan)

    # G2: 비해당→0, 무응답→NaN
    _G2 = {
        "HE_DMfh3":  ([8],  [9, 99]),
        "HE_HPfh3":  ([8],  [9, 99]),
        "HE_HLfh3":  ([8],  [9, 99]),
        "HE_IHDfh3": ([8],  [9, 99]),
        "BE3_76":    ([8],  [9, 99]),
        "BE3_77":    ([88], [99]),
        "BE3_78":    ([88], [99]),
        "BE3_86":    ([8],  [9, 99]),
        "BE3_87":    ([88], [99]),
        "BE3_88":    ([88], [99]),
    }
    for c, (zero_v, nan_v) in _G2.items():
        if c in df.columns:
            df[c] = df[c].replace(zero_v, 0).replace(nan_v, np.nan)

    # G3: 9/99 → NaN
    _G3 = ["HE_DMfh1","HE_DMfh2","HE_HPfh1","HE_HPfh2",
            "HE_HLfh1","HE_HLfh2","HE_IHDfh1","HE_IHDfh2",
            "L_OUT_FQ","L_BR_FQ"]
    for c in _G3:
        if c in df.columns:
            df[c] = df[c].replace([9, 99], np.nan)

    # G4: 99 → NaN (9='거의안먹음'은 유효값)
    for c in ["LS_FRUIT","LS_VEG1","LS_VEG2"]:
        if c in df.columns:
            df[c] = df[c].replace([99], np.nan)

    # 19세 이하 제외
    df = df[df["age"] >= 20].reset_index(drop=True)
    print(f"[특수값 처리 + 19세이하 제외] → {len(df):,}행")
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 2. 타겟 이진화
# ──────────────────────────────────────────────────────────────────────────────

def clean_targets(df: pd.DataFrame) -> pd.DataFrame:
    """타겟 변수 이진화 + NaN 행 삭제."""
    df = df.copy()
    df["HE_DM_HbA1c"] = df["HE_DM_HbA1c"].replace({1.0: 0, 2.0: 1, 3.0: 1})
    df["HE_HP"]        = df["HE_HP"].replace({1.0: 0, 2.0: 1, 3.0: 1, 4.0: 1})
    df["DI2_dg"]       = df["DI2_dg"].replace({0.0: 0, 1.0: 1, 8.0: np.nan, 9.0: np.nan})

    before = len(df)
    df = df.dropna(subset=["HE_DM_HbA1c","HE_HP","DI2_dg"]).reset_index(drop=True)
    print(f"[타겟 정제] {before:,} → {len(df):,}행")
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 3. 전처리 1 — 가족력·흡연·수면·운동
# ──────────────────────────────────────────────────────────────────────────────

def preprocess_lifestyle1(df: pd.DataFrame) -> pd.DataFrame:
    """가족력 통합, 흡연 통합, 수면시간, 운동시간 파생변수 생성."""
    df = df.copy()

    # 가족력 통합 (부/모/형제 → 1컬럼)
    for new_col, cols in {
        "FAMILY_DM":  ["HE_DMfh1","HE_DMfh2","HE_DMfh3"],
        "FAMILY_HP":  ["HE_HPfh1","HE_HPfh2","HE_HPfh3"],
        "FAMILY_IHD": ["HE_IHDfh1","HE_IHDfh2","HE_IHDfh3"],
        "FAMILY_HL":  ["HE_HLfh1","HE_HLfh2","HE_HLfh3"],
    }.items():
        exist = [c for c in cols if c in df.columns]
        if not exist:
            continue
        df[exist] = df[exist].replace({8: -1, 9: -1}).fillna(-1)
        def _fh(row):
            if (row == 1).any():     return 1.0
            elif (row == -1).all():  return -1.0
            else:                    return 0.0
        df[new_col] = df[exist].apply(_fh, axis=1)

    # 흡연 통합 → SMOKE_STATUS 문자열
    for col, rep in [("BS3_2",{888:np.nan,999:np.nan}),("BS12_47_1",{888:np.nan,999:np.nan})]:
        if col in df.columns:
            df[col] = df[col].replace(rep)
    _smoke_cnt = [c for c in ["BS3_2","BS12_47_1"] if c in df.columns]
    if _smoke_cnt:
        df["TOTAL_SMOKE_COUNT"] = df[_smoke_cnt].fillna(0).sum(axis=1)
    for col, rep, fill in [
        ("BS3_1",  {8:np.nan,9:np.nan}, -1),
        ("BS12_47",{8:np.nan,9:np.nan}, -1),
        ("BS12_2", {8:2,9:2},            2),
    ]:
        if col in df.columns:
            df[col] = df[col].replace(rep).fillna(fill).astype(int)
    _ss_cols = [c for c in ["BS3_1","BS12_47","BS12_2"] if c in df.columns]
    if len(_ss_cols) == 3:
        df["SMOKE_STATUS"] = (df["BS3_1"].astype(str) + "_" +
                               df["BS12_47"].astype(str) + "_" +
                               df["BS12_2"].astype(str))

    # 수면시간
    for new_col, (bh,bm,wh,wm) in [
        ("SLEEP_WEEKDAY", ("BP16_11","BP16_12","BP16_13","BP16_14")),
        ("SLEEP_WEEKEND", ("BP16_21","BP16_22","BP16_23","BP16_24")),
    ]:
        if all(c in df.columns for c in [bh,bm,wh,wm]):
            df[[bh,bm,wh,wm]] = df[[bh,bm,wh,wm]].replace([88,99], np.nan)
            bed  = df[bh] + df[bm].fillna(0) / 60.0
            wake = df[wh] + df[wm].fillna(0) / 60.0
            df[new_col] = np.where(wake < bed, (wake + 24) - bed, wake - bed)

    # 운동시간
    for new_col, (hc,mc) in [
        ("HIGH_EXERCISE_HOUR",    ("BE3_77","BE3_78")),
        ("MODERATE_EXERCISE_HOUR",("BE3_87","BE3_88")),
    ]:
        if hc in df.columns and mc in df.columns:
            df[[hc,mc]] = df[[hc,mc]].replace([88,99], np.nan)
            df[new_col] = (df[hc].fillna(0) + df[mc].fillna(0) / 60.0).round(2)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 4. 전처리 2 — 음주·체중변화·임신호르몬·식습관
# ──────────────────────────────────────────────────────────────────────────────

def preprocess_lifestyle2(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 음주
    for col, rep in [("BD1_11",{8.0:1.0,9.0:-1}),("BD2_1",{8.0:0.0,9.0:np.nan}),("BD2_31",{8.0:1.0,9.0:-1})]:
        if col in df.columns:
            df[col] = df[col].replace(rep)

    # 신체활동
    for col, rep in [
        ("BE3_75",{8.0:2.0,9.0:np.nan}),("BE3_85",{8.0:2.0,9.0:np.nan}),
        ("BE3_76",{8.0:0.0,9.0:np.nan}),("BE3_86",{8.0:0.0,9.0:np.nan}),
        ("BE3_31",{88.0:np.nan,99.0:np.nan}),("BE5_1",{8.0:1.0,9.0:np.nan}),
    ]:
        if col in df.columns:
            df[col] = df[col].replace(rep)

    # 체중 변화
    for col in ["BO1_1","BO1_2","BO1_3"]:
        if col in df.columns:
            df[col] = df[col].replace({8.0:0.0,9.0:np.nan})

    # 임신·폐경·호르몬
    if "LW_pr" in df.columns:
        df["LW_pr"] = df["LW_pr"].replace({8.0:2.0,9.0:np.nan})
        df.loc[(df["sex"]==1)&df["LW_pr"].isna(), "LW_pr"] = 2.0
    if "HE_prg" in df.columns:
        df["HE_prg"] = df["HE_prg"].replace({8:0})
    if "DI4_dg" in df.columns:
        df["DI4_dg"] = df["DI4_dg"].replace({8.0:0.0}).fillna(0.0)
    if "BS1_1" in df.columns:
        df["BS1_1"] = df["BS1_1"].replace({8.0:3.0,9.0:np.nan})
    if "LW_ms" in df.columns:
        def _meno(row):
            if row["sex"] == 1: return -1
            v = row["LW_ms"]
            return 0 if v in [1.0,2.0,3.0,4.0,8.0] else (1 if v in [5.0,6.0] else -1)
        df["is_menopause"] = df.apply(_meno, axis=1)
    else:
        df["is_menopause"] = -1

    for col in ["LW_oc","LW_wh"]:
        if col in df.columns:
            df[col] = df[col].replace({2.0:0.0,8.0:0.0,9.0:np.nan})
            df.loc[df["sex"]==1, col] = 0.0
    for col, rep in [("LW_wh_a",{888.0:np.nan,999.0:np.nan}),("LW_wh_dur",{8888.0:np.nan,9999.0:np.nan}),
                     ("LW_wh_yy",{88.0:np.nan,99.0:np.nan}),("LW_wh_mm",{88.0:np.nan,99.0:np.nan})]:
        if col in df.columns:
            df[col] = df[col].replace(rep)
    if "LW_wh" in df.columns:
        yy  = df["LW_wh_yy"].fillna(0) if "LW_wh_yy" in df.columns else pd.Series(0, index=df.index)
        mm  = df["LW_wh_mm"].fillna(0) if "LW_wh_mm" in df.columns else pd.Series(0, index=df.index)
        dur = df["LW_wh_dur"].fillna(0) if "LW_wh_dur" in df.columns else pd.Series(0, index=df.index)
        ym  = yy*12 + mm
        df["HORMONE_OCP_MONTHS"] = np.where(ym > 0, ym, dur).astype(float)
        df.loc[(df["LW_wh"]==0)|(df["sex"]==1), "HORMONE_OCP_MONTHS"] = 0.0
    else:
        df["HORMONE_OCP_MONTHS"] = 0.0

    if "N_WAT_C" in df.columns:
        df["N_WAT_C"] = pd.to_numeric(df["N_WAT_C"], errors="coerce").replace(0.0, np.nan)

    # 식습관 파생변수
    for col in ["LS_FRUIT","LS_VEG1","LS_VEG2","L_OUT_FQ","L_BR_FQ"]:
        if col in df.columns:
            df[col] = df[col].replace([99.0], np.nan)

    if "L_BR_FQ" in df.columns:
        df["INTERACTION_SEX_BR"] = ((df["sex"]==2)&(df["L_BR_FQ"].isin([1,2]))).astype(float)
        df["FEMALE_BR_LOW_RISK"] = ((df["sex"]==2)&(df["L_BR_FQ"]==4)).astype(float)
    if "L_OUT_FQ" in df.columns:
        df["INTERACTION_SEX_OUT"]  = ((df["sex"]==2)&(df["L_OUT_FQ"].isin([1,2,3,4,5]))).astype(float)
        df["FEMALE_OUT_HIGH_RISK"] = ((df["sex"]==2)&(df["L_OUT_FQ"].isin([1,2]))).astype(float)
        df["FEMALE_OUT_LOW_RISK"]  = ((df["sex"]==2)&(df["L_OUT_FQ"].isin([6,7]))).astype(float)
    if "LS_FRUIT" in df.columns:
        df["FRUIT_HIGH_INTAKE"]  = (df["LS_FRUIT"] <= 2.0).astype(float)
    if "LS_VEG1" in df.columns:
        df["SODIUM_RISK_GROUP"]   = (df["LS_VEG1"] <= 2.0).astype(float)
        df["INTERACTION_SEX_VEG1"] = ((df["sex"]==2)&(df["LS_VEG1"]<=2.0)).astype(float)
    if "LS_VEG2" in df.columns:
        df["HEALTHY_VEG_INTAKE"]   = (df["LS_VEG2"] <= 2.0).astype(float)
        df["INTERACTION_SEX_VEG2"] = ((df["sex"]==2)&(df["LS_VEG2"]<=2.0)).astype(float)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 5. 원본 컬럼 삭제 + BMI/HE_obe 재계산
# ──────────────────────────────────────────────────────────────────────────────

def drop_source_columns(df: pd.DataFrame) -> pd.DataFrame:
    _drop = [
        "HE_DMfh1","HE_DMfh2","HE_DMfh3","HE_HPfh1","HE_HPfh2","HE_HPfh3",
        "HE_IHDfh1","HE_IHDfh2","HE_IHDfh3","HE_HLfh1","HE_HLfh2","HE_HLfh3",
        "BS3_1","BS3_2","BS12_47","BS12_47_1","BS12_2",
        "BP16_11","BP16_12","BP16_13","BP16_14","BP16_21","BP16_22","BP16_23","BP16_24",
        "BE3_77","BE3_78","BE3_87","BE3_88",
        "LW_wh_a","LW_wh_dur","LW_wh_yy","LW_wh_mm","LW_ms",
    ]
    df = df.drop(columns=[c for c in _drop if c in df.columns])
    return df


def recalculate_bmi_obe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if all(c in df.columns for c in ["HE_BMI","HE_ht","HE_wt"]):
        mask = df["HE_BMI"].isna() & df["HE_ht"].notna() & df["HE_wt"].notna()
        df.loc[mask,"HE_BMI"] = (df.loc[mask,"HE_wt"] / (df.loc[mask,"HE_ht"]/100)**2).round(4)

    def _bmi_obe(b):
        if pd.isna(b):  return np.nan
        if b < 18.5:    return 1.0
        elif b < 23.0:  return 2.0
        elif b < 25.0:  return 3.0
        elif b < 30.0:  return 4.0
        elif b < 35.0:  return 5.0
        else:           return 6.0

    if "HE_BMI" in df.columns:
        if "HE_obe" not in df.columns:
            df["HE_obe"] = df["HE_BMI"].apply(_bmi_obe)
        else:
            mask = df["HE_obe"].isna() & df["HE_BMI"].notna()
            df.loc[mask,"HE_obe"] = df.loc[mask,"HE_BMI"].apply(_bmi_obe)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 6. 피처 엔지니어링
# ──────────────────────────────────────────────────────────────────────────────

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 신체계측
    if "HE_wc" in df.columns and "HE_ht" in df.columns:
        df["WHtR"]        = (df["HE_wc"] / df["HE_ht"]).round(4)
        df["WHtR_HIGH"]   = (df["WHtR"] >= 0.5).astype(float)
        df["ABD_OBESITY"] = (((df["sex"]==1)&(df["HE_wc"]>=90))|((df["sex"]==2)&(df["HE_wc"]>=85))).astype(float)
    if "HE_obe" in df.columns:
        df["ANTHRO_RISK_SCORE"] = (df["HE_obe"].fillna(0) +
                                    df.get("ABD_OBESITY", pd.Series(0,index=df.index))*2)

    # 수면 복합
    if "SLEEP_WEEKDAY" in df.columns and "SLEEP_WEEKEND" in df.columns:
        df["SLEEP_IMBALANCE"] = (df["SLEEP_WEEKDAY"]-df["SLEEP_WEEKEND"]).abs()
        df["SLEEP_AVG"]       = (df["SLEEP_WEEKDAY"]*5 + df["SLEEP_WEEKEND"]*2)/7.0
        df["SLEEP_QUALITY"]   = np.where(df["SLEEP_AVG"]<6, 1.0, np.where(df["SLEEP_AVG"]>=9, 2.0, 0.0))

    # 운동 복합
    if "HIGH_EXERCISE_HOUR" in df.columns and "MODERATE_EXERCISE_HOUR" in df.columns:
        df["TOTAL_EXERCISE_HOUR"] = df["HIGH_EXERCISE_HOUR"]*2 + df["MODERATE_EXERCISE_HOUR"]
        _be76 = df["BE3_76"].fillna(0) if "BE3_76" in df.columns else pd.Series(0,index=df.index)
        _be86 = df["BE3_86"].fillna(0) if "BE3_86" in df.columns else pd.Series(0,index=df.index)
        _wh = df["HIGH_EXERCISE_HOUR"]*60*_be76
        _wm = df["MODERATE_EXERCISE_HOUR"]*60*_be86
        df["WHO_PA_MET"] = ((_wh>=75)|(_wm>=150)).astype(float)

    # 흡연 지표
    if "SMOKE_STATUS" in df.columns:
        def _smoker(s):
            if pd.isna(s): return 0.0
            parts = str(s).split("_")
            if len(parts)<3: return 0.0
            try:
                r,h,l = int(parts[0]),int(parts[1]),int(parts[2])
                return 1.0 if (r in[1,2]) or (h in[1,2]) or (l==1) else 0.0
            except:
                return 0.0
        df["CURRENT_SMOKER"] = df["SMOKE_STATUS"].apply(_smoker)
    else:
        df["CURRENT_SMOKER"] = 0.0

    # 음주 지표
    if "BD1_11" in df.columns and "BD2_1" in df.columns:
        df["DRINK_RISK"]      = df["BD1_11"] * df["BD2_1"]
        df["HIGH_RISK_DRINK"] = ((df["BD1_11"]>=5)&(df["BD2_1"]>=3)).astype(float)

    # 연령 그룹 + 가족력 합산
    df["AGE_GROUP"] = pd.cut(df["age"], bins=[0,30,40,50,60,70,np.inf],
        labels=[0.0,1.0,2.0,3.0,4.0,5.0], right=False).astype(float)
    _fh_exist = [c for c in ["FAMILY_DM","FAMILY_HP","FAMILY_IHD","FAMILY_HL"] if c in df.columns]
    if _fh_exist:
        df["FAM_TOTAL"] = df[_fh_exist].replace({-1:0}).fillna(0).sum(axis=1)

    print(f"[피처 엔지니어링 완료] 컬럼 수: {len(df.columns)}")
    return df


def add_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """공복혈당 점수, 신체·연령 위험, 생활습관 위험, 혈당 부담 프록시, 지질 프록시."""
    df = df.copy()

    # 공복혈당 점수
    if "HE_glu" in df.columns:
        _fpg = df["HE_glu"]
        df["fpg_risk_continuous"]  = ((_fpg-90.0)/60.0).clip(0.0,1.0)
        df["fpg_range_score"]      = pd.Series(np.where(_fpg<100,0.0,np.where(_fpg<126,0.6,1.0)), index=df.index)
        df["fasting_glucose_score"] = (0.7*df["fpg_risk_continuous"] + 0.3*df["fpg_range_score"])
        _nan_fpg = _fpg.isna()
        df.loc[_nan_fpg,["fpg_risk_continuous","fpg_range_score","fasting_glucose_score"]] = np.nan
        df["HbA1c_glu_base"] = 2.77 + 0.0284*_fpg

    # 신체·연령 위험
    if "HE_BMI" in df.columns:
        df["BMI_risk"] = ((df["HE_BMI"]-23.0)/7.0).clip(0.0,1.0)
    if "WHtR" in df.columns:
        df["WHtR_risk"] = ((df["WHtR"]-0.45)/0.15).clip(0.0,1.0)
    df["age_risk"] = ((df["age"]-35.0)/40.0).clip(0.0,1.0)
    df["body_metabolic_score"] = (
        0.5*df.get("WHtR_risk", pd.Series(0,index=df.index)) +
        0.3*df.get("BMI_risk",  pd.Series(0,index=df.index)) +
        0.2*df["age_risk"]).clip(0.0,1.0)

    # 혈당 × 상호작용
    if "fasting_glucose_score" in df.columns:
        _fg = df["fasting_glucose_score"]
        if "WHtR_risk" in df.columns and "BMI_risk" in df.columns:
            df["glucose_adiposity_interaction"] = _fg*(0.6*df["WHtR_risk"]+0.4*df["BMI_risk"])
        if "age_risk" in df.columns:
            df["glucose_age_interaction"] = _fg * df["age_risk"]
        if "SODIUM_RISK_GROUP" in df.columns:
            df["glucose_sodium_interaction"] = _fg * df["SODIUM_RISK_GROUP"]

    # 수면 위험
    if "SLEEP_AVG" in df.columns:
        _sa = df["SLEEP_AVG"]
        df["sleep_risk"] = (0.7*(( 7.0-_sa)/3.0).clip(lower=0) +
                             0.3*((_sa-8.0)/4.0).clip(lower=0)).clip(0.0,1.0)

    # 운동 위험
    if "MODERATE_EXERCISE_HOUR" in df.columns:
        _be86 = df["BE3_86"].fillna(0) if "BE3_86" in df.columns else pd.Series(0,index=df.index)
        _mod_min = df["MODERATE_EXERCISE_HOUR"].fillna(0)*_be86*60.0
        df["moderate_exercise_min_per_week"] = _mod_min
        df["exercise_risk"] = 1.0 - (_mod_min/150.0).clip(0.0,1.0)
    else:
        df["exercise_risk"] = 0.5

    # 흡연 위험
    def _smk_r(row):
        if row.get("CURRENT_SMOKER",0)==1.0: return 1.0
        if pd.notna(row.get("BS1_1",np.nan)) and row.get("BS1_1")==2.0: return 0.5
        return 0.0
    df["smoking_risk"] = df.apply(_smk_r, axis=1)

    # 음주 위험
    if "HIGH_RISK_DRINK" in df.columns and "BD1_11" in df.columns:
        df["alcohol_risk"] = np.where(df["HIGH_RISK_DRINK"]==1.0, 1.0,
                             np.where(df["BD1_11"]>=5, 0.5, 0.0))
    else:
        df["alcohol_risk"] = 0.0

    # 가족력 점수
    if "FAMILY_DM" in df.columns:
        df["family_dm_score"] = (df["FAMILY_DM"]==1).astype(float)

    # 호르몬 점수
    _female = (df["sex"]==2).astype(float)
    if "HORMONE_OCP_MONTHS" in df.columns:
        _mc = df["HORMONE_OCP_MONTHS"].clip(upper=120).fillna(0)
        df["hormone_ocp_score"] = _female * np.log1p(_mc)/np.log1p(120)
    else:
        df["hormone_ocp_score"] = 0.0

    # 지질 숨은 위험 프록시
    _lp_w = {"WHtR_risk":0.35,"BMI_risk":0.25,"alcohol_risk":0.15,
              "exercise_risk":0.15,"hormone_ocp_score":0.10}
    df["lipid_hidden_risk_proxy"] = sum(
        df.get(c, pd.Series(0,index=df.index))*w for c,w in _lp_w.items())

    # 수분 위험
    if "N_WAT_C" in df.columns and "HE_wt" in df.columns:
        _wpk = df["N_WAT_C"] / df["HE_wt"].replace(0,np.nan)
        df["water_ml_per_kg"] = _wpk
        df["hydration_risk"]  = ((25.0-_wpk)/15.0).clip(0.0,1.0)

    # 혈당 부담 프록시 (GLYCEMIC_BURDEN_PROXY)
    _cw = {"fasting_glucose_score":0.38,"glucose_adiposity_interaction":0.10,
           "glucose_age_interaction":0.06,"glucose_sodium_interaction":0.05,
           "WHtR_risk":0.10,"BMI_risk":0.06,"age_risk":0.06,"body_metabolic_score":0.05,
           "family_dm_score":0.05,"exercise_risk":0.04,"sleep_risk":0.03,
           "smoking_risk":0.03,"alcohol_risk":0.02,"hormone_ocp_score":0.02,
           "lipid_hidden_risk_proxy":0.02,"hydration_risk":0.01}
    _cw_ok = {k:v for k,v in _cw.items() if k in df.columns}
    _ws = pd.Series(0.0, index=df.index)
    _tw = pd.Series(0.0, index=df.index)
    for col, w in _cw_ok.items():
        _v = df[col]; _mask = _v.notna()
        _ws = _ws + _v.fillna(0)*w
        _tw = _tw + _mask.astype(float)*w
    df["GLYCEMIC_BURDEN_PROXY"] = (_ws/_tw.replace(0,np.nan)).clip(0.0,1.0)

    # HbA1c 프록시
    if "HbA1c_glu_base" in df.columns:
        _gbp = df["GLYCEMIC_BURDEN_PROXY"]
        df["HbA1c_proxy_home"] = (0.65*df["HbA1c_glu_base"] + 0.35*(5.1+1.5*_gbp))
        if "HE_glu" in df.columns:
            _sl  = 5.1+1.5*_gbp
            _sw  = np.select([df["HE_glu"]<110, df["HE_glu"]<126, df["HE_glu"]>=126],
                              [0.35,0.25,0.05], default=0.35)
            _rv2 = (1-_sw)*df["HbA1c_glu_base"] + _sw*_sl
            _hinge = np.maximum(0, _rv2-5.4)
            _tail  = np.log1p(np.maximum(0, df["HE_glu"]-150)) / np.log1p(100)
            _adip  = 0.6*df.get("WHtR_risk",0) + 0.4*df.get("BMI_risk",0)
            df["HbA1c_proxy_home_v2"] = _rv2 + 0.20*_hinge + 0.10*_tail*_adip
            df["HbA1c_proxy_home_v2_high_sensitive"] = (
                df["HbA1c_proxy_home"] + 0.50*np.maximum(0, df["HbA1c_proxy_home"]-5.4))

    print(f"[위험점수 완료] 컬럼 수: {len(df.columns)}")
    return df


def add_lipid_proxies(df: pd.DataFrame) -> pd.DataFrame:
    """지질 프록시 파생변수 생성 (TG/HDL/TC/LDL/NonHDL)."""
    df = df.copy()

    _male   = (df["sex"]==1).astype(float)
    _female = (df["sex"]==2).astype(float)
    _meno_flag = ((df.get("is_menopause", pd.Series(-1,index=df.index)))==1).astype(float)

    def _age_grp(a):
        if a<30:   return "20s"
        elif a<40: return "30s"
        elif a<50: return "40s"
        elif a<60: return "50s"
        elif a<70: return "60s"
        else:      return "70+"
    _age_grp_s = df["age"].apply(_age_grp)

    _exercise_risk = df.get("exercise_risk", pd.Series(0.5,index=df.index)).fillna(0.5)
    _smoking_risk  = df.get("smoking_risk",  pd.Series(0.0,index=df.index)).fillna(0.0)
    _alcohol_risk  = df.get("alcohol_risk",  pd.Series(0.0,index=df.index)).fillna(0.0)
    _bmi_risk      = df.get("BMI_risk",      pd.Series(0.0,index=df.index)).fillna(0.0)
    _whtr_risk     = df.get("WHtR_risk",     pd.Series(0.0,index=df.index)).fillna(0.0)
    _age_risk      = df.get("age_risk",      pd.Series(0.0,index=df.index)).fillna(0.0)
    _fpg_score     = df.get("fasting_glucose_score", pd.Series(0.0,index=df.index)).fillna(0.0)
    _abd_ob        = df.get("ABD_OBESITY",   pd.Series(0.0,index=df.index)).fillna(0.0)
    _gbp           = df.get("GLYCEMIC_BURDEN_PROXY", pd.Series(0.0,index=df.index)).fillna(0.0)
    _ocp_score     = df.get("hormone_ocp_score", pd.Series(0.0,index=df.index)).fillna(0.0)

    # TG
    if "HE_TG" in df.columns:
        _tg_raw = df["HE_TG"]
        df["TG_base"] = df.groupby([df["sex"], _age_grp_s])["HE_TG"].transform("median")
        _bd1 = df["BD1_11"].fillna(0) if "BD1_11" in df.columns else pd.Series(0.0,index=df.index)
        _bd2 = df["BD2_1"].fillna(0)  if "BD2_1"  in df.columns else pd.Series(0.0,index=df.index)
        _drink_norm = (_bd1*_bd2/30.0).clip(0,1)
        df["TG_male_risk"]   = (_male*(0.35*_drink_norm+0.25*_abd_ob+0.20*_fpg_score+0.10*_bmi_risk+0.10*_age_risk)).clip(0,1)
        df["TG_female_risk"] = (_female*(0.30*_meno_flag+0.25*_bmi_risk+0.20*_fpg_score+0.15*_gbp+0.10*_ocp_score)).clip(0,1)
        df["TG_lifestyle_risk"] = (df["TG_male_risk"]+df["TG_female_risk"]).clip(0,1)
        _tg_value_risk = ((_tg_raw-100)/250).clip(0,1).where(_tg_raw.notna(), other=np.nan)
        df["TG_risk_score"] = (0.65*_tg_value_risk.fillna(_tg_value_risk.median())+0.35*df["TG_lifestyle_risk"]).clip(0,1)
        df["TG_proxy_mgdl"] = (df["TG_base"]*(1.0+0.6*df["TG_lifestyle_risk"])).clip(30,1000).round(1)

    # HDL
    if "HE_HDL_st2" in df.columns:
        _hdl_raw = df["HE_HDL_st2"]
        df["HDL_base"] = df.groupby([df["sex"], _age_grp_s])["HE_HDL_st2"].transform("median")
        df["HDL_male_risk"]   = (_male*(0.35*_smoking_risk+0.30*_abd_ob+0.20*_exercise_risk+0.15*_alcohol_risk)).clip(0,1)
        _prot = _female*(1-_meno_flag)*0.3
        df["HDL_female_risk"] = (_female*(0.40*_meno_flag+0.25*_bmi_risk+0.20*_exercise_risk+0.15*_gbp)-_prot).clip(0,1)
        df["HDL_decrease_risk"] = (df["HDL_male_risk"]+df["HDL_female_risk"]).clip(0,1)
        _hdl_thr = np.where(df["sex"]==1, 40.0, 50.0)
        _hdl_value_risk = pd.Series(((_hdl_thr-_hdl_raw)/30.0).clip(0,1), index=df.index).where(_hdl_raw.notna(), other=np.nan)
        df["HDL_risk_score"] = (0.65*_hdl_value_risk.fillna(_hdl_value_risk.median())+0.35*df["HDL_decrease_risk"]).clip(0,1)
        df["HDL_proxy_mgdl"] = (df["HDL_base"]*(1.0-0.25*df["HDL_decrease_risk"])).clip(20,120).round(1)

    # TC
    if "HE_chol" in df.columns:
        _tc_raw = df["HE_chol"]
        df["TC_base"] = df.groupby([df["sex"], _age_grp_s])["HE_chol"].transform("median")
        _fam_hl = (df["FAMILY_HL"]==1).astype(float) if "FAMILY_HL" in df.columns else pd.Series(0.0,index=df.index)
        df["TC_residual_risk"] = (0.25*_female*_meno_flag+0.20*_bmi_risk+0.15*_fam_hl+0.15*_smoking_risk+0.15*_age_risk+0.10*_ocp_score).clip(0,1)
        df["TC_proxy_mgdl"] = (df["TC_base"]*(1.0+0.35*df["TC_residual_risk"])).clip(100,400).round(1)
        _tc_value_risk = ((_tc_raw-200)/100).clip(0,1).where(_tc_raw.notna(), other=np.nan)
        df["TC_value_risk"]  = _tc_value_risk
        df["TC_risk_score"]  = (0.70*_tc_value_risk.fillna(_tc_value_risk.median())+0.30*df["TC_residual_risk"]).clip(0,1)

    # LDL
    if all(c in df.columns for c in ["HE_chol","HE_HDL_st2","HE_TG"]):
        _tc  = df["HE_chol"]; _hdl = df["HE_HDL_st2"]; _tg = df["HE_TG"]
        _ldl_fw = (_tc-_hdl-_tg/5.0).where(_tg<400, other=np.nan)
        df["LDL_friedewald"] = _ldl_fw
        if "HE_LDL_drct" in df.columns:
            df["LDL_proxy"] = np.where(df["HE_LDL_drct"].notna(), df["HE_LDL_drct"], _ldl_fw)
        else:
            df["LDL_proxy"] = _ldl_fw
        _ldl = df["LDL_proxy"]
        df["LDL_value_risk"]   = ((_ldl-100)/90).clip(0,1).where(_ldl.notna(), other=np.nan)
        df["LDL_context_risk"] = (df["LDL_value_risk"].fillna(df["LDL_value_risk"].median())*(0.5*_fpg_score+0.5*(_whtr_risk*0.6+_bmi_risk*0.4))).clip(0,1)
        df["LDL_risk_score"]   = (0.60*df["LDL_value_risk"].fillna(df["LDL_value_risk"].median())+0.25*df["LDL_context_risk"]+0.15*df.get("TC_risk_score",pd.Series(0.0,index=df.index))).clip(0,1)

    # NonHDL
    if all(c in df.columns for c in ["HE_chol","HE_HDL_st2"]):
        df["NonHDL_proxy_mgdl"] = (df["HE_chol"]-df["HE_HDL_st2"]).round(1)
        df["NonHDL_risk_score"] = ((df["NonHDL_proxy_mgdl"]-130)/130).clip(0,1)

    return df


def add_interaction_vars(df: pd.DataFrame) -> pd.DataFrame:
    """나이·생활습관 교호항 + metabolic_age + bmi_age_index."""
    df = df.copy()
    _age  = df["age"]
    _male = (df["sex"]==1).astype(float)
    _female = (df["sex"]==2).astype(float)

    df["age_norm"]        = (_age/100.0).clip(0,1).round(4)
    df["age_male_peak"]   = (_male*np.exp(-0.5*((_age-52.0)/12.0)**2)).round(4)
    df["age_female_late"] = (_female*(1.0/(1.0+np.exp(-((_age-52.0)/4.0))))).round(4)
    df["smoke_age_inter"] = (df["CURRENT_SMOKER"].fillna(0)*df["age_norm"]).round(4)
    df["alcohol_bmi_inter"] = (df["alcohol_risk"].fillna(0)*df["BMI_risk"].fillna(0)).round(4)
    _meno = df.get("is_menopause", pd.Series(-1,index=df.index)).fillna(-1).clip(lower=0)
    df["meno_age_inter"]  = (_meno*df["age_norm"]).round(4)

    _meta_age_offset = (
        df.get("fasting_glucose_score",0).fillna(0)*10.0 +
        df.get("BMI_risk",0).fillna(0)*5.0 +
        df.get("exercise_risk",0).fillna(0)*3.0 +
        df.get("sleep_risk",0).fillna(0)*2.0
    ).clip(0,20)
    df["metabolic_age"] = (_age + _meta_age_offset).round(2)

    _bmi_val = df["HE_BMI"] if "HE_BMI" in df.columns else (df.get("WHtR",pd.Series(0.5,index=df.index))*25.0).clip(15,45)
    df["bmi_age_index"] = (_bmi_val.fillna(_bmi_val.median())*df["age_norm"]).round(4)

    return df


def add_clinical_bins(df: pd.DataFrame) -> pd.DataFrame:
    """임상 기준 구간화 + 원본 연속형 삭제."""
    df = df.copy()

    # BMI 구간화
    if "HE_BMI" in df.columns:
        def _bmi_cat(v):
            if pd.isna(v): return np.nan
            if v<18.5: return 0.0
            elif v<23.0: return 1.0
            elif v<25.0: return 2.0
            elif v<30.0: return 3.0
            else: return 4.0
        df["bmi_cat"] = df["HE_BMI"].apply(_bmi_cat)

    # 허리둘레 구간화
    if "HE_wc" in df.columns:
        def _wc_cat(row):
            v,s = row["HE_wc"],row["sex"]
            if pd.isna(v): return np.nan
            return (0.0 if v<85 else (1.0 if v<90 else 2.0)) if s==1 else (0.0 if v<80 else (1.0 if v<85 else 2.0))
        df["wc_cat"] = df.apply(_wc_cat, axis=1)

    # 신장 구간화
    _ht_cut = {(1,"20대"):(170,178),(1,"30-40대"):(167,175),(1,"50대"):(164,172),(1,"60대"):(161,169),(1,"70세이상"):(158,166),
               (2,"20대"):(156,163),(2,"30-40대"):(155,162),(2,"50대"):(152,159),(2,"60대"):(149,156),(2,"70세이상"):(146,153)}
    def _age_to_grp(a):
        if a<30: return "20대"
        elif a<50: return "30-40대"
        elif a<60: return "50대"
        elif a<70: return "60대"
        else: return "70세이상"
    if "HE_ht" in df.columns:
        def _ht_cat(row):
            v=row["HE_ht"]
            if pd.isna(v): return np.nan
            lo,hi = _ht_cut.get((int(row["sex"]),_age_to_grp(row["age"])),(160,175))
            return 0.0 if v<lo else (1.0 if v<=hi else 2.0)
        df["ht_cat"] = df.apply(_ht_cat, axis=1)

    # 체중 구간화
    _wt_cut = {(1,"20대"):(62,80,95),(1,"30-40대"):(65,82,97),(1,"50대"):(63,80,95),(1,"60대"):(60,77,92),(1,"70세이상"):(57,73,87),
               (2,"20대"):(48,62,75),(2,"30-40대"):(50,65,78),(2,"50대"):(50,65,78),(2,"60대"):(50,64,77),(2,"70세이상"):(47,61,74)}
    if "HE_wt" in df.columns:
        def _wt_cat(row):
            v=row["HE_wt"]
            if pd.isna(v): return np.nan
            p25,p75,p90 = _wt_cut.get((int(row["sex"]),_age_to_grp(row["age"])),(55,75,90))
            return 0.0 if v<p25 else (1.0 if v<p75 else (2.0 if v<p90 else 3.0))
        df["wt_cat"] = df.apply(_wt_cat, axis=1)

    # 지질 4종 구간화
    if "HE_chol" in df.columns:
        df["chol_cat"] = pd.cut(df["HE_chol"],bins=[0,200,240,np.inf],labels=[0.0,1.0,2.0],right=False).astype(float)
    if "HE_TG" in df.columns:
        df["tg_cat"] = pd.cut(df["HE_TG"],bins=[0,150,200,500,np.inf],labels=[0.0,1.0,2.0,3.0],right=False).astype(float)
    if "HE_HDL_st2" in df.columns:
        def _hdl_cat(row):
            v,s = row["HE_HDL_st2"],row["sex"]
            if pd.isna(v): return np.nan
            lo,hi = (40,60) if s==1 else (50,60)
            return 0.0 if v<lo else (1.0 if v<hi else 2.0)
        df["hdl_cat"] = df.apply(_hdl_cat, axis=1)
    if "HE_LDL_drct" in df.columns:
        df["ldl_cat"] = pd.cut(df["HE_LDL_drct"],bins=[0,100,130,160,190,np.inf],labels=[0.0,1.0,2.0,3.0,4.0],right=False).astype(float)

    # 혈압 구간화
    if "HE_sbp" in df.columns and "HE_dbp" in df.columns:
        def _bp_cat(row):
            s,d = row["HE_sbp"],row["HE_dbp"]
            if pd.isna(s) or pd.isna(d): return np.nan
            if s>=160 or d>=100: return 4.0
            if s>=140 or d>=90:  return 3.0
            if s>=130 or d>=80:  return 2.0
            if s>=120 and d<80:  return 1.0
            return 0.0
        df["bp_cat"] = df.apply(_bp_cat, axis=1)

    # 원본 연속형 삭제
    _del_orig = [c for c in ["HE_BMI","HE_wc","HE_ht","HE_wt","HE_chol","HE_TG","HE_HDL_st2","HE_LDL_drct","HE_sbp","HE_dbp"] if c in df.columns]
    df = df.drop(columns=_del_orig)
    print(f"[임상 구간화 완료] 원본 연속형 {len(_del_orig)}개 삭제 → 컬럼 수: {len(df.columns)}")
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 7. 데이터 분할 (6:2:2, 성별 분리)
# ──────────────────────────────────────────────────────────────────────────────

def split_data(df: pd.DataFrame) -> dict:
    """Base/Meta 타겟 이진화 + 성별 분리 + 6:2:2 층화 분할."""
    # 이진화 버전 생성
    _binarize = {
        "tg_cat_bin":   (df["tg_cat"],   lambda x: (x>=1).astype(float)),
        "hdl_cat_bin":  (df["hdl_cat"],  lambda x: (x==0).astype(float)),
        "chol_cat_bin": (df["chol_cat"], lambda x: (x>=1).astype(float)),
        "ldl_cat_bin":  (df["ldl_cat"],  lambda x: (x>=2).astype(float)),
    }
    for col, (src, fn) in _binarize.items():
        if src is not None:
            df[col] = fn(src.fillna(-1)).where(src.notna(), other=np.nan)

    # meta 타겟 NaN 행 제거
    df = df.dropna(subset=["DI2_dg","HE_HP","HE_DM_HbA1c"]).reset_index(drop=True)
    print(f"[분할 전] {len(df):,}행")

    splits: dict = {}
    for sex_label, sex_val in [("male", 1), ("female", 2)]:
        df_sex = df[df["sex"]==sex_val].copy()
        _excl = ["ID"] + ALL_TARGETS_FULL
        X_sex = df_sex.drop(columns=[c for c in _excl if c in df_sex.columns])
        Y_base_sex     = df_sex[BASE_TARGETS].copy()
        Y_base_bin_sex = df_sex[BASE_TARGETS_BIN].copy()
        Y_meta_sex     = df_sex[META_TARGETS].copy()

        _strat = (Y_meta_sex["DI2_dg"].astype(str)+"_"+
                  Y_meta_sex["HE_HP"].astype(str)+"_"+
                  Y_meta_sex["HE_DM_HbA1c"].astype(str))
        _vc = _strat.value_counts()
        _strat = _strat.where(~_strat.isin(_vc[_vc<2].index), other="rare")

        idx_all = df_sex.index
        idx_train, idx_valtest = train_test_split(idx_all, test_size=0.4, random_state=42, stratify=_strat.loc[idx_all])
        _strat2 = _strat.loc[idx_valtest]
        _strat2 = _strat2.where(~_strat2.isin(_strat2.value_counts()[_strat2.value_counts()<2].index), other="rare")
        idx_val, idx_test = train_test_split(idx_valtest, test_size=0.5, random_state=42, stratify=_strat2)

        splits[sex_label] = {
            "X_train": X_sex.loc[idx_train], "X_val": X_sex.loc[idx_val], "X_test": X_sex.loc[idx_test],
            "Y_base_train": Y_base_sex.loc[idx_train], "Y_base_val": Y_base_sex.loc[idx_val], "Y_base_test": Y_base_sex.loc[idx_test],
            "Y_base_bin_train": Y_base_bin_sex.loc[idx_train], "Y_base_bin_val": Y_base_bin_sex.loc[idx_val], "Y_base_bin_test": Y_base_bin_sex.loc[idx_test],
            "Y_meta_train": Y_meta_sex.loc[idx_train], "Y_meta_val": Y_meta_sex.loc[idx_val], "Y_meta_test": Y_meta_sex.loc[idx_test],
            "train_idx": idx_train, "val_idx": idx_val, "test_idx": idx_test,
        }
        n_tr, n_va, n_te = len(idx_train), len(idx_val), len(idx_test)
        print(f"  [{sex_label}] Train {n_tr:,} / Val {n_va:,} / Test {n_te:,}  X: {X_sex.shape[1]}개 피처")

    return splits


# ──────────────────────────────────────────────────────────────────────────────
# Step 8. KDE 백분위 + 교호항 (분할 후)
# ──────────────────────────────────────────────────────────────────────────────

def _kde_cond_pct_train(x_train, y_train, x_all, y_all, silverman_factor=0.9, chunk=600):
    x_tr = np.asarray(x_train, dtype=np.float64); y_tr = np.asarray(y_train, dtype=np.float64)
    x_al = np.asarray(x_all, dtype=np.float64);   y_al = np.asarray(y_all, dtype=np.float64)
    n_tr = len(x_tr)
    x_std = np.std(x_tr); x_std = max(x_std, 1e-9)
    h = silverman_factor * x_std * (n_tr**-0.2)
    n_all = len(x_al); pcts = np.zeros(n_all, dtype=np.float64)
    for s in range(0, n_all, chunk):
        e = min(s+chunk, n_all)
        dx = (x_al[s:e,None]-x_tr[None,:])/h
        w  = np.exp(-0.5*dx**2); w /= w.sum(axis=1, keepdims=True)
        leq = (y_tr[None,:]<=y_al[s:e,None]).astype(np.float32)
        pcts[s:e] = (w*leq).sum(axis=1)
    return pcts


def add_post_split_features(splits: dict) -> dict:
    """분할 후 KDE 백분위 + 교호항 추가."""
    import time
    _t0 = time.time()
    print("KDE 백분위 재계산 (Train 기반)...")

    KDE_TARGETS = {
        "whtr_kde_pct_v2":   ("age","WHtR"),
        "tg_proxy_kde_pct":  ("age","TG_proxy_mgdl"),
        "hdl_proxy_kde_pct": ("age","HDL_proxy_mgdl"),
        "tc_proxy_kde_pct":  ("age","TC_proxy_mgdl"),
        "ldl_proxy_kde_pct": ("age","LDL_proxy"),
        "gbp_kde_pct":       ("age","GLYCEMIC_BURDEN_PROXY"),
        "meta_age_kde_pct":  ("age","metabolic_age"),
        "wt_bmi_idx_pct":    ("age","bmi_age_index"),
    }
    for sex_label in ["male","female"]:
        sp = splits[sex_label]
        for new_col, (x_col, y_col) in KDE_TARGETS.items():
            X_all_sex = pd.concat([sp["X_train"],sp["X_val"],sp["X_test"]])
            if x_col not in X_all_sex.columns or y_col not in X_all_sex.columns:
                continue
            x_tr = sp["X_train"][x_col].dropna(); y_tr = sp["X_train"][y_col].dropna()
            valid_tr = x_tr.index.intersection(y_tr.index)
            x_tr = x_tr.loc[valid_tr].values; y_tr = y_tr.loc[valid_tr].values
            if len(x_tr) < 20:
                continue
            x_all_v = X_all_sex[x_col]; y_all_v = X_all_sex[y_col]
            valid_all = x_all_v.notna() & y_all_v.notna(); valid_idx = X_all_sex.index[valid_all]
            pct_vals = _kde_cond_pct_train(x_tr, y_tr, x_all_v.loc[valid_idx].values, y_all_v.loc[valid_idx].values)
            pct_series = pd.Series(np.nan, index=X_all_sex.index, name=new_col)
            pct_series.loc[valid_idx] = pct_vals.round(4)
            for split_name, idx_key in [("X_train","X_train"),("X_val","X_val"),("X_test","X_test")]:
                sp[split_name][new_col] = pct_series.loc[sp[split_name].index]

    # 교호항
    def _add_interaction(splits, col_a, col_b, new_col, normalize=True):
        for sex_label in ["male","female"]:
            sp = splits[sex_label]
            if any(c not in sp["X_train"].columns for c in [col_a,col_b]):
                continue
            for split_name in ["X_train","X_val","X_test"]:
                sp[split_name][new_col] = sp[split_name][col_a].fillna(0)*sp[split_name][col_b].fillna(0)
            if normalize:
                _min = sp["X_train"][new_col].min(); _max = sp["X_train"][new_col].max()
                _range = _max-_min
                if _range > 1e-9:
                    for split_name in ["X_train","X_val","X_test"]:
                        sp[split_name][new_col] = ((sp[split_name][new_col]-_min)/_range).round(4)

    _interactions = [
        ("age_norm","TG_risk_score","age_tg_risk_inter",True),
        ("age_norm","HDL_risk_score","age_hdl_risk_inter",True),
        ("age_norm","TC_risk_score","age_tc_risk_inter",True),
        ("age_norm","WHtR_risk","age_whtr_inter",True),
        ("age_male_peak","TG_risk_score","male_peak_tg",True),
        ("age_female_late","HDL_risk_score","female_late_hdl",True),
        ("smoke_age_inter","TG_risk_score","smoke_age_tg",True),
        ("alcohol_bmi_inter","TG_risk_score","alc_bmi_tg",True),
        ("meno_age_inter","TC_risk_score","meno_age_tc",True),
        ("tg_proxy_kde_pct","hdl_proxy_kde_pct","tg_hdl_pct_dual",False),
        ("meta_age_kde_pct","TG_risk_score","meta_age_tg_inter",True),
    ]
    for col_a, col_b, new_col, norm in _interactions:
        _add_interaction(splits, col_a, col_b, new_col, normalize=norm)

    print(f"KDE + 교호항 완료 ({time.time()-_t0:.1f}s)")
    return splits


# ──────────────────────────────────────────────────────────────────────────────
# Step 9. 결측치 처리 + OHE
# ──────────────────────────────────────────────────────────────────────────────

def impute_and_encode(splits: dict) -> tuple[dict, object]:
    """결측치 대체 (train 기준) + SMOKE_STATUS OHE."""
    _CAT_COLS = [
        "pa_aerobic","HE_obe","HE_anem","BD1_11","BD2_31","BS1_1",
        "BE3_75","BE3_85","BO1_1","BO1_2","BO1_3","LW_pr","LW_oc","LW_wh","DX_Q_st",
        "INTERACTION_SEX_BR","FEMALE_BR_LOW_RISK","INTERACTION_SEX_OUT",
        "FEMALE_OUT_HIGH_RISK","FEMALE_OUT_LOW_RISK","FRUIT_HIGH_INTAKE",
        "SODIUM_RISK_GROUP","INTERACTION_SEX_VEG1","HEALTHY_VEG_INTAKE","INTERACTION_SEX_VEG2",
        "bmi_cat","wc_cat","ht_cat","wt_cat","chol_cat","tg_cat","hdl_cat","ldl_cat","bp_cat",
        "WHtR_HIGH","ABD_OBESITY","SLEEP_QUALITY","WHO_PA_MET","HIGH_RISK_DRINK","HE_prg","TH_HIGH_RISK",
    ]
    _POST_SPLIT_COLS = [
        "whtr_kde_pct_v2","tg_proxy_kde_pct","hdl_proxy_kde_pct","tc_proxy_kde_pct",
        "ldl_proxy_kde_pct","gbp_kde_pct","meta_age_kde_pct","wt_bmi_idx_pct",
        "age_tg_risk_inter","age_hdl_risk_inter","age_tc_risk_inter","age_whtr_inter",
        "male_peak_tg","female_late_hdl","smoke_age_tg","alc_bmi_tg","meno_age_tc",
        "tg_hdl_pct_dual","meta_age_tg_inter",
    ]

    for sex_label in ["male","female"]:
        sp = splits[sex_label]
        X_tr, X_va, X_te = sp["X_train"], sp["X_val"], sp["X_test"]
        _splits3 = [X_tr, X_va, X_te]

        # 범주형 최빈값
        for col in [c for c in _CAT_COLS if c in X_tr.columns]:
            _mode = X_tr[col].mode()
            if len(_mode)==0: continue
            for ds in _splits3: ds[col] = ds[col].fillna(_mode[0])

        # 수치형 중앙값
        for col in [c for c in X_tr.columns if c not in _CAT_COLS and col not in _POST_SPLIT_COLS]:
            if X_tr[col].isna().any():
                _med = X_tr[col].median()
                for ds in _splits3: ds[col] = ds[col].fillna(_med)

        # 분할 후 생성 변수 → 0
        for col in [c for c in _POST_SPLIT_COLS if c in X_tr.columns]:
            for ds in _splits3: ds[col] = ds[col].fillna(0.0)

        # N_WAT_C 극단값 클리핑
        if "N_WAT_C" in X_tr.columns:
            _upper = X_tr["N_WAT_C"].quantile(0.99)
            for ds in _splits3: ds["N_WAT_C"] = ds["N_WAT_C"].clip(upper=_upper)

        print(f"  [{sex_label}] 결측치 처리 완료  X_train shape: {X_tr.shape}")

    # SMOKE_STATUS OHE
    _col = "SMOKE_STATUS"
    encoder_smoke = None
    _has_smoke = any(_col in splits[sx]["X_train"].columns for sx in ["male","female"])
    if _has_smoke:
        _all_train = pd.concat([splits["male"]["X_train"][[_col]], splits["female"]["X_train"][[_col]]])
        _enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        _enc.fit(_all_train)
        _cnames = _enc.get_feature_names_out([_col])
        encoder_smoke = _enc
        for sex_label in ["male","female"]:
            sp = splits[sex_label]
            for split_name in ["X_train","X_val","X_test"]:
                ds = sp[split_name]
                if _col not in ds.columns: continue
                _ohe_df = pd.DataFrame(_enc.transform(ds[[_col]]), columns=_cnames, index=ds.index)
                sp[split_name] = pd.concat([ds.drop(columns=[_col]), _ohe_df], axis=1)

    return splits, encoder_smoke


# ──────────────────────────────────────────────────────────────────────────────
# Step 10. 저장
# ──────────────────────────────────────────────────────────────────────────────

def save_datasets(splits: dict, df_ml: pd.DataFrame, encoder_smoke: object, save_dir: Path) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    for sub in ["male","female"]:
        (save_dir/sub).mkdir(exist_ok=True)

    for sex_label in ["male","female"]:
        sp = splits[sex_label]
        base_path = save_dir / sex_label
        for fname, df_save in {
            "X_train": sp["X_train"], "X_val": sp["X_val"], "X_test": sp["X_test"],
            "Y_base_train": sp["Y_base_train"], "Y_base_val": sp["Y_base_val"], "Y_base_test": sp["Y_base_test"],
            "Y_meta_train": sp["Y_meta_train"], "Y_meta_val": sp["Y_meta_val"], "Y_meta_test": sp["Y_meta_test"],
        }.items():
            path = base_path / f"{fname}.csv"
            df_save.to_csv(path)
            print(f"  저장: {path}  {df_save.shape}")

    if encoder_smoke is not None:
        with open(save_dir/"encoder_smoke.pkl","wb") as fh:
            pickle.dump(encoder_smoke, fh)

    _meta = {
        "male":   {"train_idx":splits["male"]["train_idx"].tolist(),"val_idx":splits["male"]["val_idx"].tolist(),"test_idx":splits["male"]["test_idx"].tolist(),"feature_cols":list(splits["male"]["X_train"].columns)},
        "female": {"train_idx":splits["female"]["train_idx"].tolist(),"val_idx":splits["female"]["val_idx"].tolist(),"test_idx":splits["female"]["test_idx"].tolist(),"feature_cols":list(splits["female"]["X_train"].columns)},
        "base_targets": BASE_TARGETS, "meta_targets": META_TARGETS, "saved_at": datetime.now().isoformat(),
    }
    with open(save_dir/"splits_metadata.pkl","wb") as fh:
        pickle.dump(_meta, fh)

    with open(save_dir/"splits_info.txt","w",encoding="utf-8") as fh:
        fh.write(f"KNHANES ML 데이터셋 분할 요약\n저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for sx in ["male","female"]:
            sp = splits[sx]
            fh.write(f"[{sx.upper()}]\n  Train: {len(sp['X_train']):,}  Val: {len(sp['X_val']):,}  Test: {len(sp['X_test']):,}\n  피처 수: {sp['X_train'].shape[1]}\n\n")
        fh.write("[피처 목록 (남성 기준)]\n")
        for c in splits["male"]["X_train"].columns:
            fh.write(f"  {c}\n")

    print(f"\n✅ 저장 완료: {save_dir}")


# ──────────────────────────────────────────────────────────────────────────────
# 엔트리포인트
# ──────────────────────────────────────────────────────────────────────────────

def run(input_path: Path, output_dir: Path) -> None:
    print(f"\n{'='*60}\nKNHANES 전처리 파이프라인 시작\n{'='*60}")

    df_raw = load_raw(input_path)
    df     = apply_special_value_rules(df_raw)
    df_ml  = clean_targets(df)
    df_ml  = preprocess_lifestyle1(df_ml)
    df_ml  = preprocess_lifestyle2(df_ml)
    df_ml  = drop_source_columns(df_ml)
    df_ml  = recalculate_bmi_obe(df_ml)
    df_ml  = feature_engineering(df_ml)
    df_ml  = add_risk_scores(df_ml)
    df_ml  = add_lipid_proxies(df_ml)
    df_ml  = add_interaction_vars(df_ml)
    df_ml  = add_clinical_bins(df_ml)

    splits = split_data(df_ml)
    splits = add_post_split_features(splits)
    splits, encoder_smoke = impute_and_encode(splits)

    save_datasets(splits, df_ml, encoder_smoke, output_dir)

    print(f"\n{'='*60}\n전처리 완료\n"
          f"  남성: X_train {splits['male']['X_train'].shape}\n"
          f"  여성: X_train {splits['female']['X_train'].shape}\n{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="KNHANES 전처리 파이프라인")
    parser.add_argument("--input", type=Path, required=True, help="원시 CSV 경로 (knhanes_modify_update_data.csv)")
    parser.add_argument("--output", type=Path, default=Path("ai_worker/ml/datasets"), help="출력 디렉토리 (기본값: ai_worker/ml/datasets)")
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == "__main__":
    main()
