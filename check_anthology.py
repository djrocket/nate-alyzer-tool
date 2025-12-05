
from google.cloud import storage

def check_anthology():
    bucket_name = "nate-digital-twin-anthologies-djr"
    blob_name = "model-analysis-limitations.md"
    project_id = "nate-digital-twin"
    
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    print(f"Checking {blob_name} in {bucket_name}...")
    if blob.exists():
        blob.reload() # Ensure we have latest metadata
        print(f"Last Updated: {blob.updated}")
        
        content = blob.download_as_text()
        with open(blob_name, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Downloaded content to {blob_name}")
        
        if "W3cIo4xcrWo" in content:
            print("SUCCESS: Video ID found in file.")
        else:
            print("FAILURE: Video ID NOT found in file.")
    else:
        print("File does not exist.")

if __name__ == "__main__":
    check_anthology()
