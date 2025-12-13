import sys
import os

# Ensure we can import the local package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from youtube_fetcher import YouTubeFetcher

def main():
    fetcher = YouTubeFetcher()
    
    # Test Video: "Me at the zoo" (stable, short, has captions)
    # ID: jNQXAC9IVRw
    video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    print(f"Fetching transcript for: {video_url}")
    
    # Optional: Use cookies from parent dir if they exist
    cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if not os.path.exists(cookies_path):
        cookies_path = None
    else:
        print(f"Using cookies from: {cookies_path}")

    transcript, date = fetcher.get_transcript(video_url, cookies_path=cookies_path)
    
    if transcript:
        print("\nSUCCESS!")
        print(f"Publish Date: {date}")
        print("-" * 40)
        print(f"Transcript Sample (first 200 chars):\n{transcript[:200]}...")
        print("-" * 40)
    else:
        print("\nFAILURE: Could not fetch transcript.")
        sys.exit(1)

if __name__ == "__main__":
    main()
