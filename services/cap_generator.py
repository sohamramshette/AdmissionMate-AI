"""
services/cap_generator.py
=========================
AI CAP Preference Generator — service layer.

Receives validated form data from the Flask wizard and returns a clean dict.
No algorithm, no dataset processing, no AI calls.

Wizard step → form field mapping
---------------------------------
  Step 1  cet_percentile
  Step 2  category
  Step 3  gender
  Step 4  home_university
  Step 5  preferred_cities         list  (empty when Any City was selected)
  Step 6  selected_branches_ordered  comma-separated hidden field
  Step 7  priority_style
  Step 8  strategy
  (Step 9 is Review & Generate — no new fields)
"""

from __future__ import annotations
import os
import pprint


def get_branch_groups() -> dict[str, list[str]]:
    """
    Read dataset/branch_mapping.csv and return a dict of
    { User_Preference: [Mapped_Branch, ...] } sorted by preference name.
    """
    import csv

    mapping: dict[str, list[str]] = {}
    csv_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "dataset", "branch_mapping.csv")
    )

    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                group  = row.get("User_Preference", "").strip()
                branch = row.get("Mapped_Branch", "").strip()
                if group and branch:
                    mapping.setdefault(group, []).append(branch)
    except FileNotFoundError:
        pass

    return dict(sorted(mapping.items()))


def collect_cap_form_data(form) -> dict:
    """
    Parse ``request.form`` from the CAP wizard and return a clean dict.

    Parameters
    ----------
    form : werkzeug.datastructures.ImmutableMultiDict
        The raw ``request.form`` object from the Flask POST handler.

    Returns
    -------
    dict
        Structured representation of every wizard field.
    """

    # Step 1 — CET Percentile
    cet_percentile = form.get("cet_percentile", "").strip()

    # Step 2 — Category
    category = form.get("category", "").strip()

    # Step 3 — Gender
    gender = form.get("gender", "").strip()

    # Step 4 — Home University
    home_university = form.get("home_university", "").strip()

    # Step 5 — Preferred Cities
    # Empty list means the student chose "Any City".
    preferred_cities = form.getlist("preferred_cities")

    # Step 6 — Preferred Branch Groups (ordered, from hidden input)
    raw_branches = form.get("selected_branches_ordered", "").strip()
    preferred_branch_groups = (
        [b.strip() for b in raw_branches.split(",") if b.strip()]
        if raw_branches
        else []
    )

    # Step 7 — Priority Style
    priority_style = form.get("priority_style", "").strip()

    # Step 8 — Strategy
    strategy = form.get("strategy", "Balanced").strip()

    # Step 7/9 — Maximum Preferences (optional radio: 50 / 75 / 100)
    max_preferences = form.get("max_preferences", "").strip()

    # Assemble result
    data = {
        "cet_percentile":          cet_percentile,
        "category":                category,
        "gender":                  gender,
        "home_university":         home_university,
        "preferred_cities":        preferred_cities,
        "preferred_branch_groups": preferred_branch_groups,
        "priority_style":          priority_style,
        "strategy":                strategy,
        "max_preferences":         max_preferences or "No limit",
    }

    # Print to server console
    print("\n" + "=" * 60)
    print("AI CAP PREFERENCE GENERATOR — FORM SUBMISSION")
    print("=" * 60)
    pprint.pprint(data)
    print("=" * 60 + "\n")

    return data
