from __future__ import annotations

import base64
import shutil
import time
from pathlib import Path
from typing import Callable

import requests

from .utils import file_to_data_uri


ProgressFn = Callable[[str], None]


class FitnessKlingClient:
    """Minimal client for KlingAI Open Platform Motion Control.

    The Open Platform uses asynchronous tasks. We create a Motion Control task,
    poll it until completion, then download the generated video.
    """

    BASE_URL = "https://api.klingai.com"
    CREATE_PATH = "/v1/videos/motion-control"

    def __init__(self, api_key: str, poll_interval: float = 4.0):
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("Kling API key ontbreekt")
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    @staticmethod
    def _image_base64(path: str | Path) -> str:
        """Kling accepts the character image as URL/base64; send raw base64 locally."""
        return base64.b64encode(Path(path).read_bytes()).decode("ascii")

    @staticmethod
    def _download(url: str, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=180) as response:
            response.raise_for_status()
            with output_path.open("wb") as f:
                shutil.copyfileobj(response.raw, f)
        return output_path

    @staticmethod
    def _payload_error(data: dict, prefix: str) -> RuntimeError:
        code = data.get("code", "onbekend")
        message = data.get("message") or data.get("msg") or "Geen nadere omschrijving."
        request_id = data.get("request_id") or data.get("requestId")
        detail = f"{prefix}. Kling-code: {code}. Reden: {message}."
        if request_id:
            detail += f" Request-ID: {request_id}."
        return RuntimeError(detail)

    def _request_json(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.session.request(
                method,
                self.BASE_URL + path,
                timeout=90,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Geen verbinding met Kling API: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Kling gaf geen geldige JSON terug (HTTP {response.status_code})."
            ) from exc

        if response.status_code >= 400:
            raise self._payload_error(data, f"Kling API HTTP {response.status_code}")
        if data.get("code", 0) not in (0, "0", None):
            raise self._payload_error(data, "Kling API heeft de aanvraag geweigerd")
        return data

    def generate_motion_control(
        self,
        character_image: str | Path,
        reference_video: str | Path,
        output_path: str | Path,
        prompt: str = "",
        mode: str = "std",
        character_orientation: str = "video",
        keep_original_sound: bool = False,
        progress: ProgressFn | None = None,
        timeout: float = 20 * 60,
    ) -> Path:
        mode = mode if mode in {"std", "pro"} else "std"
        character_orientation = (
            character_orientation if character_orientation in {"video", "image"} else "video"
        )

        if progress:
            progress(f"Kling 3.0 Motion Control starten: {Path(reference_video).name}…")

        # Character images are sent as base64. For the motion reference we first try
        # a compact data URI so the local app does not have to publish private files.
        # If Kling changes/limits this transport, the returned API message is surfaced
        # verbatim so we can switch to an upload-URL transport without hiding the cause.
        payload = {
            "model_name": "kling-v3",
            "image_url": self._image_base64(character_image),
            "video_url": file_to_data_uri(reference_video),
            "prompt": (prompt or "")[:2500],
            "keep_original_sound": "yes" if keep_original_sound else "no",
            "character_orientation": character_orientation,
            "mode": mode,
        }

        created = self._request_json("POST", self.CREATE_PATH, json=payload)
        task = created.get("data") or {}
        task_id = task.get("task_id")
        if not task_id:
            raise RuntimeError(f"Kling gaf geen task_id terug. Antwoord: {created}")

        started = time.monotonic()
        while True:
            if time.monotonic() - started > timeout:
                raise TimeoutError(f"Kling Motion Control time-out na {timeout / 60:.0f} minuten. Task-ID: {task_id}")

            time.sleep(self.poll_interval)
            status_payload = self._request_json("GET", f"{self.CREATE_PATH}/{task_id}")
            info = status_payload.get("data") or {}
            status = str(info.get("task_status") or "").lower()

            if progress:
                label = {
                    "submitted": "in wachtrij",
                    "processing": "wordt gegenereerd",
                    "succeed": "klaar",
                    "failed": "mislukt",
                }.get(status, status or "status onbekend")
                progress(f"Kling 3.0 Motion Control: {label} · task {task_id[:8]}…")

            if status in {"submitted", "processing", "pending", "running", ""}:
                continue
            if status in {"failed", "fail", "error"}:
                reason = info.get("task_status_msg") or info.get("message") or "Geen foutdetails ontvangen."
                raise RuntimeError(
                    f"Kling Motion Control mislukt. Reden: {reason}. Task-ID: {task_id}."
                )
            if status in {"succeed", "success", "completed"}:
                result = info.get("task_result") or {}
                videos = result.get("videos") or []
                if not videos or not videos[0].get("url"):
                    raise RuntimeError(
                        f"Kling-task is klaar maar bevat geen video-URL. Task-ID: {task_id}."
                    )
                return self._download(videos[0]["url"], output_path)

            raise RuntimeError(
                f"Onbekende Kling-taskstatus '{status}'. Task-ID: {task_id}. Antwoord: {status_payload}"
            )
