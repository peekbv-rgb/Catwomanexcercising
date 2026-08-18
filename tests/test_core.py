from core.prompts import auto_reference_slot, cue_for_exercise
from core.utils import slugify


def test_slugify():
    assert slugify("Romanian Deadlift  1") == "romanian-deadlift-1"


def test_auto_reference_slot():
    assert auto_reference_slot("Squats") == "A"
    assert auto_reference_slot("Reverse lunges") == "B"
    assert auto_reference_slot("Romanian deadlift") == "C"
    assert auto_reference_slot("Glute bridge") == "D"


def test_cue():
    assert "knieën" in cue_for_exercise("Squats")
