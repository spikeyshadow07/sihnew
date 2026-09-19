import numpy as np
from typing import List, Dict, Any, Optional

def compute_iou(boxA: List[float], boxB: List[float]) -> float:
    """Compute Intersection over Union between boxA [x, y, w, h] and boxB [x, y, w, h]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    
    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return float(iou)

class Track:
    def __init__(self, track_id: int, detection: Dict[str, Any], frame_id: int, timestamp: float):
        self.track_id = track_id
        self.cls_name = detection["class"]
        self.bbox = list(detection["bbox"]) # [x, y, w, h]
        self.center = list(detection["center"]) # [cx, cy]
        self.confidence = detection["confidence"]
        self.class_history = [self.cls_name]
        self.reliability = 100
        
        # State estimation [cx, cy, vx, vy]
        self.cx = float(self.center[0])
        self.cy = float(self.center[1])
        self.vx = 0.0
        self.vy = 0.0
        self.last_observed_center = (self.cx, self.cy)
        self.last_observed_frame = frame_id
        
        self.history = [] # list of (frame_id, timestamp, center, bbox, ground_coord)
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self.confirmed = False
        
    def predict(self):
        """Predict next position based on velocity."""
        self.cx += self.vx
        self.cy += self.vy
        self.bbox[0] = self.cx - self.bbox[2] / 2
        self.bbox[1] = self.cy - self.bbox[3] / 2
        self.center = [int(self.cx), int(self.cy)]
        self.age += 1
        self.time_since_update += 1

    def update(self, detection: Dict[str, Any], frame_id: int, timestamp: float):
        """Update track with new matching detection."""
        new_bbox = detection["bbox"]
        new_cx = detection["center"][0]
        new_cy = detection["center"][1]
        
        # Smooth velocity estimation
        elapsed = max(1, frame_id - self.last_observed_frame)
        self.vx = 0.6 * self.vx + 0.4 * (new_cx - self.last_observed_center[0]) / elapsed
        self.vy = 0.6 * self.vy + 0.4 * (new_cy - self.last_observed_center[1]) / elapsed
        self.last_observed_center = (new_cx, new_cy)
        self.last_observed_frame = frame_id
        
        self.cx = float(new_cx)
        self.cy = float(new_cy)
        self.bbox = list(new_bbox)
        self.center = [int(self.cx), int(self.cy)]
        self.confidence = 0.7 * self.confidence + 0.3 * detection["confidence"]
        
        # Temporal Consensus
        self.class_history.append(detection["class"])
        if len(self.class_history) > 10:
            self.class_history.pop(0)
        self.cls_name = max(set(self.class_history), key=self.class_history.count)
        
        self.hits += 1
        self.time_since_update = 0
        if self.hits >= 3:
            self.confirmed = True
        
        # Track Reliability
        self.reliability = min(100, max(0, int((self.hits / max(1, self.age)) * self.confidence * 100)))

class MultiObjectTracker:
    """
    SORT-style tracker maintaining continuous object identities across frames.
    """
    def __init__(self, max_age: int = 15, iou_threshold: float = 0.25):
        self.max_age = max_age
        self.iou_threshold = iou_threshold
        self.tracks: List[Track] = []
        self.next_id = 1

    def update(self, detections: List[Dict[str, Any]], frame_id: int, timestamp: float) -> List[Track]:
        # 1. Predict track positions
        for trk in self.tracks:
            trk.predict()
            
        # 2. Match tracks to detections
        unmatched_dets = list(range(len(detections)))
        unmatched_trks = list(range(len(self.tracks)))
        matches = []
        
        if len(self.tracks) > 0 and len(detections) > 0:
            iou_matrix = np.zeros((len(self.tracks), len(detections)), dtype=np.float32)
            for t_idx, trk in enumerate(self.tracks):
                for d_idx, det in enumerate(detections):
                    # Combine IoU and centroid proximity
                    iou = compute_iou(trk.bbox, det["bbox"])
                    dist = np.hypot(trk.cx - det["center"][0], trk.cy - det["center"][1])
                    # Distance score normalized
                    dist_score = max(0.0, 1.0 - (dist / 120.0))
                    iou_matrix[t_idx, d_idx] = 0.7 * iou + 0.3 * dist_score

            # Greedy bipartite matching
            while True:
                max_val = np.max(iou_matrix)
                if max_val < self.iou_threshold:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                matches.append((t_idx, d_idx))
                iou_matrix[t_idx, :] = -1
                iou_matrix[:, d_idx] = -1
                
            matched_trk_indices = {m[0] for m in matches}
            matched_det_indices = {m[1] for m in matches}
            unmatched_trks = [t for t in range(len(self.tracks)) if t not in matched_trk_indices]
            unmatched_dets = [d for d in range(len(detections)) if d not in matched_det_indices]

        # 3. Update matched tracks
        for t_idx, d_idx in matches:
            self.tracks[t_idx].update(detections[d_idx], frame_id, timestamp)

        # 4. Create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            new_track = Track(self.next_id, detections[d_idx], frame_id, timestamp)
            self.next_id += 1
            self.tracks.append(new_track)

        # 5. Filter out dead tracks
        self.tracks = [
            trk for trk in self.tracks 
            if trk.time_since_update <= self.max_age
        ]

        # Return active tracks (confirmed or young active)
        return [trk for trk in self.tracks if trk.confirmed and trk.time_since_update == 0]
