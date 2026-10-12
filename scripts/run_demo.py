"""Start the local, engine-only API and browser demo in one terminal.

Run with backend/.venv/Scripts/python.exe from the repository root.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"
WEB = "http://127.0.0.1:3000/"
OPENER = build_opener(ProxyHandler({}))


def get(url: str) -> bytes | None:
    try:
        with OPENER.open(url, timeout=1) as response:
            return response.read()
    except (OSError, URLError):
        return None


def wait_for(url: str, process: subprocess.Popen[bytes] | None) -> bytes:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"A local server exited with code {process.returncode}.")
        body = get(url)
        if body is not None:
            return body
        time.sleep(0.25)
    raise RuntimeError(f"Local server did not respond at {url} within 15 seconds.")


def stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check startup, then stop without opening a browser")
    parser.add_argument("--live", action="store_true", help="Offer billable AI-assisted matching in the browser")
    args = parser.parse_args()
    processes: list[subprocess.Popen[bytes]] = []
    try:
        health = get(API + "/api/health")
        if health is None:
            environment = os.environ.copy()
            if args.live:
                environment["VENTUREMATCH_ENABLE_LIVE_AGENT"] = "1"
            else:
                environment.pop("VENTUREMATCH_ENABLE_LIVE_AGENT", None)
            api = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=ROOT / "backend", env=environment,
            )
            processes.append(api)
            health = wait_for(API + "/api/health", api)
        health_status = json.loads(health)
        if health_status.get("status") != "ok":
            raise RuntimeError("Port 8000 is occupied by a different service.")
        if args.live and not health_status.get("live_agent_enabled"):
            raise RuntimeError(
                "An engine-only backend is already running on port 8000. "
                "Stop its terminal with Ctrl+C, then rerun with --live."
            )
        print(
            "Backend ready: " + API + (" (AI-assisted available)" if health_status.get("live_agent_enabled") else " (free engine only)"),
            flush=True,
        )

        page = get(WEB)
        if page is None:
            frontend = subprocess.Popen(
                [sys.executable, "-m", "http.server", "3000", "--bind", "127.0.0.1"],
                cwd=ROOT / "frontend",
            )
            processes.append(frontend)
            page = wait_for(WEB, frontend)
        if b"VentureMatch AI" not in page:
            raise RuntimeError("Port 3000 is occupied by a different website.")
        print("Demo ready: " + WEB, flush=True)

        if args.check:
            print("Local startup check passed.", flush=True)
            return 0
        if args.live:
            print("AI-assisted selection makes a billable OpenAI call only after browser confirmation.", flush=True)
        webbrowser.open(WEB)
        print("If your browser did not open, paste the demo URL above into Chrome.", flush=True)
        print("Keep this terminal open. Press Ctrl+C to stop servers started here.", flush=True)
        while True:
            for process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f"A local server stopped with code {process.returncode}.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping local demo.", flush=True)
        return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Could not start demo: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
