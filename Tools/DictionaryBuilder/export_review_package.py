#!/usr/bin/env python3
"""Export all dictionary review queues as a compact ChatGPT review package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path


QUEUE_FILES = {
    "definition_alignment": "definition_alignment_review.csv",
    "one_character_chinese": "one_character_chinese_review.csv",
    "missing_part_of_speech": "missing_part_of_speech_candidates.csv",
    "non_chinese_translation": "non_chinese_translation_review.csv",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_common_review_words(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    section = text.split("## Still requiring manual review", maxsplit=1)
    if len(section) != 2:
        return set()
    return {
        match.group(1).strip().lower()
        for match in re.finditer(r"\|\s*`([^`]+)`\s*\|", section[1])
    }


def load_queues(audit_directory: Path) -> dict[str, list[dict[str, str]]]:
    return {
        queue: read_csv(audit_directory / filename)
        for queue, filename in QUEUE_FILES.items()
    }


def parse_json_array(value: str) -> list:
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def load_entries(
    database: Path,
    words: set[str],
) -> dict[str, list[dict]]:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    result: dict[str, list[dict]] = defaultdict(list)
    query = """
        SELECT id, word, normalized_word, uk_ipa, us_ipa, part_of_speech,
               countability, zh_definition, en_definition, examples_json,
               synonyms_json, antonyms_json
        FROM entries
        WHERE normalized_word = ?
        ORDER BY id
    """
    for word in sorted(words):
        for row in connection.execute(query, (word,)):
            item = dict(row)
            item["examples"] = parse_json_array(item.pop("examples_json"))
            item["synonyms"] = parse_json_array(item.pop("synonyms_json"))
            item["antonyms"] = parse_json_array(item.pop("antonyms_json"))
            result[word].append(item)
    connection.close()
    return result


def group_queue_rows(
    queues: dict[str, list[dict[str, str]]],
) -> dict[str, dict[str, list[dict[str, str]]]]:
    grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for queue_name, rows in queues.items():
        for row in rows:
            word = row["normalized_word"].strip().lower()
            grouped[word][queue_name].append(row)
    return grouped


def compact_issues(
    groups: dict[str, list[dict[str, str]]],
) -> dict:
    result: dict[str, object] = {}
    alignment = groups.get("definition_alignment", [])
    if alignment:
        result["definition_alignment"] = [
            {
                "part_of_speech": row["part_of_speech"],
                "chinese_definition": row["zh_definition"],
                "english_definition_count": int(
                    row["english_definition_count"]
                ),
            }
            for row in alignment
        ]
    one_character = groups.get("one_character_chinese", [])
    if one_character:
        result["one_character_chinese"] = [
            {
                "entry_id": int(row["id"]),
                "part_of_speech": row["part_of_speech"],
                "chinese_definition": row["zh_definition"],
            }
            for row in one_character
        ]
    missing = groups.get("missing_part_of_speech", [])
    if missing:
        result["missing_part_of_speech"] = sorted({
            row["missing_part_of_speech"] for row in missing
        })
        result["local_parts_of_speech"] = sorted({
            part
            for row in missing
            for part in row["local_parts_of_speech"].split("|")
            if part
        })
    non_chinese = groups.get("non_chinese_translation", [])
    if non_chinese:
        result["non_chinese_translation"] = [
            {
                "entry_id": int(row["id"]),
                "part_of_speech": row["part_of_speech"],
                "current_definition": row["zh_definition"],
            }
            for row in non_chinese
        ]
    return result


def priority_key(
    word: str,
    issue_groups: dict[str, list[dict[str, str]]],
    common_words: set[str],
) -> tuple:
    if word in common_words:
        tier = 0
    elif len(issue_groups) >= 2:
        tier = 1
    elif "definition_alignment" in issue_groups:
        tier = 2
    elif "one_character_chinese" in issue_groups:
        tier = 3
    elif "missing_part_of_speech" in issue_groups:
        tier = 4
    else:
        tier = 5
    issue_weight = sum(len(rows) for rows in issue_groups.values())
    return tier, -issue_weight, word


def output_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "IPA Dictionary reviewed replacements",
        "type": "object",
        "required": ["word_replacements", "skipped_words"],
        "properties": {
            "word_replacements": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "word", "uk_ipa", "us_ipa", "part_of_speech",
                            "countability", "chinese", "english", "examples",
                        ],
                        "properties": {
                            "word": {"type": "string"},
                            "uk_ipa": {"type": "string"},
                            "us_ipa": {"type": "string"},
                            "part_of_speech": {"type": "string"},
                            "countability": {"type": "string"},
                            "chinese": {"type": "string"},
                            "english": {"type": "string"},
                            "examples": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 1,
                                "items": {
                                    "type": "object",
                                    "required": ["english", "chinese"],
                                    "properties": {
                                        "english": {"type": "string"},
                                        "chinese": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "skipped_words": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["word", "reason"],
                    "properties": {
                        "word": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def instructions_text(manifest: dict) -> str:
    return f"""# ChatGPT dictionary review instructions

This package contains every unresolved item from the IPA Dict audit.
It contains {manifest['unique_words']:,} unique headwords in
{manifest['batch_count']} JSONL batches.

## Task

Review each JSONL record and produce correction JSON files conforming to
`output_schema.json`.

Rules:

1. Keep only common, modern meanings useful in a general learner dictionary.
2. Separate noun, verb, adjective, adverb, and other valid parts of speech.
3. Never use `interjection`; use `exclamation` when that category is needed.
4. Use accurate Traditional Chinese definitions. Do not merely translate an
   English definition without checking the lexical meaning.
5. Each English definition must have its own matching Chinese definition.
6. Include exactly one natural bilingual example for every retained sense.
7. The Chinese example must contain the main Chinese definition word.
8. Preserve or correct UK/US IPA and countability/transitivity.
9. Do not invent missing meanings solely because WordNet proposes a part of
   speech. Add it only when confident it is common and useful.
10. Skip proper nouns, technical abbreviations, or uncertain entries when the
    existing value is already acceptable. Record them in `skipped_words`.
11. Do not modify IDs or return SQL. Return only schema-valid JSON.

## Suggested workflow

- Start with `batches/000-priority-common.jsonl`.
- Continue through the numbered files in order.
- Create one output JSON for each input batch.
- Do not repeat words across output files.
- When all batches are complete, combine their `word_replacements` and
  `skipped_words` into one final JSON file.

## Input record

Each JSONL line contains:

- `word`: normalized headword
- `priority`: why it appears early in the package
- `issues`: audit findings requiring review
- `current_entries`: all current database senses, pronunciations and examples

The audit lists are candidates, not proof of an error. Preserve correct data
and explicitly skip false positives.
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_package(
    database: Path,
    audit_directory: Path,
    common_review: Path,
    output_directory: Path,
    archive: Path,
    batch_size: int,
) -> None:
    queues = load_queues(audit_directory)
    grouped = group_queue_rows(queues)
    common_words = load_common_review_words(common_review)
    reviewed_path = common_review.with_name(
        "chatgpt_reviewed_replacements.json"
    )
    reviewed_words: set[str] = set()
    if reviewed_path.exists():
        reviewed_data = json.loads(reviewed_path.read_text(encoding="utf-8"))
        reviewed_words = set(reviewed_data.get("word_replacements", {})) | {
            item["word"]
            for item in reviewed_data.get("skipped_words", [])
        }
        common_words -= reviewed_words
        grouped = {
            word: groups
            for word, groups in grouped.items()
            if word not in reviewed_words
        }
    all_words = set(grouped) | common_words
    entries = load_entries(database, all_words)

    records: list[dict] = []
    for word in sorted(
        all_words,
        key=lambda item: priority_key(
            item, grouped.get(item, {}), common_words
        ),
    ):
        issue_groups = grouped.get(word, {})
        if word in common_words:
            priority = "common_manual_review"
        elif len(issue_groups) >= 2:
            priority = "multiple_audit_queues"
        else:
            priority = next(iter(issue_groups), "manual_review")
        records.append({
            "word": word,
            "priority": priority,
            "issues": compact_issues(issue_groups),
            "current_entries": entries.get(word, []),
        })

    if output_directory.exists():
        shutil.rmtree(output_directory)
    batches_directory = output_directory / "batches"
    batches_directory.mkdir(parents=True)

    common_records = [
        record for record in records
        if record["priority"] == "common_manual_review"
    ]
    remaining_records = [
        record for record in records
        if record["priority"] != "common_manual_review"
    ]
    batch_files: list[Path] = []

    def write_batch(path: Path, items: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as destination:
            for item in items:
                destination.write(
                    json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
        batch_files.append(path)

    write_batch(
        batches_directory / "000-priority-common.jsonl",
        common_records,
    )
    for index, offset in enumerate(
        range(0, len(remaining_records), batch_size),
        start=1,
    ):
        write_batch(
            batches_directory / f"{index:03d}-review.jsonl",
            remaining_records[offset:offset + batch_size],
        )

    queue_row_counts = {
        queue: len(rows) for queue, rows in queues.items()
    }
    queue_word_counts = {
        queue: len({row["normalized_word"] for row in rows})
        for queue, rows in queues.items()
    }
    manifest = {
        "format_version": 1,
        "generated_on": date.today().isoformat(),
        "database": database.name,
        "database_sha256": sha256(database),
        "entry_count": sum(len(value) for value in entries.values()),
        "unique_words": len(records),
        "common_manual_review_words": len(common_records),
        "excluded_reviewed_words": len(reviewed_words),
        "words_in_multiple_queues": sum(
            len(groups) >= 2 for groups in grouped.values()
        ),
        "audit_queue_rows": queue_row_counts,
        "audit_queue_unique_words": queue_word_counts,
        "batch_size": batch_size,
        "batch_count": len(batch_files),
        "batches": [],
    }

    schema_path = output_directory / "output_schema.json"
    schema_path.write_text(
        json.dumps(output_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    instructions_path = output_directory / "instructions.md"
    instructions_path.write_text(
        instructions_text(manifest),
        encoding="utf-8",
    )
    for path in batch_files:
        manifest["batches"].append({
            "file": str(path.relative_to(output_directory)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "records": sum(
                1 for _ in path.open(encoding="utf-8")
            ),
        })
    manifest_path = output_directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as bundle:
        for path in sorted(output_directory.rglob("*")):
            if path.is_file():
                bundle.write(
                    path,
                    Path(output_directory.name) / path.relative_to(
                        output_directory
                    ),
                )
    print(
        f"Created {archive} with {len(records):,} unique words in "
        f"{len(batch_files)} batches."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument("--audit-directory", type=Path, required=True)
    parser.add_argument(
        "--common-review",
        type=Path,
        default=Path("Tools/DictionaryBuilder/CommonWordCuration.md"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ChatGPTReviewPackage"
        ),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ChatGPTDictionaryReview.zip"
        ),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()
    export_package(
        args.database,
        args.audit_directory,
        args.common_review,
        args.output_directory,
        args.archive,
        args.batch_size,
    )


if __name__ == "__main__":
    main()
