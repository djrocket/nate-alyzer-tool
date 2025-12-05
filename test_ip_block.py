from youtube_transcript_api import YouTubeTranscriptApi

try:
    print("Testing YouTubeTranscriptApi.list('HfvO5Hcdyt4')...")
    api = YouTubeTranscriptApi()
    t_list = api.list("HfvO5Hcdyt4")
    print("List Success!")
    
    print("Fetching transcript...")
    # Find generated since we know it exists
    transcript = t_list.find_generated_transcript(['en'])
    fetched = transcript.fetch()
    print("Fetch Success!")
except Exception as e:
    print(f"Failed: {repr(e)}")
