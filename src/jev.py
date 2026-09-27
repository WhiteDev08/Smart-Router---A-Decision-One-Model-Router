import os
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"


def classify_question(question):
    payload = {
        "model": MODEL,
        "state": {
            "message": question
        },
        "questions": {
            "coding": {
                "type": "noul",
                "instructions": "How strongly is this question related to coding or programming?"
            },
            "general_query": {
                "type": "noul",
                "instructions": "How strongly is this question a general knowledge or general-purpose query?"
            },
            "summarization": {
                "type": "noul",
                "instructions": "How strongly is this question asking for summarization?"
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return {
        "coding": data["answers"]["coding"]["noul"],
        "general_query": data["answers"]["general_query"]["noul"],
        "summarization": data["answers"]["summarization"]["noul"]
    }
