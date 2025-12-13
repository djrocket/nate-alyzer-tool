# AI Agent Guide: YouTube Fetcher Module

## Purpose
Use this module `youtube_fetcher` whenever you need to retrieve the transcript (text content) and usage metadata (publish date) from a YouTube video. 

## When to Use
- **User Request**: "Summarize this video", "Extract insights from this youtube link", "What did X say in this video?".
- **Input**: A YouTube URL (any format: `youtube.com/watch?v=...`, `youtu.be/...`, etc.).

## How to Use (Code Pattern)

Always use this exact pattern to ensure robust fetching:

```python
from youtube_fetcher import YouTubeFetcher
import os

# 1. Initialize
fetcher = YouTubeFetcher()

# 2. Define Inputs
video_url = "YOUR_VIDEO_URL_HERE"
# Optional: Use cookies if available in the workspace for better success rates
cookies = "cookies.txt" if os.path.exists("cookies.txt") else None

# 3. Fetch
transcript, publish_date = fetcher.get_transcript(video_url, cookies_path=cookies)

# 4. Handle Result
if transcript:
    # SUCCESS
    # 'publish_date' will be "YYYY-MM-DD" or "unknown"
    # 'transcript' is a single string of cleaning text (no timestamps)
    print(f"Video published: {publish_date}")
    print(f"Content: {transcript}")
else:
    # FAILURE
    print("Could not retrieve transcript. The video might be private, deleted, or no English captions exist.")
```

## Critical Notes
- **Return Values**: `get_transcript` returns a tuple `(text, date)`. `text` is `None` on failure.
- **Cookies**: If the user provides a `cookies.txt` file, ALWAYS pass it. It significantly improves success rates against YouTube's bot detection.
- **Language**: This module currently defaults to fetching **English** (en, en-US, en-GB) transcripts only.
