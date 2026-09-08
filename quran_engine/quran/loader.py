"""Loader for Quran datasets (Arabic Uthmani script and English translations)."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import urllib.request

from quran_engine.quran.models import Ayah, Surah, Quran


class QuranLoader:
    """Loads, verifies, and constructs the in-memory Quran corpus."""

    ARABIC_DEFAULT_URL = "https://api.alquran.cloud/v1/quran/quran-uthmani"
    ENGLISH_DEFAULT_URL = "https://api.alquran.cloud/v1/quran/en.sahih"
    META_DEFAULT_URL = "https://api.alquran.cloud/v1/meta"

    def __init__(
        self,
        arabic_path: str = "data/quran_ar_uthmani.json",
        english_path: str = "data/quran_en_sahih.json",
        meta_path: Optional[str] = "data/quran_meta.json",
        auto_download: bool = True,
    ):
        self.arabic_path = Path(arabic_path)
        self.english_path = Path(english_path)
        self.meta_path = Path(meta_path) if meta_path else None
        self.auto_download = auto_download

    def _ensure_file(self, path: Path, url: str) -> None:
        if not path.exists():
            if not self.auto_download:
                raise FileNotFoundError(f"Quran dataset missing at {path} and auto_download is disabled.")
            path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Quran-Daily-Dose-Engine"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                with open(path, "wb") as f:
                    f.write(content)

    def load(self) -> Quran:
        """Loads and returns the validated Quran instance."""
        self._ensure_file(self.arabic_path, self.ARABIC_DEFAULT_URL)
        self._ensure_file(self.english_path, self.ENGLISH_DEFAULT_URL)

        with open(self.arabic_path, "r", encoding="utf-8") as f:
            ar_data = json.load(f)
        with open(self.english_path, "r", encoding="utf-8") as f:
            en_data = json.load(f)

        ar_surahs = ar_data.get("data", {}).get("surahs", [])
        en_surahs = en_data.get("data", {}).get("surahs", [])

        if len(ar_surahs) != 114:
            raise ValueError(f"Expected 114 Surahs in Arabic data, found {len(ar_surahs)}")
        if len(en_surahs) != 114:
            raise ValueError(f"Expected 114 Surahs in English data, found {len(en_surahs)}")

        # Build surahs and ayahs
        surah_list: List[Surah] = []
        ayah_list: List[Ayah] = []
        global_idx = 0

        for s_idx, (ar_s, en_s) in enumerate(zip(ar_surahs, en_surahs), start=1):
            s_num = ar_s["number"]
            s_name_ar = ar_s["name"]
            s_name_en = ar_s["englishName"]
            s_name_trans = ar_s["englishNameTranslation"]
            s_rev_type = ar_s.get("revelationType", "Meccan")
            
            ar_ayahs = ar_s["ayahs"]
            en_ayahs = en_s["ayahs"]
            ayah_count = len(ar_ayahs)

            if len(en_ayahs) != ayah_count:
                raise ValueError(f"Surah {s_num} ayah count mismatch: AR={ayah_count} vs EN={len(en_ayahs)}")

            current_surah_ayahs: List[Ayah] = []

            for a_idx, (ar_a, en_a) in enumerate(zip(ar_ayahs, en_ayahs), start=1):
                is_first = (a_idx == 1)
                is_last = (a_idx == ayah_count)
                
                # Check ruku end: check if next ayah has different ruku or is last in surah
                ruku_num = ar_a.get("ruku", 1)
                is_ruku_end = False
                if is_last:
                    is_ruku_end = True
                elif a_idx < ayah_count and ar_ayahs[a_idx].get("ruku", 1) != ruku_num:
                    is_ruku_end = True

                sajda_val = ar_a.get("sajda", False)
                has_sajda = bool(sajda_val)

                ayah_obj = Ayah(
                    global_index=global_idx,
                    surah_number=s_num,
                    surah_name_ar=s_name_ar,
                    surah_name_en=s_name_en,
                    surah_name_translation=s_name_trans,
                    ayah_number=a_idx,
                    text_ar=ar_a["text"].strip(" \t\r\n\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e"),
                    text_en=en_a["text"].strip(" \t\r\n\ufeff"),
                    juz=ar_a.get("juz", 1),
                    hizb_quarter=ar_a.get("hizbQuarter", 1),
                    manzil=ar_a.get("manzil", 1),
                    ruku=ruku_num,
                    page=ar_a.get("page", 1),
                    sajdah=has_sajda,
                    is_surah_start=is_first,
                    is_surah_end=is_last,
                    is_ruku_end=is_ruku_end,
                )
                current_surah_ayahs.append(ayah_obj)
                ayah_list.append(ayah_obj)
                global_idx += 1

            surah_obj = Surah(
                number=s_num,
                name_ar=s_name_ar,
                name_en=s_name_en,
                name_translation=s_name_trans,
                revelation_type=s_rev_type,
                ayah_count=ayah_count,
                ayahs=current_surah_ayahs,
            )
            surah_list.append(surah_obj)

        if len(ayah_list) != 6236:
            raise ValueError(f"Total ayahs count is {len(ayah_list)}, expected exactly 6236.")

        return Quran(surahs=surah_list, ayahs=ayah_list)
