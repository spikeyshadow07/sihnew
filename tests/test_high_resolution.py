from unittest.mock import patch
import json
import cv2
import numpy as np
import pytest
from ai_engine.video_geometry import analysis_resolution
from ai_engine.processor import VideoProcessor
from backend.app.services.job_worker import worker

@pytest.mark.parametrize("source,expected", [
    ((3840, 2160), (1920, 1080)),
    ((2160, 3840), (1080, 1920)),
    ((4096, 2160), (1920, 1012)),
    ((1280, 720), (1280, 720)),
    ((1921, 1081), (1920, 1080)),
])
def test_analysis_dimensions(source, expected):
    assert analysis_resolution(*source) == dict(zip(("width", "height"), expected))

@pytest.mark.parametrize("source", [(7680, 4320), (10, 500)])
def test_unsupported_source_size_is_explained(source):
    with pytest.raises(ValueError, match="export larger footage at 1080p"):
        analysis_resolution(*source)

def camera_config(width=3840, height=2160):
    return {"resolution": {"width": width, "height": height}, "calibration": {
        "source_pixel_points": [[0,0], [width,0], [width,height], [0,height]],
        "dest_ground_points": [[0,0], [width*.01,0], [width*.01,height*.01], [0,height*.01]]}}

def test_resized_tracking_preserves_original_calibration(monkeypatch):
    class Capture:
        def __init__(self, path):
            self.index = 0
        def isOpened(self):
            return True
        def get(self, prop):
            return {cv2.CAP_PROP_FPS: 20, cv2.CAP_PROP_FRAME_WIDTH: 3840,
                    cv2.CAP_PROP_FRAME_HEIGHT: 2160, cv2.CAP_PROP_FRAME_COUNT: 8}[prop]
        def read(self):
            self.index += 1
            return (True, np.zeros((2160,3840,3),dtype=np.uint8)) if self.index <= 8 else (False,None)
        def release(self):
            pass
    monkeypatch.setattr(cv2, "VideoCapture", Capture)
    processor = VideoProcessor(camera_config=camera_config())
    seen_shapes = []
    def detect(frame):
        seen_shapes.append(frame.shape)
        return [{"class":"unknown", "confidence":.5, "bbox":[940,500,40,40], "center":[960,520]}]
    monkeypatch.setattr(processor.detector, "detect", detect)
    result = processor.process_video("controlled-4k.mp4")
    assert set(seen_shapes) == {(1080,1920,3)}
    track = result["frames"][-1]["tracks"][0]
    assert track["contact_pixel"] == [960,540]
    assert track["source_contact_pixel"] == [1920,1080]
    assert track["ground_coords"] == pytest.approx([19.2,10.8])
    assert result["resolution"] == {"width":1920,"height":1080}
    assert result["source_resolution"] == {"width":3840,"height":2160}

def test_actual_4k_upload_finishes_with_resized_evidence(client, tmp_path):
    path = tmp_path/"4k.mp4"
    writer = cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"mp4v"),10,(3840,2160))
    assert writer.isOpened()
    frame = np.full((2160,3840,3),70,dtype=np.uint8)
    for _ in range(8):
        writer.write(frame)
    writer.release()
    with patch.object(worker,"process_job_async",side_effect=worker._run_job_pipeline):
        response = client.post("/api/upload",files={"file":("4k.mp4",path.read_bytes(),"video/mp4")})
    assert response.status_code == 202, response.text
    job = client.get("/api/jobs/"+response.json()["id"]).json()
    assert job["status"] == "completed", job
    assert job["metadata"]["resized"] is True
    assert job["metadata"]["source_resolution"] == {"width":3840,"height":2160}
    assert job["metadata"]["resolution"] == {"width":1920,"height":1080}
    assert job["metadata"]["camera_config"] is None
    data = client.get(job["tracks_url"]).json()
    assert data["resolution"] == job["metadata"]["resolution"]
    preview = cv2.imdecode(np.frombuffer(client.get(job["frame_url"]).content,dtype=np.uint8),cv2.IMREAD_COLOR)
    assert preview.shape[:2] == (1080,1920)
    from backend.app.settings import OUTPUTS_DIR
    capture = cv2.VideoCapture(str(OUTPUTS_DIR/"annotated"/(job["id"]+".mp4")))
    assert capture.read()[1].shape[:2] == (1080,1920)
    capture.release()
