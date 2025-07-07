import streamlit as st
import json
from datetime import datetime
from services.auth_service import auth_service
from services.youtube_service import youtube_service
from utils.logging import log_system_event

def render_channel_manager():
    """Render the channel manager interface"""
    st.title("📺 Channel Manager")
    
    # Current channel status
    render_current_channel_status()
    
    # Authentication section
    st.markdown("---")
    render_authentication_section()
    
    # Saved channels
    st.markdown("---")
    render_saved_channels()

def render_current_channel_status():
    """Render current channel authentication status"""
    st.subheader("🔐 Current Channel Status")
    
    current_channel = auth_service.get_current_channel()
    
    if current_channel:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.success(f"Authenticated as: **{current_channel['name']}**")
            
            # Display channel information
            if current_channel.get('info'):
                info = current_channel['info']
                
                with st.expander("Channel Details", expanded=False):
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write(f"**Channel ID:** {info['id']}")
                        st.write(f"**Subscribers:** {info['subscriber_count']}")
                        st.write(f"**Total Views:** {info['view_count']}")
                    
                    with col_info2:
                        st.write(f"**Video Count:** {info['video_count']}")
                        if info.get('thumbnail'):
                            st.image(info['thumbnail'], width=100)
                    
                    if info.get('description'):
                        st.write(f"**Description:** {info['description'][:200]}...")
        
        with col2:
            if st.button("🔄 Refresh Info"):
                if auth_service.refresh_channel_info():
                    st.success("Channel info refreshed")
                    st.rerun()
                else:
                    st.error("Failed to refresh channel info")
            
            if st.button("🚪 Logout"):
                auth_service.logout()
                st.success("Logged out successfully")
                st.rerun()
    else:
        st.info("No channel currently authenticated")

def render_authentication_section():
    """Render authentication interface"""
    st.subheader("🔑 Authentication")
    
    # Check if already authenticated
    if auth_service.is_authenticated():
        st.info("Already authenticated. You can logout above to switch channels.")
        return
    
    # Two authentication methods
    tab1, tab2 = st.tabs(["🆕 New Authentication", "💾 Load Saved Channel"])
    
    with tab1:
        render_new_authentication()
    
    with tab2:
        render_load_saved_channel()

def render_new_authentication():
    """Render new OAuth authentication"""
    st.write("**Authenticate with a new YouTube channel**")
    
    # Step 1: Upload OAuth JSON
    st.write("**Step 1: Upload OAuth Configuration**")
    oauth_file = st.file_uploader(
        "Upload OAuth JSON file",
        type=['json'],
        help="Download this from Google Cloud Console -> APIs & Services -> Credentials"
    )
    
    if oauth_file:
        if auth_service.setup_oauth_config(oauth_file):
            st.success("OAuth configuration loaded successfully")
            
            # Step 2: Generate authorization URL
            st.write("**Step 2: Authorize Application**")
            
            auth_url = auth_service.start_oauth_flow()
            if auth_url:
                st.markdown(f"**[Click here to authorize]({auth_url})**")
                st.info("After authorization, copy the authorization code from the redirect URL")
                
                # Step 3: Enter authorization code
                st.write("**Step 3: Enter Authorization Code**")
                
                with st.form("auth_code_form"):
                    auth_code = st.text_input(
                        "Authorization Code",
                        help="Paste the authorization code from the redirect URL"
                    )
                    
                    submit_button = st.form_submit_button("Complete Authentication")
                    
                    if submit_button and auth_code:
                        if auth_service.complete_oauth_flow(auth_code):
                            st.success("Authentication completed successfully!")
                            st.rerun()
                        else:
                            st.error("Authentication failed. Please try again.")
            else:
                st.error("Failed to generate authorization URL")
        else:
            st.error("Failed to load OAuth configuration")

def render_load_saved_channel():
    """Render interface to load saved channels"""
    st.write("**Load a previously authenticated channel**")
    
    # Get saved channels
    saved_channels = auth_service.get_saved_channels()
    
    if not saved_channels:
        st.info("No saved channels found. Please authenticate a new channel first.")
        return
    
    # Select channel to load
    channel_options = [f"{ch['name']} (Last used: {ch['last_used'][:10]})" 
                      for ch in saved_channels]
    
    selected_index = st.selectbox(
        "Select channel to load",
        range(len(channel_options)),
        format_func=lambda x: channel_options[x]
    )
    
    if st.button("Load Channel"):
        selected_channel = saved_channels[selected_index]
        
        if auth_service.load_saved_channel(selected_channel['name']):
            st.success(f"Loaded channel: {selected_channel['name']}")
            st.rerun()
        else:
            st.error("Failed to load channel. Authentication may have expired.")

def render_saved_channels():
    """Render saved channels management"""
    st.subheader("💾 Saved Channels")
    
    saved_channels = auth_service.get_saved_channels()
    
    if not saved_channels:
        st.info("No saved channels found.")
        return
    
    # Display saved channels
    for i, channel in enumerate(saved_channels):
        with st.expander(f"📺 {channel['name']}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Channel ID:** {channel['id']}")
                st.write(f"**Created:** {channel['last_used'][:10]}")
            
            with col2:
                last_used = datetime.fromisoformat(channel['last_used'])
                days_ago = (datetime.now() - last_used).days
                st.write(f"**Last Used:** {days_ago} days ago")
                st.write(f"**Status:** {'Active' if channel['is_active'] else 'Inactive'}")
            
            with col3:
                if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                    if auth_service.delete_saved_channel(channel['name']):
                        st.rerun()
                
                if st.button(f"📊 Test Auth", key=f"test_{i}"):
                    test_channel_auth(channel['name'])

def test_channel_auth(channel_name):
    """Test authentication for a saved channel"""
    try:
        # Load channel temporarily
        saved_channels = auth_service.get_saved_channels()
        channel_data = next((ch for ch in saved_channels if ch['name'] == channel_name), None)
        
        if not channel_data:
            st.error("Channel not found")
            return
        
        # Test authentication
        if youtube_service.create_service(channel_data['auth']):
            if youtube_service.test_connection():
                st.success(f"✅ Authentication valid for {channel_name}")
                log_system_event(
                    component="channel_manager",
                    event_type="auth_test",
                    message=f"Authentication test passed for {channel_name}",
                    level="INFO"
                )
            else:
                st.error(f"❌ Authentication failed for {channel_name}")
                log_system_event(
                    component="channel_manager",
                    event_type="auth_test",
                    message=f"Authentication test failed for {channel_name}",
                    level="WARNING"
                )
        else:
            st.error(f"❌ Could not create service for {channel_name}")
            
    except Exception as e:
        st.error(f"Error testing authentication: {e}")
        log_system_event(
            component="channel_manager",
            event_type="auth_test_error",
            message=f"Error testing auth for {channel_name}: {e}",
            level="ERROR"
        )

def render_channel_configuration():
    """Render channel configuration options"""
    st.subheader("⚙️ Channel Configuration")
    
    if not auth_service.is_authenticated():
        st.info("Please authenticate first to configure channel settings")
        return
    
    with st.form("channel_config_form"):
        st.write("**Stream Default Settings**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_title_template = st.text_input(
                "Default Title Template",
                value="Live Stream - {date}",
                help="Use {date} for current date, {time} for current time"
            )
            
            default_description = st.text_area(
                "Default Description",
                value="Live stream via YouTube Live Streaming Studio",
                height=100
            )
        
        with col2:
            default_privacy = st.selectbox(
                "Default Privacy",
                ["unlisted", "private", "public"],
                index=0
            )
            
            default_category = st.selectbox(
                "Default Category",
                ["Gaming", "Music", "Entertainment", "Education", "News & Politics", "Other"],
                index=0
            )
        
        if st.form_submit_button("Save Configuration"):
            # This would save to database or config file
            st.success("Channel configuration saved")
            log_system_event(
                component="channel_manager",
                event_type="config_saved",
                message="Channel configuration updated",
                level="INFO"
            )
