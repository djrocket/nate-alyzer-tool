
from google.cloud import firestore

def delete_entries():
    db = firestore.Client(project="nate-digital-twin")
    video_ids = ["HfvO5Hcdyt4", "W3cIo4xcrWo"]
    
    collection_ref = db.collection("processed_videos")
    
    for vid in video_ids:
        print(f"Deleting status for {vid}...")
        doc_ref = collection_ref.document(vid)
        doc_ref.delete()
        print(f"Deleted {vid}.")

if __name__ == "__main__":
    delete_entries()
