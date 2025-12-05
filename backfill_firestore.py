import argparse
from google.cloud import storage
from google.cloud import firestore

def backfill(project_id, bucket_name):
    print(f"Connecting to Firestore (Project: {project_id})...")
    db = firestore.Client(project=project_id)
    
    print(f"Connecting to GCS Bucket: {bucket_name}...")
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    
    try:
        blobs = list(bucket.list_blobs())
    except Exception as e:
        print(f"Error listing bucket: {e}")
        return

    print(f"Found {len(blobs)} files in bucket.")
    
    collection = db.collection("processed_videos")
    
    count = 0
    skipped = 0
    
    for blob in blobs:
        if not blob.name.endswith(".txt"):
            continue
            
        video_id = blob.name.replace(".txt", "")
        
        # Check if exists
        doc_ref = collection.document(video_id)
        doc = doc_ref.get()
        
        if doc.exists:
            print(f"Skipping {video_id}: Already in Firestore")
            skipped += 1
            continue
            
        # Write
        doc_ref.set({
            "status": "COMPLETED",
            "video_id": video_id,
            "backfilled": True,
            "completed_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Backfilled {video_id} -> COMPLETED")
        count += 1
        
    print(f"\nBackfill complete.")
    print(f"Added: {count}")
    print(f"Skipped: {skipped}")

if __name__ == "__main__":
    PROJECT = "nate-digital-twin"
    BUCKET = "nate-digital-twin-transcript-cache"
    
    # Allow overriding via args if needed
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=PROJECT)
    parser.add_argument("--bucket", default=BUCKET)
    args = parser.parse_args()
    
    backfill(args.project, args.bucket)
