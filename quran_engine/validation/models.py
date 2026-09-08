"""Validation models and error types."""

from dataclasses import dataclass, field
from typing import List, Optional


class SegmentationValidationError(Exception):
    """Raised when segmentation fails any Quranic integrity or mathematical constraint."""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class ValidationReport:
    """Detailed deterministic validation report."""
    is_valid: bool
    total_expected_ayahs: int
    total_covered_ayahs: int
    missing_ayahs_count: int
    duplicate_ayahs_count: int
    invalid_references_count: int
    order_violations_count: int
    gaps_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
