
import sys
import os
from google.cloud import storage

VIDEO_ID = "xZX4KHrqwhM"
TRANSCRIPT_BUCKET = "nate-digital-twin-transcript-cache"

def clean_transcript():
    print(f"Cleaning transcript for {VIDEO_ID}...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(TRANSCRIPT_BUCKET)
    blob = bucket.blob(f"{VIDEO_ID}.txt")
    
    content = blob.download_as_text()
    print(f"Original Length: {len(content)}")
    
    # Aggressive cleaning
    # 1. Replace literal backslashes with nothing or space (they are often artifacts)
    cleaned = content.replace("\\", " ")
    # 2. Replace double quotes with single quotes to avoid JSON string breakage
    cleaned = cleaned.replace('"', "'")
    # 3. Ensure newlines are just \n
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    
    # 4. Remove any weird control characters
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch == '\n')
    
    print(f"Cleaned Length: {len(cleaned)}")
    
    # Upload back
    blob.upload_from_string(cleaned)
    print("Uploaded cleaned transcript.")

if __name__ == "__main__":
    clean_transcript()
