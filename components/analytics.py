import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from services.database import get_streaming_sessions, get_stream_metrics, get_logs_from_database
from services.auth_service import auth_service

def render_analytics():
    """Render analytics dashboard"""
    st.title("📈 Stream Analytics")
    
    # Check authentication
    if not auth_service.is_authenticated():
        st.warning("Please authenticate with a YouTube channel first.")
        return
    
    # Time range selector
    render_time_range_selector()
    
    # Analytics sections
    render_streaming_overview()
    
    st.markdown("---")
    render_performance_metrics()
    
    st.markdown("---")
    render_stream_history()
    
    st.markdown("---")
    render_system_analytics()

def render_time_range_selector():
    """Render time range selection"""
    st.subheader("📅 Time Range")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        time_range = st.selectbox(
            "Select Time Range",
            ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days", "All time"]
        )
    
    with col2:
        start_date = st.date_input(
            "Custom Start Date",
            value=datetime.now() - timedelta(days=30)
        )
    
    with col3:
        end_date = st.date_input(
            "Custom End Date",
            value=datetime.now()
        )
    
    # Store selection in session state
    if 'analytics_time_range' not in st.session_state:
        st.session_state.analytics_time_range = time_range
    
    if st.button("Apply Time Range"):
        st.session_state.analytics_time_range = time_range
        st.rerun()

def get_time_range_filter():
    """Get datetime filter based on selected time range"""
    time_range = st.session_state.get('analytics_time_range', 'Last 24 hours')
    
    if time_range == "Last 24 hours":
        return datetime.now() - timedelta(hours=24)
    elif time_range == "Last 7 days":
        return datetime.now() - timedelta(days=7)
    elif time_range == "Last 30 days":
        return datetime.now() - timedelta(days=30)
    elif time_range == "Last 90 days":
        return datetime.now() - timedelta(days=90)
    else:  # All time
        return datetime.min

def render_streaming_overview():
    """Render streaming overview statistics"""
    st.subheader("📊 Streaming Overview")
    
    try:
        # Get streaming sessions
        sessions = get_streaming_sessions(limit=1000)
        
        if not sessions:
            st.info("No streaming sessions found")
            return
        
        # Filter by time range
        cutoff_time = get_time_range_filter()
        filtered_sessions = [
            s for s in sessions
            if datetime.fromisoformat(s['start_time']) >= cutoff_time
        ]
        
        # Calculate metrics
        total_streams = len(filtered_sessions)
        total_duration = sum(s['duration_seconds'] for s in filtered_sessions if s['duration_seconds'])
        avg_duration = total_duration / total_streams if total_streams > 0 else 0
        total_viewers = sum(s['viewer_count'] for s in filtered_sessions if s['viewer_count'])
        
        # Active vs completed streams
        active_streams = len([s for s in filtered_sessions if s['status'] == 'active'])
        completed_streams = len([s for s in filtered_sessions if s['status'] == 'completed'])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Streams", total_streams)
            st.metric("Active Streams", active_streams)
        
        with col2:
            st.metric("Total Duration", f"{total_duration/3600:.1f} hours")
            st.metric("Avg Duration", f"{avg_duration/60:.1f} minutes")
        
        with col3:
            st.metric("Total Viewers", total_viewers)
            st.metric("Avg Viewers", f"{total_viewers/total_streams:.1f}" if total_streams > 0 else "0")
        
        with col4:
            st.metric("Completed Streams", completed_streams)
            success_rate = (completed_streams / total_streams * 100) if total_streams > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Streams over time chart
        if filtered_sessions:
            df = pd.DataFrame(filtered_sessions)
            df['start_time'] = pd.to_datetime(df['start_time'])
            df['date'] = df['start_time'].dt.date
            
            daily_streams = df.groupby('date').size().reset_index()
            daily_streams.columns = ['date', 'stream_count']
            
            fig_timeline = px.line(
                daily_streams,
                x='date',
                y='stream_count',
                title='Streams Over Time',
                labels={'stream_count': 'Number of Streams', 'date': 'Date'}
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading streaming overview: {e}")

def render_performance_metrics():
    """Render performance metrics and charts"""
    st.subheader("⚡ Performance Metrics")
    
    try:
        # Get stream metrics
        hours_back = 24
        time_range = st.session_state.get('analytics_time_range', 'Last 24 hours')
        
        if time_range == "Last 7 days":
            hours_back = 24 * 7
        elif time_range == "Last 30 days":
            hours_back = 24 * 30
        elif time_range == "Last 90 days":
            hours_back = 24 * 90
        elif time_range == "All time":
            hours_back = 24 * 365  # Limit to 1 year for performance
        
        metrics = get_stream_metrics(hours=hours_back)
        
        if not metrics:
            st.info("No performance metrics available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(metrics)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Performance charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Viewer count over time
            if 'viewer_count' in df.columns:
                fig_viewers = px.line(
                    df,
                    x='timestamp',
                    y='viewer_count',
                    title='Viewer Count Over Time',
                    labels={'viewer_count': 'Concurrent Viewers', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_viewers, use_container_width=True)
            
            # Bitrate over time
            if 'bitrate' in df.columns:
                fig_bitrate = px.line(
                    df,
                    x='timestamp',
                    y='bitrate',
                    title='Bitrate Over Time',
                    labels={'bitrate': 'Bitrate (bps)', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_bitrate, use_container_width=True)
        
        with col2:
            # FPS over time
            if 'fps' in df.columns:
                fig_fps = px.line(
                    df,
                    x='timestamp',
                    y='fps',
                    title='Frame Rate Over Time',
                    labels={'fps': 'FPS', 'timestamp': 'Time'}
                )
                st.plotly_chart(fig_fps, use_container_width=True)
            
            # Health status distribution
            if 'health_status' in df.columns:
                health_counts = df['health_status'].value_counts()
                fig_health = px.pie(
                    values=health_counts.values,
                    names=health_counts.index,
                    title='Stream Health Distribution'
                )
                st.plotly_chart(fig_health, use_container_width=True)
        
        # Performance summary
        st.write("**Performance Summary**")
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            if 'viewer_count' in df.columns:
                st.metric("Peak Viewers", df['viewer_count'].max())
                st.metric("Avg Viewers", f"{df['viewer_count'].mean():.1f}")
        
        with summary_col2:
            if 'bitrate' in df.columns:
                st.metric("Peak Bitrate", f"{df['bitrate'].max():,} bps")
                st.metric("Avg Bitrate", f"{df['bitrate'].mean():,.0f} bps")
        
        with summary_col3:
            if 'fps' in df.columns:
                st.metric("Peak FPS", f"{df['fps'].max():.1f}")
                st.metric("Avg FPS", f"{df['fps'].mean():.1f}")
        
    except Exception as e:
        st.error(f"Error loading performance metrics: {e}")

def render_stream_history():
    """Render stream history table"""
    st.subheader("📋 Stream History")
    
    try:
        # Get streaming sessions
        sessions = get_streaming_sessions(limit=100)
        
        if not sessions:
            st.info("No stream history available")
            return
        
        # Filter by time range
        cutoff_time = get_time_range_filter()
        filtered_sessions = [
            s for s in sessions
            if datetime.fromisoformat(s['start_time']) >= cutoff_time
        ]
        
        if not filtered_sessions:
            st.info("No streams found in selected time range")
            return
        
        # Convert to DataFrame for display
        df = pd.DataFrame(filtered_sessions)
        
        # Format columns
        df['start_time'] = pd.to_datetime(df['start_time']).dt.strftime('%Y-%m-%d %H:%M')
        df['duration'] = df['duration_seconds'].apply(lambda x: f"{x//3600:02d}:{(x%3600)//60:02d}:{x%60:02d}" if x else "00:00:00")
        
        # Select columns to display
        display_columns = ['start_time', 'stream_title', 'channel_name', 'status', 'duration', 'viewer_count']
        available_columns = [col for col in display_columns if col in df.columns]
        
        # Display table
        st.dataframe(
            df[available_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Stream details
        if st.checkbox("Show detailed stream information"):
            selected_session = st.selectbox(
                "Select session for details",
                df['session_id'].tolist() if 'session_id' in df.columns else []
            )
            
            if selected_session:
                render_stream_details(selected_session)
        
    except Exception as e:
        st.error(f"Error loading stream history: {e}")

def render_stream_details(session_id):
    """Render detailed information for a specific stream"""
    try:
        # Get session logs
        logs = get_logs_from_database(session_id=session_id, limit=50)
        
        if not logs:
            st.info("No logs found for this session")
            return
        
        st.write(f"**Stream Logs for {session_id}:**")
        
        # Display logs
        for log in logs:
            timestamp, log_type, message, video_file, channel_name, severity = log
            
            # Format timestamp
            log_time = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
            
            # Color code by severity
            if severity == 'ERROR':
                st.error(f"**{log_time}** [{log_type}] {message}")
            elif severity == 'WARNING':
                st.warning(f"**{log_time}** [{log_type}] {message}")
            else:
                st.info(f"**{log_time}** [{log_type}] {message}")
        
    except Exception as e:
        st.error(f"Error loading stream details: {e}")

def render_system_analytics():
    """Render system-wide analytics"""
    st.subheader("🖥️ System Analytics")
    
    try:
        # Get system logs
        logs = get_logs_from_database(limit=200)
        
        if not logs:
            st.info("No system logs available")
            return
        
        # Process logs for analytics
        df_logs = pd.DataFrame(logs, columns=['timestamp', 'log_type', 'message', 'video_file', 'channel_name', 'severity'])
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
        
        # Log type distribution
        col1, col2 = st.columns(2)
        
        with col1:
            log_type_counts = df_logs['log_type'].value_counts()
            fig_log_types = px.bar(
                x=log_type_counts.index,
                y=log_type_counts.values,
                title='Log Types Distribution',
                labels={'x': 'Log Type', 'y': 'Count'}
            )
            st.plotly_chart(fig_log_types, use_container_width=True)
        
        with col2:
            severity_counts = df_logs['severity'].value_counts()
            fig_severity = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                title='Log Severity Distribution'
            )
            st.plotly_chart(fig_severity, use_container_width=True)
        
        # Recent errors
        st.write("**Recent Errors:**")
        recent_errors = df_logs[df_logs['severity'] == 'ERROR'].tail(10)
        
        if not recent_errors.empty:
            for _, error in recent_errors.iterrows():
                st.error(f"**{error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}** - {error['message']}")
        else:
            st.success("No recent errors found")
        
        # System health indicators
        st.write("**System Health Indicators:**")
        
        # Calculate error rate
        total_logs = len(df_logs)
        error_logs = len(df_logs[df_logs['severity'] == 'ERROR'])
        error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
        
        health_col1, health_col2, health_col3 = st.columns(3)
        
        with health_col1:
            st.metric("Total Log Entries", total_logs)
            st.metric("Error Rate", f"{error_rate:.2f}%")
        
        with health_col2:
            warning_logs = len(df_logs[df_logs['severity'] == 'WARNING'])
            st.metric("Warning Count", warning_logs)
            st.metric("Info Count", len(df_logs[df_logs['severity'] == 'INFO']))
        
        with health_col3:
            # Calculate uptime (placeholder)
            st.metric("System Uptime", "99.9%")
            st.metric("Active Channels", len(df_logs['channel_name'].unique()))
        
    except Exception as e:
        st.error(f"Error loading system analytics: {e}")
