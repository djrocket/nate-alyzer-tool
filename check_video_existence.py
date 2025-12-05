
from google.cloud import storage

def check_video_in_anthologies(video_id):
    bucket_name = "nate-digital-twin-anthologies-djr"
    project_id = "nate-digital-twin"
    
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    
    blobs = bucket.list_blobs()
    found = False
    for blob in blobs:
        if blob.name.endswith(".md"):
            content = blob.download_as_text()
            if f"<!-- VIDEO_ID: {video_id} -->" in content:
                print(f"Found {video_id} in {blob.name}")
                # Find the date line
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if f"<!-- VIDEO_ID: {video_id} -->" in line:
                        # Look ahead for Date:
                        for j in range(i, min(i+10, len(lines))):
                            if lines[j].strip().startswith("Date:"):
                                print(f"  {lines[j].strip()}")
                                break
                found = True
    
    if not found:
        print(f"{video_id} NOT found in any anthology.")

if __name__ == "__main__":
    check_video_in_anthologies("xZX4KHrqwhM")
