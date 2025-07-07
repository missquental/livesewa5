import logging
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import Optional

class StreamlitLogHandler(logging.Handler):
    """Custom logging handler for Streamlit"""
    
    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_logs = 1000
    
    def emit(self, record):
        """Emit a log record"""
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            self.logs.append(log_entry)
            
            # Keep only the last max_logs entries
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
                
        except Exception:
            self.handleError(record)
    
    def get_logs(self, level: str = None, limit: int = 100):
        """Get recent logs with optional filtering"""
        logs = self.logs
        
        if level:
            logs = [log for log in logs if log['level'] == level]
        
        return logs[-limit:]

# Global log handler
streamlit_handler = StreamlitLogHandler()

def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    try:
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add Streamlit handler
        streamlit_handler.setLevel(getattr(logging, level.upper()))
        streamlit_handler.setFormatter(formatter)
        logger.addHandler(streamlit_handler)
        
        # Add file handler if specified
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        logging.info("Logging system initialized")
        
    except Exception as e:
        st.error(f"Error setting up logging: {e}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)

def log_stream_event(session_id: str, event_type: str, message: str, 
                    level: str = "INFO", **kwargs):
    """Log a streaming event"""
    try:
        logger = get_logger("streaming")
        
        # Add session context
        extra_info = f"[{session_id}] {message}"
        if kwargs:
            extra_info += f" - {kwargs}"
        
        log_level = getattr(logging, level.upper())
        logger.log(log_level, extra_info)
        
        # Also log to database
        from services.database import log_to_database
        log_to_database(
            session_id=session_id,
            log_type=event_type,
            message=message,
            severity=level,
            **kwargs
        )
        
    except Exception as e:
        st.error(f"Error logging stream event: {e}")

def log_system_event(component: str, event_type: str, message: str, 
                    level: str = "INFO", **kwargs):
    """Log a system event"""
    try:
        logger = get_logger("system")
        
        extra_info = f"[{component}] {event_type}: {message}"
        if kwargs:
            extra_info += f" - {kwargs}"
        
        log_level = getattr(logging, level.upper())
        logger.log(log_level, extra_info)
        
    except Exception as e:
        st.error(f"Error logging system event: {e}")

def get_recent_logs(level: str = None, limit: int = 100):
    """Get recent logs from the Streamlit handler"""
    try:
        return streamlit_handler.get_logs(level=level, limit=limit)
    except Exception as e:
        st.error(f"Error getting recent logs: {e}")
        return []

def display_logs_in_streamlit(logs, container=None):
    """Display logs in Streamlit with proper formatting"""
    try:
        if not logs:
            st.info("No logs available")
            return
        
        # Use container if provided, otherwise use main area
        display_container = container if container else st
        
        for log in reversed(logs):  # Show newest first
            timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            level = log['level']
            message = log['message']
            
            # Color code based on level
            if level == 'ERROR':
                display_container.error(f"**{timestamp}** - {message}")
            elif level == 'WARNING':
                display_container.warning(f"**{timestamp}** - {message}")
            elif level == 'INFO':
                display_container.info(f"**{timestamp}** - {message}")
            else:
                display_container.text(f"{timestamp} - {level} - {message}")
                
    except Exception as e:
        st.error(f"Error displaying logs: {e}")
