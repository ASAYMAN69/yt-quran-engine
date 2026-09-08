"""Segmentation models representing candidates, video segments, and results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from quran_engine.quran.models import Ayah


@dataclass
class CandidateSegment:
    """Represents a potential contiguous passage of ayahs considered for a video."""
    start_global_idx: int
    end_global_idx: int
    ayahs: List[Ayah]
    duration_seconds: float
    boundary_score: float
    cost: float
    is_estimated: bool = False
    crosses_surah: bool = False
    status: str = "normal"
    reason: str = ""

    @property
    def ayah_count(self) -> int:
        return len(self.ayahs)

    @property
    def start_ayah(self) -> Ayah:
        return self.ayahs[0]

    @property
    def end_ayah(self) -> Ayah:
        return self.ayahs[-1]


@dataclass
class VideoSegment:
    """Final, validated video segment with complete metadata for video rendering."""
    video_id: int
    start_global_idx: int
    end_global_idx: int
    segments: List[Dict[str, Any]]  # List of surah/ayah span dictionaries
    ayah_count: int
    duration_seconds: float
    is_estimated: bool
    semantic_score: float
    boundary_score: float
    status: str  # "normal", "short_passage", "long_ayah_exception", "short_surah_standalone", "override_applied"
    reason: str
    explanation: str
    ayah_keys: List[str]
    arabic_text_combined: str
    english_text_combined: str
    subtitles_timing: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary formatted for JSON export and video rendering."""
        return {
            "video_id": self.video_id,
            "segments": self.segments,
            "ayah_count": self.ayah_count,
            "duration_seconds": round(self.duration_seconds, 2),
            "is_estimated": self.is_estimated,
            "semantic_score": round(self.semantic_score, 3),
            "boundary_score": round(self.boundary_score, 3),
            "status": self.status,
            "reason": self.reason,
            "explanation": self.explanation,
            "ayah_keys": self.ayah_keys,
            "arabic_text": self.arabic_text_combined,
            "english_text": self.english_text_combined,
            "subtitles_timing": self.subtitles_timing,
        }


@dataclass
class SegmentationResult:
    """Encapsulates the complete Quran segmentation result and summary statistics."""
    videos: List[VideoSegment]
    total_videos: int
    total_ayahs: int
    average_duration: float
    min_duration: float
    max_duration: float
    within_target_range_count: int  # 35 - 45 seconds
    below_target_count: int  # < 35s
    above_target_count: int  # > 45s
    exceptions_count: int
    overrides_count: int
    cross_surah_count: int
