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
    # Context Processor: Inject student profile globally into templates
    # -----------------------------------------------------------------------
    @app.context_processor
    def inject_user_profile():
        from flask import session
        prof = session.get("student_profile") or session.get("student_data") or {}
        return {"current_student": prof}

    # -----------------------------------------------------------------------
    # Route: Profile Management (Dedicated Student Profile Hub)
    # -----------------------------------------------------------------------
    @app.route("/profile", methods=["GET"])
    def profile():
        """Dedicated student profile hub and credentials dashboard."""
        from flask import session
        from services.dataset import get_available_cities, get_available_universities

        # Load profile data from session
        profile_data = session.get("student_profile")
        if not profile_data:
            # Fallback to student_data if present
            profile_data = session.get("student_data", {})

        # Calculate profile completion percentage
        key_fields = ["name", "cet_percentile", "category", "preferred_branch", "preferred_city", "hsc_percentage", "home_university"]
        filled_count = sum(1 for k in key_fields if profile_data.get(k))
        completion_score = int((filled_count / len(key_fields)) * 100) if key_fields else 0
        if completion_score == 0 and profile_data.get("name"):
            completion_score = 35

        # Load dropdown lists
        try:
            cities = get_available_cities()
            universities = get_available_universities()
        except Exception:
            cities = []
            universities = []

        # Top colleges preview if percentile is available
        top_colleges = []
        if profile_data.get("cet_percentile"):
            try:
                rec_res = get_recommendations(profile_data)
                top_colleges = rec_res.get("recommendations", [])
            except Exception:
                top_colleges = []

        return render_template(
            "profile.html",
            title="Student Profile",
            profile=profile_data,
            completion_score=completion_score,
            cities=cities,
            universities=universities,
            top_colleges=top_colleges
        )

    @app.route("/profile/save", methods=["POST"])
    def profile_save():
        """Save student profile details to session."""
        from flask import session

        profile_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "gender": request.form.get("gender", ""),
            "application_id": request.form.get("application_id", "").strip(),
            "domicile": request.form.get("domicile", ""),
            "hsc_percentage": request.form.get("hsc_percentage", ""),
            "pcm_marks": request.form.get("pcm_marks", ""),
            "ssc_percentage": request.form.get("ssc_percentage", ""),

            "cet_percentile": request.form.get("cet_percentile", "").strip(),
            "exam_group": request.form.get("exam_group", "PCM"),
            "jee_percentile": request.form.get("jee_percentile", "").strip(),
            "category": request.form.get("category", "OPEN"),
            "home_university": request.form.get("home_university", ""),
            "annual_family_income": request.form.get("annual_family_income", ""),

            "tfws_eligible": request.form.get("tfws_eligible") == "yes",
            "defence_quota": request.form.get("defence_quota") == "yes",
            "pwd_quota": request.form.get("pwd_quota") == "yes",
            "minority_quota": request.form.get("minority_quota") == "yes",

            "preferred_branch": request.form.get("preferred_branch", ""),
            "preferred_city": request.form.get("preferred_city", ""),
            "max_fees": request.form.get("max_fees", "Any"),
            "college_type_pref": request.form.get("college_type_pref", "Any"),

            "doc_cet_scorecard": request.form.get("doc_cet_scorecard") == "ready",
            "doc_hsc_marksheet": request.form.get("doc_hsc_marksheet") == "ready",
            "doc_ssc_marksheet": request.form.get("doc_ssc_marksheet") == "ready",
            "doc_domicile": request.form.get("doc_domicile") == "ready",
            "doc_caste_cert": request.form.get("doc_caste_cert") == "ready",
            "doc_caste_validity": request.form.get("doc_caste_validity") == "ready",
            "doc_ncl": request.form.get("doc_ncl") == "ready",
            "doc_income_cert": request.form.get("doc_income_cert") == "ready",
            "doc_nationality": request.form.get("doc_nationality") == "ready",
            "doc_gap_cert": request.form.get("doc_gap_cert") == "ready",
        }

        session["student_profile"] = profile_data
        # Sync core student_data for compatibility with existing recommendation / comparison flows
        session["student_data"] = {
            "name": profile_data["name"],
            "cet_percentile": profile_data["cet_percentile"],
            "category": profile_data["category"],
            "preferred_branch": profile_data["preferred_branch"],
            "preferred_city": profile_data["preferred_city"],
        }

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    @app.route("/profile/reset", methods=["GET", "POST"])
    def profile_reset():
        """Reset profile data in session."""
        from flask import session
        session.pop("student_profile", None)
        session.pop("student_data", None)
        flash("Profile has been reset.", "info")
        return redirect(url_for("profile"))

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
        from flask import session

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
                saved_profile = session.get("student_profile") or session.get("student_data") or {}
                return render_template("student_form.html", title="Find Colleges",
                                       student_data=student_data, saved_profile=saved_profile)

            # Persist to session so the recommendations page can access it
            session["student_data"] = student_data
            
            # Sync to student_profile as well
            if "student_profile" not in session or not session["student_profile"]:
                session["student_profile"] = student_data
            else:
                session["student_profile"].update(student_data)

            return redirect(url_for("recommendations"))

        # Pre-populate form if user already saved a profile
        existing_profile = session.get("student_profile") or session.get("student_data") or {}
        return render_template("student_form.html", title="Find Colleges", student_data=existing_profile, saved_profile=existing_profile)

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
        """Side-by-side dynamic college comparison page."""
        return render_template("compare.html", title="Compare Colleges")

    # -----------------------------------------------------------------------
    # API: Search colleges by name (for comparison modal)
    # -----------------------------------------------------------------------
    @app.route("/api/colleges/search")
    def api_colleges_search():
        """
        Return colleges matching a name query for the comparison search modal.

        Query params:
            q : str   Search term (case-insensitive, partial match)

        Returns JSON array of {id, name, city, home_university}.
        """
        from services.comparison import get_college_directory

        q = request.args.get("q", "").strip().lower()
        directory = get_college_directory()

        if q:
            results = [
                c for c in directory
                if q in c["name"].lower() or q in c["city"].lower()
            ]
        else:
            results = directory

        # Return only the fields needed by the frontend
        return jsonify([
            {
                "id":              c["id"],
                "name":            c["name"],
                "city":            c["city"],
                "home_university": c["home_university"],
                "branch_count":    c["branch_count"],
                "avg_fees":        c["avg_fees"],
                "avg_cutoff":      c["avg_cutoff"],
            }
            for c in results[:50]   # cap at 50 results
        ])

    # -----------------------------------------------------------------------
    # API: Compare colleges endpoint
    # -----------------------------------------------------------------------
    @app.route("/api/compare", methods=["POST"])
    def api_compare():
        """
        Accept a list of college IDs, return comparison data + AI summary.

        Request JSON: { "ids": [1, 2, 3] }

        Response JSON: {
            "colleges": [...],
            "summary":  "..."
        }
        """
        from services.comparison import compare_colleges, generate_comparison_summary

        payload = request.get_json(silent=True) or {}
        ids = payload.get("ids", [])

        if not ids or not isinstance(ids, list):
            return jsonify({"error": "Provide a JSON list of college IDs under 'ids'."}), 400

        # Clamp to max 4
        ids = ids[:4]

        colleges = compare_colleges(ids)
        summary  = generate_comparison_summary(colleges)

        return jsonify({"colleges": colleges, "summary": summary})

    # -----------------------------------------------------------------------
    # Route: AI Branch Advisor (questionnaire page)
    # -----------------------------------------------------------------------
    @app.route("/branch-advisor", methods=["GET", "POST"])
    def branch_advisor():
        """
        Multi-step questionnaire that collects student interests and
        forwards them to the AI branch recommendation engine.
        """
        if request.method == "POST":
            from services.branch_advisor import recommend_branches

            profile = {
                "subjects":           request.form.getlist("subjects"),
                "work_type":          request.form.getlist("work_type"),
                "activities":         request.form.getlist("activities"),
                "career_goal":        request.form.get("career_goal", "").strip(),
                "enjoys_programming": request.form.get("enjoys_programming", "").strip(),
                "work_env":           request.form.get("work_env", "").strip(),
                "priority":           request.form.get("priority", "").strip(),
                "math_comfort":       request.form.get("math_comfort", "").strip(),
            }

            # Persist profile for the result page
            from flask import session
            session["branch_profile"] = profile

            result = recommend_branches(profile)

            return render_template(
                "branch_result.html",
                title="Branch Recommendation",
                profile=profile,
                result=result,
            )

        return render_template("branch_advisor.html", title="AI Branch Advisor")

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

        from flask import session
        saved_profile = session.get("student_profile") or session.get("student_data") or {}

        return render_template(
            "cap_generator.html",
            title="AI CAP Generator",
            universities=universities,
            cities=cities,
            branch_groups=branch_groups,
            saved_profile=saved_profile,
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
