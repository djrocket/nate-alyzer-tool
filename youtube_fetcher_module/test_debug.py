import logging
import sys
import os

# Add local path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from youtube_fetcher.client import YouTubeFetcher

def test():
    fetcher = YouTubeFetcher()
    video_id = "pEsoqm0o3Dk"
    
    print("Testing Android Client WITHOUT cookies...")
    res = fetcher._fetch_ytdlp(video_id, None, client="android")
    if res:
        print("SUCCESS (No Cookies)")
    else:
        print("FAILURE (No Cookies)")

    # Check if cookies exist to test WITH cookies
    cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if os.path.exists(cookies_path):
        print(f"\nTesting Android Client WITH cookies ({cookies_path})...")
        res = fetcher._fetch_ytdlp(video_id, cookies_path, client="android")
        if res:
             print("SUCCESS (With Cookies)")
        else:
             print("FAILURE (With Cookies)")
    else:
        print("No cookies.txt found to test.")

if __name__ == "__main__":
    test()
