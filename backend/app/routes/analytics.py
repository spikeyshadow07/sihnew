from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import EventModel, JobModel
from .events import latest_review

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/summary")
def summary(job_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(EventModel).join(JobModel).filter(JobModel.status == "completed")
    if job_id:
        query = query.filter(EventModel.job_id == job_id)
    events = query.all()
    approved = [e for e in events if latest_review(e) and latest_review(e).decision == "approved"]
    rejected = [e for e in events if latest_review(e) and latest_review(e).decision == "rejected"]
    included = [e for e in events if e not in rejected]
    bins = Counter(int(e.timestamp_peak//5)*5 for e in included)
    return {"total_events": len(events), "approved_events": len(approved), "rejected_events": len(rejected),
            "pending_reviews": sum(not e.reviews for e in events),
            "high_critical_count": sum(e.risk_level in ("high", "critical") for e in included),
            "risk_level_distribution": dict(Counter(e.risk_level for e in included)),
            "conflicts_by_type": dict(Counter(e.conflict_type for e in included)),
            "video_time_bins": [{"start_seconds": start, "count": count} for start, count in sorted(bins.items())],
            "note": "Candidate counts are not traffic-normalized collision rates. Rejected events are excluded from distributions."}
