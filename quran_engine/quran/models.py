"""Quran data models representing Ayahs, Surahs, and the entire Quran corpus."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class Ayah:
    """Represents a single verse (ayah) of the Quran with all textual and structural metadata."""
    global_index: int  # 0 to 6235 (linear index across the whole Quran)
    surah_number: int  # 1 to 114
    surah_name_ar: str
    surah_name_en: str
    surah_name_translation: str
    ayah_number: int  # 1-based index within the surah
    text_ar: str
    text_en: str
    juz: int
    hizb_quarter: int
    manzil: int
    ruku: int
    page: int
    sajdah: bool = False
    is_surah_start: bool = False
    is_surah_end: bool = False
    is_ruku_end: bool = False

    @property
    def key(self) -> str:
        """Returns standard verse key format 'surah:ayah' (e.g., '2:255')."""
        return f"{self.surah_number}:{self.ayah_number}"

    @property
    def word_count_ar(self) -> int:
        """Returns approximate word count of Arabic text."""
        return len(self.text_ar.split())

    @property
    def char_count_ar(self) -> int:
        """Returns character length of Arabic text."""
        return len(self.text_ar)

    @property
    def word_count_en(self) -> int:
        """Returns word count of English text."""
        return len(self.text_en.split())

    def __repr__(self) -> str:
        return f"Ayah({self.key}, juz={self.juz}, page={self.page})"


@dataclass
class Surah:
    """Represents a chapter (surah) of the Quran."""
    number: int  # 1 to 114
    name_ar: str
    name_en: str
    name_translation: str
    revelation_type: str  # "Meccan" or "Medinan"
    ayah_count: int
    ayahs: List[Ayah] = field(default_factory=list)

    def get_ayah(self, ayah_number: int) -> Ayah:
        if 1 <= ayah_number <= len(self.ayahs):
            return self.ayahs[ayah_number - 1]
        raise IndexError(f"Ayah {ayah_number} out of range for Surah {self.number} (1..{len(self.ayahs)})")


@dataclass
class Quran:
    """Complete Quran representation containing all 114 Surahs and 6,236 Ayahs."""
    surahs: List[Surah] = field(default_factory=list)
    ayahs: List[Ayah] = field(default_factory=list)
    _key_index: Dict[str, Ayah] = field(default_factory=dict, init=False, repr=False)
    _surah_map: Dict[int, Surah] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self._key_index = {a.key: a for a in self.ayahs}
        self._surah_map = {s.number: s for s in self.surahs}

    @property
    def total_ayahs(self) -> int:
        return len(self.ayahs)

    @property
    def total_surahs(self) -> int:
        return len(self.surahs)

    def get_ayah(self, surah_number: int, ayah_number: int) -> Ayah:
        key = f"{surah_number}:{ayah_number}"
        if key not in self._key_index:
            raise KeyError(f"Ayah {key} does not exist in Quran.")
        return self._key_index[key]

    def get_by_key(self, key: str) -> Ayah:
        if key not in self._key_index:
            raise KeyError(f"Ayah {key} does not exist in Quran.")
        return self._key_index[key]

    def get_by_global_index(self, index: int) -> Ayah:
        if 0 <= index < len(self.ayahs):
            return self.ayahs[index]
        raise IndexError(f"Global index {index} out of bounds (0..{len(self.ayahs) - 1})")

    def get_surah(self, surah_number: int) -> Surah:
        if surah_number not in self._surah_map:
            raise KeyError(f"Surah {surah_number} does not exist.")
        return self._surah_map[surah_number]

    def slice_ayahs(self, start_global_idx: int, end_global_idx: int) -> List[Ayah]:
        """Returns contiguous ayahs between start_global_idx and end_global_idx (inclusive)."""
        return self.ayahs[start_global_idx : end_global_idx + 1]
