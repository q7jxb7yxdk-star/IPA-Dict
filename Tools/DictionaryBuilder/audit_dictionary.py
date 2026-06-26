#!/usr/bin/env python3
"""Audit the bundled dictionary without modifying it."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from generate_common_curation import traditional


CORE_POS = {"noun", "verb", "adjective", "adverb"}
OEWN_POS = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}
MARKUP_PATTERN = re.compile(r"\[\[|\]\]|\{\{|\}\}")
PERCENT_ENCODING_PATTERN = re.compile(r"(?:%[0-9A-Fa-f]{2}){2,}")
IPA_MARKUP_PATTERN = re.compile(r"<[^>]+>|\[\[|\]\]|\{\{|\}\}|ref:")
HAN_PATTERN = re.compile(
    r"[\u3007\u3400-\u4DBF\u4E00-\u9FFF\U00020000-\U0003134F]"
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_entries(connection: sqlite3.Connection) -> list[dict]:
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(
        """
        SELECT id, word, normalized_word, uk_ipa, us_ipa, part_of_speech,
               countability, zh_definition, en_definition, examples_json
        FROM entries
        ORDER BY normalized_word, id
        """
    )]


def corruption_reasons(chinese: str) -> list[str]:
    reasons: list[str] = []
    if PERCENT_ENCODING_PATTERN.search(chinese):
        reasons.append("percent_encoded")
    if MARKUP_PATTERN.search(chinese):
        reasons.append("wiki_markup")
    if chinese.strip() in {"&", "0.5", "[[#", "}}"}:
        reasons.append("invalid_literal")
    return reasons


def load_oewn_parts(archive: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if not name.startswith("entries-") or not name.endswith(".json"):
                continue
            data = json.loads(bundle.read(name))
            for lemma, parts in data.items():
                word = " ".join(lemma.replace("_", " ").strip().lower().split())
                for code in parts:
                    if code in OEWN_POS:
                        result[word].add(OEWN_POS[code])
    return result


def load_alignment_resolution_keys(path: Path | None) -> set[tuple[str, str, str]]:
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (
            item["word"],
            item["part_of_speech"].lower(),
            traditional(str(item["chinese"])),
        )
        for item in data.get("resolutions", [])
    }


def load_one_character_resolution_keys(
    path: Path | None,
) -> set[tuple[str, str, str, str]]:
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (
            item["word"],
            item["part_of_speech"].lower(),
            traditional(str(item.get("resolved_chinese", item["chinese"]))),
            item["english"],
        )
        for item in data.get("resolutions", [])
    }


def load_grammar_exemption_keys(
    path: Path | None,
) -> set[tuple[str, str, str]]:
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    result = set()
    for item in data.get("reviews", []):
        resolved = item.get("structural_resolution")
        if (
            not isinstance(resolved, dict)
            or resolved.get("grammar_applicable", True)
        ):
            continue
        result.add((
            item["word"],
            resolved["new_part_of_speech"].lower(),
            resolved["new_english"],
        ))
    return result


def load_missing_part_of_speech_resolution_keys(
    path: Path | None,
) -> set[tuple[str, str]]:
    if path is None:
        return set()
    resolution_path = path.with_name(
        "missing_part_of_speech_review_resolutions.json"
    )
    if not resolution_path.exists():
        return set()
    data = json.loads(resolution_path.read_text(encoding="utf-8"))
    return {
        (
            str(item["word"]).strip().lower(),
            str(item["missing_part_of_speech"]).strip().lower(),
        )
        for item in data.get("resolutions", [])
        if item.get("status") in {
            "accepted_for_future_curation",
            "deferred_needs_chinese_source",
            "rejected_not_in_current_scope",
            "rejected_proper_name_or_demonym_overlap",
        }
    }


def load_regional_ipa_evidence(
    path: Path | None,
) -> dict[tuple[str, str, str], dict[str, set[str]]]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for item in data.get("resolutions", []):
        key = (
            item["word"],
            item["part_of_speech"].lower(),
            item["english"],
        )
        result[key] = {
            "uk": set(item.get("uk_candidates", [])),
            "us": set(item.get("us_candidates", [])),
        }
    return result


def load_semantic_corrections(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    return json.loads(
        path.read_text(encoding="utf-8")
    ).get("corrections", [])


def audit(
    database: Path,
    output: Path,
    oewn_archive: Path | None,
    alignment_resolutions: Path | None,
    one_character_resolutions: Path | None,
    grammar_structural_resolutions: Path | None,
    pronunciation_resolutions: Path | None,
    semantic_corrections: Path | None,
) -> None:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    entries = load_entries(connection)
    has_provenance_table = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'entry_provenance'
        """
    ).fetchone() is not None
    provenance_counts: dict[str, int] = {}
    if has_provenance_table:
        provenance_counts = {
            f"{kind}:{provenance}": count
            for kind, provenance, count in connection.execute(
                """
                SELECT content_kind, provenance, COUNT(*)
                FROM entry_provenance
                GROUP BY content_kind, provenance
                """
            )
        }

    corrupt_rows: list[dict] = []
    non_chinese_rows: list[dict] = []
    one_character_rows: list[dict] = []
    malformed_ipa_rows: list[dict] = []
    suspicious_regional_ipa_rows: list[dict] = []
    missing_ipa_rows: list[dict] = []
    missing_uk_ipa_count = 0
    missing_us_ipa_count = 0
    missing_example_rows: list[dict] = []
    invalid_example_rows: list[dict] = []
    missing_grammar_label_rows: list[dict] = []
    nonstandard_part_rows: list[dict] = []
    semantic_correction_failures: list[dict] = []
    grouped_definitions: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    local_parts: dict[str, set[str]] = defaultdict(set)
    grammar_exemption_keys = load_grammar_exemption_keys(
        grammar_structural_resolutions
    )
    missing_part_resolution_keys = (
        load_missing_part_of_speech_resolution_keys(semantic_corrections)
    )
    regional_ipa_evidence = load_regional_ipa_evidence(
        pronunciation_resolutions
    )

    for entry in entries:
        malformed_fields: list[str] = []
        missing_fields: list[str] = []
        for field in ("uk_ipa", "us_ipa"):
            value = entry[field].strip()
            if not value:
                missing_fields.append(field)
            elif (
                not value.startswith("/")
                or not value.endswith("/")
                or IPA_MARKUP_PATTERN.search(value)
            ):
                malformed_fields.append(field)
        if malformed_fields:
            malformed_ipa_rows.append({
                **entry,
                "malformed_fields": "|".join(malformed_fields),
            })
        regional_reasons = []
        uk_ipa = entry["uk_ipa"]
        us_ipa = entry["us_ipa"]
        evidence = regional_ipa_evidence.get((
            entry["normalized_word"],
            entry["part_of_speech"].lower(),
            entry["en_definition"],
        ), {"uk": set(), "us": set()})
        if "oʊ" in uk_ipa and uk_ipa not in evidence["uk"]:
            regional_reasons.append("uk_contains_general_american_goat")
        if (
            re.search(r"[ɝɚ]", uk_ipa)
            and uk_ipa not in evidence["uk"]
        ):
            regional_reasons.append("uk_contains_r_colored_vowel")
        if "əʊ" in us_ipa and us_ipa not in evidence["us"]:
            regional_reasons.append("us_contains_british_goat")
        if "ɒ" in us_ipa and us_ipa not in evidence["us"]:
            regional_reasons.append("us_contains_british_lot")
        if (
            re.search(r"\([ɹr]\)", us_ipa)
            and us_ipa not in evidence["us"]
        ):
            regional_reasons.append("us_contains_optional_non_rhotic_r")
        if regional_reasons:
            suspicious_regional_ipa_rows.append({
                **entry,
                "regional_ipa_reasons": "|".join(regional_reasons),
            })
        if missing_fields:
            missing_uk_ipa_count += "uk_ipa" in missing_fields
            missing_us_ipa_count += "us_ipa" in missing_fields
            missing_ipa_rows.append({
                **entry,
                "missing_fields": "|".join(missing_fields),
            })

        try:
            examples = json.loads(entry["examples_json"])
        except (TypeError, json.JSONDecodeError) as error:
            invalid_example_rows.append({
                **entry,
                "example_issue": f"invalid_json: {error}",
            })
            examples = None
        if examples == []:
            missing_example_rows.append(entry)
        elif examples is not None:
            if not isinstance(examples, list) or any(
                not isinstance(example, dict)
                or not str(example.get("english", "")).strip()
                or not str(example.get("chinese", "")).strip()
                or not HAN_PATTERN.search(str(example.get("chinese", "")))
                for example in examples
            ):
                invalid_example_rows.append({
                    **entry,
                    "example_issue": "missing_or_non_chinese_example_field",
                })

        part = entry["part_of_speech"].lower()
        grammar_key = (
            entry["normalized_word"],
            part,
            entry["en_definition"],
        )
        if (
            part in {"noun", "verb"}
            and not entry["countability"].strip()
            and grammar_key not in grammar_exemption_keys
            and not entry["en_definition"].lstrip().lower().startswith(
                "(auxiliary"
            )
        ):
            missing_grammar_label_rows.append(entry)
        if part in {"other", "phraseologicalunit", "postposition"}:
            nonstandard_part_rows.append(entry)

        chinese = entry["zh_definition"].strip()
        reasons = corruption_reasons(chinese)
        if reasons:
            corrupt_rows.append({
                **entry,
                "reasons": "|".join(reasons),
                "safe_decoded_value": urllib.parse.unquote(chinese),
            })
        decoded_chinese = urllib.parse.unquote(chinese)
        if chinese and not HAN_PATTERN.search(decoded_chinese):
            non_chinese_rows.append(entry)
        if len(chinese) == 1:
            one_character_rows.append(entry)

        key = (
            entry["normalized_word"],
            entry["part_of_speech"],
            chinese,
        )
        grouped_definitions[key].add(entry["en_definition"])
        local_parts[entry["normalized_word"]].add(
            "exclamation" if part == "interjection" else part
        )

    all_definition_conflicts = [
        {
            "normalized_word": word,
            "part_of_speech": part,
            "zh_definition": chinese,
            "english_definition_count": len(definitions),
            "english_definitions": " || ".join(sorted(definitions)),
        }
        for (word, part, chinese), definitions in grouped_definitions.items()
        if len(definitions) >= 2
    ]
    resolution_keys = load_alignment_resolution_keys(alignment_resolutions)
    one_character_resolution_keys = load_one_character_resolution_keys(
        one_character_resolutions
    )
    all_one_character_rows = one_character_rows
    one_character_rows = [
        entry
        for entry in all_one_character_rows
        if (
            entry["normalized_word"],
            entry["part_of_speech"].lower(),
            entry["zh_definition"],
            entry["en_definition"],
        ) not in one_character_resolution_keys
    ]
    definition_conflicts = [
        row
        for row in all_definition_conflicts
        if (
            row["normalized_word"],
            row["part_of_speech"].lower(),
            row["zh_definition"],
        ) not in resolution_keys
    ]
    definition_conflicts.sort(
        key=lambda row: (-row["english_definition_count"], row["normalized_word"])
    )

    semantic_items = load_semantic_corrections(semantic_corrections)
    semantic_group_keys = {
        (
            str(item["word"]).strip().lower(),
            str(item["part_of_speech"]).strip().lower(),
            str(item["new_chinese"]).strip(),
        )
        for item in semantic_items
    }
    definition_conflicts = [
        row
        for row in definition_conflicts
        if (
            row["normalized_word"],
            row["part_of_speech"].lower(),
            row["zh_definition"],
        ) not in semantic_group_keys
    ]
    entries_by_semantic_key = {
        (
            entry["normalized_word"],
            entry["part_of_speech"].lower(),
            entry["en_definition"],
        ): entry
        for entry in entries
    }
    for item in semantic_items:
        key = (
            str(item["word"]).strip().lower(),
            str(item["part_of_speech"]).strip().lower(),
            str(item["english"]).strip(),
        )
        entry = entries_by_semantic_key.get(key)
        if entry is None:
            continue
        expected_chinese = traditional(str(item["new_chinese"]).strip())
        actual_chinese = traditional(str(entry["zh_definition"]).strip())
        if actual_chinese != expected_chinese:
            semantic_correction_failures.append({
                "word": item["word"],
                "part_of_speech": item["part_of_speech"],
                "expected_chinese": expected_chinese,
                "actual_chinese": entry["zh_definition"],
                "english_definition": item["english"],
                "failure_reason": "corrected_chinese_not_applied",
            })

    missing_parts: list[dict] = []
    if oewn_archive:
        oewn_parts = load_oewn_parts(oewn_archive)
        for word, expected_parts in oewn_parts.items():
            if word not in local_parts:
                continue
            for missing_part in sorted(
                (expected_parts & CORE_POS) - local_parts[word]
            ):
                if (word, missing_part) in missing_part_resolution_keys:
                    continue
                missing_parts.append({
                    "normalized_word": word,
                    "missing_part_of_speech": missing_part,
                    "local_parts_of_speech": "|".join(sorted(local_parts[word])),
                })

    write_csv(
        output / "malformed_ipa.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json", "malformed_fields",
        ],
        malformed_ipa_rows,
    )
    write_csv(
        output / "missing_ipa.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json", "missing_fields",
        ],
        missing_ipa_rows,
    )
    write_csv(
        output / "missing_examples.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json",
        ],
        missing_example_rows,
    )
    write_csv(
        output / "invalid_examples.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json", "example_issue",
        ],
        invalid_example_rows,
    )
    write_csv(
        output / "suspicious_regional_ipa.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "regional_ipa_reasons",
        ],
        suspicious_regional_ipa_rows,
    )
    write_csv(
        output / "missing_grammar_labels.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json",
        ],
        missing_grammar_label_rows,
    )
    write_csv(
        output / "nonstandard_parts_of_speech.csv",
        [
            "id", "word", "normalized_word", "uk_ipa", "us_ipa",
            "part_of_speech", "countability", "zh_definition",
            "en_definition", "examples_json",
        ],
        nonstandard_part_rows,
    )
    write_csv(
        output / "definite_corruption.csv",
        [
            "id", "word", "normalized_word", "part_of_speech",
            "countability", "zh_definition", "en_definition", "reasons",
            "safe_decoded_value",
        ],
        corrupt_rows,
    )
    write_csv(
        output / "non_chinese_translation_review.csv",
        [
            "id", "word", "normalized_word", "part_of_speech",
            "countability", "zh_definition", "en_definition",
        ],
        non_chinese_rows,
    )
    write_csv(
        output / "one_character_chinese_review.csv",
        [
            "id", "word", "normalized_word", "part_of_speech",
            "countability", "zh_definition", "en_definition",
        ],
        one_character_rows,
    )
    write_csv(
        output / "definition_alignment_review.csv",
        [
            "normalized_word", "part_of_speech", "zh_definition",
            "english_definition_count", "english_definitions",
        ],
        definition_conflicts,
    )
    write_csv(
        output / "missing_part_of_speech_candidates.csv",
        [
            "normalized_word", "missing_part_of_speech",
            "local_parts_of_speech",
        ],
        missing_parts,
    )
    write_csv(
        output / "semantic_correction_failures.csv",
        [
            "word", "part_of_speech", "expected_chinese",
            "actual_chinese", "english_definition", "failure_reason",
        ],
        semantic_correction_failures,
    )

    summary = {
        "entry_count": len(entries),
        "headword_count": len(local_parts),
        "malformed_ipa_count": len(malformed_ipa_rows),
        "suspicious_regional_ipa_count": len(
            suspicious_regional_ipa_rows
        ),
        "missing_ipa_count": len(missing_ipa_rows),
        "missing_uk_ipa_count": missing_uk_ipa_count,
        "missing_us_ipa_count": missing_us_ipa_count,
        "missing_example_count": len(missing_example_rows),
        "invalid_example_count": len(invalid_example_rows),
        "missing_grammar_label_count": len(missing_grammar_label_rows),
        "nonstandard_part_of_speech_count": len(nonstandard_part_rows),
        "definite_corruption_count": len(corrupt_rows),
        "non_chinese_translation_review_count": len(non_chinese_rows),
        "one_character_chinese_count": len(one_character_rows),
        "reviewed_one_character_chinese_count": (
            len(all_one_character_rows) - len(one_character_rows)
        ),
        "definition_alignment_review_count": len(definition_conflicts),
        "reviewed_definition_alignment_count": (
            len(all_definition_conflicts) - len(definition_conflicts)
        ),
        "definition_alignment_resolution_ledger_count": len(resolution_keys),
        "missing_part_of_speech_candidate_count": len(missing_parts),
        "missing_part_of_speech_by_type": dict(
            Counter(row["missing_part_of_speech"] for row in missing_parts)
        ),
        "reviewed_semantic_correction_count": len(semantic_items),
        "semantic_correction_failure_count": len(
            semantic_correction_failures
        ),
        "provenance_record_count": sum(provenance_counts.values()),
        "provenance_counts": provenance_counts,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    connection.close()

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("DictionaryAudit"),
    )
    parser.add_argument(
        "--oewn",
        type=Path,
        help="Optional Open English WordNet JSON zip for POS comparison.",
    )
    parser.add_argument(
        "--alignment-resolutions",
        type=Path,
        default=Path("Tools/DictionaryBuilder/alignment_review_resolutions.json"),
    )
    parser.add_argument(
        "--one-character-resolutions",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/one_character_review_resolutions.json"
        ),
    )
    parser.add_argument(
        "--grammar-structural-resolutions",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/grammar_manual_review.json"
        ),
    )
    parser.add_argument(
        "--pronunciation-resolutions",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/pronunciation_review_resolutions.json"
        ),
    )
    parser.add_argument(
        "--semantic-corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/ai_semantic_corrections.json"
        ),
    )
    args = parser.parse_args()
    audit(
        args.database,
        args.output,
        args.oewn,
        args.alignment_resolutions,
        args.one_character_resolutions,
        args.grammar_structural_resolutions,
        args.pronunciation_resolutions,
        args.semantic_corrections,
    )


if __name__ == "__main__":
    main()
