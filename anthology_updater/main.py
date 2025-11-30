# main.py
import os
from flask import jsonify
from google.cloud import storage

storage_client = storage.Client()

# This dictionary maps the theme from the LLM to a clean, URL-safe filename.
THEME_TO_FILENAME = {
    "AI Strategy & Leadership": "ai-strategy-leadership.md",
    "Prompt & Context Engineering": "prompt-context-engineering.md",
    "Agentic Architectures & Systems": "agentic-architectures-systems.md",
    "Model Analysis & Limitations": "model-analysis-limitations.md",
    "Market Analysis & Future Trends": "market-analysis-future-trends.md",
    "News & Weekly Recap": "news-weekly-recap.md",
    "Uncategorized": "uncategorized.md"
}

def anthology_updater(request):
    """
    An HTTP-triggered Cloud Function that appends a processed transcript
    to the correct thematic anthology file in GCS.
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405, headers

    bucket_name = os.environ.get('ANTHOLOGY_BUCKET_NAME')
    if not bucket_name:
        error_message = "CRITICAL: ANTHOLOGY_BUCKET_NAME environment variable is not set."
        print(f"ERROR: {error_message}")
        return jsonify({"error": error_message}), 500, headers

    request_json = request.get_json(silent=True)
    required_keys = ['processed_transcript', 'theme', 'video_id']
    if not request_json or not all(key in request_json for key in required_keys):
        return jsonify({"error": "Invalid request: JSON payload with 'processed_transcript', 'theme', and 'video_id' is required."}), 400, headers

    processed_transcript = request_json['processed_transcript']
    theme = request_json['theme']
    video_id = request_json['video_id']
    date_value = request_json.get('date', 'unknown')

    # Look up the filename from our dictionary.
    filename = THEME_TO_FILENAME.get(theme)
    if not filename:
        return jsonify({"error": f"Invalid theme provided: {theme}"}), 400, headers

    try:
        bucket = storage_client.bucket(bucket_name)

        # --- GLOBAL IDEMPOTENCY CHECK ACROSS ALL THEME FILES ---
        # If the video already exists in ANY themed anthology, skip appending regardless of current theme.
        idempotency_marker = f"<!-- VIDEO_ID: {video_id} -->"
        for fn in THEME_TO_FILENAME.values():
            b = bucket.blob(fn)
            if b.exists():
                content = b.download_as_text()
                if idempotency_marker in content:
                    print(f"Skipping duplicate video_id across anthologies: {video_id} already in {fn}")
                    return jsonify({"status": "skipped_duplicate", "video_id": video_id, "file": fn}), 200, headers

        # Proceed to append to the selected themed file
        blob = bucket.blob(filename)
        existing_content = ""
        if blob.exists():
            existing_content = blob.download_as_text()

        # If the file is new, start with the transcript. Otherwise, add separators.
        header_date = f"Date: {date_value}" if date_value else "Date: unknown"
        if existing_content:
            new_block = f"\n\n---\n\n{idempotency_marker}\n\n{header_date}\n\n{processed_transcript}"
        else:
            new_block = f"{idempotency_marker}\n\n{header_date}\n\n{processed_transcript}"

        updated_content = existing_content + new_block

        # Upload the entire updated content back to the blob.
        blob.upload_from_string(updated_content, content_type='text/markdown')

        return jsonify({"status": "appended", "video_id": video_id, "file": filename}), 200, headers

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(f"ERROR: {error_message}")
        return jsonify({"error": error_message}), 500, headers
