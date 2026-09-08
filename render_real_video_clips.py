"""Script to render Quran videos using real YouTube video footage clips for each verse."""

import argparse
import subprocess
from pathlib import Path
from typing import Optional

from config.settings import EngineConfig
from quran_engine.pipeline import QuranSegmentationEngine
from quran_engine.renderer.audio import AudioPipeline
from quran_engine.renderer.subtitles import SubtitleGenerator
from quran_engine.renderer.video_clip_composer import YouTubeVideoClipComposer


def render_real_footage_video(
    video_id: int = 1,
    output_path: str = "output/videos/video_0001_al_fatihah_final.mp4",
    video_clips_dir: str = "assets/youtube_clips",
    hook_video: Optional[str] = "assets/hooks/hook_stop_doomscrolling.mp4",
):
    print(f"🎬 Initializing Video Rendering with Real YouTube Footage for Video ID {video_id}...")
    engine = QuranSegmentationEngine()
    result, report = engine.run_full_quran(export_outputs=False)

    target_video = next((v for v in result.videos if v.video_id == video_id), None)
    if not target_video:
        raise ValueError(f"Video ID {video_id} not found.")

    ayahs = [engine.quran.get_by_key(k) for k in target_video.ayah_keys]
    print(f"Surah/Ayahs: {target_video.ayah_keys[0]} to {target_video.ayah_keys[-1]} ({len(ayahs)} ayahs)")
    print(f"Total Duration: {target_video.duration_seconds:.1f}s")

    temp_dir = Path("temp_render")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch & Stitch Recitation Audio
    print("🎵 Step 1/3: Preparing authentic recitation audio...")
    audio_pipeline = AudioPipeline(cache_dir="cache/audio")
    audio_path, durations = audio_pipeline.prepare_segment_audio(
        ayahs=ayahs,
        output_audio_path=temp_dir / f"video_{video_id:04d}_audio.mp3",
    )
    print(f"   Audio stitched ({sum(durations):.1f}s across {len(durations)} verses)")

    # 2. Generate Subtitles
    print("📝 Step 2/3: Generating formatted ASS subtitles...")
    subtitle_gen = SubtitleGenerator()
    ass_path = subtitle_gen.generate_ass(
        video_segment=target_video,
        ayahs=ayahs,
        durations=durations,
        output_ass_path=temp_dir / f"video_{video_id:04d}_subtitles.ass",
    )

    # 3. Composite Real Video Clips
    print("🎥 Step 3/3: Cutting and compositing real YouTube video clips per verse...")
    composer = YouTubeVideoClipComposer(fonts_dir="assets/fonts", video_clips_dir=video_clips_dir)
    final_video = Path(output_path)
    composer.render_verse_video(
        video_segment=target_video,
        ayahs=ayahs,
        audio_path=audio_path,
        durations=durations,
        ass_subtitles_path=ass_path,
        output_mp4_path=final_video,
    )

    # 4. Optional Hook Intro Attachment (with smooth crossfade)
    if hook_video and Path(hook_video).exists():
        print(f"🔗 Attaching reusable hook intro from {hook_video} with smooth crossfade...")
        attach_hook_intro(
            hook_video_path=Path(hook_video),
            main_video_path=final_video,
            output_path=final_video,
            crossfade_duration=0.5,
        )

    print(f"\n🎉 REAL VIDEO FOOTAGE REEL RENDERED SUCCESSFULLY!")
    print(f"   Output File: {final_video}")
    print(f"   Resolution: 1080x1920 (9:16 Vertical Video)")
    print(f"   File Size: {final_video.stat().st_size / (1024*1024):.2f} MB")
    return final_video


def attach_hook_intro(
    hook_video_path: Path,
    main_video_path: Path,
    output_path: Path,
    crossfade_duration: float = 0.5,
) -> Path:
    """Prepends a reusable hook video to the front of the main recitation reel with smooth crossfades."""
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(hook_video_path.resolve())
    ]
    hook_dur = float(subprocess.check_output(probe_cmd).decode().strip())
    fade_offset = max(0.0, hook_dur - crossfade_duration)

    temp_out = output_path.parent / f"temp_hook_{output_path.name}"

    vf = (
        f"[0:v]fps=30,settb=AVTB[v0];"
        f"[1:v]fps=30,settb=AVTB[v1];"
        f"[v0][v1]xfade=transition=fade:duration={crossfade_duration}:offset={fade_offset:.3f}[outv];"
        f"[0:a]afade=t=out:st={fade_offset:.3f}:d={crossfade_duration}[a0];"
        f"[1:a]adelay={int(fade_offset*1000)}|{int(fade_offset*1000)},afade=t=in:st={fade_offset:.3f}:d={crossfade_duration}[a1];"
        f"[a0][a1]amix=inputs=2:duration=longest[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(hook_video_path.resolve()),
        "-i", str(main_video_path.resolve()),
        "-filter_complex", vf,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(temp_out.resolve()),
    ]
    subprocess.run(cmd, check=True)
    temp_out.replace(output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Quran video with real video footage clips.")
    parser.add_argument("--video-id", type=int, default=1, help="Video ID to render (default: 1)")
    parser.add_argument("--output", type=str, default="output/videos/video_0001_al_fatihah_final.mp4", help="Output MP4 path")
    parser.add_argument("--clips-dir", type=str, default="assets/youtube_clips", help="Directory of real video clips")
    parser.add_argument("--hook-video", type=str, default="assets/hooks/hook_stop_doomscrolling.mp4", help="Reusable hook video to prepend")
    args = parser.parse_args()

    render_real_footage_video(
        video_id=args.video_id,
        output_path=args.output,
        video_clips_dir=args.clips_dir,
        hook_video=args.hook_video,
    )
