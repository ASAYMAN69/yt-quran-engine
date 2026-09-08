"""
High-Speed GPU/Multi-Core Batch Renderer for Full Quran Reels.
Optimized for Google Colab (T4 / A100 / CPU) & local multi-processing.
"""

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from quran_engine.pipeline import QuranSegmentationEngine
from quran_engine.renderer.audio import AudioPipeline
from quran_engine.renderer.subtitles import SubtitleGenerator
from quran_engine.renderer.video_clip_composer import YouTubeVideoClipComposer


def check_nvenc_available() -> bool:
    """Checks if NVIDIA NVENC hardware encoder is supported by FFmpeg."""
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


def attach_hook_intro(
    hook_video_path: Path,
    main_video_path: Path,
    output_path: Path,
    use_nvenc: bool = False,
    crossfade_duration: float = 0.5,
) -> Path:
    """Prepends the master hook video to the front of the main recitation reel with smooth crossfade."""
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

    vcodec_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "21"] if use_nvenc else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]

    cmd = [
        "ffmpeg", "-y",
        "-i", str(hook_video_path.resolve()),
        "-i", str(main_video_path.resolve()),
        "-filter_complex", vf,
        "-map", "[outv]",
        "-map", "[outa]",
        *vcodec_args,
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(temp_out.resolve()),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    temp_out.replace(output_path)
    return output_path


def render_single_video(
    video_id: int,
    output_dir: Path,
    clips_dir: str = "assets/youtube_clips",
    fonts_dir: str = "assets/fonts",
    hook_video: Optional[str] = "assets/hooks/hook_stop_doomscrolling.mp4",
    use_nvenc: bool = False,
    force_rerender: bool = False,
) -> Tuple[int, str, float]:
    """Renders a single Quran video reel with auto-resume, ASS subtitles, and hook attachment."""
    start_time = time.time()
    out_file = output_dir / f"video_{video_id:04d}.mp4"

    # Auto-resume check
    if not force_rerender and out_file.exists() and out_file.stat().st_size > 1_000_000:
        return video_id, "SKIPPED", 0.0

    temp_dir = Path(f"temp_render/v_{video_id:04d}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        engine = QuranSegmentationEngine()
        result, _ = engine.run_full_quran(export_outputs=False)
        target_video = next((v for v in result.videos if v.video_id == video_id), None)
        if not target_video:
            return video_id, f"ERROR: Video ID {video_id} not found", 0.0

        ayahs = [engine.quran.get_by_key(k) for k in target_video.ayah_keys]

        # 1. Prepare Audio
        audio_pipeline = AudioPipeline(cache_dir="cache/audio")
        audio_path, durations = audio_pipeline.prepare_segment_audio(
            ayahs=ayahs,
            output_audio_path=temp_dir / f"audio_{video_id:04d}.mp3",
        )

        # 2. Generate ASS Subtitles
        subtitle_gen = SubtitleGenerator()
        ass_path = subtitle_gen.generate_ass(
            video_segment=target_video,
            ayahs=ayahs,
            durations=durations,
            output_ass_path=temp_dir / f"subtitles_{video_id:04d}.ass",
        )

        # 3. Render Recitation Video
        composer = YouTubeVideoClipComposer(fonts_dir=fonts_dir, video_clips_dir=clips_dir)
        temp_main_mp4 = temp_dir / f"main_{video_id:04d}.mp4"
        composer.render_verse_video(
            video_segment=target_video,
            ayahs=ayahs,
            audio_path=audio_path,
            durations=durations,
            ass_subtitles_path=ass_path,
            output_mp4_path=temp_main_mp4,
            use_nvenc=use_nvenc,
        )

        # 4. Attach Hook Intro
        if hook_video and Path(hook_video).exists():
            attach_hook_intro(
                hook_video_path=Path(hook_video),
                main_video_path=temp_main_mp4,
                output_path=out_file,
                use_nvenc=use_nvenc,
            )
        else:
            temp_main_mp4.replace(out_file)

        elapsed = time.time() - start_time
        return video_id, "SUCCESS", elapsed

    except Exception as e:
        return video_id, f"ERROR: {str(e)}", time.time() - start_time
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            for f in temp_dir.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                temp_dir.rmdir()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Batch GPU/Multi-Core Quran Video Reel Exporter.")
    parser.add_argument("--start-id", type=int, default=1, help="Starting video ID (default: 1)")
    parser.add_argument("--end-id", type=int, default=10, help="Ending video ID inclusive (default: 10)")
    parser.add_argument("--output-dir", type=str, default="output/videos", help="Target output directory for videos")
    parser.add_argument("--workers", type=int, default=2, help="Number of concurrent rendering workers (default: 2)")
    parser.add_argument("--clips-dir", type=str, default="assets/youtube_clips", help="Clips directory")
    parser.add_argument("--hook-video", type=str, default="assets/hooks/hook_stop_doomscrolling.mp4", help="Hook video path")
    parser.add_argument("--use-nvenc", action="store_true", help="Force enable NVENC GPU encoder")
    parser.add_argument("--force-rerender", action="store_true", help="Force re-rendering even if output exists")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    nvenc_supported = check_nvenc_available()
    use_nvenc = args.use_nvenc or nvenc_supported

    print("=" * 70)
    print("🎬 QURAN REELS BATCH EXPORTER (GPU / MULTI-CORE ACCELERATED)")
    print("=" * 70)
    print(f"📌 Video ID Range: {args.start_id} to {args.end_id} (Total: {args.end_id - args.start_id + 1} videos)")
    print(f"📂 Output Directory: {output_dir}")
    print(f"⚡ Workers: {args.workers}")
    print(f"🚀 Hardware NVENC GPU Acceleration: {'ENABLED' if use_nvenc else 'DISABLED (Using Multi-Threaded libx264)'}")
    print(f"🔄 Auto-Resume (Skip existing): {'OFF' if args.force_rerender else 'ON'}")
    print("=" * 70)

    video_ids = list(range(args.start_id, args.end_id + 1))
    results: Dict[int, Tuple[str, float]] = {}

    batch_start = time.time()
    completed_count = 0
    skipped_count = 0
    failed_count = 0

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            future_to_id = {
                executor.submit(
                    render_single_video,
                    vid,
                    output_dir,
                    args.clips_dir,
                    "assets/fonts",
                    args.hook_video,
                    use_nvenc,
                    args.force_rerender,
                ): vid
                for vid in video_ids
            }

            for future in as_completed(future_to_id):
                vid = future_to_id[future]
                try:
                    v_id, status, elapsed = future.result()
                    results[v_id] = (status, elapsed)
                    if status == "SUCCESS":
                        completed_count += 1
                        print(f"✅ Video {v_id:04d}: Rendered successfully in {elapsed:.1f}s")
                    elif status == "SKIPPED":
                        skipped_count += 1
                        print(f"⏩ Video {v_id:04d}: Already exists, skipped.")
                    else:
                        failed_count += 1
                        print(f"❌ Video {v_id:04d}: Failed -> {status}")
                except Exception as e:
                    failed_count += 1
                    print(f"❌ Video {vid:04d}: Exception -> {e}")
    else:
        for vid in video_ids:
            v_id, status, elapsed = render_single_video(
                vid,
                output_dir,
                args.clips_dir,
                "assets/fonts",
                args.hook_video,
                use_nvenc,
                args.force_rerender,
            )
            results[v_id] = (status, elapsed)
            if status == "SUCCESS":
                completed_count += 1
                print(f"✅ Video {v_id:04d}: Rendered successfully in {elapsed:.1f}s")
            elif status == "SKIPPED":
                skipped_count += 1
                print(f"⏩ Video {v_id:04d}: Already exists, skipped.")
            else:
                failed_count += 1
                print(f"❌ Video {v_id:04d}: Failed -> {status}")

    total_time = time.time() - batch_start
    print("\n" + "=" * 70)
    print("🏁 BATCH EXPORT SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully Rendered: {completed_count}")
    print(f"⏩ Skipped (Pre-existing): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏱️ Total Wall Time: {total_time:.1f}s ({total_time/60:.2f} mins)")
    if completed_count > 0:
        print(f"⚡ Average Speed: {total_time / completed_count:.1f}s per video")
    print("=" * 70)


if __name__ == "__main__":
    main()
