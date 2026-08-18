from pathlib import Path

from core.prompts import auto_reference_slot, cue_for_exercise
from core.utils import slugify
from core.workout import Exercise, validate_exercises


def test_slugify():
    assert slugify("Romanian Deadlift") == "romanian-deadlift"


def test_auto_reference_slots():
    assert auto_reference_slot("Squats") == "A"
    assert auto_reference_slot("Reverse lunges") == "B"
    assert auto_reference_slot("Romanian deadlift") == "C"
    assert auto_reference_slot("Glute bridge") == "D"


def test_cue_generation():
    assert "Squats" in cue_for_exercise("Squats")


def test_missing_motion_is_reported(tmp_path: Path):
    exercise = Exercise(name="Squats", motion_path=str(tmp_path / "missing.mp4"), reference_slot="A")
    errors = validate_exercises([exercise])
    assert errors
    assert "bewegingsreferentie ontbreekt" in errors[0]


def test_existing_motion_is_valid(tmp_path: Path):
    motion = tmp_path / "motion.mp4"
    motion.write_bytes(b"test")
    exercise = Exercise(name="Squats", motion_path=str(motion), reference_slot="A")
    assert validate_exercises([exercise]) == []
