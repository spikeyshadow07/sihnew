import numpy as np
import pytest
from ai_engine.calibration import CameraCalibration
from ai_engine.trajectory import TrajectoryAnalyzer
from ai_engine.tracker import MultiObjectTracker

def configuration():
    return {"resolution": {"width": 100, "height": 100}, "calibration": {
        "source_pixel_points": [[0,0],[100,0],[100,100],[0,100]],
        "dest_ground_points": [[0,0],[10,0],[10,10],[0,10]]}}

def test_uncalibrated_does_not_invent_metres():
    with pytest.raises(ValueError):
        CameraCalibration().pixel_to_ground(50,50)

def test_calibration_roundtrip():
    calibration = CameraCalibration(config=configuration())
    assert calibration.pixel_to_ground(50,50) == pytest.approx((5,5))
    assert calibration.ground_to_pixel(5,5) == (50,50)

def test_wrong_resolution_is_rejected():
    with pytest.raises(ValueError):
        CameraCalibration(config=configuration()).validate_resolution(200,100)

@pytest.mark.parametrize("points", [
    [[0,0],[1,1],[2,2],[3,3]],
    [[0,0],[100,100],[100,0],[0,100]],
    [[0,0],[float("nan"),0],[100,100],[0,100]]
])
def test_invalid_calibration(points):
    config = configuration()
    config["calibration"]["source_pixel_points"] = points
    with pytest.raises(ValueError):
        CameraCalibration(config=config)

def test_speed_uses_actual_time():
    trajectory = TrajectoryAnalyzer()
    for i in range(12):
        trajectory.add_point(1,i/30,i/30*10,0)
    assert trajectory.compute_kinematics(1)["speed_kmh"] == pytest.approx(36)

def test_gap_resets_velocity_history():
    trajectory = TrajectoryAnalyzer()
    for i in range(12):
        trajectory.add_point(1,i/30,i/30*10,0)
    trajectory.add_point(1,2,20,0)
    assert not trajectory.compute_kinematics(1)["velocity_valid"]

def test_missing_detection_is_not_a_visible_track():
    tracker = MultiObjectTracker()
    for i in range(6):
        visible = tracker.update([{"class":"unknown","bbox":[i*2,10,30,30],"center":[i*2+15,25],"confidence":.5}],i,i/30)
    assert len(visible) == 1
    assert tracker.update([],7,7/30) == []
