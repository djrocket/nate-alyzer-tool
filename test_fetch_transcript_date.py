
import os
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

def get_date_via_ytdlp(vid, cookies_path=None):
    print(f"Fetching date for {vid}...")
    try:
        url = f"https://www.youtube.com/watch?v={vid}"
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'cookiefile': cookies_path if cookies_path and os.path.exists(cookies_path) else None
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            upload_date = info.get('upload_date')
            print(f"Raw upload_date: {upload_date}")
            if upload_date and len(upload_date) == 8:
                return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    except Exception as e:
        print(f"Warning: Failed to fetch date: {e}")
    return "unknown"

def fetch_transcript_en(video_id):
    print(f"Fetching transcript for {video_id}...")
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
        
        fetched = transcript.fetch()
        text = "\n".join([item.text for item in fetched])
        print(f"Transcript fetched: {len(text)} chars")
        return text
    except Exception as e:
        print(f"Transcript fetch failed: {e}")
        return None

def test_fetch(video_id):
    cookies_path = "cookies.txt"
    date = get_date_via_ytdlp(video_id, cookies_path)
    print(f"Date Result: {date}")
    
    transcript = fetch_transcript_en(video_id)
    if transcript:
        print("Transcript Result: Success")
    else:
        print("Transcript Result: Failed")

if __name__ == "__main__":
    # Test with the new video ID
    vid = "mldfMWbnZTg" 
    test_fetch(vid)
