from collections import defaultdict, deque
import numpy as np
import math

class TrajectoryAnalyzer:
    def __init__(self, fps=30.0):
        self.fps, self.dt = fps, 1 / fps
        self.history = defaultdict(lambda: deque(maxlen=90))

    def add_point(self, track_id, timestamp, x, y):
        history = self.history[track_id]
        if history and timestamp - history[-1][0] > .25:
            history.clear()
        history.append((timestamp, x, y))

    def compute_kinematics(self, track_id):
        points = np.array(list(self.history[track_id])[-10:], dtype=float)
        if len(points) < 5 or points[-1, 0] - points[0, 0] < .1:
            return {"speed_kmh": 0., "acceleration_mps2": 0., "heading_deg": 0.,
                    "velocity": [0., 0.], "velocity_valid": False}
        t = points[:, 0] - points[:, 0].mean()
        velocity = np.sum(t[:, None] * points[:, 1:], axis=0) / np.sum(t*t)
        acceleration = 0.
        if len(points) >= 8:
            mid = len(points)//2
            v1 = (points[mid-1, 1:] - points[0, 1:]) / (points[mid-1, 0] - points[0, 0])
            v2 = (points[-1, 1:] - points[mid, 1:]) / (points[-1, 0] - points[mid, 0])
            dt = points[mid:, 0].mean() - points[:mid, 0].mean()
            acceleration = (np.linalg.norm(v2)-np.linalg.norm(v1))/dt
        return {"speed_kmh": float(np.linalg.norm(velocity)*3.6), "acceleration_mps2": float(acceleration),
                "heading_deg": math.degrees(math.atan2(velocity[1], velocity[0])),
                "velocity": velocity.tolist(), "velocity_valid": True}

    def detect_braking(self, track_id, threshold_mps2=-2.5):
        return self.compute_kinematics(track_id)["acceleration_mps2"] < threshold_mps2
