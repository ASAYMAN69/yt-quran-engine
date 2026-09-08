"""Duration model for calculating and estimating presentation durations."""

import re
from typing import Dict, List, Optional, Sequence

from quran_engine.quran.models import Ayah
from quran_engine.timing.models import AyahTiming


class DurationModel:
    """Manages audio durations for ayahs, supporting exact timings and calibrated fallbacks."""

    def __init__(
        self,
        exact_timings: Optional[Dict[str, AyahTiming]] = None,
        fallback_wpm: float = 65.0,
        fallback_cps: float = 8.5,
    ):
        self._timings: Dict[str, AyahTiming] = exact_timings or {}
        self.fallback_wpm = fallback_wpm
        self.fallback_cps = fallback_cps

    @property
    def has_full_exact_timings(self) -> bool:
        """Returns True if exact timings are loaded for all 6,236 verses."""
        return len(self._timings) >= 6236

    def get_ayah_timing(self, ayah: Ayah) -> AyahTiming:
        """Retrieves exact timing if present, or calculates a calibrated fallback estimation."""
        if ayah.key in self._timings:
            return self._timings[ayah.key]
        return self._estimate_ayah_duration(ayah)

    def get_ayah_duration(self, ayah: Ayah) -> float:
        """Returns the duration in seconds for a single ayah."""
        return self.get_ayah_timing(ayah).duration_seconds

    def get_passage_duration(self, ayahs: Sequence[Ayah]) -> float:
        """Calculates total duration in seconds for a sequence of ayahs."""
        return sum(self.get_ayah_duration(a) for a in ayahs)

    def is_passage_estimated(self, ayahs: Sequence[Ayah]) -> bool:
        """Returns True if any ayah in the passage relies on estimated duration."""
        return any(self.get_ayah_timing(a).is_estimated for a in ayahs)

    def _estimate_ayah_duration(self, ayah: Ayah) -> AyahTiming:
        """Calibrated fallback recitation estimation based on Arabic phonetic features and Tajweed pauses."""
        text = ayah.text_ar
        words = text.split()
        num_words = len(words)
        
        # Count letters without diacritics
        clean_text = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", text)
        num_chars = len(clean_text.replace(" ", ""))

        # Tajweed elongations (Madd symbols: ۤ, ۧ, etc.)
        madd_count = len(re.findall(r"[\u06E4\u06E5\u06E6\u0653]", text))

        # Base duration from word rate (~65 words per minute = ~0.92 sec/word)
        word_dur = (num_words / max(1.0, self.fallback_wpm)) * 60.0

        # Character duration adjustment
        char_dur = (num_chars / max(1.0, self.fallback_cps))

        # Blend word and character duration
        base_dur = 0.5 * word_dur + 0.5 * char_dur

        # Add pause buffer per verse and madd elongation factor (approx 0.8s per long madd)
        elongation_bonus = madd_count * 0.8
        verse_pause = 1.0  # Breath/pause between verses

        estimated_duration = max(2.0, round(base_dur + elongation_bonus + verse_pause, 2))

        return AyahTiming(
            verse_key=ayah.key,
            surah=ayah.surah_number,
            ayah=ayah.ayah_number,
            start_seconds=0.0,
            end_seconds=estimated_duration,
            duration_seconds=estimated_duration,
            is_estimated=True,
            source_name="Fallback Linguistic Tajweed Model",
            segments=[],
        )
