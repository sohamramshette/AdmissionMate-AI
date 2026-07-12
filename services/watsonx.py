import logging
import os

from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_ID = "ibm/granite-3-3-8b-instruct"

_client = None


def _get_client():
    global _client

    if _client is not None:
        return _client

    api_key    = os.environ.get("WATSONX_API_KEY", "")
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    url        = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = os.environ.get("WATSONX_MODEL_ID", "").strip() or _DEFAULT_MODEL_ID

    if not api_key:
        raise ValueError("WATSONX_API_KEY is not set in the environment / .env file.")
    if not project_id:
        raise ValueError("WATSONX_PROJECT_ID is not set in the environment / .env file.")

    logger.debug("Initialising Watsonx ModelInference (model_id=%s)", model_id)

    credentials = Credentials(
        url=url,
        api_key=api_key,
    )

    _client = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={
            "temperature": 0.7,
            "max_new_tokens": 512,
        },
    )

    return _client


def chat(user_message: str, system_prompt: str = "") -> str:
    try:
        client = _get_client()

        prompt = f"""
{system_prompt}

User:
{user_message}

Assistant:
"""

        response = client.generate_text(prompt=prompt)

        return str(response).strip()

    except Exception as e:
        logger.exception(e)
        return f"Watsonx Error: {e}"


def summarize_recommendations(student_data, recommendations):
    """
    Generate an AI summary for the recommended colleges.
    """

    if not recommendations:
        return "No colleges matched the student's profile."

    college_text = ""

    for i, college in enumerate(recommendations[:5], start=1):
        college_text += (
            f"{i}. {college['name']}\n"
            f"Branch: {college['branch']}\n"
            f"City: {college['city']}\n"
            f"Cutoff: {college['cutoff']}\n\n"
        )

    prompt = f"""
You are an experienced MHT CET admission counselor.

Student Profile

Percentile: {student_data['cet_percentile']}
Category: {student_data['category']}
Preferred Branch: {student_data['preferred_branch']}
Preferred City: {student_data['preferred_city']}

Recommended Colleges

{college_text}

Write a personalized summary.

Mention:
- Why these colleges fit the student
- Dream / Target / Safe strategy
- Branch and city preferences

Keep the response under 150 words.
"""

    return chat(prompt)