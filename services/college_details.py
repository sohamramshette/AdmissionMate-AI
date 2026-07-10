"""
services/college_details.py
============================
College Details Service
-----------------------
Assembles a complete, display-ready profile for a single college,
identified by its ``college_id``.

Responsibilities
----------------
1. Load the college's base record from the dataset via ``get_college_by_id``.
2. Aggregate sibling rows (same college name) to collect all available
   branches and category-wise cutoffs offered by that institution.
3. Derive display-friendly values (formatted fees, age, ownership label…).
4. Call IBM Watsonx Granite to generate a 5-bullet AI summary using only
   the supplied dataset data.  Falls back gracefully on any API error.

Public API
----------
    get_college_profile(college_id: str) -> dict | None
        Returns a fully-populated profile dict, or None if not found.
"""

from __future__ import annotations

import logging
from typing import Any

from services.dataset import (
    get_college_by_id,
    load_dataset,
    COL_ID, COL_NAME, COL_BRANCH, COL_CATEGORY,
    COL_CUTOFF, COL_FEES, COL_NAAC, COL_NBA,
    COL_PLACEMENT, COL_INTAKE, COL_ESTD,
    COL_CITY, COL_DISTRICT, COL_UNIV, COL_TYPE,
)
from services.watsonx import chat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI summary prompt
# ---------------------------------------------------------------------------

_SUMMARY_SYSTEM = (
    "You are an AI College Admission Counsellor.\n"
    "Summarise the following college in exactly 5 concise bullet points.\n"
    "Use ONLY the supplied dataset information — do NOT invent any figures.\n"
    "Each bullet must be one sentence. Start each line with a dash (-).\n"
    "Cover: academic reputation, branches offered, fees, placements, and location/type."
)


# ===========================================================================
# Public entry-point
# ===========================================================================

def get_college_profile(college_id: str) -> dict[str, Any] | None:
    """
    Build and return a complete display profile for the given college_id.

    Parameters
    ----------
    college_id : str
        The unique identifier, e.g. ``"COEP001"``.

    Returns
    -------
    dict | None
        Fully-populated profile dict, or ``None`` when the ID is not found.

    Profile keys
    ------------
    college_id, name, city, district, university, type, ownership_label,
    established_year, college_age,
    naac_grade, nba_accredited,
    branches            – list[dict] with keys: branch, category, cutoff, intake
    all_branch_names    – sorted list[str] of unique branch names
    cutoff_by_category  – dict[category -> list[dict{branch, cutoff}]]
    annual_fees_inr, fees_display,
    avg_placement_lpa, placement_display,
    ai_summary          – 5-bullet Watsonx paragraph (str)
    """
    # 1. Look up primary row
    primary = get_college_by_id(college_id)
    if primary is None:
        logger.warning("College ID '%s' not found.", college_id)
        return None

    college_name: str = str(primary[COL_NAME])

    # 2. Gather ALL rows for this college (all branches / categories)
    df = load_dataset()
    sibling_mask = df[COL_NAME].str.strip() == college_name.strip()
    siblings = df[sibling_mask].copy()

    # 3. Build branches list — one dict per row
    branches: list[dict[str, Any]] = []
    for _, row in siblings.iterrows():
        branches.append({
            "branch":   str(row[COL_BRANCH]),
            "category": str(row[COL_CATEGORY]),
            "cutoff":   float(row[COL_CUTOFF]),
            "intake":   int(row[COL_INTAKE]) if COL_INTAKE in row and row[COL_INTAKE] else 0,
        })

    # Unique branch names (sorted)
    all_branch_names: list[str] = sorted({b["branch"] for b in branches})

    # 4. Category-wise cutoff map  {category: [{branch, cutoff}, …]}
    cutoff_by_category: dict[str, list[dict[str, Any]]] = {}
    for b in branches:
        cat = b["category"]
        cutoff_by_category.setdefault(cat, []).append({
            "branch": b["branch"],
            "cutoff": b["cutoff"],
        })

    # 5. Derive display values from primary row
    fees_raw: int = int(primary.get(COL_FEES, 0) or 0)
    placement_raw: float = float(primary.get(COL_PLACEMENT, 0) or 0)
    estd_year: int = int(primary.get(COL_ESTD, 0) or 0)

    # Human-readable fees
    if fees_raw >= 100000:
        fees_display = f"Rs.{fees_raw / 100000:.1f}L / year"
    elif fees_raw >= 1000:
        fees_display = f"Rs.{fees_raw // 1000}K / year"
    else:
        fees_display = f"Rs.{fees_raw} / year" if fees_raw else "Not available"

    # Placement label
    placement_display = f"{placement_raw:.1f} LPA" if placement_raw > 0 else "Not available"

    # College age
    college_age = (2024 - estd_year) if estd_year > 0 else None

    # Ownership label derived from the "type" column
    ownership_label = _derive_ownership(str(primary.get(COL_TYPE, "")))

    # 6. Generate the AI summary
    ai_summary = _generate_ai_summary(primary, all_branch_names, branches)

    return {
        # Identity
        "college_id":        college_id,
        "name":              college_name,
        "city":              str(primary.get(COL_CITY, "")),
        "district":          str(primary.get(COL_DISTRICT, "")),
        "university":        str(primary.get(COL_UNIV, "")),
        "type":              str(primary.get(COL_TYPE, "")),
        "ownership_label":   ownership_label,
        "established_year":  estd_year if estd_year > 0 else None,
        "college_age":       college_age,
        # Accreditation
        "naac_grade":        str(primary.get(COL_NAAC, "N/A")),
        "nba_accredited":    str(primary.get(COL_NBA, "No")),
        # Branches & cutoffs
        "branches":          branches,
        "all_branch_names":  all_branch_names,
        "cutoff_by_category": cutoff_by_category,
        # Financials
        "annual_fees_inr":   fees_raw,
        "fees_display":      fees_display,
        # Placements
        "avg_placement_lpa": placement_raw,
        "placement_display": placement_display,
        # AI content
        "ai_summary":        ai_summary,
    }


# ===========================================================================
# Private helpers
# ===========================================================================

def _derive_ownership(college_type: str) -> str:
    """Map the raw 'type' column value to a short ownership label."""
    t = college_type.lower()
    if "government autonomous" in t:
        return "Government Autonomous"
    if "government" in t:
        return "Government"
    if "private aided" in t:
        return "Private Aided"
    if "private" in t:
        return "Private"
    return college_type or "N/A"


def _generate_ai_summary(
    primary: dict[str, Any],
    branch_names: list[str],
    branches: list[dict[str, Any]],
) -> str:
    """
    Call IBM Watsonx Granite to produce a 5-bullet college summary.

    Falls back to a pre-built rule-based summary on any error.

    Parameters
    ----------
    primary      : dict   Primary dataset row for the college.
    branch_names : list   Unique branch names offered.
    branches     : list   Full branch detail dicts.
    """
    cutoffs = [b["cutoff"] for b in branches]
    min_cutoff = min(cutoffs) if cutoffs else "N/A"
    max_cutoff = max(cutoffs) if cutoffs else "N/A"

    user_msg = (
        f"College: {primary.get(COL_NAME)}\n"
        f"Location: {primary.get(COL_CITY)}, {primary.get(COL_DISTRICT)}\n"
        f"University: {primary.get(COL_UNIV)}\n"
        f"Type: {primary.get(COL_TYPE)}\n"
        f"Established: {primary.get(COL_ESTD)}\n"
        f"NAAC Grade: {primary.get(COL_NAAC)}\n"
        f"NBA Accredited: {primary.get(COL_NBA)}\n"
        f"Branches Offered: {', '.join(branch_names)}\n"
        f"Cutoff Range: {min_cutoff} – {max_cutoff} percentile\n"
        f"Annual Fees: Rs.{primary.get(COL_FEES)}\n"
        f"Avg Placement: {primary.get(COL_PLACEMENT)} LPA\n\n"
        "Summarise in exactly 5 bullet points covering: "
        "academic reputation, branches, fees, placements, and location/ownership."
    )

    try:
        reply = chat(user_msg, system_prompt=_SUMMARY_SYSTEM)
        if reply.startswith("Watsonx Error"):
            logger.warning("Watsonx error generating AI summary; using fallback.")
            return _fallback_summary(primary, branch_names)
        return reply
    except Exception as exc:
        logger.warning("AI summary generation failed: %s", exc)
        return _fallback_summary(primary, branch_names)


def _fallback_summary(
    primary: dict[str, Any],
    branch_names: list[str],
) -> str:
    """Return a deterministic bullet-point summary when Watsonx is unavailable."""
    lines = [
        f"- {primary.get(COL_NAME)} is a {primary.get(COL_TYPE)} institution "
        f"established in {primary.get(COL_ESTD)}, affiliated to {primary.get(COL_UNIV)}.",
        f"- It holds a NAAC {primary.get(COL_NAAC)} accreditation"
        + (" and is NBA approved." if str(primary.get(COL_NBA, "")).lower() == "yes" else "."),
        f"- Branches offered include: {', '.join(branch_names)}.",
        f"- Annual tuition fees are Rs.{primary.get(COL_FEES, 'N/A')} per year.",
        f"- The average placement package is {primary.get(COL_PLACEMENT, 'N/A')} LPA.",
    ]
    return "\n".join(lines)
