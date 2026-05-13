"""
02_panel_construction.py
========================
Build State-Quarter analytical panel and merge with Census QWI data.
QWI merge uses all-industry indicators only (no industry-specific variables).

Input : data/cleaned/combined_panel.csv, data/raw/qwi_raw.csv
Output: data/panel/state_quarter_panel.csv, data/panel/merged_panel.csv

Usage:
    python 02_panel_construction.py \
        --nlrb_path data/cleaned/combined_panel.csv \
        --qwi_path  data/raw/qwi_raw.csv \
        --output_dir data/panel
"""

import argparse
import os
import pandas as pd
import numpy as np


# ============================================================
# FIPS → State mapping (50 states + DC)
# ============================================================
FIPS_TO_STATE = {
    1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT",
    10: "DE", 11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID",
    17: "IL", 18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA",
    23: "ME", 24: "MD", 25: "MA", 26: "MI", 27: "MN", 28: "MS",
    29: "MO", 30: "MT", 31: "NE", 32: "NV", 33: "NH", 34: "NJ",
    35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH", 40: "OK",
    41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD", 47: "TN",
    48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV",
    55: "WI", 56: "WY",
}

# Allegation theme patterns (regex)
ALLEGATION_THEMES = {
    "n_retaliation":    r"Concerted Activities.*Retaliation|Discharge|Discipline",
    "n_coercion":       r"Coercive Statements|Threats|Promises",
    "n_coercive_rules": r"Coercive Rules",
    "n_bargaining":     r"8\(a\)\(5\)",
    "n_discrimination": r"8\(a\)\(3\)",
    "n_surveillance":   r"Surveillance",
}


# ============================================================
# Step A: Build NLRB state-quarter panel
# ============================================================
def build_nlrb_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate case-level NLRB data to state-quarter level."""
    df["quarter"] = df["Date Filed"].dt.to_period("Q")
    rows = []

    for (state, qtr), grp in df.groupby(["state", "quarter"]):
        ca = grp[grp["case_subtype"] == "CA"]
        cb = grp[grp["case_subtype"] == "CB"]
        rc = grp[grp["case_subtype"] == "RC"]
        rc_closed = rc[rc["Status"] == "Closed"]
        cert = (rc_closed["Reason Closed"] == "Certific. of Representative").sum()

        row = {
            "state": state,
            "quarter": str(qtr),
            "year": qtr.year,
            "qtr_num": qtr.quarter,
            "admin_period": grp["admin_period"].mode().iloc[0] if len(grp) > 0 else None,
            "ca_count": len(ca),
            "cb_count": len(cb),
            "rc_count": len(rc),
            "ulp_total": len(ca) + len(cb),
            "rc_certified": cert,
            "rc_cert_rate": cert / len(rc_closed) if len(rc_closed) > 0 else np.nan,
            "ca_employees": ca["Employees on charge/petition"].median(),
            "rc_employees": rc["Employees on charge/petition"].median(),
            "ca_median_duration": ca["duration_days"].median(),
            "rc_median_duration": rc["duration_days"].median(),
            "ca_multi_allege_pct": (
                (ca["Allegations"].str.count("\n").fillna(0) > 0).mean()
                if len(ca) > 0 else np.nan
            ),
        }

        for theme_name, pattern in ALLEGATION_THEMES.items():
            row[theme_name] = ca["Allegations"].str.contains(
                pattern, na=False, case=False
            ).sum()

        rows.append(row)

    panel = pd.DataFrame(rows).sort_values(["state", "quarter"]).reset_index(drop=True)

    # Lag variables
    for lag in [1, 2, 4]:
        panel[f"ca_count_lag{lag}"] = panel.groupby("state")["ca_count"].shift(lag)
        panel[f"ulp_total_lag{lag}"] = panel.groupby("state")["ulp_total"].shift(lag)
        panel[f"n_retaliation_lag{lag}"] = panel.groupby("state")["n_retaliation"].shift(lag)

    # Year-over-year change
    panel["ca_yoy"] = panel.groupby("state")["ca_count"].pct_change(4) * 100
    panel["rc_yoy"] = panel.groupby("state")["rc_count"].pct_change(4) * 100

    return panel


# ============================================================
# Step B: Process QWI — all-industry only
# ============================================================
def process_qwi(qwi_path: str) -> pd.DataFrame:
    """
    Load Census QWI data and extract state-quarter all-industry indicators.
    No industry-specific (e.g., manufacturing) variables are produced because
    NLRB cases lack NAICS codes, making industry-level matching impossible.
    """
    qwi = pd.read_csv(qwi_path, low_memory=False)
    qwi_s = qwi[
        (qwi["geo_level"] == "S") & (qwi["year"] >= 2015) & (qwi["year"] <= 2024)
    ].copy()
    qwi_s["state"] = qwi_s["geography"].astype(int).map(FIPS_TO_STATE)
    qwi_s["quarter"] = qwi_s["year"].astype(str) + "Q" + qwi_s["quarter"].astype(str)

    # All-industry state-quarter aggregates
    qwi_panel = qwi_s[qwi_s["ind_level"] == "A"][
        ["state", "quarter", "EarnS", "Emp", "TurnOvrS"]
    ].rename(columns={
        "EarnS": "earn_all", "Emp": "emp_all", "TurnOvrS": "turnover_all"
    })
    qwi_panel = qwi_panel.sort_values(["state", "quarter"])

    # Derived labor market variables
    qwi_panel["earn_yoy"] = qwi_panel.groupby("state")["earn_all"].pct_change(4) * 100
    qwi_panel["turnover_chg"] = qwi_panel.groupby("state")["turnover_all"].diff(4)
    qwi_panel["emp_yoy"] = qwi_panel.groupby("state")["emp_all"].pct_change(4) * 100

    # Lag variables (labor market pressure precedes filing behavior)
    qwi_panel["earn_yoy_lag1"] = qwi_panel.groupby("state")["earn_yoy"].shift(1)
    qwi_panel["turnover_lag1"] = qwi_panel.groupby("state")["turnover_all"].shift(1)
    qwi_panel["turnover_chg_lag1"] = qwi_panel.groupby("state")["turnover_chg"].shift(1)

    return qwi_panel


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Build analytical panels")
    parser.add_argument("--nlrb_path", default="data/cleaned/combined_panel.csv")
    parser.add_argument("--qwi_path", default="data/raw/qwi_raw.csv")
    parser.add_argument("--output_dir", default="data/panel")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    print("[1/3] Building NLRB state-quarter panel...")
    nlrb = pd.read_csv(args.nlrb_path, low_memory=False, parse_dates=["Date Filed", "Date Closed"])
    panel = build_nlrb_panel(nlrb)
    panel.to_csv(os.path.join(args.output_dir, "state_quarter_panel.csv"), index=False)
    print(f"  state_quarter_panel.csv: {panel.shape}")

    print("\n[2/3] Processing QWI data (all-industry only)...")
    if os.path.exists(args.qwi_path):
        qwi_panel = process_qwi(args.qwi_path)
        print(f"  QWI panel: {qwi_panel.shape}")

        print("\n[3/3] Merging NLRB + QWI...")
        merged = panel.merge(qwi_panel, on=["state", "quarter"], how="left")
        merged.to_csv(os.path.join(args.output_dir, "merged_panel.csv"), index=False)
        print(f"  merged_panel.csv: {merged.shape}")
        print(f"  QWI match rate: {merged['earn_all'].notna().mean()*100:.1f}%")
    else:
        print(f"  QWI file not found at {args.qwi_path} — skipping merge.")

    print("\nDone.")


if __name__ == "__main__":
    main()
