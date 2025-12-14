# YouTube Fetcher Module

A robust, multi-strategy YouTube transcript fetcher designed for high availability and reliability. This module encapsulates logic to bypass common ephemeral IP blocks and API limitations by layering multiple fetching libraries (`youtube_transcript_api`, `yt-dlp` Android/Web clients, and direct internal API calls).

## Installation

It is recommended to use a virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
```

Then install the package:

```bash
pip install -r requirements.txt
pip install .
```

## Usage

### Simple One-Liner (Recommended)

```python
from youtube_fetcher import yt_fetch

# Returns string: "Date: YYYY-MM-DD\n\n[Content]"
content = yt_fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if content:
    print(content)
else:
    print("Failed to fetch.")
```

### Advanced Usage (Client Class)

```python
from youtube_fetcher import YouTubeFetcher
fetcher = YouTubeFetcher()

# Returns tuple: (transcript_str, date_str)
transcript, date = fetcher.get_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```

## Strategies Used

1.  **YouTubeTranscriptApi (Clean)**: Fastest, standard method.
2.  **yt-dlp (Android Client)**: Mimics mobile app traffic, often less restricted.
3.  **yt-dlp (Web Client)**: Mimics browser traffic.
4.  **Authenticated Requests**: If `cookies.txt` is provided, attempts authenticated calls.
5.  **Manual Fallback**: specific parsing of `timedtext` API if other methods fail.
