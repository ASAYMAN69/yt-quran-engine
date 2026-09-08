"""Semantic analyzer for generating passage coherence summaries and explainability."""

from typing import List, Optional, Sequence
import re

from quran_engine.quran.models import Ayah
from quran_engine.semantic.models import PassageCoherence, SemanticBoundary
from quran_engine.semantic.boundaries import SemanticBoundaryScorer


class SemanticAnalyzer:
    """Analyzes whole passages, generates explanations, and evaluates coherence."""

    def __init__(self, boundary_scorer: Optional[SemanticBoundaryScorer] = None):
        self.boundary_scorer = boundary_scorer or SemanticBoundaryScorer()

    def analyze_passage(
        self,
        ayahs: Sequence[Ayah],
        next_ayah: Optional[Ayah],
        duration_seconds: float,
        target_seconds: float = 40.0,
    ) -> PassageCoherence:
        """Analyzes a candidate passage and produces a human-readable explanation."""
        if not ayahs:
            raise ValueError("Cannot analyze empty ayah sequence.")

        start_a = ayahs[0]
        end_a = ayahs[-1]
        boundary = self.boundary_scorer.evaluate_boundary(end_a, next_ayah)

        # Generate summary theme
        theme = self._extract_passage_theme(ayahs)

        # Generate human-readable explanation
        explanation_lines: List[str] = []

        # Opening context
        if start_a.is_surah_start:
            explanation_lines.append(f"Begins at the opening of Surah {start_a.surah_name_en} ({start_a.surah_number}).")
        else:
            explanation_lines.append(f"Begins at {start_a.key} following the preceding passage.")

        # Passage narrative & length
        if len(ayahs) == 1:
            explanation_lines.append(f"Contains single complete verse {start_a.key}.")
        else:
            explanation_lines.append(f"Encompasses {len(ayahs)} verses ({start_a.key} to {end_a.key}) forming a cohesive thematic unit.")

        # Closing boundary rationale
        for r in boundary.reasons:
            explanation_lines.append(f"Ending rationale: {r}")

        # Duration assessment
        if 35.0 <= duration_seconds <= 45.0:
            explanation_lines.append(f"Duration of {duration_seconds:.1f}s is within the optimal 35–45s window.")
        elif duration_seconds < 35.0:
            if end_a.is_surah_end:
                explanation_lines.append(f"Duration of {duration_seconds:.1f}s is shorter than target due to natural Surah conclusion.")
            else:
                explanation_lines.append(f"Duration of {duration_seconds:.1f}s chosen to preserve a natural semantic break.")
        else:
            if len(ayahs) == 1:
                explanation_lines.append(f"Duration of {duration_seconds:.1f}s reflects a single long ayah that cannot be divided.")
            else:
                explanation_lines.append(f"Duration of {duration_seconds:.1f}s accommodates an extended connected passage.")

        return PassageCoherence(
            start_ayah=start_a,
            end_ayah=end_a,
            ayah_count=len(ayahs),
            boundary_score=boundary.score,
            summary_theme=theme,
            explanation=" ".join(explanation_lines),
            reasons=boundary.reasons,
        )

    def _extract_passage_theme(self, ayahs: Sequence[Ayah]) -> str:
        """Extracts brief descriptive theme from English text keywords."""
        first_en = ayahs[0].text_en
        last_en = ayahs[-1].text_en

        # Heuristic detection for common Quranic themes
        combined_en = " ".join(a.text_en for a in ayahs).lower()

        if "o you who have believed" in combined_en:
            return "Commandments to the Believers"
        elif "children of israel" in combined_en or "moses" in combined_en or "pharaoh" in combined_en:
            return "Prophetic Narrative & Historical Lessons"
        elif "abraham" in combined_en or "joseph" in combined_en or "noah" in combined_en or "jesus" in combined_en or "mary" in combined_en:
            return "Prophetic Stories & Reflections"
        elif "day of resurrection" in combined_en or "judgment" in combined_en or "paradise" in combined_en or "hellfire" in combined_en or "gardens" in combined_en:
            return "Eschatology, Resurrection & Retribution"
        elif "heavens and earth" in combined_en or "signs" in combined_en or "rain" in combined_en:
            return "Cosmic Signs of Divine Creation"
        elif "praise" in combined_en or "glorify" in combined_en or "allah" in combined_en:
            return "Divine Oneness, Attributes & Worship"
        else:
            # Fallback to truncated English opening
            clean = re.sub(r"[^\w\s]", "", first_en)
            words = clean.split()[:6]
            return " ".join(words) + "..."
