"""
services/cap_algorithm.py
=========================
AI CAP Preference Generator — core algorithm service.

Public API
----------
    generate_cap_preferences(student_profile: dict) -> list[dict]

The function is pure and stateless: it reads CSV files on every call,
applies all filtering / sorting logic, and returns an ordered list of
preference dicts ready to be rendered by cap_result.html.

No AI, no PDF export, no external HTTP calls.

Dataset files consumed (relative to project root)
--------------------------------------------------
    dataset/college_dataset.csv
        Columns: College_ID, Institute_Code, College_Name, Branch, CAP_Round,
                 Category, Gender, Seat_Type, Home_University,
                 Cutoff_Percentile, Cutoff_Rank, Annual_Fees, Intake
        Derived: City  (extracted from College_Name)

    dataset/branch_mapping.csv
        Columns: User_Preference, Mapped_Branch

    dataset/college_ranking.csv
        Columns: College_ID (C001..C050), College_Name,
                 AI_Ranking_Score, NIRF_Rank_Band, Reputation_Tier

student_profile keys (produced by cap_generator.collect_cap_form_data)
-----------------------------------------------------------------------
    cet_percentile          str | float   e.g. "92.5"
    category                str           "OPEN" | "OBC" | "SC" | "ST" | "NT1" | "NT2" | "VJ" | "EWS" | "SBC"
    gender                  str           "Male" | "Female"
    home_university         str           e.g. "Pune University (SPPU)"
    preferred_cities        list[str]     e.g. ["Pune", "Mumbai"]  (empty = Any City)
    preferred_branch_groups list[str]     ordered, e.g. ["Computer", "Electronics"]
    priority_style          str           "College First" | "Branch First"
    strategy                str           "Balanced" | "Aggressive" | "Safe"
    max_preferences         str | int     "50" | "75" | "100" | "No limit" | ""
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

# ── Dataset paths ────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_DATA = os.path.normpath(os.path.join(_HERE, "..", "dataset"))

COLLEGE_DATASET_PATH = os.path.join(_DATA, "college_dataset.csv")
BRANCH_MAPPING_PATH  = os.path.join(_DATA, "branch_mapping.csv")
COLLEGE_RANKING_PATH = os.path.join(_DATA, "college_ranking.csv")

# ── Classification thresholds ────────────────────────────────────────────────
# gap = student_percentile - row_cutoff
#
#   gap < 0           → student is below cutoff  → Dream
#   0 <= gap < 3      → just above cutoff         → Moderate
#   gap >= 3          → comfortably above         → Safe

DREAM_UPPER_THRESHOLD: float = 0.0
SAFE_GAP: float = 3.0

# ── Tier group order — Dream always first, Safe always last ──────────────────
_STATUS_ORDER: dict[str, int] = {"Dream": 0, "Moderate": 1, "Safe": 2}

# ── Strategy cutoff modifiers ─────────────────────────────────────────────────
# "Safe"       → only include rows where student is already above cutoff (gap >= 0)
# "Aggressive" → include all rows, even well-above-cutoff Dream rows
# "Balanced"   → default, no extra filter
STRATEGY_MIN_GAP: dict[str, float | None] = {
    "Safe":       0.0,    # must have gap >= 0  (no Dream rows)
    "Balanced":   None,   # no extra filter
    "Aggressive": None,   # no extra filter (include all, sort Dream rows high)
}

# ── Home-university preference bonus ─────────────────────────────────────────
HOME_UNIVERSITY_BONUS: float = 2.0

# ── Category fallback chain ───────────────────────────────────────────────────
# NT1 and NT2 are sub-categories of NT in the dataset.
CATEGORY_FALLBACK: dict[str, list[str]] = {
    "OPEN":  ["OPEN"],
    "OBC":   ["OBC",  "OPEN"],
    "SC":    ["SC",   "OPEN"],
    "ST":    ["ST",   "OPEN"],
    "NT":    ["NT1",  "NT2",  "OPEN"],
    "NT1":   ["NT1",  "OPEN"],
    "NT2":   ["NT2",  "OPEN"],
    "VJ":    ["VJ",   "OPEN"],
    "EWS":   ["EWS",  "OPEN"],
    "SBC":   ["SBC",  "OPEN"],
}

# ── Match-score weights ───────────────────────────────────────────────────────
MATCH_SCORE_WEIGHT_AI: float     = 0.5
MATCH_SCORE_WEIGHT_CUTOFF: float = 0.5
CUTOFF_PROXIMITY_DECAY: float    = 3.0

# ── Default max preferences ───────────────────────────────────────────────────
DEFAULT_MAX_PREFERENCES: int = 100

# ── Required columns ─────────────────────────────────────────────────────────
_REQUIRED_COLLEGE_COLS: list[str] = [
    "College_ID", "College_Name", "Branch",
    "Category", "Home_University", "Cutoff_Percentile", "Annual_Fees",
]
_REQUIRED_RANKING_COLS: list[str] = [
    "College_ID", "AI_Ranking_Score", "NIRF_Rank_Band", "Reputation_Tier",
]
_REQUIRED_BRANCH_MAP_COLS: list[str] = ["User_Preference", "Mapped_Branch"]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_required_columns(df: pd.DataFrame, required: list[str], source: str) -> None:
    """Raise ValueError listing every missing column."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"[CAP] {source} is missing required column(s): {missing}. "
            f"Actual columns: {df.columns.tolist()}"
        )


def _extract_city(college_name: str) -> str:
    """Extract city from College_Name (last comma-separated segment)."""
    if "," in college_name:
        return college_name.rsplit(",", 1)[-1].strip()
    parts = college_name.strip().split()
    return parts[-1] if parts else college_name


def _tier_from_reputation(tier_str: str) -> int:
    """
    Map Reputation_Tier string → integer tier (1 best).

    A+  → 1
    A   → 2
    B+  → 3
    B   → 4
    (anything else) → 5
    """
    mapping = {"A+": 1, "A": 2, "B+": 3, "B": 4}
    return mapping.get(str(tier_str).strip(), 5)


def _load_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all three CSVs, validate required columns, and return
    (colleges_df, branch_map_df, ranking_df).
    """
    # college_dataset.csv has comment lines starting with '#'
    colleges   = pd.read_csv(COLLEGE_DATASET_PATH, comment="#", skip_blank_lines=True)
    branch_map = pd.read_csv(BRANCH_MAPPING_PATH)
    ranking    = pd.read_csv(COLLEGE_RANKING_PATH)

    print(f"[CAP:algo] college_dataset.csv columns : {colleges.columns.tolist()}")
    print(f"[CAP:algo] college_ranking.csv columns : {ranking.columns.tolist()}")
    print(f"[CAP:algo] branch_mapping.csv columns  : {branch_map.columns.tolist()}")

    _check_required_columns(colleges,   _REQUIRED_COLLEGE_COLS,    "college_dataset.csv")
    _check_required_columns(ranking,    _REQUIRED_RANKING_COLS,    "college_ranking.csv")
    _check_required_columns(branch_map, _REQUIRED_BRANCH_MAP_COLS, "branch_mapping.csv")

    # Normalise string columns
    for col in ["College_Name", "Branch", "Category", "Home_University"]:
        if col in colleges.columns:
            colleges[col] = colleges[col].astype(str).str.strip()

    if "Category" in colleges.columns:
        colleges["Category"] = colleges["Category"].str.upper()
    if "Branch" in colleges.columns:
        colleges["Branch"] = colleges["Branch"].str.title()

    # Derive City from College_Name
    colleges["City"] = colleges["College_Name"].apply(_extract_city)

    # Coerce College_ID in dataset to int
    colleges["College_ID"] = pd.to_numeric(colleges["College_ID"], errors="coerce").fillna(0).astype(int)

    # Coerce Cutoff_Percentile to float
    colleges["Cutoff_Percentile"] = pd.to_numeric(colleges["Cutoff_Percentile"], errors="coerce")
    colleges = colleges.dropna(subset=["Cutoff_Percentile"]).reset_index(drop=True)

    # Normalise ranking branch_map string columns
    for col in ["User_Preference", "Mapped_Branch"]:
        if col in branch_map.columns:
            branch_map[col] = branch_map[col].astype(str).str.strip()

    # Convert ranking College_ID from "C001" → integer 1
    ranking["_numeric_id"] = (
        ranking["College_ID"]
        .astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    return colleges, branch_map, ranking


def _expand_branch_groups(
    branch_groups: list[str],
    branch_map_df: pd.DataFrame,
) -> list[str]:
    """
    Resolve a list of User_Preference group names to individual Mapped_Branch names.

    Returns a flat, deduplicated list preserving the group ordering.
    """
    seen: set[str] = set()
    result: list[str] = []

    for group in branch_groups:
        rows = branch_map_df[branch_map_df["User_Preference"] == group]["Mapped_Branch"].tolist()
        candidates = rows if rows else [group]

        for branch in candidates:
            if branch not in seen:
                seen.add(branch)
                result.append(branch)

    return result


def _resolve_max_preferences(raw: Any) -> int:
    """Convert the raw max_preferences field to an integer cap."""
    if raw in (None, "", "No limit"):
        return DEFAULT_MAX_PREFERENCES
    try:
        return int(raw)
    except (ValueError, TypeError):
        return DEFAULT_MAX_PREFERENCES


def _classify(percentile_gap: float) -> str:
    """
    Classify an admission row based on gap = student_percentile - cutoff.

    Negative gap  → Dream
    Small gap     → Moderate
    Large gap     → Safe
    """
    if percentile_gap < DREAM_UPPER_THRESHOLD:
        return "Dream"
    if percentile_gap < SAFE_GAP:
        return "Moderate"
    return "Safe"


def _compute_match_score(ai_score: float, percentile_gap: float) -> float:
    """Return a 0–100 match score blending college quality and cutoff proximity."""
    proximity = max(0.0, 100.0 - abs(percentile_gap) * CUTOFF_PROXIMITY_DECAY)
    score = MATCH_SCORE_WEIGHT_AI * ai_score + MATCH_SCORE_WEIGHT_CUTOFF * proximity
    return round(score, 1)


def _branch_priority(branch: str, ordered_branches: list[str]) -> int:
    """Return the index of *branch* in the ordered branch expansion list."""
    try:
        return ordered_branches.index(branch)
    except ValueError:
        return len(ordered_branches)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_cap_preferences(student_profile: dict) -> list[dict]:
    """
    Generate an ordered CAP preference list for a student.

    Parameters
    ----------
    student_profile : dict
        Produced by ``cap_generator.collect_cap_form_data()``.

    Returns
    -------
    list[dict]
        Each dict represents one preference row with keys:
            preference, college_id, college, city, home_university,
            branch, branch_group, category, cutoff, student_score,
            gap, status, match_score, tier, ai_score, annual_fees, intake
    """

    # ── 1. Parse and validate student profile ────────────────────────────────
    try:
        student_percentile = float(student_profile.get("cet_percentile", 0))
    except (ValueError, TypeError):
        student_percentile = 0.0

    category          = str(student_profile.get("category", "OPEN")).strip().upper()
    gender            = str(student_profile.get("gender", "")).strip()
    home_university   = str(student_profile.get("home_university", "")).strip()
    preferred_cities  = [c.strip() for c in student_profile.get("preferred_cities", []) if c.strip()]
    branch_groups     = [g.strip() for g in student_profile.get("preferred_branch_groups", []) if g.strip()]
    priority_style    = str(student_profile.get("priority_style", "College First")).strip()
    strategy          = str(student_profile.get("strategy", "Balanced")).strip()
    max_pref          = _resolve_max_preferences(student_profile.get("max_preferences"))

    # ── 2. Load datasets ──────────────────────────────────────────────────────
    colleges_df, branch_map_df, ranking_df = _load_datasets()
    print(f"[CAP:algo] Datasets loaded: {len(colleges_df)} college rows, "
          f"{len(ranking_df)} ranking rows, {len(branch_map_df)} branch-map rows")

    # ── 3. Expand branch groups → individual branch names ────────────────────
    expanded_branches: list[str] = (
        _expand_branch_groups(branch_groups, branch_map_df)
        if branch_groups
        else []
    )

    # Build branch_name → group_name lookup for output enrichment
    branch_to_group: dict[str, str] = {}
    for _, row in branch_map_df.iterrows():
        b = row["Mapped_Branch"]
        g = row["User_Preference"]
        if b not in branch_to_group:
            branch_to_group[b] = g

    # ── 4. Determine eligible categories ─────────────────────────────────────
    eligible_categories = CATEGORY_FALLBACK.get(category, [category, "OPEN"])

    # ── 5. City filter ────────────────────────────────────────────────────────
    working = colleges_df.copy()
    if preferred_cities:
        # Case-insensitive match against derived City column
        pref_lower = [c.lower() for c in preferred_cities]
        working = working[working["City"].str.lower().isin(pref_lower)]
    print(f"[CAP:algo] Rows after city filter     : {len(working)}"
          f"  (cities={preferred_cities or ['Any']})")

    # ── 6. Branch filter ──────────────────────────────────────────────────────
    if expanded_branches:
        exp_lower = [b.lower() for b in expanded_branches]
        working = working[working["Branch"].str.lower().isin(exp_lower)]
    print(f"[CAP:algo] Rows after branch filter   : {len(working)}"
          f"  (branches={expanded_branches or ['All']})")

    # ── 7. Category filter ────────────────────────────────────────────────────
    working = working[working["Category"].isin(eligible_categories)]
    print(f"[CAP:algo] Rows after category filter : {len(working)}"
          f"  (eligible={eligible_categories})")

    # ── 8. Strategy filter (Safe mode — exclude Dream rows) ──────────────────
    # Safe strategy: only keep rows where student is already above the cutoff.
    # Aggressive / Balanced: no pre-filter (classification happens after merge).
    if strategy == "Safe":
        working = working[
            working["Cutoff_Percentile"] <= student_percentile
        ]
        print(f"[CAP:algo] Rows after Safe strategy   : {len(working)}"
              f"  (cutoff <= {student_percentile})")

    # ── 9. Merge ranking data ─────────────────────────────────────────────────
    # Ranking CSV uses College_ID = C001..C050 → converted to integer _numeric_id
    # Dataset College_ID is already an integer.
    rank_cols = ranking_df[
        ["_numeric_id", "AI_Ranking_Score", "NIRF_Rank_Band", "Reputation_Tier"]
    ].drop_duplicates("_numeric_id")

    working = working.merge(
        rank_cols,
        left_on="College_ID",
        right_on="_numeric_id",
        how="left",
    )
    print(f"[CAP:algo] Rows after ranking merge   : {len(working)}")

    # Fill missing ranking data with conservative defaults
    working["AI_Ranking_Score"] = working["AI_Ranking_Score"].fillna(50.0).astype(float)
    working["Reputation_Tier"]  = working["Reputation_Tier"].fillna("B")
    working["_tier_int"]        = working["Reputation_Tier"].apply(_tier_from_reputation)

    # ── 10. Classification and match score ───────────────────────────────────
    working["gap"] = (
        student_percentile - working["Cutoff_Percentile"]
    ).round(2)

    working["status"] = working["gap"].apply(_classify)

    working["match_score"] = working.apply(
        lambda r: _compute_match_score(r["AI_Ranking_Score"], r["gap"]), axis=1
    )

    # ── 11. Home-university sort bonus ────────────────────────────────────────
    working["_uni_bonus"] = working["Home_University"].apply(
        lambda u: HOME_UNIVERSITY_BONUS if u == home_university else 0.0
    )
    working["_sort_ai"] = working["AI_Ranking_Score"] + working["_uni_bonus"]

    # ── 12. Branch priority index ─────────────────────────────────────────────
    working["_branch_priority"] = working["Branch"].apply(
        lambda b: _branch_priority(b, expanded_branches)
    )

    # ── 13. Always group Dream → Moderate → Safe, sort within each group ─────
    #
    # The output is always partitioned into three sections in this fixed order:
    #   Dream (status_order=0)  →  Moderate (status_order=1)  →  Safe (status_order=2)
    #
    # Within each group the ordering depends on priority_style:
    #
    #   College First → primary: college ranking (_tier_int asc, _sort_ai desc)
    #                   secondary: branch priority (_branch_priority asc)
    #                   tertiary: cutoff descending
    #
    #   Branch First  → primary: branch priority (_branch_priority asc)
    #                   secondary: college ranking (_tier_int asc, _sort_ai desc)
    #                   tertiary: cutoff descending
    #
    # For the "Aggressive" strategy an extra key (Cutoff_Percentile desc) is
    # prepended *within* each group so that the most-selective rows surface
    # first — the Dream/Moderate/Safe grouping is still always respected.

    working["_status_order"] = working["status"].map(_STATUS_ORDER).fillna(1).astype(int)

    if strategy == "Aggressive":
        # Aggressive: within every group float highest-cutoff rows first,
        # then apply the normal College First / Branch First sub-ordering.
        if priority_style == "Branch First":
            working = working.sort_values(
                by=["_status_order", "_branch_priority", "Cutoff_Percentile", "_tier_int", "_sort_ai"],
                ascending=[True,          True,              False,              True,        False],
            )
        else:  # College First (default)
            working = working.sort_values(
                by=["_status_order", "Cutoff_Percentile", "_tier_int", "_sort_ai", "_branch_priority"],
                ascending=[True,          False,              True,       False,     True],
            )
        print("[CAP:algo] Aggressive strategy applied — rows sorted by highest cutoff within each group")
    elif priority_style == "Branch First":
        working = working.sort_values(
            by=["_status_order", "_branch_priority", "_tier_int", "_sort_ai", "Cutoff_Percentile"],
            ascending=[True,          True,              True,       False,      False],
        )
    else:  # College First (default)
        working = working.sort_values(
            by=["_status_order", "_tier_int", "_sort_ai", "_branch_priority", "Cutoff_Percentile"],
            ascending=[True,          True,       False,     True,              False],
        )

    # ── 14. (no separate Aggressive re-sort — handled inside step 13) ─────────

    # ── 15. Apply max_preferences cap ────────────────────────────────────────
    print(f"[CAP:algo] Rows before cap            : {len(working)}  (cap={max_pref})")
    working = working.head(max_pref)

    # ── 16. Build output rows ─────────────────────────────────────────────────
    preferences: list[dict] = []
    for rank, (_, row) in enumerate(working.iterrows(), start=1):
        branch_name = row["Branch"]
        preferences.append(
            {
                "preference":    rank,
                "college_id":    int(row["College_ID"]),
                "college":       row["College_Name"],
                "city":          row["City"],
                "home_university": row["Home_University"],
                "branch":        branch_name,
                "branch_group":  branch_to_group.get(branch_name, ""),
                "category":      row["Category"],
                "cutoff":        float(row["Cutoff_Percentile"]),
                "student_score": student_percentile,
                "gap":           float(row["gap"]),
                "status":        row["status"],
                "match_score":   float(row["match_score"]),
                "tier":          int(row["_tier_int"]),
                "ai_score":      float(row["AI_Ranking_Score"]),
                "annual_fees":   int(row["Annual_Fees"]) if pd.notna(row["Annual_Fees"]) else 0,
                "intake":        int(row["Intake"])      if pd.notna(row["Intake"])      else 0,
            }
        )

    print(f"[CAP:algo] Rows returned              : {len(preferences)}")
    return preferences
