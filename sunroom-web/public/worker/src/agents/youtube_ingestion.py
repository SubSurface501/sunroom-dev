import logging
import os
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from supabase import Client
from db.schemas import UserIntegration
from .base import BaseAgent
import io

logger = logging.getLogger(__name__)

class IngestYoutubeChannelAgent(BaseAgent):
    def __init__(self, db: Client, worker, llm):
        super().__init__(db, worker, llm)
        self.youtube_api_key = os.environ.get("YOUTUBE_API_KEY") 

    def _get_youtube_service(self, credentials: UserIntegration):
        creds = Credentials.from_authorized_user_info(info={
            'refresh_token': credentials.refresh_token,
            'client_id': os.environ.get("GOOGLE_CLIENT_ID"),
            'client_secret': os.environ.get("GOOGLE_CLIENT_SECRET"),
            'token_uri': 'https://oauth2.googleapis.com/token'
        })
        creds.refresh(Request())
        
        return build('youtube', 'v3', credentials=creds)

    def _parse_sbv_to_text(self, sbv_content: str) -> str:
        """
        Parses SBV caption format to plain text.
        SBV format:
        0:00:00.599,0:00:04.160
        Text line 1
        Text line 2

        0:00:04.160,0:00:06.770
        Text line 3
        """
        lines = sbv_content.splitlines()
        text_lines = []
        timestamp_pattern = re.compile(r'^\d:\d{2}:\d{2}\.\d{3},\d:\d{2}:\d{2}\.\d{3}$')

        for line in lines:
            if not line.strip():
                continue
            if timestamp_pattern.match(line.strip()):
                continue
            text_lines.append(line.strip())
        
        return " ".join(text_lines)

    def _get_captions_from_api(self, youtube_service, video_id: str) -> str | None:
        try:
            # 1. List available caption tracks
            request = youtube_service.captions().list(
                part="snippet",
                videoId=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No caption tracks found for video {video_id}")
                return None

            # 2. Select the best track (Prioritize English, Manual > ASR)
            best_track_id = None
            # First pass: Look for English + Manual (kind='standard')
            for item in response["items"]:
                snippet = item["snippet"]
                if snippet["language"] == "en" and snippet["trackKind"] == "standard":
                    best_track_id = item["id"]
                    break
            
            # Second pass: Look for English + ASR (kind='ASR') if no manual
            if not best_track_id:
                for item in response["items"]:
                    snippet = item["snippet"]
                    if snippet["language"] == "en" and snippet["trackKind"] == "ASR":
                        best_track_id = item["id"]
                        break
            
            # Fallback: Take the first available if no English found (rare but possible)
            if not best_track_id and response["items"]:
                 best_track_id = response["items"][0]["id"]

            if not best_track_id:
                 return None

            # 3. Download the track
            # tfmt='sbv' is a simple format easier to parse than generic xml
            download_request = youtube_service.captions().download(
                id=best_track_id,
                tfmt="sbv" 
            )
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, download_request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            sbv_content = fh.getvalue().decode("utf-8")
            return self._parse_sbv_to_text(sbv_content)

        except Exception as e:
            logger.error(f"Error fetching captions via API for {video_id}: {e}")
            return None

    def run_task(self, user_id: str):
        logger.info(f"IngestYoutubeChannelAgent started for user {user_id}")

        # 1. Get user's Google credentials
        user_integration = self.db.table("User_Integrations").select("*").eq("user_id", user_id).eq("service_name", "google").single().execute().data
        if not user_integration:
            logger.warning(f"No YouTube/Google integration found for user {user_id}")
            return

        credentials = UserIntegration(**user_integration)
        youtube = self._get_youtube_service(credentials)

        # 2. Fetch all videos from the YouTube API
        all_videos = []
        next_page_token = None
        while True:
            request = youtube.search().list(
                part="snippet",
                forMine=True, 
                type="video",
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            # Filter out non-public videos
            items = response.get("items", [])
            if items:
                video_ids = [item["id"]["videoId"] for item in items]
                status_request = youtube.videos().list(
                    part="status",
                    id=",".join(video_ids)
                )
                status_response = status_request.execute()
                
                public_video_ids = set()
                for video_detail in status_response.get("items", []):
                    if video_detail["status"]["privacyStatus"] == "public":
                        public_video_ids.add(video_detail["id"])
                
                public_items = [item for item in items if item["id"]["videoId"] in public_video_ids]
                all_videos.extend(public_items)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        
        logger.info(f"Found {len(all_videos)} PUBLIC videos for user {user_id}'s channel.")

        for video in all_videos:
            video_id = video["id"]["videoId"]
            video_title = video["snippet"]["title"]

            # 3. Check if SourceDocument with that youtube_video_id already exists
            response = self.db.table("Sources").select("id").eq("metadata->>youtube_video_id", video_id).execute()
            existing_source = response.data
            
            if not existing_source:
                logger.info(f"New video found: {video_title} ({video_id}). Fetching transcript via API...")
                
                transcript_content = self._get_captions_from_api(youtube, video_id)
                
                if not transcript_content:
                    logger.warning(f"Skipping video {video_id} due to no captions found via API.")
                    continue

                # 4. Create a new SourceDocument
                source_data = {
                    "user_id": user_id,
                    "raw_text": transcript_content,
                    "metadata": {"youtube_video_id": video_id, "title": video_title},
                    "title": video_title
                }
                new_source = self.db.table("Sources").insert(source_data).execute().data
                source_id = new_source[0]["id"]
                logger.info(f"Source {source_id} created for video {video_id}.")

                # 5. Dispatch an IndexAtomAgent task
                self.worker.send_task('agents.indexing.run', args=[source_id, user_id])
                logger.info(f"Dispatched IndexAtomAgent for source {source_id}.")

            else:
                logger.info(f"Video {video_title} ({video_id}) already ingested. Skipping.")

        logger.info(f"IngestYoutubeChannelAgent finished for user {user_id}")
