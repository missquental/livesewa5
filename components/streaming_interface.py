import streamlit as st
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from services.streaming_service import streaming_service
from services.youtube_service import youtube_service
from services.auth_service import auth_service
from services.database import save_streaming_session
from utils.logging import log_stream_event


# =========================================================
# MAIN INTERFACE
# =========================================================
def render_streaming_interface():
    """Render the live streaming interface"""
    st.title("🔴 Live Streaming Interface")

    # Authentication check
    if not auth_service.is_authenticated():
        st.warning("Silakan autentikasi channel YouTube terlebih dahulu di Channel Manager.")
        return

    # FFmpeg check
    if not streaming_service.check_ffmpeg_installation():
        st.error("FFmpeg tidak ditemukan. Install FFmpeg untuk menggunakan fitur streaming.")
        return

    # Sections
    render_stream_setup()
    st.divider()
    render_stream_management()
    st.divider()
    render_stream_monitoring()


# =========================================================
# STREAM SETUP
# =========================================================
def render_stream_setup():
    st.subheader("🎬 Stream Setup")

    with st.form("stream_setup_form", clear_on_submit=False):

        col1, col2 = st.columns(2)

        # =========================
        # VIDEO SETTINGS
        # =========================
        with col1:
            st.markdown("### 🎥 Video Settings")

            video_file = st.file_uploader(
                "Upload Video",
                type=["mp4", "mkv", "avi", "mov", "wmv"]
            )

            video_path = st.text_input(
                "Atau Path Video",
                placeholder="D:/video/live.mp4"
            )

            resolution = st.selectbox(
                "Resolusi",
                ["1080p", "720p", "480p", "360p"],
                index=1
            )

            framerate = st.selectbox(
                "Frame Rate",
                ["60fps", "30fps", "24fps"],
                index=1
            )

            bitrate = st.selectbox(
                "Bitrate",
                ["4500k", "3000k", "2500k", "2000k", "1500k"],
                index=1
            )

        # =========================
        # YOUTUBE SETTINGS
        # =========================
        with col2:
            st.markdown("### 📺 YouTube Settings")

            stream_title = st.text_input(
                "Judul Live",
                value=f"Live Stream - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            stream_description = st.text_area(
                "Deskripsi",
                value="Live streaming via YouTube Live Streaming Studio",
                height=100
            )

            privacy_status = st.selectbox(
                "Privasi",
                ["public", "unlisted", "private"],
                index=1
            )

            category = st.selectbox(
                "Kategori",
                ["Gaming", "Music", "Education", "Entertainment", "News", "Other"]
            )

            made_for_kids = st.checkbox("Konten untuk Anak-anak")
            tags = st.text_input("Tags (pisahkan dengan koma)")

        # =========================
        # SETELAN TAMBAHAN (YOUTUBE STYLE)
        # =========================
        st.divider()
        st.markdown("### ⚙️ Setelan Tambahan")

        latency = st.radio(
            "Latensi Stream",
            ["Normal", "Rendah", "Ultra-rendah"],
            horizontal=True
        )

        col_a, col_b = st.columns(2)

        with col_a:
            auto_start = st.toggle("Aktifkan Mulai otomatis", value=True)
            enable_dvr = st.toggle("Aktifkan DVR", value=True)

        with col_b:
            auto_stop = st.toggle("Aktifkan Berhenti otomatis", value=False)
            video_360 = st.toggle("Video 360°", value=False)

        # =========================
        # SUBMIT
        # =========================
        submit = st.form_submit_button("🚀 Mulai Live Streaming", use_container_width=True)

        if submit:
            start_stream(
                video_file,
                video_path,
                stream_title,
                stream_description,
                privacy_status,
                category,
                made_for_kids,
                tags,
                resolution,
                framerate,
                bitrate,
                latency,
                auto_start,
                auto_stop,
                enable_dvr,
                video_360
            )


# =========================================================
# START STREAM
# =========================================================
def start_stream(
    video_file, video_path, title, description,
    privacy, category, kids, tags,
    resolution, framerate, bitrate,
    latency, auto_start, auto_stop, dvr, video_360
):
    try:
        if not video_file and not video_path:
            st.error("Video belum dipilih")
            return

        # Save uploaded file
        if video_file:
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            final_path = upload_dir / video_file.name
            with open(final_path, "wb") as f:
                f.write(video_file.getbuffer())
            video_path = str(final_path)

        if not os.path.exists(video_path):
            st.error("File video tidak ditemukan")
            return

        session_id = str(uuid.uuid4())

        # Create YouTube stream
        st.info("Membuat stream YouTube...")
        stream_info = youtube_service.create_live_stream(
            title=f"StreamKey - {title}",
            resolution=resolution,
            frame_rate=framerate
        )

        broadcast = youtube_service.create_live_broadcast(
            title=title,
            description=description,
            scheduled_start=(datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z",
            privacy_status=privacy
        )

        youtube_service.bind_stream_to_broadcast(
            broadcast["id"],
            stream_info["stream_id"]
        )

        # Save session
        save_streaming_session(
            session_id=session_id,
            video_file=video_path,
            stream_title=title,
            stream_description=description,
            tags=tags,
            category=category,
            privacy_status=privacy,
            made_for_kids=kids,
            channel_name=auth_service.get_current_channel()["name"],
            stream_key=stream_info["stream_key"]
        )

        # Store settings
        st.session_state["stream_settings"] = {
            "latency": latency,
            "auto_start": auto_start,
            "auto_stop": auto_stop,
            "dvr": dvr,
            "video_360": video_360
        }

        # Start FFmpeg
        success = streaming_service.start_stream(
            session_id=session_id,
            video_path=video_path,
            stream_url=stream_info["stream_url"],
            stream_key=stream_info["stream_key"],
            callback=lambda s, stt, msg: log_stream_event(s, stt, msg)
        )

        if success:
            st.success("Live streaming BERHASIL dimulai!")
            st.info(f"https://www.youtube.com/watch?v={broadcast['id']}")
        else:
            st.error("Gagal menjalankan FFmpeg")

    except Exception as e:
        st.error(str(e))
        log_stream_event("unknown", "ERROR", str(e))


# =========================================================
# STREAM MANAGEMENT
# =========================================================
def render_stream_management():
    st.subheader("📺 Stream Management")

    streams = streaming_service.get_all_stream_status()
    if not streams:
        st.info("Tidak ada stream aktif")
        return

    for sid, info in streams.items():
        with st.expander(f"Stream {sid}", expanded=True):
            st.write(f"Status: **{info['status']}**")
            st.write(f"Durasi: {info['duration_seconds']} detik")

            if st.button("⛔ Stop Stream", key=f"stop_{sid}"):
                streaming_service.stop_stream(sid)
                st.success("Stream dihentikan")


# =========================================================
# STREAM MONITORING
# =========================================================
def render_stream_monitoring():
    st.subheader("📊 Stream Monitoring")

    streams = streaming_service.get_all_stream_status()
    if not streams:
        st.info("Belum ada stream")
        return

    sid = st.selectbox("Pilih Stream", list(streams.keys()))
    info = streams[sid]

    st.metric("Status", info["status"])
    st.metric("Durasi (detik)", info["duration_seconds"])
