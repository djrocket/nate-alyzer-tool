
import requests
import json
from google.cloud import storage

UPDATER_URL = "https://us-central1-nate-digital-twin.cloudfunctions.net/anthology-updater"
ANTHOLOGY_BUCKET = "nate-digital-twin-anthologies-djr"

def test_updater():
    video_id = "TEST_ID_002"
    theme = "Uncategorized" 
    content = f"<!-- VIDEO_ID: {video_id} -->\nDate: 2025-01-01\n\nThis is a test content."
    
    payload = {
        "processed_transcript": content,
        "theme": theme,
        "video_id": video_id
    }
    headers = {"Content-Type": "application/json"}
    
    print(f"Calling Updater for {video_id}...")
    try:
        response = requests.post(UPDATER_URL, json=payload, headers=headers)
        response.raise_for_status()
        print("Updater response:", response.json())
        
        # Now check the file in GCS
        print(f"Checking GCS bucket {ANTHOLOGY_BUCKET} for {theme}.md...")
        client = storage.Client()
        bucket = client.bucket(ANTHOLOGY_BUCKET)
        blob = bucket.blob(f"{theme}.md")
        
        if blob.exists():
            file_content = blob.download_as_text()
            print("\n--- File Content ---")
            # Find our entry
            if video_id in file_content:
                idx = file_content.find(video_id)
                # Print surrounding context
                start = max(0, idx - 50)
                end = min(len(file_content), idx + 200)
                print(file_content[start:end])
            else:
                print("Video ID not found in file!")
        else:
            print("Anthology file not found!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_updater()
