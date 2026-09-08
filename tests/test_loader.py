"""Tests for Quran dataset loading and models."""

import pytest
from quran_engine.quran.loader import QuranLoader
from quran_engine.quran.models import Quran, Surah, Ayah


@pytest.fixture(scope="session")
def quran_corpus() -> Quran:
    loader = QuranLoader(
        arabic_path="data/quran_ar_uthmani.json",
        english_path="data/quran_en_sahih.json",
        meta_path="data/quran_meta.json",
    )
    return loader.load()


def test_quran_corpus_structure(quran_corpus: Quran):
    assert quran_corpus.total_surahs == 114
    assert quran_corpus.total_ayahs == 6236


def test_al_fatihah(quran_corpus: Quran):
    fatihah = quran_corpus.get_surah(1)
    assert fatihah.ayah_count == 7
    assert len(fatihah.ayahs) == 7
    assert fatihah.ayahs[0].key == "1:1"
    assert fatihah.ayahs[0].is_surah_start is True
    assert fatihah.ayahs[-1].key == "1:7"
    assert fatihah.ayahs[-1].is_surah_end is True


def test_an_nas(quran_corpus: Quran):
    nas = quran_corpus.get_surah(114)
    assert nas.ayah_count == 6
    assert nas.ayahs[0].key == "114:1"
    assert nas.ayahs[-1].key == "114:6"
    assert nas.ayahs[-1].global_index == 6235


def test_ayah_lookups(quran_corpus: Quran):
    kursi = quran_corpus.get_ayah(2, 255)
    assert kursi.key == "2:255"
    assert "ٱللَّهُ" in kursi.text_ar
    assert "Allah - there is no deity except Him" in kursi.text_en
    assert kursi.juz == 3
