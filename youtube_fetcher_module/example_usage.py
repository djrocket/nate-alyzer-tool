import sys
import os

# Ensure we can import the local package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from youtube_fetcher import yt_fetch

def main():
    # Test Video: "AI News" (failing for user)
    # ID: pEsoqm0o3Dk
    video_url = "https://www.youtube.com/watch?v=pEsoqm0o3Dk"
    
    print(f"Fetching transcript using yt_fetch for: {video_url}")
    
    # Optional: Use cookies from parent dir if they exist
    cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if not os.path.exists(cookies_path):
        cookies_path = None
    else:
        print(f"Using cookies from: {cookies_path}")

    # Using the new simplified wrapper
    result = yt_fetch(video_url, cookies_path=cookies_path)
    
    if result:
        print("\nSUCCESS!")
        print("-" * 40)
        print(f"Result Sample (first 200 chars):\n{result[:200]}...")
        print("-" * 40)
        
        # Verify format
        if result.startswith("Date:") and "\n\n" in result:
             print("Format Verification: PASS")
        else:
             print("Format Verification: FAIL")
    else:
        print("\nFAILURE: Could not fetch transcript.")
        sys.exit(1)

if __name__ == "__main__":
    main()
