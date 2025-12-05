
from google.cloud import firestore

def reset_status():
    db = firestore.Client(project="nate-digital-twin")
    vid = "W3cIo4xcrWo"
    print(f"Resetting status for {vid}...")
    doc_ref = db.collection("processed_videos").document(vid)
    doc_ref.set({"status": "PROCESSING_TEST_RESET"}, merge=True)
    print("Done.")

if __name__ == "__main__":
    reset_status()
