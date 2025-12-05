
from google.cloud import storage

BUCKET = "nate-digital-twin-anthologies-djr"
FILE = "ai-strategy-leadership.md"
VIDEO_ID = "xZX4KHrqwhM"

def check():
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(FILE)
    content = blob.download_as_text()
    
    count = content.count(VIDEO_ID)
    print(f"Count of {VIDEO_ID}: {count}")
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if VIDEO_ID in line:
            print(f"Match at line {i+1}: {line}")
            # Print next 5 lines
            for j in range(i+1, min(i+6, len(lines))):
                print(f"  {lines[j]}")

if __name__ == "__main__":
    check()
