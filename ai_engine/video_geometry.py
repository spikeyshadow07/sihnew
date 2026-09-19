"""Shared limits and mapping for upload previews and analysis frames."""
MAX_SOURCE_DIMENSION = 4096
MAX_ANALYSIS_DIMENSION = 1920

def analysis_resolution(width, height):
    if min(width, height) < 16 or max(width, height) > MAX_SOURCE_DIMENSION:
        raise ValueError(
            f"Video is {width} × {height} pixels. Use a video with each side between "
            f"16 and {MAX_SOURCE_DIMENSION} pixels; export larger footage at 1080p."
        )
    if max(width, height) <= MAX_ANALYSIS_DIMENSION:
        return {"width": width, "height": height}
    scale = MAX_ANALYSIS_DIMENSION / max(width, height)
    # Even dimensions keep H.264 output compatible. No cropping or upscaling.
    return {"width": max(2, int(width * scale) // 2 * 2),
            "height": max(2, int(height * scale) // 2 * 2)}
