#!/usr/bin/env python
"""
Ingest YouTube videos from videos.yml:
  1) Read repo-root videos.yml (simple list of YouTube URLs)
  2) Fetch English transcripts (manual or auto) using youtube-transcript-api
  3) Write transcripts to GCS bucket as <video_id>.txt (overwrite)
  4) Trigger the deployed Agent Engine sequentially to process each video

Usage:
  python ingest_videos.py --engine "projects/<proj>/locations/us-central1/reasoningEngines/<id>" \
      --bucket nate-digital-twin-transcript-cache --project nate-digital-twin --location us-central1

Requirements (local runtime):
  pip install youtube-transcript-api pyyaml google-cloud-storage google-cloud-aiplatform
  gcloud auth application-default login   # to grant GCS write access
"""

import argparse
import re
import sys
import ast
import datetime
import os
from typing import List, Tuple, Optional

import yaml
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from google.cloud import storage
import requests
import xml.etree.ElementTree as ET
import tempfile
import glob
import yt_dlp


def extract_video_id(url: str) -> str:
    """Extract the 11-char YouTube video ID from common URL forms or return input if it already looks like an ID."""
    url = url.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Unable to extract video ID from: {url}")


def _list_tracks(video_id: str) -> List[dict]:
    """List available caption tracks via YouTube timedtext type=list."""
    list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
    try:
        lr = requests.get(list_url, timeout=15)
        tracks: List[dict] = []
        if lr.status_code == 200 and lr.text.strip():
            root = ET.fromstring(lr.text)
            for tr in root.findall('.//track'):
                tracks.append({
                    'id': tr.get('id'),
                    'lang_code': tr.get('lang_code'),
                    'kind': tr.get('kind'),
                    'name': tr.get('name')
                })
        return tracks
    except Exception:
        return []


def fetch_transcript_en(video_id: str, cookies_path: Optional[str] = None) -> Tuple[str, str]:
    """
    Fetches English transcript for a YouTube video ID using a robust multi-layer fallback strategy.
    Returns (transcript_text, publish_date).
    publish_date is 'YYYY-MM-DD' or 'unknown'.
    """
    
    # Helper to get date via yt-dlp
    def get_date_via_ytdlp(vid):
        try:
            url = f"https://www.youtube.com/watch?v={vid}"
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'cookiefile': cookies_path if cookies_path and os.path.exists(cookies_path) else None
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                upload_date = info.get('upload_date')
                if upload_date and len(upload_date) == 8:
                    return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        except Exception:
            pass
        return "unknown"

    publish_date = get_date_via_ytdlp(video_id)
    
    def _read_and_clean_vtt(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                vtt = f.read()
            lines = []
            for line in vtt.splitlines():
                s = line.strip()
                if not s or s.startswith("WEBVTT") or "-->" in s or s.isdigit():
                    continue
                lines.append(s)
            return "\n".join(lines)
        except Exception:
            return None

    has_cookies = False
    if cookies_path and os.path.exists(cookies_path):
        has_cookies = True

    # --- Layer 1: youtube_transcript_api without cookies ---
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            
        fetched = transcript.fetch()
        text = "\n".join([item.text for item in fetched])
        return text, publish_date
    except Exception:
        pass

    # --- Layer 2: yt-dlp without cookies (Android Client) ---
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(lang)s.%(ext)s"),
                "nocheckcertificate": True,
                "extractor_args": {"youtube": {"player_client": ["android"]}},
                "retries": 3,
                "sleep_requests": 1,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            candidates = []
            for pattern in (
                os.path.join(tmpdir, f"{video_id}.en.vtt"),
                os.path.join(tmpdir, f"{video_id}.en-US.vtt"),
                os.path.join(tmpdir, f"{video_id}.en-GB.vtt"),
                os.path.join(tmpdir, f"{video_id}.*.vtt"),
            ):
                candidates.extend(glob.glob(pattern))

            if candidates:
                content = _read_and_clean_vtt(candidates[0])
                if content:
                    return content, publish_date
    except Exception:
        pass

    # --- Layer 3: yt-dlp with cookies (Web Client) ---
    if has_cookies:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["en", "en-US", "en-GB"],
                    "subtitlesformat": "vtt",
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(lang)s.%(ext)s"),
                    "nocheckcertificate": True,
                    "extractor_args": {"youtube": {"player_client": ["web"]}},
                    "retries": 3,
                    "sleep_requests": 1,
                    "cookiefile": cookies_path,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

                candidates = []
                for pattern in (
                    os.path.join(tmpdir, f"{video_id}.en.vtt"),
                    os.path.join(tmpdir, f"{video_id}.en-US.vtt"),
                    os.path.join(tmpdir, f"{video_id}.en-GB.vtt"),
                    os.path.join(tmpdir, f"{video_id}.*.vtt"),
                ):
                    candidates.extend(glob.glob(pattern))

                if candidates:
                    content = _read_and_clean_vtt(candidates[0])
                    if content:
                        return content, publish_date
        except Exception:
            pass

    # --- Layer 4: youtube_transcript_api with cookies ---
    if has_cookies:
        try:
            import http.cookiejar
            cj = http.cookiejar.MozillaCookieJar(cookies_path)
            cj.load()
            session = requests.Session()
            session.cookies = cj
            api = YouTubeTranscriptApi(http_client=session)
            transcript_list = api.list(video_id)
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            
            fetched = transcript.fetch()
            text = "\n".join([item.text for item in fetched])
            return text, publish_date
        except Exception:
            pass

    # --- Layer 5: Manual Fallback (TimedText API) ---
    try:
        tracks = _list_tracks(video_id)
        def pick_track(tracks):
            # exact en manual
            for t in tracks:
                if (t.get('lang_code') == 'en') and (t.get('kind') != 'asr'):
                    return t
            # exact en auto
            for t in tracks:
                if (t.get('lang_code') == 'en') and (t.get('kind') == 'asr'):
                    return t
            # en variants manual
            for t in tracks:
                if (t.get('lang_code', '').startswith('en')) and (t.get('kind') != 'asr'):
                    return t
            # en variants auto
            for t in tracks:
                if (t.get('lang_code', '').startswith('en')) and (t.get('kind') == 'asr'):
                    return t
            return tracks[0] if tracks else None

        best = pick_track(tracks)
        if best and best.get('id'):
            track_id = best['id']
            track_url = f"https://www.youtube.com/api/timedtext?type=track&v={video_id}&id={track_id}&fmt=srv3"
            tr = requests.get(track_url, timeout=15)
            if tr.status_code == 200 and tr.text.strip():
                try:
                    troot = ET.fromstring(tr.text)
                    texts = []
                    for node in troot.findall('.//text'):
                        t = (node.text or '').strip()
                        if t:
                            texts.append(t)
                    if texts:
                        return "\n".join(texts), publish_date
                except ET.ParseError:
                    pass
        
        for lang in ("en", "en-US", "en-GB"):
            for params in (f"lang={lang}", f"lang={lang}&kind=asr"):
                url = f"https://www.youtube.com/api/timedtext?{params}&v={video_id}"
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200 and r.text.strip():
                        try:
                            root = ET.fromstring(r.text)
                        except ET.ParseError:
                            continue
                        texts = []
                        for node in root.findall('.//text'):
                            t = (node.text or '').strip()
                            if t:
                                texts.append(t)
                        if texts:
                            return "\n".join(texts), publish_date
                except Exception:
                    continue
    except Exception:
        pass

    return None, "unknown"


def upload_to_gcs(bucket_name: str, video_id: str, content: str, publish_date: str) -> str:
    """Uploads transcript to GCS with Date header."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_name = f"{video_id}.txt"
    blob = bucket.blob(blob_name)
    
    # Prepend date to content as a clear sentence
    full_content = f"This video was published on {publish_date}.\n\n{content}"
    
    blob.upload_from_string(full_content, content_type="text/plain")
    return f"gs://{bucket_name}/{blob_name}"


def verify_gcs_upload(bucket_name: str, video_id: str, expected_date: str) -> Tuple[bool, str]:
    """Verifies GCS file exists and contains the expected date."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{video_id}.txt")
        
        if not blob.exists():
            return False, "File not found in GCS"
            
        content = blob.download_as_text()
        if not content:
            return False, "File is empty"
            
        # Check for date sentence
        first_line = content.split('\n')[0].strip()
        expected_header = f"This video was published on {expected_date}."
        
        if first_line != expected_header:
            return False, f"Date mismatch. Expected '{expected_header}', found '{first_line}'"
            
        return True, "Verified"
    except Exception as e:
        return False, str(e)


def verify_anthology_update(anthology_bucket: str, anthology_file: str, video_id: str, expected_date: str) -> Tuple[bool, str]:
    """Verifies the video ID exists in the anthology file AND has the correct date."""
    try:
        client = storage.Client()
        bucket = client.bucket(anthology_bucket)
        blob = bucket.blob(anthology_file)
        
        if not blob.exists():
            return False, f"Anthology file {anthology_file} not found"
            
        content = blob.download_as_text()
        if f"<!-- VIDEO_ID: {video_id} -->" not in content:
            return False, f"Video ID {video_id} not found in {anthology_file}"
            
        # Verify Date
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if f"<!-- VIDEO_ID: {video_id} -->" in line:
                # Look ahead for Date
                for j in range(i, min(i + 15, len(lines))):
                    if lines[j].strip().startswith("Date:"):
                        if expected_date in lines[j]:
                            return True, "Verified"
                        else:
                            return False, f"Date mismatch: found '{lines[j].strip()}', expected '{expected_date}'"
                return False, "Date line not found after Video ID"
        
        return False, "Video ID found but verification logic failed"
    except Exception as e:
        return False, str(e)


def verify_firestore_update(db, video_id: str) -> Tuple[bool, str]:
    """Verifies Firestore status is COMPLETED."""
    if not db:
        return False, "No DB connection"
    try:
        doc = db.collection("processed_videos").document(video_id).get()
        if not doc.exists:
            return False, "Document not found"
        
        status = doc.to_dict().get("status")
        if status == "COMPLETED":
            return True, "Verified"
        else:
            return False, f"Status is {status}"
    except Exception as e:
        return False, str(e)


def read_videos_yml(path: str) -> List[str]:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if not data:
        return []
    return [str(x).strip() for x in data if str(x).strip()]


def append_to_anthology(bucket_name: str, theme_file: str, video_id: str, publish_date: str, content: str):
    """Appends the entry to the anthology file in GCS, preventing duplicates."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(theme_file)
        
        current_text = ""
        if blob.exists():
            current_text = blob.download_as_text()
            
        # Check for duplicate
        if f"<!-- VIDEO_ID: {video_id} -->" in current_text:
            print(f"INFO: Video {video_id} already exists in {theme_file}. Skipping append.")
            return True
            
        if not current_text:
             current_text = f"# {theme_file.replace('.md', '').replace('-', ' ').title()}\n\n"
            
        # Construct the new entry
        new_entry = f"\n\n---\n\n<!-- VIDEO_ID: {video_id} -->\nDate: {publish_date}\n\n{content}"
        
        # Append
        updated_text = current_text + new_entry
        blob.upload_from_string(updated_text, content_type="text/markdown")
        return True
    except Exception as e:
        print(f"Error appending to anthology: {e}")
        return False


def process_video(engine_resource: str, project: str, location: str, video_id: str, publish_date: str) -> dict:
    import vertexai
    from vertexai.preview import reasoning_engines
    vertexai.init(project=project, location=location)
    agent = reasoning_engines.ReasoningEngine(engine_resource)
    prompt = (
        f"Retrieve the transcript for video_id={video_id}. "
        f"Analyze the content to identify the Core Thesis and Key Concepts. "
        f"Also identify the best anthology theme for this video (e.g. 'AI Strategy & Leadership'). "
        f"IMPORTANT: Do NOT save the transcript to the anthology. I will handle saving. "
        f"OUTPUT ONLY THE ANALYSIS. DO NOT CALL ANY TOOLS. I WILL FIRE YOU IF YOU CALL SAVE.\n"
        f"OUTPUT FORMAT:\n"
        f"THEME: [Theme Name]\n"
        f"CONTENT:\n[Your Analysis Here]"
    )
    return agent.query(prompt=prompt)


def main():
    parser = argparse.ArgumentParser()
    # Use the Engine ID from process_local_transcripts.py which is known to work
    parser.add_argument("--engine", default="projects/134885012683/locations/us-central1/reasoningEngines/2255577735638286336")
    parser.add_argument("--bucket", default="nate-digital-twin-transcript-cache")
    parser.add_argument("--anthology-bucket", default="nate-digital-twin-anthologies-djr")
    parser.add_argument("--project", default="nate-digital-twin")
    parser.add_argument("--location", default="us-central1")
    args = parser.parse_args()

    # Initialize Firestore
    try:
        from google.cloud import firestore
        db = firestore.Client(project=args.project)
    except Exception:
        db = None

    videos = read_videos_yml("videos.yml")
    
    summary_lines = []
    summary_lines.append(f"Run started at: {datetime.datetime.now().isoformat()}")
    summary_lines.append("=" * 60)
    summary_lines.append(f"{'VIDEO ID':<15} | {'STEP':<25} | {'STATUS':<10} | {'DETAILS'}")
    summary_lines.append("-" * 60)

    print("Processing videos... (See summary.txt for verification details)")

    for url in videos:
        try:
            vid = extract_video_id(url)
        except ValueError as e:
            summary_lines.append(f"{'INVALID':<15} | {'Init':<25} | {'FAILED':<10} | {url} ({e})")
            continue
        
        print(f"Processing {vid}...", end="", flush=True)
        
        # 0) Check Firestore status
        if db:
            doc_ref = db.collection("processed_videos").document(vid)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                if data.get("status") == "COMPLETED":
                    summary_lines.append(f"{vid:<15} | {'Check Firestore':<25} | {'SKIP':<10} | Already COMPLETED")
                    print(" Skipped (Already Completed)")
                    continue

            # Mark as processing
            try:
                doc_ref.set({
                    "status": "PROCESSING",
                    "started_at": firestore.SERVER_TIMESTAMP,
                    "video_id": vid
                }, merge=True)
            except Exception:
                pass
        
        # 1) Fetch transcript & Date
        try:
            cookies_file = "cookies.txt" if os.path.exists("cookies.txt") else None
            text, publish_date = fetch_transcript_en(vid, cookies_path=cookies_file)
            
            if not text:
                summary_lines.append(f"{vid:<15} | {'Fetch Transcript':<25} | {'FAILED':<10} | No text found")
                print(" FAILED (Transcript)")
                if db: doc_ref.set({"status": "FAILED", "error": "No transcript"}, merge=True)
                continue
                
            if publish_date == "unknown":
                summary_lines.append(f"{vid:<15} | {'Fetch Date':<25} | {'WARN':<10} | Date unknown")
            else:
                summary_lines.append(f"{vid:<15} | {'Fetch Date':<25} | {'PASS':<10} | {publish_date}")

        except Exception as e:
            summary_lines.append(f"{vid:<15} | {'Fetch Transcript':<25} | {'ERROR':<10} | {e}")
            print(" FAILED (Fetch Error)")
            if db: doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)
            continue

        # 2) Upload to GCS
        try:
            uri = upload_to_gcs(args.bucket, vid, text, publish_date)
            # summary_lines.append(f"{vid:<15} | {'Upload GCS':<25} | {'PASS':<10} | {uri}")
        except Exception as e:
            summary_lines.append(f"{vid:<15} | {'Upload GCS':<25} | {'ERROR':<10} | {e}")
            print(" FAILED (Upload)")
            if db: doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)
            continue

        # 3) VERIFY GCS Upload
        passed, msg = verify_gcs_upload(args.bucket, vid, publish_date)
        if passed:
            summary_lines.append(f"{vid:<15} | {'Verify GCS File':<25} | {'PASS':<10} | {msg}")
        else:
            summary_lines.append(f"{vid:<15} | {'Verify GCS File':<25} | {'FAIL':<10} | {msg}")
            print(" FAILED (GCS Verification)")
            if db: doc_ref.set({"status": "FAILED", "error": f"GCS Verify Failed: {msg}"}, merge=True)
            continue # STOP PROCESSING


        try:
            resp = process_video(args.engine, args.project, args.location, vid, publish_date)

            # Parse response
            resp_text = ""
            summary_lines.append(f"DEBUG: Raw Response Type: {type(resp)}")
            
            if isinstance(resp, dict):
                summary_lines.append(f"DEBUG: Response Keys: {list(resp.keys())}")
                
                if "response" in resp:
                    val = resp["response"]
                    summary_lines.append(f"DEBUG: 'response' value type: {type(val)}")
                    
                    # Handle stringified list/dict (e.g. "[{'text': ...}]")
                    if isinstance(val, str):
                        val = val.strip()
                        if (val.startswith("[") and val.endswith("]")) or (val.startswith("{") and val.endswith("}")):
                            try:
                                import ast
                                val = ast.literal_eval(val)
                                summary_lines.append(f"DEBUG: Parsed stringified value to: {type(val)}")
                            except Exception as e:
                                summary_lines.append(f"DEBUG: Failed to parse stringified value: {e}")

                    # Handle list (e.g. [{'text': '...', ...}])
                    if isinstance(val, list) and len(val) > 0:
                        if isinstance(val[0], dict):
                            # Try common keys
                            if "text" in val[0]:
                                resp_text = val[0]["text"]
                            elif "content" in val[0]:
                                resp_text = val[0]["content"]
                            elif "output" in val[0]:
                                resp_text = val[0]["output"]
                            else:
                                # Fallback: Dump the whole dict but warn
                                summary_lines.append(f"WARNING: No text/content key found in list item: {val[0].keys()}")
                                resp_text = str(val[0])
                        else:
                            resp_text = str(val[0])
                            
                    # Handle dict (e.g. {'text': '...', ...})
                    elif isinstance(val, dict):
                        if "text" in val:
                            resp_text = val["text"]
                        elif "content" in val:
                            resp_text = val["content"]
                        elif "output" in val:
                            resp_text = val["output"]
                        else:
                             summary_lines.append(f"WARNING: No text/content key found in dict: {val.keys()}")
                             resp_text = str(val)
                    else:
                        resp_text = str(val)
                        
                elif "text" in resp:
                    resp_text = resp["text"]
                elif "messages" in resp:
                     # LangGraph state dict
                     messages = resp["messages"]
                     if messages:
                         last_msg = messages[-1]
                         if hasattr(last_msg, "content"):
                             resp_text = str(last_msg.content)
            else:
                 resp_text = str(resp)

            # Log debug info (minimal)
            summary_lines.append(f"DEBUG: Parsed Response Length: {len(resp_text)}")
            
            # Parse THEME and CONTENT
            # Regex needs to be robust. Stop at newline or "CONTENT:"
            # We use re.DOTALL for content, but NOT for theme usually.
            # But let's use a single regex to capture both if possible, or split.
            
            # Robust Regex:
            # Look for THEME: ... (newline)
            # Look for CONTENT: ... (rest)
            
            theme_match = re.search(r"THEME:\s*(.+?)(?:\n|CONTENT:|$)", resp_text, re.IGNORECASE | re.DOTALL)
            content_match = re.search(r"CONTENT:\s*(.+)", resp_text, re.IGNORECASE | re.DOTALL)
            
            if theme_match and content_match:
                theme = theme_match.group(1).strip()
                # Fix: Agent might output literal "\n" characters
                analysis = content_match.group(1).strip().replace('\\n', '\n')
                
                # Normalize filename
                # e.g. "AI Strategy & Leadership" -> "ai-strategy-leadership.md"
                slug = theme.lower().replace(" & ", "-").replace(" ", "-").replace("---", "-")
                # Remove any non-alphanumeric chars except dashes
                slug = re.sub(r'[^a-z0-9-]', '', slug)
                
                # Fix: Remove trailing 'n' if it was captured by regex (common artifact)
                if slug.endswith('n') and len(slug) > 1:
                     # Heuristic: if it ends in 'n' but the word isn't obviously ending in n
                     # Actually, better to just trust the regex fix, but let's be safe.
                     # The regex was `(.+?)(?:\n|CONTENT:|$)`. If the text was `THEME: Foo\n`, 
                     # `.` doesn't match `\n`. But if it was `THEME: Foo\n` (literal), then `\` is matched, `n` is matched.
                     # So `Foo\n` becomes `foon`.
                     pass
                
                # Better fix for theme: Unescape it too!
                theme = theme.replace('\\n', '').strip()
                slug = theme.lower().replace(" & ", "-").replace(" ", "-").replace("---", "-")
                slug = re.sub(r'[^a-z0-9-]', '', slug)

                # Safety check for filename length
                if len(slug) > 100:
                    summary_lines.append(f"DEBUG: Slug too long ({len(slug)}), truncating.")
                    slug = slug[:100]
                
                anthology_file = f"{slug}.md"
                
                # Save LOCALLY (Bypass Cloud Function)
                append_to_anthology(args.anthology_bucket, anthology_file, vid, publish_date, analysis)
                
                summary_lines.append(f"{vid:<15} | {'Agent Processing':<25} | {'PASS':<10} | Analyzed & Saved Locally")
                summary_lines.append(f"{vid:<15} | {'Anthology File':<25} | {'INFO':<10} | {anthology_file}")
                
            else:
                # Fallback: If regex fails, maybe the agent didn't follow format.
                # Log warning and try to save to "uncategorized.md" with full text
                summary_lines.append(f"{vid:<15} | {'Agent Processing':<25} | {'WARN':<10} | Parse failed, saving to Uncategorized")
                anthology_file = "uncategorized.md"
                append_to_anthology(args.anthology_bucket, anthology_file, vid, publish_date, resp_text)

        except Exception as e:
            summary_lines.append(f"{vid:<15} | {'Agent Processing':<25} | {'ERROR':<10} | {e}")
            print(" FAILED (Agent Error)")
            if db: doc_ref.set({"status": "FAILED", "error": str(e)}, merge=True)
            continue

        # 5) VERIFY Anthology Update
        if anthology_file:
            passed, msg = verify_anthology_update(args.anthology_bucket, anthology_file, vid, publish_date)
            if passed:
                summary_lines.append(f"{vid:<15} | {'Verify Anthology':<25} | {'PASS':<10} | Found in {anthology_file}")
            else:
                summary_lines.append(f"{vid:<15} | {'Verify Anthology':<25} | {'FAIL':<10} | {msg}")
                print(" FAILED (Anthology Verification)")
                if db: doc_ref.set({"status": "FAILED", "error": f"Anthology Verify Failed: {msg}"}, merge=True)
                continue # STOP PROCESSING
        else:
            # If we don't know which file to check, we have to fail verification or check ALL (expensive)
            # For now, let's check all known anthologies as a fallback
            found_any = False
            for f in known_anthologies:
                passed, msg = verify_anthology_update(args.anthology_bucket, f, vid, publish_date)
                if passed:
                    found_any = True
                    anthology_file = f
                    summary_lines.append(f"{vid:<15} | {'Verify Anthology':<25} | {'PASS':<10} | Found in {f} (Fallback Search)")
                    break
            
            if not found_any:
                summary_lines.append(f"{vid:<15} | {'Verify Anthology':<25} | {'FAIL':<10} | Not found in any anthology")
                print(" FAILED (Anthology Verification)")
                if db: doc_ref.set({"status": "FAILED", "error": "Anthology Verify Failed"}, merge=True)
                continue

        # 6) Update Firestore
        if db:
            try:
                doc_ref.set({
                    "status": "COMPLETED",
                    "completed_at": firestore.SERVER_TIMESTAMP,
                    "anthology_file": anthology_file
                }, merge=True)
                
                # 7) VERIFY Firestore
                passed, msg = verify_firestore_update(db, vid)
                if passed:
                    summary_lines.append(f"{vid:<15} | {'Verify Firestore':<25} | {'PASS':<10} | Status is COMPLETED")
                else:
                    summary_lines.append(f"{vid:<15} | {'Verify Firestore':<25} | {'FAIL':<10} | {msg}")
                    print(" FAILED (Firestore Verification)")
                    continue

            except Exception as e:
                summary_lines.append(f"{vid:<15} | {'Firestore Update':<25} | {'ERROR':<10} | {e}")
                print(" FAILED (Firestore Error)")
                continue

        print(" Done")
        
    with open("summary.txt", "w") as f:
        f.write("\n".join(summary_lines))
    
    print("\nRun complete. Check summary.txt for verification details.")

if __name__ == "__main__":
    main()
