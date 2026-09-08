"""Command-line interface for the Quran Segmentation Engine."""

import argparse
import sys
from pathlib import Path

from config.settings import EngineConfig
from quran_engine.pipeline import QuranSegmentationEngine
from quran_engine.validation.models import SegmentationValidationError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Quran Daily Dose — High Precision Semantic Segmentation Engine for Video Reels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default_config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--overrides",
        type=str,
        default=None,
        help="Path to manual overrides YAML file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save JSON manifest and reports",
    )
    parser.add_argument(
        "--surah-start",
        type=int,
        default=None,
        help="Starting Surah number (1..114) for partial run",
    )
    parser.add_argument(
        "--surah-end",
        type=int,
        default=None,
        help="Ending Surah number (1..114) for partial run",
    )
    parser.add_argument(
        "--target-duration",
        type=float,
        default=None,
        help="Target video presentation duration in seconds (default: 40.0)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=None,
        help="Preferred minimum duration in seconds (default: 35.0)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=None,
        help="Preferred maximum duration in seconds (default: 45.0)",
    )
    parser.add_argument(
        "--disallow-cross-surah",
        action="store_true",
        help="Disallow segments from crossing Surah boundaries",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load configuration
    config_path = Path(args.config)
    if config_path.exists():
        config = EngineConfig.from_yaml(config_path)
    else:
        config = EngineConfig.default()

    # Apply CLI overrides to configuration
    if args.output_dir:
        config.output.output_dir = args.output_dir
    if args.target_duration:
        config.duration.target_seconds = args.target_duration
    if args.min_duration:
        config.duration.min_preferred_seconds = args.min_duration
    if args.max_duration:
        config.duration.max_preferred_seconds = args.max_duration
    if args.disallow_cross_surah:
        config.rules.allow_cross_surah = False

    print("=" * 70)
    print("📖 QURAN DAILY DOSE — SEGMENTATION ENGINE")
    print("=" * 70)
    print(f"Target Duration: {config.duration.target_seconds}s (Preferred: {config.duration.min_preferred_seconds}–{config.duration.max_preferred_seconds}s)")
    print(f"Allow Cross Surah: {config.rules.allow_cross_surah}")
    print(f"Output Directory: {config.output.output_dir}")
    if args.overrides:
        print(f"Manual Overrides: {args.overrides}")
    print("-" * 70)

    try:
        engine = QuranSegmentationEngine(config=config, overrides_path=args.overrides)

        if args.surah_start or args.surah_end:
            s_start = args.surah_start or 1
            s_end = args.surah_end or 114
            print(f"Running segmentation for Surahs {s_start} to {s_end}...")
            result, report = engine.run_surah_range(s_start, s_end, export_outputs=True)
        else:
            print("Running full Quran segmentation (114 Surahs, 6,236 Ayahs)...")
            result, report = engine.run_full_quran(export_outputs=True)

        print("\n" + "=" * 70)
        print("🎉 SEGMENTATION & VALIDATION COMPLETE")
        print("=" * 70)
        print(f"Total Ayahs Covered: {result.total_ayahs:,} / {report.total_expected_ayahs:,}")
        print(f"Total Videos Generated: {result.total_videos:,}")
        print(f"Average Duration: {result.average_duration:.1f}s (Min: {result.min_duration:.1f}s, Max: {result.max_duration:.1f}s)")
        print(f"Videos in 35–45s Range: {result.within_target_range_count} ({(result.within_target_range_count/result.total_videos)*100:.1f}%)")
        print(f"Videos <35s: {result.below_target_count} | Videos >45s: {result.above_target_count}")
        print(f"Exceptions Handled: {result.exceptions_count} | Cross-Surah Segments: {result.cross_surah_count}")
        print(f"Validation Status: {'✅ 100% PASSED (Zero errors/duplicates/gaps)' if report.is_valid else '❌ FAILED'}")
        print("-" * 70)
        print(f"JSON Manifest: {Path(config.output.output_dir) / config.output.json_manifest_filename}")
        print(f"Summary Report: {Path(config.output.output_dir) / config.output.report_filename}")
        print(f"QC Review Report: {Path(config.output.output_dir) / config.output.qc_report_filename}")
        print("=" * 70)

    except SegmentationValidationError as sve:
        print("\n❌ VALIDATION CRITICAL FAILURE:")
        for err in sve.errors:
            print(f"  - {err}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Execution error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
