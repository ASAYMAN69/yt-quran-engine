"""Timing loader supporting flexible JSON formats and caching."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import urllib.request

from quran_engine.timing.models import AyahTiming


class TimingLoader:
    """Loads timing information from various supported JSON formats."""

    DEFAULT_TIMING_PATH = "data/quran_timing_alafasy.json"

    def __init__(self, timing_path: Optional[str] = DEFAULT_TIMING_PATH):
        self.timing_path = Path(timing_path) if timing_path else None

    def load(self) -> Dict[str, AyahTiming]:
        """Loads timing map keyed by 'surah:ayah'."""
        if not self.timing_path or not self.timing_path.exists():
            return {}

        with open(self.timing_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        timings: Dict[str, AyahTiming] = {}

        # Case 1: Dict format { "1:1": { "surah": 1, "ayah": 1, "start_seconds": 0.0, "end_seconds": 6.09, "duration_seconds": 6.09 } }
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    surah = v.get("surah")
                    ayah = v.get("ayah")
                    if surah is None or ayah is None:
                        parts = k.split(":")
                        surah = int(parts[0])
                        ayah = int(parts[1])

                    start = float(v.get("start_seconds", v.get("start", 0.0)))
                    end = float(v.get("end_seconds", v.get("end", 0.0)))
                    dur = float(v.get("duration_seconds", v.get("duration", max(0.0, end - start))))
                    is_est = bool(v.get("is_estimated", False))
                    source = v.get("source_name", "Alafasy Recitation Audio Timings")
                    segs = v.get("segments", [])

                    timing_obj = AyahTiming(
                        verse_key=f"{surah}:{ayah}",
                        surah=surah,
                        ayah=ayah,
                        start_seconds=start,
                        end_seconds=end,
                        duration_seconds=dur,
                        is_estimated=is_est,
                        source_name=source,
                        segments=segs,
                    )
                    timings[timing_obj.verse_key] = timing_obj

        # Case 2: List format [ { "surah": 1, "ayah": 1, "start": 0.0, "end": 4.2 } ]
        elif isinstance(data, list):
            for item in data:
                surah = int(item["surah"])
                ayah = int(item["ayah"])
                start = float(item.get("start_seconds", item.get("start", 0.0)))
                end = float(item.get("end_seconds", item.get("end", 0.0)))
                dur = float(item.get("duration_seconds", item.get("duration", max(0.0, end - start))))
                is_est = bool(item.get("is_estimated", False))
                source = item.get("source_name", "Custom Timing File")

                timing_obj = AyahTiming(
                    verse_key=f"{surah}:{ayah}",
                    surah=surah,
                    ayah=ayah,
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=dur,
                    is_estimated=is_est,
                    source_name=source,
                    segments=item.get("segments", []),
                )
                timings[timing_obj.verse_key] = timing_obj

        return timings
