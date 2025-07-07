import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import List, Dict, Optional, Tuple

class DatabaseManager:
    """Manages SQLite database operations for the streaming application"""
    
    def __init__(self, db_path: str = "streaming_logs.db"):
        self.db_path = Path(db_path)
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(str(self.db_path))
    
    def execute_query(self, query: str, params: tuple = None):
        """Execute a query with proper error handling"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.fetchall()
        except Exception as e:
            st.error(f"Database error: {e}")
            return None
    
    def execute_insert(self, query: str, params: tuple):
        """Execute insert query and return lastrowid"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            st.error(f"Database insert error: {e}")
            return None

# Global database manager instance
db_manager = DatabaseManager()

def init_database():
    """Initialize SQLite database with all required tables"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS streaming_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    log_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    video_file TEXT,
                    stream_key TEXT,
                    channel_name TEXT,
                    severity TEXT DEFAULT 'INFO'
                )
            ''')
            
            # Create streaming_sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS streaming_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    video_file TEXT,
                    stream_title TEXT,
                    stream_description TEXT,
                    tags TEXT,
                    category TEXT,
                    privacy_status TEXT,
                    made_for_kids BOOLEAN,
                    channel_name TEXT,
                    status TEXT DEFAULT 'active',
                    stream_key TEXT,
                    viewer_count INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0
                )
            ''')
            
            # Create saved_channels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS saved_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT UNIQUE NOT NULL,
                    channel_id TEXT NOT NULL,
                    auth_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create stream_metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stream_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    viewer_count INTEGER,
                    bitrate INTEGER,
                    fps INTEGER,
                    resolution TEXT,
                    health_status TEXT,
                    FOREIGN KEY (session_id) REFERENCES streaming_sessions(session_id)
                )
            ''')
            
            # Create system_config table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False

def test_database_connection():
    """Test database connection and basic operations"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False

def save_channel_auth(channel_name: str, channel_id: str, auth_data: dict) -> bool:
    """Save channel authentication data persistently"""
    try:
        query = '''
            INSERT OR REPLACE INTO saved_channels 
            (channel_name, channel_id, auth_data, created_at, last_used)
            VALUES (?, ?, ?, ?, ?)
        '''
        params = (
            channel_name,
            channel_id,
            json.dumps(auth_data),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        )
        
        result = db_manager.execute_insert(query, params)
        return result is not None
        
    except Exception as e:
        st.error(f"Error saving channel auth: {e}")
        return False

def load_saved_channels() -> List[Dict]:
    """Load saved channel authentication data"""
    try:
        query = '''
            SELECT channel_name, channel_id, auth_data, last_used, is_active
            FROM saved_channels 
            WHERE is_active = 1
            ORDER BY last_used DESC
        '''
        
        rows = db_manager.execute_query(query)
        if rows is None:
            return []
        
        channels = []
        for row in rows:
            channel_name, channel_id, auth_data, last_used, is_active = row
            channels.append({
                'name': channel_name,
                'id': channel_id,
                'auth': json.loads(auth_data),
                'last_used': last_used,
                'is_active': bool(is_active)
            })
        
        return channels
        
    except Exception as e:
        st.error(f"Error loading saved channels: {e}")
        return []

def update_channel_last_used(channel_name: str):
    """Update last used timestamp for a channel"""
    try:
        query = '''
            UPDATE saved_channels 
            SET last_used = ?
            WHERE channel_name = ?
        '''
        params = (datetime.now().isoformat(), channel_name)
        
        db_manager.execute_query(query, params)
        
    except Exception as e:
        st.error(f"Error updating channel last used: {e}")

def log_to_database(session_id: str, log_type: str, message: str, 
                   video_file: str = None, stream_key: str = None, 
                   channel_name: str = None, severity: str = 'INFO'):
    """Log message to database with severity level"""
    try:
        query = '''
            INSERT INTO streaming_logs 
            (timestamp, session_id, log_type, message, video_file, stream_key, channel_name, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            datetime.now().isoformat(),
            session_id,
            log_type,
            message,
            video_file,
            stream_key,
            channel_name,
            severity
        )
        
        db_manager.execute_insert(query, params)
        
    except Exception as e:
        st.error(f"Error logging to database: {e}")

def get_logs_from_database(session_id: str = None, limit: int = 100) -> List[Tuple]:
    """Get logs from database with optional session filtering"""
    try:
        if session_id:
            query = '''
                SELECT timestamp, log_type, message, video_file, channel_name, severity
                FROM streaming_logs 
                WHERE session_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            params = (session_id, limit)
        else:
            query = '''
                SELECT timestamp, log_type, message, video_file, channel_name, severity
                FROM streaming_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            params = (limit,)
        
        rows = db_manager.execute_query(query, params)
        return rows if rows else []
        
    except Exception as e:
        st.error(f"Error getting logs from database: {e}")
        return []

def save_streaming_session(session_id: str, video_file: str, stream_title: str, 
                          stream_description: str, tags: str, category: str, 
                          privacy_status: str, made_for_kids: bool, channel_name: str,
                          stream_key: str = None):
    """Save streaming session to database"""
    try:
        query = '''
            INSERT OR REPLACE INTO streaming_sessions 
            (session_id, start_time, video_file, stream_title, stream_description, 
             tags, category, privacy_status, made_for_kids, channel_name, stream_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            session_id,
            datetime.now().isoformat(),
            video_file,
            stream_title,
            stream_description,
            tags,
            category,
            privacy_status,
            made_for_kids,
            channel_name,
            stream_key
        )
        
        db_manager.execute_insert(query, params)
        
    except Exception as e:
        st.error(f"Error saving streaming session: {e}")

def get_streaming_sessions(active_only: bool = False, limit: int = 50) -> List[Dict]:
    """Get streaming sessions from database"""
    try:
        if active_only:
            query = '''
                SELECT session_id, start_time, end_time, video_file, stream_title, 
                       channel_name, status, viewer_count, duration_seconds
                FROM streaming_sessions 
                WHERE status = 'active' OR end_time IS NULL
                ORDER BY start_time DESC 
                LIMIT ?
            '''
        else:
            query = '''
                SELECT session_id, start_time, end_time, video_file, stream_title, 
                       channel_name, status, viewer_count, duration_seconds
                FROM streaming_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            '''
        
        rows = db_manager.execute_query(query, (limit,))
        if not rows:
            return []
        
        sessions = []
        for row in rows:
            sessions.append({
                'session_id': row[0],
                'start_time': row[1],
                'end_time': row[2],
                'video_file': row[3],
                'stream_title': row[4],
                'channel_name': row[5],
                'status': row[6],
                'viewer_count': row[7] or 0,
                'duration_seconds': row[8] or 0
            })
        
        return sessions
        
    except Exception as e:
        st.error(f"Error getting streaming sessions: {e}")
        return []

def save_stream_metrics(session_id: str, viewer_count: int, bitrate: int, 
                       fps: int, resolution: str, health_status: str):
    """Save stream metrics for analytics"""
    try:
        query = '''
            INSERT INTO stream_metrics 
            (session_id, timestamp, viewer_count, bitrate, fps, resolution, health_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            session_id,
            datetime.now().isoformat(),
            viewer_count,
            bitrate,
            fps,
            resolution,
            health_status
        )
        
        db_manager.execute_insert(query, params)
        
    except Exception as e:
        st.error(f"Error saving stream metrics: {e}")

def get_stream_metrics(session_id: str = None, hours: int = 24) -> List[Dict]:
    """Get stream metrics for analytics"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if session_id:
            query = '''
                SELECT timestamp, viewer_count, bitrate, fps, resolution, health_status
                FROM stream_metrics 
                WHERE session_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
            '''
            params = (session_id, cutoff_time.isoformat())
        else:
            query = '''
                SELECT timestamp, viewer_count, bitrate, fps, resolution, health_status
                FROM stream_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            '''
            params = (cutoff_time.isoformat(),)
        
        rows = db_manager.execute_query(query, params)
        if not rows:
            return []
        
        metrics = []
        for row in rows:
            metrics.append({
                'timestamp': row[0],
                'viewer_count': row[1],
                'bitrate': row[2],
                'fps': row[3],
                'resolution': row[4],
                'health_status': row[5]
            })
        
        return metrics
        
    except Exception as e:
        st.error(f"Error getting stream metrics: {e}")
        return []
