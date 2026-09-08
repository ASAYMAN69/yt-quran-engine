"""Deterministic validator verifying Quranic integrity, coverage, order, and references."""

from typing import Dict, List, Optional, Set, Tuple

from quran_engine.quran.models import Ayah, Quran
from quran_engine.segmentation.models import SegmentationResult, VideoSegment
from quran_engine.validation.models import ValidationReport, SegmentationValidationError


class SegmentationValidator:
    """Validates that a segmentation result strictly satisfies all Quranic integrity constraints."""

    def __init__(self, quran: Quran):
        self.quran = quran

    def validate(
        self,
        result: SegmentationResult,
        expected_start_global_idx: int = 0,
        expected_end_global_idx: Optional[int] = None,
        raise_on_error: bool = True,
    ) -> ValidationReport:
        """
        Runs comprehensive deterministic checks over the segmentation result.
        Raises SegmentationValidationError if raise_on_error is True and any errors are found.
        """
        total_quran_ayahs = len(self.quran.ayahs)
        end_limit = total_quran_ayahs if expected_end_global_idx is None else expected_end_global_idx + 1
        expected_ayah_count = end_limit - expected_start_global_idx

        expected_ayahs = self.quran.ayahs[expected_start_global_idx:end_limit]
        expected_keys_set: Set[str] = {a.key for a in expected_ayahs}

        errors: List[str] = []
        warnings: List[str] = []

        seen_keys: Dict[str, int] = {}  # key -> video_id
        last_global_index = expected_start_global_idx - 1

        for v_idx, video in enumerate(result.videos, start=1):
            # Check video id sequence
            if video.video_id != v_idx:
                errors.append(f"Video sequence error: expected Video ID {v_idx}, found {video.video_id}")

            # Check spans inside video
            if not video.segments:
                errors.append(f"Video {video.video_id} contains no segment spans.")
                continue

            for span in video.segments:
                s_num = span.get("surah")
                start_a = span.get("start_ayah")
                end_a = span.get("end_ayah")

                # Check surah existence
                if not (1 <= s_num <= 114):
                    errors.append(f"Video {video.video_id} references invalid Surah number {s_num}")
                    continue

                surah_obj = self.quran.get_surah(s_num)
                if not (1 <= start_a <= surah_obj.ayah_count) or not (1 <= end_a <= surah_obj.ayah_count):
                    errors.append(f"Video {video.video_id} references invalid ayah range {start_a}..{end_a} in Surah {s_num} (max {surah_obj.ayah_count})")
                    continue

                if start_a > end_a:
                    errors.append(f"Video {video.video_id} has start_ayah ({start_a}) > end_ayah ({end_a}) in Surah {s_num}")

            # Check each individual ayah in video
            for key in video.ayah_keys:
                # 1. Valid reference
                try:
                    ayah_obj = self.quran.get_by_key(key)
                except KeyError:
                    errors.append(f"Video {video.video_id} references non-existent ayah key: {key}")
                    continue

                # 2. Duplicate check
                if key in seen_keys:
                    prev_vid = seen_keys[key]
                    errors.append(f"Duplicate Ayah {key} detected in Video {video.video_id} (previously in Video {prev_vid})")
                else:
                    seen_keys[key] = video.video_id

                # 3. Order and Gap check
                expected_next_index = last_global_index + 1
                if ayah_obj.global_index != expected_next_index:
                    if ayah_obj.global_index < expected_next_index:
                        errors.append(f"Order violation: Ayah {key} (idx {ayah_obj.global_index}) appeared after idx {last_global_index} in Video {video.video_id}")
                    else:
                        missed_count = ayah_obj.global_index - expected_next_index
                        missed_sample = self.quran.ayahs[expected_next_index].key
                        errors.append(f"Gap detected: {missed_count} ayah(s) skipped before Ayah {key} in Video {video.video_id} (missing from {missed_sample})")

                last_global_index = ayah_obj.global_index

        # 4. Coverage check
        missing_keys = expected_keys_set - set(seen_keys.keys())
        for mk in sorted(list(missing_keys)):
            errors.append(f"Coverage error: Ayah {mk} is completely missing from segmentation.")

        covered_count = len(seen_keys)
        missing_count = len(missing_keys)
        dup_count = sum(1 for e in errors if "Duplicate" in e)
        order_count = sum(1 for e in errors if "Order violation" in e)
        gaps_count = sum(1 for e in errors if "Gap detected" in e)
        invalid_ref_count = sum(1 for e in errors if "invalid" in e or "non-existent" in e)

        is_valid = (len(errors) == 0) and (covered_count == expected_ayah_count)

        report = ValidationReport(
            is_valid=is_valid,
            total_expected_ayahs=expected_ayah_count,
            total_covered_ayahs=covered_count,
            missing_ayahs_count=missing_count,
            duplicate_ayahs_count=dup_count,
            invalid_references_count=invalid_ref_count,
            order_violations_count=order_count,
            gaps_count=gaps_count,
            errors=errors,
            warnings=warnings,
        )

        if raise_on_error and not is_valid:
            error_summary = "\n".join(errors[:10])
            if len(errors) > 10:
                error_summary += f"\n... and {len(errors) - 10} more errors."
            raise SegmentationValidationError(
                f"Segmentation validation failed with {len(errors)} error(s):\n{error_summary}",
                errors=errors,
            )

        return report
