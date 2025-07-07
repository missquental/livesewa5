import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from services.database import save_channel_auth, load_saved_channels, update_channel_last_used
from services.youtube_service import youtube_service

class AuthService:
    """Handles authentication and channel management"""
    
    def __init__(self):
        self.current_channel = None
        self.oauth_config = None
    
    def setup_oauth_config(self, uploaded_file) -> bool:
        """Setup OAuth configuration from uploaded JSON file"""
        try:
            if uploaded_file is not None:
                self.oauth_config = youtube_service.load_oauth_config(uploaded_file)
                if self.oauth_config:
                    st.success("OAuth configuration loaded successfully")
                    return True
                else:
                    st.error("Failed to load OAuth configuration")
                    return False
            return False
        except Exception as e:
            st.error(f"Error setting up OAuth config: {e}")
            return False
    
    def start_oauth_flow(self) -> Optional[str]:
        """Start OAuth authentication flow"""
        try:
            if not self.oauth_config:
                st.error("OAuth configuration not loaded")
                return None
            
            auth_url = youtube_service.generate_auth_url(self.oauth_config)
            return auth_url
            
        except Exception as e:
            st.error(f"Error starting OAuth flow: {e}")
            return None
    
    def complete_oauth_flow(self, auth_code: str) -> bool:
        """Complete OAuth authentication with authorization code"""
        try:
            if not self.oauth_config:
                st.error("OAuth configuration not loaded")
                return False
            
            # Exchange code for tokens
            tokens = youtube_service.exchange_code_for_tokens(self.oauth_config, auth_code)
            if not tokens:
                return False
            
            # Create YouTube service
            if not youtube_service.create_service(tokens):
                return False
            
            # Get channel information
            channel_info = youtube_service.get_channel_info()
            if not channel_info:
                st.error("Failed to get channel information")
                return False
            
            # Save authentication data
            auth_data = {
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'token_uri': self.oauth_config.get('token_uri'),
                'client_id': self.oauth_config.get('client_id'),
                'client_secret': self.oauth_config.get('client_secret'),
                'scopes': youtube_service.scopes
            }
            
            success = save_channel_auth(
                channel_info['title'],
                channel_info['id'],
                auth_data
            )
            
            if success:
                self.current_channel = {
                    'name': channel_info['title'],
                    'id': channel_info['id'],
                    'info': channel_info
                }
                st.success(f"Successfully authenticated channel: {channel_info['title']}")
                return True
            else:
                st.error("Failed to save channel authentication")
                return False
                
        except Exception as e:
            st.error(f"Error completing OAuth flow: {e}")
            return False
    
    def load_saved_channel(self, channel_name: str) -> bool:
        """Load a previously saved channel"""
        try:
            saved_channels = load_saved_channels()
            
            for channel in saved_channels:
                if channel['name'] == channel_name:
                    # Create YouTube service with saved auth
                    if youtube_service.create_service(channel['auth']):
                        # Test connection
                        if youtube_service.test_connection():
                            # Get updated channel info
                            channel_info = youtube_service.get_channel_info()
                            if channel_info:
                                self.current_channel = {
                                    'name': channel_info['title'],
                                    'id': channel_info['id'],
                                    'info': channel_info
                                }
                                
                                # Update last used timestamp
                                update_channel_last_used(channel_name)
                                
                                st.success(f"Loaded channel: {channel_name}")
                                return True
                            else:
                                st.error("Failed to get channel information")
                                return False
                        else:
                            st.error("Authentication expired. Please re-authenticate.")
                            return False
                    else:
                        st.error("Failed to create YouTube service")
                        return False
            
            st.error(f"Channel '{channel_name}' not found")
            return False
            
        except Exception as e:
            st.error(f"Error loading saved channel: {e}")
            return False
    
    def get_saved_channels(self) -> List[Dict]:
        """Get list of saved channels"""
        try:
            return load_saved_channels()
        except Exception as e:
            st.error(f"Error getting saved channels: {e}")
            return []
    
    def get_current_channel(self) -> Optional[Dict]:
        """Get current authenticated channel"""
        return self.current_channel
    
    def logout(self):
        """Logout from current channel"""
        try:
            self.current_channel = None
            youtube_service.service = None
            youtube_service.credentials = None
            st.success("Logged out successfully")
        except Exception as e:
            st.error(f"Error during logout: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.current_channel is not None and youtube_service.service is not None
    
    def refresh_channel_info(self) -> bool:
        """Refresh current channel information"""
        try:
            if not self.is_authenticated():
                return False
            
            channel_info = youtube_service.get_channel_info()
            if channel_info:
                self.current_channel['info'] = channel_info
                return True
            return False
            
        except Exception as e:
            st.error(f"Error refreshing channel info: {e}")
            return False
    
    def delete_saved_channel(self, channel_name: str) -> bool:
        """Delete a saved channel (mark as inactive)"""
        try:
            from services.database import db_manager
            
            query = '''
                UPDATE saved_channels 
                SET is_active = 0
                WHERE channel_name = ?
            '''
            
            result = db_manager.execute_query(query, (channel_name,))
            if result is not None:
                st.success(f"Deleted saved channel: {channel_name}")
                return True
            return False
            
        except Exception as e:
            st.error(f"Error deleting saved channel: {e}")
            return False

# Global auth service instance
auth_service = AuthService()
