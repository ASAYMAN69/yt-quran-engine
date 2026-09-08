"""End-to-end integration test across the entire 6,236 verses of the Quran."""

import pytest
from quran_engine.pipeline import QuranSegmentationEngine


def test_full_quran_segmentation():
    engine = QuranSegmentationEngine()
    result, report = engine.run_full_quran(export_outputs=False)
    
    # Absolute integrity verification
    assert report.is_valid is True
    assert report.total_covered_ayahs == 6236
    assert report.total_expected_ayahs == 6236
    assert report.missing_ayahs_count == 0
    assert report.duplicate_ayahs_count == 0
    assert report.order_violations_count == 0
    assert report.invalid_references_count == 0
    assert report.gaps_count == 0
    
    # Statistical sanity
    assert 2000 <= result.total_videos <= 3000
    assert 35.0 <= result.average_duration <= 45.0
