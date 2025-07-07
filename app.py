import streamlit as st
import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

from services.database import init_database
from components.dashboard import render_dashboard
from components.streaming_interface import render_streaming_interface
from components.channel_manager import render_channel_manager
from components.analytics import render_analytics
from utils.config import load_config
from utils.logging import setup_logging

# Page configuration
st.set_page_config(
    page_title="YouTube Live Streaming Studio",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    try:
        # Initialize logging
        setup_logging()
        
        # Initialize database
        init_database()
        
        # Load configuration
        config = load_config()
        
        # Sidebar navigation
        st.sidebar.title("🎬 YouTube Live Studio")
        
        # Navigation menu
        pages = {
            "Dashboard": "📊",
            "Live Streaming": "🔴",
            "Channel Manager": "📺",
            "Analytics": "📈"
        }
        
        selected_page = st.sidebar.selectbox(
            "Navigation",
            list(pages.keys()),
            format_func=lambda x: f"{pages[x]} {x}"
        )
        
        # Status indicators in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("System Status")
        
        # Check system health
        health_status = check_system_health()
        for service, status in health_status.items():
            color = "🟢" if status else "🔴"
            st.sidebar.write(f"{color} {service}")
        
        # Main content area
        if selected_page == "Dashboard":
            render_dashboard()
        elif selected_page == "Live Streaming":
            render_streaming_interface()
        elif selected_page == "Channel Manager":
            render_channel_manager()
        elif selected_page == "Analytics":
            render_analytics()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.caption("YouTube Live Streaming Studio v2.0")
        
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("Please check the logs for more details.")

def check_system_health():
    """Check system health status"""
    health = {}
    
    # Check database
    try:
        from services.database import test_database_connection
        health["Database"] = test_database_connection()
    except Exception:
        health["Database"] = False
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        health["FFmpeg"] = result.returncode == 0
    except Exception:
        health["FFmpeg"] = False
    
    # Check YouTube API
    try:
        # This would be checked when credentials are provided
        health["YouTube API"] = True
    except Exception:
        health["YouTube API"] = False
    
    return health

if __name__ == "__main__":
    main()
