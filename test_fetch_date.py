
import yt_dlp

def get_video_date(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        upload_date = info.get('upload_date')
        # upload_date is usually YYYYMMDD
        if upload_date and len(upload_date) == 8:
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
            return formatted_date
        return upload_date

if __name__ == "__main__":
    vid = "HfvO5Hcdyt4"
    print(f"Fetching date for {vid}...")
    date = get_video_date(vid)
    print(f"Date: {date}")
