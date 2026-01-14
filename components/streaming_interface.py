import threading

# SETELAH FFmpeg START
success = streaming_service.start_stream(
    session_id=session_id,
    video_path=video_path,
    stream_url=stream_info["stream_url"],
    stream_key=stream_info["stream_key"],
    callback=lambda s, stt, msg: log_stream_event(s, stt, msg)
)

if success:
    st.info("Menunggu encoder aktif...")

    def auto_live():
        try:
            youtube_service.auto_transition_to_live(
                broadcast_id=broadcast_info["id"],
                stream_id=stream_info["stream_id"]
            )
            log_stream_event(session_id, "LIVE", "Broadcast LIVE")
        except Exception as e:
            log_stream_event(session_id, "ERROR", str(e))

    threading.Thread(target=auto_live, daemon=True).start()

    st.success("🔴 LIVE OTOMATIS AKAN AKTIF")
    st.info(f"https://www.youtube.com/watch?v={broadcast_info['id']}")
