"""Script to render a sample video segment using the Quran Video Rendering pipeline."""

import argparse
from pathlib import Path

from config.settings import EngineConfig
from quran_engine.pipeline import QuranSegmentationEngine
from quran_engine.renderer.audio import AudioPipeline
from quran_engine.renderer.subtitles import SubtitleGenerator
from quran_engine.renderer.video import VideoComposer


def render_video_by_id(video_id: int = 1, output_path: str = "output/videos/video_0001_al_fatihah.mp4"):
    print(f"🎬 Initializing video rendering for Video ID {video_id}...")
    engine = QuranSegmentationEngine()
    
    # Run full or load manifest
    result, report = engine.run_full_quran(export_outputs=False)
    
    # Find requested video
    target_video = None
    for v in result.videos:
        if v.video_id == video_id:
            target_video = v
            break
            
    if not target_video:
        raise ValueError(f"Video ID {video_id} not found.")

    ayahs = [engine.quran.get_by_key(k) for k in target_video.ayah_keys]
    print(f"Passage: {target_video.ayah_keys[0]} to {target_video.ayah_keys[-1]} ({len(ayahs)} ayahs)")
    print(f"Duration target: {target_video.duration_seconds:.1f}s")

    temp_dir = Path("temp_render")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prepare Audio
    print("🎵 Step 1/3: Preparing authentic recitation audio...")
    audio_pipeline = AudioPipeline(cache_dir="cache/audio")
    audio_path, durations = audio_pipeline.prepare_segment_audio(
        ayahs=ayahs,
        output_audio_path=temp_dir / f"video_{video_id:04d}_audio.mp3",
    )
    print(f"   Audio stitched successfully ({sum(durations):.1f}s)")

    # 2. Generate Subtitles
    print("📝 Step 2/3: Generating formatted ASS subtitles...")
    subtitle_gen = SubtitleGenerator()
    ass_path = subtitle_gen.generate_ass(
        video_segment=target_video,
        ayahs=ayahs,
        durations=durations,
        output_ass_path=temp_dir / f"video_{video_id:04d}_subtitles.ass",
    )
    print(f"   Subtitles saved to {ass_path}")

    # 3. Composite and Render Video
    print("🎥 Step 3/3: Rendering 1080x1920 vertical video with FFmpeg...")
    composer = VideoComposer(fonts_dir="assets/fonts")
    final_video_path = Path(output_path)
    
    composer.render_reel(
        audio_path=audio_path,
        ass_subtitles_path=ass_path,
        output_mp4_path=final_video_path,
        duration=sum(durations),
    )
    print(f"🎉 Video rendered successfully: {final_video_path}")
    print(f"   File size: {final_video_path.stat().st_size / (1024*1024):.2f} MB")
    return final_video_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a sample Quran video segment.")
    parser.add_argument("--video-id", type=int, default=1, help="Video ID to render (default: 1)")
    parser.add_argument("--output", type=str, default="output/videos/video_0001_al_fatihah.mp4", help="Output MP4 path")
    args = parser.parse_args()

    render_video_by_id(video_id=args.video_id, output_path=args.output)
