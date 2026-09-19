"""Retimes one measured path. No steering/braking model or collision-avoidance claims."""
import numpy as np

class WhatIfSimulator:
    def simulate_paths(self, frames, participant_ids, modified_participant_id, speed_factor=1., delay_seconds=0.):
        if modified_participant_id not in participant_ids:
            raise ValueError("Select one of this event's participants.")
        if not .25 <= speed_factor <= 1.5 or not 0 <= delay_seconds <= 1:
            raise ValueError("Speed factor must be 0.25–1.5 and delay 0–1 seconds.")
        paths = {}
        for participant in participant_ids:
            rows = [(f["timestamp"], *t["ground_coords"]) for f in frames for t in f["tracks"]
                    if t["id"] == participant and t.get("ground_coords") is not None]
            if len(rows) < 5:
                raise ValueError("Not enough measured positions for this replay.")
            paths[participant] = np.asarray(rows)
        start = max(p[0, 0] for p in paths.values())
        end = min(p[-1, 0] for p in paths.values())
        if end-start < .3:
            raise ValueError("Participants have insufficient overlapping track time.")
        def interpolate(path, time):
            if time < path[0, 0] or time > path[-1, 0]:
                return None
            index = int(np.searchsorted(path[:, 0], time))
            if 0 < index < len(path) and path[index, 0]-path[index-1, 0] > .25:
                return None
            return [float(np.interp(time, path[:, 0], path[:, axis])) for axis in (1, 2)]
        samples = []
        for time in np.linspace(start, end, min(240, max(10, int((end-start)*20)))):
            original, simulated = {}, {}
            for participant, path in paths.items():
                original[str(participant)] = interpolate(path, time)
                shifted = start + (time-start-delay_seconds)*speed_factor if participant == modified_participant_id else time
                simulated[str(participant)] = interpolate(path, shifted)
            if any(p is None for p in [*original.values(), *simulated.values()]):
                continue
            samples.append({"timestamp": float(time), "original": original, "simulated": simulated})
        if len(samples) < 5:
            raise ValueError("The change leaves too little shared observed time. Try a smaller change.")
        def separation(sample, key):
            points = list(sample[key].values())
            return float(np.linalg.norm(np.asarray(points[0])-points[1]))
        original_distance = min(separation(s, "original") for s in samples)
        simulated_distance = min(separation(s, "simulated") for s in samples)
        return {"samples": samples, "participant_ids": participant_ids,
            "modified_participant_id": modified_participant_id, "speed_factor": speed_factor,
            "delay_seconds": delay_seconds, "original_min_distance_m": round(original_distance, 3),
            "simulated_min_distance_m": round(simulated_distance, 3),
            "distance_change_m": round(simulated_distance-original_distance, 3),
            "compared_interval": [samples[0]["timestamp"], samples[-1]["timestamp"]],
            "assumptions": "One observed path is retimed; the other stays unchanged. Both distances use the same supported time samples. No extrapolation, new steering, braking response or crash prediction."}
