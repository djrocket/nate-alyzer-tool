from youtube_transcript_api import YouTubeTranscriptApi
import inspect

try:
    print("\n--- __init__ signature ---")
    print(inspect.signature(YouTubeTranscriptApi.__init__))
except Exception as e:
    print(f"Failed to get __init__ signature: {e}")
