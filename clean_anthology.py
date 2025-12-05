
import re
from google.cloud import storage

BUCKET = "nate-digital-twin-anthologies-djr"
FILE = "ai-strategy-leadership.md"
VIDEO_ID = "xZX4KHrqwhM"

def clean_gcs_file():
    print(f"Cleaning {VIDEO_ID} from gs://{BUCKET}/{FILE}...")
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(FILE)
    
    if not blob.exists():
        print("File not found in GCS.")
        return

    content = blob.download_as_text()
    print(f"Original Length: {len(content)}")
    
    # Split by "<!-- VIDEO_ID: "
    parts = re.split(r'(<!-- VIDEO_ID: )', content)
    new_parts = [parts[0]] # Keep preamble
    
    removed = False
    for i in range(1, len(parts), 2):
        header = parts[i] # "<!-- VIDEO_ID: "
        body = parts[i+1]
        
        # Check if this block belongs to our video
        if body.startswith(f"{VIDEO_ID} -->"):
            print(f"Removing entry for {VIDEO_ID}")
            removed = True
            continue
        else:
            new_parts.append(header)
            new_parts.append(body)
            
    if not removed:
        print(f"Video ID {VIDEO_ID} not found in file.")
        # Check for fragments just in case
        if VIDEO_ID in content:
             print("WARNING: ID found but regex missed it. Check manually.")
        return

    new_content = "".join(new_parts)
    print(f"New Length: {len(new_content)}")
    
    blob.upload_from_string(new_content, content_type="text/markdown")
    print("Uploaded cleaned file to GCS.")

if __name__ == "__main__":
    clean_gcs_file()
