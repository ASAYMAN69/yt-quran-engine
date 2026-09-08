"""Candidate segment generator producing valid passage transitions."""

from typing import Dict, List, Optional

from config.settings import EngineConfig
from quran_engine.quran.models import Ayah, Quran
from quran_engine.timing.duration import DurationModel
from quran_engine.segmentation.models import CandidateSegment
from quran_engine.segmentation.scoring import SegmentScorer


class CandidateGenerator:
    """Generates candidate segments starting from any verse index."""

    def __init__(
        self,
        quran: Quran,
        duration_model: DurationModel,
        scorer: SegmentScorer,
        config: EngineConfig,
    ):
        self.quran = quran
        self.duration_model = duration_model
        self.scorer = scorer
        self.config = config
        self._cache: Dict[int, List[CandidateSegment]] = {}

    def get_candidates(self, start_idx: int) -> List[CandidateSegment]:
        """Generates all viable candidate segments starting at start_idx."""
        if start_idx in self._cache:
            return self._cache[start_idx]

        total_ayahs = len(self.quran.ayahs)
        if start_idx >= total_ayahs:
            return []

        candidates: List[CandidateSegment] = []
        max_lookahead = self.config.rules.max_ayahs_per_segment
        hard_max_dur = self.config.duration.hard_max_seconds
        allow_cross = self.config.rules.allow_cross_surah

        current_ayahs: List[Ayah] = []
        current_dur = 0.0

        for offset in range(max_lookahead):
            current_idx = start_idx + offset
            if current_idx >= total_ayahs:
                break

            ayah = self.quran.ayahs[current_idx]
            current_ayahs.append(ayah)
            ayah_dur = self.duration_model.get_ayah_duration(ayah)
            current_dur += ayah_dur

            # Cross surah check
            if not allow_cross and current_ayahs[0].surah_number != ayah.surah_number:
                break

            # If duration exceeds hard_max and we have more than 1 ayah, break
            if offset > 0 and current_dur > hard_max_dur:
                break

            # Next ayah for boundary context
            next_ayah: Optional[Ayah] = None
            if current_idx + 1 < total_ayahs:
                next_ayah = self.quran.ayahs[current_idx + 1]

            # Score this candidate
            cost, b_score, status, reason = self.scorer.score_candidate(
                ayahs=current_ayahs,
                next_ayah=next_ayah,
                duration=current_dur,
            )

            if cost != float("inf"):
                is_est = self.duration_model.is_passage_estimated(current_ayahs)
                crosses = (current_ayahs[0].surah_number != current_ayahs[-1].surah_number)
                cand = CandidateSegment(
                    start_global_idx=start_idx,
                    end_global_idx=current_idx,
                    ayahs=list(current_ayahs),
                    duration_seconds=round(current_dur, 2),
                    boundary_score=b_score,
                    cost=cost,
                    is_estimated=is_est,
                    crosses_surah=crosses,
                    status=status,
                    reason=reason,
                )
                candidates.append(cand)

        # Fallback safeguard: if no candidates were admitted (e.g. strict override conflict),
        # ensure at least the single ayah is returned to prevent DP dead-ends
        if not candidates and start_idx < total_ayahs:
            single = [self.quran.ayahs[start_idx]]
            dur = self.duration_model.get_ayah_duration(single[0])
            next_a = self.quran.ayahs[start_idx + 1] if start_idx + 1 < total_ayahs else None
            b = self.scorer.boundary_scorer.evaluate_boundary(single[0], next_a)
            cand = CandidateSegment(
                start_global_idx=start_idx,
                end_global_idx=start_idx,
                ayahs=single,
                duration_seconds=round(dur, 2),
                boundary_score=b.score,
                cost=100.0,
                is_estimated=self.duration_model.is_passage_estimated(single),
                crosses_surah=False,
                status="single_ayah_fallback",
                reason="Fallback single ayah to prevent segmentation graph disconnection",
            )
            candidates.append(cand)

        self._cache[start_idx] = candidates
        return candidates
