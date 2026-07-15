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
    COL_HOME_UNIV,
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

_QUICKFACT_SYSTEM = (
    "You are an AI College Admission Counsellor.\n"
    "Write exactly ONE sentence (max 25 words) summarising this college.\n"
    "Use ONLY the supplied data. Do NOT invent figures.\n"
    "Tone: factual, helpful. No marketing language."
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

    # Home university (the real column)
    home_university: str = str(primary.get(COL_HOME_UNIV, "")).strip()

    # Aggregate intake across all sibling rows
    total_intake: int = int(siblings[COL_INTAKE].fillna(0).sum())

    # Cutoff range (OPEN category for the headline figure, else overall)
    open_rows = siblings[siblings[COL_CATEGORY].str.upper() == "OPEN"]
    if not open_rows.empty:
        open_cutoff_display = f"{float(open_rows[COL_CUTOFF].max()):.2f} (OPEN)"
    else:
        cutoff_vals = siblings[COL_CUTOFF].dropna()
        open_cutoff_display = f"{float(cutoff_vals.max()):.2f}" if not cutoff_vals.empty else ""

    # 6. Build quick-facts list — only include rows where value is meaningful
    quick_facts: list[dict[str, Any]] = []

    def _add_fact(icon: str, label: str, value: str, color: str = "") -> None:
        """Append a fact only when value is non-empty and not a sentinel."""
        v = value.strip() if value else ""
        if v and v.lower() not in ("n/a", "0", "none", "not available", "nan", ""):
            quick_facts.append({"icon": icon, "label": label, "value": v, "color": color})

    # Fields from the real dataset
    _add_fact("bi-geo-alt-fill",      "Location",         str(primary.get(COL_CITY, "")) + ", Maharashtra",        "text-primary")
    _add_fact("bi-mortarboard-fill",  "University",       home_university,                                          "text-indigo")
    _add_fact("bi-cash-coin",         "Annual Fees",      fees_display,                                             "text-success")
    _add_fact("bi-people-fill",       "Total Intake",     f"{total_intake} seats" if total_intake else "",          "text-sky")
    _add_fact("bi-percent",           "OPEN Cutoff",      open_cutoff_display,                                      "text-amber")
    _add_fact("bi-diagram-3-fill",    "Branches Offered", f"{len(all_branch_names)} branches",                      "text-primary")

    # Fields from legacy columns (present only when the dataset has them)
    naac = str(primary.get(COL_NAAC, "")).strip()
    if naac and naac not in ("N/A", "nan", ""):
        _add_fact("bi-award-fill",        "NAAC Grade",       naac,                                                 "text-success")

    nba = str(primary.get(COL_NBA, "")).strip()
    if nba.lower() == "yes":
        _add_fact("bi-patch-check-fill",  "NBA Accreditation","Accredited",                                         "text-success")

    ownership = ownership_label.strip()
    if ownership and ownership not in ("N/A", ""):
        _add_fact("bi-building-fill",     "College Type",     ownership,                                            "text-indigo")

    if estd_year > 0:
        _add_fact("bi-calendar-fill",     "Established",      str(estd_year),                                       "text-amber")

    if placement_raw > 0:
        _add_fact("bi-briefcase-fill",    "Avg. Package",     placement_display,                                    "text-success")

    # 7. Generate the AI one-liner for the Quick Facts card
    ai_oneliner = _generate_ai_oneliner(
        name=college_name,
        city=str(primary.get(COL_CITY, "")),
        university=home_university,
        fees_display=fees_display,
        branch_names=all_branch_names,
        ownership=ownership_label,
        naac=naac,
    )

    # 8. Generate the full 5-bullet AI summary
    ai_summary = _generate_ai_summary(primary, all_branch_names, branches)

    return {
        # Identity
        "college_id":        college_id,
        "name":              college_name,
        "city":              str(primary.get(COL_CITY, "")),
        "district":          str(primary.get(COL_DISTRICT, "")),
        "university":        home_university,
        "type":              str(primary.get(COL_TYPE, "")),
        "ownership_label":   ownership_label,
        "established_year":  estd_year if estd_year > 0 else None,
        "college_age":       college_age,
        # Accreditation
        "naac_grade":        naac if naac else "N/A",
        "nba_accredited":    nba if nba else "No",
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
        # Quick Facts card data
        "quick_facts":       quick_facts,
        "ai_oneliner":       ai_oneliner,
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


def _generate_ai_oneliner(
    *,
    name: str,
    city: str,
    university: str,
    fees_display: str,
    branch_names: list[str],
    ownership: str,
    naac: str,
) -> str:
    """
    Call IBM Watsonx Granite for a single-sentence college overview.
    Falls back to a deterministic sentence when unavailable.
    """
    branches_str = ", ".join(branch_names[:4])
    if len(branch_names) > 4:
        branches_str += f" and {len(branch_names) - 4} more"

    user_msg = (
        f"College: {name}\n"
        f"Location: {city}, Maharashtra\n"
        f"University: {university}\n"
        f"Type: {ownership or 'Engineering College'}\n"
        f"Branches: {branches_str}\n"
        f"Annual Fees: {fees_display}\n"
        f"NAAC: {naac or 'Not available'}\n\n"
        "Write exactly ONE sentence summarising this college for a prospective student."
    )

    try:
        reply = chat(user_msg, system_prompt=_QUICKFACT_SYSTEM)
        if reply and not reply.startswith("Watsonx Error"):
            # Strip any leading dash or bullet
            return reply.lstrip("- •").strip()
    except Exception as exc:
        logger.warning("AI one-liner generation failed: %s", exc)

    # Deterministic fallback
    branch_short = ", ".join(branch_names[:3])
    if len(branch_names) > 3:
        branch_short += f" and {len(branch_names) - 3} more"
    parts = [f"{name} is an engineering college in {city}"]
    if university:
        parts.append(f"affiliated to {university}")
    if branch_short:
        parts.append(f"offering {branch_short}")
    if fees_display and fees_display != "Not available":
        parts.append(f"with annual fees of {fees_display}")
    return " ".join(parts) + "."
