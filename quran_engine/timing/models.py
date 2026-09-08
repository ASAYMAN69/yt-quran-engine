"""Timing data models for ayah and passage durations."""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass(frozen=True)
class AyahTiming:
    """Represents the audio/subtitle presentation timing of an Ayah."""
    verse_key: str  # e.g. "1:1"
    surah: int
    ayah: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    is_estimated: bool = False
    source_name: str = "Alafasy Recitation Audio Timings"
    segments: List[Any] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.verse_key

    def __repr__(self) -> str:
        est_flag = " (ESTIMATED)" if self.is_estimated else ""
        return f"AyahTiming({self.verse_key}: {self.duration_seconds:.2f}s{est_flag})"
