import subprocess
import threading
import time

class StreamingService:

    def start_stream(self, session_id, video_path, stream_url, stream_key, callback=None):

        rtmp_url = f"{stream_url}/{stream_key}"

        cmd = [
            "ffmpeg",
            "-re",                     # REALTIME (WAJIB)
            "-stream_loop", "-1",      # LOOP VIDEO (WAJIB)
            "-i", video_path,

            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", "3000k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", "60",

            "-c:a", "aac",             # AUDIO WAJIB
            "-b:a", "128k",
            "-ar", "44100",

            "-f", "flv",
            rtmp_url
        ]

        try:
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

            # MONITOR PROCESS
            def monitor():
                for line in process.stderr:
                    if callback:
                        callback(session_id, "ffmpeg", line.strip())

                self.active_streams[session_id]["status"] = "stopped"

            threading.Thread(target=monitor, daemon=True).start()

            return True

        except Exception as e:
            if callback:
                callback(session_id, "error", str(e))
            return False
