"""Candidate screening using constant-velocity circle TTC, not crash prediction."""
import math
from itertools import combinations
from collections import defaultdict
import numpy as np

CLASS_RADII = {"pedestrian": .4, "bicycle": .8, "cyclist": .8, "motorcycle": .9,
               "car": 1.5, "truck": 2.5, "bus": 2.5, "unknown": 1.0}

def pair_metrics(a, b):
    if a.get("ground_coords") is None or b.get("ground_coords") is None:
        return None
    if not a.get("velocity_valid") or not b.get("velocity_valid"):
        return None
    p = np.asarray(b["ground_coords"]) - np.asarray(a["ground_coords"])
    velocity = np.asarray(b["velocity"]) - np.asarray(a["velocity"])
    distance = float(np.linalg.norm(p))
    radius = CLASS_RADII.get(a["class"], 1.) + CLASS_RADII.get(b["class"], 1.)
    closing = -float(np.dot(p, velocity))/max(distance, .001)
    vv = float(np.dot(velocity, velocity))
    if closing <= .3 or vv < .09:
        return None
    projection = float(np.dot(p, velocity))
    discriminant = projection**2 - vv*(distance**2-radius**2)
    ttc = None
    if distance <= radius:
        ttc = 0.
    elif discriminant >= 0:
        root = (-projection - math.sqrt(discriminant))/vv
        if root >= 0:
            ttc = root
    closest_time = max(0., -projection/vv)
    closest_distance = float(np.linalg.norm(p + velocity*closest_time))
    is_candidate = (ttc is not None and ttc <= 2.5) or (closest_time <= 2.5 and closest_distance <= radius+.5)
    if not is_candidate:
        return None
    difference = abs((a["heading_deg"]-b["heading_deg"]+180)%360-180)
    # DRAC is meaningful here only for approximately same-heading closing traffic.
    drac = closing**2/(2*max(.1, distance-radius)) if difference < 20 and ttc is not None else None
    return {"min_ttc": ttc, "pet": None, "max_drac": drac, "delta_v": math.sqrt(vv)*3.6,
            "min_distance_m": distance, "headings": [a["heading_deg"], b["heading_deg"]]}

class ConflictDetector:
    def detect_conflicts_from_tracks(self, data):
        observations = defaultdict(list)
        for frame in data["frames"]:
            for a, b in combinations(frame["tracks"], 2):
                metrics = pair_metrics(a, b)
                if metrics is not None:
                    key = tuple(sorted((a["id"], b["id"])))
                    observations[key].append({"timestamp": frame["timestamp"], "a": a, "b": b, **metrics})
        events = []
        for pair, rows in observations.items():
            segments = []
            for row in rows:
                if not segments or row["timestamp"] - segments[-1][-1]["timestamp"] > .5:
                    segments.append([])
                segments[-1].append(row)
            for segment in segments:
                if len(segment) < 3 or segment[-1]["timestamp"] - segment[0]["timestamp"] < .1:
                    continue
                peak = min(segment, key=lambda r: (r["min_ttc"] if r["min_ttc"] is not None else 99, r["min_distance_m"]))
                a, b = peak["a"], peak["b"]
                finite_ttc = [r["min_ttc"] for r in segment if r["min_ttc"] is not None]
                drac = [r["max_drac"] for r in segment if r["max_drac"] is not None]
                heading_diff = abs((peak["headings"][0]-peak["headings"][1]+180)%360-180)
                conflict = "following_conflict" if heading_diff < 30 else "opposing_conflict" if heading_diff > 150 else "crossing_conflict"
                events.append({"timestamp_start": segment[0]["timestamp"], "timestamp_peak": peak["timestamp"],
                    "timestamp_end": segment[-1]["timestamp"], "participant_ids": [a["id"], b["id"]],
                    "participant_classes": [a["class"], b["class"]], "conflict_type": conflict,
                    "surrogate_measures": {"min_ttc": min(finite_ttc) if finite_ttc else None, "pet": None,
                        "max_drac": max(drac) if drac else None, "delta_v": max(r["delta_v"] for r in segment),
                        "min_distance_m": min(r["min_distance_m"] for r in segment)},
                    "tracking_confidence": min(a["confidence"], b["confidence"]),
                    "evidence_confidence": int(min(a.get("track_reliability", a["confidence"]*100), b.get("track_reliability", b["confidence"]*100))),
                    "num_frames": len(segment),
                    "location": {"ground_coords": ((np.asarray(a["ground_coords"])+b["ground_coords"])/2).tolist(),
                                 "pixel_coords": ((np.asarray(a["contact_pixel"])+b["contact_pixel"])/2).tolist()}})
        return sorted(events, key=lambda e: e["timestamp_peak"])
