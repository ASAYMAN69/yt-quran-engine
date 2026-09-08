"""Linguistic and structural markers for Quranic semantic boundary detection."""

import re
from typing import List, Tuple

# Strip diacritics for robust pattern matching
ARABIC_DIACRITICS_REGEX = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u06DF-\u06E8\u0610-\u061A]")


def normalize_arabic(text: str) -> str:
    """Removes tashkeel (diacritics) and normalizes alefs/hamzas for regex matching."""
    text = ARABIC_DIACRITICS_REGEX.sub("", text)
    text = re.sub(r"[إأآٱ]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ة", "ه", text)
    return text.strip()


# Strong opening markers (indicates start of a new section / narrative / address)
OPENING_MARKERS: List[Tuple[str, str, float]] = [
    # Pattern, Explanation, Score bonus
    (r"^يا ايها الذين امنوا", "Vocative address to the believers", 0.45),
    (r"^يا ايها الناس", "Universal address to humanity", 0.45),
    (r"^يا بني اسرائيل", "Address to the Children of Israel", 0.45),
    (r"^يا اهل الكتاب", "Address to the People of the Scripture", 0.45),
    (r"^يا ايها النبي", "Direct divine address to the Prophet", 0.45),
    (r"^يا ايها الرسل", "Direct address to the Messengers", 0.40),
    (r"^يا عبادي", "Compassionate divine address to servants", 0.40),
    (r"^قل\b", "Direct imperative proclamation ('Say')", 0.35),
    (r"^(واذ|اذ)\b", "Narrative scene inception ('And when...')", 0.40),
    (r"^هل اتاك حديث", "Rhetorical narrative introduction", 0.45),
    (r"^الم تر( كيف| الى)?", "Reflective narrative opening ('Have you not seen...')", 0.40),
    (r"^تلك ايات", "Quranic discourse transition ('These are the verses...')", 0.40),
    (r"^يسالونك عن", "Inquiry / Legal question from companions", 0.40),
    (r"^يوم\b|^ويوم\b", "Eschatological scene opening ('The Day when...')", 0.35),
    (r"^اذا\b|^فاذا\b", "Cosmic conditional opening ('When...')", 0.35),
    (r"^ان الذين امنوا", "Thematic transition to the righteous", 0.35),
    (r"^ان الذين كفروا", "Thematic transition to the disbelievers", 0.35),
    (r"^مثل الذين", "Parable inception ('The example of those...')", 0.35),
    (r"^سبح\b|^يسبح\b", "Doxological opening of glorification", 0.35),
]

# Closing clausulae markers (indicates completion of argument / divine summary)
CLOSING_MARKERS: List[Tuple[str, str, float]] = [
    (r"ان الله غفور رحيم$", "Clausula: Divine forgiveness and mercy", 0.30),
    (r"ان الله على كل شيء قدير$", "Clausula: Divine omnipotence", 0.30),
    (r"والله عزيز حكيم$", "Clausula: Divine might and wisdom", 0.30),
    (r"والله بما تعملون خبير$", "Clausula: Divine awareness of deeds", 0.30),
    (r"والله سميع عليم$", "Clausula: Divine all-hearing, all-knowing", 0.30),
    (r"ان في ذلك لايه ل.*$", "Clausula: Deductive sign / lesson formula", 0.35),
    (r"ان في ذلك لعبره ل.*$", "Clausula: Moral lesson formula", 0.35),
    (r"لعلكم تتفكرون$|لعلكم تعقلون$|لعلهم يتذكرون$", "Clausula: Exhortation to intellect/reflection", 0.30),
    (r"وكفى بالله شهيدا$|وكفى بالله وكيلا$|وكفى بالله نصيرا$", "Clausula: Divine sufficiency", 0.30),
    (r"فباي الاء ربكما تكذبان$", "Refrain conclusion", 0.25),
]

# Tight grammatical continuation markers at start of next ayah (indicates BAD boundary to cut)
TIGHT_CONTINUATION_START_MARKERS: List[Tuple[str, str, float]] = [
    (r"^الذين\b", "Relative clause continuation ('Those who...')", -0.45),
    (r"^الا\b", "Exceptive clause continuation ('Except...')", -0.55),
    (r"^خالدين فيها", "Status descriptor continuation", -0.50),
    (r"^ليكون\b|^ليعلم\b|^ليبين\b", "Subjunctive purpose clause continuation", -0.45),
    (r"^ان\b", "Subordinating particle continuation", -0.30),
    (r"^ثم\b", "Sequential conjunction continuation", -0.20),
    (r"^او\b", "Alternative conjunction continuation", -0.30),
]

# English semantic transitions
ENGLISH_OPENING_PATTERNS: List[Tuple[str, str, float]] = [
    (r"^O you who have believed", "Direct address to the believers", 0.40),
    (r"^O mankind", "Universal address to humanity", 0.40),
    (r"^O Children of Israel", "Address to Children of Israel", 0.40),
    (r"^O People of the Scripture", "Address to People of Scripture", 0.40),
    (r"^Say,", "Direct divine command ('Say')", 0.35),
    (r"^(And )?[Aa]nd [wW]hen", "Narrative scene inception", 0.35),
    (r"^They ask you", "Question / response episode", 0.40),
    (r"^Indeed, those who", "Thematic statement transition", 0.30),
    (r"^Has there reached you", "Narrative inquiry opening", 0.40),
]
