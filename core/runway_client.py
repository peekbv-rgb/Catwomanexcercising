from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

import requests
from runwayml import RunwayML, TaskFailedError

from .prompts import REFERENCE_PROMPTS
from .utils import file_to_data_uri, ensure_dir


ProgressFn = Callable[[str], None]

# Runway currently limits data-URI inputs by encoded string length, not just raw file size.
# Keep a little headroom below the documented limits.
MAX_CHARACTER_IMAGE_DATA_URI_CHARS = 5_150_000
MAX_REFERENCE_VIDEO_DATA_URI_CHARS = 16_500_000


def _task_failure_message(exc: TaskFailedError, label: str) -> str:
    """Turn Runway's TaskFailedError into a useful end-user diagnostic."""
    details = getattr(exc, "task_details", None)
    if details is None:
        return f"{label} is door Runway afgebroken, maar er is geen foutdetail teruggegeven."

    try:
        if hasattr(details, "model_dump"):
            payload = details.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(details, dict):
            payload = details
        else:
            payload = vars(details)
    except Exception:
        payload = {"details": str(details)}

    task_id = payload.get("id") or payload.get("taskId") or payload.get("task_id")
    failure_code = payload.get("failureCode") or payload.get("failure_code") or "onbekend"
    failure = payload.get("failure") or payload.get("error") or payload.get("message") or "Geen nadere omschrijving."

    parts = [f"{label} mislukt bij Runway.", f"Foutcode: {failure_code}.", f"Reden: {failure}."]
    if task_id:
        parts.append(f"Task-ID: {task_id}.")
    # Include the compact raw details as fallback because Runway adds new failure fields over time.
    try:
        raw = json.dumps(payload, ensure_ascii=False, default=str)
        if raw and raw != "{}":
            parts.append(f"Runway-details: {raw}")
    except Exception:
        pass
    return " ".join(parts)


class FitnessRunwayClient:
    """Small wrapper around the official Runway Python SDK.

    Uses data URIs for local inputs. The app compresses motion-reference videos before
    sending them so they stay below Runway's data-URI input limit.
    """

    def __init__(self, api_key: str):
        if not api_key.strip():
            raise ValueError("Runway API key ontbreekt")
        self.client = RunwayML(api_key=api_key.strip())

    @staticmethod
    def _download(url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=180) as response:
            response.raise_for_status()
            with output_path.open("wb") as f:
                shutil.copyfileobj(response.raw, f)
        return output_path

    def generate_reference(
        self,
        slot: str,
        subject_paths: list[str | Path],
        output_dir: str | Path,
        progress: ProgressFn | None = None,
    ) -> Path:
        slot = slot.upper()
        if slot not in REFERENCE_PROMPTS:
            raise ValueError(f"Onbekende referentie-slot: {slot}")
        output_dir = ensure_dir(output_dir)
        refs = []
        for idx, path in enumerate(subject_paths[:16], start=1):
            refs.append({"uri": file_to_data_uri(path), "tag": "subject" if idx == 1 else f"ref{idx}"})

        if progress:
            progress(f"Referentie {slot} genereren…")

        ratio = "1536:1920" if slot == "E" else "1088:1920"
        try:
            task = self.client.text_to_image.create(
                model="gpt_image_2",
                prompt_text=REFERENCE_PROMPTS[slot],
                ratio=ratio,
                reference_images=refs,
                quality="medium",
                output_count=1,
                background="opaque",
            ).wait_for_task_output(timeout=12 * 60)
        except TaskFailedError as exc:
            raise RuntimeError(_task_failure_message(exc, f"Referentie {slot}")) from exc

        if not task.output:
            raise RuntimeError(f"Runway gaf geen afbeelding terug voor referentie {slot}.")
        return self._download(task.output[0], output_dir / f"reference_{slot}.png")

    def generate_character_performance(
        self,
        character_image: str | Path,
        reference_video: str | Path,
        output_path: str | Path,
        expression_intensity: int = 2,
        progress: ProgressFn | None = None,
    ) -> Path:
        if progress:
            progress(f"Act-Two motion transfer: {Path(reference_video).name}…")

        character_uri = file_to_data_uri(character_image)
        reference_uri = file_to_data_uri(reference_video)

        if len(character_uri) > MAX_CHARACTER_IMAGE_DATA_URI_CHARS:
            raise ValueError(
                "Character-afbeelding is te groot voor Runway Act-Two als data-URI. "
                "Gebruik een kleinere PNG/JPG (liefst onder circa 3,7 MB)."
            )
        if len(reference_uri) > MAX_REFERENCE_VIDEO_DATA_URI_CHARS:
            raise ValueError(
                "Motion-reference is na base64-encoding te groot voor Runway Act-Two. "
                "Kort de clip in of comprimeer hem verder."
            )

        try:
            task = self.client.character_performance.create(
                model="act_two",
                character={"type": "image", "uri": character_uri},
                reference={"type": "video", "uri": reference_uri},
                body_control=True,
                expression_intensity=max(1, min(5, int(expression_intensity))),
                ratio="720:1280",
            ).wait_for_task_output(timeout=20 * 60)
        except TaskFailedError as exc:
            raise RuntimeError(_task_failure_message(exc, "Act-Two motion transfer")) from exc

        if not task.output:
            raise RuntimeError("Runway Act-Two gaf geen video-output terug.")
        return self._download(task.output[0], Path(output_path))

    def generate_tts(
        self,
        text: str,
        output_path: str | Path,
        voice_reference: str | Path | None = None,
        progress: ProgressFn | None = None,
    ) -> Path:
        if progress:
            progress("Voice-over genereren…")
        kwargs = {
            "model": "seed_audio",
            "prompt_text": text,
            "output_format": "mp3",
            "speech_rate": 0,
            "pitch_rate": 0,
            "loudness_rate": 0,
        }
        if voice_reference:
            kwargs["voice"] = {
                "type": "reference-audio",
                "audio_uri": file_to_data_uri(voice_reference),
            }
        try:
            task = self.client.text_to_speech.create(**kwargs).wait_for_task_output(timeout=10 * 60)
        except TaskFailedError as exc:
            raise RuntimeError(_task_failure_message(exc, "Voice-over")) from exc

        if not task.output:
            raise RuntimeError("Runway gaf geen audio-output terug.")
        return self._download(task.output[0], Path(output_path))
