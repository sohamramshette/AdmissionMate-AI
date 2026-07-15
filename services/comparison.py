"""
services/comparison.py
======================
College Comparison Service
--------------------------
Builds a structured comparison payload for a list of college IDs,
derived entirely from the cached dataset.  Also provides a list of
unique colleges for the search API and an AI-generated summary.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import pandas as pd

from services.dataset import (
    load_dataset,
    COL_ID, COL_NAME, COL_BRANCH, COL_CATEGORY,
    COL_CUTOFF, COL_FEES, COL_INTAKE, COL_HOME_UNIV, COL_CITY,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# College directory (one record per unique college, cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_college_directory() -> list[dict[str, Any]]:
    """
    Return one summary dict per unique college (by College_ID).

    Fields:
        id, name, city, home_university, min_cutoff, max_cutoff,
        min_fees, max_fees, branches, intake
    """
    df = load_dataset()
    if df.empty:
        return []

    records: list[dict[str, Any]] = []

    for college_id, group in df.groupby(COL_ID, sort=True):
        first = group.iloc[0]
        name: str = str(first[COL_NAME])
        city: str = str(first.get(COL_CITY, ""))
        univ: str = str(first.get(COL_HOME_UNIV, ""))

        cutoffs = group[COL_CUTOFF].dropna()
        fees    = group[COL_FEES].dropna()

        branches = sorted(group[COL_BRANCH].dropna().unique().tolist())
        total_intake = int(group[COL_INTAKE].fillna(0).sum())

        records.append({
            "id":              int(college_id),
            "name":            name,
            "city":            city,
            "home_university": univ,
            "min_cutoff":      float(round(cutoffs.min(), 2)) if not cutoffs.empty else None,
            "max_cutoff":      float(round(cutoffs.max(), 2)) if not cutoffs.empty else None,
            "avg_cutoff":      float(round(cutoffs.mean(), 2)) if not cutoffs.empty else None,
            "min_fees":        int(fees.min()) if not fees.empty else 0,
            "max_fees":        int(fees.max()) if not fees.empty else 0,
            "avg_fees":        int(fees.mean()) if not fees.empty else 0,
            "branches":        branches,
            "branch_count":    len(branches),
            "intake":          total_intake,
        })

    return records


def get_college_directory() -> list[dict[str, Any]]:
    """Public wrapper — returns the full college directory list."""
    return _build_college_directory()


# ---------------------------------------------------------------------------
# Comparison payload builder
# ---------------------------------------------------------------------------

def compare_colleges(college_ids: list[int]) -> list[dict[str, Any]]:
    """
    Build a display-ready comparison record for each requested college ID.

    Parameters
    ----------
    college_ids : list[int]
        Up to 4 College_ID integers to compare.

    Returns
    -------
    list[dict]  One dict per college with these keys:
        id, name, city, home_university,
        cutoff_open          – OPEN category best (highest) cutoff
        cutoff_open_display,
        cutoff_sc_display,   cutoff_obc_display,
        fees_display,        fees_raw,
        branches,            branch_count,
        intake,
        categories           – sorted list of available categories
    """
    if not college_ids:
        return []

    df = load_dataset()
    if df.empty:
        return []

    results: list[dict[str, Any]] = []

    for cid in college_ids:
        subset = df[df[COL_ID] == int(cid)]
        if subset.empty:
            continue

        first    = subset.iloc[0]
        name     = str(first[COL_NAME])
        city     = str(first.get(COL_CITY, ""))
        univ     = str(first.get(COL_HOME_UNIV, ""))

        # --- Cutoffs per major category ---
        def _best_cutoff(cat: str) -> float | None:
            rows = subset[subset[COL_CATEGORY].str.upper() == cat.upper()]
            if rows.empty:
                return None
            return float(round(rows[COL_CUTOFF].max(), 2))

        open_cutoff = _best_cutoff("OPEN")
        sc_cutoff   = _best_cutoff("SC")
        obc_cutoff  = _best_cutoff("OBC")
        st_cutoff   = _best_cutoff("ST")

        all_cutoffs  = subset[COL_CUTOFF].dropna()
        max_cutoff   = float(round(all_cutoffs.max(), 2)) if not all_cutoffs.empty else None

        # --- Fees (average of unique fee values across rows) ---
        fees_vals = subset[COL_FEES].dropna()
        avg_fees  = int(fees_vals.mean()) if not fees_vals.empty else 0

        # --- Branches & intake ---
        branches      = sorted(subset[COL_BRANCH].dropna().unique().tolist())
        total_intake  = int(subset[COL_INTAKE].fillna(0).sum())
        categories    = sorted(subset[COL_CATEGORY].dropna().unique().tolist())

        # --- Format fees ---
        def _fmt_fees(val: int) -> str:
            if val >= 100_000:
                return f"₹{val / 100_000:.1f}L/yr"
            if val >= 1_000:
                return f"₹{val // 1_000}K/yr"
            return f"₹{val}/yr" if val else "N/A"

        def _fmt_cutoff(val: float | None) -> str:
            return f"{val:.2f}" if val is not None else "N/A"

        results.append({
            "id":                  int(cid),
            "name":                name,
            "city":                city,
            "home_university":     univ,
            # cutoffs
            "cutoff_open":         open_cutoff,
            "cutoff_open_display": _fmt_cutoff(open_cutoff),
            "cutoff_sc_display":   _fmt_cutoff(sc_cutoff),
            "cutoff_obc_display":  _fmt_cutoff(obc_cutoff),
            "cutoff_st_display":   _fmt_cutoff(st_cutoff),
            "cutoff_max":          max_cutoff,
            "cutoff_max_display":  _fmt_cutoff(max_cutoff),
            # fees
            "fees_raw":            avg_fees,
            "fees_display":        _fmt_fees(avg_fees),
            # branches
            "branches":            branches,
            "branch_count":        len(branches),
            "branches_display":    ", ".join(branches[:3]) + ("…" if len(branches) > 3 else ""),
            "intake":              total_intake,
            "categories":          categories,
        })

    return results


# ---------------------------------------------------------------------------
# AI comparison summary (deterministic fallback when Watsonx unavailable)
# ---------------------------------------------------------------------------

_COMPARE_SYSTEM = (
    "You are AdmissionMate AI, a college admission counsellor for Maharashtra MHT-CET students.\n"
    "Given comparison data for several colleges, produce a concise analysis.\n"
    "Use ONLY the supplied data — do NOT invent figures.\n"
    "Format your response as short labelled lines:\n"
    "Best Placements: <college>\n"
    "Lowest Fees: <college>\n"
    "Highest Cutoff (hardest to get into): <college>\n"
    "Most Branches: <college>\n"
    "Recommended Choice: <one paragraph explaining why, based on fees + cutoff + university>\n"
)


def generate_comparison_summary(colleges: list[dict[str, Any]]) -> str:
    """
    Generate a short AI analysis for the compared colleges.
    Falls back to a deterministic rule-based summary.
    """
    if not colleges:
        return ""

    try:
        from services.watsonx import chat

        lines = ["College comparison data:"]
        for c in colleges:
            lines.append(
                f"- {c['name']} ({c['city']}): OPEN cutoff={c['cutoff_open_display']}, "
                f"fees={c['fees_display']}, branches={c['branch_count']}, "
                f"university={c['home_university']}"
            )

        reply = chat("\n".join(lines), system_prompt=_COMPARE_SYSTEM)
        if reply and not reply.startswith("Watsonx Error"):
            return reply
    except Exception as exc:
        logger.warning("AI comparison summary failed: %s", exc)

    return _fallback_summary(colleges)


def _fallback_summary(colleges: list[dict[str, Any]]) -> str:
    """Rule-based comparison summary when AI is unavailable."""
    if not colleges:
        return ""

    # Lowest fees
    by_fees = [c for c in colleges if c["fees_raw"] > 0]
    cheapest = min(by_fees, key=lambda c: c["fees_raw"])["name"] if by_fees else colleges[0]["name"]

    # Highest OPEN cutoff → most prestigious / hardest to get
    by_cutoff = [c for c in colleges if c["cutoff_open"] is not None]
    hardest   = max(by_cutoff, key=lambda c: c["cutoff_open"])["name"] if by_cutoff else colleges[0]["name"]

    # Most branches
    most_branches = max(colleges, key=lambda c: c["branch_count"])["name"]

    lines = [
        f"Lowest Fees: {cheapest}",
        f"Highest OPEN Cutoff (most competitive): {hardest}",
        f"Most Branches Offered: {most_branches}",
        "",
        f"Recommended Choice: Based on fees, cutoff competitiveness, and branch diversity, "
        f"{cheapest} offers strong value. If affordability is the priority, {cheapest} stands out. "
        f"For prestige and competitive intake, {hardest} is the top choice.",
    ]
    return "\n".join(lines)
