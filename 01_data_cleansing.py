"""
01_data_cleansing.py
====================
NLRB Case Data Cleansing Pipeline
Georgia Tech MS Analytics Capstone — Team 177

Input : Raw NLRB CSV exports (from NLRB Advanced Search)
Output: combined_panel.csv, ulp_panel.csv, rc_panel.csv

Usage:
    python 01_data_cleansing.py --input_dir data/raw --output_dir data/cleaned
"""

import argparse
import os
import glob
import zipfile
import pandas as pd
import numpy as np


# ============================================================
# Configuration
# ============================================================

# Only these three subtypes are part of the new-union organizing pipeline.
# CA = Employer unfair labor practice charges (Section 8(a))
# CB = Union unfair labor practice charges (Section 8(b))
# RC = Union representation election petitions
TARGET_SUBTYPES = ["CA", "CB", "RC"]

# Excluded subtypes and rationale:
# RD  — Decertification petition (workers seeking to REMOVE an existing union)
# RM  — Employer-filed election petition (initiated by management, not workers)
# UC  — Unit clarification (administrative adjustment to existing bargaining units)
# UD  — Deauthorization petition (removing union security clause)
# AC  — Amendment of certification (administrative name/affiliation change)
# WH  — Wage-hour cases (not NLRA-related)
# These do not represent steps in the new-union formation process.

# Non-US jurisdiction codes to exclude
NON_US_STATES = ["SK", "AE"]  # SK=Saskatchewan (Canada), AE=Armed Forces Europe

ADMIN_PERIODS = [
    ("1_Pro-Labor_Expansion", pd.Timestamp("2013-01-01"), pd.Timestamp("2017-01-19")),
    ("2_Employer-Favorable",  pd.Timestamp("2017-01-20"), pd.Timestamp("2021-01-19")),
    ("3_Labor_Restoration",   pd.Timestamp("2021-01-20"), pd.Timestamp("2023-08-24")),
    ("4_Cemex_Era",           pd.Timestamp("2023-08-25"), pd.Timestamp("2024-12-31")),
]

OUTPUT_COLUMNS = [
    "Case Number", "case_subtype", "Case Type", "Case Name",
    "Status", "Date Filed", "Date Closed", "duration_days", "Reason Closed",
    "admin_period", "year", "year_month",
    "Region", "region_num", "City", "state",
    "Employees on charge/petition", "Allegations",
    "Participants", "Union", "Unit Sought", "Voters",
]


# ============================================================
# Helper functions
# ============================================================
def extract_zips(input_dir: str) -> list[str]:
    """Extract all .zip files in input_dir and return paths to CSVs."""
    csv_paths = []
    for zp in glob.glob(os.path.join(input_dir, "*.zip")):
        with zipfile.ZipFile(zp, "r") as z:
            for member in z.namelist():
                if member.endswith(".csv") and not member.startswith("__MACOSX"):
                    z.extract(member, input_dir)
                    csv_paths.append(os.path.join(input_dir, member))
    for csv in glob.glob(os.path.join(input_dir, "*.csv")):
        if csv not in csv_paths:
            csv_paths.append(csv)
    return sorted(set(csv_paths))


def assign_admin_period(dt: pd.Timestamp) -> str | None:
    """Map a filing date to one of the four administrative period labels."""
    if pd.isna(dt):
        return None
    for label, start, end in ADMIN_PERIODS:
        if start <= dt <= end:
            return label
    return None


def cleanse(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full cleansing pipeline:
      1. Parse dates
      2. Extract case subtype from Case Number
      3. Filter to target subtypes (CA, CB, RC)
      4. Deduplicate on Case Number (identical rows from overlapping downloads)
      5. Remove non-US jurisdictions (SK, AE)
      6. Derive administrative period, year, year_month, region_num, duration
      7. Fix data quality issues (negative durations, open-case durations)
      8. Rename state column, select output columns
    """
    # 1. Parse dates
    df["Date Filed"] = pd.to_datetime(df["Date Filed"], format="%m/%d/%Y", errors="coerce")
    df["Date Closed"] = pd.to_datetime(df["Date Closed"], format="%m/%d/%Y", errors="coerce")

    # 2. Extract subtype
    df["case_subtype"] = df["Case Number"].str.extract(r"\d+-([A-Z]+)-\d+")

    # 3. Filter
    df = df[df["case_subtype"].isin(TARGET_SUBTYPES)].copy()
    print(f"  After CA/CB/RC filter: {len(df):,}")

    # 4. Deduplicate rows
    before = len(df)
    df = df.drop_duplicates(subset="Case Number", keep="last").reset_index(drop=True)
    print(f"  Duplicate rows removed: {before - len(df):,} → {len(df):,}")

    # 5. Remove non-US
    df = df.rename(columns={"States & Territories": "state"})
    non_us = df["state"].isin(NON_US_STATES).sum()
    df = df[~df["state"].isin(NON_US_STATES)].reset_index(drop=True)
    print(f"  Non-US jurisdictions removed: {non_us} → {len(df):,}")

    # 6. Derived variables
    df["admin_period"] = df["Date Filed"].apply(assign_admin_period)
    df["year"] = df["Date Filed"].dt.year
    df["year_month"] = df["Date Filed"].dt.to_period("M").astype(str)
    df["region_num"] = (
        df["Region"].str.extract(r"Region\s+(\d+)").astype(float).astype("Int64")
    )
    df["duration_days"] = (df["Date Closed"] - df["Date Filed"]).dt.days

    # 7. Fix data quality
    neg = (df["duration_days"] < 0).sum()
    df.loc[df["duration_days"] < 0, "duration_days"] = np.nan
    print(f"  Negative durations nullified: {neg}")

    open_dur = (df["Status"] == "Open") & (df["duration_days"].notna())
    open_fix = open_dur.sum()
    df.loc[open_dur, "duration_days"] = np.nan
    print(f"  Open-case durations nullified: {open_fix}")

    # 8. Select columns
    df = df[OUTPUT_COLUMNS].copy()
    return df


def print_quality_report(df: pd.DataFrame) -> None:
    """Print a data quality summary to stdout."""
    print(f"\n{'='*60}")
    print("DATA QUALITY REPORT")
    print(f"{'='*60}")
    print(f"Total cases        : {len(df):,}")
    print(f"Unique Case Numbers: {df['Case Number'].nunique():,}")
    print(f"Date range         : {df['Date Filed'].min()} – {df['Date Filed'].max()}")
    print(f"Duplicate rows     : {df['Case Number'].duplicated().sum()}")
    print(f"Negative durations : {(df['duration_days'] < 0).sum()}")
    print(f"Non-US states      : {df['state'].isin(NON_US_STATES).sum()}")

    print(f"\n--- Subtype Distribution ---")
    for st, cnt in df["case_subtype"].value_counts().items():
        print(f"  {st}: {cnt:>7,}")

    print(f"\n--- Admin Period Distribution ---")
    for label, _, _ in ADMIN_PERIODS:
        cnt = (df["admin_period"] == label).sum()
        print(f"  {label:25s}: {cnt:>6,}")

    print(f"\n--- Missing Values (>0%) ---")
    for col in df.columns:
        pct = df[col].isna().mean() * 100
        if pct > 0:
            print(f"  {col:30s}: {pct:.1f}%")

    print(f"\n--- Year-by-Year Counts ---")
    for yr in sorted(df["year"].dropna().unique()):
        yr_data = df[df["year"] == yr]
        ca = (yr_data["case_subtype"] == "CA").sum()
        cb = (yr_data["case_subtype"] == "CB").sum()
        rc = (yr_data["case_subtype"] == "RC").sum()
        print(f"  {int(yr)}: CA {ca:>5,} | CB {cb:>4,} | RC {rc:>4,}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="NLRB Data Cleansing Pipeline")
    parser.add_argument("--input_dir", default="data/raw")
    parser.add_argument("--output_dir", default="data/cleaned")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    print("[1/4] Loading raw files...")
    csv_paths = extract_zips(args.input_dir)
    if not csv_paths:
        csv_paths = glob.glob(os.path.join(args.input_dir, "*.csv"))
    print(f"  Found {len(csv_paths)} CSV file(s)")

    frames = []
    for p in csv_paths:
        df = pd.read_csv(p, low_memory=False)
        date_col = pd.to_datetime(df["Date Filed"], format="%m/%d/%Y", errors="coerce")
        print(f"  {os.path.basename(p)}: {len(df):,} rows, "
              f"{date_col.min().strftime('%Y-%m-%d')} – {date_col.max().strftime('%Y-%m-%d')}")
        frames.append(df)

    combined_raw = pd.concat(frames, ignore_index=True)
    print(f"  Combined raw total: {len(combined_raw):,}")

    print("\n[2/4] Cleansing...")
    cleaned = cleanse(combined_raw)

    print("\n[3/4] Saving...")
    ulp = cleaned[cleaned["case_subtype"].isin(["CA", "CB"])].copy()
    rc = cleaned[cleaned["case_subtype"] == "RC"].copy()

    cleaned.to_csv(os.path.join(args.output_dir, "combined_panel.csv"), index=False)
    ulp.to_csv(os.path.join(args.output_dir, "ulp_panel.csv"), index=False)
    rc.to_csv(os.path.join(args.output_dir, "rc_panel.csv"), index=False)

    print(f"  combined_panel.csv : {len(cleaned):>7,}")
    print(f"  ulp_panel.csv      : {len(ulp):>7,}")
    print(f"  rc_panel.csv       : {len(rc):>7,}")

    print("\n[4/4] Quality report...")
    print_quality_report(cleaned)
    print(f"\nDone. Output written to {args.output_dir}/")


if __name__ == "__main__":
    main()
