import json
import urllib.parse
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, Optional, Tuple

try:
    import google.auth
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow
except ImportError:
    st.error("Google API libraries not installed. Please install them first.")

class YouTubeService:
    """Handles YouTube API operations and authentication"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/youtube.force-ssl']
    
    def load_oauth_config(self, json_file) -> Optional[Dict]:
        """Load Google OAuth configuration from uploaded JSON file"""
        try:
            config = json.load(json_file)
            if 'web' in config:
                return config['web']
            elif 'installed' in config:
                return config['installed']
            else:
                st.error("Invalid Google OAuth JSON format")
                return None
        except Exception as e:
            st.error(f"Error loading Google OAuth JSON: {e}")
            return None
    
    def generate_auth_url(self, client_config: Dict) -> Optional[str]:
        """Generate OAuth authorization URL"""
        try:
            auth_url = (
                f"{client_config['auth_uri']}?"
                f"client_id={client_config['client_id']}&"
                f"redirect_uri={urllib.parse.quote(client_config['redirect_uris'][0])}&"
                f"scope={urllib.parse.quote(' '.join(self.scopes))}&"
                f"response_type=code&"
                f"access_type=offline&"
                f"prompt=consent"
            )
            return auth_url
        except Exception as e:
            st.error(f"Error generating auth URL: {e}")
            return None
    
    def exchange_code_for_tokens(self, client_config: Dict, auth_code: str) -> Optional[Dict]:
        """Exchange authorization code for access and refresh tokens"""
        try:
            token_data = {
                'client_id': client_config['client_id'],
                'client_secret': client_config['client_secret'],
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': client_config['redirect_uris'][0]
            }
            
            response = requests.post(client_config['token_uri'], data=token_data)
            
            if response.status_code == 200:
                tokens = response.json()
                return tokens
            else:
                st.error(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            st.error(f"Error exchanging code for tokens: {e}")
            return None
    
    def create_service(self, credentials_dict: Dict) -> bool:
        """Create YouTube API service from credentials"""
        try:
            if 'token' in credentials_dict:
                self.credentials = Credentials.from_authorized_user_info(credentials_dict)
            else:
                self.credentials = Credentials(
                    token=credentials_dict.get('access_token'),
                    refresh_token=credentials_dict.get('refresh_token'),
                    token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                    client_id=credentials_dict.get('client_id'),
                    client_secret=credentials_dict.get('client_secret'),
                    scopes=self.scopes
                )
            
            self.service = build('youtube', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            st.error(f"Error creating YouTube service: {e}")
            return False
    
    def get_channel_info(self) -> Optional[Dict]:
        """Get authenticated channel information"""
        try:
            if not self.service:
                return None
            
            request = self.service.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'thumbnail': channel['snippet']['thumbnails']['default']['url'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', 'N/A'),
                    'video_count': channel['statistics'].get('videoCount', 'N/A'),
                    'view_count': channel['statistics'].get('viewCount', 'N/A')
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting channel info: {e}")
            return None
    
    def create_live_broadcast(self, title: str, description: str, scheduled_start: str, 
                            privacy_status: str = 'unlisted') -> Optional[Dict]:
        """Create a live broadcast"""
        try:
            if not self.service:
                return None
            
            request = self.service.liveBroadcasts().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "scheduledStartTime": scheduled_start
                    },
                    "status": {
                        "privacyStatus": privacy_status
                    }
                }
            )
            response = request.execute()
            return response
            
        except Exception as e:
            st.error(f"Error creating live broadcast: {e}")
            return None
    
    def create_live_stream(self, title: str, resolution: str = "1080p", 
                          frame_rate: str = "30fps") -> Optional[Dict]:
        """Create a live stream to get stream key"""
        try:
            if not self.service:
                return None
            
            stream_request = self.service.liveStreams().insert(
                part="snippet,cdn",
                body={
                    "snippet": {
                        "title": title
                    },
                    "cdn": {
                        "resolution": resolution,
                        "frameRate": frame_rate,
                        "ingestionType": "rtmp"
                    }
                }
            )
            stream_response = stream_request.execute()
            
            return {
                "stream_key": stream_response['cdn']['ingestionInfo']['streamName'],
                "stream_url": stream_response['cdn']['ingestionInfo']['ingestionAddress'],
                "stream_id": stream_response['id']
            }
            
        except Exception as e:
            st.error(f"Error creating live stream: {e}")
            return None
    
    def bind_stream_to_broadcast(self, broadcast_id: str, stream_id: str) -> bool:
        """Bind stream to broadcast"""
        try:
            if not self.service:
                return False
            
            request = self.service.liveBroadcasts().bind(
                part="id,contentDetails",
                id=broadcast_id,
                streamId=stream_id
            )
            response = request.execute()
            return True
            
        except Exception as e:
            st.error(f"Error binding stream to broadcast: {e}")
            return False
    
    def get_live_broadcasts(self, broadcast_status: str = 'upcoming') -> Optional[Dict]:
        """Get live broadcasts"""
        try:
            if not self.service:
                return None
            
            request = self.service.liveBroadcasts().list(
                part="snippet,status",
                mine=True,
                broadcastStatus=broadcast_status
            )
            response = request.execute()
            return response
            
        except Exception as e:
            st.error(f"Error getting live broadcasts: {e}")
            return None
    
    def transition_broadcast(self, broadcast_id: str, broadcast_status: str) -> bool:
        """Transition broadcast status (testing, live, complete)"""
        try:
            if not self.service:
                return False
            
            request = self.service.liveBroadcasts().transition(
                part="snippet,status",
                id=broadcast_id,
                broadcastStatus=broadcast_status
            )
            response = request.execute()
            return True
            
        except Exception as e:
            st.error(f"Error transitioning broadcast: {e}")
            return False
    
    def get_stream_health(self, stream_id: str) -> Optional[Dict]:
        """Get stream health information"""
        try:
            if not self.service:
                return None
            
            request = self.service.liveStreams().list(
                part="status",
                id=stream_id
            )
            response = request.execute()
            
            if response.get('items'):
                stream_status = response['items'][0]['status']
                return {
                    'stream_status': stream_status.get('streamStatus'),
                    'health_status': stream_status.get('healthStatus', {}),
                    'last_error': stream_status.get('healthStatus', {}).get('lastUpdateTimeSeconds')
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting stream health: {e}")
            return None
    
    def get_broadcast_statistics(self, broadcast_id: str) -> Optional[Dict]:
        """Get broadcast statistics"""
        try:
            if not self.service:
                return None
            
            request = self.service.liveBroadcasts().list(
                part="statistics",
                id=broadcast_id
            )
            response = request.execute()
            
            if response.get('items'):
                stats = response['items'][0].get('statistics', {})
                return {
                    'concurrent_viewers': stats.get('concurrentViewers', 0),
                    'total_chat_count': stats.get('totalChatCount', 0)
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting broadcast statistics: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test YouTube API connection"""
        try:
            if not self.service:
                return False
            
            # Simple test request
            request = self.service.channels().list(
                part="snippet",
                mine=True
            )
            response = request.execute()
            return bool(response.get('items'))
            
        except Exception as e:
            st.error(f"YouTube API connection test failed: {e}")
            return False

# Global YouTube service instance
youtube_service = YouTubeService()
