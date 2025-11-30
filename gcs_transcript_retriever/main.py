# main.py
import os
from flask import jsonify
from google.cloud import storage

# Initialize the GCS client. This is best done globally.
storage_client = storage.Client()

def gcs_transcript_retriever(request):
    """
    An HTTP-triggered Cloud Function that retrieves a transcript from a GCS bucket.
    Expects a POST request with a JSON body: {"video_id": "some_id"}
    """
    # Set CORS headers for the preflight request and the main response.
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405, headers

    # Get the bucket name from an environment variable.
    bucket_name = os.environ.get('GCS_BUCKET_NAME')
    if not bucket_name:
        error_message = "CRITICAL: GCS_BUCKET_NAME environment variable is not set."
        print(f"ERROR: {error_message}")
        return jsonify({"error": error_message}), 500, headers

    # Get the JSON payload from the request.
    request_json = request.get_json(silent=True)
    if not request_json or 'video_id' not in request_json:
        return jsonify({"error": "Invalid request: JSON payload with 'video_id' is required."}), 400, headers

    video_id = request_json['video_id']
    blob_name = f"{video_id}.txt"

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return jsonify({"error": f"Transcript not found for video_id: {video_id}"}), 404, headers

        # Download the content of the file as a string.
        transcript_text = blob.download_as_text()

        return jsonify({"transcript_text": transcript_text}), 200, headers

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        print(f"ERROR: {error_message}")
        return jsonify({"error": error_message}), 500, headers