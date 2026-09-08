"""Audio processing and concatenation for video rendering."""

import os
import subprocess
from pathlib import Path
from typing import List, Tuple
import urllib.request

from quran_engine.quran.models import Ayah
from quran_engine.segmentation.models import VideoSegment


class AudioPipeline:
    """Fetches, caches, and stitches recitation audio clips for video segments."""

    AUDIO_BASE_URL = "https://cdn.islamic.network/quran/audio/128/ar.alafasy/{global_ayah_num}.mp3"

    def __init__(self, cache_dir: str = "cache/audio"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_ayah_audio(self, ayah: Ayah) -> Path:
        """Fetches individual ayah audio file if not cached."""
        global_num = ayah.global_index + 1
        dest = self.cache_dir / f"{global_num:04d}_{ayah.surah_number}_{ayah.ayah_number}.mp3"
        if not dest.exists():
            url = self.AUDIO_BASE_URL.format(global_ayah_num=global_num)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Quran-Video-Renderer"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(dest, "wb") as f:
                    f.write(resp.read())
        return dest

    def prepare_segment_audio(self, ayahs: List[Ayah], output_audio_path: Path) -> Tuple[Path, List[float]]:
        """
        Fetches all ayah audio clips, extracts exact durations, and concatenates them into output_audio_path.
        Returns: (output_audio_path, list_of_individual_durations)
        """
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_files: List[Path] = [self.fetch_ayah_audio(a) for a in ayahs]

        # Calculate exact duration of each audio file using ffprobe
        durations: List[float] = []
        for af in audio_files:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(af),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            dur = float(res.stdout.strip())
            durations.append(dur)

        # Concatenate audio files using ffmpeg concat demuxer
        concat_list_file = output_audio_path.parent / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for af in audio_files:
                f.write(f"file '{af.resolve()}'\n")

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_audio_path),
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)

        if concat_list_file.exists():
            concat_list_file.unlink()

        return output_audio_path, durations
