"""
services/comparison.py
======================
College Comparison Service
--------------------------
Accepts a list of college identifiers and returns a structured
comparison payload ready for rendering in the compare template.

Current state: STUB — returns an empty list.

Usage (once implemented):
    from services.comparison import compare_colleges
    comparison = compare_colleges(college_ids)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compare_colleges(college_ids: list[str]) -> list[dict[str, Any]]:
    """
    Return detailed data for the specified colleges for side-by-side display.

    Parameters
    ----------
    college_ids : list[str]
        List of college identifiers (e.g. internal IDs or college names).

    Returns
    -------
    list[dict]
        Each dict contains full college details:
        name, city, cutoff, fees, naac, nba, placement,
        intake, branch, estd, type

    TODO
    ----
    1. Load dataset via services.dataset.load_dataset()
    2. Filter rows matching the provided college_ids
    3. Return structured comparison data
    """
    logger.info("compare_colleges called for IDs: %s", college_ids)
    # TODO: implement comparison logic
    return []
