from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

import requests
from runwayml import RunwayML, TaskFailedError

from .prompts import REFERENCE_PROMPTS
from .utils import ensure_dir, file_to_data_uri


ProgressFn = Callable[[str], None]


def _task_failure_message(exc: TaskFailedError, label: str) -> str:
    details = getattr(exc, "task_details", None)
    if details is None:
        return f"{label} is door Runway afgebroken zonder foutdetails."

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

    parts = [
        f"{label} mislukt bij Runway.",
        f"Foutcode: {failure_code}.",
        f"Reden: {failure}.",
    ]
    if task_id:
        parts.append(f"Task-ID: {task_id}.")
    try:
        raw = json.dumps(payload, ensure_ascii=False, default=str)
        if raw and raw != "{}":
            parts.append(f"Runway-details: {raw}")
    except Exception:
        pass
    return " ".join(parts)


class FitnessRunwayClient:
    """Runway helper used only for character reference images and optional TTS.

    Full-body fitness motion is handled by Kling Motion Control, not Runway Act-Two.
    """

    def __init__(self, api_key: str):
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("Runway API key ontbreekt")
        self.client = RunwayML(api_key=api_key)

    @staticmethod
    def _download(url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=180) as response:
            response.raise_for_status()
            with output_path.open("wb") as handle:
                shutil.copyfileobj(response.raw, handle)
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
            refs.append(
                {
                    "uri": file_to_data_uri(path),
                    "tag": "subject" if idx == 1 else f"ref{idx}",
                }
            )

        if progress:
            progress(f"Referentie {slot} genereren via Runway…")

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

    def generate_tts(
        self,
        text: str,
        output_path: str | Path,
        voice_reference: str | Path | None = None,
        progress: ProgressFn | None = None,
    ) -> Path:
        text = (text or "").strip()
        if not text:
            raise ValueError("Voice-over tekst ontbreekt")

        if progress:
            progress("Voice-over genereren via Runway…")

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
