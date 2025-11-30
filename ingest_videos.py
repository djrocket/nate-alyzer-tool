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
import os
import re
import sys
from typing import List, Tuple, Optional

import yaml
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from google.cloud import storage
import vertexai
from vertexai import agent_engines
import requests
import xml.etree.ElementTree as ET
import tempfile
import glob


def extract_video_id(url: str) -> str:
    """Extract the 11-char YouTube video ID from common URL forms or return input if it already looks like an ID."""
    url = url.strip()
    # If it already looks like a video ID, return as-is
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    # youtu.be/<id>
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    # youtube.com/watch?v=<id>
    m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    # youtube.com/embed/<id>
    m = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Unable to extract video ID from: {url}")


def _list_tracks(video_id: str) -> List[dict]:
    """List available caption tracks via YouTube timedtext type=list."""
    list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
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


def fetch_transcript_en(video_id: str, cookies_path: Optional[str] = None) -> str:
    """Fetch English transcript using a broad-compatible API call.
    Prefers English; tries a few variants. Returns plain text.
    """
    # If cookies are provided, prefer yt_dlp path immediately (cookies help avoid 429s)
    if cookies_path:
        try:
            import yt_dlp  # type: ignore
        except Exception:
            raise RuntimeError("yt_dlp not installed. Install with: pip install yt-dlp")

        import tempfile, glob
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(lang)s.%(ext)s"),
                "nocheckcertificate": True,
                # When using cookies, force the web client which supports cookies
                "extractor_args": {"youtube": {"player_client": ["web"]}},
                "retries": 10,
                "sleep_requests": 2,
                # Use exported cookies.txt (Netscape format)
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

            for path in candidates:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        vtt = f.read()
                    lines = []
                    for line in vtt.splitlines():
                        s = line.strip()
                        if not s or s.startswith("WEBVTT") or "-->" in s or s.isdigit():
                            continue
                        lines.append(s)
                    if lines:
                        return "\n".join(lines)
                except Exception:
                    continue
        # If cookies path provided but no subtitles fetched, fall through to other methods

    # First attempt: youtube-transcript-api if available and supports get_transcript
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        try:
            entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except NoTranscriptFound:
            try:
                entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US', 'en-GB', 'en'])
            except (NoTranscriptFound, TranscriptsDisabled):
                entries = None
        except TranscriptsDisabled:
            entries = None
        except Exception:
            entries = None

        if entries is not None:
            lines = [e.get('text', '').strip() for e in entries if e.get('text')]
            return "\n".join(lines)

    # Fallback: use YouTube timedtext API. First list tracks, then download the best English track.
    try:
        tracks = _list_tracks(video_id)
        # Preference: manual EN, then auto EN, then any EN variant, else first
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
            # Fetch by track id; fmt=srv3 is a modern XML-ish format
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
                        return "\n".join(texts)
                except ET.ParseError:
                    pass
        # As a last resort, attempt direct en/en-US/en-GB manual or ASR endpoints
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
                            return "\n".join(texts)
                except requests.RequestException:
                    continue
    except Exception:
        # swallow and fall through to error
        pass

    # Final fallback: use yt_dlp to download subtitles directly (manual or auto) and parse locally.
    try:
        try:
            import yt_dlp  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "yt_dlp not installed. Install with: pip install yt-dlp"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,          # do not download video
                "writesubtitles": True,         # write subtitles if available
                "writeautomaticsub": True,      # also consider auto-generated subs
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "vtt",
                # Save into our temp dir. %(id)s.%(lang)s.%(ext)s typically for subs
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(lang)s.%(ext)s"),
                "nocheckcertificate": True,
                # Robustness knobs. Use iOS client only when not using cookies.
                "retries": 10,
                "sleep_requests": 2,
            }
            if cookies_path:
                ydl_opts["cookiefile"] = cookies_path
            else:
                # Without cookies, iOS client reduces SABR/429 issues
                ydl_opts["extractor_args"] = {"youtube": {"player_client": ["ios"]}}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download will fetch subtitle files only due to the options above
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            # Look for English vtt files produced
            candidates = []
            for pattern in (
                os.path.join(tmpdir, f"{video_id}.en.vtt"),
                os.path.join(tmpdir, f"{video_id}.en-US.vtt"),
                os.path.join(tmpdir, f"{video_id}.en-GB.vtt"),
                os.path.join(tmpdir, f"{video_id}.*.vtt"),
            ):
                candidates.extend(glob.glob(pattern))

            for path in candidates:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        vtt = f.read()
                    lines = []
                    for line in vtt.splitlines():
                        s = line.strip()
                        if not s or s.startswith("WEBVTT") or "-->" in s or s.isdigit():
                            continue
                        lines.append(s)
                    if lines:
                        return "\n".join(lines)
                except Exception:
                    continue

        raise RuntimeError("No downloadable English subtitle found via yt_dlp download")
    except Exception as e:
        raise RuntimeError(
            f"No English transcript available for {video_id} via library, timedtext, or yt_dlp: {e}"
        )


def upload_to_gcs(bucket_name: str, video_id: str, content: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_name = f"{video_id}.txt"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type="text/plain")
    return f"gs://{bucket_name}/{blob_name}"


def load_videos_yml(path: str) -> List[str]:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError("videos.yml must be a simple YAML list of URLs or IDs")
    return [str(x).strip() for x in data if str(x).strip()]


def process_video(engine_resource: str, project: str, location: str, video_id: str) -> dict:
    vertexai.init(project=project, location=location)
    agent = agent_engines.get(engine_resource)
    prompt = (
        f"Retrieve transcript for video_id={video_id}, analyze it, and save it to the anthology."
    )
    return agent.query(prompt=prompt)


def main():
    parser = argparse.ArgumentParser(description="Ingest YouTube transcripts to GCS and trigger Agent Engine")
    parser.add_argument("--engine", required=True, help="Agent Engine resource path (projects/.../locations/.../reasoningEngines/ID)")
    parser.add_argument("--bucket", required=True, help="GCS bucket to store raw transcripts")
    parser.add_argument("--videos", default="videos.yml", help="Path to videos.yml (simple list)")
    parser.add_argument("--project", default="nate-digital-twin", help="GCP project for Agent Engine")
    parser.add_argument("--location", default="us-central1", help="GCP location for Agent Engine")
    args = parser.parse_args()

    try:
        urls = load_videos_yml(args.videos)
    except Exception as e:
        print(f"Failed to load {args.videos}: {e}")
        sys.exit(1)

    results: List[Tuple[str, str]] = []  # (video_id, status)
    errors: List[Tuple[str, str]] = []

    for url in urls:
        try:
            vid = extract_video_id(url)
        except Exception as e:
            errors.append((url, f"bad_url: {e}"))
            continue
        print(f"\n=== Processing {vid} ===")
        # 1) Fetch transcript
        try:
            text = fetch_transcript_en(vid)
            print(f"Fetched transcript: {len(text)} chars")
        except Exception as e:
            errors.append((vid, f"fetch_failed: {e}"))
            continue
        # 2) Upload to GCS (overwrite)
        try:
            uri = upload_to_gcs(args.bucket, vid, text)
            print(f"Uploaded to {uri}")
        except Exception as e:
            errors.append((vid, f"upload_failed: {e}"))
            continue
        # 3) Trigger Agent Engine
        try:
            resp = process_video(args.engine, args.project, args.location, vid)
            print("Agent response: ok")
            results.append((vid, "processed"))
        except Exception as e:
            errors.append((vid, f"agent_failed: {e}"))

    # Summary
    print("\n=== Summary ===")
    if results:
        print("Processed:")
        for vid, st in results:
            print(f"- {vid}: {st}")
    if errors:
        print("Errors:")
        for vid, msg in errors:
            print(f"- {vid}: {msg}")

    # Non-zero exit if any errors
    if errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
