"""Explicit planar calibration. No calibration means no metric estimates."""
import json
import cv2
import numpy as np

class CameraCalibration:
    def __init__(self, config_path=None, config=None):
        self.H = self.H_inv = None
        self.road_zones = []
        self.config = config
        self.source_points = None
        if config_path:
            with open(config_path, encoding="utf-8") as f:
                self.config = json.load(f)
        if self.config:
            calibration = self.config.get("calibration", {})
            self.set_calibration_points(calibration.get("source_pixel_points"), calibration.get("dest_ground_points"))
            self.road_zones = self.config.get("road_zones", [])

    @property
    def calibrated(self):
        return self.H is not None

    def set_calibration_points(self, src_pts, dst_pts):
        src, dst = np.asarray(src_pts, dtype=np.float64), np.asarray(dst_pts, dtype=np.float64)
        if src.shape != (4, 2) or dst.shape != (4, 2):
            raise ValueError("Calibration needs four matching pixel and ground points.")
        if not np.isfinite(src).all() or not np.isfinite(dst).all():
            raise ValueError("Calibration points must be finite numbers.")
        for points in (src, dst):
            contour = points.astype(np.float32)
            if not cv2.isContourConvex(contour) or abs(cv2.contourArea(contour)) < .01:
                raise ValueError("Select four corners in order around a non-flat road rectangle.")
        self.H, _ = cv2.findHomography(src, dst, 0)
        if self.H is None or not np.isfinite(self.H).all() or abs(np.linalg.det(self.H)) < 1e-12:
            raise ValueError("These points cannot form a valid ground mapping.")
        self.H_inv = np.linalg.inv(self.H)
        self.source_points = src.astype(np.float32)

    def validate_resolution(self, width, height):
        if not self.calibrated:
            return
        resolution = self.config.get("resolution", {})
        if resolution.get("width") != width or resolution.get("height") != height:
            raise ValueError("Calibration resolution does not match this video. Select its corners again.")
        if (self.source_points < 0).any() or (self.source_points[:, 0] > width).any() or (self.source_points[:, 1] > height).any():
            raise ValueError("Calibration points must be inside the video frame.")

    def contains(self, u, v):
        return self.calibrated and cv2.pointPolygonTest(self.source_points, (float(u), float(v)), False) >= 0

    def pixel_to_ground(self, u, v):
        if not self.calibrated:
            raise ValueError("Ground measurements require camera calibration.")
        if abs(self.H[2, 0]*u + self.H[2, 1]*v + self.H[2, 2]) < 1e-9:
            raise ValueError("Point is too close to the calibration horizon.")
        p = cv2.perspectiveTransform(np.array([[[u, v]]], dtype=np.float64), self.H)[0, 0]
        return float(p[0]), float(p[1])

    def ground_to_pixel(self, x_m, y_m):
        if not self.calibrated:
            raise ValueError("Ground measurements require camera calibration.")
        p = cv2.perspectiveTransform(np.array([[[x_m, y_m]]], dtype=np.float64), self.H_inv)[0, 0]
        return int(round(p[0])), int(round(p[1]))

    def compute_ground_distance(self, p1, p2):
        return float(np.linalg.norm(np.asarray(p1) - np.asarray(p2)))
