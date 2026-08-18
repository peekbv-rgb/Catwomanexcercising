from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import requests
from runwayml import RunwayML

from .prompts import REFERENCE_PROMPTS
from .utils import file_to_data_uri, ensure_dir


ProgressFn = Callable[[str], None]


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
        task = self.client.text_to_image.create(
            model="gpt_image_2",
            prompt_text=REFERENCE_PROMPTS[slot],
            ratio=ratio,
            reference_images=refs,
            quality="medium",
            output_count=1,
            background="opaque",
        ).wait_for_task_output(timeout=12 * 60)

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
        task = self.client.character_performance.create(
            model="act_two",
            character={"type": "image", "uri": file_to_data_uri(character_image)},
            reference={"type": "video", "uri": file_to_data_uri(reference_video)},
            body_control=True,
            expression_intensity=max(1, min(5, int(expression_intensity))),
            ratio="720:1280",
        ).wait_for_task_output(timeout=20 * 60)
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
        task = self.client.text_to_speech.create(**kwargs).wait_for_task_output(timeout=10 * 60)
        if not task.output:
            raise RuntimeError("Runway gaf geen audio-output terug.")
        return self._download(task.output[0], Path(output_path))
