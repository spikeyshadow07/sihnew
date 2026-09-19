import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import EventModel
from ..models.schemas import WhatIfRequest
from ..settings import OUTPUTS_DIR
from risk_engine.simulator import WhatIfSimulator

router = APIRouter(prefix="/api/simulation", tags=["Path replay"])

def event_tracks(event):
    path = OUTPUTS_DIR / "tracks" / f"{event.job_id}.json"
    if not path.is_file():
        raise HTTPException(409, "No measured tracks were saved for this event. Analyze the video again.")
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = json.loads(event.participant_ids)
    start, end = max(0, event.timestamp_start-2), event.timestamp_end+2
    return ids, [{"timestamp": f["timestamp"], "tracks": [t for t in f["tracks"] if t["id"] in ids]}
                 for f in data["frames"] if start <= f["timestamp"] <= end]

@router.post("/run")
def simulate(req: WhatIfRequest, db: Session = Depends(get_db)):
    event = db.get(EventModel, req.event_id)
    if event is None:
        raise HTTPException(404, "Event not found.")
    ids, frames = event_tracks(event)
    try:
        return WhatIfSimulator().simulate_paths(frames, ids, req.modified_participant_id, req.speed_factor, req.delay_seconds)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
