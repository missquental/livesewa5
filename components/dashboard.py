import streamlit as st
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from services.database import get_streaming_sessions, get_stream_metrics
from services.streaming_service import streaming_service
from services.auth_service import auth_service
from utils.logging import get_recent_logs, display_logs_in_streamlit

def render_dashboard():
    """Render the main dashboard"""
    st.title("📊 Live Streaming Dashboard")
    
    # Check authentication
    if not auth_service.is_authenticated():
        st.warning("Please authenticate with a YouTube channel first in the Channel Manager.")
        return
    
    # Dashboard layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_quick_stats()
    
    with col2:
        render_active_streams()
    
    with col3:
        render_system_health()
    
    # Stream monitoring section
    st.markdown("---")
    render_stream_monitoring()
    
    # Recent activity
    st.markdown("---")
    render_recent_activity()
    
    # Auto-refresh
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()

def render_quick_stats():
    """Render quick statistics cards"""
    st.subheader("📈 Quick Stats")
    
    try:
        # Get streaming sessions
        sessions = get_streaming_sessions(limit=100)
        active_sessions = [s for s in sessions if s['status'] == 'active']
        
        # Calculate stats
        total_streams = len(sessions)
        active_streams = len(active_sessions)
        
        # Calculate total streaming time
        total_time = sum(s['duration_seconds'] for s in sessions if s['duration_seconds'])
        total_hours = total_time / 3600
        
        # Get recent sessions (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_sessions = [
            s for s in sessions 
            if datetime.fromisoformat(s['start_time']) > recent_cutoff
        ]
        
        # Display metrics
        st.metric("Total Streams", total_streams)
        st.metric("Active Streams", active_streams)
        st.metric("Total Hours", f"{total_hours:.1f}h")
        st.metric("Recent (24h)", len(recent_sessions))
        
    except Exception as e:
        st.error(f"Error loading quick stats: {e}")

def render_active_streams():
    """Render active streams information"""
    st.subheader("🔴 Active Streams")
    
    try:
        # Get active stream status
        active_streams = streaming_service.get_all_stream_status()
        
        if not active_streams:
            st.info("No active streams")
            return
        
        for session_id, stream_info in active_streams.items():
            if stream_info['status'] in ['active', 'starting']:
                with st.expander(f"Stream: {session_id}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Status:** {stream_info['status']}")
                        st.write(f"**Duration:** {stream_info['duration_seconds']}s")
                        st.write(f"**Video:** {stream_info['video_path']}")
                    
                    with col2:
                        if stream_info['video_info']:
                            info = stream_info['video_info']
                            st.write(f"**Resolution:** {info['width']}x{info['height']}")
                            st.write(f"**FPS:** {info['fps']:.1f}")
                            st.write(f"**Bitrate:** {info['bitrate']} bps")
                    
                    # Stop button
                    if st.button(f"Stop Stream {session_id}", key=f"stop_{session_id}"):
                        streaming_service.stop_stream(session_id)
                        st.rerun()
                        
    except Exception as e:
        st.error(f"Error loading active streams: {e}")

def render_system_health():
    """Render system health information"""
    st.subheader("🏥 System Health")
    
    try:
        # Get system resources
        resources = streaming_service.get_system_resources()
        
        if resources:
            # CPU usage
            cpu_usage = resources.get('cpu_percent', 0)
            st.metric("CPU Usage", f"{cpu_usage:.1f}%")
            
            # Memory usage
            memory_usage = resources.get('memory_percent', 0)
            st.metric("Memory Usage", f"{memory_usage:.1f}%")
            
            # Disk usage
            disk_usage = resources.get('disk_usage', 0)
            st.metric("Disk Usage", f"{disk_usage:.1f}%")
            
            # Health indicators
            st.write("**Health Status:**")
            if cpu_usage > 90:
                st.error("🔴 High CPU usage")
            elif cpu_usage > 70:
                st.warning("🟡 Moderate CPU usage")
            else:
                st.success("🟢 CPU OK")
            
            if memory_usage > 90:
                st.error("🔴 High memory usage")
            elif memory_usage > 70:
                st.warning("🟡 Moderate memory usage")
            else:
                st.success("🟢 Memory OK")
        else:
            st.info("System health data not available")
            
    except Exception as e:
        st.error(f"Error loading system health: {e}")

def render_stream_monitoring():
    """Render stream monitoring charts"""
    st.subheader("📊 Stream Monitoring")
    
    try:
        # Get stream metrics
        metrics = get_stream_metrics(hours=24)
        
        if not metrics:
            st.info("No stream metrics available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(metrics)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create charts
        col1, col2 = st.columns(2)
        
        with col1:
            if 'viewer_count' in df.columns:
                # Viewer count chart
                fig_viewers = px.line(
                    df, 
                    x='timestamp', 
                    y='viewer_count',
                    title='Viewer Count Over Time',
                    labels={'viewer_count': 'Viewers', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_viewers, use_container_width=True)
        
        with col2:
            if 'bitrate' in df.columns:
                # Bitrate chart
                fig_bitrate = px.line(
                    df, 
                    x='timestamp', 
                    y='bitrate',
                    title='Bitrate Over Time',
                    labels={'bitrate': 'Bitrate (bps)', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_bitrate, use_container_width=True)
        
        # Health status distribution
        if 'health_status' in df.columns:
            health_counts = df['health_status'].value_counts()
            fig_health = px.pie(
                values=health_counts.values,
                names=health_counts.index,
                title='Stream Health Status Distribution'
            )
            st.plotly_chart(fig_health, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading stream monitoring: {e}")

def render_recent_activity():
    """Render recent activity logs"""
    st.subheader("📋 Recent Activity")
    
    try:
        # Get recent logs
        logs = get_recent_logs(limit=50)
        
        if not logs:
            st.info("No recent activity")
            return
        
        # Create expandable log viewer
        with st.expander("View Recent Logs", expanded=False):
            # Filter options
            col1, col2 = st.columns(2)
            
            with col1:
                log_levels = ['ALL'] + list(set(log['level'] for log in logs))
                selected_level = st.selectbox("Filter by level", log_levels)
            
            with col2:
                max_logs = st.slider("Max logs to show", 10, 100, 20)
            
            # Filter logs
            filtered_logs = logs
            if selected_level != 'ALL':
                filtered_logs = [log for log in logs if log['level'] == selected_level]
            
            # Display logs
            display_logs_in_streamlit(filtered_logs[:max_logs])
            
    except Exception as e:
        st.error(f"Error loading recent activity: {e}")

def auto_refresh_dashboard():
    """Auto-refresh dashboard data"""
    if st.checkbox("Auto-refresh (30s)", value=False):
        time.sleep(30)
        st.rerun()
