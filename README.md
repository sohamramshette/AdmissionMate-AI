# 🎓 College Admission Assistant

> **AI-powered college recommendation platform for Maharashtra CET students.**
> Built with Python Flask + Bootstrap 5, powered by IBM Watsonx AI.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [IBM Watsonx Integration](#ibm-watsonx-integration)
- [Tech Stack](#tech-stack)
- [Roadmap](#roadmap)

---

## Overview

College Admission Assistant helps Maharashtra CET students find the best-fit colleges
by analysing their percentile, reservation category, branch preference, and city
preference. The platform provides:

- **AI-curated recommendations** (IBM Watsonx, pending integration)
- **Side-by-side college comparison** with key metrics
- **Conversational AI chat** for admission queries
- **Responsive, mobile-first UI** built with Bootstrap 5

---

## Features

| Feature | Status |
|---|---|
| Student profile form | ✅ Complete |
| Responsive Bootstrap UI | ✅ Complete |
| Flask routing & sessions | ✅ Complete |
| College recommendation cards | 🔲 Service stub |
| College comparison table | 🔲 Service stub |
| AI Chatbot UI | ✅ Complete |
| Chatbot backend (`/api/chat`) | 🔲 Watsonx pending |
| Dataset (CSV) loaded | ✅ Placeholder data |
| IBM Watsonx integration | 🔲 Config ready |

---

## Project Structure

```
college-admission-assistant/
│
├── app.py                  ← Flask application factory & routes
├── config.py               ← Environment-based configuration classes
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
├── README.md               ← This file
│
├── static/
│   ├── css/
│   │   └── style.css       ← Global stylesheet (Bootstrap companion)
│   ├── js/
│   │   └── main.js         ← Navbar, chat, form validation, scroll-reveal
│   └── images/             ← Static images (add your assets here)
│
├── templates/
│   ├── base.html           ← Master layout: navbar, footer, flash messages
│   ├── home.html           ← Landing page with hero + features
│   ├── student_form.html   ← CET student profile form
│   ├── recommendations.html← College recommendation cards
│   ├── compare.html        ← Side-by-side comparison table
│   └── chatbot.html        ← AI chat interface
│
├── services/
│   ├── __init__.py
│   ├── recommendation.py   ← Recommendation logic (stub)
│   ├── comparison.py       ← Comparison logic (stub)
│   ├── dataset.py          ← CSV dataset loader (pandas, cached)
│   └── watsonx.py          ← IBM Watsonx AI client wrapper (stub)
│
└── dataset/
    └── college_dataset.csv ← College data with CET cutoffs
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/college-admission-assistant.git
cd college-admission-assistant

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in at minimum: SECRET_KEY

# 5. Run the development server
python app.py
```

Open your browser at **http://localhost:5000**

### Production Deployment

```bash
# Using Gunicorn (Linux/macOS)
gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4

# Set environment variables in your hosting platform
# Never use FLASK_DEBUG=true in production
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask session secret — use a long random string |
| `FLASK_DEBUG` | No | `true` for development, `false` for production |
| `WATSONX_API_KEY` | For AI | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | For AI | Watsonx project identifier |
| `WATSONX_URL` | No | Regional endpoint (default: `us-south`) |
| `WATSONX_MODEL_ID` | No | Model ID (default: `ibm/granite-13b-chat-v2`) |
| `DATASET_PATH` | No | Custom path to the college CSV file |

---

## IBM Watsonx Integration

The Watsonx integration is **prepared but not yet active**. To enable it:

1. Create an IBM Cloud account at https://cloud.ibm.com
2. Provision a **Watsonx.ai** service instance
3. Create an **API key** at https://cloud.ibm.com/iam/apikeys
4. Create a **Watsonx project** and copy the Project ID
5. Add credentials to your `.env` file
6. Open `services/watsonx.py` and follow the `TODO` comments to
   uncomment and complete the `_get_client()` initialisation
7. Update `services/recommendation.py` to call the model for scoring

The chat endpoint (`/api/chat`) in `app.py` already calls
`services.watsonx.chat()` — it will automatically become live once
the service module is implemented.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Python Flask 3.0 |
| Templating | Jinja2 |
| Frontend CSS | Bootstrap 5.3 + Custom CSS |
| Frontend JS | Vanilla ES6 |
| Icons | Bootstrap Icons 1.11 |
| AI / NLP | IBM Watsonx (`ibm-watsonx-ai`) |
| Data processing | Pandas 2.2 |
| Production server | Gunicorn |
| Config management | python-dotenv |

---

## Roadmap

- [ ] Implement recommendation algorithm (dataset filter + Watsonx scoring)
- [ ] Wire comparison page to live dataset
- [ ] Connect Watsonx chat with conversation history
- [ ] Add NAAC / NIRF ranking data to the dataset
- [ ] User authentication (save shortlisted colleges)
- [ ] Export recommendations as PDF
- [ ] Deploy to IBM Code Engine / Cloud Foundry

---

## License

MIT © 2024 College Admission Assistant Project
