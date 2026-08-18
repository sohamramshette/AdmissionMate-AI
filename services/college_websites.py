"""
services/college_websites.py
=============================
Official College Website Directory & AI Resolver for Maharashtra Engineering Colleges.
Provides verified official URLs for popular colleges across Maharashtra (Pune, Mumbai, Nagpur,
Nashik, Aurangabad, Sangli, Kolhapur, Amravati, etc.) and dynamic domain resolution.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

# ---------------------------------------------------------------------------
# Verified Directory of Popular Maharashtra Engineering College Official Websites
# ---------------------------------------------------------------------------

POPULAR_COLLEGE_WEBSITES: dict[str, dict[str, str]] = {
    # ── Pune Region ────────────────────────────────────────────────────────
    "coep": {
        "name": "COEP Technological University, Pune",
        "url": "https://www.coeptech.ac.in",
        "domain": "coeptech.ac.in",
        "portal": "https://www.coeptech.ac.in/admissions/"
    },
    "pict": {
        "name": "Pune Institute of Computer Technology (PICT)",
        "url": "https://pict.edu",
        "domain": "pict.edu",
        "portal": "https://pict.edu/admissions/"
    },
    "vit pune": {
        "name": "Vishwakarma Institute of Technology (VIT), Pune",
        "url": "https://www.vit.edu",
        "domain": "vit.edu",
        "portal": "https://www.vit.edu/index.php/admissions"
    },
    "viit": {
        "name": "Vishwakarma Institute of Information Technology (VIIT), Pune",
        "url": "https://www.viit.ac.in",
        "domain": "viit.ac.in",
        "portal": "https://www.viit.ac.in"
    },
    "pccoe": {
        "name": "Pimpri Chinchwad College of Engineering (PCCOE), Pune",
        "url": "https://www.pccoepune.com",
        "domain": "pccoepune.com",
        "portal": "https://www.pccoepune.com/admissions.php"
    },
    "pccoer": {
        "name": "PCCOE & Research (PCCOER), Ravet",
        "url": "https://pccoer.com",
        "domain": "pccoer.com",
        "portal": "https://pccoer.com"
    },
    "cummins": {
        "name": "MKSSS Cummins College of Engineering for Women, Pune",
        "url": "https://www.cumminscollege.org",
        "domain": "cumminscollege.org",
        "portal": "https://www.cumminscollege.org/admission/"
    },
    "mit": {
        "name": "MIT World Peace University (MIT-WPU / MIT Pune)",
        "url": "https://mitwpu.edu.in",
        "domain": "mitwpu.edu.in",
        "portal": "https://mitwpu.edu.in/admissions"
    },
    "mitaoe": {
        "name": "MIT Academy of Engineering (MIT AOE), Alandi Pune",
        "url": "https://mitaoe.ac.in",
        "domain": "mitaoe.ac.in",
        "portal": "https://mitaoe.ac.in/admission.php"
    },
    "aissms": {
        "name": "AISSMS College of Engineering, Pune",
        "url": "https://aissmscoe.com",
        "domain": "aissmscoe.com",
        "portal": "https://aissmscoe.com/admission/"
    },
    "aissms ioit": {
        "name": "AISSMS Institute of Information Technology, Pune",
        "url": "https://aissmsioit.org",
        "domain": "aissmsioit.org",
        "portal": "https://aissmsioit.org"
    },
    "sinhgad": {
        "name": "Sinhgad College of Engineering (SCOE), Vadgaon Pune",
        "url": "http://cms.sinhgad.edu/sinhgad_engineering_institutes/scoe_vadgaon/about.aspx",
        "domain": "sinhgad.edu",
        "portal": "http://www.sinhgad.edu"
    },
    "skncoe": {
        "name": "Smt. Kashibai Navale College of Engineering, Pune",
        "url": "http://cms.sinhgad.edu/sinhgad_engineering_institutes/skncoe_vadgaon/about.aspx",
        "domain": "sinhgad.edu",
        "portal": "http://www.sinhgad.edu"
    },
    "dy patil akurdi": {
        "name": "D.Y. Patil College of Engineering (DYPCOE), Akurdi Pune",
        "url": "https://www.dypcoeakurdi.ac.in",
        "domain": "dypcoeakurdi.ac.in",
        "portal": "https://www.dypcoeakurdi.ac.in/admissions"
    },
    "dypiemr": {
        "name": "Dr. D.Y. Patil Institute of Engineering (DYPIEMR), Akurdi",
        "url": "https://www.dypiemr.ac.in",
        "domain": "dypiemr.ac.in",
        "portal": "https://www.dypiemr.ac.in"
    },
    "dy patil pimpri": {
        "name": "Dr. D.Y. Patil Institute of Technology, Pimpri Pune",
        "url": "https://engg.dypvp.edu.in",
        "domain": "engg.dypvp.edu.in",
        "portal": "https://engg.dypvp.edu.in"
    },
    "jspm": {
        "name": "JSPM's Rajarshi Shahu College of Engineering (RSCOE), Pune",
        "url": "https://jspmrscoe.edu.in",
        "domain": "jspmrscoe.edu.in",
        "portal": "https://jspmrscoe.edu.in"
    },
    "mescoe": {
        "name": "Modern Education Society's College of Engineering (MESCOE), Pune",
        "url": "https://mescoepune.org",
        "domain": "mescoepune.org",
        "portal": "https://mescoepune.org"
    },
    "pvg": {
        "name": "PVG's COET & GKPIOM, Pune",
        "url": "https://www.pvgcoet.ac.in",
        "domain": "pvgcoet.ac.in",
        "portal": "https://www.pvgcoet.ac.in"
    },
    "army institute": {
        "name": "Army Institute of Technology (AIT), Pune",
        "url": "https://www.aitpune.com",
        "domain": "aitpune.com",
        "portal": "https://www.aitpune.com/admissions.aspx"
    },

    # ── Mumbai & Navi Mumbai Region ────────────────────────────────────────
    "vjti": {
        "name": "Veermata Jijabai Technological Institute (VJTI), Mumbai",
        "url": "https://vjti.ac.in",
        "domain": "vjti.ac.in",
        "portal": "https://vjti.ac.in/admissions/"
    },
    "spit": {
        "name": "Sardar Patel Institute of Technology (SPIT), Mumbai",
        "url": "https://www.spit.ac.in",
        "domain": "spit.ac.in",
        "portal": "https://www.spit.ac.in/admissions/"
    },
    "spce": {
        "name": "Sardar Patel College of Engineering (SPCE), Mumbai",
        "url": "https://www.spce.ac.in",
        "domain": "spce.ac.in",
        "portal": "https://www.spce.ac.in"
    },
    "ict mumbai": {
        "name": "Institute of Chemical Technology (ICT), Mumbai",
        "url": "https://www.ictmumbai.edu.in",
        "domain": "ictmumbai.edu.in",
        "portal": "https://www.ictmumbai.edu.in/admission"
    },
    "dj sanghvi": {
        "name": "Dwarkadas J. Sanghvi College of Engineering (DJSCE), Mumbai",
        "url": "https://www.djsce.ac.in",
        "domain": "djsce.ac.in",
        "portal": "https://www.djsce.ac.in/admissions.php"
    },
    "somaiya": {
        "name": "K.J. Somaiya College of Engineering (KJSCE), Mumbai",
        "url": "https://kjsce.somaiya.edu",
        "domain": "kjsce.somaiya.edu",
        "portal": "https://kjsce.somaiya.edu/en/admission"
    },
    "thadomal": {
        "name": "Thadomal Shahani Engineering College (TSEC), Mumbai",
        "url": "https://tsec.edu",
        "domain": "tsec.edu",
        "portal": "https://tsec.edu/admissions/"
    },
    "fr conceicao": {
        "name": "Fr. Conceicao Rodrigues College of Engineering (CRCE), Bandra Mumbai",
        "url": "https://www.frcrce.ac.in",
        "domain": "frcrce.ac.in",
        "portal": "https://www.frcrce.ac.in"
    },
    "fcrit": {
        "name": "Fr. C. Rodrigues Institute of Technology (FCRIT), Vashi Navi Mumbai",
        "url": "https://www.fcrit.ac.in",
        "domain": "fcrit.ac.in",
        "portal": "https://www.fcrit.ac.in"
    },
    "vidyalankar": {
        "name": "Vidyalankar Institute of Technology (VIT), Wadala Mumbai",
        "url": "https://vit.edu.in",
        "domain": "vit.edu.in",
        "portal": "https://vit.edu.in/admissions/"
    },
    "rait": {
        "name": "Ramrao Adik Institute of Technology (RAIT), Navi Mumbai",
        "url": "https://dypatil.edu/schools/engineering",
        "domain": "dypatil.edu",
        "portal": "https://dypatil.edu/admission"
    },
    "sakec": {
        "name": "Shah & Anchor Kutchhi Engineering College (SAKEC), Chembur Mumbai",
        "url": "https://www.shahandanchor.com",
        "domain": "shahandanchor.com",
        "portal": "https://www.shahandanchor.com/home/"
    },
    "pillai": {
        "name": "Pillai College of Engineering (PCE), New Panvel",
        "url": "https://www.pce.ac.in",
        "domain": "pce.ac.in",
        "portal": "https://www.pce.ac.in/admissions/"
    },
    "don bosco": {
        "name": "Don Bosco Institute of Technology (DBIT), Kurla Mumbai",
        "url": "https://www.dbit.in",
        "domain": "dbit.in",
        "portal": "https://www.dbit.in"
    },
    "rajiv gandhi": {
        "name": "Rajiv Gandhi Institute of Technology (RGIT), Andheri Mumbai",
        "url": "https://www.mctrgit.ac.in",
        "domain": "mctrgit.ac.in",
        "portal": "https://www.mctrgit.ac.in"
    },
    "atharva": {
        "name": "Atharva College of Engineering, Malad Mumbai",
        "url": "https://www.atharvacoe.ac.in",
        "domain": "atharvacoe.ac.in",
        "portal": "https://www.atharvacoe.ac.in"
    },
    "vesit": {
        "name": "Vivekanand Education Society's Institute of Technology (VESIT), Chembur",
        "url": "https://vesit.ves.ac.in",
        "domain": "vesit.ves.ac.in",
        "portal": "https://vesit.ves.ac.in/admission"
    },

    # ── Nagpur & Vidarbha Region ──────────────────────────────────────────
    "vnit": {
        "name": "Visvesvaraya National Institute of Technology (VNIT), Nagpur",
        "url": "https://vnit.ac.in",
        "domain": "vnit.ac.in",
        "portal": "https://vnit.ac.in/admission/"
    },
    "ramdeobaba": {
        "name": "Shri Ramdeobaba College of Engineering (RCOEM / RBU), Nagpur",
        "url": "https://www.rknec.edu",
        "domain": "rknec.edu",
        "portal": "https://www.rknec.edu/Admission/"
    },
    "ycce": {
        "name": "Yeshwantrao Chavan College of Engineering (YCCE), Nagpur",
        "url": "https://www.ycce.edu",
        "domain": "ycce.edu",
        "portal": "https://www.ycce.edu"
    },
    "gcoen": {
        "name": "Government College of Engineering, Nagpur",
        "url": "https://www.gcoen.ac.in",
        "domain": "gcoen.ac.in",
        "portal": "https://www.gcoen.ac.in"
    },
    "gcoea": {
        "name": "Government College of Engineering, Amravati",
        "url": "https://www.gcoea.ac.in",
        "domain": "gcoea.ac.in",
        "portal": "https://www.gcoea.ac.in"
    },
    "gcoec": {
        "name": "Government College of Engineering, Chandrapur",
        "url": "http://www.gcoec.ac.in",
        "domain": "gcoec.ac.in",
        "portal": "http://www.gcoec.ac.in"
    },

    # ── Nashik & North Maharashtra Region ─────────────────────────────────
    "kk wagh": {
        "name": "K.K. Wagh Institute of Engineering Education & Research, Nashik",
        "url": "https://engg.kkwagh.edu.in",
        "domain": "engg.kkwagh.edu.in",
        "portal": "https://engg.kkwagh.edu.in/admissions"
    },
    "geca": {
        "name": "Government College of Engineering, Chhatrapati Sambhajinagar (Aurangabad)",
        "url": "https://geca.ac.in",
        "domain": "geca.ac.in",
        "portal": "https://geca.ac.in"
    },
    "gcoej": {
        "name": "Government College of Engineering, Jalgaon",
        "url": "https://www.gcoej.ac.in",
        "domain": "gcoej.ac.in",
        "portal": "https://www.gcoej.ac.in"
    },

    # ── Western Maharashtra & Sangli / Kolhapur ───────────────────────────
    "walchand": {
        "name": "Walchand College of Engineering (WCE), Sangli",
        "url": "http://www.walchandsangli.ac.in",
        "domain": "walchandsangli.ac.in",
        "portal": "http://www.walchandsangli.ac.in/admission.aspx"
    },
    "gcek": {
        "name": "Government College of Engineering, Karad",
        "url": "https://gcek.ac.in",
        "domain": "gcek.ac.in",
        "portal": "https://gcek.ac.in"
    },
    "rit": {
        "name": "Rajarambapu Institute of Technology (RIT), Islampur / Sakharale",
        "url": "https://www.ritindia.edu",
        "domain": "ritindia.edu",
        "portal": "https://www.ritindia.edu"
    },
    "dkte": {
        "name": "DKTE Society's Textile and Engineering Institute, Ichalkaranji",
        "url": "https://www.dktes.com",
        "domain": "dktes.com",
        "portal": "https://www.dktes.com"
    },
    "kit kolhapur": {
        "name": "KIT's College of Engineering (Autonomous), Kolhapur",
        "url": "https://www.kitcoek.in",
        "domain": "kitcoek.in",
        "portal": "https://www.kitcoek.in"
    }
}


# ---------------------------------------------------------------------------
# Smart Lookup Function
# ---------------------------------------------------------------------------

def get_college_website(college_name: str, college_id: str | None = None) -> dict[str, Any]:
    """
    Resolve the official website for a given college name or identifier.

    Returns a dict:
        url            : Verified official URL or search portal URL
        domain         : Clean display domain (e.g. 'coeptech.ac.in')
        portal         : Admissions portal direct URL (if available)
        is_verified    : True if verified in official registry, False if fallback
    """
    if not college_name:
        return {
            "url": "https://cetcell.mahacet.org",
            "domain": "cetcell.mahacet.org",
            "portal": "https://cetcell.mahacet.org",
            "is_verified": False,
        }

    c_norm = college_name.lower().strip()
    id_norm = (college_id or "").lower().strip()

    # 1. Exact or keyword match from directory
    for key, data in POPULAR_COLLEGE_WEBSITES.items():
        if key in c_norm or (id_norm and key in id_norm):
            return {
                "url": data["url"],
                "domain": data["domain"],
                "portal": data.get("portal", data["url"]),
                "is_verified": True,
            }

    # 2. Specific keyword heuristics
    if "coep" in c_norm:
        return {"url": "https://www.coeptech.ac.in", "domain": "coeptech.ac.in", "portal": "https://www.coeptech.ac.in", "is_verified": True}
    if "vjti" in c_norm:
        return {"url": "https://vjti.ac.in", "domain": "vjti.ac.in", "portal": "https://vjti.ac.in", "is_verified": True}
    if "pict" in c_norm:
        return {"url": "https://pict.edu", "domain": "pict.edu", "portal": "https://pict.edu", "is_verified": True}
    if "spit" in c_norm or "sardar patel institute" in c_norm:
        return {"url": "https://www.spit.ac.in", "domain": "spit.ac.in", "portal": "https://www.spit.ac.in", "is_verified": True}
    if "spce" in c_norm or "sardar patel college" in c_norm:
        return {"url": "https://www.spce.ac.in", "domain": "spce.ac.in", "portal": "https://www.spce.ac.in", "is_verified": True}
    if "vishwakarma institute of information" in c_norm or "viit" in c_norm:
        return {"url": "https://www.viit.ac.in", "domain": "viit.ac.in", "portal": "https://www.viit.ac.in", "is_verified": True}
    if "vishwakarma" in c_norm or ("vit" in c_norm and "pune" in c_norm):
        return {"url": "https://www.vit.edu", "domain": "vit.edu", "portal": "https://www.vit.edu", "is_verified": True}
    if "walchand" in c_norm:
        return {"url": "http://www.walchandsangli.ac.in", "domain": "walchandsangli.ac.in", "portal": "http://www.walchandsangli.ac.in", "is_verified": True}
    if "cummins" in c_norm:
        return {"url": "https://www.cumminscollege.org", "domain": "cumminscollege.org", "portal": "https://www.cumminscollege.org", "is_verified": True}
    if "somaiya" in c_norm:
        return {"url": "https://kjsce.somaiya.edu", "domain": "kjsce.somaiya.edu", "portal": "https://kjsce.somaiya.edu", "is_verified": True}
    if "sanghvi" in c_norm or "djsce" in c_norm:
        return {"url": "https://www.djsce.ac.in", "domain": "djsce.ac.in", "portal": "https://www.djsce.ac.in", "is_verified": True}
    if "pccoer" in c_norm:
        return {"url": "https://pccoer.com", "domain": "pccoer.com", "portal": "https://pccoer.com", "is_verified": True}
    if "pccoe" in c_norm or "pimpri chinchwad" in c_norm:
        return {"url": "https://www.pccoepune.com", "domain": "pccoepune.com", "portal": "https://www.pccoepune.com", "is_verified": True}
    if "vnit" in c_norm:
        return {"url": "https://vnit.ac.in", "domain": "vnit.ac.in", "portal": "https://vnit.ac.in", "is_verified": True}
    if "ict" in c_norm and "mumbai" in c_norm:
        return {"url": "https://www.ictmumbai.edu.in", "domain": "ictmumbai.edu.in", "portal": "https://www.ictmumbai.edu.in", "is_verified": True}
    if "thadomal" in c_norm or "tsec" in c_norm:
        return {"url": "https://tsec.edu", "domain": "tsec.edu", "portal": "https://tsec.edu", "is_verified": True}
    if "fr. conceicao" in c_norm or "conceicao" in c_norm or "crce" in c_norm:
        return {"url": "https://www.frcrce.ac.in", "domain": "frcrce.ac.in", "portal": "https://www.frcrce.ac.in", "is_verified": True}
    if "vidyalankar" in c_norm:
        return {"url": "https://vit.edu.in", "domain": "vit.edu.in", "portal": "https://vit.edu.in", "is_verified": True}
    if "ramrao adik" in c_norm or "rait" in c_norm:
        return {"url": "https://dypatil.edu/schools/engineering", "domain": "dypatil.edu", "portal": "https://dypatil.edu", "is_verified": True}
    if "sinhgad" in c_norm:
        return {"url": "https://www.sinhgad.edu", "domain": "sinhgad.edu", "portal": "https://www.sinhgad.edu", "is_verified": True}
    if "patil" in c_norm:
        return {"url": "https://www.dypcoeakurdi.ac.in", "domain": "dypcoeakurdi.ac.in", "portal": "https://www.dypcoeakurdi.ac.in", "is_verified": True}
    if "mit" in c_norm and "aoe" in c_norm:
        return {"url": "https://mitaoe.ac.in", "domain": "mitaoe.ac.in", "portal": "https://mitaoe.ac.in", "is_verified": True}
    if "mit" in c_norm:
        return {"url": "https://mitwpu.edu.in", "domain": "mitwpu.edu.in", "portal": "https://mitwpu.edu.in", "is_verified": True}
    if "aissms" in c_norm:
        return {"url": "https://aissmscoe.com", "domain": "aissmscoe.com", "portal": "https://aissmscoe.com", "is_verified": True}
    if "ramdeobaba" in c_norm or "rcoem" in c_norm:
        return {"url": "https://www.rknec.edu", "domain": "rknec.edu", "portal": "https://www.rknec.edu", "is_verified": True}
    if "wagh" in c_norm:
        return {"url": "https://engg.kkwagh.edu.in", "domain": "engg.kkwagh.edu.in", "portal": "https://engg.kkwagh.edu.in", "is_verified": True}
    if "karad" in c_norm:
        return {"url": "https://gcek.ac.in", "domain": "gcek.ac.in", "portal": "https://gcek.ac.in", "is_verified": True}
    if "aurangabad" in c_norm or "geca" in c_norm:
        return {"url": "https://geca.ac.in", "domain": "geca.ac.in", "portal": "https://geca.ac.in", "is_verified": True}
    if "amravati" in c_norm:
        return {"url": "https://www.gcoea.ac.in", "domain": "gcoea.ac.in", "portal": "https://www.gcoea.ac.in", "is_verified": True}
    if "nagpur" in c_norm and "government" in c_norm:
        return {"url": "https://www.gcoen.ac.in", "domain": "gcoen.ac.in", "portal": "https://www.gcoen.ac.in", "is_verified": True}
    if "shah" in c_norm and "anchor" in c_norm:
        return {"url": "https://www.shahandanchor.com", "domain": "shahandanchor.com", "portal": "https://www.shahandanchor.com", "is_verified": True}
    if "pillai" in c_norm:
        return {"url": "https://www.pce.ac.in", "domain": "pce.ac.in", "portal": "https://www.pce.ac.in", "is_verified": True}
    if "jspm" in c_norm or "rajarshi shahu" in c_norm:
        return {"url": "https://jspmrscoe.edu.in", "domain": "jspmrscoe.edu.in", "portal": "https://jspmrscoe.edu.in", "is_verified": True}

    # 3. Safe fallback with Google Search query for the official portal
    clean_query = re.sub(r"[^\w\s]", " ", college_name).strip()
    encoded = urllib.parse.quote_plus(f"{clean_query} official website engineering")
    return {
        "url": f"https://www.google.com/search?q={encoded}",
        "domain": "Search Official Site",
        "portal": f"https://www.google.com/search?q={encoded}",
        "is_verified": False,
    }
