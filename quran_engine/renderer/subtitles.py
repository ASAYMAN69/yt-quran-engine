"""Smart ASS subtitle generator with dynamic auto-sizing, safe UI margins, and balanced hierarchy."""

import re
from pathlib import Path
from typing import List, Tuple

from quran_engine.quran.models import Ayah
from quran_engine.segmentation.models import VideoSegment


def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS timestamp format H:MM:SS.cc (e.g. 0:00:04.25)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def strip_tashkeel(text: str) -> str:
    """Strips Arabic diacritics (harakat/tashkeel) for accurate visual width measurement."""
    return re.sub(r'[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]', '', text)


def smart_wrap(text: str, max_chars_per_line: int) -> str:
    """Wraps text naturally at punctuation or word boundaries without awkward breaks."""
    words = text.split()
    if not words:
        return ""

    lines = []
    current_line = []
    current_len = 0

    for w in words:
        if current_len + len(w) + 1 > max_chars_per_line and current_line:
            lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
        else:
            current_line.append(w)
            current_len += len(w) + 1

    if current_line:
        lines.append(" ".join(current_line))

    return r"\N".join(lines)


def smart_wrap_arabic(text: str, max_base_chars_per_line: int) -> str:
    """Wraps Arabic text based on base-letter length (ignoring diacritics) so it uses the full text box width."""
    words = text.split()
    if not words:
        return ""

    lines = []
    current_line = []
    current_base_len = 0

    for w in words:
        w_base_len = len(strip_tashkeel(w))
        if current_base_len + w_base_len + 1 > max_base_chars_per_line and current_line:
            lines.append(" ".join(current_line))
            current_line = [w]
            current_base_len = w_base_len
        else:
            current_line.append(w)
            current_base_len += w_base_len + 1

    if current_line:
        lines.append(" ".join(current_line))

    return r"\N".join(lines)


class SubtitleGenerator:
    """Generates auto-sized, centered typography with Reels/Shorts safe margin zones."""

    def generate_ass(
        self,
        video_segment: VideoSegment,
        ayahs: List[Ayah],
        durations: List[float],
        output_ass_path: Path,
    ) -> Path:
        """Constructs ASS file with dynamic font sizing per ayah and UI button safe zones."""
        output_ass_path = Path(output_ass_path)
        output_ass_path.parent.mkdir(parents=True, exist_ok=True)

        surah_names = ", ".join(s["surah_name"] for s in video_segment.segments)
        total_ayahs = len(ayahs)

        # Base ASS Header:
        # Note: MarginL=90, MarginR=90 provides an expanded 900px usable width text box (1080 - 2*90)
        ass_lines = [
            "[Script Info]",
            "Title: Daily Dose of Quran",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # Header Title at top center
            "Style: Header,Cormorant Garamond,46,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,0,1,8,90,90,150,1",
            # Ayah indicator badge top center
            "Style: Badge,Cormorant Garamond,36,&H004FD1C5,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,1,8,90,90,225,1",
            # Dynamic styles instantiated inline using ASS overrides
            "Style: DefaultArabic,Amiri Quran,74,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,0,2,5,90,90,0,1",
            "Style: DefaultEnglish,Cormorant Garamond,70,&H00F8FAFC,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,0,2,5,90,90,0,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        total_duration = sum(durations)
        start_total = format_ass_time(0.0)
        end_total = format_ass_time(total_duration)

        # Header Title
        ass_lines.append(f"Dialogue: 0,{start_total},{end_total},Header,,90,90,0,,DAILY DOSE OF QURAN")

        # Per Ayah Events with Expanded Width Auto-Sizing & Tight Vertical Spacing
        center_x = 540
        current_time = 0.0

        for idx, (ayah, dur) in enumerate(zip(ayahs, durations), start=1):
            a_start = format_ass_time(current_time)
            a_end = format_ass_time(current_time + dur)

            # Badge: Single verse count e.g. "VERSE 1 OF 7"
            badge_text = f"VERSE {idx} OF {total_ayahs}"
            ass_lines.append(f"Dialogue: 1,{a_start},{a_end},Badge,,90,90,0,,{badge_text}")

            clean_ar = ayah.text_ar.strip(" \t\r\n\ufeff\u200e\u200f")
            clean_en = ayah.text_en.strip(" \t\r\n\ufeff")

            base_ar = strip_tashkeel(clean_ar)
            base_ar_len = len(base_ar)
            en_len = len(clean_en)

            # 1. Dynamic Auto-Sizing for Arabic Text across the full 900px width
            if base_ar_len <= 30:
                font_size_ar = 76
                max_base_chars_ar = 34  # Ensures 1 single full-width line for short ayahs
            elif base_ar_len <= 65:
                font_size_ar = 66
                max_base_chars_ar = 38
            elif base_ar_len <= 110:
                font_size_ar = 56
                max_base_chars_ar = 44
            else:
                font_size_ar = 48
                max_base_chars_ar = 50

            # 2. Dynamic Auto-Sizing for English Text across the full 900px width
            if en_len <= 45:
                font_size_en = 74
                max_chars_en = 32
            elif en_len <= 90:
                font_size_en = 66
                max_chars_en = 38
            elif en_len <= 150:
                font_size_en = 56
                max_chars_en = 44
            else:
                font_size_en = 48
                max_chars_en = 50

            wrapped_ar = smart_wrap_arabic(clean_ar, max_base_chars_ar)
            wrapped_en = smart_wrap(clean_en, max_chars_en)

            ar_lines = wrapped_ar.count(r"\N") + 1
            en_lines = wrapped_en.count(r"\N") + 1

            # Tight vertical grouping centered around 960 (middle of the 1:1 video box at y=420..1500)
            if ar_lines == 1 and en_lines == 1:
                pos_y_ar = 910
                pos_y_en = 995
            elif ar_lines == 1 and en_lines == 2:
                pos_y_ar = 895
                pos_y_en = 1005
            elif ar_lines == 1 and en_lines >= 3:
                pos_y_ar = 875
                pos_y_en = 1000
            elif ar_lines == 2 and en_lines <= 2:
                pos_y_ar = 880
                pos_y_en = 1020
            elif ar_lines == 2 and en_lines >= 3:
                pos_y_ar = 860
                pos_y_en = 1030
            else:
                # 3+ lines Arabic / long passage
                pos_y_ar = 835
                pos_y_en = 1045

            ar_dialogue = f"{{\\fs{font_size_ar}\\an5\\pos({center_x},{pos_y_ar})}}{wrapped_ar}"
            en_dialogue = f"{{\\fs{font_size_en}\\an5\\pos({center_x},{pos_y_en})}}{wrapped_en}"

            ass_lines.append(f"Dialogue: 2,{a_start},{a_end},DefaultArabic,,90,90,0,,{ar_dialogue}")
            ass_lines.append(f"Dialogue: 2,{a_start},{a_end},DefaultEnglish,,90,90,0,,{en_dialogue}")

            current_time += dur

        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_lines))

        return output_ass_path
