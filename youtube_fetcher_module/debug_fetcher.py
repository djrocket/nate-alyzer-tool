import logging
import sys
import os
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

# Ensure we can import the local package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from youtube_fetcher.client import YouTubeFetcher, logger

def main():
    # 1. Print Versions
    print(f"Python Version: {sys.version}")
    print(f"yt-dlp Version: {yt_dlp.version.__version__}")
    try:
        import youtube_transcript_api
        print(f"youtube-transcript-api Version: {youtube_transcript_api.__version__}")
    except:
        print("youtube-transcript-api version unknown")

    # 2. Configure Logging to see EVERYTHING
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    
    # 3. Test the difficult video
    video_url = "https://www.youtube.com/watch?v=pEsoqm0o3Dk"
    print(f"\n--- Attempting to fetch: {video_url} ---")
    
    fetcher = YouTubeFetcher()
    
    # We will try to fetch and let the logs show us what happens
    transcript, date = fetcher.get_transcript(video_url)
    
    if transcript:
        print("\nSUCCESS!")
        print(f"Date: {date}")
        print(f"Length: {len(transcript)}")
    else:
        print("\nFAILURE: All strategies failed.")

if __name__ == "__main__":
    main()
