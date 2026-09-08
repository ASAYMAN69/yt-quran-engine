"""Tests for deterministic validation engine."""

import pytest
from quran_engine.quran.loader import QuranLoader
from quran_engine.validation.validator import SegmentationValidator
from quran_engine.validation.models import SegmentationValidationError
from quran_engine.segmentation.models import VideoSegment, SegmentationResult


@pytest.fixture(scope="session")
def quran():
    return QuranLoader().load()


def test_validator_detects_gap(quran):
    validator = SegmentationValidator(quran=quran)
    
    # Intentionally missing 1:4
    video1 = VideoSegment(
        video_id=1,
        start_global_idx=0,
        end_global_idx=2,
        segments=[{"surah": 1, "surah_name": "Al-Faatiha", "start_ayah": 1, "end_ayah": 3}],
        ayah_count=3,
        duration_seconds=18.0,
        is_estimated=False,
        semantic_score=0.5,
        boundary_score=0.5,
        status="normal",
        reason="test",
        explanation="test",
        ayah_keys=["1:1", "1:2", "1:3"],
        arabic_text_combined="",
        english_text_combined="",
        subtitles_timing=[],
    )
    video2 = VideoSegment(
        video_id=2,
        start_global_idx=4,  # Skipped index 3 (1:4)
        end_global_idx=6,
        segments=[{"surah": 1, "surah_name": "Al-Faatiha", "start_ayah": 5, "end_ayah": 7}],
        ayah_count=3,
        duration_seconds=22.0,
        is_estimated=False,
        semantic_score=0.5,
        boundary_score=0.5,
        status="normal",
        reason="test",
        explanation="test",
        ayah_keys=["1:5", "1:6", "1:7"],
        arabic_text_combined="",
        english_text_combined="",
        subtitles_timing=[],
    )
    res = SegmentationResult(
        videos=[video1, video2],
        total_videos=2,
        total_ayahs=6,
        average_duration=20.0,
        min_duration=18.0,
        max_duration=22.0,
        within_target_range_count=0,
        below_target_count=2,
        above_target_count=0,
        exceptions_count=0,
        overrides_count=0,
        cross_surah_count=0,
    )
    
    report = validator.validate(res, expected_start_global_idx=0, expected_end_global_idx=6, raise_on_error=False)
    assert report.is_valid is False
    assert report.missing_ayahs_count == 1
    assert any("1:4" in e for e in report.errors)
