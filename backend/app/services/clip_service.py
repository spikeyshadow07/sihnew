import subprocess
from pathlib import Path
import imageio_ffmpeg

class EvidenceClipService:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_clip(self, video_path, event):
        name = event["id"] + ".mp4"
        destination = self.output_dir / name
        start = max(0., event["timestamp_start"]-2.)
        duration = event["timestamp_end"]+2.-start
        try:
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-ss", str(start), "-i", str(video_path),
                            "-t", str(duration), "-an", "-c:v", "libx264", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)],
                           capture_output=True, check=True, timeout=120)
        except (subprocess.SubprocessError, OSError) as exc:
            destination.unlink(missing_ok=True)
            raise RuntimeError("Evidence clip encoding failed.") from exc
        if not destination.is_file() or destination.stat().st_size < 100:
            raise RuntimeError("Evidence clip is empty.")
        return "/outputs/clips/" + name
