"""Configuration loader and settings dataclasses."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


@dataclass
class DurationConfig:
    target_seconds: float = 40.0
    min_preferred_seconds: float = 35.0
    max_preferred_seconds: float = 45.0
    min_acceptable_seconds: float = 25.0
    max_acceptable_seconds: 55.0 = 55.0
    hard_min_seconds: float = 10.0
    hard_max_seconds: float = 80.0


@dataclass
class WeightsConfig:
    duration_weight: float = 1.0
    semantic_weight: float = 1.6
    surah_boundary_bonus: float = 0.8
    ruku_boundary_bonus: float = 0.5
    cross_surah_penalty: float = 1.2
    tight_connection_penalty: float = 2.0


@dataclass
class RulesConfig:
    allow_cross_surah: bool = True
    combine_short_surahs: bool = True
    max_short_surah_stand_alone_duration: float = 25.0
    allow_single_ayah_exception: bool = True
    max_ayahs_per_segment: int = 20


@dataclass
class DatasetConfig:
    arabic_path: str = "data/quran_ar_uthmani.json"
    english_path: str = "data/quran_en_sahih.json"
    meta_path: str = "data/quran_meta.json"
    timing_path: str = "data/quran_timing_alafasy.json"
    fallback_wpm: float = 65.0
    fallback_cps: float = 8.5


@dataclass
class OutputConfig:
    output_dir: str = "output"
    json_manifest_filename: str = "quran_daily_dose_segments.json"
    report_filename: str = "segmentation_report.md"
    qc_report_filename: str = "quality_control_report.md"


@dataclass
class EngineConfig:
    duration: DurationConfig = field(default_factory=DurationConfig)
    weights: WeightsConfig = field(default_factory=WeightsConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "EngineConfig":
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        duration_cfg = DurationConfig(**raw.get("duration", {}))
        weights_cfg = WeightsConfig(**raw.get("weights", {}))
        rules_cfg = RulesConfig(**raw.get("rules", {}))
        dataset_cfg = DatasetConfig(**raw.get("dataset", {}))
        output_cfg = OutputConfig(**raw.get("output", {}))

        return cls(
            duration=duration_cfg,
            weights=weights_cfg,
            rules=rules_cfg,
            dataset=dataset_cfg,
            output=output_cfg,
        )

    @classmethod
    def default(cls) -> "EngineConfig":
        default_yaml = Path(__file__).parent / "default_config.yaml"
        if default_yaml.exists():
            return cls.from_yaml(default_yaml)
        return cls()
