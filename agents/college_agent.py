"""
agents/college_agent.py
========================
Central AI Agent — College Admission Assistant
-----------------------------------------------
CollegeAdmissionAgent is the single entry-point for every user request.
It identifies intent, validates the student profile, collects missing
information, delegates to the appropriate service, and returns a
natural-language response.

Responsibilities
----------------
- Receive every user request (text or structured dict).
- Identify the user's intent via keyword / pattern matching.
- Validate the student profile and ask for missing fields.
- Coordinate services.recommendation  → college recommendations.
- Coordinate services.comparison      → college / branch comparison.
- Coordinate services.watsonx         → general AI answers.
- Return a final natural-language response string.

Current state: ARCHITECTURE — service calls are wired but the
underlying services are still stubs (they return empty lists).
Watsonx integration is intentionally left as a stub.

Usage
-----
    from agents import CollegeAdmissionAgent

    agent = CollegeAdmissionAgent()
    reply = agent.generate_response(
        user_message="Which college is best for Computer Engineering in Pune?",
        student_profile={"name": "Aisha", "cet_percentile": 92.5,
                         "category": "OPEN", "preferred_branch": "Computer Engineering",
                         "preferred_city": "Pune"},
    )
    print(reply)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.recommendation import get_recommendations
from services.comparison import compare_colleges
from services.watsonx import chat as watsonx_chat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent labels
# ---------------------------------------------------------------------------
INTENT_RECOMMEND          = "recommend_colleges"
INTENT_COMPARE_COLLEGES   = "compare_colleges"
INTENT_COMPARE_BRANCHES   = "compare_branches"
INTENT_GENERAL_QUESTION   = "general_question"
INTENT_UNKNOWN            = "unknown"

# ---------------------------------------------------------------------------
# Required fields for a complete student profile
# ---------------------------------------------------------------------------
REQUIRED_PROFILE_FIELDS: dict[str, str] = {
    "name":             "your full name",
    "cet_percentile":   "your MHT-CET percentile",
    "category":         "your reservation category (e.g. OPEN, OBC, SC, ST)",
    "preferred_branch": "your preferred branch (e.g. Computer Engineering)",
    "preferred_city":   "your preferred city (e.g. Pune)",
}

# ---------------------------------------------------------------------------
# Keyword sets used by identify_intent()
# ---------------------------------------------------------------------------
_RECOMMEND_KEYWORDS = {
    "recommend", "suggest", "best college", "which college", "find college",
    "top college", "good college", "admission", "eligible", "colleges for me",
}

_COMPARE_COLLEGE_KEYWORDS = {
    "compare college", "vs college", "college vs", "difference between college",
    "compare between", "compare these college",
}

_COMPARE_BRANCH_KEYWORDS = {
    "compare branch", "vs branch", "branch vs", "which branch", "better branch",
    "difference between branch", "branch comparison", "branch vs branch",
    "engineering vs", "vs engineering", "engineering or", "or engineering",
    "technology vs", "vs technology",
}

# Branch names used both for intent detection and for compare_branches()
KNOWN_BRANCHES = [
    "computer engineering", "information technology",
    "electronics and telecommunication", "mechanical engineering",
    "civil engineering", "electrical engineering",
    "artificial intelligence", "data science",
]


# ===========================================================================
# CollegeAdmissionAgent
# ===========================================================================

class CollegeAdmissionAgent:
    """
    Central orchestrator for the College Admission Assistant.

    Parameters
    ----------
    max_recommendations : int
        Maximum number of college suggestions to return.  Default 5.
    """

    def __init__(self, max_recommendations: int = 5) -> None:
        self.max_recommendations = max_recommendations
        logger.info(
            "CollegeAdmissionAgent initialised (max_recommendations=%d)",
            self.max_recommendations,
        )

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def generate_response(
        self,
        user_message: str,
        student_profile: dict[str, Any] | None = None,
        college_ids: list[str] | None = None,
    ) -> str:
        """
        Main entry-point.  Process a user request end-to-end and return
        a natural-language response string.

        Parameters
        ----------
        user_message : str
            Free-text input from the user.
        student_profile : dict, optional
            Partial or complete student data collected so far.
            Keys: name, cet_percentile, category, preferred_branch, preferred_city.
        college_ids : list[str], optional
            Pre-selected college identifiers for comparison requests.

        Returns
        -------
        str
            Final natural-language reply ready for display.
        """
        logger.info("generate_response called | intent detection in progress")

        student_profile = student_profile or {}
        college_ids     = college_ids     or []

        # 1. Identify what the user wants
        intent = self.identify_intent(user_message)
        logger.info("Detected intent: %s", intent)

        # 2. Route to the appropriate handler
        if intent == INTENT_RECOMMEND:
            missing = self.collect_missing_information(student_profile)
            if missing:
                return missing
            return self.recommend_colleges(student_profile)

        if intent == INTENT_COMPARE_COLLEGES:
            return self.compare_colleges(college_ids, user_message)

        if intent == INTENT_COMPARE_BRANCHES:
            return self.compare_branches(user_message)

        if intent == INTENT_GENERAL_QUESTION:
            return self.answer_general_question(user_message)

        # Fallback: let the AI handle anything unclassified
        return self.answer_general_question(user_message)

    # ------------------------------------------------------------------
    # Intent identification
    # ------------------------------------------------------------------

    def identify_intent(self, user_message: str) -> str:
        """
        Classify the user's intent from free-text input.

        Strategy
        --------
        Keyword matching against four intent buckets. The method is
        intentionally simple so it can be replaced with an LLM-based
        classifier later without changing the public interface.

        Parameters
        ----------
        user_message : str
            Raw message from the user.

        Returns
        -------
        str
            One of the INTENT_* constants defined at module level.
        """
        text = user_message.lower().strip()

        # Branch comparison takes priority over generic college comparison.
        # Triggers when a known keyword matches OR when "vs" / "or" appears
        # between two recognised branch names.
        branches_in_text = [b for b in KNOWN_BRANCHES if b in text]
        has_comparison_verb = " vs " in text or " or " in text
        if (any(kw in text for kw in _COMPARE_BRANCH_KEYWORDS)
                or (len(branches_in_text) >= 2 and has_comparison_verb)
                or (len(branches_in_text) >= 1 and any(kw in text for kw in {"vs", "or", "better"}))):
            return INTENT_COMPARE_BRANCHES

        if any(kw in text for kw in _COMPARE_COLLEGE_KEYWORDS):
            return INTENT_COMPARE_COLLEGES

        if any(kw in text for kw in _RECOMMEND_KEYWORDS):
            return INTENT_RECOMMEND

        # Anything question-like falls back to general Q&A
        question_markers = {"what", "how", "why", "when", "where", "who",
                            "is", "are", "can", "should", "do", "does", "?"}
        words = set(re.findall(r"\w+", text))
        if words & question_markers or text.endswith("?"):
            return INTENT_GENERAL_QUESTION

        return INTENT_UNKNOWN

    # ------------------------------------------------------------------
    # Profile validation
    # ------------------------------------------------------------------

    def validate_student_profile(self, student_profile: dict[str, Any]) -> bool:
        """
        Return True when the profile contains all required, non-empty fields.

        Parameters
        ----------
        student_profile : dict
            The student data dictionary to validate.

        Returns
        -------
        bool
            True  — profile is complete and ready for recommendation.
            False — one or more required fields are missing or empty.
        """
        for field in REQUIRED_PROFILE_FIELDS:
            value = student_profile.get(field)
            if value is None or str(value).strip() == "":
                logger.debug("Profile validation failed — missing field: %s", field)
                return False
        return True

    # ------------------------------------------------------------------
    # Missing information collection
    # ------------------------------------------------------------------

    def collect_missing_information(self, student_profile: dict[str, Any]) -> str:
        """
        Identify absent profile fields and return a friendly prompt asking
        the user to supply them.

        Parameters
        ----------
        student_profile : dict
            Partial student data collected so far.

        Returns
        -------
        str
            A natural-language question listing the missing fields,
            OR an empty string when the profile is already complete.
        """
        missing_labels: list[str] = []

        for field, label in REQUIRED_PROFILE_FIELDS.items():
            value = student_profile.get(field)
            if value is None or str(value).strip() == "":
                missing_labels.append(label)

        if not missing_labels:
            return ""

        if len(missing_labels) == 1:
            prompt = f"Could you please share {missing_labels[0]}?"
        else:
            items = ", ".join(missing_labels[:-1])
            prompt = (
                f"To give you personalised college recommendations, "
                f"I still need: {items} and {missing_labels[-1]}. "
                f"Could you please provide these?"
            )

        logger.info("Requesting missing profile fields: %s", missing_labels)
        return prompt

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def recommend_colleges(self, student_profile: dict[str, Any]) -> str:
        """
        Fetch college recommendations for the given student profile and
        return a formatted natural-language response.

        Delegates to services.recommendation.get_recommendations().

        Parameters
        ----------
        student_profile : dict
            Complete student profile (validated before this call).

        Returns
        -------
        str
            Formatted recommendation list or a "no results" message.
        """
        logger.info(
            "recommend_colleges called for: %s", student_profile.get("name")
        )
        result = get_recommendations(student_profile)
        colleges: list[dict[str, Any]] = result["recommendations"]

        if not colleges:
            return (
                "I couldn't find matching colleges at the moment. "
                "The recommendation engine is still being set up. "
                "Please try again shortly or adjust your preferences."
            )

        top = colleges[: self.max_recommendations]
        lines = [
            f"Here are the top {len(top)} college recommendations "
            f"for {student_profile.get('name', 'you')}:\n"
        ]
        for i, college in enumerate(top, start=1):
            name   = college.get("name",                    "N/A")
            city   = college.get("city",                    "N/A")
            branch = college.get("branch",                  "N/A")
            cutoff = college.get("cutoff",                  "N/A")
            fees   = college.get("annual_fees",             "N/A")
            naac   = college.get("naac_grade",              "N/A")
            score  = college.get("match_score",             "N/A")
            lines.append(
                f"{i}. {name} ({city})\n"
                f"   Branch: {branch} | Cutoff: {cutoff} | "
                f"Fees: ₹{fees}/yr | NAAC: {naac} | Match: {score}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # College comparison
    # ------------------------------------------------------------------

    def compare_colleges(
        self,
        college_ids: list[str],
        user_message: str = "",
    ) -> str:
        """
        Fetch side-by-side data for the given colleges and return a
        formatted comparison response.

        Delegates to services.comparison.compare_colleges().

        Parameters
        ----------
        college_ids : list[str]
            Identifiers of the colleges to compare.
        user_message : str, optional
            Original user message (used to extract college names if
            college_ids is empty).

        Returns
        -------
        str
            Formatted comparison or a prompt asking for college names.
        """
        if not college_ids:
            return (
                "Which colleges would you like to compare? "
                "Please provide at least two college names."
            )

        if len(college_ids) < 2:
            return (
                "I need at least two colleges to compare. "
                "Please provide one more college name."
            )

        logger.info("compare_colleges called for IDs: %s", college_ids)
        results: list[dict[str, Any]] = compare_colleges(college_ids)

        if not results:
            return (
                "I couldn't retrieve comparison data right now. "
                "The comparison service is still being set up. "
                "Please try again shortly."
            )

        lines = ["Here is a side-by-side comparison:\n"]
        fields = [
            ("City",             "city"),
            ("Branch",           "branch"),
            ("Cutoff",           "cutoff"),
            ("Annual Fees",      "fees"),
            ("NAAC Grade",       "naac"),
            ("NBA Accredited",   "nba"),
            ("Avg Placement",    "placement"),
            ("Intake",           "intake"),
            ("Established",      "estd"),
            ("Type",             "type"),
        ]
        for label, key in fields:
            row_parts = [f"{label:<18}"]
            for college in results:
                row_parts.append(str(college.get(key, "N/A")))
            lines.append(" | ".join(row_parts))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Branch comparison
    # ------------------------------------------------------------------

    def compare_branches(self, user_message: str) -> str:
        """
        Compare two or more engineering branches and return a structured
        summary to help the user decide.

        Parameters
        ----------
        user_message : str
            User's raw message, expected to name the branches to compare.

        Returns
        -------
        str
            Formatted branch comparison or a clarification prompt.

        NOTE
        ----
        Branch metadata is currently static.  A future version should
        pull live placement / demand data from the dataset service.
        """
        logger.info("compare_branches called | message: %s", user_message)

        # Re-use the module-level canonical list (title-cased for display)
        title_branches = [b.title() for b in KNOWN_BRANCHES]

        text = user_message.lower()
        matched = [b for b in title_branches if b.lower() in text]

        if len(matched) < 2:
            return (
                "Which branches would you like to compare? "
                "For example: 'Compare Computer Engineering vs Mechanical Engineering'."
            )

        # Static summary data — replace with dataset lookup once available
        # Keys must match str.title() of KNOWN_BRANCHES entries exactly
        branch_info: dict[str, dict[str, str]] = {
            "Computer Engineering":                  {"demand": "Very High", "avg_package": "₹8–15 LPA"},
            "Information Technology":                {"demand": "High",      "avg_package": "₹7–13 LPA"},
            "Electronics And Telecommunication":     {"demand": "Moderate",  "avg_package": "₹5–10 LPA"},
            "Mechanical Engineering":                {"demand": "Moderate",  "avg_package": "₹4–8 LPA"},
            "Civil Engineering":                     {"demand": "Moderate",  "avg_package": "₹4–7 LPA"},
            "Electrical Engineering":                {"demand": "Moderate",  "avg_package": "₹5–9 LPA"},
            "Artificial Intelligence":               {"demand": "Very High", "avg_package": "₹9–18 LPA"},
            "Data Science":                          {"demand": "Very High", "avg_package": "₹8–16 LPA"},
        }

        lines = [f"Branch comparison — {' vs '.join(matched)}:\n"]
        header = f"{'Metric':<22}" + "".join(f"{b[:22]:<24}" for b in matched)
        lines.append(header)
        lines.append("-" * len(header))

        for metric in ("demand", "avg_package"):
            label = "Industry Demand" if metric == "demand" else "Avg Package"
            row   = f"{label:<22}"
            for branch in matched:
                info = branch_info.get(branch, {})
                row += f"{info.get(metric, 'N/A'):<24}"
            lines.append(row)

        lines.append(
            "\nNote: Package figures are indicative. "
            "Actual data will be pulled from the live dataset once it is populated."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # General Q&A
    # ------------------------------------------------------------------

    def answer_general_question(self, user_message: str) -> str:
        """
        Forward a general or unclassified question to the Watsonx service
        and return the AI-generated response.

        Delegates to services.watsonx.chat().

        Parameters
        ----------
        user_message : str
            The user's question or unclassified input.

        Returns
        -------
        str
            AI-generated reply (or the Watsonx stub message until the
            service is configured).
        """
        logger.info("answer_general_question delegating to watsonx.chat()")
        system_prompt = (
            "You are a helpful College Admission Assistant specialising in "
            "Maharashtra engineering admissions (MHT-CET). "
            "Answer clearly and concisely. If you do not know, say so."
        )
        return watsonx_chat(user_message, system_prompt=system_prompt)
