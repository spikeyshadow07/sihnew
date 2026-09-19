import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("NEARGUARD_DATA_DIR", ROOT / "data"))
OUTPUTS_DIR = Path(os.getenv("NEARGUARD_OUTPUTS_DIR", ROOT / "outputs"))
DB_PATH = Path(os.getenv("NEARGUARD_DB_PATH", ROOT / "nearguard.db"))
MODEL_PATH = Path(os.getenv("NEARGUARD_MODEL_PATH", ROOT / "models" / "yolo11n.pt"))
MAX_UPLOAD_BYTES = 150 * 1024 * 1024
MAX_DURATION_SECONDS = 120
for directory in (DATA_DIR / "uploads", OUTPUTS_DIR / "clips", OUTPUTS_DIR / "annotated", OUTPUTS_DIR / "tracks", OUTPUTS_DIR / "frames"):
    directory.mkdir(parents=True, exist_ok=True)
