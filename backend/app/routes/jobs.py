import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import JobModel
from ..settings import OUTPUTS_DIR

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

def format_job(job):
    metadata = json.loads(job.config_json or "{}")
    complete = job.status == "completed"
    return {"id": job.id, "video_name": job.video_name, "status": job.status, "progress": job.progress,
        "status_message": job.status_message, "total_events": job.total_events, "created_at": job.created_at,
        "completed_at": job.completed_at, "metadata": metadata,
        "frame_url": f"/outputs/frames/{job.id}.jpg" if (OUTPUTS_DIR/"frames"/f"{job.id}.jpg").is_file() else None,
        "annotated_url": f"/outputs/annotated/{job.id}.mp4" if complete and (OUTPUTS_DIR/"annotated"/f"{job.id}.mp4").is_file() else None,
        "tracks_url": f"/outputs/tracks/{job.id}.json" if complete and (OUTPUTS_DIR/"tracks"/f"{job.id}.json").is_file() else None}

@router.get("")
def get_jobs(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return [format_job(j) for j in db.query(JobModel).order_by(JobModel.created_at.desc()).limit(limit).all()]

@router.get("/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.get(JobModel, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return format_job(job)
