"""Semantic boundary scoring engine evaluating potential division points between verses."""

import re
from typing import Dict, List, Optional, Tuple

from quran_engine.quran.models import Ayah
from quran_engine.semantic.models import SemanticBoundary
from quran_engine.semantic.markers import (
    normalize_arabic,
    OPENING_MARKERS,
    CLOSING_MARKERS,
    TIGHT_CONTINUATION_START_MARKERS,
    ENGLISH_OPENING_PATTERNS,
)


class SemanticBoundaryScorer:
    """Evaluates the semantic and linguistic naturalness of placing a video boundary after an ayah."""

    def __init__(
        self,
        surah_bonus: float = 0.40,
        ruku_bonus: float = 0.30,
        base_score: float = 0.50,
    ):
        self.surah_bonus = surah_bonus
        self.ruku_bonus = ruku_bonus
        self.base_score = base_score
        self._boundary_cache: Dict[str, SemanticBoundary] = {}

    def evaluate_boundary(self, from_ayah: Ayah, to_ayah: Optional[Ayah]) -> SemanticBoundary:
        """Evaluates boundary quality after from_ayah before to_ayah."""
        cache_key = f"{from_ayah.global_index}_{to_ayah.global_index if to_ayah else -1}"
        if cache_key in self._boundary_cache:
            return self._boundary_cache[cache_key]

        score = self.base_score
        reasons: List[str] = []
        signals: List[str] = []

        is_surah_boundary = from_ayah.is_surah_end
        is_ruku_boundary = from_ayah.is_ruku_end

        # 1. Final Ayah of the entire Quran
        if to_ayah is None:
            return SemanticBoundary(
                from_ayah=from_ayah,
                to_ayah=None,
                score=1.0,
                is_surah_boundary=True,
                is_ruku_boundary=True,
                reasons=["Final verse of the Quran (Surah An-Nas)."],
                signals=["quran_end"],
            )

        # 2. Surah Boundary
        if is_surah_boundary or from_ayah.surah_number != to_ayah.surah_number:
            score += self.surah_bonus
            reasons.append(f"Complete ending of Surah {from_ayah.surah_name_en} ({from_ayah.surah_number}).")
            signals.append("surah_boundary")

        # 3. Traditional Ruku' (thematic section) Boundary
        if is_ruku_boundary and not is_surah_boundary:
            score += self.ruku_bonus
            reasons.append(f"Traditional Ruku' section completion (Ruku {from_ayah.ruku}).")
            signals.append("ruku_boundary")

        # 4. Closing Clausulae / Formulae at end of from_ayah
        norm_ar_from = normalize_arabic(from_ayah.text_ar)
        for pattern, desc, bonus in CLOSING_MARKERS:
            if re.search(pattern, norm_ar_from):
                score += bonus
                reasons.append(f"Ending clausula in {from_ayah.key}: {desc}")
                signals.append("closing_clausula")
                break

        # 5. Opening Markers at start of to_ayah
        norm_ar_to = normalize_arabic(to_ayah.text_ar)
        for pattern, desc, bonus in OPENING_MARKERS:
            if re.search(pattern, norm_ar_to):
                score += bonus
                reasons.append(f"Opening marker in next verse {to_ayah.key}: {desc}")
                signals.append("opening_marker")
                break

        # 6. English Translation Shift Indicators
        en_to_text = to_ayah.text_en.strip()
        for pattern, desc, bonus in ENGLISH_OPENING_PATTERNS:
            if re.search(pattern, en_to_text, re.IGNORECASE):
                score += (bonus * 0.5)  # Supporting secondary signal
                reasons.append(f"English translation transition in {to_ayah.key}: {desc}")
                signals.append("en_opening_marker")
                break

        # 7. Tight Continuation Penalties (bad to cut)
        for pattern, desc, penalty in TIGHT_CONTINUATION_START_MARKERS:
            if re.search(pattern, norm_ar_to):
                score += penalty  # penalty is negative
                reasons.append(f"Close syntactic dependency with {to_ayah.key}: {desc}")
                signals.append("tight_continuation_penalty")
                break

        # Bound score between 0.05 and 1.0
        final_score = max(0.05, min(1.0, score))

        if not reasons:
            reasons.append("Standard verse boundary within continuous passage.")

        boundary = SemanticBoundary(
            from_ayah=from_ayah,
            to_ayah=to_ayah,
            score=round(final_score, 3),
            is_surah_boundary=is_surah_boundary,
            is_ruku_boundary=is_ruku_boundary,
            reasons=reasons,
            signals=signals,
        )

        self._boundary_cache[cache_key] = boundary
        return boundary
