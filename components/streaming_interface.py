import streamlit as st
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from services.streaming_service import streaming_service
from services.youtube_service import youtube_service
from services.auth_service import auth_service
from services.database import save_streaming_session, log_to_database
from utils.logging import log_stream_event

def render_streaming_interface():
    """Render the live streaming interface"""
    st.title("🔴 Live Streaming Interface")
    
    # Check authentication
    if not auth_service.is_authenticated():
        st.warning("Please authenticate with a YouTube channel first in the Channel Manager.")
        return
    
    # Check FFmpeg installation
    if not streaming_service.check_ffmpeg_installation():
        st.error("FFmpeg is not installed or not accessible. Please install FFmpeg to use streaming features.")
        return
    
    # Main streaming interface
    render_stream_setup()
    
    # Stream management
    st.markdown("---")
    render_stream_management()
    
    # Stream monitoring
    st.markdown("---")
    render_stream_monitoring()

def render_stream_setup():
    """Render stream setup interface"""
    st.subheader("🎬 Stream Setup")
    
    with st.form("stream_setup_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Video Settings**")
            
            # Video file upload
            video_file = st.file_uploader(
                "Upload video file",
                type=['mp4', 'avi', 'mkv', 'mov', 'wmv'],
                help="Select the video file to stream"
            )
            
            # Or video file path
            video_path = st.text_input(
                "Or enter video file path",
                help="Full path to the video file on the server"
            )
            
            # Stream quality settings
            resolution = st.selectbox(
                "Stream Resolution",
                ["1080p", "720p", "480p", "360p"],
                index=0
            )
            
            framerate = st.selectbox(
                "Frame Rate",
                ["30fps", "60fps", "24fps"],
                index=0
            )
            
            bitrate = st.selectbox(
                "Bitrate",
                ["3000k", "2500k", "2000k", "1500k", "1000k"],
                index=0
            )
        
        with col2:
            st.write("**YouTube Settings**")
            
            # Stream title
            stream_title = st.text_input(
                "Stream Title",
                value=f"Live Stream - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                help="Title for your YouTube live stream"
            )
            
            # Stream description
            stream_description = st.text_area(
                "Stream Description",
                value="Live stream via YouTube Live Streaming Studio",
                height=100,
                help="Description for your YouTube live stream"
            )
            
            # Privacy settings
            privacy_status = st.selectbox(
                "Privacy Status",
                ["unlisted", "private", "public"],
                index=0,
                help="Who can view your stream"
            )
            
            # Stream category
            category = st.selectbox(
                "Category",
                ["Gaming", "Music", "Entertainment", "Education", "News & Politics", "Other"],
                index=0
            )
            
            # Made for kids
            made_for_kids = st.checkbox(
                "Made for Kids",
                value=False,
                help="Check if this content is made for kids"
            )
            
            # Tags
            tags = st.text_input(
                "Tags (comma-separated)",
                help="Tags to help people find your stream"
            )
        
        # Submit button
        submit_button = st.form_submit_button("🚀 Start Stream", use_container_width=True)
        
        if submit_button:
            start_stream(
                video_file=video_file,
                video_path=video_path,
                stream_title=stream_title,
                stream_description=stream_description,
                privacy_status=privacy_status,
                category=category,
                made_for_kids=made_for_kids,
                tags=tags,
                resolution=resolution,
                framerate=framerate,
                bitrate=bitrate
            )

def start_stream(video_file, video_path, stream_title, stream_description, 
                privacy_status, category, made_for_kids, tags, resolution, 
                framerate, bitrate):
    """Start a new live stream"""
    try:
        # Validate inputs
        if not video_file and not video_path:
            st.error("Please provide either a video file or video path")
            return
        
        if not stream_title:
            st.error("Please provide a stream title")
            return
        
        # Determine video file path
        if video_file:
            # Save uploaded file
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_path = upload_dir / video_file.name
            with open(file_path, "wb") as f:
                f.write(video_file.getbuffer())
            
            final_video_path = str(file_path)
        else:
            final_video_path = video_path
        
        # Validate video file exists
        if not os.path.exists(final_video_path):
            st.error(f"Video file not found: {final_video_path}")
            return
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create YouTube live stream
        st.info("Creating YouTube live stream...")
        
        # Create live stream to get stream key
        stream_info = youtube_service.create_live_stream(
            title=f"Stream Key - {stream_title}",
            resolution=resolution,
            frame_rate=framerate
        )
        
        if not stream_info:
            st.error("Failed to create YouTube live stream")
            return
        
        # Create live broadcast
        scheduled_start = (datetime.now() + timedelta(minutes=1)).isoformat() + "Z"
        broadcast_info = youtube_service.create_live_broadcast(
            title=stream_title,
            description=stream_description,
            scheduled_start=scheduled_start,
            privacy_status=privacy_status
        )
        
        if not broadcast_info:
            st.error("Failed to create YouTube live broadcast")
            return
        
        # Bind stream to broadcast
        bind_success = youtube_service.bind_stream_to_broadcast(
            broadcast_info['id'],
            stream_info['stream_id']
        )
        
        if not bind_success:
            st.error("Failed to bind stream to broadcast")
            return
        
        # Save streaming session
        save_streaming_session(
            session_id=session_id,
            video_file=final_video_path,
            stream_title=stream_title,
            stream_description=stream_description,
            tags=tags,
            category=category,
            privacy_status=privacy_status,
            made_for_kids=made_for_kids,
            channel_name=auth_service.get_current_channel()['name'],
            stream_key=stream_info['stream_key']
        )
        
        # Start FFmpeg streaming
        st.info("Starting FFmpeg streaming process...")
        
        def stream_callback(session_id, status, message):
            """Callback for stream status updates"""
            log_stream_event(session_id, status, message)
        
        success = streaming_service.start_stream(
            session_id=session_id,
            video_path=final_video_path,
            stream_url=stream_info['stream_url'],
            stream_key=stream_info['stream_key'],
            callback=stream_callback
        )
        
        if success:
            st.success(f"Stream started successfully! Session ID: {session_id}")
            
            # Display stream information
            st.info(f"**YouTube Stream URL:** https://www.youtube.com/watch?v={broadcast_info['id']}")
            st.info(f"**Stream Key:** {stream_info['stream_key'][:10]}...")
            
            # Log success
            log_stream_event(
                session_id=session_id,
                event_type="stream_started",
                message=f"Stream started for video: {final_video_path}",
                level="INFO"
            )
            
        else:
            st.error("Failed to start FFmpeg streaming")
            
    except Exception as e:
        st.error(f"Error starting stream: {e}")
        log_stream_event(
            session_id=session_id if 'session_id' in locals() else 'unknown',
            event_type="stream_error",
            message=f"Error starting stream: {e}",
            level="ERROR"
        )

def render_stream_management():
    """Render stream management interface"""
    st.subheader("📺 Stream Management")
    
    # Get active streams
    active_streams = streaming_service.get_all_stream_status()
    
    if not active_streams:
        st.info("No active streams")
        return
    
    # Display active streams
    for session_id, stream_info in active_streams.items():
        with st.expander(f"Stream: {session_id}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Status:** {stream_info['status']}")
                st.write(f"**Duration:** {stream_info['duration_seconds']}s")
                st.write(f"**Video:** {Path(stream_info['video_path']).name}")
            
            with col2:
                if stream_info.get('video_info'):
                    info = stream_info['video_info']
                    st.write(f"**Resolution:** {info['width']}x{info['height']}")
                    st.write(f"**FPS:** {info['fps']:.1f}")
                    st.write(f"**Bitrate:** {info['bitrate']} bps")
            
            with col3:
                # Control buttons
                if st.button(f"Stop Stream", key=f"stop_{session_id}"):
                    stop_stream(session_id)
                
                if st.button(f"Get Stream Health", key=f"health_{session_id}"):
                    get_stream_health(session_id)

def stop_stream(session_id):
    """Stop a streaming session"""
    try:
        success = streaming_service.stop_stream(session_id)
        if success:
            st.success(f"Stream {session_id} stopped successfully")
            log_stream_event(
                session_id=session_id,
                event_type="stream_stopped",
                message="Stream stopped by user",
                level="INFO"
            )
        else:
            st.error(f"Failed to stop stream {session_id}")
            
    except Exception as e:
        st.error(f"Error stopping stream: {e}")
        log_stream_event(
            session_id=session_id,
            event_type="stream_error",
            message=f"Error stopping stream: {e}",
            level="ERROR"
        )

def get_stream_health(session_id):
    """Get and display stream health information"""
    try:
        # This would need to be implemented with YouTube API
        st.info("Stream health check feature coming soon...")
        
    except Exception as e:
        st.error(f"Error getting stream health: {e}")

def render_stream_monitoring():
    """Render stream monitoring section"""
    st.subheader("📊 Stream Monitoring")
    
    # Get active streams
    active_streams = streaming_service.get_all_stream_status()
    
    if not active_streams:
        st.info("No active streams to monitor")
        return
    
    # Select stream to monitor
    stream_options = list(active_streams.keys())
    selected_stream = st.selectbox("Select stream to monitor", stream_options)
    
    if selected_stream:
        stream_info = active_streams[selected_stream]
        
        # Display monitoring information
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Status", stream_info['status'])
            st.metric("Duration", f"{stream_info['duration_seconds']}s")
            
        with col2:
            if stream_info.get('video_info'):
                info = stream_info['video_info']
                st.metric("Resolution", f"{info['width']}x{info['height']}")
                st.metric("FPS", f"{info['fps']:.1f}")
        
        # Real-time monitoring (placeholder)
        if st.button("Start Real-time Monitoring"):
            st.info("Real-time monitoring feature coming soon...")
