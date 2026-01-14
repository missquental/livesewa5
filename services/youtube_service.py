import time
from googleapiclient.discovery import build


class YouTubeService:
    def __init__(self, credentials):
        self.youtube = build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )

    # ===============================
    # CREATE LIVE STREAM
    # ===============================
    def create_live_stream(self, title, resolution, frame_rate):
        request = self.youtube.liveStreams().insert(
            part="snippet,cdn",
            body={
                "snippet": {
                    "title": title
                },
                "cdn": {
                    "frameRate": frame_rate.replace("fps", ""),
                    "resolution": resolution,
                    "ingestionType": "rtmp"
                }
            }
        )
        response = request.execute()

        return {
            "stream_id": response["id"],
            "stream_key": response["cdn"]["ingestionInfo"]["streamName"],
            "stream_url": response["cdn"]["ingestionInfo"]["ingestionAddress"]
        }

    # ===============================
    # CREATE BROADCAST
    # ===============================
    def create_live_broadcast(self, title, description, scheduled_start, privacy_status):
        request = self.youtube.liveBroadcasts().insert(
            part="snippet,status,contentDetails",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "scheduledStartTime": scheduled_start
                },
                "status": {
                    "privacyStatus": privacy_status
                },
                "contentDetails": {
                    "enableAutoStart": False,
                    "enableAutoStop": False,
                    "enableDvr": True
                }
            }
        )
        return request.execute()

    # ===============================
    # BIND STREAM
    # ===============================
    def bind_stream_to_broadcast(self, broadcast_id, stream_id):
        request = self.youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_id,
            streamId=stream_id
        )
        request.execute()
        return True

    # ===============================
    # CHECK STREAM STATUS
    # ===============================
    def is_stream_active(self, stream_id):
        request = self.youtube.liveStreams().list(
            part="status",
            id=stream_id
        )
        response = request.execute()

        if not response.get("items"):
            return False

        return response["items"][0]["status"]["streamStatus"] == "active"

    # ===============================
    # AUTO TRANSITION (KUNCI UTAMA)
    # ===============================
    def auto_transition_to_live(self, broadcast_id, stream_id, timeout=90):
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_stream_active(stream_id):
                return self.youtube.liveBroadcasts().transition(
                    broadcastStatus="live",
                    id=broadcast_id,
                    part="status"
                ).execute()

            time.sleep(3)

        raise TimeoutError("Encoder tidak aktif, gagal auto LIVE")

    # ===============================
    # END LIVE
    # ===============================
    def transition_to_complete(self, broadcast_id):
        return self.youtube.liveBroadcasts().transition(
            broadcastStatus="complete",
            id=broadcast_id,
            part="status"
        ).execute()
