"""Script to render a pure black minimalist hook clip with ultra-smooth text fades."""

import argparse
import subprocess
from pathlib import Path


def render_minimal_black_hook(
    output_path: str = "assets/hooks/hook_stop_doomscrolling.mp4",
    duration: float = 4.8,
):
    print(f"🎬 Generating Reusable Minimalist Black Hook ({duration}s)...")
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = Path("temp_render")
    temp_dir.mkdir(parents=True, exist_ok=True)
    ass_path = temp_dir / "hook_typography_black.ass"

    # Smooth fades without text clash:
    # Phase 1: STOP DOOMSCROLLING (0.00s - 1.80s, fad 400ms, 350ms)
    # Phase 2: Give your brain some peace of mind. (1.80s - 4.40s, fad 450ms, 450ms)
    # Remaining 4.40s - 4.80s: Clean pure black tail for seamless fade into recitation video
    hook_ass = (
        "[Script Info]\n"
        "Title: Daily Dose of Quran - Hook\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: HookMain,Cormorant Garamond,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,3,0,1,0,0,5,90,90,0,1\n"
        "Style: HookSub,Cormorant Garamond,74,&H00F8FAFC,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,90,90,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 1,0:00:00.00,0:00:01.80,HookMain,,90,90,0,,{\\an5\\pos(540,960)\\fad(400,350)\\fs88\\b1}STOP DOOMSCROLLING\n"
        "Dialogue: 1,0:00:01.80,0:00:04.40,HookSub,,90,90,0,,{\\an5\\pos(540,960)\\fad(450,450)\\fs74}Give your brain some\\Npeace of mind.\n"
    )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(hook_ass)

    fps = 30
    subtitles_str = str(ass_path.resolve()).replace(":", r"\:").replace("\\", "/")
    fonts_dir_str = "assets/fonts"

    vf_filter = f"ass='{subtitles_str}':fontsdir='{fonts_dir_str}'"
    audio_src = f"anullsrc=r=44100:cl=stereo"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r={fps}:d={duration}",
        "-f", "lavfi", "-i", audio_src,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        str(output_file.resolve()),
    ]

    print("🎥 Rendering hook video...")
    subprocess.run(cmd, check=True)
    print(f"🎉 Hook clip rendered successfully: {output_file}")
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render pure black hook clip")
    parser.add_argument("--output", type=str, default="assets/hooks/hook_stop_doomscrolling.mp4", help="Output MP4 path")
    parser.add_argument("--duration", type=float, default=4.8, help="Duration in seconds")
    args = parser.parse_args()

    render_minimal_black_hook(output_path=args.output, duration=args.duration)
