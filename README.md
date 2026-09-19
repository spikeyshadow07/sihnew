# NearGuard AI 

**Tagline:** See the risks. Prevent the accidents.

NearGuard AI is an AI-powered urban traffic near-miss detection and road-safety intelligence platform. It turns ordinary traffic video into proactive road-safety intelligence. 

## The Problem
Urban traffic accidents often appear random, but they are typically preceded by numerous "near-miss" interactions. Traditional traffic analysis relies on crash data, which is inherently reactive—somebody must get hurt before a dangerous junction is identified.

## The Solution
NearGuard AI solves this by analyzing real traffic CCTV footage to automatically detect, track, and analyze near-miss events (conflicts) before crashes happen. It calculates precise safety metrics (like TTC and PET), verifies evidence, and maps the data to real-world hotspots, empowering authorities to proactively implement safety interventions.

## Primary Differentiators
1. **Dual Score (Risk Severity vs. Evidence Confidence):** Clearly separates the algorithmic danger score from the AI's tracking confidence.
2. **Dynamic Conflict Graph:** Intelligently filters out safe parallel movement, focusing only on converging trajectories.
3. **Evidence Capsule:** Automatically clips the 10-second video proof of every detected event for human verification.
4. **Exposure-Normalized Hotspots:** Calculates near-misses per 1000 road users, preventing busy roads from falsely appearing more dangerous.
5. **Counterfactual Safety Twin:** An interactive simulation tab that lets you test "what-if" scenarios (e.g., "What if the car was moving 10 km/h slower?").

## Architecture & Tech Stack
- **Frontend**: React, Vite, Tailwind CSS, Recharts, React-Leaflet
- **Backend**: Python, FastAPI, Uvicorn, SQLite/PostgreSQL
- **Computer Vision**: OpenCV, Ultralytics YOLO (Object Detection), ByteTrack (Object Tracking)
- **Data Analytics**: NumPy, Math

## Installation & Local Setup

### 1. Backend Setup
Navigate to the `backend` directory, create a virtual environment, and install dependencies:
```bash
cd backend
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
Navigate to the `frontend` directory:
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:8000`.

## How It Works

### YOLO Setup & Video Upload
By default, the prototype uses a lightweight motion-based tracker to ensure it runs on any hardware. To enable YOLO object detection (Cars, Motorcycles, Pedestrians), you must download YOLO weights and configure them in the `backend/models` directory. Once configured, upload MP4/MOV traffic videos directly via the **Video Studio**.

### Camera Calibration
Users can click 4 points on the road to map pixel coordinates to real-world metric coordinates (ground-plane). This homography matrix is required to calculate accurate speeds and distances.

### TTC (Time To Collision)
TTC is calculated by assuming both objects continue at a constant velocity. If their projected circular footprints will overlap, the time remaining until that overlap is recorded as the TTC.

### PET (Post Encroachment Time)
PET is the time difference between one vehicle leaving a spatial conflict zone and another vehicle entering it.

### Heatmaps & Hotspots
Detected event ground-coordinates are translated into GPS coordinates. Using Leaflet, these coordinates are mapped to produce an interactive heatmap showing exact danger zones, helping identify recurring hotspots.

### Risk vs Confidence
- **Risk Severity**: A heuristic score (0-100) based on TTC, relative speed, and deceleration.
- **Evidence Confidence**: The reliability of the tracker during the event (factors in track age, YOLO confidence, and temporal consensus). 
- **Reliability Gate**: If a high-risk event has low confidence, it is flagged for manual human review.

## Limitations & Future Improvements
- **Limitations**: The prototype relies on a flat-ground assumption for calibration. Changes in elevation (hills) will skew metric measurements. Real-world speeds are approximations.
- **Future Improvements**: Integration with real-time RTSP streams, native database migration to PostgreSQL/Supabase, and advanced DBSCAN hotspot clustering logic for city-wide maps.
