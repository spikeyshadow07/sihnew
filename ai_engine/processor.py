import cv2
import os
from .detector import RoadUserDetector
from .tracker import MultiObjectTracker
from .calibration import CameraCalibration
from .trajectory import TrajectoryAnalyzer
from .video_geometry import analysis_resolution

class VideoProcessor:
    def __init__(self, camera_config_path=None, camera_config=None, detector_mode="motion", model_path=None):
        self.calibration = CameraCalibration(camera_config_path, camera_config)
        self.detector = RoadUserDetector(mode=detector_mode, model_path=model_path)
        self.tracker = MultiObjectTracker()
        self.trajectory_analyzer = TrajectoryAnalyzer()

    def process_video(self, video_path, output_annotated_path=None, progress_callback=None, max_frames=None):
        cap, writer, frames = cv2.VideoCapture(str(video_path)), None, []
        try:
            if not cap.isOpened():
                raise ValueError("This video could not be decoded.")
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if not 1 <= fps <= 120 or min(width, height) < 16:
                raise ValueError("Unsupported dimensions or frame rate (1–120 fps required).")
            self.calibration.validate_resolution(width, height)
            source_resolution = {"width": width, "height": height}
            processed_resolution = analysis_resolution(width, height)
            source_width, source_height = width, height
            width, height = processed_resolution["width"], processed_resolution["height"]
            scale_x, scale_y = width/source_width, height/source_height
            if output_annotated_path:
                os.makedirs(os.path.dirname(output_annotated_path), exist_ok=True)
                writer = cv2.VideoWriter(str(output_annotated_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
                if not writer.isOpened():
                    raise RuntimeError("Could not create the annotated video.")
            index = 0
            while max_frames is None or index < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                if index >= 14400:
                    raise ValueError("Video exceeds the 14,400-frame prototype limit.")
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                timestamp = index / fps
                active = self.tracker.update(self.detector.detect(frame), index, timestamp)
                entries = []
                for track in active:
                    u, v = track.cx, track.bbox[1] + track.bbox[3]
                    # Calibration points come from the original uploaded frame.
                    # Map the resized detection back before computing metres.
                    source_u, source_v = u/scale_x, v/scale_y
                    ground, kin = None, None
                    if self.calibration.contains(source_u, source_v):
                        gx, gy = self.calibration.pixel_to_ground(source_u, source_v)
                        self.trajectory_analyzer.add_point(track.track_id, timestamp, gx, gy)
                        ground = [gx, gy]
                        kin = self.trajectory_analyzer.compute_kinematics(track.track_id)
                    entries.append({"id": track.track_id, "class": track.cls_name, "bbox": track.bbox,
                        "center": [track.cx, track.cy], "contact_pixel": [u, v], "ground_coords": ground,
                        "source_contact_pixel": [source_u, source_v],
                        "confidence": float(track.confidence), "track_reliability": int(track.reliability),
                        "velocity_valid": bool(kin and kin["velocity_valid"]),
                        "speed_kmh": kin["speed_kmh"] if kin else None,
                        "velocity": kin["velocity"] if kin else None, "heading_deg": kin["heading_deg"] if kin else None})
                    if writer is not None:
                        x, y, w, h = map(int, track.bbox)
                        
                        # Select professional, muted colors based on class
                        color_map = {
                            "car": (246, 130, 59),        # Blue (BGR)
                            "motorcycle": (11, 158, 245), # Amber
                            "pedestrian": (238, 211, 34), # Cyan
                            "bicycle": (168, 85, 247),    # Purple
                            "bus": (94, 197, 34),         # Green
                            "truck": (139, 116, 100)      # Slate
                        }
                        color = color_map.get(track.cls_name.lower(), (255, 255, 255))
                        
                        # Thin bounding box
                        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 1)
                        
                        # Prepare label
                        speed = f" {kin['speed_kmh']:.0f}km/h" if kin and kin["velocity_valid"] else ""
                        label = f"#{track.track_id} {track.cls_name}{speed}"
                        
                        # Draw semi-transparent dark tag
                        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                        tag_x, tag_y = x, max(20, y - label_h - 10)
                        
                        # Create overlay for transparency
                        overlay = frame.copy()
                        cv2.rectangle(overlay, (tag_x, tag_y), (tag_x + label_w + 6, tag_y + label_h + 8), (15, 23, 31), -1) # Dark navy background
                        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                        
                        cv2.putText(frame, label, (tag_x + 3, tag_y + label_h + 4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (248, 250, 252), 1) # White text

                frames.append({"frame_id": index, "timestamp": timestamp, "tracks": entries})
                if writer is not None:
                    # Top-left clean badge
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (12, 12), (300, 40), (15, 23, 31), -1)
                    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                    cv2.putText(frame, f"NearGuard AI | {self.detector.mode.upper()} | {timestamp:.1f}s", (18, 28),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    writer.write(frame)
                index += 1
                if progress_callback and index % 30 == 0:
                    progress_callback(min(100, 100*index/max(total, 1)), f"Tracking frame {index}/{total}")
            if not frames:
                raise ValueError("No readable frames were found.")
            return {"video_id": os.path.basename(video_path), "fps": fps, "resolution": {"width": width, "height": height},
                    "source_resolution": source_resolution, "pixel_scale": [scale_x, scale_y],
                    "calibrated": self.calibration.calibrated, "detector_mode": self.detector.mode, "frames": frames}
        finally:
            cap.release()
            if writer is not None:
                writer.release()
