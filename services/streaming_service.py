import subprocess
import threading
import time
import os
import streamlit as st
from datetime import datetime
from typing import Dict, Optional, Callable
import signal
import psutil

class StreamingService:
    """Handles FFmpeg streaming operations and monitoring"""
    
    def __init__(self):
        self.active_streams = {}
        self.stream_threads = {}
        self.monitoring_threads = {}
        self.stream_processes = {}
    
    def check_ffmpeg_installation(self) -> bool:
        """Check if FFmpeg is installed and available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def get_video_info(self, video_path: str) -> Optional[Dict]:
        """Get video file information using FFprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
                # Extract video stream info
                video_stream = None
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    return {
                        'duration': float(info.get('format', {}).get('duration', 0)),
                        'width': video_stream.get('width', 0),
                        'height': video_stream.get('height', 0),
                        'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                        'bitrate': int(info.get('format', {}).get('bit_rate', 0)),
                        'codec': video_stream.get('codec_name', 'unknown')
                    }
            return None
            
        except Exception as e:
            st.error(f"Error getting video info: {e}")
            return None
    
    def start_stream(self, session_id: str, video_path: str, stream_url: str, 
                    stream_key: str, callback: Callable = None) -> bool:
        """Start FFmpeg streaming process"""
        try:
            if session_id in self.active_streams:
                st.warning(f"Stream {session_id} is already active")
                return False
            
            # Validate video file
            if not os.path.exists(video_path):
                st.error(f"Video file not found: {video_path}")
                return False
            
            # Get video info
            video_info = self.get_video_info(video_path)
            if not video_info:
                st.error("Could not read video file information")
                return False
            
            # Construct FFmpeg command
            rtmp_url = f"{stream_url}/{stream_key}"
            
            cmd = [
                'ffmpeg',
                '-re',  # Read input at its native frame rate
                '-i', video_path,
                '-c:v', 'libx264',  # Video codec
                '-preset', 'fast',  # Encoding speed
                '-maxrate', '3000k',  # Max bitrate
                '-bufsize', '6000k',  # Buffer size
                '-vf', 'scale=1920:1080',  # Scale to 1080p
                '-g', '60',  # GOP size
                '-c:a', 'aac',  # Audio codec
                '-b:a', '128k',  # Audio bitrate
                '-ac', '2',  # Audio channels
                '-ar', '44100',  # Audio sample rate
                '-f', 'flv',  # Output format
                rtmp_url
            ]
            
            # Start streaming process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store stream information
            self.active_streams[session_id] = {
                'video_path': video_path,
                'stream_url': stream_url,
                'stream_key': stream_key,
                'start_time': datetime.now(),
                'status': 'starting',
                'video_info': video_info,
                'rtmp_url': rtmp_url
            }
            
            self.stream_processes[session_id] = process
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_stream,
                args=(session_id, process, callback)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            self.monitoring_threads[session_id] = monitor_thread
            
            st.success(f"Started streaming session: {session_id}")
            return True
            
        except Exception as e:
            st.error(f"Error starting stream: {e}")
            return False
    
    def _monitor_stream(self, session_id: str, process: subprocess.Popen, 
                       callback: Callable = None):
        """Monitor streaming process in background thread"""
        try:
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    # Process has terminated
                    if session_id in self.active_streams:
                        self.active_streams[session_id]['status'] = 'stopped'
                        self.active_streams[session_id]['end_time'] = datetime.now()
                    
                    if callback:
                        callback(session_id, 'stopped', 'Stream process terminated')
                    break
                
                # Update stream status
                if session_id in self.active_streams:
                    elapsed = (datetime.now() - self.active_streams[session_id]['start_time']).total_seconds()
                    if elapsed > 10 and self.active_streams[session_id]['status'] == 'starting':
                        self.active_streams[session_id]['status'] = 'active'
                        if callback:
                            callback(session_id, 'active', 'Stream is now active')
                
                time.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            if callback:
                callback(session_id, 'error', f"Monitor error: {e}")
    
    def stop_stream(self, session_id: str) -> bool:
        """Stop streaming process"""
        try:
            if session_id not in self.active_streams:
                st.warning(f"Stream {session_id} is not active")
                return False
            
            # Terminate FFmpeg process
            if session_id in self.stream_processes:
                process = self.stream_processes[session_id]
                process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if necessary
                    process.kill()
                    process.wait()
                
                del self.stream_processes[session_id]
            
            # Update stream status
            if session_id in self.active_streams:
                self.active_streams[session_id]['status'] = 'stopped'
                self.active_streams[session_id]['end_time'] = datetime.now()
            
            st.success(f"Stopped streaming session: {session_id}")
            return True
            
        except Exception as e:
            st.error(f"Error stopping stream: {e}")
            return False
    
    def get_stream_status(self, session_id: str) -> Optional[Dict]:
        """Get current stream status"""
        if session_id in self.active_streams:
            status = self.active_streams[session_id].copy()
            
            # Calculate duration
            start_time = status['start_time']
            end_time = status.get('end_time', datetime.now())
            duration = (end_time - start_time).total_seconds()
            status['duration_seconds'] = int(duration)
            
            return status
        return None
    
    def get_all_stream_status(self) -> Dict:
        """Get status of all streams"""
        status = {}
        for session_id in self.active_streams:
            status[session_id] = self.get_stream_status(session_id)
        return status
    
    def stop_all_streams(self):
        """Stop all active streams"""
        for session_id in list(self.active_streams.keys()):
            self.stop_stream(session_id)
    
    def get_system_resources(self) -> Dict:
        """Get system resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': psutil.net_io_counters()._asdict()
            }
        except Exception as e:
            st.error(f"Error getting system resources: {e}")
            return {}
    
    def cleanup(self):
        """Clean up all resources"""
        try:
            # Stop all streams
            self.stop_all_streams()
            
            # Clean up data structures
            self.active_streams.clear()
            self.stream_threads.clear()
            self.monitoring_threads.clear()
            self.stream_processes.clear()
            
        except Exception as e:
            st.error(f"Error during cleanup: {e}")

# Global streaming service instance
streaming_service = StreamingService()
