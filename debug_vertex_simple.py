import vertexai
from vertexai.generative_models import GenerativeModel
import time

PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

print(f"1. Initializing Vertex AI (Project: {PROJECT_ID}, Loc: {LOCATION})...")
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("   - Init complete.")
except Exception as e:
    print(f"   - INIT FAILED: {e}")
    exit(1)

print(f"2. Loading Model {MODEL_NAME}...")
try:
    model = GenerativeModel(MODEL_NAME)
    print("   - Model loaded.")
except Exception as e:
    print(f"   - LOAD FAILED: {e}")
    exit(1)

print("3. Sending 'Hello' (Timeout=30s)...")
start = time.time()
try:
    response = model.generate_content("Hello, can you hear me?", stream=False)
    duration = time.time() - start
    print(f"   - Response received in {duration:.2f}s")
    print(f"   - Text: {response.text}")
except Exception as e:
    print(f"   - GENERATE FAILED: {e}")

print("Done.")
