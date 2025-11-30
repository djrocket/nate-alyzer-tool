#!/usr/bin/env python
"""
Quickly test YouTube transcript retrieval for a single video.

Usage:
  python test_transcript_fetch.py --video https://youtu.be/aVXtoWm1DEM
  python test_transcript_fetch.py --video aVXtoWm1DEM

Optional: pass exported cookies.txt (Netscape format) to avoid 429:
  python test_transcript_fetch.py --video <url_or_id> --cookies cookies.txt
"""

import argparse
from ingest_videos import extract_video_id, fetch_transcript_en, _list_tracks


def main():
    ap = argparse.ArgumentParser(description="Test YouTube transcript retrieval")
    ap.add_argument("--video", required=True, help="YouTube URL or 11-char video ID")
    ap.add_argument("--cookies", help="Path to cookies.txt (Netscape format) for yt-dlp")
    args = ap.parse_args()

    vid = extract_video_id(args.video)
    print(f"Video ID: {vid}")
    # Show available tracks for diagnosis
    try:
        tracks = _list_tracks(vid)
        if tracks:
            print("Available caption tracks:")
            for t in tracks:
                print(f"- id={t.get('id')} lang={t.get('lang_code')} kind={t.get('kind')} name={t.get('name')}")
        else:
            print("No caption tracks listed by timedtext API.")
    except Exception as e:
        print(f"Failed to list tracks: {e}")
    text = fetch_transcript_en(vid, cookies_path=args.cookies)
    print(f"Transcript length: {len(text)} chars")
    preview = "\n".join(text.splitlines()[:20])
    print("\nFirst 20 lines:\n----------------")
    print(preview)


if __name__ == "__main__":
    main()
