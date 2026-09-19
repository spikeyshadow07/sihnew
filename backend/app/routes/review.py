from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import EventModel, HumanReviewModel, JobModel
from ..models.schemas import HumanReviewSubmit
from .events import format_event_response

router = APIRouter(prefix="/api/review", tags=["Review"])

@router.get("/queue")
def get_review_queue(job_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(EventModel).join(JobModel).filter(JobModel.status == "completed")
    if job_id:
        query = query.filter(EventModel.job_id == job_id)
    return [format_event_response(e) for e in query.order_by(EventModel.risk_score.desc()).all() if not e.reviews]

@router.post("/{event_id}")
def submit_review(event_id: str, data: HumanReviewSubmit, db: Session = Depends(get_db)):
    event = db.get(EventModel, event_id)
    if event is None:
        raise HTTPException(404, "Event not found.")
    db.add(HumanReviewModel(event_id=event_id, reviewer_id=data.reviewer_id, decision=data.decision, notes=data.notes))
    # A human decision does not change the detector's measurement-quality flags.
    db.commit()
    db.refresh(event)
    return format_event_response(event)
