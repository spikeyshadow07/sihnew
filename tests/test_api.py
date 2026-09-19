import json
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from backend.app.services.job_worker import worker

def test_health_and_empty_database(client):
    assert client.get("/api/health").json()["status"] == "healthy"
    assert client.get("/api/events").json() == []

def test_missing_upload_does_not_start_demo(client):
    assert client.post("/api/upload").status_code == 400

def test_invalid_video_is_rejected(client):
    assert client.post("/api/upload",files={"file":("fake.mp4",b"not a video","video/mp4")}).status_code == 400

def test_unknown_demo_cannot_read_arbitrary_path(client):
    assert client.post("/api/upload",data={"use_demo":"true","scenario":"../../README.md"}).status_code == 400

def test_invalid_review_decision_is_rejected(client):
    assert client.post("/api/review/no-event",json={"decision":"anything"}).status_code == 422

def test_demo_completes_with_saved_tracks_and_playable_video(client,demo_job):
    assert demo_job["metadata"]["source_type"] == "synthetic_demo"
    assert demo_job["metadata"]["frame_count"] > 0
    assert client.get(demo_job["tracks_url"]).status_code == 200
    response=client.get(demo_job["annotated_url"],headers={"Range":"bytes=0-1023"})
    assert response.status_code in (200,206)
    from backend.app.settings import OUTPUTS_DIR
    capture=cv2.VideoCapture(str(OUTPUTS_DIR/"annotated"/(demo_job["id"]+".mp4")))
    assert capture.read()[0]
    capture.release()

def test_review_persists_and_does_not_relabel_measurement_quality(client,demo_job):
    events=client.get("/api/events",params={"job_id":demo_job["id"]}).json()
    assert events, "Bundled intersection demo should produce computed candidates with this baseline."
    event=events[0]
    assert event["surrogate_measures"]["pet"] is None
    response=client.post("/api/review/"+event["id"],json={"decision":"approved","notes":"Test review"})
    assert response.status_code == 200
    saved=client.get("/api/events/"+event["id"]).json()
    assert saved["human_review"]["decision"] == "approved"
    assert saved["quality_check"]["status"] == "uncertain"
    queue=client.get("/api/review/queue",params={"job_id":demo_job["id"]}).json()
    assert event["id"] not in [e["id"] for e in queue]
    assert client.post("/api/review/"+event["id"],json={"decision":"rejected","notes":"Updated review"}).status_code == 200
    assert client.get("/api/events/"+event["id"]).json()["human_review"]["decision"] == "rejected"
    export=client.get("/api/events/export.csv",params={"job_id":demo_job["id"]})
    assert export.status_code == 200 and "Updated review" in export.text

def test_real_track_replay_no_change(client,demo_job):
    events=client.get("/api/events",params={"job_id":demo_job["id"]}).json()
    for event in events:
        response=client.post("/api/simulation/run",json={"event_id":event["id"],
            "modified_participant_id":event["participant_ids"][0],"speed_factor":1,"delay_seconds":0})
        if response.status_code == 200:
            assert response.json()["distance_change_m"] == 0
            return
    raise AssertionError("No computed demo candidate had sufficient measured tracks for replay.")

def test_blank_uploaded_video_has_zero_candidates(client,tmp_path):
    path=tmp_path/"blank.mp4"
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"mp4v"),20,(320,240))
    for _ in range(50):
        writer.write(np.full((240,320,3),80,dtype=np.uint8))
    writer.release()
    calibration={"resolution":{"width":320,"height":240},"calibration":{
        "source_pixel_points":[[0,0],[320,0],[320,240],[0,240]],
        "dest_ground_points":[[0,0],[32,0],[32,24],[0,24]]}}
    with patch.object(worker,"process_job_async",side_effect=worker._run_job_pipeline):
        response=client.post("/api/upload",files={"file":("../blank.mp4",path.read_bytes(),"video/mp4")},
            data={"calibration_json":json.dumps(calibration)})
    assert response.status_code == 202,response.text
    job=client.get("/api/jobs/"+response.json()["id"]).json()
    assert job["status"] == "completed",job
    assert job["total_events"] == 0
    assert job["video_name"] == "blank.mp4"
    assert client.get("/api/events",params={"job_id":job["id"]}).json() == []

def test_custom_video_without_calibration_is_tracking_only(client,tmp_path):
    path=tmp_path/"uncalibrated.mp4"
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"mp4v"),20,(320,240))
    for i in range(50):
        frame=np.full((240,320,3),50,dtype=np.uint8)
        cv2.rectangle(frame,(i*3,100),(i*3+25,140),(0,255,0),-1)
        writer.write(frame)
    writer.release()
    with patch.object(worker,"process_job_async",side_effect=worker._run_job_pipeline):
        response=client.post("/api/upload",files={"file":("uncalibrated.mp4",path.read_bytes(),"video/mp4")})
    assert response.status_code == 202,response.text
    job=client.get("/api/jobs/"+response.json()["id"]).json()
    assert job["status"] == "completed",job
    assert job["metadata"]["camera_config"] is None
    assert job["total_events"] == 0
    data=client.get(job["tracks_url"]).json()
    assert all(t["ground_coords"] is None for f in data["frames"] for t in f["tracks"])
