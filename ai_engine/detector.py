"""Motion baseline or optional pretrained YOLO. Modes never silently substitute."""
import cv2

class RoadUserDetector:
    def __init__(self, mode="motion", model_path=None, min_area=250, confidence_threshold=.35):
        self.mode, self.model, self.frames_seen = mode, None, 0
        self.min_area, self.confidence_threshold = min_area, confidence_threshold
        if mode == "yolo":
            from pathlib import Path
            if not model_path or not Path(model_path).is_file():
                raise ValueError("YOLO weights are missing. See README: optional trained detector.")
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ValueError("Install requirements-ai.txt before selecting YOLO.") from exc
            self.model = YOLO(str(model_path))
        elif mode == "motion":
            self.bg = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=32, detectShadows=True)
            self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        else:
            raise ValueError("Unknown detector mode.")

    def detect(self, frame, roi_mask=None):
        height, width = frame.shape[:2]
        if self.model is not None:
            result = self.model.predict(frame, conf=self.confidence_threshold, classes=[0, 1, 2, 3, 5, 7], verbose=False)[0]
            names = {0: "pedestrian", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
            detections = []
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append({"class": names[int(box.cls.item())], "bbox": [x1, y1, x2-x1, y2-y1],
                                   "center": [(x1+x2)/2, (y1+y2)/2], "confidence": float(box.conf.item())})
            return detections
        foreground = self.bg.apply(frame)
        self.frames_seen += 1
        if self.frames_seen <= 15:
            return []
        _, mask = cv2.threshold(foreground, 200, 255, cv2.THRESH_BINARY)
        if roi_mask is not None:
            mask = cv2.bitwise_and(mask, roi_mask)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for contour in contours:
            if not self.min_area <= cv2.contourArea(contour) <= width * height * .12:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if min(w, h) >= 8:
                # Motion cannot identify a category; 0.5 is a heuristic quality marker.
                detections.append({"class": "unknown", "bbox": [x, y, w, h],
                                   "center": [x+w/2, y+h/2], "confidence": .5})
        return detections
