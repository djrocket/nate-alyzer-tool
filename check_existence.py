
from google.cloud import storage

BUCKET = "nate-digital-twin-anthologies-djr"
FILE = "ai-strategy-leadership.md"
VIDEO_ID = "xZX4KHrqwhM"

def check():
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(FILE)
    content = blob.download_as_text()
    
    if VIDEO_ID in content:
        print(f"Video {VIDEO_ID} FOUND in GCS.")
        idx = content.find(VIDEO_ID)
        print(f"Context: {content[idx-50:idx+50]}")
    else:
        print(f"Video {VIDEO_ID} NOT FOUND in GCS.")

if __name__ == "__main__":
    check()
