"""Download MediaPipe task files needed by computer_vision/analyzer.py.

Run from project root: python computer_vision/download_models.py
"""
from __future__ import annotations
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
BASE_URL = "https://raw.githubusercontent.com/chaithra-chaii/AI-Presentation-Coach/main/computer_vision/models/"
MODEL_FILES = ("face_landmarker.task", "hand_landmarker.task", "pose_landmarker_full.task", "pose_landmarker_lite.task")
MIN_MODEL_BYTES = 100_000

def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in MODEL_FILES:
        destination = MODELS_DIR / filename
        if destination.exists() and destination.stat().st_size >= MIN_MODEL_BYTES:
            print(f"Already present: {filename}")
            continue
        temporary = destination.with_suffix(destination.suffix + ".part")
        print(f"Downloading {filename} ...")
        try:
            request = urllib.request.Request(BASE_URL + filename, headers={"User-Agent": "AI-Presentation-Coach-Model-Setup"})
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            size = temporary.stat().st_size
            if size < MIN_MODEL_BYTES:
                raise RuntimeError(f"Downloaded file too small ({size} bytes); check the source URL.")
            temporary.replace(destination)
            print(f"Saved {filename} ({size:,} bytes)")
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            print(f"Failed to download {filename}: {exc}", file=sys.stderr)
            return 1
    print(f"All models are ready in {MODELS_DIR}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
