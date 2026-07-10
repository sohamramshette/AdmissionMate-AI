"""
services/rag.py
===============
Retrieval-Augmented Generation (RAG) for the College Admission Assistant.

Flow
----
User Question
  → Intent Detection   (_detect_intent)
  → Dataset Retrieval  (_retrieve_colleges)
  → Context Building   (_build_context)
  → Granite via chat() (_generate_answer)
  → Answer

Fallback
--------
If the dataset returns no relevant colleges, the question is forwarded
directly to Watsonx without any injected context (pure LLM fallback).

Public API
----------
    rag_chat(user_message: str) -> str
        Single entry-point — drop-in replacement for watsonx.chat().
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.dataset import (
    filter_colleges,
    load_dataset,
    search_college,
)
from services.watsonx import chat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RAG system prompt — injected every time context is available
# ---------------------------------------------------------------------------

_RAG_SYSTEM_PROMPT = """
You are an AI College Admission Assistant specialised in Maharashtra engineering admissions (MHT CET).

Rules:
1. Answer ONLY using the college data provided in the context below.
2. If the specific information is not present in the context, say clearly:
   "I don't have that information in my current dataset."
3. NEVER invent or estimate placement figures, fees, cutoffs, or NAAC grades.
4. When comparing colleges, use a clear structured format.
5. Keep responses concise, helpful, and student-friendly.
6. Amounts are in Indian Rupees (INR, shown as Rs.); placements are in LPA (Lakhs Per Annum).

Context:
{context}
""".strip()

# Fallback system prompt used when no dataset context is available
_FALLBACK_SYSTEM_PROMPT = """
You are an AI College Admission Assistant specialised in Maharashtra engineering admissions (MHT CET).

Answer questions about:
- MHT CET admissions
- Maharashtra engineering colleges
- Engineering branches and career guidance
- College fees, cutoffs, placements in general terms

Keep answers concise and helpful.
If asked about specific college data you are uncertain about, say so clearly.
""".strip()

# ---------------------------------------------------------------------------
# Known college short-name / abbreviation → full name fragments
# (Used for fuzzy matching so "COEP", "VJTI", "PICT" etc. all resolve)
# ---------------------------------------------------------------------------

_COLLEGE_ALIASES: dict[str, str] = {
    "coep":   "College of Engineering Pune",
    "vjti":   "Veermata Jijabai Technological Institute",
    "pict":   "Pune Institute of Computer Technology",
    "mit":    "MIT",
    "mitaoe": "MIT Academy of Engineering",
    "mit aoe": "MIT Academy of Engineering",
    "pccoe":  "Pimpri Chinchwad College of Engineering",
    "spit":   "Sardar Patel Institute of Technology",
    "kjs":    "K.J. Somaiya",
    "somaiya": "K.J. Somaiya",
    "djscoe": "Dwarkadas J. Sanghvi",
    "dj sanghvi": "Dwarkadas J. Sanghvi",
    "rait":   "Ramrao Adik",
    "vit":    "Vishwakarma Institute of Technology",
    "viit":   "Vishwakarma Institute of Information Technology",
    "cummins": "Cummins College",
    "symbiosis": "Symbiosis",
    "scoe":   "Symbiosis",
    "walchand": "Walchand",
    "wcoe":   "Walchand",
}

# Branch keywords → canonical branch names (title-cased to match dataset)
_BRANCH_KEYWORDS: dict[str, str] = {
    "computer engineering": "Computer Engineering",
    "computer science":     "Computer Engineering",
    "cs":                   "Computer Engineering",
    "cse":                  "Computer Engineering",
    "it":                   "Information Technology",
    "information technology": "Information Technology",
    "entc":                 "Electronics & Telecommunication Engineering",
    "electronics":          "Electronics & Telecommunication Engineering",
    "e&tc":                 "Electronics & Telecommunication Engineering",
    "mechanical":           "Mechanical Engineering",
    "mech":                 "Mechanical Engineering",
    "civil":                "Civil Engineering",
    "electrical":           "Electrical Engineering",
    "ai":                   "Artificial Intelligence & Data Science",
    "ai & ds":              "Artificial Intelligence & Data Science",
    "ai&ds":                "Artificial Intelligence & Data Science",
    "aiml":                 "Artificial Intelligence & Machine Learning",
    "ai & ml":              "Artificial Intelligence & Machine Learning",
    "data science":         "Artificial Intelligence & Data Science",
    "ds":                   "Artificial Intelligence & Data Science",
}

# City keywords → normalised city names (title-cased to match dataset)
_CITY_KEYWORDS: list[str] = [
    "pune", "mumbai", "nagpur", "nashik", "aurangabad",
    "kolhapur", "solapur", "thane", "navi mumbai",
]

# Category keywords → normalised category strings
_CATEGORY_KEYWORDS: dict[str, str] = {
    "open":    "OPEN",
    "general": "OPEN",
    "obc":     "OBC",
    "sc":      "SC",
    "st":      "ST",
    "ews":     "EWS",
    "nt":      "NT",
    "sebc":    "SEBC",
    "vj":      "VJ",
}

# Maximum number of colleges included in a single context block
_MAX_CONTEXT_COLLEGES = 5


# ===========================================================================
# Intent detection
# ===========================================================================

class _Intent:
    """Bag of extracted entities from the user question."""

    def __init__(self) -> None:
        self.college_names: list[str] = []   # free-text fragments to search
        self.branch: str | None = None
        self.city: str | None = None
        self.category: str | None = None
        self.percentile: float | None = None
        self.is_comparison: bool = False
        self.is_fees: bool = False
        self.is_placement: bool = False
        self.is_cutoff: bool = False
        self.is_branch_query: bool = False
        self.is_city_query: bool = False

    def has_specifics(self) -> bool:
        """True when at least one retrieval signal is present."""
        return bool(
            self.college_names
            or self.branch
            or self.city
            or self.category
            or self.percentile is not None
        )


def _detect_intent(message: str) -> _Intent:
    """
    Parse the user message into structured retrieval signals.

    Uses keyword matching and simple regex — no external NLP dependency.

    Parameters
    ----------
    message : str
        Raw user question.

    Returns
    -------
    _Intent
        Populated intent object.
    """
    intent = _Intent()
    lower = message.lower()

    # --- question type flags ---
    intent.is_comparison  = bool(re.search(r"\bcompar\w*\b", lower))
    intent.is_fees        = bool(re.search(r"\bfee[s]?\b|\bcost\b|\btuition\b|\bannual\b", lower))
    intent.is_placement   = bool(re.search(r"\bplacement[s]?\b|\bpackage\b|\blpa\b|\bsalary\b|\bhighest\b", lower))
    intent.is_cutoff      = bool(re.search(r"\bcutoff\b|\bcut.off\b|\bpercentile\b|\bcutoffs\b", lower))
    intent.is_branch_query = bool(re.search(r"\bbest\b.*\bcollege[s]?\b|\bwhich\s+college[s]?\b|\btop\s+college[s]?\b", lower))
    intent.is_city_query  = bool(re.search(r"\bin\s+(pune|mumbai|nagpur|nashik|aurangabad|kolhapur|solapur|thane)\b", lower))

    # --- percentile extraction ---
    pct_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:percentile|%)", lower)
    if pct_match:
        try:
            intent.percentile = float(pct_match.group(1))
        except ValueError:
            pass

    # --- category extraction ---
    for kw, cat in _CATEGORY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", lower):
            intent.category = cat
            break

    # --- branch extraction ---
    for kw, branch in _BRANCH_KEYWORDS.items():
        if kw in lower:
            intent.branch = branch
            break

    # --- city extraction ---
    for city in _CITY_KEYWORDS:
        if city in lower:
            intent.city = city.title()
            break

    # --- college name extraction (alias + direct) ---
    # Check known abbreviations first
    for alias, full_name in _COLLEGE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            if full_name not in intent.college_names:
                intent.college_names.append(full_name)

    # Also try to find multi-word capitalised sequences that look like proper
    # institution names (e.g. "MIT Academy of Engineering", "Sardar Patel Institute").
    # Require at least three words OR a word not already resolved by aliases to avoid
    # picking up question fragments like "Compare COEP" or "Tell VJTI".
    _SKIP_FIRST_WORDS = {
        "compare", "tell", "about", "what", "which", "best", "list",
        "give", "show", "find", "highest", "fees", "cutoff", "placement",
    }
    capitalised = re.findall(
        r"\b([A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+){2,})\b",
        message
    )
    for token in capitalised:
        clean = token.strip()
        first_word = clean.split()[0].lower()
        if first_word not in _SKIP_FIRST_WORDS and clean not in intent.college_names:
            intent.college_names.append(clean)

    return intent


# ===========================================================================
# Retrieval
# ===========================================================================

def _retrieve_colleges(intent: _Intent) -> list[dict[str, Any]]:
    """
    Query the dataset using the detected intent and return up to
    ``_MAX_CONTEXT_COLLEGES`` relevant rows.

    Strategy
    --------
    1. If specific college names are mentioned → search each name.
    2. If a branch/city/category is detected  → filter_colleges().
    3. If a percentile is given               → filter by percentile range.
    4. Deduplicate and cap at ``_MAX_CONTEXT_COLLEGES``.

    Parameters
    ----------
    intent : _Intent
        Populated intent object from ``_detect_intent``.

    Returns
    -------
    list[dict]
        Up to ``_MAX_CONTEXT_COLLEGES`` college records.
    """
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _add(rows: list[dict[str, Any]]) -> None:
        """Append rows without duplicates (keyed on college_id)."""
        for row in rows:
            cid = str(row.get("college_id", ""))
            if cid not in seen_ids:
                seen_ids.add(cid)
                results.append(row)

    # 1. Named college search
    for name_fragment in intent.college_names:
        _add(search_college(name_fragment))

    # 2. Structured filter (branch + city + category + percentile)
    if intent.branch or intent.city or intent.category or intent.percentile is not None:
        max_cutoff = intent.percentile  # student's percentile = upper bound for safe matches
        filtered = filter_colleges(
            branch=intent.branch,
            city=intent.city,
            category=intent.category,
            max_cutoff=max_cutoff,
        )

        # Sort by cutoff descending to surface the most competitive colleges first
        filtered.sort(key=lambda r: r.get("cutoff_percentile") or 0, reverse=True)
        _add(filtered)

    # 3. Cap
    return results[:_MAX_CONTEXT_COLLEGES]


# ===========================================================================
# Context building
# ===========================================================================

def _build_context(colleges: list[dict[str, Any]]) -> str:
    """
    Serialise a list of college records into a concise plain-text block
    that fits comfortably inside the Watsonx prompt.

    Parameters
    ----------
    colleges : list[dict]
        College records from the dataset.

    Returns
    -------
    str
        Multi-line context string.
    """
    if not colleges:
        return ""

    lines: list[str] = []
    for i, college in enumerate(colleges, start=1):
        nba = "Yes" if str(college.get("nba_accredited", "")).lower() == "yes" else "No"
        lines.append(
            f"[{i}] {college.get('name', 'N/A')}  ({college.get('college_id', '')})\n"
            f"    City       : {college.get('city', 'N/A')}\n"
            f"    Branch     : {college.get('branch', 'N/A')}\n"
            f"    Category   : {college.get('category', 'N/A')}\n"
            f"    Cutoff     : {college.get('cutoff_percentile', 'N/A')} percentile\n"
            f"    Fees       : Rs.{college.get('annual_fees_inr', 'N/A')} per year\n"
            f"    NAAC Grade : {college.get('naac_grade', 'N/A')}\n"
            f"    NBA        : {nba}\n"
            f"    Placement  : {college.get('avg_placement_lpa', 'N/A')} LPA (avg)\n"
            f"    University : {college.get('university', 'N/A')}\n"
            f"    Type       : {college.get('type', 'N/A')}\n"
        )

    return "\n".join(lines)


# ===========================================================================
# Public entry-point
# ===========================================================================

def rag_chat(user_message: str) -> str:
    """
    RAG-powered chat that grounds Granite's answer in the college dataset.

    Parameters
    ----------
    user_message : str
        The raw question from the student.

    Returns
    -------
    str
        The assistant's reply — sourced from dataset context when available,
        falling back to a pure Watsonx LLM response otherwise.
    """
    # 1. Detect intent
    intent = _detect_intent(user_message)
    logger.debug(
        "Intent: colleges=%s  branch=%s  city=%s  category=%s  pct=%s",
        intent.college_names, intent.branch, intent.city,
        intent.category, intent.percentile,
    )

    # 2. Retrieve relevant colleges from dataset
    colleges = _retrieve_colleges(intent) if intent.has_specifics() else []
    logger.info("RAG retrieved %d colleges for query: %r", len(colleges), user_message[:80])

    # 3. Build context and choose system prompt
    if colleges:
        context = _build_context(colleges)
        system_prompt = _RAG_SYSTEM_PROMPT.format(context=context)
    else:
        # No dataset match — pure LLM fallback
        logger.info("No dataset match — falling back to direct Watsonx call.")
        system_prompt = _FALLBACK_SYSTEM_PROMPT

    # 4. Call Watsonx Granite
    return chat(user_message, system_prompt=system_prompt)
