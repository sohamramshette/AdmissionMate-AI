"""
College Admission Assistant — Flask Application Entry Point
===========================================================
Main Flask application that wires together routes, templates,
and service modules.  AI-specific logic is intentionally left
as stubs so the UI / navigation layer can be developed and
validated independently.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import Config
from services.recommendation import get_recommendations
from services.cap_generator import collect_cap_form_data, get_branch_groups

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(config_class=Config):
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # -----------------------------------------------------------------------
    # Route: Home
    # -----------------------------------------------------------------------
    @app.route("/")
    def home():
        """Landing page with hero section, description, and feature cards."""
        return render_template("home.html", title="Home")

    # -----------------------------------------------------------------------
    # Route: Student Form  (GET → render / POST → process)
    # -----------------------------------------------------------------------
    @app.route("/find-colleges", methods=["GET", "POST"])
    def find_colleges():
        """Collect student details and forward to the recommendations page."""
        if request.method == "POST":
            # Gather form fields
            student_data = {
                "name":              request.form.get("name", "").strip(),
                "cet_percentile":    request.form.get("cet_percentile", ""),
                "category":          request.form.get("category", ""),
                "preferred_branch":  request.form.get("preferred_branch", ""),
                "preferred_city":    request.form.get("preferred_city", ""),
            }

            # Basic validation — all fields required
            if not all(student_data.values()):
                flash("Please fill in all fields before proceeding.", "warning")
                return render_template("student_form.html", title="Find Colleges",
                                       student_data=student_data)

            # Persist to session so the recommendations page can access it
            from flask import session
            session["student_data"] = student_data
            return redirect(url_for("recommendations"))

        return render_template("student_form.html", title="Find Colleges")

    # -----------------------------------------------------------------------
    # Route: Recommendations
    # -----------------------------------------------------------------------
    @app.route("/recommendations")
    def recommendations():
        """Display personalized college recommendations."""

        from flask import session

        student_data = session.get("student_data", {})

        if student_data:
            recommendation_data = get_recommendations(student_data)
        else:
            recommendation_data = {
                "recommendations": [],
                "summary": ""
            }

        return render_template(
            "recommendations.html",
            title="Recommendations",
            student_data=student_data,
            colleges=recommendation_data["recommendations"],
            summary=recommendation_data["summary"],
        )

    # -----------------------------------------------------------------------
    # Route: College Details
    # -----------------------------------------------------------------------
    @app.route("/college/<college_id>")
    def college_details(college_id: str):
        """
        Display the full profile page for a single college.

        The college_id comes from the dataset (e.g. ``COEP001``).
        Returns 404 when the ID is not found.
        """
        from services.college_details import get_college_profile

        profile = get_college_profile(college_id)
        if profile is None:
            from flask import abort
            abort(404)

        return render_template(
            "college_details.html",
            title=profile["name"],
            college=profile,
        )

    # -----------------------------------------------------------------------
    # Route: College Comparison
    # -----------------------------------------------------------------------
    @app.route("/compare")
    def compare():
        """Side-by-side college comparison table (placeholder)."""
        # TODO: call services.comparison.compare_colleges(selected_ids)
        colleges = []  # Placeholder
        return render_template("compare.html", title="Compare Colleges",
                               colleges=colleges)

    # -----------------------------------------------------------------------
    # Route: AI CAP Preference Generator
    # -----------------------------------------------------------------------
    @app.route("/cap-generator", methods=["GET", "POST"])
    def cap_generator():
        """Multi-step wizard to collect CAP preference inputs from the student."""
        from services.cap_algorithm import generate_cap_preferences
        from services.dataset import (
            get_available_universities, get_available_cities, load_dataset,
            COL_ID, COL_NAME, COL_BRANCH,
        )

        # Load unique dropdown values from the production dataset
        try:
            universities = get_available_universities()
            cities       = get_available_cities()
            df           = load_dataset()
            print(f"[CAP] Dataset loaded: {len(df)} rows, "
                  f"{df[COL_ID].nunique()} colleges, "
                  f"{df[COL_BRANCH].nunique()} branches")
        except Exception as exc:
            universities = []
            cities       = []
            print(f"[CAP] Dataset load failed: {exc}")

        # Branch groups come from branch_mapping.csv (sorted group names only)
        branch_groups = list(get_branch_groups().keys())

        if request.method == "POST":
            form_data = collect_cap_form_data(request.form)

            # ── Run the algorithm ─────────────────────────────────────────
            print("[CAP] Calling generate_cap_preferences ...")
            print("[CAP] Profile: "
                  f"percentile={form_data.get('cet_percentile')}, "
                  f"category={form_data.get('category')}, "
                  f"cities={form_data.get('preferred_cities')}, "
                  f"branch_groups={form_data.get('preferred_branch_groups')}, "
                  f"priority={form_data.get('priority_style')}, "
                  f"strategy={form_data.get('strategy')}, "
                  f"max_pref={form_data.get('max_preferences')}")

            try:
                preferences = generate_cap_preferences(form_data)
                print(f"[CAP] generate_cap_preferences returned {len(preferences)} preferences")
            except Exception as exc:
                import traceback
                print(f"[CAP] ERROR in generate_cap_preferences: {exc}")
                traceback.print_exc()
                preferences = []

            return render_template(
                "cap_result.html",
                title="CAP Preference List",
                form_data=form_data,
                preferences=preferences,
            )

        return render_template(
            "cap_generator.html",
            title="AI CAP Generator",
            universities=universities,
            cities=cities,
            branch_groups=branch_groups,
        )

    # -----------------------------------------------------------------------
    # Route: AI Chatbot
    # -----------------------------------------------------------------------
    @app.route("/chatbot")
    def chatbot():
        """Conversational AI chat interface powered by IBM Watsonx (placeholder)."""
        return render_template("chatbot.html", title="AI Chat Assistant")

    # -----------------------------------------------------------------------
    # API: Chat message endpoint (consumed by frontend JS)
    # -----------------------------------------------------------------------
    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """
        Receive a user message via JSON, run it through the RAG pipeline,
        and return the assistant's reply.

        Flow: intent detection → dataset retrieval → context injection → Granite.
        Falls back to a direct Watsonx call when no dataset match is found.
        """
        payload = request.get_json(silent=True) or {}
        user_message = payload.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        from services.rag import rag_chat

        reply = rag_chat(user_message)
        return jsonify({"reply": reply})

    return app


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
import os

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", True)
    )
