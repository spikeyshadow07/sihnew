import pytest
from risk_engine.simulator import WhatIfSimulator

def frames():
    return [{"timestamp":i*.05,"tracks":[
        {"id":1,"ground_coords":[i*.1,0]},
        {"id":2,"ground_coords":[5,i*.1-5]}]} for i in range(101)]

def test_unchanged_replay_is_identical():
    result=WhatIfSimulator().simulate_paths(frames(),[1,2],1,1,0)
    assert result["distance_change_m"] == 0
    assert all(s["original"] == s["simulated"] for s in result["samples"])

def test_replay_keeps_other_participant_unchanged():
    result=WhatIfSimulator().simulate_paths(frames(),[1,2],1,.8,0)
    assert all(s["original"]["2"] == s["simulated"]["2"] for s in result["samples"])
    assert any(s["original"]["1"] != s["simulated"]["1"] for s in result["samples"])

def test_replay_rejects_missing_tracks():
    with pytest.raises(ValueError):
        WhatIfSimulator().simulate_paths([], [1,2], 1)

def test_replay_rejects_foreign_participant():
    with pytest.raises(ValueError):
        WhatIfSimulator().simulate_paths(frames(),[1,2],9)

def test_replay_does_not_claim_crash_avoidance():
    result=WhatIfSimulator().simulate_paths(frames(),[1,2],1,.8,.1)
    assert "collision_avoided" not in result
    assert "simulated_risk_score" not in result
