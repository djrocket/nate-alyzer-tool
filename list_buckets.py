
from google.cloud import storage

def list_buckets():
    project_id = "nate-digital-twin"
    storage_client = storage.Client(project=project_id)
    
    print(f"Listing buckets in {project_id}...")
    buckets = list(storage_client.list_buckets())
    for bucket in buckets:
        print(f"- {bucket.name}")

if __name__ == "__main__":
    list_buckets()
