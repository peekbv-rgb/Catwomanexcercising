from __future__ import annotations

import http.server
import os
import platform
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

import requests


ProgressFn = Callable[[str], None]
_TRYCLOUDFLARE_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)


class _VideoServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, video_path: Path):
        super().__init__(server_address, handler_class)
        self.video_path = Path(video_path)


class _SingleVideoHandler(http.server.BaseHTTPRequestHandler):
    """Serve exactly one MP4, including byte-range requests used by media downloaders."""

    server: _VideoServer

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(send_body=False)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(send_body=True)

    def _serve(self, send_body: bool) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            if send_body:
                self.wfile.write(b"ok")
            return

        if path != "/motion.mp4":
            self.send_error(404)
            return

        video = self.server.video_path
        if not video.exists():
            self.send_error(404)
            return

        total = video.stat().st_size
        start = 0
        end = max(0, total - 1)
        status = 200

        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            match = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if match:
                left, right = match.groups()
                if left:
                    start = int(left)
                if right:
                    end = int(right)
                end = min(end, total - 1)
                if start > end or start >= total:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{total}")
                    self.end_headers()
                    return
                status = 206

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.end_headers()

        if not send_body:
            return

        with video.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(1024 * 256, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


class TemporaryPublicVideo:
    """Expose one local motion MP4 through a short-lived Cloudflare Quick Tunnel.

    Kling Motion Control requires video_url to be a retrievable HTTPS URL. This context manager
    keeps the file on the user's computer and opens a temporary TryCloudflare URL only while
    Kling needs it. The tunnel and local HTTP server are stopped automatically afterwards.
    """

    def __init__(
        self,
        video_path: str | Path,
        progress: ProgressFn | None = None,
        startup_timeout: float = 60.0,
    ):
        self.video_path = Path(video_path)
        self.progress = progress
        self.startup_timeout = startup_timeout
        self.httpd: _VideoServer | None = None
        self.http_thread: threading.Thread | None = None
        self.process: subprocess.Popen | None = None
        self.temp_home: tempfile.TemporaryDirectory | None = None
        self.public_url: str | None = None

    @staticmethod
    def _download_url_for_platform() -> tuple[str, str]:
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "windows" and machine in {"amd64", "x86_64"}:
            return (
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
                "cloudflared.exe",
            )
        if system == "linux" and machine in {"amd64", "x86_64"}:
            return (
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                "cloudflared",
            )

        raise RuntimeError(
            "Cloudflare Quick Tunnel auto-install wordt op dit systeem nog niet ondersteund. "
            "Installeer cloudflared handmatig en zet CLOUDFLARED_PATH in .env."
        )

    def _find_or_install_cloudflared(self) -> Path:
        configured = os.getenv("CLOUDFLARED_PATH", "").strip()
        if configured:
            path = Path(configured).expanduser()
            if path.exists():
                return path
            raise FileNotFoundError(f"CLOUDFLARED_PATH bestaat niet: {path}")

        found = shutil.which("cloudflared")
        if found:
            return Path(found)

        url, filename = self._download_url_for_platform()
        tools_dir = Path(__file__).resolve().parents[1] / ".tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        destination = tools_dir / filename
        if destination.exists() and destination.stat().st_size > 1_000_000:
            return destination

        if self.progress:
            self.progress("Eerste keer: Cloudflare-tunnelhulp downloaden…")

        partial = destination.with_suffix(destination.suffix + ".part")
        try:
            with requests.get(url, stream=True, timeout=180, allow_redirects=True) as response:
                response.raise_for_status()
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            partial.replace(destination)
            if platform.system().lower() != "windows":
                destination.chmod(0o755)
        except Exception:
            try:
                partial.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        return destination

    def _start_local_server(self) -> int:
        self.httpd = _VideoServer(("127.0.0.1", 0), _SingleVideoHandler, self.video_path)
        port = int(self.httpd.server_address[1])
        self.http_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.http_thread.start()
        return port

    def _start_cloudflared(self, port: int) -> str:
        executable = self._find_or_install_cloudflared()
        self.temp_home = tempfile.TemporaryDirectory(prefix="fitness-video-tunnel-")
        env = os.environ.copy()
        # Keep user-specific cloudflared config/certificates out of this one-off Quick Tunnel.
        env["HOME"] = self.temp_home.name
        if platform.system().lower() == "windows":
            env["USERPROFILE"] = self.temp_home.name

        cmd = [
            str(executable),
            "tunnel",
            "--url",
            f"http://127.0.0.1:{port}",
            "--no-autoupdate",
        ]
        creationflags = 0
        if platform.system().lower() == "windows":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            creationflags=creationflags,
        )

        lines: queue.Queue[str] = queue.Queue()
        logs: list[str] = []

        def reader() -> None:
            assert self.process is not None
            assert self.process.stdout is not None
            for line in self.process.stdout:
                lines.put(line)

        threading.Thread(target=reader, daemon=True).start()

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                line = lines.get(timeout=0.5)
            except queue.Empty:
                continue
            logs.append(line.strip())
            match = _TRYCLOUDFLARE_RE.search(line)
            if match:
                return match.group(0).rstrip("/")

        detail = "\n".join(logs[-12:]) or "geen cloudflared-uitvoer"
        raise RuntimeError(
            "Cloudflare Quick Tunnel kon niet worden gestart. Controleer internet/firewall. "
            f"Details: {detail}"
        )

    @staticmethod
    def _verify_public_url(url: str, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        last_error = ""
        while time.monotonic() < deadline:
            try:
                response = requests.get(
                    url,
                    headers={"Range": "bytes=0-63"},
                    timeout=10,
                    allow_redirects=True,
                )
                if response.status_code in {200, 206} and response.content:
                    return
                last_error = f"HTTP {response.status_code}"
            except requests.RequestException as exc:
                last_error = str(exc)
            time.sleep(1.0)
        raise RuntimeError(f"Tijdelijke video-URL werd niet bereikbaar. Laatste fout: {last_error}")

    def __enter__(self) -> str:
        if not self.video_path.exists():
            raise FileNotFoundError(f"Motion-video ontbreekt: {self.video_path}")
        if self.progress:
            self.progress("Motion-video tijdelijk beschikbaar maken voor Kling…")

        try:
            port = self._start_local_server()
            base = self._start_cloudflared(port)
            self.public_url = base + "/motion.mp4"
            self._verify_public_url(self.public_url)
            if self.progress:
                self.progress("Tijdelijke beveiligde video-URL is klaar; Kling kan de motion ophalen…")
            return self.public_url
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None

        if self.temp_home is not None:
            try:
                self.temp_home.cleanup()
            except Exception:
                pass
            self.temp_home = None

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
