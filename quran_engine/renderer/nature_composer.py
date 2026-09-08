"""Multi-scene nature video composer synchronizing background visual clips with each verse."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from quran_engine.quran.models import Ayah
from quran_engine.segmentation.models import VideoSegment
from quran_engine.renderer.audio import AudioPipeline
from quran_engine.renderer.subtitles import SubtitleGenerator


class NatureVideoComposer:
    """Generates dynamic multi-scene nature videos where the visual scene switches with every verse."""

    def __init__(self, fonts_dir: str = "assets/fonts", nature_clips_dir: str = "assets/nature_clips"):
        self.fonts_dir = Path(fonts_dir).resolve()
        self.nature_clips_dir = Path(nature_clips_dir).resolve()

    def get_nature_scenes(self, count: int) -> List[Path]:
        """Retrieves available nature images/video clips in cyclic order."""
        available = sorted([
            p for p in self.nature_clips_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".mp4", ".mov"]
        ])
        if not available:
            raise FileNotFoundError(f"No nature clips found in {self.nature_clips_dir}")
        # Repeat/cycle if needed
        scenes = []
        for i in range(count):
            scenes.append(available[i % len(available)])
        return scenes

    def render_multi_scene_video(
        self,
        video_segment: VideoSegment,
        ayahs: List[Ayah],
        audio_path: Path,
        durations: List[float],
        ass_subtitles_path: Path,
        output_mp4_path: Path,
        nature_scenes: Optional[List[Path]] = None,
    ) -> Path:
        """
        Renders a 9:16 vertical video where each verse has its own dynamic animated nature scene.
        """
        output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = output_mp4_path.parent / "temp_scenes"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if not nature_scenes:
            nature_scenes = self.get_nature_scenes(len(ayahs))

        rendered_scene_clips: List[Path] = []
        fps = 30

        print(f"🌲 Generating {len(ayahs)} synchronized nature scene clips with cinematic camera motion...")
        
        # 1. Generate individual animated scene video for each verse
        for idx, (scene_path, dur) in enumerate(zip(nature_scenes, durations), start=1):
            scene_clip_path = temp_dir / f"scene_{idx:02d}.mp4"
            total_frames = int(round(dur * fps))
            
            # Subtle cinematic Ken Burns zoom and dark contrast vignette
            # Alternate zoom in and zoom out for visual variety
            if idx % 2 == 1:
                zoom_filter = (
                    f"zoompan=z='min(zoom+0.0008,1.15)':d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
                )
            else:
                zoom_filter = (
                    f"zoompan=z='max(1.15-0.0008*on,1.0)':d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
                )

            # Darkening filter overlay (35% darkness + contrast) so Quranic text is perfectly readable
            filter_chain = (
                f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                f"{zoom_filter},"
                f"eq=brightness=-0.18:contrast=1.1:saturation=1.15,format=yuv420p"
            )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(scene_path.resolve()),
                "-vf", filter_chain,
                "-t", str(dur),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                str(scene_clip_path.resolve()),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            rendered_scene_clips.append(scene_clip_path)

        # 2. Concatenate the scene video clips
        concat_list = temp_dir / "scenes_concat.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for sc in rendered_scene_clips:
                f.write(f"file '{sc.resolve()}'\n")

        subtitles_str = str(ass_subtitles_path.resolve()).replace(":", r"\:").replace("\\", "/")
        fonts_dir_str = str(self.fonts_dir).replace(":", r"\:").replace("\\", "/")

        print("✨ Burning stylized Quran typography and stitching audio...")
        # 3. Combine visual clips + audio + ASS subtitles into final video
        final_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list.resolve()),
            "-i", str(audio_path.resolve()),
            "-vf", f"ass='{subtitles_str}':fontsdir='{fonts_dir_str}'",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_mp4_path.resolve()),
        ]
        res = subprocess.run(final_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to render nature video:\n{res.stderr}")

        # Cleanup temp scene files
        for sc in rendered_scene_clips:
            if sc.exists():
                sc.unlink()
        if concat_list.exists():
            concat_list.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()

        return output_mp4_path
