"""
services/document_ai.py
========================
Dedicated AI Document & Verification Assistant for Maharashtra CET Admissions.
Covers:
- Category-wise document requirements (OPEN, OBC, SC, ST, EWS, TFWS, SEBC, VJ/NT, SBC, PWD, Defence, Minority, Orphan, OMS).
- Document formats, issuing authorities, and validity deadlines (NCL valid till 31st March, CVC rules).
- Candidature Domicile Types (Type A, B, C, D, E, OMS, J&K).
- Proforma formats (Proforma A through Z, Gap Certificate affidavit).
- Physical Scrutiny vs E-Scrutiny guidelines at Facilitation Centers (FC / ARC).
- Troubleshooting common verification issues (Receipt vs Validity, Spelling mismatch, Name change affidavit).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.watsonx import chat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comprehensive Maharashtra CET Document Knowledge Base
# ---------------------------------------------------------------------------

DOCUMENT_KNOWLEDGE_BASE = {
    "mandatory_all": {
        "title": "Mandatory Documents for ALL Candidates (General / OPEN / Reserved)",
        "documents": [
            {
                "name": "MHT-CET Scorecard 2026",
                "format": "Printed copy of the official scorecard downloaded from cetcell.mahacet.org",
                "authority": "State Common Entrance Test Cell, Maharashtra",
                "notes": "Must clearly show PCM / PCB percentile and registration details."
            },
            {
                "name": "MHT-CET / CAP Online Application Form & Receipt",
                "format": "Printout of the confirmed online registration form with FC acknowledgement stamp",
                "authority": "MHT-CET Portal",
                "notes": "Carry 2 self-attested copies."
            },
            {
                "name": "HSC / 12th Standard Marksheet",
                "format": "Original marksheet + 3 photocopies",
                "authority": "Maharashtra State Board or equivalent (CBSE / ICSE)",
                "notes": "Must meet minimum eligibility (45% for OPEN, 40% for Reserved categories in PCM/PMB)."
            },
            {
                "name": "SSC / 10th Standard Marksheet & Passing Certificate",
                "format": "Original certificate + 3 photocopies",
                "authority": "Divisional Secondary & Higher Secondary Board",
                "notes": "Used as official proof of Date of Birth and Full Name spelling."
            },
            {
                "name": "Indian Nationality Certificate",
                "format": "Any one of: Valid Indian Passport, School/College Leaving Certificate mentioning nationality as 'Indian', or Nationality Certificate issued by Taluka Executive Magistrate / Tehsildar",
                "authority": "Tehsildar / Competent Executive Magistrate",
                "notes": "Aadhaar card alone is NOT accepted as conclusive nationality proof during physical verification."
            },
            {
                "name": "Maharashtra Domicile Certificate / Birth Certificate / TC",
                "format": "Domicile Certificate or Birth Certificate showing birth in Maharashtra or School Leaving Certificate stating place of birth in Maharashtra",
                "authority": "Sub-Divisional Officer (SDO) / Tehsildar",
                "notes": "Required to claim Maharashtra State (MH) Candidature seats."
            }
        ]
    },

    "categories": {
        "OBC": {
            "title": "OBC (Other Backward Class) Category Requirements",
            "docs": [
                "1. **Caste Certificate**: Issued by Sub-Divisional Magistrate / Competent Authority in Maharashtra stating the specific caste/sub-caste.",
                "2. **Caste Validity Certificate (CVC)**: Issued by Divisional Caste Scrutiny Committee. Mandatory for seat confirmation under category.",
                "3. **Non-Creamy Layer Certificate (NCL)**: Issued by Tehsildar / SDO, valid up to **31st March of current financial/academic year**. (Mandatory for OBC to claim reservation and 50% tuition fee concession under MahaDBT)."
            ],
            "fee_benefit": "50% Tuition Fee & Exam Fee concession under Government EBC/Post-Matric Scholarship scheme."
        },
        "SC": {
            "title": "SC (Scheduled Caste) Category Requirements",
            "docs": [
                "1. **Caste Certificate**: Issued by Competent Authority in Maharashtra State.",
                "2. **Caste Validity Certificate (CVC)**: Issued by Social Welfare Scrutiny Committee.",
                "3. **Income Certificate**: (For claiming 100% tuition & development fee scholarship under Social Justice Dept)."
            ],
            "fee_benefit": "100% Tuition Fee & 100% Development Fee waived under Government Scholarship."
        },
        "ST": {
            "title": "ST (Scheduled Tribe) Category Requirements",
            "docs": [
                "1. **Tribe Certificate**: Issued by Competent Authority in Maharashtra State.",
                "2. **Tribe Validity Certificate (TVC)**: Issued by Scheduled Tribe Certificate Scrutiny Committee (Nashik/Pune/Nagpur/Amravati/Gadchiroli).",
                "3. **Income Certificate**: (For claiming 100% fee scholarship under Tribal Development Dept)."
            ],
            "fee_benefit": "100% Tuition Fee & Development Fee waived."
        },
        "EWS": {
            "title": "EWS (Economically Weaker Section) Category Requirements",
            "docs": [
                "1. **EWS Eligibility Certificate (Proforma-V)**: Issued by Competent Authority (Tehsildar / Sub-Divisional Officer).",
                "2. **Annual Family Income**: Gross annual income must be **below ₹8,00,000 (8 Lakhs)** from all sources for the previous financial year.",
                "3. **State Domicile**: Candidate must belong to Maharashtra state (Not eligible for Caste Certificate holders who already have OBC/SC/ST reservation)."
            ],
            "fee_benefit": "10% Supernumerary quota seats in all engineering colleges + 50% Tuition fee concession under MahaDBT."
        },
        "TFWS": {
            "title": "TFWS (Tuition Fee Waiver Scheme) Requirements",
            "docs": [
                "1. **Income Certificate**: Issued by Tehsildar / Sub-Divisional Officer showing annual family income from all sources is **strictly below ₹8,00,000 (8 Lakhs)**.",
                "2. **Maharashtra Domicile Certificate**: Only Maharashtra State Type A/B/C/D candidates are eligible.",
                "3. **Option Form Selection**: Must choose TFWS branch code (ending with 'T', e.g. 600624510T) in the CAP preference form."
            ],
            "fee_benefit": "100% Tuition Fee Waived for all 4 years across government and private unaided colleges (5% supernumerary seats)."
        },
        "VJ_NT": {
            "title": "VJ / DT / NT-1 / NT-2 / NT-3 Category Requirements",
            "docs": [
                "1. **Caste Certificate**: Stating VJ (DT-A) or NT (NT-B, NT-C, NT-D).",
                "2. **Caste Validity Certificate**: From Divisional Caste Scrutiny Committee.",
                "3. **Non-Creamy Layer (NCL) Certificate**: Valid up to **31st March of current academic year**."
            ],
            "fee_benefit": "100% Tuition Fee concession in Govt & Autonomous colleges; 100% Tuition fee in Private Unaided colleges under Freeship/Scholarship."
        },
        "SEBC": {
            "title": "SEBC (Socially and Educationally Backward Class) Requirements",
            "docs": [
                "1. **SEBC Caste Certificate**: Issued by Competent Authority in Maharashtra State.",
                "2. **SEBC Caste Validity Certificate**: Issued by Caste Scrutiny Committee.",
                "3. **Non-Creamy Layer (NCL) Certificate**: Valid up to **31st March of current academic year**."
            ],
            "fee_benefit": "10% reservation in admission + 50% tuition fee concession under MahaDBT."
        },
        "PWD": {
            "title": "PWD / Divyangjan (Person with Disability) Requirements",
            "docs": [
                "1. **Disability Certificate**: Minimum **40% permanent benchmark disability** certified by District Civil Surgeon / Medical Superintendent / Central UDID Card.",
                "2. **Proforma-F / F-1**: Certificate of disability from competent authority for MHT-CET.",
                "3. **Maharashtra Domicile**: Stating domicile in Maharashtra."
            ],
            "fee_benefit": "5% horizontal reservation in all engineering colleges + exam relaxation/scribe assistance."
        },
        "DEFENCE": {
            "title": "Defence Ward Quota (Def-1, Def-2, Def-3) Requirements",
            "docs": [
                "1. **Def-1**: Children of Ex-Service Defence personnel who are Domiciled in Maharashtra (Proforma-C issued by Zilla Sainik Welfare Officer).",
                "2. **Def-2**: Children of Active Defence Service personnel Domiciled in Maharashtra (Proforma-D issued by Commanding Officer).",
                "3. **Def-3**: Children of Active Defence Personnel transferred and posted in Maharashtra (Proforma-E issued by Commanding Officer)."
            ],
            "fee_benefit": "5% quota reservation seats in all government and aided institutes."
        },
        "MINORITY": {
            "title": "Religious / Linguistic Minority Quota Requirements",
            "docs": [
                "1. **Leaving Certificate**: Indicating candidate's Mother Tongue (e.g. Hindi, Gujarati, Sindhi) or Religion (e.g. Muslim, Christian, Jain, Sikh, Parsi).",
                "2. **Minority Affidavit (Proforma-O)**: Self-declaration on ₹100 stamp paper registered before an Executive Magistrate / Notary."
            ],
            "fee_benefit": "51% seats reserved in minority institutes (e.g. DJ Sanghvi, K.J. Somaiya, Rizvi, Vidyalankar)."
        }
    }
}

# ---------------------------------------------------------------------------
# Document Verification System Prompt for RAG / Watsonx
# ---------------------------------------------------------------------------

_DOC_SYSTEM_PROMPT = """
You are the Official MHT-CET Admission Document & Verification Expert for Maharashtra State CET Cell engineering/pharmacy admissions.

Knowledge & Rules:
1. Mandatory Docs for all: 10th & 12th Marksheet, CET Scorecard, Domicile/Birth certificate, Nationality proof.
2. OBC / VJ / NT / SEBC require: Caste Certificate + Caste Validity Certificate + Non-Creamy Layer (NCL valid till 31st March of current AY).
3. SC / ST require: Caste/Tribe Certificate + Caste/Tribe Validity. (NCL NOT needed).
4. EWS requires: Proforma-V Certificate from Tehsildar (Family income < Rs.8 Lakhs).
5. TFWS requires: Income Certificate from Tehsildar (< Rs.8 Lakhs) + Maharashtra Domicile.
6. Gap Certificate: Required if 1 or more academic years dropped after 12th (Rs.100 stamp paper affidavit).
7. If Caste Validity is not yet received, explain the Scrutiny receipt submission rule and the undertaking deadline given by CET Cell.
8. Format all answers with clear markdown headings, bullet points, checklists, and issuing authorities. Keep it exact, actionable, and encouraging for students.
""".strip()

# ---------------------------------------------------------------------------
# Rule-based Engine for Accurate Grounded Document Guidance
# ---------------------------------------------------------------------------

def _rule_based_document_advisor(query: str) -> str:
    """Generate high-precision structured document guidance based on CET Cell norms."""
    q = query.lower()

    # 1. OBC documents
    if "obc" in q:
        data = DOCUMENT_KNOWLEDGE_BASE["categories"]["OBC"]
        return f"""### 📑 **Documents Required for OBC Category (MHT-CET)**

To claim an **OBC category seat** and **50% tuition fee scholarship**, you must present:

| Document | Issuing Authority | Key Conditions |
| :--- | :--- | :--- |
| **1. Caste Certificate** | Sub-Divisional Magistrate (SDO) / Tehsildar | Must state recognized OBC caste in Maharashtra |
| **2. Caste Validity Certificate (CVC)** | Divisional Caste Scrutiny Committee | Mandatory for final seat confirmation |
| **3. Non-Creamy Layer (NCL)** | Tehsildar / Sub-Divisional Officer | Must be **valid up to 31st March 2026** |
| **4. MHT-CET Scorecard & App Form** | CET Cell | Printed with FC verification stamp |
| **5. 10th & 12th Marksheets** | State Board / CBSE / ICSE | Min 40% aggregate in PCM for OBC |
| **6. Domicile & Nationality Proof** | SDO / Tehsildar / Passport / LC | Proves Maharashtra state candidature |

> [!IMPORTANT]
> **Non-Creamy Layer (NCL)** is **mandatory for OBC**. Without a valid NCL certificate, your category will automatically be converted to **OPEN / General** in CAP round seat allocation.

💰 **Scholarship Benefit:** 50% Tuition Fee & 50% Exam Fee concession under Government EBC/Post-Matric Scholarship."""

    # 2. EWS documents
    if "ews" in q:
        return """### 📑 **Documents Required for EWS (Economically Weaker Section)**

Under the 10% EWS quota in Maharashtra MHT-CET engineering admissions:

1. **EWS Eligibility Certificate (Proforma-V)**:
   - Issued by **Tehsildar / Sub-Divisional Magistrate (SDO)**.
   - Must be issued for the **current financial year**.
2. **Income Criteria**:
   - Total gross annual family income from all sources must be **strictly below ₹8,00,000 (8 Lakhs)**.
3. **Maharashtra State Domicile**:
   - Must be a resident of Maharashtra (Type A/B/C/D).
4. **General Academic Documents**:
   - 10th Marksheet, 12th Marksheet (min 45% aggregate in PCM), MHT-CET Scorecard, and School Leaving Certificate.

> [!NOTE]
> EWS reservation is only for candidates who **do not** belong to SC, ST, or OBC categories. You receive **10% extra supernumerary seats** and **50% tuition fee reimbursement** under Rajarshi Shahu Maharaj EBC scheme."""

    # 3. TFWS documents & rules
    if "tfws" in q or "tuition fee waiver" in q:
        return """### ⚡ **TFWS (Tuition Fee Waiver Scheme) Document Requirements**

The TFWS scheme provides **100% Tuition Fee Waiver** across all government, aided, and private engineering colleges in Maharashtra (5% supernumerary seats per branch):

| Required Document | Authority | Specifications |
| :--- | :--- | :--- |
| **1. Income Certificate** | Tehsildar / SDO | Annual family income **< ₹8,00,000 (8 Lakhs)** for previous FY |
| **2. Maharashtra Domicile** | Tehsildar / Executive Magistrate | Proves Maharashtra State Candidature |
| **3. MHT-CET Scorecard** | CET Cell | Merit-based allotment on CET percentile |
| **4. 10th & 12th Marksheets** | Board | Original + photocopies |

💡 **How to Apply:**
- While filling out the CAP option preference form, select college choices with the **TFWS code (Choice code ending in 'T')**.
- You will only pay nominal examination/gymkhana fees (around ₹5,000 to ₹15,000/year instead of ₹1.5+ Lakhs)."""

    # 4. SC / ST Category
    if "sc" in q or "st " in q or "scheduled caste" in q or "scheduled tribe" in q:
        return """### 📑 **Documents Required for SC & ST Categories**

Candidates applying under SC / ST reservation in MHT-CET need:

1. **Caste / Tribe Certificate**: Issued by Competent Authority in Maharashtra State.
2. **Caste / Tribe Validity Certificate (CVC / TVC)**: Issued by Divisional Scrutiny Committee / Tribal Research Scrutiny Board.
3. **Income Certificate**: Issued by Tehsildar (required for 100% scholarship reimbursement from Social Justice/Tribal Development Dept).
4. **General Documents**: 10th Marksheet, 12th Marksheet (Min 40% aggregate in PCM), CET Scorecard, and Domicile/Birth Certificate.

> [!TIP]
> **Non-Creamy Layer (NCL) is NOT required** for SC and ST candidates."""

    # 5. Gap Certificate
    if "gap" in q or "drop" in q:
        return """### 📝 **Gap Certificate Format & Requirements (After 12th / Drop Year)**

If you took a 1-year or 2-year drop after passing your 12th Standard for CET preparation:

- **Format:** Affidavit on a **₹100 Non-Judicial Stamp Paper** registered before a Notary Public or Executive Magistrate.
- **Content Required:**
  1. Your Full Name, Father's Name, and Permanent Address.
  2. Year of passing 12th standard and Board Roll Number.
  3. Clear statement stating you were not admitted into any other degree/diploma college during the gap period.
  4. Reason for gap: *"Preparing for MHT-CET / JEE Competitive Entrance Examination"*.
  5. Confirmation of good moral character without any criminal/legal proceedings.

> [!NOTE]
> You only need **1 original notary affidavit + 2 photocopies** during physical document verification at the Scrutiny Center."""

    # 6. Caste Validity Pending / Receipt
    if "validity" in q or "receipt" in q:
        return """### ⏳ **What to Do If Your Caste Validity Certificate is Pending?**

If your Caste Validity Certificate is still in process at the Scrutiny Committee:

1. **At Online Registration & FC Verification:**
   - You can upload the **Official Caste Validity Application Receipt / Acknowledgement Slip (Chalan)**.
2. **CET Cell Undertaking (Proforma-H):**
   - You must submit an undertaking stating that you will produce the original Caste Validity Certificate before the deadline announced by CET Cell (usually before CAP Round 3 seat confirmation).
3. **Consequence of Non-Submission:**
   - If the original Validity is not produced before the cutoff date, your category seat will be converted to **OPEN category** for subsequent rounds."""

    # 7. Non-Creamy Layer (NCL)
    if "ncl" in q or "creamy" in q:
        return """### 🔍 **Non-Creamy Layer (NCL) Certificate Rules & Validity**

- **Who Needs NCL?**
  - Mandatory for: **OBC, VJ/DT-A, NT-B, NT-C, NT-D, SEBC, and SBC** categories.
  - **NOT needed** for: SC, ST, OPEN, EWS.
- **Validity Date Rule:**
  - The NCL certificate must explicitly state that it is **valid up to 31st March 2026** (or end of current academic year).
- **Issuing Authority:**
  - Sub-Divisional Officer (SDO) / Tehsildar / Sub-Divisional Magistrate in Maharashtra.
- **Income Limit:**
  - Gross annual family income must be within ₹8,00,000 for the preceding 3 consecutive financial years."""

    # 8. Domicile / Candidature Types
    if "domicile" in q or "type a" in q or "type b" in q or "oms" in q:
        return """### 🏠 **Maharashtra Candidature Types & Domicile Proof**

| Candidature Type | Eligibility Criteria | Required Proof |
| :--- | :--- | :--- |
| **Type A** | Passed 10th & 12th from MH + Born/Domiciled in MH | Domicile Certificate / Birth Certificate / LC showing place of birth in MH |
| **Type B** | Candidate does not have Domicile, but Father/Mother is Domiciled in MH | Domicile Certificate of Father or Mother |
| **Type C** | Father/Mother is Govt of India employee posted in MH | Proforma-A from Central Govt office |
| **Type D** | Father/Mother is Maharashtra Govt / Corporation employee | Proforma-B from MH Govt department |
| **Type E** | Passed 10th/12th from MH-Karnataka disputed border area | Proforma-G1 / G2 certificate |
| **OMS (All India)** | Candidate from outside Maharashtra | JEE Main Scorecard + 12th Marksheet |"""

    # 9. Default Comprehensive Checklist
    return """### 📋 **Complete MHT-CET Admission Document Checklist**

Here is the master list of physical documents required for Scrutiny Center (FC) verification:

#### 1️⃣ **Mandatory for ALL Students:**
- ✅ **MHT-CET Scorecard 2026** (Printed)
- ✅ **CAP Online Application Form & FC Acknowledgement Receipt**
- ✅ **12th / HSC Marksheet** (Original + 3 photocopies)
- ✅ **10th / SSC Marksheet & Passing Certificate** (DOB proof)
- ✅ **Maharashtra Domicile Certificate** or **Birth Certificate** (MH State)
- ✅ **Indian Nationality Certificate** or **Passport** or **LC stating Indian**
- ✅ **School / Junior College Leaving Certificate (TC)**

#### 2️⃣ **If Claiming Category Reservation:**
- 🏷️ **OBC / VJ / NT / SEBC / SBC:** Caste Certificate + Caste Validity (CVC) + Non-Creamy Layer (NCL valid up to 31st March 2026).
- 🏷️ **SC / ST:** Caste / Tribe Certificate + Caste / Tribe Validity Certificate.
- 🏷️ **EWS:** Proforma-V Certificate issued by Tehsildar (Family income < ₹8 Lakhs).
- 🏷️ **TFWS:** Annual Income Certificate issued by Tehsildar (< ₹8 Lakhs).

#### 3️⃣ **Special Cases (If Applicable):**
- 📝 **Gap Year:** Gap Certificate Affidavit on ₹100 stamp paper.
- ♿ **PWD:** Disability Certificate (Min 40% permanent) / UDID Card.
- 🎖️ **Defence:** Proforma-C / D / E from Zilla Sainik Board / Commanding Officer.
- 🕌 **Minority:** Leaving Certificate showing religion/mother tongue or Proforma-O affidavit.

---
💡 *Ask me about any specific category, certificate validity, or proforma format!*"""


# ---------------------------------------------------------------------------
# Public Chat API for Document AI
# ---------------------------------------------------------------------------

def document_ai_chat(user_message: str) -> str:
    """
    Process document queries using specialized MHT-CET rules and Watsonx AI.
    """
    clean_msg = user_message.strip()
    if not clean_msg:
        return "Please ask your document or verification question!"

    # First attempt rule-based engine for guaranteed accurate regulatory details
    rule_resp = _rule_based_document_advisor(clean_msg)

    # If Watsonx is active and available, we can augment with custom LLM advice if needed
    try:
        llm_resp = chat(user_message, system_prompt=_DOC_SYSTEM_PROMPT)
        if llm_resp and not llm_resp.startswith("Watsonx Error:"):
            return llm_resp
    except Exception as exc:
        logger.debug("Watsonx document fallback: %s", exc)

    return rule_resp
