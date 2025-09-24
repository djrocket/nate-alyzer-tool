# app.py - FINAL CORRECT VERSION

import os
from flask import Flask, request, jsonify
from google.cloud import storage

app = Flask(__name__)

storage_client = storage.Client()
CACHE_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@app.route("/", methods=["POST", "OPTIONS"])
def handle_request(request): # Standard pattern: request is passed as an argument
    """The primary entry point for handling requests."""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    if not CACHE_BUCKET_NAME:
        return jsonify({"error": "CRITICAL: GCS_BUCKET_NAME environment variable is not set."}), 500, headers

    data = request.get_json()
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
            return jsonify({"transcript": cached_transcript, "source": "cache_final_version"}), 200, headers
        else:
            return jsonify({"status": f"Cache MISS for video ID: {video_id}. Live fetch disabled."}), 404, headers

    except Exception as e:
        return jsonify({"error": f"An error occurred while checking GCS cache: {str(e)}"}), 500, headers

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))