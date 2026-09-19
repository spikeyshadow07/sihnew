"""Start the packaged local app. No Node.js needed for the supplied build."""
import importlib.util
import sqlite3
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def main():
    missing = [name for name in ("fastapi", "uvicorn", "sqlalchemy", "cv2", "numpy", "imageio_ffmpeg")
               if importlib.util.find_spec(name) is None]
    if missing:
        raise SystemExit("Missing dependencies: " + ", ".join(missing) + ". Run INSTALL_WINDOWS.bat first.")
    if not (ROOT/"frontend"/"dist"/"index.html").is_file():
        raise SystemExit("Frontend build missing. In frontend, run npm ci and npm run build.")
    from backend.app.settings import DB_PATH
    if DB_PATH.exists():
        try:
            with sqlite3.connect(DB_PATH) as database:
                result = database.execute("PRAGMA quick_check").fetchone()
            if result != ("ok",):
                raise sqlite3.DatabaseError("Integrity check failed.")
        except sqlite3.DatabaseError as exc:
            raise SystemExit("The existing database is unreadable. Preserve it and use a newly extracted copy of this project. No data was deleted.") from exc
    import uvicorn
    import webview
    import time

    print("NearGuard by BITHAWK")
    print("Starting Desktop Application...")
    print("Press Ctrl+C to stop in this console if the window is closed.")
    
    def start_server():
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    time.sleep(1.5) # Give uvicorn a moment to bind to the port
    
    webview.create_window('NearGuard AI Command Center', 'http://127.0.0.1:8000', width=1280, height=800)
    webview.start()
if __name__ == "__main__":
    main()
