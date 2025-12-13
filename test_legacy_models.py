import vertexai
from vertexai.language_models import TextGenerationModel
import time

PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"

def test_legacy():
    print(f"Initializing Vertex AI for {PROJECT_ID}...")
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"Init failed: {e}")
        return

    print("\nTesting text-bison (Legacy)...")
    try:
        model = TextGenerationModel.from_pretrained("text-bison")
        response = model.predict("Hello")
        print(f"SUCCESS: text-bison works! Response: {response.text.strip()}")
    except Exception as e:
        print(f"FAILED: text-bison - {e}")

if __name__ == "__main__":
    test_legacy()
