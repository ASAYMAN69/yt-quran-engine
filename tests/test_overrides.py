"""Tests for manual override rules."""

import pytest
from quran_engine.overrides.manager import OverrideManager, ForceBoundaryRule, KeepTogetherRule
from quran_engine.pipeline import QuranSegmentationEngine


def test_override_force_boundary():
    manager = OverrideManager(force_boundaries=[ForceBoundaryRule(surah=12, ayah=29)])
    a12_29 = AyahTimingObj = None
    engine = QuranSegmentationEngine()
    a12_29 = engine.quran.get_ayah(12, 29)
    assert manager.is_boundary_forced(a12_29) is True


def test_override_keep_together():
    manager = OverrideManager(keep_togethers=[KeepTogetherRule(surah=12, start_ayah=23, end_ayah=29)])
    engine = QuranSegmentationEngine()
    a12_24 = engine.quran.get_ayah(12, 24)
    assert manager.is_boundary_forbidden(a12_24) is True
