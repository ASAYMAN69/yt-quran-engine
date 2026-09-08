"""Manual override manager for human-in-the-loop boundary corrections."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import yaml

from quran_engine.quran.models import Ayah, Quran


@dataclass
class KeepTogetherRule:
    surah: int
    start_ayah: int
    end_ayah: int
    reason: str = "Manual rule: keep passage together"


@dataclass
class ForceBoundaryRule:
    surah: int
    ayah: int
    reason: str = "Manual rule: force boundary after this ayah"


@dataclass
class ForbiddenBoundaryRule:
    surah: int
    ayah: int
    reason: str = "Manual rule: forbid boundary after this ayah"


class OverrideManager:
    """Loads, validates, and evaluates manual override rules for segmentation."""

    def __init__(
        self,
        force_boundaries: Optional[List[ForceBoundaryRule]] = None,
        keep_togethers: Optional[List[KeepTogetherRule]] = None,
        forbidden_boundaries: Optional[List[ForbiddenBoundaryRule]] = None,
    ):
        self.force_boundaries: List[ForceBoundaryRule] = force_boundaries or []
        self.keep_togethers: List[KeepTogetherRule] = keep_togethers or []
        self.forbidden_boundaries: List[ForbiddenBoundaryRule] = forbidden_boundaries or []

        self._forced_keys: Set[str] = {f"{r.surah}:{r.ayah}" for r in self.force_boundaries}
        self._forbidden_keys: Set[str] = {f"{r.surah}:{r.ayah}" for r in self.forbidden_boundaries}

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "OverrideManager":
        """Loads override rules from a YAML/JSON configuration file."""
        path = Path(yaml_path)
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        forces: List[ForceBoundaryRule] = []
        for item in data.get("force_boundary_after", []):
            forces.append(ForceBoundaryRule(
                surah=int(item["surah"]),
                ayah=int(item["ayah"]),
                reason=item.get("reason", "Manual rule: force boundary"),
            ))

        keeps: List[KeepTogetherRule] = []
        for item in data.get("keep_together", []):
            keeps.append(KeepTogetherRule(
                surah=int(item["surah"]),
                start_ayah=int(item["start_ayah"]),
                end_ayah=int(item["end_ayah"]),
                reason=item.get("reason", "Manual rule: keep passage together"),
            ))

        forbids: List[ForbiddenBoundaryRule] = []
        for item in data.get("forbidden_boundary_after", []):
            forbids.append(ForbiddenBoundaryRule(
                surah=int(item["surah"]),
                ayah=int(item["ayah"]),
                reason=item.get("reason", "Manual rule: forbid boundary"),
            ))

        return cls(
            force_boundaries=forces,
            keep_togethers=keeps,
            forbidden_boundaries=forbids,
        )

    def is_boundary_forced(self, ayah: Ayah) -> bool:
        """Returns True if a cut is strictly mandated after this ayah."""
        return ayah.key in self._forced_keys

    def is_boundary_forbidden(self, ayah: Ayah) -> bool:
        """Returns True if a cut is strictly forbidden after this ayah."""
        if ayah.key in self._forbidden_keys:
            return True
        # Check if this ayah falls strictly inside a keep_together range
        for kt in self.keep_togethers:
            if kt.surah == ayah.surah_number:
                if kt.start_ayah <= ayah.ayah_number < kt.end_ayah:
                    return True
        return False

    def violates_keep_together(self, start_ayah: Ayah, end_ayah: Ayah) -> bool:
        """Returns True if a candidate segment starting at start_ayah and ending at end_ayah breaks a keep_together rule."""
        for kt in self.keep_togethers:
            if kt.surah == start_ayah.surah_number or kt.surah == end_ayah.surah_number:
                # If the candidate starts inside the keep_together (after start_ayah) or ends inside it (before end_ayah)
                # Case 1: Candidate starts after kt.start_ayah but <= kt.end_ayah
                if start_ayah.surah_number == kt.surah and kt.start_ayah < start_ayah.ayah_number <= kt.end_ayah:
                    return True
                # Case 2: Candidate ends after kt.start_ayah but < kt.end_ayah
                if end_ayah.surah_number == kt.surah and kt.start_ayah <= end_ayah.ayah_number < kt.end_ayah:
                    return True
        return False
