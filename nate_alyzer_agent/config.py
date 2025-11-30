# config.py
PROJECT_ID = "nate-digital-twin"
LOCATION = "us-central1"
AGENT_MODEL = "gemini-2.5-flash"
RETRIEVER_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/gcs-transcript-retriever"
PROCESSOR_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/transcript-processor-and-classifier"
UPDATER_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/anthology-updater"