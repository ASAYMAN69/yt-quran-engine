"""Segment scoring engine calculating cost for candidate segments."""

import math
from typing import List, Optional, Tuple

from config.settings import EngineConfig
from quran_engine.quran.models import Ayah
from quran_engine.semantic.boundaries import SemanticBoundaryScorer
from quran_engine.semantic.models import SemanticBoundary
from quran_engine.overrides.manager import OverrideManager


class SegmentScorer:
    """Calculates optimization costs for candidate video segments."""

    def __init__(
        self,
        config: EngineConfig,
        boundary_scorer: SemanticBoundaryScorer,
        override_manager: Optional[OverrideManager] = None,
    ):
        self.config = config
        self.boundary_scorer = boundary_scorer
        self.override_manager = override_manager or OverrideManager()

    def score_candidate(
        self,
        ayahs: List[Ayah],
        next_ayah: Optional[Ayah],
        duration: float,
    ) -> Tuple[float, float, str, str]:
        """
        Calculates cost (lower is better), boundary score, status, and rationale.
        Returns: (cost, boundary_score, status, reason)
        """
        start_ayah = ayahs[0]
        end_ayah = ayahs[-1]
        ayah_count = len(ayahs)

        # 1. Override validation
        if self.override_manager.is_boundary_forbidden(end_ayah):
            return float("inf"), 0.0, "forbidden", "Manual override: forbidden boundary"

        if self.override_manager.violates_keep_together(start_ayah, end_ayah):
            return float("inf"), 0.0, "forbidden", "Manual override: violates keep_together"

        # Check if any intermediate ayah had a forced boundary that was skipped
        for a in ayahs[:-1]:
            if self.override_manager.is_boundary_forced(a):
                return float("inf"), 0.0, "forbidden", "Manual override: skipped forced boundary"

        is_forced_end = self.override_manager.is_boundary_forced(end_ayah)

        # 2. Semantic boundary evaluation
        boundary: SemanticBoundary = self.boundary_scorer.evaluate_boundary(end_ayah, next_ayah)
        b_score = boundary.score

        # 3. Surah continuity check
        crosses_surah = (start_ayah.surah_number != end_ayah.surah_number)
        ends_at_surah = end_ayah.is_surah_end

        # 4. Duration cost calculation
        target = self.config.duration.target_seconds
        min_pref = self.config.duration.min_preferred_seconds
        max_pref = self.config.duration.max_preferred_seconds
        min_acc = self.config.duration.min_acceptable_seconds
        max_acc = self.config.duration.max_acceptable_seconds

        status = "normal"
        reason = ""

        # Case A: Single Long Ayah Exception (e.g. Ayat Al-Kursi, Ayat Ad-Dayn)
        if ayah_count == 1 and duration >= max_pref:
            status = "long_ayah_exception"
            reason = f"Single indivisible ayah ({start_ayah.key}) of {duration:.1f}s cannot be split."
            # Mild cost so it is picked cleanly without distorting global path
            duration_cost = 0.2 * abs(duration - target) / 10.0

        # Case B: Single Short Surah Standalone (e.g. Al-Kawthar, Al-Ikhlas)
        elif start_ayah.is_surah_start and end_ayah.is_surah_end and start_ayah.surah_number == end_ayah.surah_number and duration < min_pref:
            status = "short_surah_standalone"
            reason = f"Complete short Surah {start_ayah.surah_name_en} ({start_ayah.surah_number}) of {duration:.1f}s preserved as standalone unit."
            # Modest penalty to allow standing alone if combining creates poor coherence
            duration_cost = 1.0 + 0.8 * ((target - duration) / 10.0)

        # Case C: Standard multi-ayah or normal single ayah duration
        else:
            if min_pref <= duration <= max_pref:
                # Sweet spot [35s, 45s]
                dev = abs(duration - target)
                duration_cost = 0.1 * (dev / 5.0) ** 2
                status = "normal"
                reason = f"Optimal duration ({duration:.1f}s) with natural boundary score {b_score:.2f}."
            elif min_acc <= duration < min_pref:
                # 25s - 35s
                dev = min_pref - duration
                duration_cost = 0.8 + 1.2 * (dev / 10.0)
                status = "short_passage"
                reason = f"Slightly short passage ({duration:.1f}s) preferred due to strong natural boundary."
            elif max_pref < duration <= max_acc:
                # 45s - 55s
                dev = duration - max_pref
                duration_cost = 0.8 + 1.4 * (dev / 10.0)
                status = "extended_passage"
                reason = f"Extended passage ({duration:.1f}s) preserved to avoid breaking tightly connected context."
            elif duration < min_acc:
                # < 25s
                dev = min_acc - duration
                duration_cost = 2.5 + 2.5 * (dev / 10.0) ** 1.5
                status = "very_short"
                reason = f"Unusually short segment ({duration:.1f}s)."
            else:
                # > 55s
                dev = duration - max_acc
                duration_cost = 3.0 + 3.0 * (dev / 10.0) ** 1.5
                status = "very_long"
                reason = f"Unusually long segment ({duration:.1f}s)."

        # 5. Semantic quality cost (Higher boundary score gives bigger discount)
        # b_score is in [0.05, 1.0] -> semantic_cost ranges from -1.6 to -0.08
        semantic_cost = -self.config.weights.semantic_weight * b_score

        # 6. Bonuses and Penalties
        bonus_penalty = 0.0

        if ends_at_surah:
            bonus_penalty -= self.config.weights.surah_boundary_bonus
        elif end_ayah.is_ruku_end:
            bonus_penalty -= self.config.weights.ruku_boundary_bonus

        if crosses_surah:
            if not self.config.rules.allow_cross_surah:
                return float("inf"), b_score, "forbidden", "Crossing surah boundaries is disabled in config."
            # If start ayah surah is short, apply smaller cross-surah penalty
            if start_ayah.is_surah_start and start_ayah.surah_number != end_ayah.surah_number:
                bonus_penalty += self.config.weights.cross_surah_penalty * 0.6
            else:
                bonus_penalty += self.config.weights.cross_surah_penalty

        if is_forced_end:
            # Massive bonus to ensure forced boundary is selected
            bonus_penalty -= 100.0
            status = "override_applied"
            reason = "Manual override: forced boundary applied."

        total_cost = (
            self.config.weights.duration_weight * duration_cost
            + semantic_cost
            + bonus_penalty
        )

        return total_cost, b_score, status, reason
