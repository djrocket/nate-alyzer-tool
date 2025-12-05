# Nate-alyzer Agent — Quick Start

This repo deploys a LangGraph agent to Vertex AI Agent Engine and provides simple CLIs for running it on YouTube transcripts.

## Prerequisites
- Python venv with required libs installed for tools and CLIs (you already have this).
- GCP auth for GCS writes: run `gcloud auth application-default login` in your shell.
- A deployed Agent Engine resource (created by `nate_alyzer_agent/deploy_final.py`). Copy the printed resource path like `projects/<proj>/locations/us-central1/reasoningEngines/<ENGINE_ID>`.


## Architecture & Workflow

The pipeline follows this flow: `Local Script` → `GCS (Raw)` → `Agent (Brain)` → `Cloud Functions (Tools)` → `GCS (Final)`

### Step 1: The Trigger (Local)
- **Action:** You run `process_local_transcripts.py`.
- **Code:** `process_local_transcripts.py`
- **Cloud Resource:** None (Local Machine).

### Step 2: The Raw Storage
- **Action:** The script uploads the raw text file to GCS.
- **Cloud Resource:** GCS Bucket `nate-digital-twin-transcript-cache`.
- **Verification:** Check the bucket in the [Google Cloud Storage Browser](https://console.cloud.google.com/storage/browser?project=nate-digital-twin).

### Step 3: The Brain (Agent Engine)
- **Action:** The script sends a prompt ("Process video ID...") to the Vertex AI Agent Engine.
- **Cloud Resource:** Vertex AI Reasoning Engine (ID: `4486055819837702144`).
- **Verification:** Check the local terminal output for "Agent response: ok".

### Step 4: The Tools (Cloud Functions)
The Agent orchestrates the process by calling these three functions:

#### Tool A: Retriever
- **Action:** Fetches raw text from the cache bucket.
- **Cloud Resource:** Cloud Function `gcs-transcript-retriever`.
- **Verification:** Check logs in [Cloud Functions Overview](https://console.cloud.google.com/functions/list?project=nate-digital-twin).

#### Tool B: Processor (The Intelligence)
- **Action:** Uses Gemini 1.5 Flash to distill the "Core Thesis" and classify the video.
- **Cloud Resource:** Cloud Function `transcript-processor-and-classifier`.
- **Verification:** Check logs for "Executing LLM call...".

#### Tool C: Updater
- **Action:** Appends the processed entry to the correct anthology file in GCS.
- **Cloud Resource:** Cloud Function `anthology-updater`.
- **Verification:** Check logs for "Appended video...".

### Step 5: The Result (GCS Anthologies)
- **Action:** Final Markdown files are updated.
- **Cloud Resource:** GCS Bucket `nate-digital-twin-anthologies`.
- **Verification:** View/Download files from the [Google Cloud Storage Browser](https://console.cloud.google.com/storage/browser?project=nate-digital-twin).

## Prepare Transcripts (manual path)
1) Create a folder `transcripts/` at the repo root.
2) For each video, save a file named `<video_id>.txt` with the raw transcript.
3) Optional but recommended: put a date as the first line using this format: `date: MM-DD-YYYY` (e.g., `date: 11-04-2025`). The system normalizes to `YYYY-MM-DD` and writes it into anthologies. If missing/unreadable, entries use `Date: unknown`.

## Process and Upload
Run the helper to upload transcripts to GCS and trigger the agent (sequentially):

Windows PowerShell:
```
python process_local_transcripts.py --engine "projects/<proj>/locations/us-central1/reasoningEngines/<ENGINE_ID>" --bucket nate-digital-twin-transcript-cache --project nate-digital-twin --location us-central1 --dir transcripts
```

Linux/macOS (bash/zsh):
```
python process_local_transcripts.py \
  --engine "projects/<proj>/locations/us-central1/reasoningEngines/<ENGINE_ID>" \
  --bucket nate-digital-twin-transcript-cache \
  --project nate-digital-twin \
  --location us-central1 \
  --dir transcripts
```

What it does:
- Uploads each `<video_id>.txt` to `gs://nate-digital-twin-transcript-cache/<video_id>.txt`.
- Calls the deployed Agent Engine with a prompt to retrieve, process, classify and save to the anthology.

## Classification + Anthologies
- Categories include: AI Strategy & Leadership, Prompt & Context Engineering, Agentic Architectures & Systems, Model Analysis & Limitations, Market Analysis & Future Trends, News & Weekly Recap, and Uncategorized.
- Anthology files in GCS (by theme):
  - `ai-strategy-leadership.md`
  - `prompt-context-engineering.md`
  - `agentic-architectures-systems.md`
  - `model-analysis-limitations.md`
  - `market-analysis-future-trends.md`
  - `news-weekly-recap.md`
  - `uncategorized.md`
- Each entry is appended once across all themes using a per-video idempotency marker. If a video already exists in any anthology, further runs are skipped.

## Running the Agent Locally (optional)
- Quick sanity test:
  - `python nate_alyzer_agent/local_test.py --local --prompt "Say hello"`
- Remote test against your engine:
  - `python nate_alyzer_agent/local_test.py --engine "projects/<proj>/locations/us-central1/reasoningEngines/<ENGINE_ID>" --prompt "Say hello"`

## Troubleshooting
- 401/403 calling tools: grant “Cloud Functions Invoker” to the Agent Engine’s service account for all functions.
- New category/date support lives in the Cloud Functions. Redeploy both if you haven’t:
  - `transcript_processor_and_classifier/main.py`
  - `anthology_updater/main.py`
- If a transcript reprocesses but anthologies don’t change, check Logs Explorer for the Reasoning Engine and Cloud Functions for error messages.

## Files of Interest
- Agent deployment: `nate_alyzer_agent/deploy_final.py`
- Local/remote tests: `nate_alyzer_agent/local_test.py`
- Manual transcript flow: `process_local_transcripts.py`
- Transcript processor/classifier (Gemini + date parsing): `transcript_processor_and_classifier/main.py`
- Anthology updater (theme map + idempotency + date header): `anthology_updater/main.py`
