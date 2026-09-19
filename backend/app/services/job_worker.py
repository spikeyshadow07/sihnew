import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from ..database.db import SessionLocal
from ..database.models import JobModel, EventModel
from ..settings import OUTPUTS_DIR, MODEL_PATH
from .media import make_browser_video
from .clip_service import EvidenceClipService
from ai_engine.processor import VideoProcessor
from risk_engine.conflict_detector import ConflictDetector
from risk_engine.risk_score import calculate_near_miss_risk_score

logger = logging.getLogger(__name__)

class BackgroundWorker:
    def __init__(self):
        # One worker avoids simultaneous CPU inference and shared-model/SQLite races.
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nearguard")

    def process_job_async(self, job_id):
        return self.executor.submit(self._run_job_pipeline, job_id)

    def _run_job_pipeline(self, job_id):
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            if job is None:
                return
            raw_video = OUTPUTS_DIR / "annotated" / f"{job_id}.raw.mp4"
            try:
                config = json.loads(job.config_json)
                job.status, job.progress = "processing", 1
                job.status_message = "Opening video and detector"
                db.commit()
                def progress(value, message):
                    job.progress, job.status_message = 5+value*.6, message
                    db.commit()
                import cv2
                cap = cv2.VideoCapture(str(job.video_path))
                health_scores = {"visibility": 100, "sharpness": 100, "overall": 100}
                if cap.isOpened():
                    ok, frame = cap.read()
                    if ok:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                        brightness = gray.mean()
                        v_score = min(100, max(0, int((brightness / 255.0) * 100 + 20)))
                        s_score = min(100, max(0, int((sharpness / 1000.0) * 100)))
                        health_scores = {"visibility": v_score, "sharpness": s_score, "overall": (v_score + s_score) // 2}
                    cap.release()
                config = json.loads(job.config_json or "{}")
                config["video_health"] = health_scores
                job.config_json = json.dumps(config)

                processor = VideoProcessor(camera_config=config.get("camera_config"),
                                           detector_mode=config["detector_mode"], model_path=MODEL_PATH)
                tracks = processor.process_video(job.video_path, raw_video, progress)
                tracks["job_id"] = job_id
                tracks_path = OUTPUTS_DIR / "tracks" / f"{job_id}.json"
                temporary = tracks_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(tracks, allow_nan=False), encoding="utf-8")
                temporary.replace(tracks_path)
                job.progress, job.status_message = 68, "Encoding playable evidence video"
                db.commit()
                annotated = OUTPUTS_DIR / "annotated" / f"{job_id}.mp4"
                make_browser_video(raw_video, annotated)
                candidates = ConflictDetector().detect_conflicts_from_tracks(tracks) if tracks["calibrated"] else []
                config["candidate_count_before_limit"] = len(candidates)
                config["frame_count"] = len(tracks["frames"])
                config["track_count"] = len({t["id"] for f in tracks["frames"] for t in f["tracks"]})
                config["warnings"] = []
                if len(candidates) > 100:
                    config["warnings"].append("Only the first 100 chronological candidates were retained. Use a shorter clip.")
                if config["detector_mode"] == "motion":
                    config["warnings"].append("Motion baseline: categories are unknown and object merging/fragmentation can produce false results.")
                config["warnings"].append("PET is not implemented; DRAC applies only to approximate same-heading conflicts.")
                clip_service = EvidenceClipService(OUTPUTS_DIR / "clips")
                retained = candidates[:100]
                for index, candidate in enumerate(retained):
                    identifier = f"EVT-{job_id.removeprefix('job_')}-{index+1:03d}"
                    measures = candidate["surrogate_measures"]
                    score = calculate_near_miss_risk_score(
                        measures["min_ttc"], None, measures["max_drac"], measures["delta_v"],
                        measures["min_distance_m"], candidate["participant_classes"])
                    candidate["id"] = identifier
                    clip = clip_service.extract_clip(annotated, candidate)
                    reasons = ["Requires human confirmation; estimates depend on tracking and planar calibration.",
                               "Circular road-user footprints and constant velocity are approximate."]
                    if config["detector_mode"] == "motion":
                        reasons.append("Motion baseline: class and confidence are not learned model predictions.")
                    db.add(EventModel(id=identifier, job_id=job_id, video_id=job.video_name,
                        timestamp_start=candidate["timestamp_start"], timestamp_peak=candidate["timestamp_peak"],
                        timestamp_end=candidate["timestamp_end"], participant_ids=json.dumps(candidate["participant_ids"]),
                        participant_classes=json.dumps(candidate["participant_classes"]), conflict_type=candidate["conflict_type"],
                        **measures, risk_score=score["risk_score"], risk_level=score["risk_level"], status="uncertain",
                        tracking_confidence=candidate.get("evidence_confidence", candidate["tracking_confidence"]*100) / 100.0,
                        uncertainty_reasons=json.dumps(reasons),
                        road_zone="Calibrated road area", ground_coords=json.dumps(candidate["location"]["ground_coords"]),
                        pixel_coords=json.dumps(candidate["location"]["pixel_coords"]), evidence_clip_path=clip,
                        recommendation_summary="Review both tracked paths and the evidence clip before accepting this candidate.",
                        engineering_action="If similar confirmed events recur here, ask a road-safety engineer to investigate visibility and movement conflicts.",
                        policy_action="This prototype cannot establish a cause or choose a road intervention."))
                job.config_json = json.dumps(config)
                job.total_events, job.progress, job.status = len(retained), 100, "completed"
                job.completed_at = datetime.utcnow()
                job.status_message = (f"Completed: {len(retained)} candidate events. Review the evidence." if tracks["calibrated"]
                                      else "Tracking completed. No risk measurements: this video was not calibrated.")
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.exception("Analysis failed for %s", job_id)
                job = db.get(JobModel, job_id)
                if job:
                    job.status, job.status_message = "failed", str(exc)[:500]
                    job.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                raw_video.unlink(missing_ok=True)

worker = BackgroundWorker()
