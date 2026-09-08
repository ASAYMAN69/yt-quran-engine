"""Semantic data models for boundary and passage evaluation."""

from dataclasses import dataclass, field
from typing import List, Optional
from quran_engine.quran.models import Ayah


@dataclass
class SemanticBoundary:
    """Represents the semantic quality of cutting between two ayahs."""
    from_ayah: Ayah
    to_ayah: Optional[Ayah]  # None if at the end of the entire Quran
    score: float  # Normalized 0.0 (terrible cut) to 1.0 (perfect natural boundary)
    is_surah_boundary: bool = False
    is_ruku_boundary: bool = False
    reasons: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        to_key = self.to_ayah.key if self.to_ayah else "END"
        return f"{self.from_ayah.key} -> {to_key}"

    def __repr__(self) -> str:
        return f"SemanticBoundary({self.key}, score={self.score:.2f}, signals={len(self.signals)})"


@dataclass
class PassageCoherence:
    """Represents the semantic coherence analysis of an entire passage."""
    start_ayah: Ayah
    end_ayah: Ayah
    ayah_count: int
    boundary_score: float
    summary_theme: str
    explanation: str
    reasons: List[str] = field(default_factory=list)
