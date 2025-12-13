import vertexai
from vertexai.generative_models import GenerativeModel
import time
import sys

PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"

MODELS_TO_TEST = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.0-pro"
]

def log(msg, file):
    print(msg)
    file.write(msg + "\n")

def test_models():
    with open("model_report.txt", "w", encoding="utf-8") as f:
        log(f"Initializing Vertex AI for {PROJECT_ID}...", f)
        try:
            vertexai.init(project=PROJECT_ID, location=LOCATION)
        except Exception as e:
            log(f"Init failed: {e}", f)
            return

        for model_name in MODELS_TO_TEST:
            log(f"\nTesting {model_name}...", f)
            try:
                model = GenerativeModel(model_name)
                response = model.generate_content("Hello", stream=False)
                log(f"SUCCESS: {model_name} works! Response: {response.text.strip()}", f)
                return # Stop after finding one that works
            except Exception as e:
                # Catching generic Exception to ensure we log it
                log(f"FAILED: {model_name} - {str(e)}", f)

if __name__ == "__main__":
    test_models()
