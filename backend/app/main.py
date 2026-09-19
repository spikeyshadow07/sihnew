import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path
import imageio_ffmpeg
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from .settings import ROOT, OUTPUTS_DIR, DATA_DIR, MODEL_PATH
from .database.db import init_db, SessionLocal
from .routes import upload, jobs, events, review, analytics, simulation, realtime
from ai_engine.video_geometry import MAX_SOURCE_DIMENSION, MAX_ANALYSIS_DIMENSION

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="NearGuard · BITHAWK", version="2.0.1", lifespan=lifespan)
for route in (upload, jobs, events, review, analytics, simulation, realtime):
    app.include_router(route.router)
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

@app.get("/api/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    encoder = Path(imageio_ffmpeg.get_ffmpeg_exe()).is_file()
    return {"status": "healthy" if encoder else "degraded", "database": "SQLite", "encoder_available": encoder,
            "yolo_available": MODEL_PATH.is_file() and importlib.util.find_spec("ultralytics") is not None,
            "version": "2.0.1", "max_upload_mb": 150, "max_duration_seconds": 120,
            "max_source_dimension": MAX_SOURCE_DIMENSION, "max_analysis_dimension": MAX_ANALYSIS_DIMENSION}

dist = ROOT / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def missing_frontend():
        return "<h1>NearGuard backend is running</h1><p>Build the frontend with npm ci and npm run build, then restart.</p>"
