import pytest
from risk_engine.conflict_detector import pair_metrics, ConflictDetector
from risk_engine.risk_score import calculate_near_miss_risk_score

def track(identifier, position, velocity, heading=0):
    return {"id":identifier,"class":"car","ground_coords":position,"velocity":velocity,
            "velocity_valid":True,"heading_deg":heading,"contact_pixel":position,"confidence":.8}

def test_approaching_pair_ttc():
    result = pair_metrics(track(1,[0,0],[10,0]), track(2,[10,0],[-10,0],180))
    assert result["min_ttc"] == pytest.approx(.35)
    assert result["pet"] is None
    assert result["max_drac"] is None

def test_lateral_pass_is_not_a_collision_course():
    assert pair_metrics(track(1,[0,0],[10,0]),track(2,[10,10],[0,0])) is None

def test_stationary_neighbors_are_not_conflicts():
    assert pair_metrics(track(1,[0,0],[0,0]),track(2,[1,0],[0,0])) is None

def test_equal_velocity_neighbors_are_not_conflicts():
    assert pair_metrics(track(1,[0,0],[10,0]),track(2,[1,0],[10,0])) is None

def test_empty_video_has_no_injected_events():
    assert ConflictDetector().detect_conflicts_from_tracks({"frames":[]}) == []

def test_separate_encounters_remain_separate():
    frames=[]
    for start in (0,5):
        for i in range(5):
            frames.append({"timestamp":start+i*.1,"tracks":[track(1,[i,0],[5,0]),track(2,[10-i,0],[-5,0],180)]})
    assert len(ConflictDetector().detect_conflicts_from_tracks({"frames":frames})) == 2

def test_missing_measures_score_without_fabrication():
    result=calculate_near_miss_risk_score(None,None,None,0,100,[])
    assert result["risk_score"] == 0
