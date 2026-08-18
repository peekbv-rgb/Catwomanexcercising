from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .prompts import auto_reference_slot, cue_for_exercise
from .utils import slugify


@dataclass
class Exercise:
    name: str
    motion_path: str
    reference_slot: str = ""
    voiceover: str = ""

    def normalized(self) -> "Exercise":
        return Exercise(
            name=self.name.strip(),
            motion_path=self.motion_path,
            reference_slot=(self.reference_slot or auto_reference_slot(self.name)).upper(),
            voiceover=self.voiceover.strip() or cue_for_exercise(self.name),
        )

    @property
    def slug(self) -> str:
        return slugify(self.name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())


def validate_exercises(exercises: list[Exercise]) -> list[str]:
    errors: list[str] = []
    if not exercises:
        errors.append("Voeg minimaal één oefening toe.")
        return errors
    for i, ex in enumerate(exercises, start=1):
        n = ex.normalized()
        if not n.name:
            errors.append(f"Oefening {i}: naam ontbreekt.")
        if n.reference_slot not in {"A", "B", "C", "D", "E"}:
            errors.append(f"Oefening {i}: ongeldige referentie {n.reference_slot}.")
        if not n.motion_path or not Path(n.motion_path).exists():
            errors.append(f"Oefening {i} ({n.name or 'zonder naam'}): motion-reference ontbreekt.")
    return errors
