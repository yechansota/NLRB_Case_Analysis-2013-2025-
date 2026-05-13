"""
06_employer_normalization.py
============================
Employer name normalization pipeline for NLRB Case Name field.

Goal: Improve case-to-employer matching accuracy beyond raw Case Name
      string matching, increasing the detected CA → RC employer overlap
      rate above the baseline 28.6%.

Pipeline:
  Phase 1 — Hard-coded normalization (deterministic, transparent)
  Phase 2 — Known-employer canonical lookup (Top US employers)
  Phase 3 — Fuzzy matching with TF-IDF + cosine similarity (optional)

Recommended approach:
  Run Phase 1 + 2 first (gives ~80% of the benefit with full transparency).
  Phase 3 is optional and requires manual validation of matched clusters.

Input : data/cleaned/combined_panel.csv
Output: data/cleaned/combined_panel_normalized.csv

Usage:
    python 06_employer_normalization.py \
        --input  data/cleaned/combined_panel.csv \
        --output data/cleaned/combined_panel_normalized.csv \
        --phase  1+2          # or "1+2+3" to include fuzzy matching
"""

import argparse
import os
import re
from collections import defaultdict

import pandas as pd
import numpy as np


# ============================================================
# PHASE 1 — Hard-coded normalization rules
# ============================================================

# Corporate suffixes to strip
SUFFIX_PATTERNS = [
    r',?\s*INCORPORATED\s*\.?$',
    r',?\s*INC\s*\.?$',
    r',?\s*LLC\s*\.?$',
    r',?\s*L\.?\s*L\.?\s*C\.?$',
    r',?\s*LTD\s*\.?$',
    r',?\s*LIMITED\s*\.?$',
    r',?\s*CORP\s*\.?$',
    r',?\s*CORPORATION\s*\.?$',
    r',?\s*COMPANY\s*\.?$',
    r',?\s*CO\s*\.?$',
    r',?\s*L\.?P\.?$',
    r',?\s*LP\s*\.?$',
    r',?\s*PLC\s*\.?$',
    r',?\s*HOLDINGS?\s*\.?$',
    r',?\s*GROUP\s*\.?$',
    r',?\s*ENTERPRISES?\s*\.?$',
    r',?\s*PARTNERS?\s*\.?$',
    r',?\s*LLP\s*\.?$',
    r',?\s*PA\s*\.?$',
    r',?\s*PC\s*\.?$',
    r',?\s*USA\s*\.?$',
    r',?\s*US\s*\.?$',
    r',?\s*N\.?A\.?$',
]

# Common abbreviations to expand for consistent matching
ABBREVIATIONS = {
    r'\bMFG\b':           'MANUFACTURING',
    r'\bMFRG\b':          'MANUFACTURING',
    r'\bDIST\b':          'DISTRIBUTION',
    r'\bDISTRIB\b':       'DISTRIBUTION',
    r'\bINTL\b':          'INTERNATIONAL',
    r'\bINT\'?L\b':       'INTERNATIONAL',
    r'\bASSN\b':          'ASSOCIATION',
    r'\bASSOC\b':         'ASSOCIATION',
    r'\bSVCS\b':          'SERVICES',
    r'\bSVC\b':           'SERVICE',
    r'\bMGMT\b':          'MANAGEMENT',
    r'\bENT\b':           'ENTERPRISES',
    r'\bIND\b':           'INDUSTRIES',
    r'\bHLDGS\b':         'HOLDINGS',
    r'\bHLDG\b':          'HOLDING',
    r'\bMFRS\b':          'MANUFACTURERS',
    r'\bSYS\b':           'SYSTEMS',
    r'\bTECH\b':          'TECHNOLOGY',
    r'\bSOL\b':           'SOLUTIONS',
    r'\bGRP\b':           'GROUP',
    r'\bN\s+AMER(ICA)?\b':'NORTH AMERICA',
    r'\bNORTH AM\b':      'NORTH AMERICA',
    r'\bAMER\b':          'AMERICA',
    r'\bAMERICAN\b':      'AMERICA',
    r'\bNATL\b':          'NATIONAL',
    r'\bRESTAURANT\b':    'REST',
    r'\bRESTAURANTS\b':   'REST',
}

# Facility identifier patterns to strip (store numbers, location markers)
FACILITY_PATTERNS = [
    r'#\s*\d+',
    r'\bSTORE\s+(NO\.?|NUMBER|#)?\s*\d+',
    r'\bFACILITY\s+\d+',
    r'\bUNIT\s+\d+',
    r'\bLOCATION\s+\d+',
    r'\bBRANCH\s+\d+',
    r'\bPLANT\s+\d+',
    r'\bDIVISION\s+\d+',
    r'\bDIV\s+\d+',
    r'\b\d{5}(-\d{4})?\b',          # ZIP codes
    r'\(\s*[A-Z]{2}\s*\)\s*$',      # trailing state code in parens
]


def normalize_phase1(name: str) -> str:
    """Phase 1 — deterministic normalization."""
    if not isinstance(name, str) or not name.strip():
        return ""

    # Uppercase and strip
    n = name.upper().strip()

    # Remove parenthetical content (often nicknames or DBA references)
    n = re.sub(r'\([^)]*\)', ' ', n)

    # Strip facility identifiers FIRST (before they tangle with other rules)
    for pattern in FACILITY_PATTERNS:
        n = re.sub(pattern, ' ', n, flags=re.IGNORECASE)

    # Strip corporate suffixes (iterate — some companies have stacked suffixes)
    for _ in range(3):
        for pattern in SUFFIX_PATTERNS:
            n = re.sub(pattern, '', n, flags=re.IGNORECASE)
        n = n.strip().rstrip(',').strip()

    # Expand abbreviations
    for abbr, full in ABBREVIATIONS.items():
        n = re.sub(abbr, full, n, flags=re.IGNORECASE)

    # Punctuation → space
    n = re.sub(r'[,\.\'"\-/&]', ' ', n)

    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()

    return n


# ============================================================
# PHASE 2 — Known-employer canonical lookup
# ============================================================

# Top US employers by NLRB filing volume + general labor-market presence.
# Format: canonical_name → list of variation patterns (substring match after Phase 1)
KNOWN_EMPLOYERS = {
    # Retail
    "WALMART":          ["WALMART", "WAL MART", "WAL-MART", "WALMART STORES",
                         "WALMART SUPERCENTER", "WALMART NEIGHBORHOOD",
                         "SAMS CLUB", "SAM S CLUB"],
    "AMAZON":           ["AMAZON", "AMAZON COM", "AMAZON LOGISTICS",
                         "AMAZON SERVICES", "AMAZON FULFILLMENT", "AMZN"],
    "TARGET":           ["TARGET", "TARGET STORES", "TARGET BRANDS"],
    "COSTCO":           ["COSTCO", "COSTCO WHOLESALE"],
    "KROGER":           ["KROGER", "THE KROGER"],
    "HOME DEPOT":       ["HOME DEPOT", "THE HOME DEPOT", "HOMEDEPOT"],
    "LOWES":            ["LOWES", "LOWE S", "LOWES HOME"],
    "CVS":              ["CVS", "CVS HEALTH", "CVS PHARMACY", "CVS CAREMARK"],
    "WALGREENS":        ["WALGREENS", "WALGREEN", "WAG"],
    "ALBERTSONS":       ["ALBERTSONS", "ALBERTSON S", "SAFEWAY"],
    "BEST BUY":         ["BEST BUY", "BESTBUY"],
    "MACYS":            ["MACYS", "MACY S"],
    "NORDSTROM":        ["NORDSTROM"],
    "DOLLAR GENERAL":   ["DOLLAR GENERAL", "DG MARKET"],
    "DOLLAR TREE":      ["DOLLAR TREE", "FAMILY DOLLAR"],
    "TRADER JOES":      ["TRADER JOE S", "TRADER JOES"],
    "WHOLE FOODS":      ["WHOLE FOODS", "WHOLEFOODS"],
    "PUBLIX":           ["PUBLIX", "PUBLIX SUPER MARKETS"],
    "GIANT EAGLE":      ["GIANT EAGLE"],
    "WEGMANS":          ["WEGMANS"],
    "REI":              ["REI", "RECREATIONAL EQUIPMENT"],

    # Food service
    "STARBUCKS":        ["STARBUCKS", "STARBUCKS COFFEE", "STARBUCKS CORPORATION"],
    "MCDONALDS":        ["MCDONALDS", "MCDONALD S", "MCDONALDS USA"],
    "CHIPOTLE":         ["CHIPOTLE", "CHIPOTLE MEXICAN"],
    "DUNKIN":           ["DUNKIN", "DUNKIN BRANDS", "DUNKIN DONUTS"],
    "SUBWAY":           ["SUBWAY"],
    "BURGER KING":      ["BURGER KING"],
    "WENDYS":           ["WENDYS", "WENDY S"],
    "TACO BELL":        ["TACO BELL"],
    "KFC":              ["KFC", "KENTUCKY FRIED"],
    "PIZZA HUT":        ["PIZZA HUT"],
    "DOMINOS":          ["DOMINOS", "DOMINO S"],
    "PANERA":           ["PANERA", "PANERA BREAD"],
    "CHIPOTLE":         ["CHIPOTLE"],
    "FIVE GUYS":        ["FIVE GUYS"],
    "SHAKE SHACK":      ["SHAKE SHACK"],
    "OUTBACK STEAKHOUSE":["OUTBACK STEAKHOUSE"],
    "DARDEN RESTAURANTS":["DARDEN", "OLIVE GARDEN", "LONGHORN STEAKHOUSE"],

    # Logistics & Delivery
    "UPS":              ["UPS", "UNITED PARCEL", "UNITED PARCEL SERVICE"],
    "FEDEX":            ["FEDEX", "FEDERAL EXPRESS", "FED EX"],
    "DHL":              ["DHL", "DHL EXPRESS"],
    "USPS":             ["USPS", "UNITED STATES POSTAL", "POSTAL SERVICE"],
    "XPO LOGISTICS":    ["XPO", "XPO LOGISTICS"],
    "OLD DOMINION":     ["OLD DOMINION FREIGHT"],
    "YRC FREIGHT":      ["YRC FREIGHT", "YELLOW FREIGHT"],
    "ESTES EXPRESS":    ["ESTES EXPRESS"],
    "DOORDASH":         ["DOORDASH", "DASHER"],
    "UBER":             ["UBER", "UBER TECHNOLOGIES", "UBER EATS"],
    "LYFT":             ["LYFT"],
    "INSTACART":        ["INSTACART", "MAPLEBEAR"],

    # Tech
    "GOOGLE":           ["GOOGLE", "ALPHABET"],
    "MICROSOFT":        ["MICROSOFT", "MSFT"],
    "META":             ["META", "FACEBOOK", "INSTAGRAM"],
    "APPLE":            ["APPLE INC", "APPLE COMPUTER", "APPLE RETAIL"],
    "TESLA":            ["TESLA", "TESLA MOTORS"],
    "INTEL":            ["INTEL"],
    "ORACLE":           ["ORACLE"],
    "SALESFORCE":       ["SALESFORCE"],
    "IBM":              ["IBM", "INTERNATIONAL BUSINESS MACHINES"],
    "HP":               ["HEWLETT PACKARD", "HP INC", "HEWLETT-PACKARD"],
    "DELL":             ["DELL TECHNOLOGIES", "DELL INC", "DELL COMPUTER"],
    "CISCO":            ["CISCO SYSTEMS", "CISCO"],

    # Auto manufacturers
    "GENERAL MOTORS":   ["GENERAL MOTORS", "GM ", "GMC"],
    "FORD":             ["FORD MOTOR", "FORD MFG", "FORD MANUFACTURING"],
    "STELLANTIS":       ["STELLANTIS", "FCA US", "CHRYSLER", "FIAT CHRYSLER",
                         "JEEP", "DODGE", "RAM TRUCKS"],
    "TOYOTA":           ["TOYOTA MOTOR", "TOYOTA MANUFACTURING", "TOYOTA NORTH AMERICA"],
    "HONDA":            ["HONDA OF AMERICA", "HONDA MANUFACTURING", "HONDA MOTOR"],
    "NISSAN":           ["NISSAN NORTH AMERICA", "NISSAN MOTOR"],
    "HYUNDAI":          ["HYUNDAI MOTOR", "HYUNDAI MANUFACTURING", "HYUNDAI MOTORS"],
    "KIA":              ["KIA MOTORS", "KIA MANUFACTURING", "KIA AMERICA"],
    "VOLKSWAGEN":       ["VOLKSWAGEN", "VW GROUP", "VOLKSWAGEN GROUP"],
    "BMW":              ["BMW MANUFACTURING", "BMW NORTH AMERICA", "BMW OF NORTH AMERICA"],
    "MERCEDES":         ["MERCEDES BENZ", "MERCEDES-BENZ", "MBUSI"],
    "VOLVO":            ["VOLVO TRUCKS", "VOLVO GROUP", "VOLVO CARS"],
    "RIVIAN":           ["RIVIAN", "RIVIAN AUTOMOTIVE"],
    "LUCID":            ["LUCID MOTORS", "LUCID GROUP"],

    # Manufacturing/industrial
    "BOEING":           ["BOEING", "THE BOEING"],
    "GE":               ["GENERAL ELECTRIC", "GE AVIATION", "GE APPLIANCES"],
    "CATERPILLAR":      ["CATERPILLAR"],
    "JOHN DEERE":       ["JOHN DEERE", "DEERE COMPANY"],
    "3M":               ["3M COMPANY", "MINNESOTA MINING"],
    "LOCKHEED MARTIN":  ["LOCKHEED MARTIN", "LOCKHEED"],
    "RAYTHEON":         ["RAYTHEON", "RTX CORPORATION"],
    "NORTHROP GRUMMAN": ["NORTHROP GRUMMAN", "NORTHROP"],

    # Healthcare
    "HCA HEALTHCARE":   ["HCA HEALTHCARE", "HCA INC", "HOSPITAL CORPORATION"],
    "KAISER":           ["KAISER PERMANENTE", "KAISER FOUNDATION"],
    "TENET HEALTHCARE": ["TENET HEALTHCARE", "TENET HEALTH"],
    "COMMUNITY HEALTH": ["COMMUNITY HEALTH SYSTEMS", "CHS"],
    "ASCENSION":        ["ASCENSION HEALTH"],
    "CVS HEALTH":       ["CVS HEALTH", "AETNA"],
    "ANTHEM":           ["ANTHEM", "ELEVANCE"],
    "UNITED HEALTHCARE":["UNITED HEALTHCARE", "UNITEDHEALTH"],

    # Hotels & Hospitality
    "MARRIOTT":         ["MARRIOTT INTERNATIONAL", "MARRIOTT HOTELS"],
    "HILTON":           ["HILTON HOTELS", "HILTON WORLDWIDE"],
    "HYATT":            ["HYATT HOTELS", "HYATT REGENCY"],
    "MGM RESORTS":      ["MGM RESORTS", "MGM GRAND"],
    "CAESARS":          ["CAESARS ENTERTAINMENT", "CAESARS PALACE"],
    "WYNN RESORTS":     ["WYNN RESORTS", "WYNN LAS VEGAS"],

    # Media & Entertainment
    "DISNEY":           ["WALT DISNEY", "DISNEY"],
    "WARNER BROS":      ["WARNER BROS", "WARNER MEDIA", "WARNERMEDIA",
                         "WARNER BROTHERS"],
    "NETFLIX":          ["NETFLIX"],
    "PARAMOUNT":        ["PARAMOUNT GLOBAL", "VIACOMCBS", "VIACOM CBS",
                         "PARAMOUNT PICTURES"],
    "NBCUNIVERSAL":     ["NBCUNIVERSAL", "NBC UNIVERSAL", "COMCAST NBCU"],
    "COMCAST":          ["COMCAST CORPORATION", "COMCAST CABLE"],

    # Telecom
    "AT&T":             ["AT T", "AT AND T", "ATT INC", "AT&T"],
    "VERIZON":          ["VERIZON COMMUNICATIONS", "VERIZON WIRELESS"],
    "T-MOBILE":         ["T MOBILE", "T-MOBILE", "TMOBILE"],
    "CHARTER":          ["CHARTER COMMUNICATIONS", "SPECTRUM"],

    # Financial
    "JPMORGAN":         ["JPMORGAN CHASE", "JP MORGAN", "CHASE BANK"],
    "BANK OF AMERICA":  ["BANK OF AMERICA"],
    "WELLS FARGO":      ["WELLS FARGO"],
    "CITIGROUP":        ["CITIGROUP", "CITIBANK", "CITI INC"],
    "GOLDMAN SACHS":    ["GOLDMAN SACHS"],
    "MORGAN STANLEY":   ["MORGAN STANLEY"],

    # Airlines
    "AMERICAN AIRLINES":["AMERICAN AIRLINES"],
    "DELTA":            ["DELTA AIR LINES", "DELTA AIRLINES"],
    "UNITED AIRLINES":  ["UNITED AIRLINES", "UNITED CONTINENTAL"],
    "SOUTHWEST":        ["SOUTHWEST AIRLINES"],
    "JETBLUE":          ["JETBLUE AIRWAYS", "JET BLUE"],
    "ALASKA AIRLINES":  ["ALASKA AIRLINES", "ALASKA AIR"],
    "SPIRIT AIRLINES":  ["SPIRIT AIRLINES"],
    "FRONTIER AIRLINES":["FRONTIER AIRLINES"],

    # Energy
    "EXXONMOBIL":       ["EXXON", "EXXONMOBIL", "EXXON MOBIL", "MOBIL"],
    "CHEVRON":          ["CHEVRON"],
    "BP":               ["BP AMERICA", "BP PRODUCTS", "BRITISH PETROLEUM"],
    "SHELL":            ["SHELL OIL", "ROYAL DUTCH SHELL", "SHELL USA"],

    # Construction/Building
    "DR HORTON":        ["D R HORTON", "DR HORTON"],
    "LENNAR":           ["LENNAR"],
    "PULTE":            ["PULTE GROUP", "PULTEHOMES"],
}


def normalize_phase2(phase1_name: str) -> str | None:
    """Phase 2 — match against known employer dictionary."""
    if not phase1_name:
        return None
    for canonical, variations in KNOWN_EMPLOYERS.items():
        for variant in variations:
            # Match if the variant appears as a substring (word-boundary)
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, phase1_name):
                return canonical
    return None


# ============================================================
# PHASE 3 — TF-IDF fuzzy clustering (optional)
# ============================================================
def normalize_phase3(names: list[str], threshold: float = 0.85) -> dict:
    """
    Phase 3 — TF-IDF + cosine similarity clustering.

    NOTE: This is computationally expensive (O(n²)) and produces
    fuzzy matches that should be MANUALLY VALIDATED before use.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        print("  scikit-learn required for Phase 3. Skipping.")
        return {}

    unique_names = sorted(set(n for n in names if n))
    print(f"  Phase 3: clustering {len(unique_names):,} unique normalized names...")

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 3))
    tfidf = vectorizer.fit_transform(unique_names)

    # For very large name sets, similarity matrix is impractical.
    # Use approximate clustering — match each name to its highest-similarity
    # peer above threshold using sparse dot product.
    clusters = {}
    cluster_id = 0
    name_to_cluster = {}

    # Process in batches to control memory
    batch_size = 1000
    for start in range(0, len(unique_names), batch_size):
        end = min(start + batch_size, len(unique_names))
        sim_batch = cosine_similarity(tfidf[start:end], tfidf)

        for i_local, i_global in enumerate(range(start, end)):
            if unique_names[i_global] in name_to_cluster:
                continue
            # Find all peers above threshold
            similar_idx = np.where(sim_batch[i_local] >= threshold)[0]
            if len(similar_idx) == 0:
                continue

            # Assign all similar names to the same cluster
            cluster_id += 1
            for j in similar_idx:
                name_j = unique_names[j]
                if name_j not in name_to_cluster:
                    name_to_cluster[name_j] = f"FUZZY_CLUSTER_{cluster_id:06d}"

    return name_to_cluster


# ============================================================
# Main pipeline
# ============================================================
def run_pipeline(df: pd.DataFrame, phases: str = "1+2") -> pd.DataFrame:
    """Execute normalization phases on the case dataframe."""
    df = df.copy()

    print("\n[Phase 1] Hard-coded normalization...")
    df["name_phase1"] = df["Case Name"].apply(normalize_phase1)
    print(f"  Original unique names : {df['Case Name'].nunique():,}")
    print(f"  After Phase 1         : {df['name_phase1'].nunique():,}")

    if "2" in phases:
        print("\n[Phase 2] Known-employer canonical lookup...")
        df["name_canonical"] = df["name_phase1"].apply(normalize_phase2)
        matched = df["name_canonical"].notna().sum()
        print(f"  Cases matched to known employers : {matched:,} "
              f"({matched/len(df)*100:.1f}%)")
        print(f"  Unique known employers matched   : "
              f"{df['name_canonical'].dropna().nunique():,}")

        # Fill name_canonical with name_phase1 for unmatched cases
        df["name_canonical"] = df["name_canonical"].fillna(df["name_phase1"])
    else:
        df["name_canonical"] = df["name_phase1"]

    if "3" in phases:
        print("\n[Phase 3] TF-IDF fuzzy clustering...")
        # Apply only to cases not matched by Phase 2
        unmatched = df[df["name_canonical"] == df["name_phase1"]]
        unmatched_names = unmatched["name_phase1"].dropna().unique().tolist()
        cluster_map = normalize_phase3(unmatched_names, threshold=0.85)
        df["name_canonical"] = df["name_phase1"].map(cluster_map).fillna(
            df["name_canonical"]
        )
        print(f"  Cases assigned to fuzzy clusters : {len(cluster_map):,}")

    # Build employer key combining canonical name + state
    df["employer_key_normalized"] = (
        df["name_canonical"].astype(str) + "|" + df["state"].astype(str)
    )
    df["employer_key_raw"] = (
        df["Case Name"].str.strip().str.upper() + "|" + df["state"].astype(str)
    )

    print(f"\n[Final] Employer keys")
    print(f"  Raw employer keys        : {df['employer_key_raw'].nunique():,}")
    print(f"  Normalized employer keys : {df['employer_key_normalized'].nunique():,}")
    print(f"  Reduction                : "
          f"{(1 - df['employer_key_normalized'].nunique() / df['employer_key_raw'].nunique())*100:.1f}%")

    return df


def evaluate_overlap(df: pd.DataFrame) -> None:
    """Compute CA → RC employer overlap before and after normalization."""
    print(f"\n{'='*60}")
    print("CA ↔ RC EMPLOYER OVERLAP")
    print(f"{'='*60}")

    ca = df[df["case_subtype"] == "CA"]
    rc = df[df["case_subtype"] == "RC"]

    # Raw overlap
    ca_raw = set(ca["employer_key_raw"].dropna())
    rc_raw = set(rc["employer_key_raw"].dropna())
    raw_overlap = ca_raw & rc_raw
    raw_pct = len(raw_overlap) / len(rc_raw) * 100 if rc_raw else 0
    print(f"\nRAW (string match):")
    print(f"  CA employers: {len(ca_raw):,}")
    print(f"  RC employers: {len(rc_raw):,}")
    print(f"  Overlap     : {len(raw_overlap):,} ({raw_pct:.1f}% of RC employers)")

    # Normalized overlap
    ca_norm = set(ca["employer_key_normalized"].dropna())
    rc_norm = set(rc["employer_key_normalized"].dropna())
    norm_overlap = ca_norm & rc_norm
    norm_pct = len(norm_overlap) / len(rc_norm) * 100 if rc_norm else 0
    print(f"\nNORMALIZED:")
    print(f"  CA employers: {len(ca_norm):,}")
    print(f"  RC employers: {len(rc_norm):,}")
    print(f"  Overlap     : {len(norm_overlap):,} ({norm_pct:.1f}% of RC employers)")

    print(f"\nIMPROVEMENT: {norm_pct - raw_pct:+.1f} percentage points")


def main():
    parser = argparse.ArgumentParser(
        description="NLRB employer name normalization pipeline"
    )
    parser.add_argument("--input",  default="data/cleaned/combined_panel.csv")
    parser.add_argument("--output", default="data/cleaned/combined_panel_normalized.csv")
    parser.add_argument(
        "--phase",
        default="1+2",
        choices=["1", "1+2", "1+2+3"],
        help="Which normalization phases to run (default: 1+2)",
    )
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    df = pd.read_csv(args.input, low_memory=False)
    print(f"  {len(df):,} cases loaded")

    df = run_pipeline(df, phases=args.phase)
    evaluate_overlap(df)

    print(f"\nSaving to {args.output}...")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"  Saved {len(df):,} rows × {df.shape[1]} columns")


if __name__ == "__main__":
    main()
