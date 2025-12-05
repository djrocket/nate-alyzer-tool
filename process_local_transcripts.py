#!/usr/bin/env python
"""
Process manually saved transcripts:
  - Reads .txt files from a local folder (default: transcripts/)
  - Uploads each to GCS bucket as <video_id>.txt (overwrite)
  - Triggers the deployed Agent Engine to process + append to anthology

Usage:
  python process_local_transcripts.py \
    --engine "projects/<proj>/locations/us-central1/reasoningEngines/<id>" \
    --bucket nate-digital-twin-transcript-cache \
    --project nate-digital-twin --location us-central1 \
    --dir transcripts

Requirements:
  - google-cloud-storage
  - google-cloud-aiplatform
  - gcloud auth application-default login   (to write to GCS)
"""

import argparse
import os
import re
from pathlib import Path
from typing import List, Tuple

from google.cloud import storage
import vertexai
from vertexai.preview import reasoning_engines


def is_video_id(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", name))


def upload_to_gcs(bucket_name: str, video_id: str, content: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_name = f"{video_id}.txt"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type="text/plain")
    return f"gs://{bucket_name}/{blob_name}"


def process_with_engine(engine_resource: str, project: str, location: str, video_id: str) -> dict:
    vertexai.init(project=project, location=location)
    agent = reasoning_engines.ReasoningEngine(engine_resource)
    prompt = (
        f"Retrieve transcript for video_id={video_id}, analyze it, and save it to the anthology."
    )
    return agent.query(prompt=prompt)


def main():
    ap = argparse.ArgumentParser(description="Upload local transcripts and trigger Agent Engine")
    ap.add_argument("--engine", default="projects/134885012683/locations/us-central1/reasoningEngines/2255577735638286336", help="Agent Engine resource path")
    ap.add_argument("--bucket", default="nate-digital-twin-transcript-cache", help="GCS bucket for raw transcripts")
    ap.add_argument("--project", default="nate-digital-twin", help="GCP project ID")
    ap.add_argument("--location", default="us-central1", help="GCP location")
    ap.add_argument("--dir", default="transcripts", help="Local directory containing <video_id>.txt files")
    args = ap.parse_args()

    folder = Path(args.dir)
    if not folder.exists():
        print(f"Directory not found: {folder}")
        return

    txt_files = list(folder.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {folder}. Place files named <video_id>.txt.")
        return

    # Initialize Firestore
    try:
        from google.cloud import firestore
        db = firestore.Client(project=args.project)
        videos_ref = db.collection("processed_videos")
        print(f"Connected to Firestore project: {args.project}")
    except Exception as e:
        print(f"Warning: Could not connect to Firestore: {e}")
        print("Duplicate checking will be DISABLED.")
        db = None

    results: List[Tuple[str, str]] = []
    errors: List[Tuple[str, str]] = []

    for path in txt_files:
        video_id = path.stem
        if not is_video_id(video_id):
            errors.append((path.name, "filename is not a valid 11-char YouTube video ID"))
            continue

        # 0) Check Firestore
        if db:
            doc_ref = videos_ref.document(video_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                status = data.get("status")
                if status == "COMPLETED":
                    print(f"Skipping {video_id}: Already marked as COMPLETED in Firestore.")
                    results.append((video_id, "skipped_duplicate"))
                    continue
            
            # Mark as PROCESSING
            try:
                doc_ref.set({
                    "status": "PROCESSING",
                    "started_at": firestore.SERVER_TIMESTAMP,
                    "video_id": video_id
                }, merge=True)
            except Exception as e:
                print(f"Warning: Failed to update Firestore status: {e}")
            
            print(f"[New Video] Starting processing for {video_id}...")

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            errors.append((video_id, f"read_failed: {e}"))
            if db:
                doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)
            continue

        try:
            uri = upload_to_gcs(args.bucket, video_id, content)
            print(f"Uploaded {path.name} -> {uri}")
        except Exception as e:
            errors.append((video_id, f"upload_failed: {e}"))
            if db:
                doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)
            continue

        try:
            _ = process_with_engine(args.engine, args.project, args.location, video_id)
            print(f"Triggered agent for {video_id}")
            results.append((video_id, "processed"))
        except Exception as e:
            errors.append((video_id, f"agent_failed: {e}"))
            if db:
                doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)

    print("\n=== Summary ===")
    if results:
        print("Processed:")
        for vid, st in results:
            print(f"- {vid}: {st}")
    if errors:
        print("Errors:")
        for vid, msg in errors:
            print(f"- {vid}: {msg}")


if __name__ == "__main__":
    main()

