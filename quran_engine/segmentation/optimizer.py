"""Global dynamic programming optimizer for Quran segmentation."""

from typing import Dict, List, Optional, Tuple, Any

from config.settings import EngineConfig
from quran_engine.quran.models import Ayah, Quran
from quran_engine.timing.duration import DurationModel
from quran_engine.semantic.analyzer import SemanticAnalyzer
from quran_engine.segmentation.models import CandidateSegment, VideoSegment, SegmentationResult
from quran_engine.segmentation.candidates import CandidateGenerator


class QuranOptimizer:
    """Finds the globally optimal sequence of video segments across the Quran."""

    def __init__(
        self,
        quran: Quran,
        duration_model: DurationModel,
        candidate_generator: CandidateGenerator,
        semantic_analyzer: SemanticAnalyzer,
        config: EngineConfig,
    ):
        self.quran = quran
        self.duration_model = duration_model
        self.candidate_generator = candidate_generator
        self.semantic_analyzer = semantic_analyzer
        self.config = config

    def optimize(
        self,
        start_global_idx: int = 0,
        end_global_idx: Optional[int] = None,
    ) -> SegmentationResult:
        """Runs dynamic programming optimization and returns the complete SegmentationResult."""
        total_ayahs = len(self.quran.ayahs)
        end_limit = total_ayahs if end_global_idx is None else min(total_ayahs, end_global_idx + 1)

        # DP state: dp[i] = min cost from index i to end_limit
        dp: Dict[int, float] = {end_limit: 0.0}
        best_cand: Dict[int, CandidateSegment] = {}

        # Backward DP pass
        for i in range(end_limit - 1, start_global_idx - 1, -1):
            candidates = self.candidate_generator.get_candidates(i)
            min_cost = float("inf")
            chosen: Optional[CandidateSegment] = None

            for cand in candidates:
                next_idx = cand.end_global_idx + 1
                if next_idx > end_limit:
                    continue

                future_cost = dp.get(next_idx, float("inf"))
                total_cost = cand.cost + future_cost

                if total_cost < min_cost:
                    min_cost = total_cost
                    chosen = cand

            if chosen is None and candidates:
                # If all exceed end_limit or have inf cost, choose first candidate
                chosen = candidates[0]
                min_cost = chosen.cost

            dp[i] = min_cost
            if chosen is not None:
                best_cand[i] = chosen

        # Forward reconstruction pass
        video_segments: List[VideoSegment] = []
        curr_idx = start_global_idx
        video_counter = 1

        while curr_idx < end_limit and curr_idx in best_cand:
            cand = best_cand[curr_idx]
            ayahs = cand.ayahs
            next_a = self.quran.ayahs[cand.end_global_idx + 1] if cand.end_global_idx + 1 < total_ayahs else None

            # Generate semantic explanation
            coherence = self.semantic_analyzer.analyze_passage(
                ayahs=ayahs,
                next_ayah=next_a,
                duration_seconds=cand.duration_seconds,
                target_seconds=self.config.duration.target_seconds,
            )

            # Build structural span metadata
            segments_meta = self._build_segments_meta(ayahs)

            # Build subtitle timings
            subtitles_timing = self._build_subtitles_timing(ayahs)

            # Combined texts
            ar_combined = " ".join(f"{a.text_ar} ﴿{a.ayah_number}﴾" for a in ayahs)
            en_combined = " ".join(f"({a.ayah_number}) {a.text_en}" for a in ayahs)

            video_seg = VideoSegment(
                video_id=video_counter,
                start_global_idx=cand.start_global_idx,
                end_global_idx=cand.end_global_idx,
                segments=segments_meta,
                ayah_count=len(ayahs),
                duration_seconds=cand.duration_seconds,
                is_estimated=cand.is_estimated,
                semantic_score=cand.boundary_score,
                boundary_score=cand.boundary_score,
                status=cand.status,
                reason=cand.reason or coherence.explanation,
                explanation=coherence.explanation,
                ayah_keys=[a.key for a in ayahs],
                arabic_text_combined=ar_combined,
                english_text_combined=en_combined,
                subtitles_timing=subtitles_timing,
            )

            video_segments.append(video_seg)
            video_counter += 1
            curr_idx = cand.end_global_idx + 1

        # Calculate result statistics
        return self._compute_statistics(video_segments, end_limit - start_global_idx)

    def _build_segments_meta(self, ayahs: List[Ayah]) -> List[Dict[str, Any]]:
        """Groups contiguous ayahs by surah into spans."""
        spans: List[Dict[str, Any]] = []
        if not ayahs:
            return spans

        current_surah = ayahs[0].surah_number
        current_surah_name = ayahs[0].surah_name_en
        start_ayah_num = ayahs[0].ayah_number
        prev_ayah_num = start_ayah_num

        for a in ayahs[1:]:
            if a.surah_number == current_surah and a.ayah_number == prev_ayah_num + 1:
                prev_ayah_num = a.ayah_number
            else:
                spans.append({
                    "surah": current_surah,
                    "surah_name": current_surah_name,
                    "start_ayah": start_ayah_num,
                    "end_ayah": prev_ayah_num,
                })
                current_surah = a.surah_number
                current_surah_name = a.surah_name_en
                start_ayah_num = a.ayah_number
                prev_ayah_num = a.ayah_number

        spans.append({
            "surah": current_surah,
            "surah_name": current_surah_name,
            "start_ayah": start_ayah_num,
            "end_ayah": prev_ayah_num,
        })
        return spans

    def _build_subtitles_timing(self, ayahs: List[Ayah]) -> List[Dict[str, Any]]:
        """Constructs per-ayah subtitle and audio timing details."""
        timing_list: List[Dict[str, Any]] = []
        offset = 0.0

        for a in ayahs:
            t_obj = self.duration_model.get_ayah_timing(a)
            dur = t_obj.duration_seconds
            timing_list.append({
                "verse_key": a.key,
                "surah": a.surah_number,
                "ayah": a.ayah_number,
                "start_seconds": round(offset, 3),
                "end_seconds": round(offset + dur, 3),
                "duration_seconds": round(dur, 3),
                "is_estimated": t_obj.is_estimated,
                "segments": t_obj.segments,
            })
            offset += dur

        return timing_list

    def _compute_statistics(self, videos: List[VideoSegment], total_expected_ayahs: int) -> SegmentationResult:
        """Computes summary metrics across all generated video segments."""
        if not videos:
            return SegmentationResult(
                videos=[],
                total_videos=0,
                total_ayahs=0,
                average_duration=0.0,
                min_duration=0.0,
                max_duration=0.0,
                within_target_range_count=0,
                below_target_count=0,
                above_target_count=0,
                exceptions_count=0,
                overrides_count=0,
                cross_surah_count=0,
            )

        total_v = len(videos)
        total_a = sum(v.ayah_count for v in videos)
        durations = [v.duration_seconds for v in videos]
        avg_dur = sum(durations) / max(1, total_v)
        min_dur = min(durations)
        max_dur = max(durations)

        min_pref = self.config.duration.min_preferred_seconds
        max_pref = self.config.duration.max_preferred_seconds

        within_target = sum(1 for d in durations if min_pref <= d <= max_pref)
        below_target = sum(1 for d in durations if d < min_pref)
        above_target = sum(1 for d in durations if d > max_pref)

        exceptions = sum(1 for v in videos if v.status in ("long_ayah_exception", "short_surah_standalone", "very_short", "very_long"))
        overrides = sum(1 for v in videos if "override" in v.status)
        cross_surahs = sum(1 for v in videos if len(v.segments) > 1)

        return SegmentationResult(
            videos=videos,
            total_videos=total_v,
            total_ayahs=total_a,
            average_duration=round(avg_dur, 2),
            min_duration=round(min_dur, 2),
            max_duration=round(max_dur, 2),
            within_target_range_count=within_target,
            below_target_count=below_target,
            above_target_count=above_target,
            exceptions_count=exceptions,
            overrides_count=overrides,
            cross_surah_count=cross_surahs,
        )
