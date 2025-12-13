import re
import os
import requests
import xml.etree.ElementTree as ET
import tempfile
import glob
import logging
from typing import Tuple, Optional, List
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeFetcher:
    """
    A robust client for fetching YouTube transcripts using a multi-layer fallback strategy.
    Designed to be resilient against IP blocks and API changes.
    """

    def __init__(self):
        pass

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Video ID extraction logic."""
        url = url.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
            return url
        m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
        if m: return m.group(1)
        m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
        if m: return m.group(1)
        m = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)
        if m: return m.group(1)
        raise ValueError(f"Unable to extract video ID from: {url}")

    def get_transcript(self, video_url: str, cookies_path: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Fetches English transcript for a video URL.
        
        Args:
            video_url: The YouTube URL or Video ID.
            cookies_path: Optional path to cookies.txt for authenticated requests (bypasses some age-gating/blocks).

        Returns:
            Tuple[Optional[str], str]: (transcript_text, publish_date).
            - transcript_text is the full transcript or None if failed.
            - publish_date is 'YYYY-MM-DD' or 'unknown'.
        """
        try:
            video_id = self.extract_video_id(video_url)
        except ValueError as e:
            logger.error(f"Invalid URL: {e}")
            return None, "unknown"

        # 1. Get Date via yt-dlp (fastest stable method)
        publish_date = self._get_date_via_ytdlp(video_id, cookies_path)

        # 2. Try Fetching Transcript Strategies
        strategies = [
            ("YouTubeTranscriptApi (No Cookies)", lambda: self._fetch_api(video_id, None)),
            ("yt-dlp Android Client", lambda: self._fetch_ytdlp(video_id, cookies_path, client="android")),
            ("yt-dlp Web Client", lambda: self._fetch_ytdlp(video_id, cookies_path, client="web")),
            ("YouTubeTranscriptApi (With Cookies)", lambda: self._fetch_api(video_id, cookies_path)),
            ("Manual TimedText API", lambda: self._fetch_manual(video_id))
        ]

        for name, strategy in strategies:
            # Skip cookie strategies if no cookies provided
            if "Cookies" in name and not cookies_path and "No Cookies" not in name:
                continue
                
            try:
                content = strategy()
                if content:
                    logger.info(f"Success using strategy: {name}")
                    return content, publish_date
            except Exception as e:
                logger.debug(f"Strategy {name} failed: {e}")
                continue

        logger.error(f"All transcript fetch strategies failed for {video_id}")
        return None, publish_date

    def _get_date_via_ytdlp(self, video_id: str, cookies_path: Optional[str]) -> str:
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                'quiet': True, 'no_warnings': True, 'skip_download': True,
                'cookiefile': cookies_path if cookies_path and os.path.exists(cookies_path) else None
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                upload_date = info.get('upload_date')
                if upload_date and len(upload_date) == 8:
                    return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        except Exception:
            pass
        return "unknown"

    def _fetch_api(self, video_id: str, cookies_path: Optional[str]) -> Optional[str]:
        if cookies_path:
            import http.cookiejar
            cj = http.cookiejar.MozillaCookieJar(cookies_path)
            cj.load()
            session = requests.Session()
            session.cookies = cj
            api = YouTubeTranscriptApi(http_client=session)
        else:
            api = YouTubeTranscriptApi()

        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
        
        fetched = transcript.fetch()
        return " ".join([item['text'] for item in fetched]).replace('\n', ' ')

    def _fetch_ytdlp(self, video_id: str, cookies_path: Optional[str], client: str) -> Optional[str]:
        # Only run if client is 'android' (no cookies needed usually) or 'web' (needs cookies usually)
        # But we pass cookies if available regardless.
        
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(lang)s.%(ext)s"),
                "nocheckcertificate": True,
                "extractor_args": {"youtube": {"player_client": [client]}},
                "retries": 3,
                "cookiefile": cookies_path if cookies_path and os.path.exists(cookies_path) else None
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            candidates = []
            for pattern in (f"{video_id}.en.vtt", f"{video_id}.en-US.vtt", f"{video_id}.en-GB.vtt", f"{video_id}.*.vtt"):
                candidates.extend(glob.glob(os.path.join(tmpdir, pattern)))

            if candidates:
                return self._read_and_clean_vtt(candidates[0])
        return None

    def _read_and_clean_vtt(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                vtt = f.read()
            lines = []
            for line in vtt.splitlines():
                s = line.strip()
                if not s or s.startswith("WEBVTT") or "-->" in s or s.isdigit():
                    continue
                lines.append(s)
            return " ".join(lines).replace('\n', ' ')
        except Exception:
            return None

    def _fetch_manual(self, video_id: str) -> Optional[str]:
        tracks = self._list_tracks(video_id)
        if not tracks: return None

        # Priority: Manual EN -> Auto EN -> Manual EN-* -> Auto EN-*
        def score(t):
            lang = t.get('lang_code', '')
            kind = t.get('kind', '')
            s = 0
            if lang == 'en': s += 100
            elif lang.startswith('en'): s += 50
            if kind != 'asr': s += 20
            return s

        tracks.sort(key=score, reverse=True)
        best = tracks[0] if tracks else None

        if best and best.get('id'):
            track_url = f"https://www.youtube.com/api/timedtext?type=track&v={video_id}&id={best['id']}&fmt=srv3"
            tr = requests.get(track_url, timeout=15)
            if tr.status_code == 200 and tr.text.strip():
                try:
                    troot = ET.fromstring(tr.text)
                    texts = [node.text for node in troot.findall('.//text') if node.text]
                    if texts: return " ".join(texts).replace('\n', ' ')
                except Exception:
                    pass
        return None

    def _list_tracks(self, video_id: str) -> List[dict]:
        list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
        try:
            lr = requests.get(list_url, timeout=15)
            tracks = []
            if lr.status_code == 200 and lr.text.strip():
                root = ET.fromstring(lr.text)
                for tr in root.findall('.//track'):
                    tracks.append({
                        'id': tr.get('id'),
                        'lang_code': tr.get('lang_code'),
                        'kind': tr.get('kind'),
                        'name': tr.get('name')
                    })
            return tracks
        except Exception:
            return []
