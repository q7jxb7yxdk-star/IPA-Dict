#!/usr/bin/env python3
"""Normalize adjective Traditional Chinese definitions.

For display consistency, adjective gloss segments should read adjectivally in
Chinese. This tool appends ``的`` to each semicolon-separated Chinese segment
for rows whose part of speech is ``adjective``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DATABASE = Path("IPA Dict/Data/dictionary.sqlite")
DEFAULT_REPORT = Path("Tools/DictionaryBuilder/adjective_definition_suffix_report.json")
TOOL_VERSION = "adjective_definition_suffix_v1"


def needs_suffix(segment: str) -> bool:
    stripped = segment.strip()
    if not stripped:
        return False
    return not stripped.endswith("的")


def normalize_definition(value: str) -> str:
    parts = [part.strip() for part in value.split("；")]
    normalized: list[str] = []
    for part in parts:
        if not part:
            continue
        normalized.append(f"{part}的" if needs_suffix(part) else part)
    return "；".join(normalized)


def integrity_check(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else ""


def normalize_database(
    database: Path,
    report_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    if not database.exists():
        raise FileNotFoundError(database)

    backup_path = Path("/tmp") / (
        f"{database.stem}-before-adjective-suffix-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}{database.suffix}"
    )
    if not dry_run:
        shutil.copy2(database, backup_path)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row

    before_total = connection.execute(
        "SELECT COUNT(*) FROM entries WHERE part_of_speech = 'adjective'"
    ).fetchone()[0]
    before_missing = connection.execute(
        """
        SELECT COUNT(*)
        FROM entries
        WHERE part_of_speech = 'adjective'
          AND zh_definition NOT LIKE '%的'
        """
    ).fetchone()[0]
    rows = connection.execute(
        """
        SELECT id, word, normalized_word, zh_definition
        FROM entries
        WHERE part_of_speech = 'adjective'
        ORDER BY normalized_word, id
        """
    ).fetchall()

    updates: list[dict[str, Any]] = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        for row in rows:
            original = row["zh_definition"]
            normalized = normalize_definition(original)
            if normalized == original:
                continue
            connection.execute(
                "UPDATE entries SET zh_definition = ? WHERE id = ?",
                (normalized, row["id"]),
            )
            updates.append({
                "id": row["id"],
                "word": row["word"],
                "normalized_word": row["normalized_word"],
                "old_chinese": original,
                "new_chinese": normalized,
            })

        check = integrity_check(connection)
        if check != "ok":
            raise RuntimeError(f"integrity_check failed: {check}")

        if dry_run:
            connection.execute("ROLLBACK")
        else:
            connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise

    after_missing = connection.execute(
        """
        SELECT COUNT(*)
        FROM entries
        WHERE part_of_speech = 'adjective'
          AND zh_definition NOT LIKE '%的'
        """
    ).fetchone()[0]
    final_check = integrity_check(connection)
    connection.close()

    report = {
        "tool": Path(__file__).name,
        "tool_version": TOOL_VERSION,
        "database": str(database),
        "dry_run": dry_run,
        "backup_path": None if dry_run else str(backup_path),
        "adjective_entry_count": before_total,
        "before_missing_suffix_count": before_missing,
        "after_missing_suffix_count": after_missing,
        "updated_entry_count": len(updates),
        "integrity_check": final_check,
        "sample_updates": updates[:100],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = normalize_database(args.database, args.report, args.dry_run)
    print(json.dumps({
        "dry_run": report["dry_run"],
        "adjective_entry_count": report["adjective_entry_count"],
        "before_missing_suffix_count": report["before_missing_suffix_count"],
        "after_missing_suffix_count": report["after_missing_suffix_count"],
        "updated_entry_count": report["updated_entry_count"],
        "integrity_check": report["integrity_check"],
        "report": str(args.report),
        "backup_path": report["backup_path"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
