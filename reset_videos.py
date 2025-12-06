import argparse
from google.cloud import firestore
from google.cloud import storage

def reset_videos(project: str, bucket_name: str):
    db = firestore.Client(project=project)
    storage_client = storage.Client(project=project)
    bucket = storage_client.bucket(bucket_name)

    # Hardcoded list provided by user (Round 2)
    videos = [
        "xZX4KHrqwhM",
        "-5zFZznthw0",
        "B3rSU7XROrg",
        "jW89fT_pgOQ"
    ]

    print(f"Resetting {len(videos)} videos...")

    for vid in videos:
        vid = vid.strip()
        print(f"Resetting {vid}...")

        # 1. Delete from Firestore
        doc_ref = db.collection("video_status").document(vid)
        doc_ref.delete()
        print(f"  - Deleted from Firestore (video_status)")

        # 2. Delete from GCS Cache
        blob = bucket.blob(f"{vid}.txt")
        if blob.exists():
            blob.delete()
            print(f"  - Deleted from GCS Cache ({vid}.txt)")
        else:
            print(f"  - GCS Cache not found (already deleted?)")

if __name__ == "__main__":
    reset_videos("nate-digital-twin", "nate-digital-twin-transcript-cache")
