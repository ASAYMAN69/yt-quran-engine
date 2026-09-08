"""Video composer using FFmpeg to render vertical reels with burned subtitles."""

import subprocess
from pathlib import Path
from typing import Optional


class VideoComposer:
    """Renders final MP4 video with background, audio, and burned ASS subtitles."""

    def __init__(self, fonts_dir: str = "assets/fonts"):
        self.fonts_dir = Path(fonts_dir).resolve()

    def render_reel(
        self,
        audio_path: Path,
        ass_subtitles_path: Path,
        output_mp4_path: Path,
        duration: float,
        bg_video_path: Optional[Path] = None,
    ) -> Path:
        """Renders 1080x1920 vertical video."""
        output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        subtitles_str = str(ass_subtitles_path.resolve()).replace(":", r"\:").replace("\\", "/")
        fonts_dir_str = str(self.fonts_dir).replace(":", r"\:").replace("\\", "/")

        if bg_video_path and bg_video_path.exists():
            # Use custom background video in loop
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                f"boxblur=20:5,format=yuv420p,"
                f"ass='{subtitles_str}':fontsdir='{fonts_dir_str}'[outv]"
            )
            input_args = [
                "-stream_loop", "-1",
                "-i", str(bg_video_path.resolve()),
                "-i", str(audio_path.resolve()),
            ]
        else:
            # Generate high-aesthetic deep obsidian animated background
            # Subtle moving wave gradient
            filter_complex = (
                f"gradients=s=1080x1920:d={duration}:c0=0x080E1A:c1=0x1E293B:c2=0x0F172A:c3=0x020617:r=25:type=radial:x0=540:y0=960:radius=800,"
                f"format=yuv420p,"
                f"ass='{subtitles_str}':fontsdir='{fonts_dir_str}'[outv]"
            )
            input_args = [
                "-f", "lavfi",
                "-i", f"nullsrc=s=1080x1920:d={duration}:r=30",
                "-i", str(audio_path.resolve()),
            ]

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-t", str(round(duration, 2)),
            str(output_mp4_path.resolve()),
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback if 'gradients' filter not compiled in lavfi: use testsrc / color gradient
            fallback_filter = (
                f"color=c=0x0B1120:s=1080x1920:d={duration}:r=30,"
                f"format=yuv420p,"
                f"ass='{subtitles_str}':fontsdir='{fonts_dir_str}'[outv]"
            )
            ffmpeg_cmd[ffmpeg_cmd.index("-filter_complex") + 1] = fallback_filter
            result2 = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result2.returncode != 0:
                raise RuntimeError(f"FFmpeg rendering failed:\n{result2.stderr}")

        return output_mp4_path
