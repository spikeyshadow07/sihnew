# Validation report — NearGuard BITHAWK v2.0.1

Date: 2026-09-16

## Completed checks

- Python compilation of active backend, AI and risk modules.
- 40 automated tests passed (pytest; Python 3.12, Linux).
- Actual 3840 × 2160 MP4 upload accepted and processed into 1920 × 1080 evidence and preview.
- Landscape, portrait, DCI 4K, HD and near-limit resizing dimensions verified.
- Calibration test confirms resized detections map back to the original ground coordinates.
- Oversized (8K) and invalid source dimensions remain rejected with clear limits.
- React/Vite production build passed.
- End-to-end API processing of the bundled intersection demo: saved measured tracks, completed job, computed candidates and decodable annotated video.
- HTTP retrieval/range access for annotated media.
- A calibrated blank uploaded video returns zero candidates without loading preset incidents.
- An uncalibrated uploaded video produces tracks without metric estimates or candidate events.
- Missing/invalid upload rejection and invalid demo path rejection.
- Calibration roundtrip, degenerate/bow-tie/non-finite point rejection and resolution mismatch rejection.
- Tracking disappearance and velocity-history reset after a gap.
- Approaching-pair TTC, safe lateral pass, stationary/equal-velocity pairs and separate encounter splitting.
- Review persistence and latest-decision selection; review does not remove measurement uncertainty.
- CSV output contains saved review notes.
- Measured-track replay returns identical positions/separation with unchanged parameters.
- Retimed replay preserves the other participant; missing tracks and invalid participant are rejected.

## Not established

- Browser visual/interaction verification: the provided browser service blocked access to the local app; no visual pass is claimed.
- Windows launcher execution: supplied but not executable in the Linux test environment.
- Optional YOLO inference: adapter provided, but package/weights were not installed or evaluated.
- Real-road detection precision/recall, measurement accuracy, night/rain performance and processing speed on your laptop.
- The specific Pixabay clip in the user's screenshot was not supplied; the resolution fix was tested with a generated 4K MP4.
- Live-camera operation, production security, PET computation, or reliable crash prevention.

The automatic tests validate software behavior, not real-world road-safety accuracy. Deprecation warnings from installed dependencies were non-fatal.

## Before the hackathon presentation

1. Extract into a new folder, run the Windows installer, then the launcher.
2. Run the intersection demo and check all six navigation screens.
3. Play an evidence clip, save a review, reload and verify it remains saved.
4. Run no-op replay, then a small timing change.
5. Export CSV and annotated video.
6. Test your own authorized clip with known calibration.
7. Present baseline vs optional YOLO and measured vs estimated values accurately.
