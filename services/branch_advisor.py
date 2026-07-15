"""
services/branch_advisor.py
==========================
AI Branch Recommendation Service
---------------------------------
Accepts a student interest profile and returns a ranked list of
engineering branch recommendations with compatibility scores,
career paths, skill roadmaps, and an AI-generated explanation.

Public API
----------
    recommend_branches(profile: dict) -> dict
        Returns: {
            primary:      dict   – top branch with score, bullets, roadmap
            alternatives: list   – next 2–3 branches with score + reason
            summary:      str    – overall AI advisory paragraph
        }

AI strategy
-----------
1. Build a rich prompt from the 8-question profile.
2. Call IBM Watsonx Granite (via services.watsonx.chat).
3. Parse the structured JSON block in the AI response.
4. If parsing fails or Watsonx is unavailable, fall back to a
   deterministic rule-based engine that produces the same schema.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Branch metadata catalogue  (static knowledge — never inferred)
# ---------------------------------------------------------------------------

BRANCH_CATALOGUE: dict[str, dict[str, Any]] = {
    "Computer Engineering": {
        "icon":          "bi-laptop-fill",
        "color":         "icon-indigo",
        "difficulty":    4,
        "salary":        5,
        "placement":     5,
        "higher_studies":4,
        "coding_req":    5,
        "math_req":      4,
        "future_demand": 5,
        "career_path": [
            "Software Engineer",
            "Full Stack Developer",
            "AI / ML Engineer",
            "Cloud Engineer",
            "DevOps Engineer",
            "Technical Architect",
            "CTO",
        ],
        "skills": {
            "Core":        ["Python", "C++", "DSA", "Git", "Databases"],
            "Systems":     ["Operating Systems", "Computer Networks", "Cloud Computing"],
            "Advanced":    ["Machine Learning", "Web Dev", "System Design"],
        },
        "roadmap": {
            "Year 1": ["Programming Basics (Python, C)", "Mathematics", "Git & Linux"],
            "Year 2": ["DSA", "DBMS", "Operating Systems", "Computer Networks"],
            "Year 3": ["Web Development", "Machine Learning", "Projects", "Internship"],
            "Year 4": ["System Design", "Open Source", "Interview Prep", "Resume"],
        },
        "recruiters": ["Google", "Microsoft", "Amazon", "Meta", "IBM", "TCS", "Infosys", "Wipro"],
        "keywords": ["coding", "computer science", "software", "ai", "gaming", "cybersecurity",
                     "logical thinking", "problem solving", "software engineer", "ai engineer",
                     "data scientist", "full stack", "cloud", "devops", "startup"],
    },
    "Artificial Intelligence & Data Science": {
        "icon":          "bi-cpu-fill",
        "color":         "icon-sky",
        "difficulty":    4,
        "salary":        5,
        "placement":     5,
        "higher_studies":5,
        "coding_req":    4,
        "math_req":      5,
        "future_demand": 5,
        "career_path": [
            "Data Analyst",
            "Data Scientist",
            "ML Engineer",
            "AI Researcher",
            "NLP Engineer",
            "AI Product Manager",
            "Research Scientist",
        ],
        "skills": {
            "Core":        ["Python", "R", "Statistics", "SQL", "NumPy / Pandas"],
            "ML/AI":       ["Machine Learning", "Deep Learning", "TensorFlow", "PyTorch"],
            "Advanced":    ["NLP", "Computer Vision", "MLOps", "Research Writing"],
        },
        "roadmap": {
            "Year 1": ["Python", "Statistics & Probability", "Linear Algebra", "SQL"],
            "Year 2": ["Machine Learning", "Data Visualisation", "DBMS", "Cloud Basics"],
            "Year 3": ["Deep Learning", "NLP / CV Projects", "Kaggle / Research", "Internship"],
            "Year 4": ["MLOps", "Publications / Patents", "Interview Prep", "Portfolio"],
        },
        "recruiters": ["Google DeepMind", "OpenAI", "IBM Research", "Amazon AWS",
                       "Mu Sigma", "Fractal Analytics", "Tiger Analytics"],
        "keywords": ["ai", "research", "data", "mathematics", "problem solving",
                     "ai engineer", "data scientist", "machine learning", "higher studies",
                     "research", "analytics"],
    },
    "Information Technology": {
        "icon":          "bi-hdd-network-fill",
        "color":         "icon-emerald",
        "difficulty":    3,
        "salary":        4,
        "placement":     5,
        "higher_studies":3,
        "coding_req":    4,
        "math_req":      3,
        "future_demand": 4,
        "career_path": [
            "Software Developer",
            "Web Developer",
            "IT Consultant",
            "Network Engineer",
            "Cloud Architect",
            "IT Manager",
        ],
        "skills": {
            "Core":        ["Java", "Python", "HTML/CSS/JS", "SQL", "Networking"],
            "Platforms":   ["Linux", "Cloud (AWS/GCP)", "Docker", "Kubernetes"],
            "Advanced":    ["Microservices", "Security", "Agile / Scrum"],
        },
        "roadmap": {
            "Year 1": ["Java / Python Basics", "HTML & CSS", "Networking Fundamentals"],
            "Year 2": ["Web Development", "DBMS", "Operating Systems", "Linux"],
            "Year 3": ["Cloud Computing", "DevOps", "Project Work", "Internship"],
            "Year 4": ["Certifications (AWS, GCP)", "Open Source", "Placement Prep"],
        },
        "recruiters": ["TCS", "Infosys", "Accenture", "Wipro", "Cognizant",
                       "HCL", "Capgemini", "Oracle"],
        "keywords": ["coding", "computer science", "software", "logical thinking",
                     "office", "remote", "high salary", "software engineer", "it"],
    },
    "Cyber Security": {
        "icon":          "bi-shield-lock-fill",
        "color":         "icon-amber",
        "difficulty":    4,
        "salary":        5,
        "placement":     4,
        "higher_studies":4,
        "coding_req":    4,
        "math_req":      3,
        "future_demand": 5,
        "career_path": [
            "Security Analyst",
            "Penetration Tester (Ethical Hacker)",
            "SOC Analyst",
            "Cyber Forensics Expert",
            "Security Architect",
            "CISO",
        ],
        "skills": {
            "Core":        ["Networking", "Linux", "Python", "Cryptography"],
            "Security":    ["Ethical Hacking", "SIEM Tools", "Malware Analysis", "CTF"],
            "Certs":       ["CEH", "CompTIA Security+", "CISSP", "OSCP"],
        },
        "roadmap": {
            "Year 1": ["Networking Basics", "Linux & Python", "Operating Systems"],
            "Year 2": ["Ethical Hacking", "Cryptography", "Network Security"],
            "Year 3": ["SIEM / SOC", "CTF Competitions", "Bug Bounty", "Internship"],
            "Year 4": ["Certifications (CEH, OSCP)", "Research", "Placement Prep"],
        },
        "recruiters": ["Cisco", "Palo Alto Networks", "IBM Security", "Deloitte",
                       "KPMG", "CERT-In", "TCS Cyber", "HackerOne"],
        "keywords": ["cybersecurity", "gaming", "logical thinking", "problem solving",
                     "security", "networking", "cybersecurity engineer", "research", "startup"],
    },
    "Electronics & Telecommunication Engineering": {
        "icon":          "bi-broadcast-pin",
        "color":         "icon-sky",
        "difficulty":    4,
        "salary":        4,
        "placement":     4,
        "higher_studies":5,
        "coding_req":    3,
        "math_req":      5,
        "future_demand": 4,
        "career_path": [
            "VLSI Design Engineer",
            "Embedded Systems Engineer",
            "Telecom Engineer",
            "IoT Engineer",
            "RF Engineer",
            "Semiconductor Engineer",
            "Research Scientist",
        ],
        "skills": {
            "Core":        ["Circuit Theory", "Signals & Systems", "Embedded C", "VHDL"],
            "Platforms":   ["Arduino", "Raspberry Pi", "FPGA", "MATLAB"],
            "Advanced":    ["5G / 6G", "IoT Protocols", "VLSI Design", "PCB Design"],
        },
        "roadmap": {
            "Year 1": ["Circuit Theory", "Physics", "Basic Electronics", "C Programming"],
            "Year 2": ["Signals & Systems", "Microprocessors", "Communication Systems"],
            "Year 3": ["VLSI / Embedded", "IoT Projects", "Antenna Design", "Internship"],
            "Year 4": ["GATE Prep / Industry Projects", "Research", "Certifications"],
        },
        "recruiters": ["Qualcomm", "Intel", "Samsung R&D", "ISRO", "DRDO", "TATA Elxsi",
                       "Texas Instruments", "Broadcom"],
        "keywords": ["electronics", "physics", "robotics", "research", "laboratory",
                     "higher studies", "government jobs", "innovation", "hardware",
                     "telecom", "embedded", "iot"],
    },
    "Electrical Engineering": {
        "icon":          "bi-lightning-charge-fill",
        "color":         "icon-amber",
        "difficulty":    4,
        "salary":        4,
        "placement":     4,
        "higher_studies":4,
        "coding_req":    2,
        "math_req":      5,
        "future_demand": 4,
        "career_path": [
            "Power Systems Engineer",
            "Electrical Design Engineer",
            "Automation Engineer",
            "Control Systems Engineer",
            "Energy Consultant",
            "Government PSU Engineer",
        ],
        "skills": {
            "Core":        ["Circuit Analysis", "Power Systems", "Control Theory", "MATLAB"],
            "Tools":       ["AutoCAD Electrical", "ETAP", "PLC / SCADA"],
            "Advanced":    ["Renewable Energy", "Smart Grid", "Motor Drives"],
        },
        "roadmap": {
            "Year 1": ["Circuit Theory", "Mathematics", "Physics", "Engineering Drawing"],
            "Year 2": ["Power Systems", "Electrical Machines", "Control Systems"],
            "Year 3": ["Power Electronics", "PLC / SCADA", "Renewable Energy", "Internship"],
            "Year 4": ["GATE / PSU Prep", "Industrial Projects", "Certifications"],
        },
        "recruiters": ["TATA Power", "Siemens", "ABB", "Schneider Electric",
                       "BHEL", "MAHADISCOM", "L&T", "NTPC"],
        "keywords": ["electricity", "physics", "field work", "government jobs",
                     "job stability", "government sector", "building", "power",
                     "automation", "energy", "renewable"],
    },
    "Mechanical Engineering": {
        "icon":          "bi-gear-fill",
        "color":         "icon-emerald",
        "difficulty":    4,
        "salary":        3,
        "placement":     3,
        "higher_studies":4,
        "coding_req":    2,
        "math_req":      5,
        "future_demand": 3,
        "career_path": [
            "Design Engineer",
            "Manufacturing Engineer",
            "Automobile Engineer",
            "Thermal Engineer",
            "Robotics Engineer",
            "Product Manager",
            "PSU / Government Engineer",
        ],
        "skills": {
            "Core":        ["CAD/CAM (SolidWorks, CATIA)", "Thermodynamics", "FEA"],
            "Software":    ["ANSYS", "AutoCAD", "MATLAB"],
            "Advanced":    ["Robotics", "Additive Manufacturing", "Industry 4.0"],
        },
        "roadmap": {
            "Year 1": ["Engineering Drawing", "Workshop", "Physics", "Mathematics"],
            "Year 2": ["Thermodynamics", "Fluid Mechanics", "Manufacturing Processes"],
            "Year 3": ["CAD/CAM", "Robotics", "FEA / CFD Projects", "Internship"],
            "Year 4": ["GATE / UPSC Prep", "Core Industry Projects", "Certifications"],
        },
        "recruiters": ["Tata Motors", "Mahindra", "Bajaj Auto", "L&T",
                       "ISRO", "DRDO", "Bosch", "Cummins", "Honeywell"],
        "keywords": ["building machines", "physics", "creativity", "designing",
                     "field work", "government jobs", "innovation", "manufacturing",
                     "automobile", "robotics", "mechanical"],
    },
    "Civil Engineering": {
        "icon":          "bi-building-fill",
        "color":         "icon-sky",
        "difficulty":    3,
        "salary":        3,
        "placement":     3,
        "higher_studies":4,
        "coding_req":    1,
        "math_req":      4,
        "future_demand": 3,
        "career_path": [
            "Structural Engineer",
            "Site Engineer",
            "Urban Planner",
            "Environmental Engineer",
            "Project Manager",
            "Government PWD Engineer",
        ],
        "skills": {
            "Core":        ["AutoCAD", "Structural Design", "Surveying", "Soil Mechanics"],
            "Software":    ["STAAD.Pro", "REVIT", "GIS"],
            "Advanced":    ["Green Building", "Smart Cities", "Project Management"],
        },
        "roadmap": {
            "Year 1": ["Engineering Drawing", "Surveying", "Mathematics", "Chemistry"],
            "Year 2": ["Structural Analysis", "Concrete Technology", "Soil Mechanics"],
            "Year 3": ["Steel Design", "Transportation", "Site Projects", "Internship"],
            "Year 4": ["GATE / UPSC Prep", "Design Projects", "Certifications"],
        },
        "recruiters": ["L&T Construction", "Shapoorji Pallonji", "NHAI", "MCGM",
                       "PWD Maharashtra", "Tata Projects", "Afcons", "Gammon India"],
        "keywords": ["building", "creativity", "field work", "government jobs",
                     "designing", "innovation", "environment", "civil", "infrastructure"],
    },
    "Chemical Engineering": {
        "icon":          "bi-droplet-fill",
        "color":         "icon-indigo",
        "difficulty":    4,
        "salary":        3,
        "placement":     3,
        "higher_studies":5,
        "coding_req":    2,
        "math_req":      5,
        "future_demand": 3,
        "career_path": [
            "Process Engineer",
            "Chemical Plant Manager",
            "Pharmaceutical Engineer",
            "Environmental Engineer",
            "R&D Scientist",
            "Refinery Engineer",
        ],
        "skills": {
            "Core":        ["Thermodynamics", "Fluid Mechanics", "Mass Transfer", "Reaction Kinetics"],
            "Software":    ["ASPEN Plus", "MATLAB", "AutoCAD P&ID"],
            "Advanced":    ["Process Simulation", "Safety Engineering", "Green Chemistry"],
        },
        "roadmap": {
            "Year 1": ["Chemistry", "Mathematics", "Engineering Basics"],
            "Year 2": ["Chemical Process Industries", "Mass Transfer", "Thermodynamics"],
            "Year 3": ["Process Control", "Petroleum Refining", "Lab Projects", "Internship"],
            "Year 4": ["GATE Prep", "Research Projects", "Industry Certifications"],
        },
        "recruiters": ["Reliance Industries", "ONGC", "IOCL", "BASF India",
                       "CIPLA", "Sun Pharma", "Hindustan Unilever", "UPL"],
        "keywords": ["chemistry", "research", "laboratory", "higher studies",
                     "physics", "innovation", "chemical", "pharmaceutical"],
    },
}

BRANCH_NAMES = list(BRANCH_CATALOGUE.keys())

# ---------------------------------------------------------------------------
# System prompt for Watsonx
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are AdmissionMate AI, an expert engineering branch counsellor for Maharashtra students.
Analyse the student profile and recommend the TOP 4 most suitable engineering branches.

RULES:
- Use ONLY the branches provided in AVAILABLE_BRANCHES.
- Produce a valid JSON object (no markdown, no explanation outside JSON).
- Compatibility scores must be integers between 50 and 98.
- Each bullet must be a single sentence under 20 words.
- Do NOT repeat the same branch name more than once.

OUTPUT FORMAT (strict JSON, no other text):
{
  "primary": {
    "branch": "<branch name from list>",
    "score": <integer 50-98>,
    "bullets": ["<reason 1>", "<reason 2>", "<reason 3>", "<reason 4>", "<reason 5>"]
  },
  "alternatives": [
    {"branch": "<name>", "score": <int>, "reason": "<1-sentence reason>"},
    {"branch": "<name>", "score": <int>, "reason": "<1-sentence reason>"},
    {"branch": "<name>", "score": <int>, "reason": "<1-sentence reason>"}
  ],
  "summary": "<2-3 sentence personalised advisory paragraph>"
}"""


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def recommend_branches(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Generate branch recommendations for the supplied student profile.

    Parameters
    ----------
    profile : dict
        Keys: subjects, work_type, activities, career_goal,
              enjoys_programming, work_env, priority, math_comfort

    Returns
    -------
    dict
        primary      – top branch record (branch, score, bullets, metadata)
        alternatives – list of 2–3 alternative branch records
        summary      – AI advisory paragraph
    """
    ai_result = _call_watsonx(profile)
    if ai_result is None:
        logger.info("Watsonx unavailable — using fallback recommendation engine.")
        ai_result = _fallback_recommend(profile)

    return _enrich(ai_result)


# ---------------------------------------------------------------------------
# Watsonx call
# ---------------------------------------------------------------------------

def _call_watsonx(profile: dict[str, Any]) -> dict[str, Any] | None:
    """
    Build a prompt, call Watsonx, and parse the JSON response.
    Returns None on any failure.
    """
    try:
        from services.watsonx import chat

        user_msg = _build_prompt(profile)
        raw = chat(user_msg, system_prompt=_SYSTEM_PROMPT)

        if raw.startswith("Watsonx Error"):
            logger.warning("Watsonx error: %s", raw)
            return None

        return _parse_ai_response(raw)

    except Exception as exc:
        logger.warning("Watsonx call failed: %s", exc)
        return None


def _build_prompt(profile: dict[str, Any]) -> str:
    subjects    = ", ".join(profile.get("subjects", []))       or "Not specified"
    work_type   = ", ".join(profile.get("work_type", []))      or "Not specified"
    activities  = ", ".join(profile.get("activities", []))     or "Not specified"
    career      = profile.get("career_goal", "Not specified")
    coding      = profile.get("enjoys_programming", "Not specified")
    work_env    = profile.get("work_env", "Not specified")
    priority    = profile.get("priority", "Not specified")
    math        = profile.get("math_comfort", "Not specified")

    available   = "\n".join(f"- {b}" for b in BRANCH_NAMES)

    return f"""AVAILABLE_BRANCHES:
{available}

STUDENT PROFILE:
- Favourite Subjects: {subjects}
- Preferred Work Type: {work_type}
- Enjoyed Activities: {activities}
- Career Goal: {career}
- Enjoys Programming: {coding}
- Preferred Work Environment: {work_env}
- What Matters Most: {priority}
- Mathematics Comfort: {math}

Analyse the profile and return the JSON recommendation as instructed."""


def _parse_ai_response(raw: str) -> dict[str, Any] | None:
    """Extract and validate the JSON block from the AI response."""
    # Try to find a JSON object in the response
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logger.warning("No JSON found in AI response.")
        return None

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s", e)
        return None

    # Validate required keys
    if "primary" not in data or "alternatives" not in data:
        logger.warning("AI response missing required keys.")
        return None

    # Ensure branch names are valid
    primary_branch = data["primary"].get("branch", "")
    if primary_branch not in BRANCH_CATALOGUE:
        # Try case-insensitive match
        for name in BRANCH_CATALOGUE:
            if name.lower() == primary_branch.lower():
                data["primary"]["branch"] = name
                break
        else:
            logger.warning("Unknown primary branch '%s' from AI.", primary_branch)
            return None

    return data


# ---------------------------------------------------------------------------
# Fallback deterministic engine
# ---------------------------------------------------------------------------

# Keyword-to-branch weight mapping
_KEYWORD_WEIGHTS: dict[str, dict[str, float]] = {
    kw: {branch: 1.0
         for branch, meta in BRANCH_CATALOGUE.items()
         if kw.lower() in [k.lower() for k in meta["keywords"]]}
    for kw in set(
        kw
        for meta in BRANCH_CATALOGUE.values()
        for kw in meta["keywords"]
    )
}


def _fallback_recommend(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic keyword-scoring fallback when AI is unavailable.
    Scores each branch by counting matching keywords from the profile.
    """
    # Collect all profile text tokens
    tokens: list[str] = []
    tokens += [s.lower() for s in profile.get("subjects", [])]
    tokens += [w.lower() for w in profile.get("work_type", [])]
    tokens += [a.lower() for a in profile.get("activities", [])]
    tokens += profile.get("career_goal", "").lower().split()
    tokens += [profile.get("priority", "").lower()]
    tokens += [profile.get("work_env", "").lower()]

    # Score branches
    scores: dict[str, float] = {b: 0.0 for b in BRANCH_NAMES}
    for branch, meta in BRANCH_CATALOGUE.items():
        for kw in meta["keywords"]:
            for token in tokens:
                if kw in token or token in kw:
                    scores[branch] += 1.0

    # Math comfort bonus
    math = profile.get("math_comfort", "").lower()
    if math in ("excellent", "good"):
        for branch, meta in BRANCH_CATALOGUE.items():
            scores[branch] += meta["math_req"] * 0.5

    # Programming bonus
    prog = profile.get("enjoys_programming", "").lower()
    if "yes" in prog:
        for b in ["Computer Engineering", "Information Technology",
                  "Cyber Security", "Artificial Intelligence & Data Science"]:
            scores[b] += 3.0
    elif "no" in prog:
        for b in ["Mechanical Engineering", "Civil Engineering",
                  "Electrical Engineering", "Chemical Engineering"]:
            scores[b] += 2.0

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top    = ranked[0]
    alts   = ranked[1:4]

    def _score_to_pct(raw: float, max_raw: float) -> int:
        if max_raw == 0:
            return 72
        pct = 55 + int((raw / max_raw) * 40)
        return min(pct, 97)

    max_score = top[1] if top[1] > 0 else 1

    primary_branch = top[0]
    primary_meta   = BRANCH_CATALOGUE[primary_branch]

    bullets = _generate_bullets(primary_branch, profile)

    return {
        "primary": {
            "branch":  primary_branch,
            "score":   _score_to_pct(top[1], max_score),
            "bullets": bullets,
        },
        "alternatives": [
            {
                "branch": b,
                "score":  _score_to_pct(s, max_score),
                "reason": _alt_reason(b, profile),
            }
            for b, s in alts
        ],
        "summary": _generate_summary(primary_branch, profile),
    }


def _generate_bullets(branch: str, profile: dict[str, Any]) -> list[str]:
    """Generate 5 contextual reason bullets for the primary branch."""
    meta    = BRANCH_CATALOGUE[branch]
    bullets = []

    prog = profile.get("enjoys_programming", "").lower()
    if "yes" in prog or "little" in prog:
        bullets.append(f"You enjoy programming — {branch} is one of the most coding-intensive fields.")

    math = profile.get("math_comfort", "").lower()
    if math in ("excellent", "good") and meta["math_req"] >= 4:
        bullets.append(f"Your strong mathematics skills align perfectly with {branch}'s curriculum.")

    activities = [a.lower() for a in profile.get("activities", [])]
    for act in activities:
        for kw in meta["keywords"][:4]:
            if kw.lower() in act:
                bullets.append(f"Your interest in {act} maps directly to {branch} skill areas.")
                break
        if len(bullets) >= 3:
            break

    career = profile.get("career_goal", "")
    if career:
        bullets.append(f"Your career goal '{career}' has strong pathways through {branch}.")

    if len(bullets) < 5:
        env = profile.get("work_env", "")
        bullets.append(
            f"The {env or 'flexible'} work environment you prefer suits {branch} graduates well."
        )

    priority = profile.get("priority", "").lower()
    if "salary" in priority or "high salary" in priority:
        bullets.append(f"{branch} offers competitive salaries with a demand score of {meta['salary']}/5.")
    elif "research" in priority:
        bullets.append(f"{branch} provides excellent higher studies and research opportunities.")

    return bullets[:5] if len(bullets) >= 5 else (bullets + [
        f"{branch} has a placement score of {meta['placement']}/5 with top MNC recruiters.",
        f"The future demand for {branch} graduates is rated {meta['future_demand']}/5.",
    ])[:5]


def _alt_reason(branch: str, profile: dict[str, Any]) -> str:
    meta   = BRANCH_CATALOGUE[branch]
    career = profile.get("career_goal", "your goals")
    return (
        f"{branch} aligns with your interest profile and offers "
        f"a placement score of {meta['placement']}/5, supporting {career}."
    )


def _generate_summary(branch: str, profile: dict[str, Any]) -> str:
    career = profile.get("career_goal", "your chosen career")
    math   = profile.get("math_comfort", "")
    prog   = profile.get("enjoys_programming", "")
    meta   = BRANCH_CATALOGUE[branch]

    return (
        f"Based on your interests, strengths, and career goal of '{career}', "
        f"{branch} is your strongest match with excellent future demand. "
        f"Your {math.lower() or 'mathematical'} aptitude and "
        f"{'coding enthusiasm' if 'yes' in prog.lower() else 'practical skill set'} "
        f"position you well for this field. "
        f"Top recruiters actively hire {branch} graduates, and the salary potential "
        f"is rated {meta['salary']}/5 — making this a solid long-term investment."
    )


# ---------------------------------------------------------------------------
# Enrichment — attach static catalogue metadata to AI/fallback result
# ---------------------------------------------------------------------------

def _enrich(data: dict[str, Any]) -> dict[str, Any]:
    """
    Attach career_path, skills, roadmap, recruiters, and difficulty metrics
    from the BRANCH_CATALOGUE to the AI-generated result.
    """
    primary_name = data["primary"]["branch"]
    primary_meta = BRANCH_CATALOGUE.get(primary_name, {})

    data["primary"].update({
        "icon":          primary_meta.get("icon", "bi-mortarboard"),
        "color":         primary_meta.get("color", "icon-indigo"),
        "career_path":   primary_meta.get("career_path", []),
        "skills":        primary_meta.get("skills", {}),
        "roadmap":       primary_meta.get("roadmap", {}),
        "recruiters":    primary_meta.get("recruiters", []),
        "difficulty":    primary_meta.get("difficulty", 3),
        "salary":        primary_meta.get("salary", 3),
        "placement":     primary_meta.get("placement", 3),
        "higher_studies":primary_meta.get("higher_studies", 3),
        "coding_req":    primary_meta.get("coding_req", 3),
        "math_req":      primary_meta.get("math_req", 3),
        "future_demand": primary_meta.get("future_demand", 3),
    })

    enriched_alts = []
    for alt in data.get("alternatives", [])[:3]:
        alt_meta = BRANCH_CATALOGUE.get(alt.get("branch", ""), {})
        enriched_alts.append({
            **alt,
            "icon":       alt_meta.get("icon", "bi-mortarboard"),
            "color":      alt_meta.get("color", "icon-indigo"),
            "salary":     alt_meta.get("salary", 3),
            "placement":  alt_meta.get("placement", 3),
            "future_demand": alt_meta.get("future_demand", 3),
        })
    data["alternatives"] = enriched_alts

    return data
