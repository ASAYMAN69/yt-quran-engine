"""Human-readable segmentation report and quality-control report generator."""

from pathlib import Path
from typing import List, Union

from quran_engine.segmentation.models import SegmentationResult, VideoSegment
from quran_engine.validation.models import ValidationReport


class ReportGenerator:
    """Generates human-readable Markdown reports and Quality Control flags."""

    def __init__(self, output_dir: Union[str, Path] = "output"):
        self.output_dir = Path(output_dir)

    def generate_summary_report(
        self,
        result: SegmentationResult,
        validation_report: ValidationReport,
        filename: str = "segmentation_report.md",
    ) -> Path:
        """Generates the primary Quran Segmentation Summary Report."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / filename

        pct_within = (result.within_target_range_count / max(1, result.total_videos)) * 100

        lines: List[str] = [
            "# 📖 QURAN SEGMENTATION REPORT — DAILY DOSE OF QURAN",
            "",
            "## 1. Executive Summary",
            f"- **Total Quranic Ayahs Processed:** {result.total_ayahs:,}",
            f"- **Total Generated Video Segments:** {result.total_videos:,}",
            f"- **Average Video Duration:** {result.average_duration:.1f}s",
            f"- **Min / Max Duration:** {result.min_duration:.1f}s / {result.max_duration:.1f}s",
            f"- **Videos in Preferred Range (35–45s):** {result.within_target_range_count} ({pct_within:.1f}%)",
            f"- **Videos Below 35s:** {result.below_target_count}",
            f"- **Videos Above 45s:** {result.above_target_count}",
            f"- **Cross-Surah Segments:** {result.cross_surah_count}",
            f"- **Special Exceptions Flagged:** {result.exceptions_count}",
            f"- **Manual Overrides Applied:** {result.overrides_count}",
            "",
            "## 2. Quranic Integrity & Validation",
            f"- **Validation Status:** {'✅ PASSED (100% Deterministic Integrity)' if validation_report.is_valid else '❌ FAILED'}",
            f"- **Ayahs Covered:** {validation_report.total_covered_ayahs:,} / {validation_report.total_expected_ayahs:,}",
            f"- **Missing Ayahs:** {validation_report.missing_ayahs_count}",
            f"- **Duplicate Ayahs:** {validation_report.duplicate_ayahs_count}",
            f"- **Order Violations:** {validation_report.order_violations_count}",
            f"- **Invalid References:** {validation_report.invalid_references_count}",
            f"- **Gaps / Partial Ayahs:** {validation_report.gaps_count}",
            "",
            "## 3. Sample Generated Segments (First 15 Videos)",
            "",
            "| Video ID | Surah | Ayahs | Ayah Count | Duration | Status | Primary Rationale |",
            "| :--- | :--- | :--- | :---: | :---: | :--- | :--- |",
        ]

        for v in result.videos[:15]:
            surah_span_str = ", ".join(f"{s['surah_name']} ({s['surah']}:{s['start_ayah']}–{s['end_ayah']})" for s in v.segments)
            ayah_range_str = f"{v.ayah_keys[0]}–{v.ayah_keys[-1]}" if len(v.ayah_keys) > 1 else v.ayah_keys[0]
            lines.append(
                f"| Video {v.video_id:03d} | {surah_span_str} | {ayah_range_str} | {v.ayah_count} | {v.duration_seconds:.1f}s | `{v.status}` | {v.reason[:80]}... |"
            )

        lines.extend([
            "",
            "---",
            "*Report generated automatically by the Quran Segmentation Engine.*",
        ])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return out_path

    def generate_qc_report(
        self,
        result: SegmentationResult,
        filename: str = "quality_control_report.md",
    ) -> Path:
        """Generates Quality Control report flagging unusual segments for human review."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / filename

        unusual_videos = [
            v for v in result.videos
            if v.duration_seconds < 35.0 or v.duration_seconds > 45.0 or v.status != "normal" or len(v.segments) > 1
        ]

        lines: List[str] = [
            "# 🔍 QUALITY-CONTROL & REVIEW REPORT",
            "",
            "This report highlights video segments that fall outside the standard 35–45s window or represent structural exceptions (e.g. indivisible long verses, short standalone surahs, or cross-surah combinations).",
            "",
            f"**Total Segments Flagged for Review:** {len(unusual_videos)} / {result.total_videos}",
            "",
            "| Video ID | Surah / Span | Duration | Status | Rationale / Exception Detail |",
            "| :--- | :--- | :---: | :--- | :--- |",
        ]

        for v in unusual_videos:
            surah_span_str = ", ".join(f"{s['surah_name']} {s['surah']}:{s['start_ayah']}–{s['end_ayah']}" for s in v.segments)
            lines.append(
                f"| Video {v.video_id:04d} | {surah_span_str} | **{v.duration_seconds:.1f}s** | `{v.status}` | {v.explanation} |"
            )

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return out_path
