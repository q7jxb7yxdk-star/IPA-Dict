#!/usr/bin/env python3
"""Create a conservatively cleaned copy of the dictionary database."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import urllib.parse
from pathlib import Path

from generate_common_curation import traditional
from generate_fallback_content import (
    ensure_provenance_table,
    fill_generated_examples,
    fill_generated_pronunciations,
    record_default_provenance,
    record_reviewed_semantics,
)


MARKUP_PATTERN = re.compile(r"\[\[|\]\]|\{\{|\}\}")
PERCENT_ENCODING_PATTERN = re.compile(r"(?:%[0-9A-Fa-f]{2}){2,}")
HAN_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
IPA_SLASH_PATTERN = re.compile(r"/([^/\n]+?)/")
IPA_BRACKET_PATTERN = re.compile(r"^\[([^\]\n]+)\]")
GRAMMAR_LABEL_PATTERN = re.compile(r"^\(([^)]*)\)")
DEFINITION_SEPARATOR_PATTERN = re.compile(r"[；;，,、／/（）()\s]+")


def normalized_part_of_speech(value: str) -> str:
    normalized = value.strip()
    aliases = {
        "interjection": "exclamation",
        "phraseologicalunit": "phrase",
        "postposition": "preposition",
    }
    return aliases.get(normalized.lower(), normalized)


def safely_clean_ipa(value: str) -> str:
    """Return a display-safe IPA value without source markup."""
    cleaned = value.strip()
    if not cleaned:
        return ""
    slash = IPA_SLASH_PATTERN.search(cleaned)
    if slash:
        return f"/{slash.group(1).strip()}/"
    bracket = IPA_BRACKET_PATTERN.match(cleaned)
    if bracket:
        return f"/{bracket.group(1).strip()}/"
    return ""


def inferred_grammar_label(part_of_speech: str, definition: str) -> str:
    """Infer countability/transitivity only from explicit source labels."""
    match = GRAMMAR_LABEL_PATTERN.match(definition.strip())
    if not match:
        return ""
    label = match.group(1).lower()
    part = normalized_part_of_speech(part_of_speech).lower()
    if part == "noun":
        has_countable = bool(re.search(r"\bcountable\b", label))
        has_uncountable = bool(re.search(r"\buncountable\b", label))
        if has_countable and has_uncountable:
            return "C or U"
        if has_countable:
            return "C"
        if has_uncountable:
            return "U"
    if part == "verb":
        if "ambitransitive" in label:
            return "I or T"
        has_transitive = bool(re.search(r"\btransitive\b", label))
        has_intransitive = bool(re.search(r"\bintransitive\b", label))
        if has_transitive and has_intransitive:
            return "I or T"
        if has_transitive:
            return "T"
        if has_intransitive:
            return "I"
    return ""


def example_matches_chinese_definition(
    chinese_definition: str,
    chinese_example: str,
) -> bool:
    """Require the example to contain at least one displayed definition term."""
    definition = traditional(chinese_definition.strip())
    example = traditional(chinese_example.strip())
    if not definition or not example:
        return False
    terms = [
        term
        for term in DEFINITION_SEPARATOR_PATTERN.split(definition)
        if term
        and not term.startswith("（")
        and not re.fullmatch(r"[A-Za-z0-9+.#-]+", term)
    ]
    return any(term in example for term in terms)


def load_curated_data(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for supplemental_name in (
        "common_word_replacements.json",
        "chatgpt_reviewed_replacements.json",
        "codex_reviewed_replacements.json",
    ):
        generated_path = path.with_name(supplemental_name)
        if not generated_path.exists():
            continue
        generated = json.loads(generated_path.read_text(encoding="utf-8"))
        replacements = data.setdefault("word_replacements", {})
        overlap = replacements.keys() & generated.get("word_replacements", {}).keys()
        if overlap:
            if supplemental_name in {
                "chatgpt_reviewed_replacements.json",
                "codex_reviewed_replacements.json",
            }:
                for word in overlap:
                    replacements.pop(word)
            else:
                raise RuntimeError(
                    f"{supplemental_name} overlaps existing replacement entries: "
                    + ", ".join(sorted(overlap))
                )
        replacements.update(generated.get("word_replacements", {}))
        superseded = data.setdefault(
            "superseded_resolution_words",
            [],
        )
        superseded.extend(
            word
            for word in generated.get(
                "superseded_resolution_words",
                [],
            )
            if word not in superseded
        )
    return data


def load_alignment_resolutions(path: Path) -> list[dict]:
    resolution_path = path.with_name("alignment_review_resolutions.json")
    if not resolution_path.exists():
        return []
    return json.loads(
        resolution_path.read_text(encoding="utf-8")
    ).get("resolutions", [])


def load_one_character_resolutions(path: Path) -> list[dict]:
    resolution_path = path.with_name("one_character_review_resolutions.json")
    if not resolution_path.exists():
        return []
    return json.loads(
        resolution_path.read_text(encoding="utf-8")
    ).get("resolutions", [])


def load_pronunciation_resolutions(path: Path) -> list[dict]:
    resolution_path = path.with_name(
        "pronunciation_review_resolutions.json"
    )
    if not resolution_path.exists():
        return []
    return json.loads(
        resolution_path.read_text(encoding="utf-8")
    ).get("resolutions", [])


def load_grammar_resolutions(path: Path) -> list[dict]:
    resolution_path = path.with_name("grammar_review_resolutions.json")
    if not resolution_path.exists():
        return []
    return json.loads(
        resolution_path.read_text(encoding="utf-8")
    ).get("resolutions", [])


def load_grammar_structural_resolutions(path: Path) -> list[dict]:
    resolutions = []
    for name in (
        "grammar_manual_review.json",
        "noun_countability_review.json",
    ):
        resolution_path = path.with_name(name)
        if not resolution_path.exists():
            continue
        resolutions.extend(
            item
            for item in json.loads(
                resolution_path.read_text(encoding="utf-8")
            ).get("reviews", [])
            if isinstance(item.get("structural_resolution"), dict)
        )
    return resolutions


def apply_grammar_structural_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> int:
    updated = 0
    for item in resolutions:
        resolved = item["structural_resolution"]
        if resolved.get("action") == "delete":
            cursor = connection.execute(
                """
                DELETE FROM entries
                WHERE normalized_word = ?
                  AND lower(part_of_speech) = lower(?)
                  AND en_definition = ?
                """,
                (
                    item["word"],
                    item["part_of_speech"],
                    item["english"],
                ),
            )
            if cursor.rowcount == 1:
                updated += 1
                continue
            retained = connection.execute(
                """
                SELECT 1 FROM entries
                WHERE normalized_word = ?
                  AND lower(part_of_speech) = lower(?)
                  AND en_definition = ?
                LIMIT 1
                """,
                (
                    item["word"],
                    item["part_of_speech"],
                    item["english"],
                ),
            ).fetchone()
            if retained:
                raise RuntimeError(
                    "Grammar structural deletion did not match exactly: "
                    f"{item['word']} [{item['part_of_speech']}]"
                )
            continue
        cursor = connection.execute(
            """
            UPDATE entries
            SET part_of_speech = ?, countability = ?,
                zh_definition = ?, en_definition = ?
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
            """,
            (
                resolved["new_part_of_speech"],
                resolved["new_countability"],
                resolved["new_chinese"],
                resolved["new_english"],
                item["word"],
                item["part_of_speech"],
                item["english"],
            ),
        )
        if cursor.rowcount == 1:
            updated += 1
            continue
        retained = connection.execute(
            """
            SELECT 1 FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND countability = ?
              AND zh_definition = ?
              AND en_definition = ?
            LIMIT 1
            """,
            (
                item["word"],
                resolved["new_part_of_speech"],
                resolved["new_countability"],
                resolved["new_chinese"],
                resolved["new_english"],
            ),
        ).fetchone()
        if not retained:
            raise RuntimeError(
                "Grammar structural resolution did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}]"
            )
    return updated


def remap_example_resolutions(
    resolutions: list[dict],
    structural_resolutions: list[dict],
) -> list[dict]:
    structural_by_key = {
        (
            item["word"],
            item["part_of_speech"].lower(),
            item["english"],
        ): item["structural_resolution"]
        for item in structural_resolutions
    }
    remapped = []
    for item in resolutions:
        resolved = structural_by_key.get((
            item["word"],
            item["part_of_speech"].lower(),
            item["english"],
        ))
        if not resolved:
            remapped.append(item)
            continue
        if resolved.get("action") == "delete":
            continue
        mapped = {
            **item,
            "part_of_speech": resolved["new_part_of_speech"],
            "chinese": resolved["new_chinese"],
            "english": resolved["new_english"],
        }
        example = mapped.get("example")
        if isinstance(example, dict):
            chinese_example = str(example.get("chinese", "")).strip()
            if not (
                example_matches_chinese_definition(
                    mapped["chinese"],
                    chinese_example,
                )
                or mapped["chinese"].strip() in chinese_example
            ):
                mapped["example"] = None
                mapped["status"] = (
                    "removed_by_structural_sense_correction"
                )
        remapped.append(mapped)
    return remapped


def exclude_structurally_resolved_items(
    resolutions: list[dict],
    structural_resolutions: list[dict],
) -> list[dict]:
    structural_keys = {
        (
            item["word"],
            item["part_of_speech"].lower(),
            item["english"],
        )
        for item in structural_resolutions
    }
    return [
        item
        for item in resolutions
        if (
            item["word"],
            item["part_of_speech"].lower(),
            item["english"],
        ) not in structural_keys
    ]


def exclude_replaced_words(
    resolutions: list[dict],
    replacement_words: set[str],
) -> list[dict]:
    """Ignore obsolete exact-sense decisions for fully rebuilt headwords."""
    return [
        item
        for item in resolutions
        if str(item.get("word", "")).strip().lower()
        not in replacement_words
    ]


def load_example_resolutions(path: Path) -> list[dict]:
    resolutions = []
    tatoeba_path = path.with_name("example_review_resolutions.json")
    if tatoeba_path.exists():
        resolutions.extend(json.loads(
            tatoeba_path.read_text(encoding="utf-8")
        ).get("resolutions", []))

    wikimatrix_path = path.with_name(
        "wikimatrix_example_review.json"
    )
    if wikimatrix_path.exists():
        resolutions.extend(
            item
            for item in json.loads(
                wikimatrix_path.read_text(encoding="utf-8")
            ).get("reviews", [])
            if item.get("decision") == "approved"
        )
    rebuild_path = path.with_name("rebuild_example_review.json")
    if rebuild_path.exists():
        resolutions.extend(
            item
            for item in json.loads(
                rebuild_path.read_text(encoding="utf-8")
            ).get("reviews", [])
            if item.get("decision") == "approved"
        )
    return resolutions


def load_semantic_corrections(path: Path) -> list[dict]:
    correction_path = path.with_name("ai_semantic_corrections.json")
    if not correction_path.exists():
        return []
    return json.loads(
        correction_path.read_text(encoding="utf-8")
    ).get("corrections", [])


def exclude_semantically_corrected_items(
    resolutions: list[dict],
    corrections: list[dict],
) -> list[dict]:
    corrected_keys = {
        (
            str(item["word"]).strip().lower(),
            normalized_part_of_speech(
                str(item["part_of_speech"])
            ).lower(),
            str(item["english"]).strip(),
        )
        for item in corrections
    }
    return [
        item
        for item in resolutions
        if (
            str(item["word"]).strip().lower(),
            normalized_part_of_speech(
                str(item["part_of_speech"])
            ).lower(),
            str(item["english"]).strip(),
        ) not in corrected_keys
    ]


def apply_semantic_corrections(
    connection: sqlite3.Connection,
    corrections: list[dict],
) -> int:
    corrected = 0
    for item in corrections:
        new_chinese = str(item["new_chinese"]).strip()
        example = item.get("example")
        examples_json = None
        if isinstance(example, dict):
            english_example = str(example.get("english", "")).strip()
            chinese_example = str(example.get("chinese", "")).strip()
            if (
                not english_example
                or not chinese_example
                or not example_matches_chinese_definition(
                    new_chinese,
                    chinese_example,
                )
            ):
                raise RuntimeError(
                    f"Invalid semantic example for {item['word']}"
                )
            examples_json = json.dumps(
                [{
                    "english": english_example,
                    "chinese": chinese_example,
                }],
                ensure_ascii=False,
            )

        row = connection.execute(
            """
            SELECT id, zh_definition, examples_json
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
            """,
            (
                item["word"].strip().lower(),
                item["part_of_speech"],
                item["english"],
            ),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "Semantic correction did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}]"
            )
        entry_id, current_chinese, current_examples = row
        expected_chinese = str(item["old_chinese"]).strip()
        if current_chinese not in {expected_chinese, new_chinese}:
            raise RuntimeError(
                "Semantic correction source changed: "
                f"{item['word']} [{item['part_of_speech']}] "
                f"expected {expected_chinese!r}, found {current_chinese!r}"
            )
        next_examples = examples_json or current_examples
        if (
            current_chinese == new_chinese
            and current_examples == next_examples
        ):
            continue
        connection.execute(
            """
            UPDATE entries
            SET zh_definition = ?, examples_json = ?
            WHERE id = ?
            """,
            (new_chinese, next_examples, entry_id),
        )
        corrected += 1
    return corrected


def apply_grammar_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> int:
    updated = 0
    for item in resolutions:
        label = item.get("grammar_label", "")
        if not label:
            continue
        cursor = connection.execute(
            """
            UPDATE entries
            SET countability = ?
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
              AND countability = ''
            """,
            (
                label,
                item["word"],
                item["part_of_speech"],
                item["english"],
            ),
        )
        if cursor.rowcount == 1:
            updated += 1
            continue
        retained = connection.execute(
            """
            SELECT 1
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
              AND countability = ?
            LIMIT 1
            """,
            (
                item["word"],
                item["part_of_speech"],
                item["english"],
                label,
            ),
        ).fetchone()
        if not retained:
            raise RuntimeError(
                "Grammar resolution did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}]"
            )
    return updated


def apply_example_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
    replace_existing: bool = False,
) -> int:
    updated = 0
    for item in resolutions:
        example = item.get("example")
        if not isinstance(example, dict):
            continue
        english_example = str(example.get("english", "")).strip()
        chinese_example = str(example.get("chinese", "")).strip()
        if (
            not english_example
            or not chinese_example
            or not (
                example_matches_chinese_definition(
                    item["chinese"],
                    chinese_example,
                )
                or (
                    item["chinese"].strip()
                    and item["chinese"].strip() in chinese_example
                )
            )
        ):
            raise RuntimeError(
                f"Invalid example resolution for {item['word']}"
            )
        encoded = json.dumps(
            [{
                "english": english_example,
                "chinese": chinese_example,
            }],
            ensure_ascii=False,
        )
        query = """
            UPDATE entries
            SET examples_json = ?
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
              AND en_definition = ?
        """
        parameters = (
            encoded,
            item["word"],
            item["part_of_speech"],
            item["chinese"],
            item["english"],
        )
        if not replace_existing:
            query += " AND examples_json = '[]'"
        cursor = connection.execute(query, parameters)
        if cursor.rowcount == 1:
            updated += 1
            continue
        retained = connection.execute(
            """
            SELECT 1
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
              AND en_definition = ?
              AND examples_json = ?
            LIMIT 1
            """,
            (
                item["word"],
                item["part_of_speech"],
                item["chinese"],
                item["english"],
                encoded,
            ),
        ).fetchone()
        if not retained:
            raise RuntimeError(
                "Example resolution did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}]"
            )
    return updated


def apply_pronunciation_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> tuple[int, int]:
    uk_updated = 0
    us_updated = 0
    for item in resolutions:
        uk_ipa = safely_clean_ipa(item.get("uk_ipa", ""))
        us_ipa = safely_clean_ipa(item.get("us_ipa", ""))
        clear_uk = bool(item.get("clear_uk", False))
        clear_us = bool(item.get("clear_us", False))
        if not uk_ipa and not us_ipa and not clear_uk and not clear_us:
            continue
        row = connection.execute(
            """
            SELECT id, uk_ipa, us_ipa
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND en_definition = ?
            """,
            (
                item["word"],
                item["part_of_speech"],
                item["english"],
            ),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "Pronunciation resolution did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}]"
            )
        entry_id, current_uk, current_us = row
        if clear_uk and not uk_ipa:
            next_uk = ""
        else:
            next_uk = (
                uk_ipa
                if uk_ipa and item.get("replace_uk", False)
                else current_uk or uk_ipa
            )
        if clear_us and not us_ipa:
            next_us = ""
        else:
            next_us = (
                us_ipa
                if us_ipa and item.get("replace_us", False)
                else current_us or us_ipa
            )
        if next_uk == current_uk and next_us == current_us:
            continue
        connection.execute(
            "UPDATE entries SET uk_ipa = ?, us_ipa = ? WHERE id = ?",
            (next_uk, next_us, entry_id),
        )
        uk_updated += next_uk != current_uk
        us_updated += next_us != current_us
    return uk_updated, us_updated


def apply_one_character_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> int:
    corrected = 0
    for item in resolutions:
        resolved = item.get("resolved_chinese", item["chinese"])
        if resolved == item["chinese"]:
            continue
        cursor = connection.execute(
            """
            UPDATE entries
            SET zh_definition = ?
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
              AND en_definition = ?
            """,
            (
                resolved,
                item["word"],
                item["part_of_speech"],
                item["chinese"],
                item["english"],
            ),
        )
        if cursor.rowcount == 1:
            corrected += 1
            continue
        retained = connection.execute(
            """
            SELECT 1
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
              AND en_definition = ?
            LIMIT 1
            """,
            (
                item["word"],
                item["part_of_speech"],
                resolved,
                item["english"],
            ),
        ).fetchone()
        if not retained:
            raise RuntimeError(
                "One-character resolution did not match exactly: "
                f"{item['word']} [{item['part_of_speech']}] "
                f"{item['chinese']}"
            )
    return corrected


def apply_alignment_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> int:
    deleted = 0
    for item in resolutions:
        keep_english = item.get("keep_english", "")
        if not keep_english:
            continue
        rows = connection.execute(
            """
            SELECT id, en_definition
            FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
            """,
            (item["word"], item["part_of_speech"], item["chinese"]),
        ).fetchall()
        resolved_chinese = item.get("resolved_chinese", item["chinese"])
        if not rows and resolved_chinese != item["chinese"]:
            retained = connection.execute(
                """
                SELECT 1
                FROM entries
                WHERE normalized_word = ?
                  AND lower(part_of_speech) = lower(?)
                  AND zh_definition = ?
                  AND en_definition = ?
                LIMIT 1
                """,
                (
                    item["word"],
                    item["part_of_speech"],
                    resolved_chinese,
                    keep_english,
                ),
            ).fetchone()
            if retained:
                continue
        if not any(english == keep_english for _, english in rows):
            raise RuntimeError(
                "Alignment resolution did not match its retained definition: "
                f"{item['word']} [{item['part_of_speech']}] "
                f"{item['chinese']}"
            )
        retained_id = next(
            entry_id
            for entry_id, english in rows
            if english == keep_english
        )
        if resolved_chinese != item["chinese"]:
            connection.execute(
                "UPDATE entries SET zh_definition = ? WHERE id = ?",
                (resolved_chinese, retained_id),
            )
        for entry_id, english in rows:
            if english == keep_english:
                continue
            connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            deleted += 1
    return deleted


def apply_superseded_alignment_resolutions(
    connection: sqlite3.Connection,
    resolutions: list[dict],
) -> int:
    """Delete old sibling senses replaced by one structural resolution."""
    deleted = 0
    for item in resolutions:
        if item.get("status") != "superseded_by_structural_resolution":
            continue
        cursor = connection.execute(
            """
            DELETE FROM entries
            WHERE normalized_word = ?
              AND lower(part_of_speech) = lower(?)
              AND zh_definition = ?
            """,
            (
                item["word"],
                item["part_of_speech"],
                item["chinese"],
            ),
        )
        deleted += cursor.rowcount
    return deleted


def apply_curated_data(
    connection: sqlite3.Connection,
    curated_data: dict,
) -> tuple[int, int]:
    replacement_words = {
        word.strip().lower()
        for word in curated_data.get("word_replacements", {})
    }
    corrections = {
        (
            item["word"].strip().lower(),
            normalized_part_of_speech(item["part_of_speech"]).lower(),
            item["english"],
        ): item["chinese"]
        for item in curated_data.get("corrections", [])
        if item["word"].strip().lower() not in replacement_words
    }
    matched_corrections: set[tuple[str, str, str]] = set()

    rows = connection.execute(
        """
        SELECT id, normalized_word, part_of_speech, en_definition
        FROM entries
        """
    ).fetchall()
    for entry_id, word, part, english in rows:
        key = (
            word.strip().lower(),
            normalized_part_of_speech(part).lower(),
            english,
        )
        chinese = corrections.get(key)
        if chinese is None:
            continue
        connection.execute(
            "UPDATE entries SET zh_definition = ? WHERE id = ?",
            (chinese, entry_id),
        )
        matched_corrections.add(key)

    unmatched = set(corrections) - matched_corrections
    if unmatched:
        values = "\n".join(
            f"- {word} [{part}]: {english}"
            for word, part, english in sorted(unmatched)
        )
        raise RuntimeError(f"Unmatched curated corrections:\n{values}")

    replacement_count = 0
    for normalized_word, entries in curated_data.get(
        "word_replacements",
        {},
    ).items():
        connection.execute(
            "DELETE FROM entries WHERE normalized_word = ?",
            (normalized_word,),
        )
        for entry in entries:
            connection.execute(
                """
                INSERT INTO entries (
                    word, normalized_word, uk_ipa, us_ipa, part_of_speech,
                    countability, zh_definition, en_definition, examples_json,
                    synonyms_json, antonyms_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]')
                """,
                (
                    entry["word"],
                    normalized_word,
                    safely_clean_ipa(entry.get("uk_ipa", "")),
                    safely_clean_ipa(entry.get("us_ipa", "")),
                    normalized_part_of_speech(entry["part_of_speech"]),
                    entry.get("countability", ""),
                    entry["chinese"],
                    entry["english"],
                    json.dumps(entry.get("examples", []), ensure_ascii=False),
                ),
            )
            replacement_count += 1

    return len(matched_corrections), replacement_count


def safely_clean_chinese(value: str) -> str | None:
    cleaned = value.strip()
    if PERCENT_ENCODING_PATTERN.search(cleaned):
        cleaned = urllib.parse.unquote(cleaned)

    if cleaned.startswith("[[") and cleaned.endswith("]]"):
        cleaned = cleaned[2:-2].strip()
    if cleaned.endswith("]]") and "[[" not in cleaned:
        cleaned = cleaned[:-2].strip()

    if not cleaned or MARKUP_PATTERN.search(cleaned) or cleaned in {
        "&", "0.5", "[[#", "}}",
    }:
        return None
    return cleaned


def clean(
    source: Path,
    destination: Path,
    corrections_path: Path,
) -> None:
    if source.resolve() == destination.resolve():
        raise ValueError("Destination must not overwrite the source database.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    connection = sqlite3.connect(destination)
    # Provenance is derived from the final cleaned rows. Rebuild it from
    # scratch so deleted/reinserted curated entries cannot leave stale IDs.
    connection.execute("DROP TABLE IF EXISTS entry_provenance")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS quarantined_entries (
            original_id INTEGER,
            word TEXT NOT NULL,
            normalized_word TEXT NOT NULL,
            part_of_speech TEXT NOT NULL,
            zh_definition TEXT NOT NULL,
            en_definition TEXT NOT NULL,
            quarantine_reason TEXT NOT NULL
        )
    """)

    connection.execute("""
        UPDATE entries
        SET part_of_speech = 'exclamation'
        WHERE lower(part_of_speech) = 'interjection'
    """)
    connection.execute("""
        UPDATE entries
        SET part_of_speech = 'phrase'
        WHERE lower(part_of_speech) = 'phraseologicalunit'
    """)
    connection.execute("""
        UPDATE entries
        SET part_of_speech = 'preposition'
        WHERE lower(part_of_speech) = 'postposition'
    """)
    connection.execute("""
        UPDATE entries
        SET part_of_speech = 'phrase'
        WHERE lower(part_of_speech) = 'other'
          AND instr(normalized_word, ' ') > 0
    """)
    curated_data = load_curated_data(corrections_path)
    reviewed_replacement_words = {
        word.strip().lower()
        for word in curated_data.get("word_replacements", {})
    }
    superseded_resolution_words = {
        word.strip().lower()
        for word in curated_data.get(
            "superseded_resolution_words",
            [],
        )
    }
    corrected, replacements = apply_curated_data(connection, curated_data)
    structural_resolutions = exclude_replaced_words(
        load_grammar_structural_resolutions(corrections_path),
        superseded_resolution_words,
    )
    alignment_rows_deleted = apply_alignment_resolutions(
        connection,
        exclude_replaced_words(
            load_alignment_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    one_character_corrections = apply_one_character_resolutions(
        connection,
        exclude_structurally_resolved_items(
            exclude_replaced_words(
                load_one_character_resolutions(corrections_path),
                superseded_resolution_words,
            ),
            structural_resolutions,
        ),
    )
    grammar_corrections = apply_grammar_resolutions(
        connection,
        exclude_structurally_resolved_items(
            exclude_replaced_words(
                load_grammar_resolutions(corrections_path),
                superseded_resolution_words,
            ),
            structural_resolutions,
        ),
    )
    grammar_structural_corrections = apply_grammar_structural_resolutions(
        connection,
        structural_resolutions,
    )
    alignment_rows_deleted += apply_superseded_alignment_resolutions(
        connection,
        exclude_replaced_words(
            load_alignment_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    semantic_corrections = load_semantic_corrections(corrections_path)
    example_resolutions = exclude_semantically_corrected_items(
        remap_example_resolutions(
            exclude_replaced_words(
                load_example_resolutions(corrections_path),
                superseded_resolution_words,
            ),
            structural_resolutions,
        ),
        semantic_corrections,
    )
    example_corrections = apply_example_resolutions(
        connection,
        example_resolutions,
    )
    semantic_correction_count = apply_semantic_corrections(
        connection,
        semantic_corrections,
    )
    reviewed_example_keys = {
        (
            item["word"].strip().lower(),
            normalized_part_of_speech(item["part_of_speech"]).lower(),
            item["chinese"].strip(),
            item["english"].strip(),
        )
        for item in example_resolutions
        if isinstance(item.get("example"), dict)
    }
    reviewed_example_keys.update(
        (
            item["word"].strip().lower(),
            normalized_part_of_speech(item["part_of_speech"]).lower(),
            item["new_chinese"].strip(),
            item["english"].strip(),
        )
        for item in semantic_corrections
        if isinstance(item.get("example"), dict)
    )
    pronunciation_uk = 0
    pronunciation_us = 0

    rows = connection.execute(
        """
        SELECT id, word, normalized_word, uk_ipa, us_ipa, part_of_speech,
               countability, zh_definition, en_definition
        FROM entries
        ORDER BY id
        """
    ).fetchall()
    repaired = 0
    ipa_repaired = 0
    grammar_labels_inferred = 0
    mismatched_examples_removed = 0
    quarantined = 0

    for row in rows:
        (
            entry_id, word, normalized_word, uk_ipa, us_ipa, part,
            countability, chinese, english,
        ) = row
        cleaned_uk = safely_clean_ipa(uk_ipa)
        cleaned_us = safely_clean_ipa(us_ipa)
        if cleaned_uk != uk_ipa or cleaned_us != us_ipa:
            connection.execute(
                "UPDATE entries SET uk_ipa = ?, us_ipa = ? WHERE id = ?",
                (cleaned_uk, cleaned_us, entry_id),
            )
            ipa_repaired += 1

        inferred_label = (
            inferred_grammar_label(part, english)
            if not countability.strip()
            else ""
        )
        if inferred_label:
            connection.execute(
                "UPDATE entries SET countability = ? WHERE id = ?",
                (inferred_label, entry_id),
            )
            grammar_labels_inferred += 1

        reviewed_example_key = (
            normalized_word,
            normalized_part_of_speech(part).lower(),
            chinese.strip(),
            english.strip(),
        )
        if (
            normalized_word not in reviewed_replacement_words
            and reviewed_example_key not in reviewed_example_keys
        ):
            examples_json = connection.execute(
                "SELECT examples_json FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()[0]
            try:
                examples = json.loads(examples_json)
            except (TypeError, json.JSONDecodeError):
                examples = []
            # Unreviewed headword-level fallback examples can match the
            # Chinese term while illustrating a different English sense.
            # Only exact-sense review ledgers or curated replacements may
            # retain an example.
            valid_examples = []
            if valid_examples != examples:
                connection.execute(
                    "UPDATE entries SET examples_json = ? WHERE id = ?",
                    (
                        json.dumps(valid_examples[:1], ensure_ascii=False),
                        entry_id,
                    ),
                )
                mismatched_examples_removed += 1

        cleaned = safely_clean_chinese(chinese)
        if cleaned is None:
            connection.execute(
                """
                INSERT INTO quarantined_entries (
                    original_id, word, normalized_word, part_of_speech,
                    zh_definition, en_definition, quarantine_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id, word, normalized_word, part, chinese, english,
                    "invalid_or_non_chinese_definition",
                ),
            )
            connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            quarantined += 1
        elif cleaned != chinese:
            connection.execute(
                "UPDATE entries SET zh_definition = ? WHERE id = ?",
                (cleaned, entry_id),
            )
            repaired += 1

    pronunciation_uk, pronunciation_us = apply_pronunciation_resolutions(
        connection,
        exclude_replaced_words(
            load_pronunciation_resolutions(corrections_path),
            superseded_resolution_words,
        ),
    )
    ensure_provenance_table(connection)
    generated_examples = fill_generated_examples(connection)
    generated_uk, generated_us = fill_generated_pronunciations(connection)
    reviewed_semantic_provenance = record_reviewed_semantics(
        connection,
        semantic_corrections,
    )
    default_provenance = record_default_provenance(connection)

    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_alignment_rows_deleted', ?)
        """,
        (str(alignment_rows_deleted),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_one_character_corrections', ?)
        """,
        (str(one_character_corrections),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_grammar_corrections', ?)
        """,
        (str(grammar_corrections),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_grammar_structural_corrections', ?)
        """,
        (str(grammar_structural_corrections),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_example_corrections', ?)
        """,
        (str(example_corrections),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_semantic_corrections', ?)
        """,
        (str(semantic_correction_count),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_generated_fallback_examples', ?)
        """,
        (str(generated_examples),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_generated_fallback_uk_ipa', ?)
        """,
        (str(generated_uk),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_generated_fallback_us_ipa', ?)
        """,
        (str(generated_us),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_reviewed_semantic_provenance', ?)
        """,
        (str(reviewed_semantic_provenance),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_default_provenance_records', ?)
        """,
        (str(default_provenance),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_pronunciation_uk', ?)
        """,
        (str(pronunciation_uk),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_pronunciation_us', ?)
        """,
        (str(pronunciation_us),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_removed_mismatched_examples', ?)
        """,
        (str(mismatched_examples_removed),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_version', '1')
        """
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_quarantined_entries', ?)
        """,
        (str(quarantined),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_repaired_entries', ?)
        """,
        (str(repaired),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_repaired_ipa', ?)
        """,
        (str(ipa_repaired),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_inferred_grammar_labels', ?)
        """,
        (str(grammar_labels_inferred),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_curated_corrections', ?)
        """,
        (str(corrected),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('cleanup_replacement_entries', ?)
        """,
        (str(replacements),),
    )
    entry_count = connection.execute(
        "SELECT COUNT(*) FROM entries"
    ).fetchone()[0]
    headword_count = connection.execute(
        "SELECT COUNT(DISTINCT normalized_word) FROM entries"
    ).fetchone()[0]
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES ('entry_count', ?)",
        (str(entry_count),),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO metadata(key, value)
        VALUES ('headword_count', ?)
        """,
        (str(headword_count),),
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    print(
        f"Created {destination}: corrected {corrected}, "
        f"replacement entries {replacements}, repaired {repaired}, "
        f"IPA repaired {ipa_repaired}, grammar labels inferred "
        f"{grammar_labels_inferred}, mismatched examples removed "
        f"{mismatched_examples_removed}, alignment rows deleted "
        f"{alignment_rows_deleted}, one-character corrections "
        f"{one_character_corrections}, grammar structures corrected "
        f"{grammar_structural_corrections}, UK IPA updated {pronunciation_uk}, "
        f"US IPA updated {pronunciation_us}, grammar labels added "
        f"{grammar_corrections}, examples added {example_corrections}, "
        f"semantic corrections {semantic_correction_count}, "
        f"generated examples {generated_examples}, generated UK IPA "
        f"{generated_uk}, generated US IPA {generated_us}, "
        f"quarantined {quarantined}."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("IPA Dict/Data/dictionary.sqlite"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--corrections",
        type=Path,
        default=Path(
            "Tools/DictionaryBuilder/curated_corrections.json"
        ),
    )
    args = parser.parse_args()
    clean(args.source, args.output, args.corrections)


if __name__ == "__main__":
    main()
