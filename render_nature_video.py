"""Script to render a dynamic multi-scene nature video for Quran segments."""

import argparse
from pathlib import Path

from config.settings import EngineConfig
from quran_engine.pipeline import QuranSegmentationEngine
from quran_engine.renderer.audio import AudioPipeline
from quran_engine.renderer.subtitles import SubtitleGenerator
from quran_engine.renderer.nature_composer import NatureVideoComposer


def render_nature_video_by_id(
    video_id: int = 1,
    output_path: str = "output/videos/video_0001_al_fatihah_nature.mp4",
    clips_dir: str = "assets/nature_clips",
):
    print(f"🎬 Initializing Nature Video Rendering for Video ID {video_id}...")
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

    # 1. Fetch & Stitch Audio
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

    # 3. Render Multi-Scene Nature Video
    print("🌲 Step 3/3: Rendering multi-scene nature background with cinematic motion...")
    composer = NatureVideoComposer(fonts_dir="assets/fonts", nature_clips_dir=clips_dir)
    final_video = Path(output_path)
    composer.render_multi_scene_video(
        video_segment=target_video,
        ayahs=ayahs,
        audio_path=audio_path,
        durations=durations,
        ass_subtitles_path=ass_path,
        output_mp4_path=final_video,
    )

    print(f"\n🎉 NATURE REEL RENDERED SUCCESSFULLY!")
    print(f"   Output File: {final_video}")
    print(f"   Resolution: 1080x1920 (9:16 Vertical Video)")
    print(f"   Duration: {sum(durations):.1f}s")
    print(f"   File Size: {final_video.stat().st_size / (1024*1024):.2f} MB")
    return final_video


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render dynamic multi-scene nature Quran video.")
    parser.add_argument("--video-id", type=int, default=1, help="Video ID to render (default: 1)")
    parser.add_argument("--output", type=str, default="output/videos/video_0001_al_fatihah_nature.mp4", help="Output MP4 path")
    parser.add_argument("--clips-dir", type=str, default="assets/nature_clips", help="Directory of nature visuals/clips")
    args = parser.parse_args()

    render_nature_video_by_id(video_id=args.video_id, output_path=args.output, clips_dir=args.clips_dir)
