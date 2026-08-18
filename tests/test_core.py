from pathlib import Path

import requests

from core.prompts import auto_reference_slot, cue_for_exercise
from core.public_tunnel import TemporaryPublicVideo
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


def test_local_motion_server_supports_byte_ranges(tmp_path: Path):
    motion = tmp_path / "motion.mp4"
    payload = bytes(range(256)) * 16
    motion.write_bytes(payload)

    tunnel = TemporaryPublicVideo(motion)
    try:
        port = tunnel._start_local_server()
        response = requests.get(
            f"http://127.0.0.1:{port}/motion.mp4",
            headers={"Range": "bytes=10-19"},
            timeout=5,
        )
        assert response.status_code == 206
        assert response.headers["Content-Type"] == "video/mp4"
        assert response.headers["Accept-Ranges"] == "bytes"
        assert response.content == payload[10:20]
    finally:
        tunnel.close()
