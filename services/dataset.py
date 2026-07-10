"""
services/dataset.py
====================
College Dataset Service
-----------------------
Single data-access layer for the college CSV dataset.
All other services should import from here — never read the CSV directly.

Cached after the first load via functools.lru_cache so the file is
read only once per process lifetime.

Public API
----------
    load_dataset()              → pd.DataFrame   (full normalised table)
    get_all_colleges()          → list[dict]      (every row as a dict)
    filter_colleges(...)        → list[dict]      (filtered rows)
    search_college(query)       → list[dict]      (name / city substring match)
    get_available_branches()    → list[str]       (sorted unique branch names)
    get_available_cities()      → list[str]       (sorted unique city names)
    get_available_universities()→ list[str]       (sorted unique home universities)
    get_college_by_id(id)       → dict | None     (single record by College_ID)

Dataset columns (production schema)
------------------------------------
    College_ID, Institute_Code, College_Name, Branch, CAP_Round,
    Category, Gender, Seat_Type, Home_University,
    Cutoff_Percentile, Cutoff_Rank, Annual_Fees, Intake
    + derived: City  (extracted from College_Name)

NOTE: The CSV file starts with 3 comment lines (# ...) and one blank line
before the actual header row.  We use comment='#', skip_blank_lines=True.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default path — resolved relative to this file so it is CWD-independent
# ---------------------------------------------------------------------------
_DEFAULT_DATASET_PATH: str = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "dataset", "college_dataset.csv")
)

# ---------------------------------------------------------------------------
# Column name constants — centralised so a CSV rename only needs one edit
# ---------------------------------------------------------------------------
COL_ID        = "College_ID"
COL_INST_CODE = "Institute_Code"
COL_NAME      = "College_Name"
COL_BRANCH    = "Branch"
COL_CAP_ROUND = "CAP_Round"
COL_CATEGORY  = "Category"
COL_GENDER    = "Gender"
COL_SEAT_TYPE = "Seat_Type"
COL_HOME_UNIV = "Home_University"
COL_CUTOFF    = "Cutoff_Percentile"
COL_RANK      = "Cutoff_Rank"
COL_FEES      = "Annual_Fees"
COL_INTAKE    = "Intake"

# Derived column (not in CSV — computed during normalisation)
COL_CITY = "City"

REQUIRED_COLUMNS: list[str] = [
    COL_ID, COL_NAME, COL_BRANCH, COL_CATEGORY,
    COL_CUTOFF, COL_FEES, COL_HOME_UNIV,
]

# ---------------------------------------------------------------------------
# Backward-compatible aliases — keep old code importing from here working.
# These names no longer exist in the production CSV; access to the columns
# they reference will return empty/None values at query time.
# ---------------------------------------------------------------------------
COL_CITY      = "City"          # Derived — still present (computed from College_Name)
COL_DISTRICT  = "district"      # Removed — not in production CSV
COL_UNIV      = "university"    # Removed — use COL_HOME_UNIV instead
COL_TYPE      = "type"          # Removed — not in production CSV
COL_NAAC      = "naac_grade"    # Removed
COL_NBA       = "nba_accredited"# Removed
COL_PLACEMENT = "avg_placement_lpa"  # Removed
COL_ESTD      = "established_year"   # Removed


# ===========================================================================
# Core loader — cached
# ===========================================================================

@lru_cache(maxsize=1)
def load_dataset(path: str | None = None) -> pd.DataFrame:
    """
    Load the college dataset CSV into a normalised pandas DataFrame.

    The CSV has 3 comment lines (# ...) and one blank line before the header.
    We skip them using comment='#' and skip_blank_lines=True.

    The result is cached after the first successful call.

    Returns
    -------
    pd.DataFrame
        All columns normalised; includes a derived ``City`` column
        extracted from the last comma-segment of ``College_Name``.
        An empty DataFrame is returned on any load failure.
    """
    csv_path = path or _DEFAULT_DATASET_PATH

    if not os.path.isfile(csv_path):
        logger.warning("Dataset not found at '%s' — returning empty DataFrame.", csv_path)
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            csv_path,
            dtype=str,
            comment="#",
            skip_blank_lines=True,
        )
        logger.info("Raw dataset loaded: %d rows from '%s'", len(df), csv_path)
    except Exception as exc:
        logger.error("Failed to read CSV at '%s': %s", csv_path, exc)
        return pd.DataFrame()

    df = _normalise(df)
    logger.info("Dataset ready: %d rows × %d columns", len(df), len(df.columns))
    return df


def _extract_city(college_name: str) -> str:
    """
    Derive city from the College_Name field.

    Convention: city is the last comma-separated token.
    e.g.  "COEP Technological University, Pune"   → "Pune"
          "VJTI, Mumbai"                           → "Mumbai"
          "VNIT Nagpur"                            → "Nagpur"  (no comma → last word)
    """
    if "," in college_name:
        return college_name.rsplit(",", 1)[-1].strip()
    # No comma — last whitespace-delimited word (city often appended as suffix)
    parts = college_name.strip().split()
    return parts[-1] if parts else college_name


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and type-coerce the raw DataFrame.

    - Strip leading/trailing whitespace from every string column.
    - Normalise Category to uppercase.
    - Normalise Branch to title case.
    - Derive City from College_Name.
    - Coerce Cutoff_Percentile to float; drop rows with missing cutoff.
    - Coerce Annual_Fees and Intake to int.
    """
    # Strip all string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Normalise categoricals
    if COL_CATEGORY in df.columns:
        df[COL_CATEGORY] = df[COL_CATEGORY].str.upper()
    if COL_BRANCH in df.columns:
        df[COL_BRANCH] = df[COL_BRANCH].str.title()
    if COL_GENDER in df.columns:
        df[COL_GENDER] = df[COL_GENDER].str.title()

    # Derive City
    if COL_NAME in df.columns:
        df[COL_CITY] = df[COL_NAME].apply(_extract_city)

    # Coerce numerics
    for col, kind in [
        (COL_CUTOFF, "float"),
        (COL_FEES,   "int"),
        (COL_INTAKE, "int"),
        (COL_ID,     "int"),
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if kind == "int":
                df[col] = df[col].fillna(0).astype(int)

    # Drop rows where cutoff is missing — unusable for ranking
    if COL_CUTOFF in df.columns:
        before = len(df)
        df = df.dropna(subset=[COL_CUTOFF]).reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            logger.warning("Dropped %d rows with missing Cutoff_Percentile.", dropped)

    return df


# ===========================================================================
# Query helpers
# ===========================================================================

def get_all_colleges() -> list[dict[str, Any]]:
    """Return every row in the dataset as a list of dicts."""
    return load_dataset().to_dict(orient="records")


def filter_colleges(
    *,
    category: str | None = None,
    branch: str | None = None,
    city: str | None = None,
    max_cutoff: float | None = None,
    min_cutoff: float | None = None,
) -> list[dict[str, Any]]:
    """
    Return rows matching all supplied (non-None) criteria.

    Parameters
    ----------
    category    : str, optional  e.g. "OPEN", "OBC" (case-insensitive)
    branch      : str, optional  e.g. "Computer Engineering" (case-insensitive)
    city        : str, optional  e.g. "Pune" (case-insensitive)
    max_cutoff  : float, optional  Keep rows where Cutoff_Percentile <= max_cutoff
    min_cutoff  : float, optional  Keep rows where Cutoff_Percentile >= min_cutoff

    Returns
    -------
    list[dict]  Filtered rows as plain dicts.
    """
    df = load_dataset()
    if df.empty:
        return []

    mask = pd.Series([True] * len(df), index=df.index)

    if category is not None:
        mask &= df[COL_CATEGORY].str.upper() == category.strip().upper()

    if branch is not None:
        mask &= df[COL_BRANCH].str.lower() == branch.strip().lower()

    if city is not None and COL_CITY in df.columns:
        mask &= df[COL_CITY].str.lower() == city.strip().lower()

    if max_cutoff is not None:
        mask &= df[COL_CUTOFF] <= float(max_cutoff)

    if min_cutoff is not None:
        mask &= df[COL_CUTOFF] >= float(min_cutoff)

    return df[mask].to_dict(orient="records")


def search_college(query: str) -> list[dict[str, Any]]:
    """
    Case-insensitive substring search across College_Name and City.

    Parameters
    ----------
    query : str
        Search term, e.g. "COEP", "Pune", or "Walchand".

    Returns
    -------
    list[dict]  Matching rows as plain dicts.
    """
    df = load_dataset()
    if df.empty or not query:
        return []

    q = query.strip().lower()
    name_match = df[COL_NAME].str.lower().str.contains(q, na=False)

    if COL_CITY in df.columns:
        city_match = df[COL_CITY].str.lower().str.contains(q, na=False)
        result: pd.DataFrame = df[name_match | city_match]
        return result.to_dict(orient="records")

    result = df[name_match]
    return result.to_dict(orient="records")


def get_available_branches() -> list[str]:
    """Return a sorted list of unique branch names present in the dataset."""
    df = load_dataset()
    if df.empty or COL_BRANCH not in df.columns:
        return []
    return sorted(df[COL_BRANCH].dropna().unique().tolist())


def get_available_cities() -> list[str]:
    """Return a sorted list of unique cities derived from College_Name."""
    df = load_dataset()
    if df.empty or COL_CITY not in df.columns:
        return []
    return sorted(df[COL_CITY].dropna().unique().tolist())


def get_available_universities() -> list[str]:
    """Return a sorted list of unique Home_University values."""
    df = load_dataset()
    if df.empty or COL_HOME_UNIV not in df.columns:
        return []
    return sorted(df[COL_HOME_UNIV].dropna().unique().tolist())


def get_college_by_id(college_id: int | str) -> dict[str, Any] | None:
    """
    Retrieve all rows for a given College_ID.

    Returns the first matching row as a dict, or None when not found.
    """
    df = load_dataset()
    if df.empty or COL_ID not in df.columns:
        return None

    try:
        cid = int(college_id)
    except (ValueError, TypeError):
        logger.debug("Invalid college_id '%s'.", college_id)
        return None

    matches = df[df[COL_ID] == cid]
    if matches.empty:
        logger.debug("College_ID %s not found in dataset.", cid)
        return None

    return matches.iloc[0].to_dict()
