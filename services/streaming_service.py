import subprocess
import threading
import time


class StreamingService:
    def __init__(self):
        self.active_streams = {}

    def check_ffmpeg_installation(self):
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True)
            return True
        except Exception:
            return False

    def start_stream(self, session_id, video_path, stream_url, stream_key, callback=None):
        rtmp_url = f"{stream_url}/{stream_key}"

        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", "3000k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            rtmp_url
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self.active_streams[session_id] = {
            "process": process,
            "status": "running",
            "start_time": time.time(),
            "video_path": video_path
        }

        def monitor():
            for line in process.stderr:
                if callback:
                    callback(session_id, "ffmpeg", line.strip())

            self.active_streams[session_id]["status"] = "stopped"

        threading.Thread(target=monitor, daemon=True).start()
        return True

    def stop_stream(self, session_id):
        if session_id in self.active_streams:
            self.active_streams[session_id]["process"].terminate()
            self.active_streams[session_id]["status"] = "stopped"
            return True
        return False

    def get_all_stream_status(self):
        data = {}
        for sid, info in self.active_streams.items():
            data[sid] = {
                "status": info["status"],
                "duration_seconds": int(time.time() - info["start_time"]),
                "video_path": info["video_path"]
            }
        return data
