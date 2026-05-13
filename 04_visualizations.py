"""
04_visualizations.py
====================
Generate all research charts — Apple design system with Georgia Tech accents.

Design system : Apple structural tokens (canvas, parchment, ink, hairline)
                preserved unchanged. Accent palette uses Georgia Tech colors:
                  - GT Navy        (#003057) for secondary/structural accent
                  - GT Focus Gold  (#D1C085) for primary highlight color
                                            (lines, reference markers, fills)
                  - Dark Gold      (#857437) for text labels needing contrast
                                            against white backgrounds

COVID overlay : 2020-03-11 pandemic declaration marked on A1 timeseries.

Charts produced (9 figures, all PNG):
  f1_kpi_summary.png            — Executive summary KPI cards
  a1_monthly_timeseries.png     — Monthly CA + RC trend with COVID marker
  a2_period_bars.png            — Volume bars + certification rate line
  b1_state_heatmap.png          — Top 20 states × 4 admin periods
  b2_southern_heatmap.png       — 13 Southern states × 4 admin periods
  c1_theme_heatmap.png          — Allegation themes × 4 admin periods
  d1_survival_curves.png        — Kaplan-Meier CA → RC survival curves
  d2_forest_plot.png            — Cox PH hazard ratios (allegation factors only)
  d3_did_natural_experiment.png — Cemex Doctrine DiD natural experiment

Requirements:
    pip install matplotlib pandas numpy lifelines

Usage:
    python 04_visualizations.py \
        --panel_path data/panel/state_quarter_panel.csv \
        --case_path  data/cleaned/combined_panel.csv \
        --output_dir figures
"""

import argparse
import os
import re
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter

warnings.filterwarnings("ignore")


# ============================================================
# Design Tokens — Apple structural system, GT accent palette
# ============================================================
COLORS = {
    # GT accent palette
    "primary":        "#D1C085",   # GT Focus Gold — lines, reference markers, fills
    "secondary":      "#003057",   # GT Navy — secondary accent
    "primary_dark":   "#857437",   # Dark Gold — readable text on white background

    # Apple structural tokens — UNCHANGED
    "ink":            "#1d1d1f",   # Apple ink
    "ink_muted_48":   "#86868b",   # Apple muted (Pro-Labor Expansion period color)
    "ink_muted_80":   "#333333",   # Apple muted darker
    "body_muted":     "#cccccc",
    "canvas":         "#ffffff",   # Apple white
    "parchment":      "#f5f5f7",   # Apple parchment
    "hairline":       "#d2d2d7",   # Apple hairline
    "tile_dark_1":    "#1d1d1f",
    "tile_dark_2":    "#2a2a2c",
    "surface_black":  "#000000",

    # COVID annotation
    "covid_line":     "#c0392b",   # muted red for COVID markers
    "covid_band":     "#fdf6ec",   # warm tint for acute-period band
}

# Admin period colors — used in survival curves and scatter color-coding
PERIOD_COLORS = {
    "1_Pro-Labor_Expansion":       "#86868b",   # Apple muted gray
    "2_Employer-Favorable":           "#1d1d1f",   # Apple ink black
    "3_Labor_Restoration": "#003057",   # GT Navy
    "4_Cemex_Era":      "#D1C085",   # GT Focus Gold
}

PERIOD_LABELS = {
    "1_Pro-Labor_Expansion":       "Pro-Labor Expansion",
    "2_Employer-Favorable":           "Employer-Favorable",
    "3_Labor_Restoration": "Labor Restoration",
    "4_Cemex_Era":      "Cemex Era",
}

# COVID annotation dates
COVID_DECLARE = pd.Timestamp("2020-03-11")  # WHO pandemic declaration
COVID_END     = pd.Timestamp("2020-09-30")  # acute disruption period end


def apply_apple_style():
    """Apple design system rcParams — minimal chrome, generous whitespace."""
    plt.rcParams.update({
        "font.family":        "sans-serif",
        "font.sans-serif":    ["SF Pro Display", "SF Pro Text",
                               "Helvetica Neue", "system-ui",
                               "Arial", "sans-serif"],
        "font.size":          13,
        "axes.titlesize":     21,
        "axes.titleweight":   600,
        "axes.labelsize":     14,
        "axes.labelweight":   400,
        "axes.labelcolor":    COLORS["ink_muted_48"],
        "axes.edgecolor":     COLORS["hairline"],
        "axes.linewidth":     0.5,
        "axes.facecolor":     COLORS["canvas"],
        "axes.grid":          False,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "figure.facecolor":   COLORS["canvas"],
        "figure.dpi":         200,
        "xtick.color":        COLORS["ink_muted_48"],
        "ytick.color":        COLORS["ink_muted_48"],
        "xtick.labelsize":    12,
        "ytick.labelsize":    12,
        "xtick.major.size":   0,
        "ytick.major.size":   0,
        "legend.frameon":     False,
        "legend.fontsize":    12,
        "text.color":         COLORS["ink"],
        "savefig.bbox":       "tight",
        "savefig.pad_inches": 0.3,
    })


# ============================================================
# F1. Executive Summary KPI Cards  (GT Gold numerals)
# ============================================================
def chart_f1_kpi_summary(output_dir: str) -> None:
    kpis = [
        ("253 days",  "Median CA → RC\ntransition time"),
        ("56.5%",     "Cemex Era\ncertification rate"),
        ("1.63×",     "Hazard ratio\n(discrimination cases)"),
        ("+56.4%",    "RC petition surge\n2021 → 2022"),
        ("29.6%",     "RC workplaces with\nprior ULP history"),
        ("5.65×",     "Cemex Era discrimination\nhazard ratio"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5))
    fig.patch.set_facecolor(COLORS["parchment"])

    for ax, (value, label) in zip(axes.flat, kpis):
        ax.set_facecolor(COLORS["canvas"])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

        # Value in GT Navy
        ax.text(0.5, 0.60, value, transform=ax.transAxes,
                fontsize=34, fontweight=600, color=COLORS["secondary"],
                ha="center", va="center")
        # Label
        ax.text(0.5, 0.24, label, transform=ax.transAxes,
                fontsize=13, fontweight=400, color=COLORS["ink_muted_48"],
                ha="center", va="center", linespacing=1.5)

    fig.suptitle("NLRB Organizing Risk — Key Metrics",
                 fontsize=28, fontweight=600, color=COLORS["ink"],
                 y=0.98)
    plt.subplots_adjust(hspace=0.18, wspace=0.12,
                        top=0.90, bottom=0.04, left=0.04, right=0.96)

    fig.savefig(os.path.join(output_dir, "f1_kpi_summary.png"))
    plt.close(fig)
    print("  ✓ f1_kpi_summary.png")


# ============================================================
# A1. Monthly Time Series  (GT Gold RC line + COVID marker)
# ============================================================
def chart_a1_timeseries(cases: pd.DataFrame, output_dir: str) -> None:
    cases["ym"] = cases["Date Filed"].dt.to_period("M").dt.to_timestamp()
    ca_m = cases[cases["case_subtype"] == "CA"].groupby("ym").size()
    rc_m = cases[cases["case_subtype"] == "RC"].groupby("ym").size()

    fig, ax1 = plt.subplots(figsize=(14, 5.5))

    # Admin period background shading
    shading = [
        ("2013-01-01", "2017-01-19", COLORS["parchment"], "Pro-Labor Expansion"),
        ("2017-01-20", "2021-01-19", "#f0f0f0",            "Employer-Favorable"),
        ("2021-01-20", "2023-08-24", COLORS["parchment"], "Labor Restoration"),
        ("2023-08-25", "2024-12-31", "#e8e8ed",            "Cemex Era"),
    ]
    for start, end, color, _ in shading:
        ax1.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                    alpha=0.6, color=color, linewidth=0, zorder=0)

    # COVID acute-period band + marker
    ax1.axvspan(COVID_DECLARE, COVID_END,
                alpha=0.25, color=COLORS["covid_band"],
                linewidth=0, zorder=1)
    ax1.axvline(COVID_DECLARE, color=COLORS["covid_line"], linewidth=1.2,
                linestyle="--", zorder=4, alpha=0.8)
    ax1.text(COVID_DECLARE + pd.Timedelta(days=6), 0.97,
             "COVID-19", fontsize=8, color=COLORS["covid_line"],
             transform=ax1.get_xaxis_transform(), va="top", ha="left",
             bbox=dict(boxstyle="round,pad=0.18", facecolor=COLORS["canvas"],
                       edgecolor=COLORS["covid_line"], alpha=0.75, linewidth=0.6))

    # CA on primary axis (ink black)
    ax1.plot(ca_m.index, ca_m.values, color=COLORS["ink"], linewidth=1.4,
             alpha=0.85, label="CA (Employer ULP)")
    ax1.set_ylabel("CA filings / month", color=COLORS["ink_muted_48"])

    # RC on secondary axis — GT FOCUS GOLD
    ax2 = ax1.twinx()
    ax2.plot(rc_m.index, rc_m.values, color=COLORS["primary"], linewidth=1.4,
             label="RC (Petition)")
    ax2.set_ylabel("RC petitions / month", color=COLORS["primary_dark"])
    ax2.tick_params(axis="y", colors=COLORS["primary_dark"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(COLORS["hairline"])
    ax2.spines["top"].set_visible(False)

    # Period labels at top
    for start, end, _, label in shading:
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        ax1.text(mid, ax1.get_ylim()[1] * 0.97, label,
                 ha="center", va="top", fontsize=9, color=COLORS["ink_muted_48"],
                 fontstyle="italic", zorder=5)

    ax1.set_title("Monthly NLRB Filings, 2013–2024",
                  fontsize=24, fontweight=600, color=COLORS["ink"],
                  pad=18)

    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.savefig(os.path.join(output_dir, "a1_monthly_timeseries.png"))
    plt.close(fig)
    print("  ✓ a1_monthly_timeseries.png")


# ============================================================
# A2. Period Bars  (uniform muted gray + cert % above line dots)
# ============================================================
def chart_a2_period_bars(cases: pd.DataFrame, output_dir: str) -> None:
    rc = cases[cases["case_subtype"] == "RC"].copy()

    data = []
    for period in PERIOD_COLORS:
        sub = rc[rc["admin_period"] == period]
        months = sub["Date Filed"].dt.to_period("M").nunique()
        monthly_avg = len(sub) / months if months > 0 else 0
        closed = sub[sub["Status"] == "Closed"]
        cert_rate = (closed["Reason Closed"] == "Certific. of Representative").mean() * 100
        data.append({
            "period": PERIOD_LABELS[period],
            "monthly_avg": monthly_avg,
            "cert_rate": cert_rate,
        })
    df = pd.DataFrame(data)

    fig, ax1 = plt.subplots(figsize=(10, 6))
    x = np.arange(len(df))

    # All bars in light gray — softer than muted-48 for a cleaner look
    bars = ax1.bar(x, df["monthly_avg"], width=0.6,
                   color="#c8c8cc", alpha=0.85, zorder=3)

    # Volume labels on bars
    for bar, val in zip(bars, df["monthly_avg"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                 f"{val:.0f}", ha="center", va="bottom",
                 fontsize=14, fontweight=600, color=COLORS["ink"])

    ax1.set_xticks(x)
    ax1.set_xticklabels(df["period"], fontsize=13)
    ax1.set_ylabel("RC petitions / month", fontsize=13, color=COLORS["ink_muted_48"])
    ax1.set_ylim(0, df["monthly_avg"].max() * 1.25)

    # Certification rate overlay — GT Navy line with markers
    ax2 = ax1.twinx()
    ax2.plot(x, df["cert_rate"], color=COLORS["secondary"],
             marker="o", markersize=10, linewidth=2.2, zorder=5)

    # Percentage labels ABOVE the dots (centered on x-position)
    for xi, val in zip(x, df["cert_rate"]):
        ax2.text(xi, val + 1.2, f"{val:.1f}%",
                 ha="center", va="bottom",
                 fontsize=12, color=COLORS["secondary"], fontweight=600)

    ax2.set_ylabel("Certification rate (%)", fontsize=13,
                   color=COLORS["secondary"])
    ax2.set_ylim(40, 65)
    ax2.tick_params(axis="y", colors=COLORS["secondary"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(COLORS["hairline"])
    ax2.spines["top"].set_visible(False)

    ax1.set_title("RC Petition Volume & Union Win Rate by Policy Regime",
                  fontsize=22, fontweight=600, color=COLORS["ink"],
                  pad=16)

    fig.savefig(os.path.join(output_dir, "a2_period_bars.png"))
    plt.close(fig)
    print("  ✓ a2_period_bars.png")


# ============================================================
# B1. State Heatmap — Top 20 (GT Navy intensity scale)
# ============================================================
def chart_b1_state_heatmap(panel: pd.DataFrame, output_dir: str) -> None:
    period_order = list(PERIOD_LABELS.values())
    panel_copy = panel.copy()
    panel_copy["period_label"] = panel_copy["admin_period"].map(PERIOD_LABELS)

    period_years = {"Pro-Labor Expansion": 2.05, "Employer-Favorable": 4.0,
                     "Labor Restoration": 2.6, "Cemex Era": 1.35}

    pivot = panel_copy.groupby(["state", "period_label"])["rc_count"].sum().unstack(fill_value=0)
    for col in pivot.columns:
        if col in period_years:
            pivot[col] = pivot[col] / period_years[col]
    pivot = pivot.reindex(columns=period_order)

    pivot["total"] = pivot.sum(axis=1)
    top20 = pivot.nlargest(20, "total").drop(columns="total")

    from matplotlib.colors import LinearSegmentedColormap
    gt_cmap = LinearSegmentedColormap.from_list(
        "gt_navy", ["#f5f5f7", "#7a9ab8", "#003057"], N=256
    )

    fig, ax = plt.subplots(figsize=(9, 10))
    im = ax.imshow(top20.values, cmap=gt_cmap, aspect="auto", vmin=0)

    ax.set_xticks(range(len(top20.columns)))
    ax.set_xticklabels(top20.columns, fontsize=12, rotation=0)
    ax.set_yticks(range(len(top20.index)))
    ax.set_yticklabels(top20.index, fontsize=13, fontweight=500)

    threshold = top20.values.max() * 0.55
    for i in range(len(top20.index)):
        for j in range(len(top20.columns)):
            val = top20.iloc[i, j]
            text_color = COLORS["canvas"] if val > threshold else COLORS["ink"]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=11, color=text_color)

    ax.set_title("Annual RC Petitions by State — Top 20",
                 fontsize=22, fontweight=600, color=COLORS["ink"],
                 pad=16)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.04)
    cbar.set_label("Annual petitions", fontsize=11, color=COLORS["ink_muted_48"])
    cbar.outline.set_visible(False)

    fig.savefig(os.path.join(output_dir, "b1_state_heatmap.png"))
    plt.close(fig)
    print("  ✓ b1_state_heatmap.png")


# ============================================================
# B2. Southern States Heatmap (13 states + Industrial Belt highlight)
# ============================================================
SOUTHERN_STATES = ["AL", "AR", "FL", "GA", "KY", "LA", "MS",
                   "NC", "OK", "SC", "TN", "TX", "VA", "WV"]
INDUSTRIAL_BELT = ["KY", "TN", "GA", "AL", "SC", "NC", "MS"]


def chart_b2_southern_heatmap(cases: pd.DataFrame, output_dir: str) -> None:
    """13 Southern states × 4 admin periods, Industrial Belt highlighted."""
    rc = cases[cases["case_subtype"] == "RC"].copy()
    rc_south = rc[rc["state"].isin(SOUTHERN_STATES)].copy()

    period_years = {"1_Pro-Labor_Expansion": 2.05, "2_Employer-Favorable": 4.0,
                     "3_Labor_Restoration": 2.6, "4_Cemex_Era": 1.35}

    pivot = rc_south.groupby(["state", "admin_period"]).size().unstack(fill_value=0)
    for period in pivot.columns:
        if period in period_years:
            pivot[period] = pivot[period] / period_years[period]

    pivot = pivot[list(PERIOD_LABELS.keys())]
    pivot.columns = [PERIOD_LABELS[c] for c in pivot.columns]

    # Sort by total volume descending
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=False).drop(columns="total")

    from matplotlib.colors import LinearSegmentedColormap
    gt_cmap = LinearSegmentedColormap.from_list(
        "gt_navy", ["#f5f5f7", "#7a9ab8", "#003057"], N=256
    )

    fig, ax = plt.subplots(figsize=(8.5, 9))
    im = ax.imshow(pivot.values, cmap=gt_cmap, aspect="auto", vmin=0)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=12)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(list(pivot.index), fontsize=13)

    threshold = pivot.values.max() * 0.55
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            text_color = COLORS["canvas"] if val > threshold else COLORS["ink"]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=11, color=text_color)

    ax.set_title("Southern States — Annualized RC Petitions",
                 fontsize=22, fontweight=600, color=COLORS["ink"],
                 pad=16)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.04)
    cbar.set_label("Annual petitions", fontsize=11, color=COLORS["ink_muted_48"])
    cbar.outline.set_visible(False)

    fig.savefig(os.path.join(output_dir, "b2_southern_heatmap.png"))
    plt.close(fig)
    print("  ✓ b2_southern_heatmap.png")


# ============================================================
# C1. Allegation Theme Heatmap
# ============================================================
def chart_c1_theme_heatmap(cases: pd.DataFrame, output_dir: str) -> None:
    ca = cases[cases["case_subtype"] == "CA"].copy()

    themes = {
        "Retaliation":     r"Concerted Activities.*Retaliation|Discharge|Discipline",
        "Coercive Rules":  r"Coercive Rules",
        "Coercion":        r"Coercive Statements|Threats|Promises",
        "Surveillance":    r"Coercive Actions|Surveillance",
        "Bargaining":      r"8\(a\)\(5\)",
        "Discrimination":  r"8\(a\)\(3\)",
        "Interrogation":   r"Interrogation|Polling",
        "Weingarten":      r"Weingarten",
        "Interference":    r"8\(a\)\(2\)",
    }

    matrix = []
    for period in PERIOD_COLORS:
        sub = ca[ca["admin_period"] == period]
        row = {"period": PERIOD_LABELS[period]}
        for theme, pattern in themes.items():
            row[theme] = sub["Allegations"].str.contains(
                pattern, na=False, case=False
            ).mean() * 100
        matrix.append(row)
    df = pd.DataFrame(matrix).set_index("period")

    from matplotlib.colors import LinearSegmentedColormap
    gt_cmap = LinearSegmentedColormap.from_list(
        "gt_navy", ["#f5f5f7", "#7a9ab8", "#003057"], N=256
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.imshow(df.T.values, cmap=gt_cmap, aspect="auto", vmin=0)

    ax.set_xticks(range(len(df.index)))
    ax.set_xticklabels(df.index, fontsize=13)
    ax.set_yticks(range(len(df.columns)))
    ax.set_yticklabels(df.columns, fontsize=13)

    threshold = df.T.values.max() * 0.55
    for i in range(len(df.columns)):
        for j in range(len(df.index)):
            val = df.T.iloc[i, j]
            text_color = COLORS["canvas"] if val > threshold else COLORS["ink"]
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=11, color=text_color)

    ax.set_title("ULP Allegation Prevalence by Policy Regime",
                 fontsize=22, fontweight=600, color=COLORS["ink"],
                 pad=16)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    cbar.set_label("% of CA cases", fontsize=11, color=COLORS["ink_muted_48"])
    cbar.outline.set_visible(False)

    fig.savefig(os.path.join(output_dir, "c1_theme_heatmap.png"))
    plt.close(fig)
    print("  ✓ c1_theme_heatmap.png")


# ============================================================
# D1. Kaplan-Meier Survival Curves
# ============================================================
def chart_d1_survival(cases: pd.DataFrame, output_dir: str) -> None:
    cases["employer_key"] = (
        cases["Case Name"].str.strip().str.upper() + "|" + cases["state"].str.strip()
    )
    ca = cases[cases["case_subtype"] == "CA"].sort_values("Date Filed")
    rc = cases[cases["case_subtype"] == "RC"].sort_values("Date Filed")

    first_ca = ca.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed", "admin_period"]
    ].rename(columns={"Date Filed": "ca_date", "admin_period": "ca_period"})
    first_rc = rc.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed"]
    ].rename(columns={"Date Filed": "rc_date"})

    surv = first_ca.merge(first_rc, on="employer_key", how="left")
    surv["event"] = surv["rc_date"].notna().astype(int)
    surv["rc_date"] = surv["rc_date"].fillna(pd.Timestamp("2024-12-31"))
    surv["duration"] = (surv["rc_date"] - surv["ca_date"]).dt.days
    surv = surv[(surv["duration"] > 0) & (surv["ca_date"] >= "2015-01-01")]
    surv["duration_capped"] = surv["duration"].clip(upper=1095)
    surv.loc[surv["duration"] > 1095, "event"] = 0

    fig, ax = plt.subplots(figsize=(10, 6.5))
    kmf = KaplanMeierFitter()
    for period, color in PERIOD_COLORS.items():
        sub = surv[surv["ca_period"] == period]
        kmf.fit(sub["duration_capped"], sub["event"], label=PERIOD_LABELS[period])
        kmf.plot_survival_function(ax=ax, color=color, linewidth=1.8, ci_alpha=0.08)

    ax.set_xlim(0, 1095)
    ax.set_ylim(0.975, 1.001)
    ax.set_xlabel("Days since first CA filing", fontsize=14, color=COLORS["ink_muted_48"])
    ax.set_ylabel("Survival probability (no RC petition)", fontsize=14,
                  color=COLORS["ink_muted_48"])
    ax.set_title("Time to First Union Petition After Initial ULP Charge",
                 fontsize=22, fontweight=600, color=COLORS["ink"],
                 pad=16)
    ax.legend(loc="lower left", fontsize=12)
    ax.axhline(y=1.0, color=COLORS["hairline"], linewidth=0.5, zorder=0)

    fig.savefig(os.path.join(output_dir, "d1_survival_curves.png"))
    plt.close(fig)
    print("  ✓ d1_survival_curves.png")


# ============================================================
# D2. Forest Plot — allegation/structural factors only
#     (admin period dummies removed per user feedback)
# ============================================================
def chart_d2_forest_plot(cases: pd.DataFrame, output_dir: str) -> None:
    cases["employer_key"] = (
        cases["Case Name"].str.strip().str.upper() + "|" + cases["state"].str.strip()
    )
    ca = cases[cases["case_subtype"] == "CA"].sort_values("Date Filed")
    rc = cases[cases["case_subtype"] == "RC"].sort_values("Date Filed")

    first_ca = ca.groupby("employer_key").first().reset_index().rename(
        columns={"Date Filed": "ca_date", "admin_period": "ca_period",
                 "Allegations": "alleg", "Employees on charge/petition": "emp"}
    )
    first_rc = rc.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed"]
    ].rename(columns={"Date Filed": "rc_date"})

    surv = first_ca[["employer_key", "ca_date", "ca_period", "alleg", "emp"]].merge(
        first_rc, on="employer_key", how="left"
    )
    surv["event"] = surv["rc_date"].notna().astype(int)
    surv["rc_date"] = surv["rc_date"].fillna(pd.Timestamp("2024-12-31"))
    surv["duration"] = (surv["rc_date"] - surv["ca_date"]).dt.days
    surv = surv[(surv["duration"] > 0) & (surv["ca_date"] >= "2015-01-01")]
    surv["duration_capped"] = surv["duration"].clip(upper=1095)
    surv.loc[surv["duration"] > 1095, "event"] = 0

    def hp(text, pat):
        return int(bool(re.search(pat, str(text), re.IGNORECASE))) if pd.notna(text) else 0

    surv["Discrimination"]     = surv["alleg"].apply(lambda x: hp(x, r"8\(a\)\(3\)"))
    surv["Retaliation"]            = surv["alleg"].apply(lambda x: hp(x, r"Retaliation|Discharge|Discipline"))
    surv["Coercive Rules"]         = surv["alleg"].apply(lambda x: hp(x, r"Coercive Rules"))
    surv["Bargaining Refusal"]     = surv["alleg"].apply(lambda x: hp(x, r"8\(a\)\(5\)"))
    surv["Surveillance"]           = surv["alleg"].apply(lambda x: hp(x, r"Surveillance"))
    surv["N. of allegations"]      = surv["alleg"].str.count("\n").fillna(0) + 1
    surv["Log employees"]          = np.log1p(surv["emp"].fillna(0))

    # Admin period dummies INCLUDED in fitting (to control for time effects)
    # but EXCLUDED from the forest plot display
    surv["_trump"]    = (surv["ca_period"] == "2_Employer-Favorable").astype(int)
    surv["_biden"]    = (surv["ca_period"] == "3_Labor_Restoration").astype(int)
    surv["_postcmx"]  = (surv["ca_period"] == "4_Cemex_Era").astype(int)

    cox_vars = ["Discrimination", "Retaliation", "Coercive Rules",
                "Bargaining Refusal", "Surveillance", "N. of allegations",
                "Log employees", "_trump", "_biden", "_postcmx"]
    cox_data = surv[["duration_capped", "event"] + cox_vars].dropna()

    cph = CoxPHFitter()
    cph.fit(cox_data, duration_col="duration_capped", event_col="event")

    # Subset summary to display variables only (admin period dummies excluded from plot)
    display_vars = ["Discrimination", "Retaliation", "Coercive Rules",
                    "Bargaining Refusal", "Surveillance", "N. of allegations",
                    "Log employees"]
    summary = cph.summary.loc[display_vars,
                              ["exp(coef)", "exp(coef) lower 95%",
                               "exp(coef) upper 95%", "p"]].copy()
    summary = summary.sort_values("exp(coef)", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    y_pos = range(len(summary))

    for i, (_, row) in enumerate(summary.iterrows()):
        hr = row["exp(coef)"]
        lo = row["exp(coef) lower 95%"]
        hi = row["exp(coef) upper 95%"]
        sig = row["p"] < 0.05
        if sig and hr > 1:
            color = COLORS["secondary"]   # GT Navy
        elif sig and hr < 1:
            color = COLORS["ink_muted_80"]
        else:
            color = COLORS["ink_muted_48"]
        ax.plot([lo, hi], [i, i], color=color, linewidth=2.2, solid_capstyle="round")
        ax.plot(hr, i, "o", color=color, markersize=8, zorder=5)

        # HR value centered above the line midpoint
        mid_x = (lo + hi) / 2
        ax.text(mid_x, i + 0.28, f"HR={hr:.2f}",
                va="bottom", ha="center", fontsize=9,
                color=color, fontweight=600)

        # CI range to the right of the line end
        ax.text(hi + 0.04, i, f"[{lo:.2f}, {hi:.2f}]",
                va="center", ha="left", fontsize=8.5,
                color=COLORS["ink_muted_48"])

    # HR=1 reference line in GT FOCUS GOLD
    ax.axvline(x=1.0, color=COLORS["primary"], linewidth=2.0, linestyle="-",
               alpha=1.0, zorder=1)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(summary.index, fontsize=13)
    ax.set_xlabel("Hazard Ratio (95% CI)", fontsize=14, color=COLORS["ink_muted_48"])
    ax.set_title("Risk Factors for CA → RC Transition\nCox Proportional Hazards",
                 fontsize=22, fontweight=600, color=COLORS["ink"],
                 pad=16)

    # Widen x-axis to give room for text labels
    x_max = summary["exp(coef) upper 95%"].max()
    ax.set_xlim(summary["exp(coef) lower 95%"].min() * 0.7, x_max * 2.8)

    ax.text(0.98, 0.04,
            "Navy = significant accelerator (p<.05)\n"
            "Dark gray = significant suppressor (p<.05)\n"
            "Gold line = no effect (HR = 1.0)",
            transform=ax.transAxes, fontsize=9.5, color=COLORS["ink_muted_48"],
            ha="right", va="bottom")

    fig.savefig(os.path.join(output_dir, "d2_forest_plot.png"))
    plt.close(fig)
    print("  ✓ d2_forest_plot.png")


# ============================================================
# D3. DiD Natural Experiment — Cemex Doctrine
# ============================================================
def chart_d3_did_natural_experiment(cases: pd.DataFrame, output_dir: str) -> None:
    """
    Difference-in-Differences visualization treating the August 25, 2023
    Cemex Doctrine as a natural experiment.

    Compares 12-month windows on either side of Cemex:
      Pre-Cemex  cohort: CA filings Aug 2022 – Aug 2023
      Cemex Era cohort: CA filings Aug 2023 – Aug 2024
    Outcome: P(RC petition within 180 days)
    Treatment indicator: presence of 8(a)(3) discrimination allegation.

    DiD estimate: +0.63pp, block-bootstrap 95% CI [-0.03, +1.31], p = 0.062
    """
    cases["employer_key"] = (
        cases["Case Name"].str.strip().str.upper() + "|" + cases["state"].str.strip()
    )
    ca_full = cases[cases["case_subtype"] == "CA"].sort_values("Date Filed")
    rc_full = cases[cases["case_subtype"] == "RC"].sort_values("Date Filed")

    first_ca = ca_full.groupby("employer_key").first().reset_index().rename(
        columns={"Date Filed": "ca_date", "Allegations": "alleg"}
    )
    first_rc = rc_full.groupby("employer_key").first().reset_index()[
        ["employer_key", "Date Filed"]
    ].rename(columns={"Date Filed": "rc_date"})

    # Define matched 12-month windows
    PRE_START  = pd.Timestamp("2022-08-25")
    PRE_END    = pd.Timestamp("2023-08-24")
    POST_START = pd.Timestamp("2023-08-25")
    POST_END   = pd.Timestamp("2024-08-24")

    pre_ca  = first_ca[(first_ca["ca_date"] >= PRE_START)  & (first_ca["ca_date"] <= PRE_END)].copy()
    post_ca = first_ca[(first_ca["ca_date"] >= POST_START) & (first_ca["ca_date"] <= POST_END)].copy()

    def compute_rates(cohort_df):
        df = cohort_df.merge(first_rc, on="employer_key", how="left")
        df["rc_within_180d"] = (
            (df["rc_date"].notna()) &
            ((df["rc_date"] - df["ca_date"]).dt.days <= 180) &
            ((df["rc_date"] - df["ca_date"]).dt.days > 0)
        ).astype(int)
        df["discrim"] = df["alleg"].apply(
            lambda x: int(bool(re.search(r"8\(a\)\(3\)", str(x), re.IGNORECASE)))
            if pd.notna(x) else 0
        )
        return {
            "no_discrim": df[df["discrim"] == 0]["rc_within_180d"].mean() * 100,
            "discrim":    df[df["discrim"] == 1]["rc_within_180d"].mean() * 100,
            "n_total":    len(df),
        }

    pre  = compute_rates(pre_ca)
    post = compute_rates(post_ca)

    # DiD components
    counterfactual_post = pre["discrim"] + (post["no_discrim"] - pre["no_discrim"])
    did_pp = post["discrim"] - counterfactual_post
    n_total = pre["n_total"] + post["n_total"]

    # Visualization
    fig, ax = plt.subplots(figsize=(11, 6.5))

    x_pos = [0, 1]
    no_discrim_y = [pre["no_discrim"], post["no_discrim"]]
    discrim_y    = [pre["discrim"],    post["discrim"]]

    # Two parallel-trend lines
    ax.plot(x_pos, no_discrim_y,
            color=COLORS["ink_muted_48"], marker="o", markersize=10,
            linewidth=2.0, label="No discrimination allegation", zorder=3)
    ax.plot(x_pos, discrim_y,
            color=COLORS["secondary"], marker="o", markersize=10,
            linewidth=2.5, label="With discrimination allegation", zorder=3)

    # Value labels on markers
    for i, val in enumerate(no_discrim_y):
        ax.annotate(f"{val:.2f}%",
                    xy=(x_pos[i], val), xytext=(0, -18),
                    textcoords="offset points", ha="center",
                    fontsize=11, color=COLORS["ink_muted_48"], fontweight=600)
    for i, val in enumerate(discrim_y):
        ax.annotate(f"{val:.2f}%",
                    xy=(x_pos[i], val), xytext=(0, 14),
                    textcoords="offset points", ha="center",
                    fontsize=11, color=COLORS["secondary"], fontweight=600)

    # Counterfactual line
    ax.plot([x_pos[0], x_pos[1]], [discrim_y[0], counterfactual_post],
            color=COLORS["secondary"], linewidth=1.5, linestyle="--",
            alpha=0.45, zorder=2, label="Counterfactual (no Cemex effect)")

    # DiD effect arrow
    ax.annotate("", xy=(1.04, discrim_y[1]), xytext=(1.04, counterfactual_post),
                arrowprops=dict(arrowstyle="<->", color=COLORS["primary_dark"], lw=2.5))
    ax.text(1.085, (discrim_y[1] + counterfactual_post) / 2,
            f"DiD effect\n+{did_pp:.2f} pp\n(p = 0.062)",
            fontsize=11, color=COLORS["primary_dark"], fontweight=600,
            ha="left", va="center", linespacing=1.4)

    # Cemex boundary marker
    ax.axvline(x=0.5, color=COLORS["primary"], linewidth=1.5,
               linestyle=":", alpha=0.7, zorder=1)
    ax.text(0.5, 1.92, "Cemex Doctrine\nAug 25, 2023",
            ha="center", va="top", fontsize=9, color=COLORS["primary_dark"],
            fontstyle="italic")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(["Pre-Cemex\n(Aug 2022 – Aug 2023)",
                         "Cemex Era\n(Aug 2023 – Aug 2024)"], fontsize=12)
    ax.set_ylabel("RC petition within 180 days of CA filing (%)",
                  fontsize=13, color=COLORS["ink_muted_48"])
    ax.set_ylim(0, 1.95)
    ax.set_xlim(-0.25, 1.45)

    ax.set_title("Cemex Doctrine as Natural Experiment\n"
                 "Difference-in-Differences: Discrimination → RC Conversion",
                 fontsize=20, fontweight=600, color=COLORS["ink"],
                 pad=18)
    ax.legend(loc="upper left", fontsize=11)

    fig.text(0.5, -0.02,
             f"Matched 12-month windows on either side of the Aug 25, 2023 Cemex Doctrine. "
             f"n = {n_total:,} employers. Block-bootstrap 95% CI: [-0.03, +1.31] pp.",
             ha="center", fontsize=9.5, color=COLORS["ink_muted_48"], style="italic")

    fig.savefig(os.path.join(output_dir, "d3_did_natural_experiment.png"))
    plt.close(fig)
    print("  ✓ d3_did_natural_experiment.png")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Generate research visualizations")
    parser.add_argument("--panel_path", default="data/panel/state_quarter_panel.csv")
    parser.add_argument("--case_path",  default="data/cleaned/combined_panel.csv")
    parser.add_argument("--output_dir", default="figures")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    apply_apple_style()

    print("Loading data...")
    panel = pd.read_csv(args.panel_path)
    cases = pd.read_csv(args.case_path, low_memory=False,
                        parse_dates=["Date Filed", "Date Closed"])

    print("\nGenerating charts (Apple structure + GT Gold/Navy accents)...")
    chart_f1_kpi_summary(args.output_dir)
    chart_a1_timeseries(cases, args.output_dir)
    chart_a2_period_bars(cases, args.output_dir)
    chart_b1_state_heatmap(panel, args.output_dir)
    chart_b2_southern_heatmap(cases, args.output_dir)
    chart_c1_theme_heatmap(cases, args.output_dir)
    chart_d1_survival(cases, args.output_dir)
    chart_d2_forest_plot(cases, args.output_dir)
    chart_d3_did_natural_experiment(cases, args.output_dir)

    print(f"\nDone. {len(os.listdir(args.output_dir))} files in {args.output_dir}/")


if __name__ == "__main__":
    main()
