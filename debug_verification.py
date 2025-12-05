
from google.cloud import storage

BUCKET = "nate-digital-twin-anthologies-djr"
FILE = "ai-strategy-leadership.md"
VIDEO_ID = "xZX4KHrqwhM"
EXPECTED_DATE = "2025-06-23"

def verify_anthology_update(anthology_bucket: str, anthology_file: str, video_id: str, expected_date: str):
    print(f"Verifying {video_id} in {anthology_file} with expected date {expected_date}...")
    client = storage.Client()
    bucket = client.bucket(anthology_bucket)
    blob = bucket.blob(anthology_file)
    
    if not blob.exists():
        print("File not found")
        return False, f"Anthology file {anthology_file} not found"
        
    content = blob.download_as_text()
    if f"<!-- VIDEO_ID: {video_id} -->" not in content:
        print("Video ID not found")
        return False, f"Video ID {video_id} not found in {anthology_file}"
        
    # Verify Date
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if f"<!-- VIDEO_ID: {video_id} -->" in line:
            print(f"Found Video ID at line {i+1}")
            # Look ahead for Date
            for j in range(i, min(i + 15, len(lines))):
                print(f"Checking line {j+1}: '{lines[j]}'")
                if lines[j].strip().startswith("Date:"):
                    print(f"Found Date line: '{lines[j]}'")
                    if expected_date in lines[j]:
                        print("Date MATCH")
                        return True, "Verified"
                    else:
                        print(f"Date MISMATCH: '{lines[j].strip()}' vs '{expected_date}'")
                        return False, f"Date mismatch: found '{lines[j].strip()}', expected '{expected_date}'"
            print("Date line not found")
            return False, "Date line not found after Video ID"
    return False, "Loop finished without finding ID (should be caught above)"

if __name__ == "__main__":
    verify_anthology_update(BUCKET, FILE, VIDEO_ID, EXPECTED_DATE)
