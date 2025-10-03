import os
import tempfile
from pathlib import Path
from typing import Tuple
import threading
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# Ensure local imports work
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.composition_engine import CompositionEngine
from src.services.export_service import ExportService
from src.utils.logger import setup_logger
from src.models.meeting_config import MeetingConfig
from src.models.speaker_config import SpeakerConfig
from src.models.export_config import (
    ExportConfig,
    VideoCodecConfig,
    AudioCodecConfig,
    GPUConfig,
)


logger = setup_logger()


def hex_to_rgb(hex_color: str) -> Tuple[int, ...]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 180) -> Tuple[int, int, int, int]:
    rgb = hex_to_rgb(hex_color)
    return rgb[0], rgb[1], rgb[2], alpha


def clamp_font_size(speaker_height: int, requested_font_size: int) -> int:
    font_min = max(12, int(speaker_height * 0.04))
    font_max = max(font_min + 1, int(speaker_height * 0.15))
    return max(font_min, min(font_max, requested_font_size))


def clamp_padding(output_height: int, requested_padding: int) -> int:
    pydantic_padding_limit = 50
    padding_min = max(2, int(output_height * 0.01))
    return max(padding_min, min(pydantic_padding_limit, requested_padding))


def build_configs(
    speaker_width: int,
    speaker_height: int,
    manual_font_size: int,
    # new: font family name
    font_family: str,
    font_color: str,
    plate_bg_color: str,
    plate_border_color: str,
    plate_border_width: int,
    plate_padding: int,
    output_width: int,
    output_height: int,
    fps: int,
    ffmpeg_preset: str,
    ffmpeg_crf: int,
    use_gpu: bool,
) -> Tuple[SpeakerConfig, ExportConfig]:
    # Enforce speaker size limits: width <= 46% of output width, height <= 55% of output height
    max_speaker_width = max(1, int(output_width * 0.46))
    max_speaker_height = max(1, int(output_height * 0.55))
    limited_speaker_width = min(speaker_width, max_speaker_width)
    limited_speaker_height = min(speaker_height, max_speaker_height)

    dynamic_font_size = clamp_font_size(limited_speaker_height, manual_font_size)
    dynamic_plate_padding = clamp_padding(output_height, plate_padding)

    speaker_config = SpeakerConfig(
        width=limited_speaker_width,
        height=limited_speaker_height,
        position=None,
        font_size=dynamic_font_size,
        font_family=font_family,
        font_color=hex_to_rgb(font_color),
        plate_bg_color=hex_to_rgba(plate_bg_color),
        plate_border_color=hex_to_rgb(plate_border_color),
        plate_border_width=plate_border_width,
        plate_padding=dynamic_plate_padding,
    )

    export_config = ExportConfig(
        width=output_width,
        height=output_height,
        fps=fps,
        video_codec=VideoCodecConfig(preset=ffmpeg_preset, crf=ffmpeg_crf),
        audio_codec=AudioCodecConfig(),
        gpu_config=GPUConfig(use_gpu=use_gpu),
    )

    return speaker_config, export_config


app = FastAPI(title="Video Meeting Composer API")

# Mount static assets
static_dir = Path(__file__).parent / "static"
public_dir = Path(__file__).parent / "public"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/public", StaticFiles(directory=str(public_dir)), name="public")

jobs_lock = threading.Lock()
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
def index():
    index_path = static_dir / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Static UI not found</h1>", status_code=404)
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.post("/api/preview")
async def generate_preview(
    background: UploadFile = File(...),
    speaker1: UploadFile = File(...),
    speaker2: UploadFile = File(...),
    speaker1_name: str = Form(...),
    speaker2_name: str = Form(...),
    speaker_width: int = Form(...),
    speaker_height: int = Form(...),
    manual_font_size: int = Form(...),
    font_color: str = Form(...),
    plate_bg_color: str = Form(...),
    plate_border_color: str = Form(...),
    plate_border_width: int = Form(...),
    plate_padding: int = Form(...),
    font_family: str = Form("DejaVuSans-Bold"),
    output_width: int = Form(...),
    output_height: int = Form(...),
    fps: int = Form(...),
    ffmpeg_preset: str = Form(...),
    ffmpeg_crf: int = Form(...),
    use_gpu: bool = Form(...),
):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            background_path = os.path.join(temp_dir, background.filename)
            speaker1_path = os.path.join(temp_dir, speaker1.filename)
            speaker2_path = os.path.join(temp_dir, speaker2.filename)

            with open(background_path, "wb") as f:
                f.write(await background.read())
            with open(speaker1_path, "wb") as f:
                f.write(await speaker1.read())
            with open(speaker2_path, "wb") as f:
                f.write(await speaker2.read())

            speaker_config, export_config = build_configs(
                speaker_width,
                speaker_height,
                manual_font_size,
                font_color,
                plate_bg_color,
                plate_border_color,
                plate_border_width,
                plate_padding,
                output_width,
                output_height,
                fps,
                ffmpeg_preset,
                ffmpeg_crf,
                use_gpu,
            )

            engine = CompositionEngine(speaker_config, export_config)
            preview_path = os.path.join(temp_dir, "preview.jpg")
            success = engine.create_preview(
                background_path,
                speaker1_path,
                speaker2_path,
                speaker1_name,
                speaker2_name,
                preview_path,
            )

            if not success:
                return JSONResponse({"error": "Failed to create preview"}, status_code=500)

            # Read bytes before TemporaryDirectory is cleaned up
            with open(preview_path, "rb") as f:
                data = f.read()
            return Response(content=data, media_type="image/jpeg", headers={"Content-Disposition": "attachment; filename=preview.jpg"})
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/export")
async def export_video(
    background: UploadFile = File(...),
    speaker1: UploadFile = File(...),
    speaker2: UploadFile = File(...),
    speaker1_name: str = Form(...),
    speaker2_name: str = Form(...),
    speaker_width: int = Form(...),
    speaker_height: int = Form(...),
    manual_font_size: int = Form(...),
    font_color: str = Form(...),
    plate_bg_color: str = Form(...),
    plate_border_color: str = Form(...),
    plate_border_width: int = Form(...),
    plate_padding: int = Form(...),
    output_width: int = Form(...),
    output_height: int = Form(...),
    fps: int = Form(...),
    ffmpeg_preset: str = Form(...),
    ffmpeg_crf: int = Form(...),
    use_gpu: bool = Form(...),
):
    try:
        # Persist files in a per-job temp dir, because export runs in background
        job_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp(prefix=f"export_{job_id}_")

        background_path = os.path.join(temp_dir, background.filename)
        speaker1_path = os.path.join(temp_dir, speaker1.filename)
        speaker2_path = os.path.join(temp_dir, speaker2.filename)

        with open(background_path, "wb") as f:
            f.write(await background.read())
        with open(speaker1_path, "wb") as f:
            f.write(await speaker1.read())
        with open(speaker2_path, "wb") as f:
            f.write(await speaker2.read())

        speaker_config, export_config = build_configs(
            speaker_width,
            speaker_height,
            manual_font_size,
            font_family,
            font_color,
            plate_bg_color,
            plate_border_color,
            plate_border_width,
            plate_padding,
            output_width,
            output_height,
            fps,
            ffmpeg_preset,
            ffmpeg_crf,
            use_gpu,
        )

        output_file_path = os.path.join(temp_dir, "meeting_output.mp4")
        meeting_config = MeetingConfig(
            background_path=background_path,
            speaker1_path=speaker1_path,
            speaker2_path=speaker2_path,
            speaker1_name=speaker1_name,
            speaker2_name=speaker2_name,
            output_path=output_file_path,
        )

        engine = CompositionEngine(speaker_config, export_config)
        exporter = ExportService(export_config)

        with jobs_lock:
            jobs[job_id] = {"progress": 0.0, "status": "running", "path": output_file_path, "dir": temp_dir}

        def run_export():
            try:
                def progress_cb(p: float):
                    with jobs_lock:
                        if job_id in jobs:
                            jobs[job_id]["progress"] = float(max(0.0, min(100.0, p)))

                ok = exporter.export_video(meeting_config, engine, progress_cb)
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "done" if ok else "error"
                        if ok:
                            jobs[job_id]["progress"] = 100.0
            except Exception as ex:
                logger.error(f"Job {job_id} failed: {ex}")
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "error"

        threading.Thread(target=run_export, daemon=True).start()
        return JSONResponse({"job_id": job_id})
    except Exception as e:
        logger.error(f"Export error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/export/status/{job_id}")
def export_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "not found"}, status_code=404)
        return {"status": job["status"], "progress": job["progress"]}


@app.get("/api/export/download/{job_id}")
def export_download(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "not found"}, status_code=404)
        if job["status"] != "done":
            return JSONResponse({"error": "not ready"}, status_code=400)
        path = job["path"]
    if not os.path.exists(path):
        return JSONResponse({"error": "file missing"}, status_code=404)
    return FileResponse(path, media_type="video/mp4", filename="meeting_output.mp4")

