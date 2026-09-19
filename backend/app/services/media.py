import os
import subprocess
from pathlib import Path
import imageio_ffmpeg

def make_browser_video(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.stem + ".encoding.mp4")
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(source), "-an",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
               "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(temporary)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=240)
        if temporary.stat().st_size < 100:
            raise ValueError("Video encoding produced an empty output.")
        os.replace(temporary, destination)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("FFmpeg could not encode the video. Check the input codec and free disk space.") from exc
    finally:
        temporary.unlink(missing_ok=True)
