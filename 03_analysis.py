"""
03_analysis.py
==============
Statistical analysis pipeline: Panel regression, survival analysis,
and Hansen threshold regression.

Input : data/panel/merged_panel.csv, data/cleaned/combined_panel.csv
Output: results/ directory with model summaries (printed to stdout)

Requirements:
    pip install pandas numpy scipy linearmodels lifelines

Usage:
    python 03_analysis.py \
        --panel_path data/panel/merged_panel.csv \
        --case_path  data/cleaned/combined_panel.csv
"""

import argparse
import re
import warnings

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
from numpy.linalg import lstsq
from scipy import stats

warnings.filterwarnings("ignore")

ADMIN_PERIODS = ["1_Pro-Labor_Expansion", "2_Employer-Favorable", "3_Labor_Restoration", "4_Cemex_Era"]


# ============================================================
# A. Panel Fixed-Effects Regression
# ============================================================
def run_panel_regressions(panel: pd.DataFrame) -> None:
    """Run three specifications of FE panel regression."""
    df = panel.dropna(subset=["ca_count_lag1", "earn_yoy"]).copy()
    df["quarter_idx"] = pd.Categorical(df["quarter"]).codes
    df = df.set_index(["state", "quarter_idx"])

    # Admin period + seasonal dummies
    df["is_trump"] = (df["admin_period"] == "2_Employer-Favorable").astype(int)
    df["is_biden_precemex"] = (df["admin_period"] == "3_Labor_Restoration").astype(int)
    df["is_postcemex"] = (df["admin_period"] == "4_Cemex_Era").astype(int)
    for q in [1, 2, 3]:
        df[f"Q{q}"] = (df["qtr_num"] == q).astype(int)

    seasonal = ["Q1", "Q2", "Q3"]
    regime = ["is_trump", "is_biden_precemex", "is_postcemex"]

    # --- Model 1: CA lags only ---
    print("=" * 70)
    print("MODEL 1: FE — CA Lag → RC Count")
    print("=" * 70)
    df_m1 = df.dropna(subset=["ca_count_lag1", "ca_count_lag2", "ca_count_lag4"])
    exog = df_m1[["ca_count_lag1", "ca_count_lag2", "ca_count_lag4"] + regime + seasonal].copy()
    exog.insert(0, "const", 1)
    mod1 = PanelOLS(df_m1["rc_count"], exog, entity_effects=True)
    res1 = mod1.fit(cov_type="clustered", cluster_entity=True)
    print(res1.summary.tables[1])

    # --- Model 5: Full model (CA + QWI + Theme lags) ---
    print("\n" + "=" * 70)
    print("MODEL 5: FE — Full Model (CA + QWI + Themes → RC)")
    print("=" * 70)
    for col in ["n_coercive_rules", "n_discrimination"]:
        df[f"{col}_lag1"] = df.groupby(level="state")[col].shift(1)
    df["earn_yoy_lag1"] = df.groupby(level="state")["earn_yoy"].shift(1)
    df["turnover_lag1"] = df.groupby(level="state")["turnover_all"].shift(1)

    theme_vars = ["n_retaliation_lag1", "n_coercive_rules_lag1", "n_discrimination_lag1"]
    qwi_vars = ["earn_yoy_lag1", "turnover_lag1"]
    all_vars = ["ca_count_lag1"] + qwi_vars + theme_vars + regime + seasonal

    df_m5 = df.dropna(subset=all_vars).copy()
    exog5 = df_m5[all_vars].copy()
    exog5.insert(0, "const", 1)
    mod5 = PanelOLS(df_m5["rc_count"], exog5, entity_effects=True)
    res5 = mod5.fit(cov_type="clustered", cluster_entity=True)
    print(res5.summary.tables[1])

    # --- Model 6: QWI → CA ---
    print("\n" + "=" * 70)
    print("MODEL 6: FE — Labor Market → CA (ULP)")
    print("=" * 70)
    df_m6 = df.dropna(subset=["earn_yoy_lag1", "turnover_lag1"]).copy()
    exog6 = df_m6[["earn_yoy_lag1", "turnover_lag1"] + regime + seasonal].copy()
    exog6.insert(0, "const", 1)
    mod6 = PanelOLS(df_m6["ca_count"], exog6, entity_effects=True)
    res6 = mod6.fit(cov_type="clustered", cluster_entity=True)
    print(res6.summary.tables[1])

    # --- Summary ---
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)
    print(f"  Model 1 (CA lags):       Within-R² = {res1.rsquared_within:.4f}")
    print(f"  Model 5 (Full):          Within-R² = {res5.rsquared_within:.4f}")
    print(f"  Model 6 (QWI → CA):      Within-R² = {res6.rsquared_within:.4f}")


# ============================================================
# B. Survival Analysis
# ============================================================
def run_survival_analysis(cases: pd.DataFrame) -> None:
    """Kaplan-Meier + Cox PH for CA → RC transition."""
    print("\n\n" + "=" * 70)
    print("SURVIVAL ANALYSIS: CA → RC Transition")
    print("=" * 70)

    cases["employer_key"] = (
        cases["Case Name"].str.strip().str.upper() + "|" + cases["state"].str.strip()
    )

    ca = cases[cases["case_subtype"] == "CA"].sort_values("Date Filed")
    rc = cases[cases["case_subtype"] == "RC"].sort_values("Date Filed")

    # First CA and first RC per employer
    first_ca = ca.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed", "admin_period", "Allegations", "Employees on charge/petition"]
    ].rename(columns={
        "Date Filed": "ca_date", "admin_period": "ca_period",
        "Allegations": "ca_allegations", "Employees on charge/petition": "ca_employees",
    })

    first_rc = rc.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed", "Reason Closed"]
    ].rename(columns={"Date Filed": "rc_date", "Reason Closed": "rc_outcome"})

    surv = first_ca.merge(first_rc, on="employer_key", how="left")
    surv["event"] = surv["rc_date"].notna().astype(int)
    surv["rc_date"] = surv["rc_date"].fillna(pd.Timestamp("2024-12-31"))
    surv["duration"] = (surv["rc_date"] - surv["ca_date"]).dt.days
    surv = surv[(surv["duration"] > 0) & (surv["ca_date"] >= "2015-01-01")]
    surv["duration_capped"] = surv["duration"].clip(upper=1095)
    surv.loc[surv["duration"] > 1095, "event"] = 0

    print(f"\nDataset: {len(surv):,} employers, {surv['event'].sum():,} events ({surv['event'].mean()*100:.1f}%)")

    # Kaplan-Meier
    print(f"\n--- Kaplan-Meier by Admin Period ---")
    kmf = KaplanMeierFitter()
    for period in ADMIN_PERIODS:
        sub = surv[surv["ca_period"] == period]
        kmf.fit(sub["duration_capped"], sub["event"], label=period)
        s90, s365 = kmf.predict(90), kmf.predict(365)
        print(f"  {period:25s}: n={len(sub):>5,} | S(90d)={s90:.3f} | S(365d)={s365:.3f}")

    # Log-rank tests
    print(f"\n--- Log-Rank Tests ---")
    for i in range(len(ADMIN_PERIODS)):
        for j in range(i + 1, len(ADMIN_PERIODS)):
            g1 = surv[surv["ca_period"] == ADMIN_PERIODS[i]]
            g2 = surv[surv["ca_period"] == ADMIN_PERIODS[j]]
            result = logrank_test(
                g1["duration_capped"], g2["duration_capped"], g1["event"], g2["event"]
            )
            sig = "***" if result.p_value < 0.001 else "**" if result.p_value < 0.01 else "*" if result.p_value < 0.05 else "n.s."
            print(f"  {ADMIN_PERIODS[i]:25s} vs {ADMIN_PERIODS[j]:25s}: p={result.p_value:.4f} {sig}")

    # Cox PH
    print(f"\n--- Cox Proportional Hazards ---")

    def has_pattern(text, pattern):
        return int(bool(re.search(pattern, str(text), re.IGNORECASE))) if pd.notna(text) else 0

    surv["is_retaliation"] = surv["ca_allegations"].apply(
        lambda x: has_pattern(x, r"Retaliation|Discharge|Discipline")
    )
    surv["is_coercive_rules"] = surv["ca_allegations"].apply(
        lambda x: has_pattern(x, r"Coercive Rules")
    )
    surv["is_bargaining"] = surv["ca_allegations"].apply(
        lambda x: has_pattern(x, r"8\(a\)\(5\)")
    )
    surv["is_discrimination"] = surv["ca_allegations"].apply(
        lambda x: has_pattern(x, r"8\(a\)\(3\)")
    )
    surv["is_surveillance"] = surv["ca_allegations"].apply(
        lambda x: has_pattern(x, r"Surveillance")
    )
    surv["n_allegations"] = surv["ca_allegations"].str.count("\n").fillna(0) + 1
    surv["ln_employees"] = np.log1p(surv["ca_employees"].fillna(0))
    surv["is_trump"] = (surv["ca_period"] == "2_Employer-Favorable").astype(int)
    surv["is_biden_precemex"] = (surv["ca_period"] == "3_Labor_Restoration").astype(int)
    surv["is_postcemex"] = (surv["ca_period"] == "4_Cemex_Era").astype(int)

    cox_vars = [
        "is_retaliation", "is_coercive_rules", "is_bargaining",
        "is_discrimination", "is_surveillance", "n_allegations",
        "ln_employees", "is_trump", "is_biden_precemex", "is_postcemex",
    ]
    cox_data = surv[["duration_capped", "event"] + cox_vars].dropna()

    cph = CoxPHFitter()
    cph.fit(cox_data, duration_col="duration_capped", event_col="event")
    cph.print_summary(columns=["coef", "exp(coef)", "se(coef)", "p"])

    print(f"\nConcordance Index: {cph.concordance_index_:.4f}")


# ============================================================
# C. Hansen Threshold Regression
# ============================================================
def run_hansen_threshold(panel: pd.DataFrame) -> None:
    """Grid-search threshold regression on CA lag → RC."""
    print("\n\n" + "=" * 70)
    print("HANSEN THRESHOLD REGRESSION")
    print("=" * 70)

    df = panel.dropna(subset=["ca_count_lag1", "rc_count"]).copy()
    df = df[df["ca_count_lag1"] > 0]

    threshold_var = "ca_count_lag1"
    dep_var = "rc_count"
    n = len(df)

    candidates = np.unique(
        np.percentile(df[threshold_var], np.arange(10, 91, 1)).astype(int)
    )

    results = []
    for gamma in candidates:
        low = df[df[threshold_var] <= gamma]
        high = df[df[threshold_var] > gamma]
        if len(low) < 30 or len(high) < 30:
            continue
        X_l = np.column_stack([np.ones(len(low)), low[threshold_var].values])
        X_h = np.column_stack([np.ones(len(high)), high[threshold_var].values])
        b_l, *_ = lstsq(X_l, low[dep_var].values, rcond=None)
        b_h, *_ = lstsq(X_h, high[dep_var].values, rcond=None)
        ssr = np.sum((low[dep_var].values - X_l @ b_l) ** 2) + \
              np.sum((high[dep_var].values - X_h @ b_h) ** 2)
        results.append({
            "gamma": gamma, "ssr": ssr,
            "n_low": len(low), "n_high": len(high),
            "slope_low": b_l[1], "slope_high": b_h[1],
        })

    res_df = pd.DataFrame(results)
    best = res_df.loc[res_df["ssr"].idxmin()]

    print(f"\n  Optimal threshold: CA(t-1) = {int(best['gamma'])} cases")
    print(f"  Low regime  (≤{int(best['gamma'])}): slope = {best['slope_low']:.4f}")
    print(f"  High regime (>{int(best['gamma'])}): slope = {best['slope_high']:.4f}")
    print(f"  Ratio: {best['slope_high']/best['slope_low']:.2f}×")

    # Per-period thresholds
    print(f"\n--- Threshold by Admin Period ---")
    for period in ADMIN_PERIODS:
        sub = df[df["admin_period"] == period]
        sub = sub[sub["ca_count_lag1"] > 0]
        if len(sub) < 60:
            continue
        cands = np.unique(np.percentile(sub["ca_count_lag1"], np.arange(15, 86, 2)).astype(int))
        best_ssr, best_g, best_slopes = np.inf, None, None
        for gamma in cands:
            lo, hi = sub[sub["ca_count_lag1"] <= gamma], sub[sub["ca_count_lag1"] > gamma]
            if len(lo) < 10 or len(hi) < 10:
                continue
            X_l = np.column_stack([np.ones(len(lo)), lo["ca_count_lag1"].values])
            X_h = np.column_stack([np.ones(len(hi)), hi["ca_count_lag1"].values])
            b_l, *_ = lstsq(X_l, lo["rc_count"].values, rcond=None)
            b_h, *_ = lstsq(X_h, hi["rc_count"].values, rcond=None)
            ssr = np.sum((lo["rc_count"].values - X_l @ b_l) ** 2) + \
                  np.sum((hi["rc_count"].values - X_h @ b_h) ** 2)
            if ssr < best_ssr:
                best_ssr, best_g, best_slopes = ssr, gamma, (b_l[1], b_h[1])
        if best_g:
            print(f"  {period:25s}: γ={best_g:>3} | ratio={best_slopes[1]/best_slopes[0]:.2f}×")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Run all statistical analyses")
    parser.add_argument("--panel_path", default="data/panel/merged_panel.csv")
    parser.add_argument("--case_path", default="data/cleaned/combined_panel.csv")
    args = parser.parse_args()

    panel = pd.read_csv(args.panel_path)
    cases = pd.read_csv(args.case_path, low_memory=False, parse_dates=["Date Filed", "Date Closed"])

    run_panel_regressions(panel)
    run_survival_analysis(cases)
    run_hansen_threshold(panel)


if __name__ == "__main__":
    main()
