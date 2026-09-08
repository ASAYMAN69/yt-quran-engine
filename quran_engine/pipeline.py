"""High-level segmentation pipeline orchestrating loading, scoring, optimization, validation, and export."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from config.settings import EngineConfig
from quran_engine.quran.loader import QuranLoader
from quran_engine.quran.models import Quran
from quran_engine.timing.loader import TimingLoader
from quran_engine.timing.duration import DurationModel
from quran_engine.semantic.boundaries import SemanticBoundaryScorer
from quran_engine.semantic.analyzer import SemanticAnalyzer
from quran_engine.overrides.manager import OverrideManager
from quran_engine.segmentation.scoring import SegmentScorer
from quran_engine.segmentation.candidates import CandidateGenerator
from quran_engine.segmentation.optimizer import QuranOptimizer
from quran_engine.segmentation.models import SegmentationResult
from quran_engine.validation.validator import SegmentationValidator
from quran_engine.validation.models import ValidationReport
from quran_engine.output.json_export import JsonManifestExporter
from quran_engine.output.report import ReportGenerator


class QuranSegmentationEngine:
    """Complete end-to-end engine for segmenting the Quran into video-ready passages."""

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        overrides_path: Optional[Union[str, Path]] = None,
    ):
        self.config = config or EngineConfig.default()
        
        # 1. Load Quran corpus (Arabic Uthmani + English Saheeh)
        self.quran_loader = QuranLoader(
            arabic_path=self.config.dataset.arabic_path,
            english_path=self.config.dataset.english_path,
            meta_path=self.config.dataset.meta_path,
        )
        self.quran: Quran = self.quran_loader.load()

        # 2. Load presentation timings
        self.timing_loader = TimingLoader(timing_path=self.config.dataset.timing_path)
        exact_timings = self.timing_loader.load()
        self.duration_model = DurationModel(
            exact_timings=exact_timings,
            fallback_wpm=self.config.dataset.fallback_wpm,
            fallback_cps=self.config.dataset.fallback_cps,
        )

        # 3. Setup semantic boundary & analyzer
        self.boundary_scorer = SemanticBoundaryScorer(
            surah_bonus=self.config.weights.surah_boundary_bonus,
            ruku_bonus=self.config.weights.ruku_boundary_bonus,
        )
        self.semantic_analyzer = SemanticAnalyzer(boundary_scorer=self.boundary_scorer)

        # 4. Setup overrides
        self.override_manager = (
            OverrideManager.from_yaml(overrides_path)
            if overrides_path
            else OverrideManager()
        )

        # 5. Setup candidate scoring & generator
        self.segment_scorer = SegmentScorer(
            config=self.config,
            boundary_scorer=self.boundary_scorer,
            override_manager=self.override_manager,
        )
        self.candidate_generator = CandidateGenerator(
            quran=self.quran,
            duration_model=self.duration_model,
            scorer=self.segment_scorer,
            config=self.config,
        )

        # 6. Optimizer & Validator
        self.optimizer = QuranOptimizer(
            quran=self.quran,
            duration_model=self.duration_model,
            candidate_generator=self.candidate_generator,
            semantic_analyzer=self.semantic_analyzer,
            config=self.config,
        )
        self.validator = SegmentationValidator(quran=self.quran)

        # 7. Exporters
        self.json_exporter = JsonManifestExporter(output_dir=self.config.output.output_dir)
        self.report_generator = ReportGenerator(output_dir=self.config.output.output_dir)

    def run_full_quran(
        self,
        export_outputs: bool = True,
    ) -> Tuple[SegmentationResult, ValidationReport]:
        """Runs segmentation across the entire Quran (all 114 Surahs, 6,236 Ayahs)."""
        result = self.optimizer.optimize(
            start_global_idx=0,
            end_global_idx=len(self.quran.ayahs) - 1,
        )

        # Strict validation
        validation_report = self.validator.validate(
            result=result,
            expected_start_global_idx=0,
            expected_end_global_idx=len(self.quran.ayahs) - 1,
            raise_on_error=True,
        )

        if export_outputs:
            self.export_all(result, validation_report)

        return result, validation_report

    def run_surah_range(
        self,
        start_surah: int,
        end_surah: int,
        export_outputs: bool = True,
    ) -> Tuple[SegmentationResult, ValidationReport]:
        """Runs segmentation on a specific range of Surahs (e.g. 1 to 2, or 108 to 114)."""
        if not (1 <= start_surah <= end_surah <= 114):
            raise ValueError(f"Invalid surah range: {start_surah}..{end_surah}")

        start_ayah = self.quran.get_surah(start_surah).ayahs[0]
        end_ayah = self.quran.get_surah(end_surah).ayahs[-1]

        result = self.optimizer.optimize(
            start_global_idx=start_ayah.global_index,
            end_global_idx=end_ayah.global_index,
        )

        validation_report = self.validator.validate(
            result=result,
            expected_start_global_idx=start_ayah.global_index,
            expected_end_global_idx=end_ayah.global_index,
            raise_on_error=True,
        )

        if export_outputs:
            self.export_all(result, validation_report)

        return result, validation_report

    def export_all(
        self,
        result: SegmentationResult,
        validation_report: ValidationReport,
    ) -> Dict[str, Path]:
        """Exports JSON manifest, Markdown Summary Report, and Quality-Control Report."""
        json_path = self.json_exporter.export(
            result=result,
            validation_report=validation_report,
            filename=self.config.output.json_manifest_filename,
        )
        report_path = self.report_generator.generate_summary_report(
            result=result,
            validation_report=validation_report,
            filename=self.config.output.report_filename,
        )
        qc_path = self.report_generator.generate_qc_report(
            result=result,
            filename=self.config.output.qc_report_filename,
        )
        return {
            "json_manifest": json_path,
            "summary_report": report_path,
            "qc_report": qc_path,
        }
