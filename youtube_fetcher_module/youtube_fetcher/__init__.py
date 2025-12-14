from .client import YouTubeFetcher
from typing import Optional

def yt_fetch(url: str, cookies_path: Optional[str] = None) -> Optional[str]:
    """
    Fetches a YouTube transcript and returns it in a standardized format:
    
    Date: YYYY-MM-DD

    [Transcript Content]

    Args:
        url: The YouTube video URL or ID.
        cookies_path: Optional path to cookies.txt.

    Returns:
        str: The formatted transcript string, or None if fetching failed.
    """
    fetcher = YouTubeFetcher()
    transcript, date = fetcher.get_transcript(url, cookies_path=cookies_path)
    
    if transcript:
        return f"Date: {date}\n\n{transcript}"
    return None

__all__ = ["YouTubeFetcher", "yt_fetch"]
