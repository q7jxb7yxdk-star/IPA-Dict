#!/usr/bin/env python3
"""Merge same-headword same-part-of-speech rows in the bundled SQLite dictionary.

The app displays dictionary results grouped by part of speech. This tool makes
the SQLite data match that model by collapsing rows with the same
``normalized_word`` and ``part_of_speech`` into one row while preserving unique
definitions, one example, and unioned linked-word lists.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


TOOL_VERSION = "same_pos_merge_v2"
DEFAULT_DATABASE = Path("IPA Dict/Data/dictionary.sqlite")
DEFAULT_REPORT = Path("Tools/DictionaryBuilder/same_pos_merge_report.json")

PROVENANCE_PRIORITY = {
    "ai_reviewed": 5,
    "source_or_reviewed": 4,
    "source_or_curated": 4,
    "verified_source": 3,
    "generated_fallback": 1,
}


def unique_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join((value or "").split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def merge_grammar_labels(values: list[str]) -> str:
    labels = unique_nonempty(values)
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]

    atoms: set[str] = set()
    for label in labels:
        for part in label.split(" or "):
            part = part.strip()
            if part:
                atoms.add(part)

    if atoms == {"C", "U"}:
        return "C or U"
    if atoms == {"I", "T"}:
        return "I or T"

    ordered_atoms = [atom for atom in ("C", "U", "I", "T") if atom in atoms]
    ordered_atoms.extend(sorted(atoms - set(ordered_atoms)))
    if ordered_atoms:
        return " or ".join(ordered_atoms)
    return " or ".join(labels)


def bulleted_definitions(values: list[str]) -> str:
    definitions = unique_nonempty(values)
    if not definitions:
        return ""
    if len(definitions) == 1:
        return definitions[0]
    return "\n".join(
        f"- {definition}"
        for definition in definitions
    )


def decode_json_array(value: str) -> list[Any]:
    try:
        decoded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def merge_word_list_json(values: list[str]) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in decode_json_array(value):
            if not isinstance(item, str):
                continue
            word = item.strip()
            key = word.lower()
            if word and key not in seen:
                seen.add(key)
                words.append(word)
    return compact_json(words)


def choose_example_json(rows: list[sqlite3.Row]) -> tuple[str, int | None]:
    for row in rows:
        examples = decode_json_array(row["examples_json"])
        for example in examples:
            if not isinstance(example, dict):
                continue
            english = str(example.get("english", "")).strip()
            chinese = str(example.get("chinese", "")).strip()
            if english and chinese:
                return compact_json([{"english": english, "chinese": chinese}]), row["id"]
    return "[]", None


def choose_first_nonempty(
    rows: list[sqlite3.Row],
    column: str,
) -> tuple[str, int | None, bool]:
    values = unique_nonempty([row[column] for row in rows])
    has_conflict = len(values) > 1
    for row in rows:
        value = (row[column] or "").strip()
        if value:
            return value, row["id"], has_conflict
    return "", None, has_conflict


def load_groups(connection: sqlite3.Connection) -> list[list[sqlite3.Row]]:
    grouped_keys = connection.execute(
        """
        SELECT normalized_word, part_of_speech
        FROM entries
        GROUP BY normalized_word, part_of_speech
        HAVING COUNT(*) > 1
        ORDER BY normalized_word, part_of_speech
        """
    ).fetchall()

    groups: list[list[sqlite3.Row]] = []
    for key in grouped_keys:
        rows = connection.execute(
            """
            SELECT *
            FROM entries
            WHERE normalized_word = ? AND part_of_speech = ?
            ORDER BY id
            """,
            (key["normalized_word"], key["part_of_speech"]),
        ).fetchall()
        groups.append(rows)
    return groups


def best_provenance(
    connection: sqlite3.Connection,
    entry_ids: list[int],
    content_kind: str,
) -> sqlite3.Row | None:
    placeholders = ",".join("?" for _ in entry_ids)
    rows = connection.execute(
        f"""
        SELECT *
        FROM entry_provenance
        WHERE content_kind = ? AND entry_id IN ({placeholders})
        """,
        (content_kind, *entry_ids),
    ).fetchall()
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            PROVENANCE_PRIORITY.get(row["provenance"], 0),
            -entry_ids.index(row["entry_id"]),
        ),
    )


def upsert_provenance(
    connection: sqlite3.Connection,
    entry_id: int,
    content_kind: str,
    provenance: str,
    source: str,
    generator_version: str,
) -> None:
    connection.execute(
        """
        INSERT INTO entry_provenance (
            entry_id, content_kind, provenance, source, generator_version
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entry_id, content_kind) DO UPDATE SET
            provenance = excluded.provenance,
            source = excluded.source,
            generator_version = excluded.generator_version
        """,
        (entry_id, content_kind, provenance, source, generator_version),
    )


def copy_best_provenance(
    connection: sqlite3.Connection,
    retained_id: int,
    source_ids: list[int],
    content_kind: str,
) -> None:
    row = best_provenance(connection, source_ids, content_kind)
    if row is None:
        return
    upsert_provenance(
        connection,
        retained_id,
        content_kind,
        row["provenance"],
        row["source"],
        row["generator_version"],
    )


def mark_merged_provenance(
    connection: sqlite3.Connection,
    retained_id: int,
    content_kind: str,
) -> None:
    upsert_provenance(
        connection,
        retained_id,
        content_kind,
        "source_or_reviewed",
        "same_pos_merge",
        TOOL_VERSION,
    )


def merge_group(
    connection: sqlite3.Connection,
    rows: list[sqlite3.Row],
) -> dict[str, Any]:
    retained = rows[0]
    retained_id = retained["id"]
    merged_ids = [row["id"] for row in rows[1:]]
    all_ids = [row["id"] for row in rows]

    uk_ipa, uk_source_id, uk_conflict = choose_first_nonempty(rows, "uk_ipa")
    us_ipa, us_source_id, us_conflict = choose_first_nonempty(rows, "us_ipa")
    example_json, example_source_id = choose_example_json(rows)

    merged_values = {
        "word": retained["word"],
        "normalized_word": retained["normalized_word"],
        "uk_ipa": uk_ipa,
        "us_ipa": us_ipa,
        "part_of_speech": retained["part_of_speech"],
        "countability": merge_grammar_labels([row["countability"] for row in rows]),
        "zh_definition": "；".join(
            unique_nonempty([row["zh_definition"] for row in rows])
        ),
        "en_definition": bulleted_definitions([row["en_definition"] for row in rows]),
        "examples_json": example_json,
        "synonyms_json": merge_word_list_json([row["synonyms_json"] for row in rows]),
        "antonyms_json": merge_word_list_json([row["antonyms_json"] for row in rows]),
    }

    connection.execute(
        """
        UPDATE entries
        SET word = ?,
            normalized_word = ?,
            uk_ipa = ?,
            us_ipa = ?,
            part_of_speech = ?,
            countability = ?,
            zh_definition = ?,
            en_definition = ?,
            examples_json = ?,
            synonyms_json = ?,
            antonyms_json = ?
        WHERE id = ?
        """,
        (
            merged_values["word"],
            merged_values["normalized_word"],
            merged_values["uk_ipa"],
            merged_values["us_ipa"],
            merged_values["part_of_speech"],
            merged_values["countability"],
            merged_values["zh_definition"],
            merged_values["en_definition"],
            merged_values["examples_json"],
            merged_values["synonyms_json"],
            merged_values["antonyms_json"],
            retained_id,
        ),
    )

    if len(unique_nonempty([row["zh_definition"] for row in rows])) > 1:
        mark_merged_provenance(connection, retained_id, "zh_definition")
    else:
        copy_best_provenance(connection, retained_id, all_ids, "zh_definition")

    if len(unique_nonempty([row["en_definition"] for row in rows])) > 1:
        mark_merged_provenance(connection, retained_id, "en_definition")
    else:
        copy_best_provenance(connection, retained_id, all_ids, "en_definition")

    if example_source_id is not None:
        copy_best_provenance(connection, retained_id, [example_source_id], "example")
    else:
        copy_best_provenance(connection, retained_id, all_ids, "example")

    if uk_source_id is not None:
        copy_best_provenance(connection, retained_id, [uk_source_id], "uk_ipa")
    else:
        copy_best_provenance(connection, retained_id, all_ids, "uk_ipa")

    if us_source_id is not None:
        copy_best_provenance(connection, retained_id, [us_source_id], "us_ipa")
    else:
        copy_best_provenance(connection, retained_id, all_ids, "us_ipa")

    if merged_ids:
        placeholders = ",".join("?" for _ in merged_ids)
        connection.execute(
            f"DELETE FROM entry_provenance WHERE entry_id IN ({placeholders})",
            merged_ids,
        )
        connection.execute(
            f"DELETE FROM entries WHERE id IN ({placeholders})",
            merged_ids,
        )

    return {
        "word": retained["normalized_word"],
        "part_of_speech": retained["part_of_speech"],
        "retained_id": retained_id,
        "merged_ids": merged_ids,
        "row_count": len(rows),
        "zh_definition_count": len(
            unique_nonempty([row["zh_definition"] for row in rows])
        ),
        "en_definition_count": len(
            unique_nonempty([row["en_definition"] for row in rows])
        ),
        "countability_values": unique_nonempty([row["countability"] for row in rows]),
        "uk_ipa_conflict": uk_conflict,
        "us_ipa_conflict": us_conflict,
    }


def integrity_check(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else ""


def orphan_provenance_count(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM entry_provenance
        WHERE entry_id NOT IN (SELECT id FROM entries)
        """
    ).fetchone()
    return int(row[0])


NUMBERED_DEFINITION_PATTERN = re.compile(r"^\s*\d+\.\s+(.+)$")


def numbered_list_to_bullets(value: str) -> str | None:
    lines = value.splitlines()
    if len(lines) < 2:
        return None

    converted: list[str] = []
    for line in lines:
        match = NUMBERED_DEFINITION_PATTERN.match(line)
        if match is None:
            return None
        converted.append(f"- {match.group(1).strip()}")

    return "\n".join(converted)


def reformat_numbered_definitions(
    database: Path,
    report_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    if not database.exists():
        raise FileNotFoundError(database)

    backup_path = Path("/tmp") / (
        f"{database.stem}-before-definition-reformat-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}{database.suffix}"
    )
    if not dry_run:
        shutil.copy2(database, backup_path)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row

    before_entries = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    rows = connection.execute(
        "SELECT id, normalized_word, part_of_speech, en_definition FROM entries"
    ).fetchall()

    updates: list[dict[str, Any]] = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        for row in rows:
            converted = numbered_list_to_bullets(row["en_definition"])
            if converted is None:
                continue
            connection.execute(
                "UPDATE entries SET en_definition = ? WHERE id = ?",
                (converted, row["id"]),
            )
            updates.append({
                "id": row["id"],
                "word": row["normalized_word"],
                "part_of_speech": row["part_of_speech"],
            })

        check = integrity_check(connection)
        orphans = orphan_provenance_count(connection)
        if check != "ok":
            raise RuntimeError(f"integrity_check failed: {check}")
        if orphans:
            raise RuntimeError(f"orphan provenance rows remain: {orphans}")

        if dry_run:
            connection.execute("ROLLBACK")
        else:
            connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise

    after_entries = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    final_check = integrity_check(connection)
    final_orphans = orphan_provenance_count(connection)
    connection.close()

    report = {
        "tool": Path(__file__).name,
        "tool_version": TOOL_VERSION,
        "operation": "reformat_numbered_definitions",
        "database": str(database),
        "dry_run": dry_run,
        "backup_path": None if dry_run else str(backup_path),
        "before": {
            "entries": before_entries,
        },
        "after": {
            "entries": after_entries,
        },
        "reformatted_entry_count": len(updates),
        "integrity_check": final_check,
        "orphan_provenance_count": final_orphans,
        "sample_updates": updates[:100],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def merge_database(database: Path, report_path: Path, dry_run: bool) -> dict[str, Any]:
    if not database.exists():
        raise FileNotFoundError(database)

    backup_path = Path("/tmp") / (
        f"{database.stem}-before-same-pos-merge-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}{database.suffix}"
    )
    if not dry_run:
        shutil.copy2(database, backup_path)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row

    before_entries = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    before_provenance = connection.execute(
        "SELECT COUNT(*) FROM entry_provenance"
    ).fetchone()[0]
    groups = load_groups(connection)

    reports: list[dict[str, Any]] = []
    pos_counter: Counter[str] = Counter()
    row_delete_count = 0
    ipa_conflicts: list[dict[str, Any]] = []
    grammar_conflicts: list[dict[str, Any]] = []

    try:
        connection.execute("BEGIN IMMEDIATE")
        for rows in groups:
            item = merge_group(connection, rows)
            reports.append(item)
            pos_counter[item["part_of_speech"]] += 1
            row_delete_count += len(item["merged_ids"])
            if item["uk_ipa_conflict"] or item["us_ipa_conflict"]:
                ipa_conflicts.append(item)
            if len(item["countability_values"]) > 1:
                grammar_conflicts.append(item)

        check = integrity_check(connection)
        orphans = orphan_provenance_count(connection)
        if check != "ok":
            raise RuntimeError(f"integrity_check failed: {check}")
        if orphans:
            raise RuntimeError(f"orphan provenance rows remain: {orphans}")

        if dry_run:
            connection.execute("ROLLBACK")
        else:
            connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise

    after_entries = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    after_provenance = connection.execute(
        "SELECT COUNT(*) FROM entry_provenance"
    ).fetchone()[0]
    final_check = integrity_check(connection)
    final_orphans = orphan_provenance_count(connection)
    connection.close()

    report = {
        "tool": Path(__file__).name,
        "tool_version": TOOL_VERSION,
        "database": str(database),
        "dry_run": dry_run,
        "backup_path": None if dry_run else str(backup_path),
        "before": {
            "entries": before_entries,
            "entry_provenance": before_provenance,
        },
        "after": {
            "entries": after_entries,
            "entry_provenance": after_provenance,
        },
        "merged_group_count": len(groups),
        "deleted_entry_count": row_delete_count,
        "groups_by_part_of_speech": dict(sorted(pos_counter.items())),
        "ipa_conflict_count": len(ipa_conflicts),
        "grammar_conflict_count": len(grammar_conflicts),
        "integrity_check": final_check,
        "orphan_provenance_count": final_orphans,
        "sample_merges": reports[:50],
        "ipa_conflicts": ipa_conflicts[:100],
        "grammar_conflicts": grammar_conflicts[:100],
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
    parser.add_argument(
        "--reformat-numbered-definitions",
        action="store_true",
        help="Convert merged numbered English definitions to unordered lists.",
    )
    args = parser.parse_args()

    if args.reformat_numbered_definitions:
        report = reformat_numbered_definitions(
            args.database,
            args.report,
            args.dry_run,
        )
        summary = {
            "operation": report["operation"],
            "dry_run": report["dry_run"],
            "reformatted_entry_count": report["reformatted_entry_count"],
            "before_entries": report["before"]["entries"],
            "after_entries": report["after"]["entries"],
            "integrity_check": report["integrity_check"],
            "orphan_provenance_count": report["orphan_provenance_count"],
            "report": str(args.report),
            "backup_path": report["backup_path"],
        }
    else:
        report = merge_database(args.database, args.report, args.dry_run)
        summary = {
            "operation": "merge_same_pos_entries",
            "dry_run": report["dry_run"],
            "merged_group_count": report["merged_group_count"],
            "deleted_entry_count": report["deleted_entry_count"],
            "before_entries": report["before"]["entries"],
            "after_entries": report["after"]["entries"],
            "integrity_check": report["integrity_check"],
            "orphan_provenance_count": report["orphan_provenance_count"],
            "report": str(args.report),
            "backup_path": report["backup_path"],
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
