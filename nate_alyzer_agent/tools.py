# tools.py
import requests
from langchain_core.tools import tool
import config

@tool
def retrieve_transcript(video_id: str) -> dict:
    """Fetches the raw transcript text for a given video_id from a GCS bucket."""
    payload = {"video_id": video_id}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(config.RETRIEVER_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to call retriever tool: {str(e)}"}

@tool
def distill_and_classify_transcript(transcript_text: str) -> dict:
    """Analyzes raw transcript text to generate a Core Thesis and Key Concepts, then classifies it."""
    payload = {"transcript_text": transcript_text}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(config.PROCESSOR_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to call processor tool: {str(e)}"}

@tool
def save_transcript_to_anthology(processed_transcript: str, theme: str, video_id: str) -> dict:
    """Appends the final, processed transcript to the correct thematic anthology file in GCS."""
    payload = {"processed_transcript": processed_transcript, "theme": theme, "video_id": video_id}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(config.UPDATER_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to call updater tool: {str(e)}"}