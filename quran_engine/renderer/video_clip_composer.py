"""Compositor that cuts and stitches real YouTube video clips in 1:1 resolution with semi-transparent black overlay."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from quran_engine.quran.models import Ayah
from quran_engine.segmentation.models import VideoSegment


class YouTubeVideoClipComposer:
    """Combines real video clips (e.g. from YouTube) in 1:1 resolution with dark overlay scrim."""

    def __init__(self, fonts_dir: str = "assets/fonts", video_clips_dir: str = "assets/youtube_clips"):
        self.fonts_dir = Path(fonts_dir).resolve()
        self.video_clips_dir = Path(video_clips_dir).resolve()

    def get_available_clips(self, count: int, min_duration: float = 10.0) -> List[Path]:
        """Gets real video clips in sorted order, filtering out any clip shorter than min_duration (default: 10s)."""
        all_clips = sorted([
            p for p in self.video_clips_dir.glob("*")
            if p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
        ])
        if not all_clips:
            raise FileNotFoundError(f"No video clips found in {self.video_clips_dir}")

        qualified_clips = []
        for p in all_clips:
            dur = self._get_clip_duration(p)
            if dur >= min_duration:
                qualified_clips.append(p)
            else:
                print(f"⚠️ Skipping clip {p.name} ({dur:.1f}s) because it is under {min_duration}s")

        if not qualified_clips:
            raise FileNotFoundError(f"No qualified video clips >= {min_duration}s found in {self.video_clips_dir}")

        res = []
        for i in range(count):
            res.append(qualified_clips[i % len(qualified_clips)])
        return res

    def _get_clip_duration(self, clip_path: Path) -> float:
        """Gets exact duration of a video clip file via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(clip_path.resolve())
        ]
        try:
            out = subprocess.check_output(cmd).decode().strip()
            return float(out)
        except Exception:
            return 10.0

    def render_verse_video(
        self,
        video_segment: VideoSegment,
        ayahs: List[Ayah],
        audio_path: Path,
        durations: List[float],
        ass_subtitles_path: Path,
        output_mp4_path: Path,
        video_clips: Optional[List[Path]] = None,
        canvas_mode: str = "vertical_with_1x1_middle",
        dark_overlay_opacity: float = 0.38,
        use_nvenc: bool = False,
    ) -> Path:
        """
        Takes real video footage clips, crops to 1:1 square, centers in the frame, and adds a dark overlay.
        If a verse is longer than the video clip, it slows down the clip to match the verse duration.
        If the video clip is longer than the verse, it plays at normal speed.
        """
        output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = output_mp4_path.parent / f"temp_vclips_{video_segment.video_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if not video_clips:
            video_clips = self.get_available_clips(len(ayahs))

        rendered_segments: List[Path] = []
        fps = 30
        trans_duration = 0.45 if len(durations) > 1 else 0.0
        vcodec_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "21"] if use_nvenc else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]

        print(f"🎬 Processing {len(ayahs)} real video clips with 1:1 center framing, {int(dark_overlay_opacity*100)}% dark overlay, and smooth crossfades...")

        for idx, (v_clip, dur) in enumerate(zip(video_clips, durations), start=1):
            out_seg_path = temp_dir / f"verse_vclip_{idx:02d}.mp4"
            # Add extra handle duration for smooth crossfade overlap
            seg_dur = dur + trans_duration if idx < len(durations) else dur
            clip_dur = self._get_clip_duration(v_clip)

            # If verse is longer than the clip, slow down video to match duration.
            # If clip is longer than verse, keep normal speed (1.0x).
            if clip_dur > 0 and seg_dur > clip_dur:
                speed_factor = seg_dur / clip_dur
                pts_filter = f"setpts={speed_factor:.6f}*PTS,"
                print(f"   ⏱️ Verse {idx} ({v_clip.name}): verse duration ({seg_dur:.2f}s) > clip duration ({clip_dur:.2f}s) -> slowing down {speed_factor:.2f}x to match perfectly.")
            else:
                pts_filter = ""
                print(f"   ⏱️ Verse {idx} ({v_clip.name}): clip duration ({clip_dur:.2f}s) >= verse duration ({seg_dur:.2f}s) -> playing at normal speed.")

            if canvas_mode == "pure_1x1":
                # 1080x1080 pure square video with dark overlay
                vf_filter = (
                    f"[0:v]{pts_filter}scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,"
                    f"eq=brightness=-0.12:contrast=1.12[fg_raw];"
                    f"color=c=black@{dark_overlay_opacity}:s=1080x1080[scrim];"
                    f"[fg_raw][scrim]overlay=0:0,fps={fps},settb=AVTB,format=yuv420p"
                )
            else:
                # 1080x1920 canvas with 1080x1080 1:1 video framed in the middle (y=420)
                # Background: sleek dark blurred ambiance. Center: 1:1 square video with dark overlay scrim
                vf_filter = (
                    f"[0:v]{pts_filter}split=2[bg_in][fg_in];"
                    f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.42:contrast=1.1[bg];"
                    f"[fg_in]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,eq=brightness=-0.12:contrast=1.12[fg_raw];"
                    f"color=c=black@{dark_overlay_opacity}:s=1080x1080[scrim];"
                    f"[fg_raw][scrim]overlay=0:0[fg_tinted];"
                    f"[bg][fg_tinted]overlay=0:420,fps={fps},settb=AVTB,format=yuv420p"
                )

            cmd = [
                "ffmpeg", "-y",
                "-i", str(v_clip.resolve()),
                "-filter_complex", vf_filter,
                "-t", str(seg_dur),
                *vcodec_args,
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-an",
                str(out_seg_path.resolve()),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            rendered_segments.append(out_seg_path)

        subtitles_str = str(ass_subtitles_path.resolve()).replace(":", r"\:").replace("\\", "/")
        fonts_dir_str = str(self.fonts_dir).replace(":", r"\:").replace("\\", "/")

        print("✨ Blending clips with smooth crossfade & burning typography...")
        total_duration = sum(durations)

        # Clean white stripe progress bar starting from left to right at bottom edge of 1:1 clip using geq overlay
        pbar_src = (
            f"color=white@0:s=1080x8:r={fps}:d={total_duration:.2f},format=rgba,"
            f"geq=r='255':g='255':b='255':a='255*lte(X,1080*T/{total_duration:.2f})'"
        )

        if len(rendered_segments) == 1:
            # Single clip
            final_cmd = [
                "ffmpeg", "-y",
                "-i", str(rendered_segments[0].resolve()),
                "-i", str(audio_path.resolve()),
                "-filter_complex", f"{pbar_src}[pbar];[0:v][pbar]overlay=0:1492:format=auto[v_pbar];[v_pbar]ass='{subtitles_str}':fontsdir='{fonts_dir_str}'[out_v]",
                "-map", "[out_v]",
                "-map", "1:a",
                *vcodec_args,
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-t", str(total_duration),
                str(output_mp4_path.resolve()),
            ]
        else:
            # Multi-clip with chained xfade transitions
            filter_chain = []
            last_label = "0:v"
            curr_offset = 0.0

            for i in range(1, len(rendered_segments)):
                curr_offset += durations[i - 1]
                out_label = f"xf{i}"
                filter_chain.append(
                    f"[{last_label}][{i}:v]xfade=transition=fade:duration={trans_duration}:offset={curr_offset:.3f}[{out_label}]"
                )
                last_label = out_label

            # Append geq progress bar overlay and subtitles filter to final blended stream
            filter_chain.append(f"{pbar_src}[pbar]")
            filter_chain.append(f"[{last_label}][pbar]overlay=0:1492:format=auto[v_pbar]")
            filter_chain.append(f"[v_pbar]ass='{subtitles_str}':fontsdir='{fonts_dir_str}'[out_v]")

            final_cmd = ["ffmpeg", "-y"]
            for seg in rendered_segments:
                cmd_in = ["-i", str(seg.resolve())]
                final_cmd.extend(cmd_in)

            # Audio input index is len(rendered_segments)
            audio_idx = len(rendered_segments)
            final_cmd.extend([
                "-i", str(audio_path.resolve()),
                "-filter_complex", ";".join(filter_chain),
                "-map", "[out_v]",
                "-map", f"{audio_idx}:a",
                *vcodec_args,
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-t", str(total_duration),
                str(output_mp4_path.resolve()),
            ])

        res = subprocess.run(final_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg render failed:\n{res.stderr}")

        # Cleanup
        for s in rendered_segments:
            if s.exists():
                s.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()

        return output_mp4_path
