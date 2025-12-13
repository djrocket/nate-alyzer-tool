# YouTube Fetcher Module

A robust, multi-strategy YouTube transcript fetcher designed for high availability and reliability. This module encapsulates logic to bypass common ephemeral IP blocks and API limitations by layering multiple fetching libraries (`youtube_transcript_api`, `yt-dlp` Android/Web clients, and direct internal API calls).

## Installation

```bash
pip install -r requirements.txt
pip install .
```

## Usage

```python
from youtube_fetcher import YouTubeFetcher

fetcher = YouTubeFetcher()

# Simple Fetch
url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
transcript, date = fetcher.get_transcript(url)

if transcript:
    print(f"Published on: {date}")
    print(f"Transcript: {transcript[:100]}...")
else:
    print("Failed to fetch transcript.")

# Authenticated Fetch (Use cookies.txt to bypass age-gating or strict blocks)
# Export cookies.txt from your browser using an extension like 'Get cookies.txt LOCALLY'
transcript, date = fetcher.get_transcript(url, cookies_path="cookies.txt")
```

## Strategies Used

1.  **YouTubeTranscriptApi (Clean)**: Fastest, standard method.
2.  **yt-dlp (Android Client)**: Mimics mobile app traffic, often less restricted.
3.  **yt-dlp (Web Client)**: Mimics browser traffic.
4.  **Authenticated Requests**: If `cookies.txt` is provided, attempts authenticated calls.
5.  **Manual Fallback**: specific parsing of `timedtext` API if other methods fail.
