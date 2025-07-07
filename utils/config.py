import os
import json
import streamlit as st
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config_file = Path("config.json")
        self.default_config = {
            "app": {
                "title": "YouTube Live Streaming Studio",
                "version": "2.0.0",
                "debug": False
            },
            "streaming": {
                "default_resolution": "1080p",
                "default_framerate": "30fps",
                "default_bitrate": "3000k",
                "buffer_size": "6000k",
                "max_concurrent_streams": 5
            },
            "database": {
                "path": "streaming_logs.db",
                "backup_enabled": True,
                "backup_interval_hours": 24
            },
            "youtube": {
                "api_quota_limit": 10000,
                "rate_limit_per_minute": 100
            },
            "monitoring": {
                "health_check_interval": 30,
                "metrics_collection_interval": 60,
                "log_retention_days": 30
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create with defaults"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_config = self._merge_config(self.default_config, config)
                return merged_config
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config.copy()
                
        except Exception as e:
            st.warning(f"Error loading config, using defaults: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error saving config: {e}")
            return False
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults"""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_env_config(self) -> Dict[str, Any]:
        """Get configuration from environment variables"""
        env_config = {}
        
        # API Keys
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if youtube_api_key:
            env_config["youtube_api_key"] = youtube_api_key
        
        # Database settings
        db_path = os.getenv("DATABASE_PATH")
        if db_path:
            env_config["database_path"] = db_path
        
        # Debug mode
        debug = os.getenv("DEBUG", "false").lower() == "true"
        env_config["debug"] = debug
        
        # Streaming settings
        max_streams = os.getenv("MAX_CONCURRENT_STREAMS")
        if max_streams:
            try:
                env_config["max_concurrent_streams"] = int(max_streams)
            except ValueError:
                pass
        
        return env_config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            current_config = self.load_config()
            updated_config = self._merge_config(current_config, updates)
            return self.save_config(updated_config)
        except Exception as e:
            st.error(f"Error updating config: {e}")
            return False

# Global config manager instance
config_manager = ConfigManager()

def load_config() -> Dict[str, Any]:
    """Load application configuration"""
    config = config_manager.load_config()
    
    # Override with environment variables
    env_config = config_manager.get_env_config()
    if env_config:
        config.update(env_config)
    
    return config

def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a configuration value using dot notation (e.g., 'streaming.default_resolution')"""
    config = load_config()
    keys = key_path.split('.')
    
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def set_config_value(key_path: str, value: Any) -> bool:
    """Set a configuration value using dot notation"""
    keys = key_path.split('.')
    updates = {}
    
    # Build nested dictionary structure
    current = updates
    for key in keys[:-1]:
        current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    
    return config_manager.update_config(updates)
