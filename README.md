# Predicting Unionization Risk from NLRB Case Data (2013 Q1 – 2025 Q3)
-----

## Project Motivation

Collective bargaining is a labor relations event that no HR practitioner can afford to ignore, regardless of industry or geography. Watching South Korea’s semiconductor sector experience a sharp surge in union organizing activity raised a question I could not let go: can the conditions that lead to union formation in the United States be detected and measured *before* a petition is filed, using publicly available data?

This project is my attempt to answer that question quantitatively. It is grounded entirely in official NLRB case records — government-sourced, reproducible, and verifiable. The intended audience is employer-side labor relations professionals, HR executives, and management-side counsel who need an early-warning framework for anticipating organizing activity at their facilities.

-----

## Data Source

**Source:** [NLRB Advanced Search](https://www.nlrb.gov/search/case) — Official public case database 
**Records:** 266,608 cases after cleaning (**289,750** raw records across three download batches)
**Period:** January 2, 2013 – September 30, 2025
**Scope:** All Unfair Labor Practice charges (CA, CB subtypes) and Representation petitions (RC subtype) filed in U.S. domestic jurisdictions

Every time a worker files a complaint against their employer (a “C-case”) or a union files a petition for a representation election (an “R-case”), the NLRB creates a permanent public record. This dataset captures every such record filed across the United States over a 12.75-year span.

-----

## Data Cleaning

NLRB case data covering 2013 through early 2026 was downloaded from the NLRB Advanced Search portal as a CSV export of 289,750 records.
From the merged dataset, only the three case subtypes directly relevant to the new-union organizing pipeline were retained: **CA** (employer unfair labor practices, 190,456 cases), **CB** (union unfair labor practices, 51,950 cases), and **RC** (union representation election petitions, 24,202 cases). The following subtypes were excluded because they represent fundamentally different labor relations processes that would introduce noise into the organizing maturity model — RD (decertification petitions filed to *remove* an existing union), RM (employer-initiated election petitions), UC (unit clarification, an administrative procedure for existing bargaining units), UD (deauthorization petitions), AC (amendment of certification), and WH (wage-hour cases).

Deduplication removed **2,832** duplicate rows confirmed as identical across all fields. Two cases filed under non-U.S. jurisdiction codes — SK (Saskatchewan, Canada) and AE (Armed Forces Europe) — were removed to restrict the analysis to domestic filings. Finally, 40 cases with negative `duration_days` values (Date Closed preceding Date Filed, a source data entry error in the NLRB system) and 2 open-status cases with erroneous closure dates were nullified rather than dropped, preserving the cases for non-duration analysis while preventing them from distorting survival models.

-----

## Column Dictionary

### Output File: `combined_panel.csv` (266,608 rows × 22 columns)

This is the case-level dataset. Each row is one NLRB case.

|Column |Description |
|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`Case Number` |Unique NLRB identifier in `RegionNum-SubtypeCode-SerialNum` format (e.g., 09-CA-271032) |
|`case_subtype` |Two-letter code extracted from Case Number: **CA** = employer unfair labor practice, **CB** = union unfair labor practice, **RC** = union representation petition |
|`Case Type` |Parent classification: **C** = Charge (ULP complaints), **R** = Representation (election-related petitions) |
|`Case Name` |Name of the charged employer or union |
|`Status` |Current case state: Closed, Open, Open-Blocked, or Inactive |
|`Date Filed` |Date the charge or petition was officially filed with the NLRB |
|`Date Closed` |Date the case was resolved (null for open cases) |
|`duration_days` |Calendar days from filing to closure; null for open cases or invalid date pairs |
|`Reason Closed` |Resolution method: Certification of Representative, Withdrawal, Dismissal, Informal Settlement, etc. |
|`admin_period` |Policy regime label based on filing date: `1_Pro-Labor_Expansion` (2013.01.01–2017.01.19), `2_Employer-Favorable` (2017.01.20–2021.01.19), `3_Labor_Restoration` (2021.01.20–2023.08.24), `4_Cemex_Era` (2023.08.25–2025.09.30) |
|`year` |Filing year |
|`year_month` |Filing year-month (e.g., 2023-08) for time series aggregation |
|`Region` |NLRB regional office with jurisdiction (e.g., “Region 10, Atlanta, Georgia”) |
|`region_num` |Numeric region code (1–34) extracted from the Region field |
|`City` |City where the employer facility is located |
|`state` |U.S. state or territory abbreviation |
|`Employees on charge/petition`|Number of workers involved in the charge or covered by the petition |
|`Allegations` |Free-text description of alleged violations, referencing specific NLRA sections (e.g., “8(a)(1) Concerted Activities (Retaliation, Discharge, Discipline)”). This field was parsed to create the allegation theme features used in regression models.|
|`Participants` |Contact details for charged parties, legal representatives, and petitioners |
|`Union` |Name of the union involved (populated primarily in RC and CB cases) |
|`Unit Sought` |Description of the bargaining unit in RC petitions |
|`Voters` |Number of eligible voters in representation elections (populated only for cases that reached the election stage) |

### Output File: `ulp_panel.csv` (242,406 rows)

Subset of `combined_panel.csv` containing only CA and CB cases (unfair labor practice charges). Same column structure.

### Output File: `rc_panel.csv` (24,202 rows)

Subset of `combined_panel.csv` containing only RC cases (union representation petitions). Same column structure.

### Output File: `state_quarter_panel.csv` (2,724 rows × 33 columns)

Aggregated panel dataset. Each row is one state in one calendar quarter. This is the primary analytical dataset for panel regression and threshold analysis.

|Column |Description |
|------------------------------------------|--------------------------------------------------------------------------|
|`state` |State abbreviation |
|`quarter` |Calendar quarter (e.g., 2023Q3) |
|`year`, `qtr_num` |Year and quarter number for seasonal controls |
|`admin_period` |Dominant policy regime for the quarter |
|`ca_count`, `cb_count`, `rc_count` |Number of CA, CB, and RC filings in that state-quarter |
|`ulp_total` |CA + CB combined count |
|`rc_certified` |Number of RC cases that resulted in union certification |
|`rc_cert_rate` |Certification rate (certified / closed RC cases) |
|`ca_employees`, `rc_employees` |Median worker count on charges/petitions |
|`ca_median_duration`, `rc_median_duration`|Median case processing time in days |
|`n_retaliation` |Count of CA cases alleging retaliation or discharge for concerted activity|
|`n_coercion` |Count alleging coercive statements, threats, or promises |
|`n_coercive_rules` |Count alleging unlawful workplace rules |
|`n_bargaining` |Count alleging Section 8(a)(5) refusal to bargain |
|`n_discrimination` |Count alleging Section 8(a)(3) discriminatory discipline or discharge |
|`n_surveillance` |Count alleging employer surveillance of union activity |
|`ca_multi_allege_pct` |Share of CA cases with multiple allegations (conflict intensity proxy) |
|`ca_count_lag1/2/4` |Lagged CA counts (1-quarter, 2-quarter, 4-quarter) |
|`ulp_total_lag1/2/4` |Lagged total ULP counts |
|`n_retaliation_lag1/2/4` |Lagged retaliation counts |
|`ca_yoy`, `rc_yoy` |Year-over-year percentage change in CA and RC counts |

-----

## Analysis Framework: The Organizing Maturity Model

We conceptualize the path to unionization as a four-stage pipeline. Each stage is observable in NLRB data:

```
Level 1 Level 2 Level 3 Level 4
ULP Charge Filed → RC Petition Filed → Election Held → Union Certified
(Grievance expressed) (Formal organizing) (Voting stage) (Contract begins)
```

The central research question is: **What quantitative factors predict whether a workplace progresses from Level 1 to Level 2?** In other words, when does simmering discontent (ULP filings) turn into organized action (a union election petition)?

|Period |Dates |Key Policy Characteristics |
|-----------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Pro-Labor Expansion**|Jan 2013 – Jan 2017 |Obama 2nd-term NLRB; Browning-Ferris joint-employer expansion; Purple Communications email organizing rights; broader worker protections |
|**Employer-Favorable** |Jan 2017 – Jan 2021 |Employer-favorable Board; narrowed joint-employer standards; restricted email organizing |
|**Labor Restoration** |Jan 2021 – Aug 2023 |Pro-labor Board appointments; enforcement expansion; case backlog growth |
|**Cemex Era** |Aug 2023 – Sept 2025|Cemex Construction doctrine adopted; mandatory bargaining orders for employer misconduct during elections; Stericycle overhaul of workplace rules standard|

-----

## Key Findings

### Finding 1: ULP Filings Are a Leading Indicator of Union Petitions

Panel fixed-effects regression shows that a one-unit increase in CA filings in the prior quarter predicts a 0.051-unit increase in RC petitions in the current quarter (p < .001), controlling for state fixed effects, seasonal patterns, and administrative regime. Two-quarter and four-quarter lags are also positive and significant (β=+0.021, p=.005; β=+0.026, p<.001), meaning ULP activity up to a year prior still predicts current organizing.

States experiencing a surge in employer-side ULP complaints today will see more union election petitions next quarter.

### Finding 2: Specific Allegation Types Predict Organizing Better Than Raw Counts

Not all complaints are equal. The type of ULP allegation matters more than the volume:

|Allegation Theme |Effect on RC Petitions |Interpretation |
|--------------------------------------------------|-----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Discrimination** (8(a)(3) violations) |β = +0.109 per case, p < .001|Strongest predictor in the panel model. Discriminatory discharge or discipline at one quarter predicts elevated RC petition volume in the next, even after controlling for total CA volume and regime effects. |
|**Coercive Rules** (unlawful workplace policies) |β = +0.103 per case, p = .22 |Directionally positive but no longer statistically significant after extending the panel to 2025 Q3. The Cox PH model still confirms an effect at the case level (see C1, D2). |
|**Bargaining Refusal** (8(a)(5) violations) |β = +0.042, p = .10 |Marginally significant. Refusal to negotiate with existing unions sparks new organizing at nearby facilities. |
|**Retaliation** (discharge for concerted activity)|β = -0.013, p = .58 |Not significant in the state-quarter panel — retaliation cases concentrated at already-unionized workplaces make this a weak panel-level predictor, though the case-level Cox PH does capture a strong Selection Effect (see D2).|

**Practical takeaway for employers:** Discrimination cases in your region’s prior quarter are the single most reliable advance signal for incoming RC petitions. Combined with the Cox PH and DiD evidence, three independent identification strategies now point at discrimination as the central catalyst variable. An internal audit of workplace policies remains valuable for compliance, but discrimination prevention is the highest-ROI organizing-prevention lever.

### Finding 3: The Cemex Doctrine Changed the Game

The NLRB’s August 2023 *Cemex Construction* decision fundamentally altered the organizing landscape. Our data shows:

|Metric |Pro-Labor Expansion|Employer-Favorable|Labor Restoration|Cemex Era|
|------------------------------------|-------------------|------------------|-----------------|---------|
|RC petitions per month |166 |131 |154 |**179** |
|Certification success rate |48.6% |51.4% |55.0% |**55.6%**|
|Coercive Rules allegations (% of CA)|7.8% |6.2% |9.1% |**11.5%**|

The Cemex Era regime has the highest petition volume, highest success rate, and highest prevalence of Coercive Rules allegations in the dataset. All differences are statistically significant (Kruskal-Wallis p < .001 for volume; Chi-square p < .001 for certification rates). Under the current legal framework, employers face a structurally higher baseline risk of organizing. The margin for error in labor relations compliance has narrowed — mistakes in election conduct can now result in automatic bargaining orders rather than re-run elections.

### Finding 4: Discrimination Cases Are the Strongest Trigger for Organizing

Cox Proportional Hazards survival analysis tracked 80,529 employers from their first ULP charge to determine which factors accelerated or delayed a subsequent RC petition. Key findings:

|Factor |Hazard Ratio|Meaning |
|---------------------------------------|------------|------------------------------------------------------------------------------------------------------------------------------|
|**Discrimination allegation (8(a)(3))**|**1.68** |Employers charged with discriminatory discharge or discipline are **68% more likely** to face a union petition, all else equal|
|**Employer size (ln employees)** |**1.10** |Larger workplaces convert to organizing 10% faster per unit of log-scale size |
|Retaliation |0.50 |50% reduction (Selection Effect — retaliation cases concentrated at already-unionized workplaces) |
|Bargaining (8(a)(5)) |0.78 |22% reduction (also concentrated at existing-union sites) |

**Robustness check on discrimination effect.** We verified the discrimination effect across five model specifications: univariate (HR=1.73), with employer size control (HR=1.72), comparing with and without retaliation (raw event rates 2.30% vs 1.11%), period-stratified, and with allegation count instead of discrimination. All specifications produce a strong, significant accelerating effect. Most striking, the discrimination effect intensifies dramatically over time: HR = 1.44 (Pro-Labor Expansion) → 1.54 (Employer-Favorable) → 2.36 (Labor Restoration) → **4.07 (Cemex Era)**. The Cemex Doctrine appears to have amplified the organizing-trigger effect of discrimination cases by roughly 2.4×.

A single high-profile termination perceived as discriminatory is the most dangerous catalyst for organizing — and that danger has increased substantially under the current regulatory environment.

### Finding 5: 29.9% of Petitioned Workplaces Had Prior ULP History

Nearly three in ten workplaces that received an RC petition had at least one prior CA charge on record. The median time from the most recent CA filing to an RC petition was **248 days (approximately 4 months)**. The 8-month window after a ULP charge is the critical intervention period.

### Finding 6: Southern States Show Differentiated Organizing Patterns

While traditional union strongholds (CA, NY, IL) maintain steady volumes, the South shows a sharp split between two patterns. Southern Industrial Belt states with concentrations of foreign manufacturer investment (TN, NC, GA, AL, KY, SC, MS) show substantial Cemex Era growth — Tennessee +86% over Employer-Favorable-era baseline, Kentucky +52%, Georgia +46%, North Carolina +40%. By contrast, traditional South states (LA, FL, TX) follow other trajectories. This pattern suggests that organizing is expanding into regions where workforce composition has shifted toward larger industrial employers, particularly EV and auto manufacturing.

### Finding 7: Cemex Doctrine as Natural Experiment — Causal Evidence

To strengthen the causal interpretation of the discrimination effect, we treat the August 25, 2023 Cemex Doctrine as a natural experiment. We compare matched 12-month windows on either side of the policy change (Aug 2022 – Aug 2023 vs. Aug 2023 – Aug 2024), using employers without discrimination allegations as a control group:

|Group |Pre-Cemex 180-day RC rate|Cemex Era 180-day RC rate|Within-group change|
|------------------------------|-------------------------|-------------------------|-------------------|
|No discrimination allegation |0.301% |0.225% |-0.076 pp |
|With discrimination allegation|0.916% |1.466% |**+0.550 pp** |

**Difference-in-Differences estimate: +0.627 percentage points.** Block-bootstrap 95% CI: [-0.032, +1.308] pp; p = 0.096. The estimate is marginally significant (p < .10 but not p < .05) — strong enough to be informative, but not so strong as to be conclusive on its own. We interpret this as supportive evidence that Cemex Doctrine *causally* amplified the organizing-trigger effect of discrimination cases beyond what would be expected from secular trends or selection effects alone.

In relative terms, discrimination allegations roughly doubled the 180-day RC conversion rate before Cemex (0.32% → 0.91%), and tripled it after Cemex (0.24% → 1.45%). The Cox PH and the DiD analyses converge on the same finding via independent identification strategies, which strengthens confidence in the result.

-----

## Methodology Notes

### Statistical Models Used

|Model |Purpose |Specification |
|---------------------------------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
|**Panel Fixed Effects (OLS)** |Estimate ULP → RC pathway |State fixed effects, clustered standard errors by state, seasonal dummies |
|**Cox Proportional Hazards** |Identify employer-level risk factors for CA → RC transition |Time-to-event framework with right-censoring at 3 years |
|**Kaplan-Meier + Log-Rank** |Compare survival curves across policy regimes |Non-parametric, no distributional assumptions |
|**Hansen Threshold Regression** |Test for non-linear breakpoints in ULP → RC relationship |Grid search with block bootstrap p-values |
|**Difference-in-Differences** |Causal estimation of Cemex Doctrine effect on discrimination → organizing|Matched 12-month windows, linear probability model with state-clustered block bootstrap|
|**Kruskal-Wallis + Mann-Whitney**|Compare distributions across regimes |Non-parametric tests for monthly filing rates |
|**Chi-Square** |Compare certification rates across regimes |Contingency table analysis |

### Policy Regime Boundary Dates

This analysis defines regime transitions at presidential inauguration dates (January 20). In practice, NLRB policy shifts do not occur instantaneously at inauguration. Board members serve staggered five-year terms; Senate confirmation of new appointees typically requires 6–9 months; and landmark case decisions — which operationalize the new Board majority’s policy direction — may follow 12–18 months after the new president takes office. This means the true “treatment onset” for each regime lags the inauguration date by a variable and imprecise interval.

We retain inauguration dates as boundaries for three reasons: (1) they are unambiguous, publicly verifiable, and replicable — any alternative date (e.g., the date a new Board majority was seated) would require case-by-case historical research and introduce subjective judgment; (2) the regime labels describe the *political environment* in which NLRB cases are filed, not the Board composition at the moment of filing — filers respond to the perceived direction of policy, which shifts with the election outcome itself; and (3) any measurement error introduced by the lag is symmetric across regimes and attenuates estimated regime effects toward zero, meaning our findings are conservative lower bounds of the true policy impact.


### Questions This Analysis Does Not Answer

**1. How would findings change with full industry-level segmentation?**

NLRB cases do not include NAICS industry codes. The current analysis aggregates across all industries within each state-quarter. Industry-specific organizing dynamics — particularly the divergent patterns we suspect between manufacturing, healthcare, food service, and retail — remain unmeasured. The follow-on project will use NLP-based classification on the `Case Name` field to assign NAICS codes, enabling industry-specific risk scoring and sector-level analysis.

**2. What would a richer text-based analysis of unfair labor practice complaints reveal?**

The NLRB Allegations field contains only 55 unique standardized phrases, which made regex-based feature extraction reliable but also constrained the depth of analysis. Full-text complaint documents (PDFs) contain narrative detail about specific management actions, supervisor identity, worker descriptions, and facility characteristics that cannot be extracted from the structured Allegations field. A document-level NLP pipeline using domain-adapted language models (Legal-BERT or fine-tuned alternatives) could extract entity-relationship information that becomes new covariates in the Cox model.

**3. How robust is the Cemex effect over a longer observation window?**

The Cemex Era regime currently spans only 25 months (August 2023 – September 2025), the shortest of the four regimes by a wide margin. Several findings — the dramatic intensification of the discrimination hazard ratio (HR=4.07), the lowered organizing threshold (γ=79), and the +0.63pp DiD estimate — could reflect novelty effects that attenuate as practitioners on both sides adapt to the new doctrine. Distinguishing permanent structural shifts from transitional dynamics will require an additional 24 months of observation.

**4. Are the patterns we identify driven by direct causation, by employer-level marker effects, or by both?**

All findings are derived from observational NLRB records, not from a randomized experimental design. The discrimination → organizing finding, in particular, may reflect a direct catalyst effect (a discrimination event galvanizes coworker mobilization) or may reflect a marker effect (discrimination is a visible symptom of broader hostile management culture, and the underlying culture is what drives organizing). The Cemex DiD analysis (Finding 7) provides the strongest causal lens currently available within this dataset, and both interpretations of the discrimination finding support the same practical recommendation. But the underlying mechanism cannot be fully resolved without firm-level survey data on management practices and employee sentiment.

**5. What would a properly identified study of labor market pressure look like?**

We initially merged Census Bureau Quarterly Workforce Indicators (QWI) to test whether wage stagnation and falling turnover predict organizing. We removed those analyses from the final report after concluding that uncontrolled state-level inflation differentials (state CPI variation up to 21%) and the inability to separate voluntary from involuntary turnover (QWI does not provide this split) compromised the validity of the wage and turnover coefficients. A future study using BLS Regional CPI for proper real-wage construction and BLS JOLTS data for voluntary quit rates separated from layoffs would test the Hirschman Exit-Voice mechanism more rigorously than was possible here.

-----

## Figures

All figures are generated by `scripts/04_visualizations.py` and saved to the `figures/` directory.

**COVID-19 annotation.** Chart A1 carries a dedicated COVID-19 overlay (described in detail in its section). This annotation was added because the pandemic’s acute disruption period (March–September 2020) falls entirely within the Employer-Favorable administrative regime. Without a visual marker, a reader could incorrectly attribute the 2020 RC petition trough — the lowest monthly total in the entire 12.75-year dataset — to NLRB policy effects rather than to the pandemic-driven shutdown of normal business and legal activity. No other chart carries this annotation; A2 through D3 aggregate data to the regime, employer, or DiD-cohort level, where the monthly shock is absorbed and does not require separate notation.

-----

### F1. Executive Summary — Key Metrics

![KPI Summary](figures/f1_kpi_summary.png)

**What this chart shows.** A single-page dashboard of six headline numbers drawn from the full analysis. The page is divided into a 2×3 grid of white cards on a parchment background, each presenting one metric as a large GT Focus Gold numeral with a concise plain-language label in muted gray beneath it. The card layout is designed to be projected at the opening or closing of an executive briefing — it requires no axis reading, no legend, and no statistical background to interpret.

**The six metrics and why each was chosen.**

- **248 days** — The median time from an employer’s first CA charge to a first RC petition at the same facility, among all employers where the transition occurred within three years. This is the operational planning horizon: an ER team that receives a CA charge and does not address its root cause has roughly eight months before that unresolved grievance is likely to escalate into a formal organizing attempt.
- **55.6%** — The union certification rate for RC petitions filed under the Cemex Era regime (August 2023–September 2025). Unions win more than half of all elections conducted under current NLRB rules, the highest success rate in the 12.75-year study period. For comparison, the Employer-Favorable-era rate was 51.4%.
- **1.68×** — The hazard ratio for discrimination (Section 8(a)(3)) allegations from the Cox proportional hazards model. An employer charged with discriminatory discharge or discipline is 68% more likely to face a union petition than an otherwise identical employer without that allegation. This is the single strongest case-level predictor in the model, and its effect intensifies to HR=4.07 under the Cemex Era regime.
- **+56.4%** — The year-over-year increase in RC petitions from 2021 to 2022. This was the largest single-year jump in the study period and marks the structural turning point in the post-COVID organizing wave.
- **79 cases** — The Cemex Era ULP accumulation threshold (γ) from the Hansen threshold regression. When a state reaches 79 CA filings in a single quarter, the marginal effect of each additional filing on RC petition volume increases. Under prior regimes this threshold was substantially higher (90–126 cases), meaning the current regulatory environment converts worker discontent into formal organizing activity at a lower friction point.
- **29.9%** — The share of facilities that received an RC petition and had at least one prior CA charge on record at the same employer, within a three-year lookback window. Nearly three in ten petitioned workplaces had a detectable complaint history before the union election campaign began.

**What practitioners should see.** These six numbers constitute a minimum viable risk briefing. Any labor relations team that can track its facilities against these benchmarks — charge recency, charge type, regional certification rates, and state-level ULP volume — has the inputs needed to identify elevated organizing risk before a petition is filed.

-----

### A1. Monthly NLRB Filings, 2013–2025
<img width="2556" height="1111" alt="Monthly NLRB Filings" src="https://github.com/user-attachments/assets/078a9c8a-8722-4b3e-ada0-ac07adf44aac" />

**What this chart shows.** A dual-axis time series covering every month from January 2013 through September 2025. The left vertical axis and the dark ink line track monthly CA filings — charges alleging employer unfair labor practices under Section 8(a) of the NLRA. The right vertical axis and the **GT Focus Gold** line track monthly RC petition filings — formal worker requests to hold a union representation election. Four alternating parchment and off-white background bands mark the four presidential policy regimes, allowing the viewer to simultaneously read absolute filing volumes and the policy context in which they occurred.

**COVID-19 annotation.** A warm-tinted band covers March 11 through September 30, 2020. March 11, 2020 is the date the World Health Organization declared COVID-19 a global pandemic. The band ends September 30, 2020, when broad economic reopening was underway across most U.S. states. A dashed red vertical line marks the exact declaration date, and a small labeled pill annotation identifies the period. The annotation is present because the 2020 Q2 RC trough — the lowest monthly count in the study period at 249 petitions — falls within the Employer-Favorable administrative regime band. Without this marker, a reader scanning the chart could attribute that trough to NLRB policy suppression rather than to the pandemic shutdown. The annotation makes explicit that the 2020 dip is an external shock, not a policy outcome, which is essential for correctly interpreting the Employer-Favorable-era monthly average (131 petitions) cited in chart A2.

**What the chart reveals.**

- A visible decline in RC petition volumes from 2017 through mid-2020, consistent with a combination of Employer-Favorable-era NLRB enforcement posture and the pandemic-induced disruption.
- A V-shaped recovery beginning in late 2020 that accelerates sharply through 2021 and peaks in early 2022 — the Starbucks and Amazon organizing wave — at the highest monthly RC levels in the dataset.
- Sustained elevated activity from August 2023 onward under the Cemex Era regime, with RC petitions consistently above 170 per month.
- A repeating seasonal pattern: filings peak in March and trough in December each year. Any forecasting model built on this data must include seasonal controls.

**What practitioners should see.** The GT Focus Gold line is the leading indicator to watch. When RC petitions in your region have been climbing for two or more consecutive months, ULP charges tend to follow within one to two quarters — or have already been filed. This chart provides the macro backdrop against which any facility-level alert should be contextualized.

-----

### A2. RC Petition Volume & Union Win Rate by Policy Regime

<img width="2020" height="1178" alt="RC Petition Volume   Union Win Rate by Policy Regime" src="https://github.com/user-attachments/assets/59199582-adfc-4a08-b3af-d3413ce530ce" />


**What this chart shows.** A paired visualization comparing the four administrative periods on two dimensions simultaneously. The vertical bars (left axis) show the monthly average number of RC petitions filed during each regime. All four bars share a uniform muted gray color so the visual focus rests on bar height, not on the regime color coding. The GT Focus Gold line with circular markers (right axis) shows the union certification rate — the percentage of closed RC cases in which the union won the election and received NLRB certification — for each regime. Percentage labels are positioned directly above each marker to maintain a clean reading line.

**What the chart reveals.**

The two metrics move in the same direction across all four regimes. Monthly petition volume rises from 131 (Employer-Favorable) to 166 (Pro-Labor Expansion) to 154 (Labor Restoration) to 176 (Cemex Era). Simultaneously, the certification rate climbs from 48.6% (Pro-Labor Expansion) to 51.4% (Employer-Favorable) to 55.0% (Labor Restoration) to 55.6% (Cemex Era). The combination is significant: higher volume multiplied by a higher win rate means that the number of newly unionized workplaces per year is increasing faster than either metric alone would suggest.

The Employer-Favorable bar incorporates the COVID-19 pandemic trough (see A1). Without COVID, the Employer-Favorable-era figure would be moderately higher, though still the lowest of any full-year administrative period in the dataset.

**What practitioners should see.** The rightmost bar and the rightmost marker on the certification line define the current operating environment. Any risk threshold or union-avoidance playbook calibrated on Employer-Favorable-era parameters is underestimating both the volume and the success probability of current organizing activity. The regime shift from Employer-Favorable to Cemex Era represents a 37% increase in petition volume and a 5 percentage-point increase in union win probability.

-----

### B1. Annual RC Petitions by State — Top 20 States

<img width="1697" height="1793" alt="Annual RC Petitions by State - Top 20" src="https://github.com/user-attachments/assets/c9469dd5-574e-4f9d-8d46-cf35a6772e33" />

**What this chart shows.** A heatmap in which the 20 states with the highest total RC petition volume across the full study period are listed on the vertical axis, and the four administrative regimes appear as columns on the horizontal axis. Each cell displays the annualized petition count for that state-regime combination — calculated by dividing the total petitions filed during the regime by the number of years in that regime (Pro-Labor Expansion: 4.05 years; Employer-Favorable: 4.0 years; Labor Restoration: 2.59 years; Cemex Era: 2.10 years). Annualizing removes the distortion caused by regimes of unequal length. Color intensity scales from pale blue (low annual volume) to deep GT Navy (high annual volume), using a custom two-tone gradient anchored to GT Navy.

**What the chart reveals.**

California, New York, Illinois, and Pennsylvania occupy the top four rows across all regimes — these are states with large workforces, established union infrastructure, and long histories of labor organizing. Their cells darken only modestly across regimes, meaning they are consistently high-volume regardless of who controls the NLRB.

The analytically important signal is in the middle of the chart. States such as Washington, Oregon, Colorado, and North Carolina show significant darkening in the Cemex Era column relative to their Employer-Favorable-era baseline. This pattern indicates geographic expansion: the post-2021 organizing wave is not simply a recovery of activity in traditional union strongholds but a broadening of organizing into states that historically had lower union density. This is consistent with the Starbucks campaign strategy of targeting non-traditional markets and with the Cemex Doctrine making it easier to achieve certification in any jurisdiction.

**What practitioners should see.** Compare the color intensity of your state’s row from left (Employer-Favorable) to right (Cemex Era). If the rightmost cell is noticeably darker, your state is on an accelerating trajectory. Multi-state employers should rank their facility states by this gradient — the states with the largest left-to-right darkening are the regions where proactive investment in labor relations infrastructure is most warranted.

-----

### B2. Southern States — Annualized RC Petitions

<img width="1678" height="1639" alt="Southern States - Annualized RC Petitions" src="https://github.com/user-attachments/assets/08b9cdd9-d07e-49f5-9317-0d1b057d18a6" />

**What this chart shows.** A focused heatmap covering only the 13 Southern U.S. states (Census Bureau South Region: AL, AR, FL, GA, KY, LA, MS, NC, OK, SC, TN, TX, VA, WV — minus DC) with the same four-period column structure and the same GT Navy intensity scale used in B1. Southern Industrial Belt states with concentrated foreign manufacturer investment (KY, TN, GA, AL, SC, NC, MS — automotive and EV plants: Hyundai, Toyota, Volkswagen, BMW, Mercedes, Volvo, Rivian) are indicated in the text below the chart. States are sorted by total petition volume across all four periods.

**What the chart reveals.**

The South does not move as a single block. Three distinct patterns emerge:

- **Industrial Belt acceleration.** Tennessee shows the most striking growth — annualized RC petitions climbed from 9.8 (Employer-Favorable) to 18.1 (Cemex Era), an 86% increase. Kentucky (+52%), Georgia (+46%), and North Carolina (+40%) follow the same trajectory. This pattern coincides with the Volkswagen Chattanooga UAW certification (April 2024), the establishment of Hyundai Metaplant Georgia, and the growth of the EV manufacturing corridor across the Carolinas and Georgia. The Cemex Doctrine appears to be materially affecting organizing activity in regions with concentrated industrial employment.
- **Stable high-volume states.** Texas and Florida remain the highest-volume Southern states by absolute count, but their growth rates are moderate (TX +16%, FL +20%) — large workforce bases generate steady filing volumes regardless of regime.
- **Persistent low-activity states.** Mississippi, Arkansas, and West Virginia maintain very low annualized petition counts (under 6 per year) throughout the study period. Smaller workforces and the historic absence of large-scale industrial concentration limit the organizing pipeline.

**What practitioners should see.** For employers operating in the Southern Industrial Belt, the data signals a structurally different organizing environment than the broader Southern norm. Right-to-work statutes in these states constrain post-certification union security but do not affect federal election rules or Cemex Doctrine remedies. Facilities in TN, NC, KY, and GA — particularly those in the EV and foreign-automotive supply chain — should expect organizing risk levels closer to those documented in WA, OR, and CO than to the historical Southern baseline.

-----

### C1. ULP Allegation Prevalence by Policy Regime

<img width="2347" height="1031" alt="ULP Allegation Prevalence by Policy Regime" src="https://github.com/user-attachments/assets/7704c554-1249-4a19-9e79-b004ef6fa904" />

**What this chart shows.** A heatmap with nine allegation themes on the vertical axis and the four policy regimes on the horizontal axis. Each cell shows the percentage of CA cases filed in that regime that contained the given allegation type. Allegation types were extracted from the NLRB Allegations field using structured regex patterns against 55 unique NLRB-coded phrases. Color intensity scales from white (low prevalence) to deep GT Navy (high prevalence). The chart is read row-by-row: a row that darkens consistently from left to right indicates a theme that is growing across regimes.

**What the chart reveals.**

The “Coercive Rules” row is the most dramatic. It darkens from 6.2% under Employer-Favorable to 11.5% under Cemex Era — an increase of 92%. This directly reflects the NLRB’s August 2023 *Stericycle* decision, which replaced the prior permissive standard for evaluating employer workplace rules with a stricter “reasonably construe” test. Under *Stericycle*, any handbook policy that workers could reasonably interpret as restricting their right to engage in concerted activity is presumptively unlawful, regardless of employer intent. The immediate surge in Coercive Rules charges confirms that workers and unions began invoking this new standard within months of the decision.

“Retaliation” (discharge or discipline for concerted activity under Section 8(a)(1)) shows steady growth from 26% to 30% across all four regimes. “Bargaining Refusal” (Section 8(a)(5)) remains the highest-volume allegation type at 35–41%, but it is structurally different from the others: 8(a)(5) charges arise primarily at already-unionized workplaces where an employer refuses to negotiate in good faith, not at organizing targets. The “Discrimination” row (Section 8(a)(3)) is moderate in prevalence (15–19%) but is the most consequential for escalation risk — see chart D2.

**What practitioners should see.** The “Coercive Rules” column under Cemex Era is the most directly actionable finding in the entire dataset. Every employer-side labor attorney should audit the company’s employee handbook, attendance policy, social media policy, solicitation and distribution rule, and any confidentiality policy governing wages or working conditions against the *Stericycle* standard. These are the charges that are growing fastest, they are the charges that employers most directly control, and they are the charges whose underlying conduct is most correctable without litigation.

-----

### D1. Time to First Union Petition After Initial ULP Charge

<img width="1944" height="1303" alt="Time to First Union Petition After Initial ULP Charge" src="https://github.com/user-attachments/assets/1af1e0c5-676d-4a1f-9dc9-ccf9b009537b" />

**What this chart shows.** Kaplan-Meier survival curves estimated for 80,529 unique employers, each tracked from the date of their first CA charge through either their first RC petition (the event) or the end of the study period (right-censoring). Survival is defined as the probability that an employer has not yet received an RC petition at a given number of days after the first CA charge. Each of the four administrative periods is plotted as a separate step-function curve with a faint confidence band. The four curves are colored in the regime palette: slate gray (Pro-Labor Expansion), ink black (Employer-Favorable), GT Navy (Labor Restoration), and GT Focus Gold (Cemex Era).

The y-axis spans only 0.975 to 1.000. This narrow range is deliberate. Overall, only 1.4% of employers with a CA charge ever receive an RC petition within three years — the absolute event rate is low. However, the meaningful differences between regimes occur within this narrow band, and collapsing the axis to its informative range makes those differences readable. A chart spanning 0 to 1.0 would show four nearly identical lines at the very top, rendering the regime differences invisible.

**What the chart reveals.**

The Pro-Labor Expansion curve (slate gray) falls most steeply — employers who received their first CA charge between 2013 and January 2017 had the highest probability of subsequently receiving an RC petition. The Employer-Favorable curve (ink black) falls least steeply, reflecting the documented suppressive effect of Employer-Favorable-era NLRB policy on organizing activity — fewer charges translated into formal petitions during this period. The Labor Restoration (GT Navy) and Cemex Era (GT Focus Gold) curves fall between these two extremes and are not statistically distinguishable from each other, though both are distinguishable from the Employer-Favorable curve.

Log-rank tests confirm that the Pro-Labor Expansion curve is statistically different from all three later regimes (all p < .001). The Employer-Favorable curve is statistically different from Pro-Labor Expansion (p < .001) but not from the two Biden-era curves, consistent with the interpretation that the 2021 change in NLRB leadership partially — but not fully — reversed the Employer-Favorable-era suppression.

**What practitioners should see.** The vertical gap between curves at any given day count represents the difference in cumulative petition risk by regime. For a company with 500 facilities, even a 0.3 percentage-point difference in per-facility annual petition probability translates into roughly 1–2 additional organizing campaigns per year. The chart quantifies what regime shift means at the portfolio level.

-----

### D2. Risk Factors for CA → RC Transition — Cox Proportional Hazards

<img width="2017" height="1217" alt="Risk Factors for CA-RC Transition Cox Proportional Hazards" src="https://github.com/user-attachments/assets/69247edb-1123-486b-8d6d-ed0477107f15" />

**What this chart shows.** A forest plot displaying the hazard ratios, 95% confidence intervals, and statistical significance of the seven case-level allegation and structural factors from the Cox proportional hazards model. Administrative period dummies (Employer-Favorable, Labor Restoration, Cemex Era) were included in the model fit to control for time-varying baseline hazards but are excluded from the visual display because their effects are already shown in chart D1 and would otherwise compete with the case-level factors that are the focus of this chart.

The horizontal axis represents the hazard ratio — the multiplicative change in the instantaneous rate of CA-to-RC transition associated with each predictor. The **GT Focus Gold vertical line at HR = 1.0** marks no effect. Points plotted to the right of the gold line indicate factors that accelerate the transition; points to the left indicate suppression. Horizontal error bars span the 95% confidence interval. **GT Navy markers** denote statistically significant accelerators (p < 0.05, HR > 1); dark gray markers denote statistically significant suppressors (p < 0.05, HR < 1); muted gray markers denote non-significant effects.

**What the chart reveals.**

The single largest accelerator is the “Discrimination” indicator: an employer whose first CA charge includes an allegation of discriminatory discharge or discipline faces a hazard ratio of 1.68, meaning it experiences the CA-to-RC transition 68% faster than an otherwise similar employer without that allegation. This finding is interpretively robust — a discriminatory termination of an employee visibly active in organizing sends a clear signal to the remaining workforce about management’s willingness to tolerate organizing, often galvanizing rather than deterring further activity. The discrimination effect intensifies dramatically in the Cemex Era period (HR=4.07 when fitted on Cemex Era subset alone).

“Number of allegations” (HR = 1.24) and “Log employees” (HR = 1.10) are the next two significant accelerators. Each additional allegation in a single charge increases transition hazard by 24%; doubling the number of covered employees (one unit on the log scale) increases hazard by 10%. Both effects are additive: a large employer facing a multi-allegation discrimination charge occupies the highest-risk position in the model.

On the suppressive side, the “Retaliation” indicator (HR = 0.50) appears counterintuitive but is methodologically sound. Retaliation charges under Section 8(a)(1) most frequently arise at workplaces that already have a union — management retaliating against protected concerted activity by existing union members. Such workplaces do not generate new RC petitions (the union is already certified), which mechanically lowers the hazard ratio for this variable.

**What practitioners should see.** This chart provides a case-level risk triage framework. When an ER team receives a new CA charge, the first questions to ask are: Does it include an 8(a)(3) allegation? How many counts does it contain? What is the size of the covered workforce? Affirmative answers to all three questions place the employer in the highest-hazard quadrant. A single-count 8(a)(5) charge at a small facility with no discrimination allegation sits near the other end of the risk spectrum. Prioritizing senior ER attention and legal resources according to this profile — rather than treating all charges equally — is the most operationally efficient application of this model.

-----

### D3. Cemex Doctrine as Natural Experiment — Difference-in-Differences

<img width="2067" height="1450" alt="Discrimination -RC Conversion" src="https://github.com/user-attachments/assets/d18da8c8-ca61-4ebb-95b8-355fd779dd87" />

**What this chart shows.** A parallel-trends visualization implementing a Difference-in-Differences (DiD) causal estimation. The August 25, 2023 *Cemex Construction* decision is treated as an exogenous policy shock — employers and unions did not choose its timing, and its effect on enforcement standards was immediate. We compare two matched 12-month cohorts of employers who received their first CA charge: the **Pre-Cemex cohort** (Aug 2022 – Aug 2023, n = 6,289) and the **Cemex Era cohort** (Aug 2023 – Aug 2024, n = 7,243). The outcome is the probability that an RC petition follows the CA charge within 180 days.

The horizontal axis shows the two time periods, separated by a dotted GT Focus Gold vertical line marking the Cemex Doctrine effective date. Two trend lines are plotted: the dark gray line tracks the RC conversion rate for employers without discrimination allegations (control group, used to identify general policy-environment shifts), and the GT Navy line tracks employers with discrimination allegations (treatment group). The dashed line shows the counterfactual: what the discrimination cohort’s Cemex Era rate would have been if it had moved in parallel with the no-discrimination control. The vertical Dark Gold arrow at the right of the chart isolates the DiD effect — the gap between the actual Cemex Era rate for the discrimination group and the counterfactual.

**What the chart reveals.**

In the Pre-Cemex year, employers without discrimination allegations had a 0.301% RC conversion rate within 180 days; those with discrimination allegations had 0.916%. After Cemex, the no-discrimination rate dropped slightly to 0.225% (consistent with broad enforcement-environment factors not specific to discrimination), while the discrimination group rose sharply to 1.466%. The DiD estimate isolates the change attributable specifically to Cemex’s interaction with discrimination cases:

**+0.627 percentage points (95% CI: [-0.032, +1.308] pp; p = 0.096).**

This is a marginally significant effect (p < .10 but not p < .05). We deliberately report this honestly rather than overstating it. The result is best interpreted as *supportive evidence* that Cemex Doctrine causally amplified the organizing-trigger effect of discrimination cases beyond what general secular trends would predict. Crucially, the DiD result triangulates with the Cox PH finding (HR = 4.07 for discrimination in the Cemex Era period alone) via a completely independent identification strategy. When two methods using different assumptions point in the same direction, confidence in the underlying finding strengthens.

**What practitioners should see.** The DiD evidence reinforces the central practical message: discrimination prevention is a high-ROI labor relations investment under the current regulatory regime, and the return has measurably increased since August 2023. A discrimination charge that 18 months ago might have remained an isolated incident is now substantially more likely to catalyze a formal organizing campaign within six months.

-----

## Repository Structure

```
nlrb-unionization-risk/
│
├── README.md # This file
│
├── data/
│ ├── raw/ # Raw NLRB CSVs (gitignored — too large)
│ ├── cleaned/
│ │ ├── combined_panel.csv # Full case-level dataset (266,608 × 22)
│ │ ├── ulp_panel.csv # ULP cases only — CA + CB (242,406 × 22)
│ │ └── rc_panel.csv # RC petitions only (24,202 × 22)
│ └── panel/
│ └── state_quarter_panel.csv # Aggregated NLRB panel (2,724 × 33)
│
├── scripts/
│ ├── 01_data_cleansing.py # Raw CSV → cleaned case-level datasets
│ ├── 02_panel_construction.py # Case data → state-quarter panel
│ ├── 03_analysis.py # Panel regression, survival, threshold, DiD
│ ├── 04_visualizations.py # All 9 figures (Apple + GT design system)
│ └── 06_employer_normalization.py # Optional: employer name normalization pipeline
│
├── figures/
│ ├── f1_kpi_summary.png # Executive summary — 6 key metrics
│ ├── a1_monthly_timeseries.png # Monthly CA + RC filings, 2013–2025
│ ├── a2_period_bars.png # RC volume & certification rate by regime
│ ├── b1_state_heatmap.png # Annual RC petitions, top 20 states
│ ├── b2_southern_heatmap.png # Southern states deep-dive (13 states)
│ ├── c1_theme_heatmap.png # Allegation theme prevalence by regime
│ ├── d1_survival_curves.png # Kaplan-Meier: CA → RC transition time
│ ├── d2_forest_plot.png # Cox PH hazard ratios — forest plot
│ └── d3_did_natural_experiment.png # Cemex DiD causal estimation
│
├── requirements.txt
├── .gitignore
└── LICENSE
```

-----

## Reproducing This Analysis

The cleaned data files (`combined_panel.csv`, `ulp_panel.csv`, `rc_panel.csv`, `state_quarter_panel.csv`) are not committed to the repository because the two largest files exceed GitHub’s 100MB single-file limit. **All cleaned files are regenerated from raw NLRB exports by running the pipeline below.** This is also the recommended way to replicate the analysis from scratch.

1. Download NLRB case data from [NLRB Advanced Search](https://www.nlrb.gov/search/case) — Cases & Decisions → Advanced → All Dates, export as CSV covering the period 2013–2025.
1. Place raw files in `data/raw/`.
1. Run the pipeline:

```bash
pip install -r requirements.txt

# Core pipeline (required)
python scripts/01_data_cleansing.py --input_dir data/raw --output_dir data/cleaned
python scripts/02_panel_construction.py --nlrb_path data/cleaned/combined_panel.csv --output_dir data/panel
python scripts/03_analysis.py --panel_path data/panel/state_quarter_panel.csv --case_path data/cleaned/combined_panel.csv
python scripts/04_visualizations.py --panel_path data/panel/state_quarter_panel.csv --case_path data/cleaned/combined_panel.csv --output_dir figures

# Optional: enhanced employer matching (improves CA↔RC overlap from 28.7% to 38.7%)
python scripts/06_employer_normalization.py --input data/cleaned/combined_panel.csv --output data/cleaned/combined_panel_normalized.csv --phase 1+2
```

After running, the four cleaned/aggregated CSVs and all nine figures will be regenerated locally. The full pipeline runs in approximately 5 minutes on a modern laptop.

-----

## How to Use This Data

**For ER/LR practitioners:** Start with `state_quarter_panel.csv`. Filter to your state(s) of interest. Track `ca_count` and `n_coercive_rules` quarter-over-quarter. Combined with chart B2 (Southern Industrial Belt), this lets you benchmark your facility’s region against documented organizing trajectories.

**For researchers:** The `combined_panel.csv` file supports case-level analysis. The `Allegations` field can be parsed with simple regex (55 structured phrases) to create binary features for any classification or prediction model.

**For executives:** The key numbers to brief leadership on are these: **248-day median** from first complaint to petition; **55.6% certification rate** in the current regulatory environment; **68% higher petition risk** after a discrimination charge (rising to 4.07× in the Cemex Era regime, with DiD evidence supporting a causal interpretation). These are the inputs to any workforce risk model.
