"""Tests for dynamic programming segmentation optimizer."""

import pytest
from quran_engine.pipeline import QuranSegmentationEngine
from config.settings import EngineConfig


def test_optimizer_al_fatihah():
    engine = QuranSegmentationEngine()
    result, report = engine.run_surah_range(1, 1, export_outputs=False)
    
    assert report.is_valid is True
    assert result.total_videos == 1
    assert result.videos[0].ayah_count == 7
    assert result.videos[0].ayah_keys == ["1:1", "1:2", "1:3", "1:4", "1:5", "1:6", "1:7"]


def test_optimizer_short_surahs():
    engine = QuranSegmentationEngine()
    result, report = engine.run_surah_range(108, 114, export_outputs=False)
    
    assert report.is_valid is True
    assert result.total_videos >= 5
    assert result.total_ayahs == sum(engine.quran.get_surah(s).ayah_count for s in range(108, 115))
