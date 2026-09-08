# 📖 Quran Daily Dose — Quran Segmentation Engine

A production-ready Python segmentation engine that partitions the **entire Quran (114 Surahs, 6,236 Ayahs)** into coherent, short-form video passages for the **“Daily Dose of Quran”** project.

Each generated video segment represents a **naturally coherent Quranic passage** optimized for a presentation duration of **~40 seconds** (preferred **35–45 seconds**), strictly enforcing Quranic integrity and explainability.

---

## ✨ Core Principles & Guarantees

1. **Priority 1 — Quranic Integrity (Hard Constraint)**
   - **100% Coverage:** Every single ayah from 1:1 to 114:6 is covered.
   - **0 Duplicates:** No ayah appears in more than one video.
   - **0 Gaps / Omissions:** Contiguous sequence is strictly preserved.
   - **0 Split Ayahs:** Every segment begins and ends at an authentic ayah boundary.
   - **Order Preserved:** Exact Quranic chronological order is maintained.

2. **Priority 2 — Semantic Coherence**
   - Employs multi-signal linguistic and thematic boundary detection:
     - Traditional **Ruku' (thematic section)** completion marks
     - **Surah transitions** and conclusions
     - **Vocative & Divine Address** shifts (*Yā ayyuha alladhīna āmanū*, *Yā ayyuha an-nās*, *Yā bani Isrā'īl*, *Qul*, etc.)
     - **Narrative & Scene Openings** (*Idh*, *Wa idh*, *Hal atāka*, *Tilka*, *Dhālika*, *Fa-lammā*, etc.)
     - **Closing Clausulae & Attribute Summaries** (*Inna Allāha ghafūrun raḥīm*, *'Alā kulli shay'in qadīr*, etc.)
     - **Tight Continuation Penalties** preventing bad breaks before dependent clauses (*Alladhīna*, *Illā*, *Liyakūna*, etc.)

3. **Priority 3 — Duration Optimization (~40s, 35–45s Preferred)**
   - Uses real recitation audio timing data (Mishary Rashid Alafasy) down to millisecond precision with word-level segment timings.
   - Includes a calibrated fallback Tajweed phonetics model when external audio data is absent.
   - Global dynamic programming (DAG shortest-path optimization) ensures decisions consider future consequence, eliminating awkward residual fragments.

4. **Priority 4 — Practical Consistency & Exceptions**
   - **Single Long Ayahs:** Indivisible verses (e.g., Ayat Al-Kursi 2:255, Ayat Ad-Dayn 2:282) are preserved as complete single-ayah videos with explicit exception notes.
   - **Short Surahs:** Short standalone surahs (e.g., Al-Kawthar) are preserved cleanly or combined harmoniously (e.g., Al-Ikhlas + Al-Falaq) when semantically sound.

5. **Human-in-the-Loop Overrides**
   - Declarative YAML rules allow overriding AI decisions without modifying code:
     - `force_boundary_after`: Mandates a cut after a specific ayah.
     - `keep_together`: Enforces a passage range to remain unified.
     - `forbidden_boundary_after`: Prevents cuts at specific locations.

---

## 🏗️ Architecture & Project Structure

```
.
├── config/
│   ├── __init__.py
│   ├── default_config.yaml      # Configurable target durations, weights, paths
│   └── settings.py              # Strongly-typed configuration dataclasses
├── data/
│   ├── quran_ar_uthmani.json    # Complete Arabic Uthmani text with diacritics
│   ├── quran_en_sahih.json      # English Saheeh International translation
│   ├── quran_meta.json          # Structural metadata (Juz, Hizb, Ruku, Sajdah)
│   └── quran_timing_alafasy.json# Exact millisecond audio and word segment timings
├── quran_engine/
│   ├── __init__.py
│   ├── pipeline.py              # End-to-end segmentation orchestrator
│   ├── quran/
│   │   ├── models.py            # Ayah, Surah, Quran models
│   │   └── loader.py            # Dataset loader and validator
│   ├── timing/
│   │   ├── models.py            # AyahTiming dataclass
│   │   ├── loader.py            # Audio timestamps parser
│   │   └── duration.py          # Duration model & Tajweed fallback estimator
│   ├── semantic/
│   │   ├── models.py            # SemanticBoundary, PassageCoherence
│   │   ├── markers.py           # Arabic & English linguistic regex markers
│   │   ├── boundaries.py        # Multi-signal boundary scorer
│   │   └── analyzer.py          # Passage explanation and theme extractor
│   ├── segmentation/
│   │   ├── models.py            # CandidateSegment, VideoSegment, SegmentationResult
│   │   ├── candidates.py        # Candidate lookahead window generator
│   │   ├── scoring.py           # Multi-objective cost function
│   │   └── optimizer.py         # Global Dynamic Programming optimizer (O(N*K))
│   ├── overrides/
│   │   ├── manager.py           # Manual override enforcement
│   ├── validation/
│   │   ├── models.py            # ValidationReport, SegmentationValidationError
│   │   └── validator.py         # Deterministic integrity validator
│   └── output/
│       ├── json_export.py       # Downstream video pipeline JSON manifest
│       └── report.py            # Markdown summary report & QC review report
├── output/
│   ├── quran_daily_dose_segments.json  # Complete machine-readable manifest
│   ├── segmentation_report.md          # Comprehensive summary report
│   └── quality_control_report.md       # Flagged review list for human QA
├── tests/
│   ├── test_loader.py           # Corpus verification tests
│   ├── test_timing.py           # Timing & fallback model tests
│   ├── test_semantic.py         # Linguistic boundary scorer tests
│   ├── test_optimizer.py        # DP optimizer tests
│   ├── test_overrides.py        # Manual overrides tests
│   ├── test_validator.py        # Deterministic validator tests
│   └── test_full_quran.py       # 100% full-Quran integration test
├── overrides_example.yaml       # Example override file
├── main.py                      # CLI entrypoint
└── README.md
```

---

## 🚀 Quickstart & Usage

### 1. Run Full Quran Segmentation (Default)
Segments all 114 Surahs and 6,236 Ayahs:
```bash
python3 main.py
```

### 2. Segment a Specific Surah or Range
```bash
# Segment only Surah Al-Baqarah (Surah 2)
python3 main.py --surah-start 2 --surah-end 2

# Segment Surah Yusuf (Surah 12)
python3 main.py --surah-start 12 --surah-end 12

# Segment the last 10 Surahs (105 to 114)
python3 main.py --surah-start 105 --surah-end 114
```

### 3. Apply Manual Overrides
```bash
python3 main.py --overrides overrides_example.yaml
```

### 4. Customize Duration & Rules via CLI
```bash
python3 main.py --target-duration 45 --min-duration 40 --max-duration 50 --disallow-cross-surah
```

---

## 📋 Downstream Video Rendering Schema

The generated JSON manifest (`output/quran_daily_dose_segments.json`) contains everything needed by the video rendering pipeline (FFmpeg, Remotion, or custom compositor):

```json
{
  "video_id": 47,
  "segments": [
    {
      "surah": 12,
      "surah_name": "Yusuf",
      "start_ayah": 23,
      "end_ayah": 29
    }
  ],
  "ayah_count": 7,
  "duration_seconds": 41.8,
  "is_estimated": false,
  "semantic_score": 0.94,
  "boundary_score": 0.91,
  "status": "normal",
  "reason": "Optimal duration (41.8s) with natural boundary score 0.91.",
  "explanation": "Begins at 12:23 following the preceding passage. Encompasses 7 verses (12:23 to 12:29) forming a cohesive thematic unit. Ending rationale: Traditional Ruku' section completion (Ruku 4). Duration of 41.8s is within the optimal 35–45s window.",
  "ayah_keys": ["12:23", "12:24", "12:25", "12:26", "12:27", "12:28", "12:29"],
  "arabic_text": "...",
  "english_text": "...",
  "subtitles_timing": [
    {
      "verse_key": "12:23",
      "surah": 12,
      "ayah": 23,
      "start_seconds": 0.0,
      "end_seconds": 7.42,
      "duration_seconds": 7.42,
      "is_estimated": false,
      "segments": [
        [1, 0, 850],
        [2, 850, 1920],
        ...
      ]
    }
  ]
}
```

---

## 🧪 Running Automated Tests

Run the test suite with pytest:
```bash
pytest -v
```
