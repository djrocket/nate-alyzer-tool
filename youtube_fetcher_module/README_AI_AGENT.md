# AI Agent Guide: YouTube Fetcher Module

## Purpose
Use this module `youtube_fetcher` whenever you need to retrieve the transcript (text content) and usage metadata (publish date) from a YouTube video. 

## When to Use
- **User Request**: "Summarize this video", "Extract insights from this youtube link", "What did X say in this video?".
- **Input**: A YouTube URL (any format: `youtube.com/watch?v=...`, `youtu.be/...`, etc.).

## How to Use (Code Pattern)

### Primary Method: `yt_fetch` (Standard Format)

Use this for most tasks. It returns a formatted string containing the date and content.

```python
from youtube_fetcher import yt_fetch
import os

url = "YOUR_VIDEO_URL_HERE"
# Always use cookies if available
cookies = "cookies.txt" if os.path.exists("cookies.txt") else None

# Returns: "Date: YYYY-MM-DD\n\n[Transcript Text]"
result = yt_fetch(url, cookies_path=cookies)

if result:
    print(result) # Ready for analysis or saving
else:
    print("Failed to fetch transcript.")
```

### Low-Level Method: `YouTubeFetcher`

Use this if you need the date and transcript separated (e.g., for structured data entry).

```python
from youtube_fetcher import YouTubeFetcher

fetcher = YouTubeFetcher()
transcript, date = fetcher.get_transcript(url, cookies_path=cookies)
# date is "YYYY-MM-DD" or "unknown"
# transcript is the raw text string
```

## Critical Notes
- **Cookies**: If the user provides a `cookies.txt` file, ALWAYS pass it to improve success rates.
- **Language**: This module currently defaults to fetching **English** (en, en-US, en-GB) transcripts only.
