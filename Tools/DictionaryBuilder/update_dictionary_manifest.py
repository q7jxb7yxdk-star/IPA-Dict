#!/usr/bin/env python3
"""Update the bundled dictionary manifest.

The manifest is intentionally small and human-readable so every platform can
display the same database date without opening SQLite first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_TIME_ZONE = "Asia/Hong_Kong"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate IPA Dict/Data/dictionary_manifest.json."
    )
    parser.add_argument(
        "--updated-at",
        help=(
            "Database update time in ISO 8601 format. "
            "Defaults to current Asia/Hong_Kong time."
        ),
    )
    parser.add_argument(
        "--time-zone",
        default=DEFAULT_TIME_ZONE,
        help="IANA time zone used when --updated-at is omitted.",
    )
    return parser.parse_args()


def manifest_time(args: argparse.Namespace) -> datetime:
    if args.updated_at:
        parsed = datetime.fromisoformat(args.updated_at)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(args.time_zone))
        return parsed
    return datetime.now(ZoneInfo(args.time_zone)).replace(microsecond=0)


def main() -> None:
    args = parse_arguments()
    root = project_root()
    database_path = root / "IPA Dict" / "Data" / "dictionary.sqlite"
    manifest_path = root / "IPA Dict" / "Data" / "dictionary_manifest.json"

    updated_at = manifest_time(args)
    generated_at = datetime.now(ZoneInfo(args.time_zone)).replace(microsecond=0)

    manifest = {
        "database_file": "dictionary.sqlite",
        "database_updated_at": updated_at.isoformat(),
        "display_updated_at": updated_at.strftime("%Y-%m-%d %H:%M"),
        "sha256": sha256_digest(database_path),
        "generated_at": generated_at.isoformat(),
    }

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {manifest_path.relative_to(root)}")
    print(f"Database date: {manifest['display_updated_at']}")
    print(f"SHA-256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
