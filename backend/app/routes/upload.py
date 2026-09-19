import json
import math
import importlib.util
import uuid
from pathlib import Path
import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import JobModel
from ..settings import DATA_DIR, OUTPUTS_DIR, MODEL_PATH, MAX_UPLOAD_BYTES, MAX_DURATION_SECONDS
from ..services.job_worker import worker
from ai_engine.calibration import CameraCalibration
from ai_engine.video_geometry import analysis_resolution
from .jobs import format_job

router = APIRouter(prefix="/api/upload", tags=["Upload"])
DEMOS = {"demo_video.mp4", "pedestrian_school_zone.mp4"}

def inspect_video(path):
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError("The file is not a supported video.")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ok, frame = capture.read()
        if not ok or not math.isfinite(fps) or not 1 <= fps <= 120 or count < 2:
            raise ValueError("The video has no usable frames or has an unsupported frame rate.")
        analysis_resolution(width, height)
        if count/fps > MAX_DURATION_SECONDS or count > 14400:
            raise ValueError("Use a clip no longer than two minutes.")
        return {"width": width, "height": height}, fps, count/fps, frame
    finally:
        capture.release()

@router.post("", status_code=202)
def upload_video(file: UploadFile | None = File(None), use_demo: bool = Form(False),
                 scenario: str = Form("demo_video.mp4"), calibration_json: str | None = Form(None),
                 detector_mode: str = Form("motion"), db: Session = Depends(get_db)):
    if use_demo and file is not None:
        raise HTTPException(400, "Choose either a demo or an uploaded file.")
    if not use_demo and file is None:
        raise HTTPException(400, "Choose a video file first.")
    if detector_mode not in ("motion", "yolo"):
        raise HTTPException(400, "Unknown detector mode.")
    if detector_mode == "yolo" and (not MODEL_PATH.is_file() or importlib.util.find_spec("ultralytics") is None):
        raise HTTPException(400, "YOLO is not installed with local weights. See README or select the motion baseline.")
    if db.query(JobModel).filter(JobModel.status.in_(["queued", "processing"])).count() >= 5:
        raise HTTPException(429, "The processing queue is full. Wait for a job to finish.")
    identifier = "job_" + uuid.uuid4().hex
    path, created_upload = None, False
    try:
        if use_demo:
            if scenario not in DEMOS:
                raise ValueError("Unknown demo scenario.")
            path = DATA_DIR / scenario
            name = scenario
            if not path.is_file():
                raise ValueError("Bundled demo video is missing.")
        else:
            name = Path((file.filename or "video.mp4").replace("\\", "/")).name
            suffix = Path(name).suffix.lower()
            if suffix not in (".mp4", ".mov", ".avi", ".webm", ".mkv"):
                raise ValueError("Use MP4, MOV, AVI, WebM or MKV.")
            path, created_upload = DATA_DIR / "uploads" / (identifier+suffix), True
            size = 0
            with path.open("wb") as destination:
                while chunk := file.file.read(1024*1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise ValueError("Video exceeds the 150 MB upload limit.")
                    destination.write(chunk)
        resolution, fps, duration, frame = inspect_video(path)
        processed_resolution = analysis_resolution(**resolution)
        resized = processed_resolution != resolution
        camera = None
        if use_demo:
            # These top-down synthetic scenes use an illustrative scale, not a field survey.
            w, h = resolution["width"], resolution["height"]
            camera = {"resolution": resolution, "calibration": {
                "source_pixel_points": [[0, 0], [w, 0], [w, h], [0, h]],
                "dest_ground_points": [[0, 0], [w*.05, 0], [w*.05, h*.05], [0, h*.05]]}}
        elif calibration_json:
            if len(calibration_json) > 20000:
                raise ValueError("Calibration payload is too large.")
            camera = json.loads(calibration_json)
            CameraCalibration(config=camera).validate_resolution(**resolution)
        metadata = {"schema_version": 2, "source_type": "synthetic_demo" if use_demo else "uploaded",
            "detector_mode": detector_mode, "camera_config": camera, "resolution": processed_resolution,
            "source_resolution": resolution, "resized": resized,
            "fps": fps, "duration_seconds": duration}
        if resized:
            frame = cv2.resize(frame, (processed_resolution["width"], processed_resolution["height"]),
                               interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(OUTPUTS_DIR / "frames" / (identifier+".jpg")), frame)
        job = JobModel(id=identifier, video_path=str(path), video_name=name[:256],
                       status="queued", progress=0, config_json=json.dumps(metadata))
        db.add(job)
        db.commit()
        db.refresh(job)
        worker.process_job_async(identifier)
        return format_job(job)
    except (ValueError, TypeError, AttributeError, cv2.error) as exc:
        db.rollback()
        if created_upload and path:
            path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc
    finally:
        if file:
            file.file.close()
