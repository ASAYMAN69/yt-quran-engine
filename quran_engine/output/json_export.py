"""JSON manifest exporter for downstream video rendering pipelines."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from quran_engine.segmentation.models import SegmentationResult
from quran_engine.validation.models import ValidationReport


class JsonManifestExporter:
    """Exports structured JSON manifest ready for FFmpeg / video rendering engine."""

    def __init__(self, output_dir: Union[str, Path] = "output"):
        self.output_dir = Path(output_dir)

    def export(
        self,
        result: SegmentationResult,
        validation_report: ValidationReport,
        filename: str = "quran_daily_dose_segments.json",
        metadata: Dict[str, Any] = None,
    ) -> Path:
        """Serializes and saves the segmentation result to JSON."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / filename

        payload = {
            "metadata": {
                "project": "Quran Daily Dose — Quran Segmentation Engine",
                "version": "1.0.0",
                "total_videos": result.total_videos,
                "total_ayahs": result.total_ayahs,
                "average_duration_seconds": result.average_duration,
                "min_duration_seconds": result.min_duration,
                "max_duration_seconds": result.max_duration,
                "within_preferred_range_35_45s": result.within_target_range_count,
                "below_35s_count": result.below_target_count,
                "above_45s_count": result.above_target_count,
                "exceptions_count": result.exceptions_count,
                "cross_surah_count": result.cross_surah_count,
                "overrides_count": result.overrides_count,
                "validation": {
                    "is_valid": validation_report.is_valid,
                    "missing_ayahs": validation_report.missing_ayahs_count,
                    "duplicate_ayahs": validation_report.duplicate_ayahs_count,
                    "order_violations": validation_report.order_violations_count,
                },
                **(metadata or {}),
            },
            "videos": [v.to_dict() for v in result.videos],
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return out_path
