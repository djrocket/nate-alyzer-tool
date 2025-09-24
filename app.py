# app.py - COMPLETELY NEW FILENAMES AND FUNCTION NAMES

import os
from flask import Flask, request, jsonify
from google.cloud import storage

# The Flask object must be named 'app' for Gunicorn to find it.
app = Flask(__name__)

# Initialize GCS Client
storage_client = storage.Client()
# Get Bucket Name from Environment Variable
CACHE_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@app.route("/", methods=["POST", "OPTIONS"])
def handle_request(req): # Renamed function, renamed parameter
    """The new, primary entry point for handling requests."""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    if req.method == 'OPTIONS':
        return ('', 204, headers)

    # --- CORE LOGIC ---
    if not CACHE_BUCKET_NAME:
        return jsonify({"error": "CRITICAL: GCS_BUCKET_NAME environment variable is not set."}), 500, headers

    data = req.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing JSON payload or 'url' key."}), 400, headers

    video_url = data['url']
    
    try:
        video_id = video_url.split('v=')[1].split('&')[0]
    except IndexError:
        return jsonify({"error": "Invalid YouTube URL format."}), 400, headers

    try:
        bucket = storage_client.bucket(CACHE_BUCKET_NAME)
        blob_name = f"{video_id}.txt"
        blob = bucket.blob(blob_name)

        if blob.exists():
            cached_transcript = blob.download_as_text()
            return jsonify({"transcript": cached_transcript, "source": "cache_v2"}), 200, headers # Added _v2 to source
        else:
            # In this simple version, we just report a miss.
            return jsonify({"status": f"Cache MISS for video ID: {video_id}. Live fetch disabled."}), 404, headers

    except Exception as e:
        return jsonify({"error": f"An error occurred while checking GCS cache: {str(e)}"}), 500, headers

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))