from __future__ import annotations

from dataclasses import asdict, dataclass
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
        return ["Voeg minimaal één oefening toe."]

    for i, exercise in enumerate(exercises, start=1):
        normalized = exercise.normalized()
        if not normalized.name:
            errors.append(f"Oefening {i}: naam ontbreekt.")
        if normalized.reference_slot not in {"A", "B", "C", "D", "E"}:
            errors.append(f"Oefening {i}: ongeldige referentie {normalized.reference_slot}.")
        if not normalized.motion_path or not Path(normalized.motion_path).exists():
            errors.append(
                f"Oefening {i} ({normalized.name or 'zonder naam'}): bewegingsreferentie ontbreekt."
            )
    return errors
