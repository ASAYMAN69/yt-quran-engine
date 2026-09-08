"""Tests for timing models and duration estimation."""

import pytest
from quran_engine.quran.loader import QuranLoader
from quran_engine.timing.loader import TimingLoader
from quran_engine.timing.duration import DurationModel


@pytest.fixture(scope="session")
def quran_and_timing():
    quran = QuranLoader().load()
    timings = TimingLoader().load()
    duration_model = DurationModel(exact_timings=timings)
    return quran, duration_model


def test_timing_loaded(quran_and_timing):
    quran, duration_model = quran_and_timing
    assert duration_model.has_full_exact_timings is True
    
    # Check 1:1 duration
    a1_1 = quran.get_ayah(1, 1)
    timing_1_1 = duration_model.get_ayah_timing(a1_1)
    assert 5.0 <= timing_1_1.duration_seconds <= 7.0
    assert timing_1_1.is_estimated is False


def test_passage_duration(quran_and_timing):
    quran, duration_model = quran_and_timing
    fatihah_ayahs = quran.get_surah(1).ayahs
    fatihah_dur = duration_model.get_passage_duration(fatihah_ayahs)
    assert 40.0 <= fatihah_dur <= 50.0


def test_fallback_estimation(quran_and_timing):
    quran, _ = quran_and_timing
    # DurationModel with empty exact timings to test fallback
    fallback_model = DurationModel(exact_timings={})
    a2_255 = quran.get_ayah(2, 255)
    est = fallback_model.get_ayah_timing(a2_255)
    assert est.is_estimated is True
    assert 40.0 <= est.duration_seconds <= 70.0
