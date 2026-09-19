import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import EventModel, JobModel

router = APIRouter(prefix="/api/events", tags=["Events"])

def latest_review(event):
    return max(event.reviews, key=lambda r: r.id) if event.reviews else None

def format_event_response(event):
    review = latest_review(event)
    return {"id": event.id, "job_id": event.job_id, "video_id": event.video_id,
        "timestamp_start": event.timestamp_start, "timestamp_peak": event.timestamp_peak, "timestamp_end": event.timestamp_end,
        "participant_ids": json.loads(event.participant_ids), "participant_classes": json.loads(event.participant_classes),
        "conflict_type": event.conflict_type, "risk_score": event.risk_score, "risk_level": event.risk_level,
        "surrogate_measures": {"min_ttc": event.min_ttc, "pet": event.pet, "max_drac": event.max_drac,
            "delta_v": event.delta_v, "min_distance_m": event.min_distance_m},
        "quality_check": {"status": event.status, "tracking_confidence": event.tracking_confidence,
            "uncertainty_reasons": json.loads(event.uncertainty_reasons or "[]")},
        "human_review": {"reviewed": bool(review), "decision": review.decision if review else "pending",
            "reviewer_id": review.reviewer_id if review else None, "notes": review.notes if review else "",
            "reviewed_at": review.reviewed_at if review else None},
        "location": {"road_zone": event.road_zone, "ground_coords": json.loads(event.ground_coords),
            "pixel_coords": json.loads(event.pixel_coords)},
        "evidence_clip_path": event.evidence_clip_path, "created_at": event.created_at,
        "recommendation": {"summary": event.recommendation_summary, "engineering_action": event.engineering_action,
            "policy_action": event.policy_action}}

def scoped_events(db, job_id=None):
    query = db.query(EventModel).join(JobModel).filter(JobModel.status == "completed")
    if job_id:
        query = query.filter(EventModel.job_id == job_id)
    return query

@router.get("")
def get_events(job_id: str | None = None, risk_level: str | None = None,
               review_decision: str | None = None, limit: int = Query(500, ge=1, le=1000),
               db: Session = Depends(get_db)):
    query = scoped_events(db, job_id)
    if risk_level:
        query = query.filter(EventModel.risk_level == risk_level)
    rows = [format_event_response(e) for e in query.order_by(EventModel.risk_score.desc()).limit(limit).all()]
    return [e for e in rows if review_decision is None or e["human_review"]["decision"] == review_decision]

@router.get("/export.csv")
def export_events(job_id: str, db: Session = Depends(get_db)):
    if db.get(JobModel, job_id) is None:
        raise HTTPException(404, "Job not found.")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["event_id", "video_name", "peak_seconds", "type", "risk_score_heuristic", "risk_level",
                     "ttc_estimate_seconds", "pet_seconds", "drac_estimate_mps2", "center_distance_m",
                     "review_decision", "review_notes", "source_type", "detector_mode"])
    metadata = json.loads(db.get(JobModel, job_id).config_json or "{}")
    def safe(value):
        value = "" if value is None else str(value)
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value
    for event in scoped_events(db, job_id).order_by(EventModel.timestamp_peak).all():
        review = latest_review(event)
        writer.writerow([safe(value) for value in [event.id, event.video_id, event.timestamp_peak, event.conflict_type,
            event.risk_score, event.risk_level, event.min_ttc, event.pet, event.max_drac, event.min_distance_m,
            review.decision if review else "pending", review.notes if review else "",
            metadata.get("source_type"), metadata.get("detector_mode")]])
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{job_id}_events.csv"'})

@router.get("/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(EventModel, event_id)
    if event is None:
        raise HTTPException(404, "Event not found.")
    return format_event_response(event)

@router.get("/{event_id}/tracks")
def tracks(event_id: str, db: Session = Depends(get_db)):
    from .simulation import event_tracks
    event = db.get(EventModel, event_id)
    if event is None:
        raise HTTPException(404, "Event not found.")
    ids, frames = event_tracks(event)
    return {"participant_ids": ids, "frames": frames}
