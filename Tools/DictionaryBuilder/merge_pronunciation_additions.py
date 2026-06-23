#!/usr/bin/env python3
"""Merge only newly sourced regional IPA into an existing review ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def key(item: dict) -> tuple[str, str, str]:
    return (
        str(item["word"]).strip().lower(),
        str(item["part_of_speech"]).strip().lower(),
        str(item["english"]).strip(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-note",
        default=(
            "Incremental explicit-regional additions from Kaikki English "
            "downloaded 2026-06-23; existing verified values preserved."
        ),
    )
    args = parser.parse_args()

    existing = json.loads(args.existing.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    candidate_by_key = {
        key(item): item
        for item in candidate.get("resolutions", [])
    }
    uk_added = 0
    us_added = 0
    for item in existing.get("resolutions", []):
        incoming = candidate_by_key.get(key(item))
        if incoming is None:
            continue
        if not item.get("uk_ipa") and incoming.get("uk_ipa"):
            item["uk_ipa"] = incoming["uk_ipa"]
            item["uk_candidates"] = incoming.get("uk_candidates", [])
            item["source_part_of_speech"] = incoming.get(
                "source_part_of_speech",
                item.get("source_part_of_speech", ""),
            )
            item["replace_uk"] = False
            item["clear_uk"] = False
            uk_added += 1
        if not item.get("us_ipa") and incoming.get("us_ipa"):
            item["us_ipa"] = incoming["us_ipa"]
            item["us_candidates"] = incoming.get("us_candidates", [])
            item["source_part_of_speech"] = incoming.get(
                "source_part_of_speech",
                item.get("source_part_of_speech", ""),
            )
            item["replace_us"] = False
            item["clear_us"] = False
            us_added += 1

    existing["incremental_source_note"] = args.source_note
    existing["incremental_uk_additions"] = uk_added
    existing["incremental_us_additions"] = us_added
    resolutions = existing.get("resolutions", [])
    existing["matched_uk_count"] = sum(
        bool(item.get("uk_ipa")) for item in resolutions
    )
    existing["matched_us_count"] = sum(
        bool(item.get("us_ipa")) for item in resolutions
    )
    args.output.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "uk_added": uk_added,
        "us_added": us_added,
        "matched_uk_count": existing["matched_uk_count"],
        "matched_us_count": existing["matched_us_count"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
