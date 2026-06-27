#!/usr/bin/env python3
"""Audit bundled phoneme MP3 files against AudioPlayerService mappings.

This script is intentionally lightweight and read-only. It checks that every
`ipa_*` file name referenced by `AudioPlayerService.phonemeAudioMap` exists in
the app bundle audio folder, that no bundled MP3 is orphaned, and that each MP3
can be decoded by ffprobe with a short single-shot duration.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_SWIFT_FILE = Path("IPA Dict/Services/AudioPlayerService.swift")
DEFAULT_AUDIO_DIR = Path("IPA Dict/Audio/Phonemes")


def mapped_file_stems(swift_file: Path) -> set[str]:
    text = swift_file.read_text(encoding="utf-8")
    return set(re.findall(r'"(ipa_[a-z0-9_]+)"', text))


def mp3_duration(path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def audit(swift_file: Path, audio_dir: Path, max_duration: float) -> dict:
    mapped = mapped_file_stems(swift_file)
    bundled = {path.stem for path in audio_dir.glob("*.mp3")}

    invalid_files: list[str] = []
    long_files: list[dict] = []

    for path in sorted(audio_dir.glob("*.mp3")):
        duration = mp3_duration(path)
        if duration is None:
            invalid_files.append(path.name)
        elif duration > max_duration:
            long_files.append(
                {
                    "file": path.name,
                    "duration": round(duration, 3),
                    "max_duration": max_duration,
                }
            )

    missing_files = sorted(f"{stem}.mp3" for stem in mapped - bundled)
    orphan_files = sorted(f"{stem}.mp3" for stem in bundled - mapped)

    return {
        "swift_file": str(swift_file),
        "audio_dir": str(audio_dir),
        "mapped_file_count": len(mapped),
        "bundled_mp3_count": len(bundled),
        "missing_files": missing_files,
        "orphan_files": orphan_files,
        "invalid_files": invalid_files,
        "long_files": long_files,
        "max_duration": max_duration,
        "passed": not (
            missing_files or orphan_files or invalid_files or long_files
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--swift-file", type=Path, default=DEFAULT_SWIFT_FILE)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--max-duration", type=float, default=1.3)
    args = parser.parse_args()

    report = audit(args.swift_file, args.audio_dir, args.max_duration)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
