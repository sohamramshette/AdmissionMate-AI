import os
import logging

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client

    if _client:
        return _client

    credentials = Credentials(
        url=os.getenv("WATSONX_URL"),
        api_key=os.getenv("WATSONX_API_KEY"),
    )

    _client = ModelInference(
        model_id=os.getenv("WATSONX_MODEL_ID"),
        credentials=credentials,
        project_id=os.getenv("WATSONX_PROJECT_ID"),
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