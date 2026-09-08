"""Quran dataset and models module."""

from quran_engine.quran.models import Ayah, Surah, Quran
from quran_engine.quran.loader import QuranLoader

__all__ = ["Ayah", "Surah", "Quran", "QuranLoader"]
