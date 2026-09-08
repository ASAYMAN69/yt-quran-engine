"""Tests for semantic boundary scorer and markers."""

import pytest
from quran_engine.quran.loader import QuranLoader
from quran_engine.semantic.boundaries import SemanticBoundaryScorer


@pytest.fixture(scope="session")
def quran():
    return QuranLoader().load()


def test_surah_boundary_score(quran):
    scorer = SemanticBoundaryScorer()
    fatihah_last = quran.get_ayah(1, 7)
    baqarah_first = quran.get_ayah(2, 1)
    
    boundary = scorer.evaluate_boundary(fatihah_last, baqarah_first)
    assert boundary.is_surah_boundary is True
    assert boundary.score >= 0.85
    assert any("Complete ending of Surah" in r for r in boundary.reasons)


def test_opening_marker_detection(quran):
    scorer = SemanticBoundaryScorer()
    # 2:20 -> 2:21 (2:21 begins with 'Yaa ayyuhan-naas' - vocative address)
    a2_20 = quran.get_ayah(2, 20)
    a2_21 = quran.get_ayah(2, 21)
    
    boundary = scorer.evaluate_boundary(a2_20, a2_21)
    assert boundary.score >= 0.80
    assert any("Universal address to humanity" in r for r in boundary.reasons)


def test_quran_end_boundary(quran):
    scorer = SemanticBoundaryScorer()
    last_ayah = quran.get_ayah(114, 6)
    boundary = scorer.evaluate_boundary(last_ayah, None)
    assert boundary.score == 1.0
    assert boundary.is_surah_boundary is True
